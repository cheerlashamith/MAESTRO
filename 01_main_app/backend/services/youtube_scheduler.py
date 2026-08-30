"""
YouTube Scheduling & Resumable Upload Queue Manager.

Features:
- Persistent JSON queue in data/scheduled_uploads.json
- Native YouTube scheduling (publishAt timestamp) & Local queue scheduling
- Chunked resumable video uploads with live progress reporting
- Custom thumbnail uploading via YouTube Data API v3
- Background scheduler daemon for automated publishing
"""
from __future__ import annotations
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from googleapiclient.http import MediaFileUpload

from backend.core.config import project_root
from backend.core.job_store import get_job, update_job
from backend.core.schemas import ScheduledUploadRecord
from backend.services.youtube_auth import get_authenticated_service, is_authenticated

QUEUE_FILE = project_root() / "data" / "scheduled_uploads.json"
_LOCK = threading.Lock()
_SCHEDULER_STARTED = False


def _load_records() -> Dict[str, ScheduledUploadRecord]:
    if not QUEUE_FILE.exists():
        return {}
    try:
        data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        return {k: ScheduledUploadRecord(**v) for k, v in data.items()}
    except Exception as e:
        print(f"[YouTubeScheduler] Error loading queue file: {e}")
        return {}


def _save_records(records: Dict[str, ScheduledUploadRecord]) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v.model_dump() for k, v in records.items()}
    QUEUE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def schedule_upload(
    video_path: str,
    title: str,
    description: str,
    tags: List[str] = [],
    category_id: str = "27",
    privacy_status: str = "private",
    schedule_time: Optional[str] = None,
    schedule_mode: str = "local",
    thumbnail_path: Optional[str] = None,
    job_id: Optional[str] = None,
    immediate: bool = False
) -> ScheduledUploadRecord:
    """Add a new video upload to the scheduling queue."""
    schedule_id = uuid.uuid4().hex[:12]

    status = "scheduled"
    if immediate:
        schedule_time = None

    rec = ScheduledUploadRecord(
        schedule_id=schedule_id,
        job_id=job_id,
        video_path=str(Path(video_path).resolve()),
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
        schedule_time=schedule_time,
        schedule_mode=schedule_mode,
        thumbnail_path=str(Path(thumbnail_path).resolve()) if thumbnail_path and Path(thumbnail_path).exists() else None,
        status=status,
        progress=0,
        message="Queued for upload"
    )

    with _LOCK:
        records = _load_records()
        records[schedule_id] = rec
        _save_records(records)

    # Link to parent job if applicable
    if job_id:
        try:
            update_job(job_id, scheduled_upload_id=schedule_id)
        except Exception:
            pass

    # If immediate or already due, trigger upload in a worker thread
    if immediate or not schedule_time:
        t = threading.Thread(target=execute_upload, args=(schedule_id,), daemon=True)
        t.start()

    return rec


def list_scheduled() -> List[Dict[str, Any]]:
    """Return all scheduled and completed upload records sorted newest first."""
    with _LOCK:
        records = _load_records()
    items = list(records.values())
    items.sort(key=lambda x: x.created_at, reverse=True)
    return [item.model_dump() for item in items]


def get_scheduled(schedule_id: str) -> Optional[ScheduledUploadRecord]:
    with _LOCK:
        records = _load_records()
        return records.get(schedule_id)


def cancel_scheduled(schedule_id: str) -> bool:
    """Cancel a pending scheduled upload."""
    with _LOCK:
        records = _load_records()
        if schedule_id in records:
            if records[schedule_id].status in ["completed", "uploading"]:
                return False
            records[schedule_id].status = "cancelled"
            records[schedule_id].message = "Cancelled by user"
            _save_records(records)
            return True
    return False


def _update_record(schedule_id: str, **kwargs) -> Optional[ScheduledUploadRecord]:
    with _LOCK:
        records = _load_records()
        if schedule_id in records:
            rec_dict = records[schedule_id].model_dump()
            rec_dict.update(kwargs)
            updated = ScheduledUploadRecord(**rec_dict)
            records[schedule_id] = updated
            _save_records(records)
            return updated
    return None


def execute_upload(schedule_id: str) -> Dict[str, Any]:
    """Perform resumable upload of a queued item to YouTube."""
    rec = get_scheduled(schedule_id)
    if not rec:
        raise ValueError(f"Schedule record not found: {schedule_id}")

    if rec.status == "completed":
        return {"success": True, "video_id": rec.youtube_video_id, "url": rec.youtube_url}

    video_path = Path(rec.video_path)
    if not video_path.exists() or not video_path.is_file():
        err_msg = f"Video file not found: {video_path}"
        _update_record(schedule_id, status="failed", error=err_msg, message="File not found")
        raise FileNotFoundError(err_msg)

    if not is_authenticated():
        err_msg = "YouTube account is not connected. Connect channel first."
        _update_record(schedule_id, status="failed", error=err_msg, message="OAuth not connected")
        raise PermissionError(err_msg)

    _update_record(schedule_id, status="uploading", progress=5, message="Starting YouTube upload...")
    if rec.job_id:
        try:
            update_job(rec.job_id, current_task="Uploading to YouTube (0%)")
        except Exception:
            pass

    try:
        youtube = get_authenticated_service()

        # Build YouTube status payload
        status_body: Dict[str, Any] = {}
        if rec.schedule_mode == "native" and rec.schedule_time:
            # Native YouTube scheduled publication requires privacyStatus = "private" + publishAt timestamp
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = rec.schedule_time
        else:
            # Local schedule or direct publish
            privacy = rec.privacy_status
            if privacy not in ["public", "unlisted", "private"]:
                privacy = "private"
            status_body["privacyStatus"] = privacy

        body = {
            "snippet": {
                "title": rec.title[:100],
                "description": rec.description[:5000],
                "tags": rec.tags[:50],
                "categoryId": rec.category_id or "27",
            },
            "status": status_body,
        }

        # 2MB chunks for resumable upload
        chunk_size = 2 * 1024 * 1024
        media = MediaFileUpload(str(video_path), chunksize=chunk_size, resumable=True)

        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                pct = int(status.progress() * 85) + 5
                _update_record(schedule_id, progress=pct, message=f"Uploading video... {pct}%")
                if rec.job_id:
                    try:
                        update_job(rec.job_id, current_task=f"Uploading to YouTube ({pct}%)")
                    except Exception:
                        pass

        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube API did not return a valid video ID.")

        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        _update_record(schedule_id, progress=90, message="Processing uploaded video...")

        # Set custom thumbnail if available
        if rec.thumbnail_path and Path(rec.thumbnail_path).exists():
            try:
                _update_record(schedule_id, message="Setting custom thumbnail...")
                thumb_media = MediaFileUpload(rec.thumbnail_path)
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumb_media
                ).execute()
            except Exception as thumb_err:
                print(f"[YouTubeScheduler] Thumbnail upload error: {thumb_err}")

        # Update completed state
        now_iso = datetime.now(timezone.utc).isoformat()
        _update_record(
            schedule_id,
            status="completed",
            progress=100,
            message="Published successfully",
            youtube_video_id=video_id,
            youtube_url=watch_url,
            uploaded_at=now_iso,
            error=None
        )

        # Update parent JobRecord
        if rec.job_id:
            try:
                update_job(
                    rec.job_id,
                    youtube_video_id=video_id,
                    youtube_url=watch_url,
                    uploaded_at=now_iso,
                    current_task="Published to YouTube"
                )
            except Exception as e:
                print(f"[YouTubeScheduler] Error updating parent job: {e}")

        return {"success": True, "video_id": video_id, "url": watch_url}

    except Exception as e:
        err_str = str(e)
        print(f"[YouTubeScheduler] Upload error for {schedule_id}: {err_str}")
        _update_record(schedule_id, status="failed", progress=0, message="Upload failed", error=err_str)
        if rec.job_id:
            try:
                update_job(rec.job_id, current_task=f"YouTube Upload Failed: {err_str[:60]}")
            except Exception:
                pass
        raise e


def _scheduler_loop():
    """Background polling loop for scheduled uploads."""
    print("[YouTubeScheduler] Daemon started. Polling queue every 20 seconds...")
    while True:
        try:
            records = _load_records()
            now_utc = datetime.now(timezone.utc)

            for schedule_id, rec in list(records.items()):
                if rec.status == "scheduled":
                    should_run = False
                    if not rec.schedule_time:
                        # Immediate upload that hasn't executed yet
                        should_run = True
                    else:
                        try:
                            # Parse ISO string
                            sched_dt = datetime.fromisoformat(rec.schedule_time.replace("Z", "+00:00"))
                            if sched_dt <= now_utc:
                                should_run = True
                        except Exception as dt_err:
                            print(f"[YouTubeScheduler] Date parsing error for {schedule_id}: {dt_err}")

                    if should_run:
                        print(f"[YouTubeScheduler] Triggering scheduled upload {schedule_id} for '{rec.title}'")
                        t = threading.Thread(target=execute_upload, args=(schedule_id,), daemon=True)
                        t.start()

        except Exception as e:
            print(f"[YouTubeScheduler] Loop error: {e}")

        time.sleep(20)


def start_scheduler_daemon():
    """Initialize background daemon thread."""
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return
    _SCHEDULER_STARTED = True
    daemon_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="YouTubeScheduler")
    daemon_thread.start()
