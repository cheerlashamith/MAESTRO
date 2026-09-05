from __future__ import annotations
import json, os, uuid, threading, asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .schemas import JobRecord, JobStatus, GenerateRequest
from .config import outputs_root

_LOCK = threading.Lock()
_JOBS: Dict[str, JobRecord] = {}

# Subscribers are (event_loop, queue) pairs. The loop is captured at subscribe()
# time because update_job() is called from worker threads, and waking an asyncio
# queue from a foreign thread requires loop.call_soon_threadsafe().
_EVENTS_LOCK = threading.Lock()
_JOB_EVENTS: Dict[str, List[Tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}

# Statuses that only make sense while a worker thread is alive. If they survive a
# restart the worker is gone, so the job is orphaned rather than in-flight.
_IN_FLIGHT = {JobStatus.queued, JobStatus.planning, JobStatus.rendering, JobStatus.assembling}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_persisted_jobs() -> None:
    """Load previously persisted jobs from disk on startup.

    Two repairs happen here:
      * created_at is backfilled from the job.json mtime when absent, otherwise
        Pydantic's default_factory re-stamps it with boot time on every restart
        and the video history reorders itself.
      * jobs left in an in-flight status are marked failed, because their worker
        thread died with the previous process. Without this they inflate
        active_workers forever and can never be cleaned up from the UI.
    """
    try:
        root = outputs_root()
    except Exception:
        return

    try:
        job_dirs = list(root.iterdir())
    except Exception:
        return

    for job_dir in job_dirs:
        job_file = job_dir / "job.json"
        if not job_file.exists():
            continue
        try:
            data = json.loads(job_file.read_text(encoding="utf-8"))

            repaired = False
            if not data.get("created_at"):
                data["created_at"] = datetime.fromtimestamp(
                    job_file.stat().st_mtime, tz=timezone.utc
                ).isoformat()
                repaired = True

            data.setdefault("user_id", "shamith")
            data.setdefault("tenant_id", "default")

            rec = JobRecord(**data)

            if rec.status in _IN_FLIGHT:
                rec = rec.model_copy(update={
                    "status": JobStatus.failed,
                    "message": "Interrupted — the server restarted while this job was running.",
                    "current_task": "",
                    "current_model": "",
                })
                repaired = True

            _JOBS[rec.job_id] = rec
            if repaired:
                try:
                    save_job(rec)
                except Exception:
                    pass  # Read-only dir shouldn't stop the server from booting
        except Exception:
            pass  # Skip corrupted job files


def create_job(req: GenerateRequest, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> JobRecord:
    job_id = uuid.uuid4().hex[:12]
    out = outputs_root() / job_id
    out.mkdir(parents=True, exist_ok=True)
    uid = user_id or req.user_id or "shamith"
    tid = tenant_id or req.tenant_id or "default"
    rec = JobRecord(
        job_id=job_id,
        status=JobStatus.queued,
        request=req,
        output_dir=str(out),
        message="Queued",
        user_id=uid,
        tenant_id=tid
    )
    with _LOCK:
        _JOBS[job_id] = rec
    save_job(rec)
    return rec


def update_job(job_id: str, **kwargs) -> Optional[JobRecord]:
    """Apply a partial update to a job and notify SSE subscribers.

    Returns None if the job is unknown (e.g. deleted while its worker was still
    running) rather than raising, so a delete can't kill a live worker thread.
    """
    with _LOCK:
        existing = _JOBS.get(job_id)
        if existing is None:
            return None
        data = existing.model_dump()
        data.update(kwargs)
        rec = JobRecord(**data)
        _JOBS[job_id] = rec
    save_job(rec)
    _notify(job_id, rec)
    return rec


def _notify(job_id: str, rec: JobRecord) -> None:
    """Push a record to every subscriber of this job, thread-safely."""
    with _EVENTS_LOCK:
        subscribers = list(_JOB_EVENTS.get(job_id, ()))

    for loop, q in subscribers:
        try:
            if loop.is_closed():
                continue
            # call_soon_threadsafe also writes the loop's self-pipe, which is what
            # actually wakes a loop parked in select(). Plain put_nowait does not.
            loop.call_soon_threadsafe(q.put_nowait, rec)
        except RuntimeError:
            pass  # Loop shut down between the is_closed() check and the call


def get_job(job_id: str) -> Optional[JobRecord]:
    with _LOCK:
        return _JOBS.get(job_id)


def delete_job(job_id: str) -> bool:
    return delete_job_permanently(job_id)


def cancel_job(job_id: str, reason: str = "Stopped by user") -> bool:
    """Stop/cancel an in-flight or queued job and notify listeners."""
    with _LOCK:
        existing = _JOBS.get(job_id)
        if existing is None:
            return False
        if existing.status in (JobStatus.completed, JobStatus.failed, JobStatus.cancelled):
            return False
        data = existing.model_dump()
        data.update({
            "status": JobStatus.cancelled,
            "message": reason,
            "current_task": "Stopped",
            "current_model": ""
        })
        rec = JobRecord(**data)
        _JOBS[job_id] = rec
    save_job(rec)
    _notify(job_id, rec)
    # Release any waiting human approval event so thread doesn't hang
    resolve_approval(job_id, {"action": "reject"})
    return True


def pause_job(job_id: str) -> bool:
    """Pause an in-flight job by holding it in awaiting_approval status."""
    with _LOCK:
        existing = _JOBS.get(job_id)
        if existing is None or existing.status not in _IN_FLIGHT:
            return False
        data = existing.model_dump()
        data.update({
            "status": JobStatus.awaiting_approval,
            "message": "Paused by user",
            "current_task": "Paused"
        })
        rec = JobRecord(**data)
        _JOBS[job_id] = rec
    save_job(rec)
    _notify(job_id, rec)
    return True


def resume_job(job_id: str) -> bool:
    """Resume a paused or queued job."""
    with _LOCK:
        existing = _JOBS.get(job_id)
        if existing is None or existing.status != JobStatus.awaiting_approval:
            return False
        data = existing.model_dump()
        data.update({
            "status": JobStatus.rendering,
            "message": "Resumed pipeline execution",
            "current_task": "Resumed"
        })
        rec = JobRecord(**data)
        _JOBS[job_id] = rec
    save_job(rec)
    _notify(job_id, rec)
    resolve_approval(job_id, {"action": "approve"})
    return True


def delete_job_permanently(job_id: str) -> bool:
    """Permanently delete a job record from memory and remove its output directory."""
    with _LOCK:
        rec = _JOBS.pop(job_id, None)
    
    # Release any waiting approval event
    resolve_approval(job_id, {"action": "reject"})

    if rec and rec.output_dir:
        out_dir = Path(rec.output_dir)
        try:
            if out_dir.exists():
                import shutil
                shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            pass
    return rec is not None


def clear_all_jobs(user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> int:
    """Permanently stop and delete jobs from memory and disk.
    If user_id or tenant_id is provided, only deletes jobs belonging to that user/tenant.
    Otherwise, purges all jobs.
    """
    import shutil
    target_ids = []
    with _LOCK:
        if user_id or tenant_id:
            for jid, rec in list(_JOBS.items()):
                if user_id and getattr(rec, "user_id", "shamith") != user_id:
                    continue
                if tenant_id and getattr(rec, "tenant_id", "default") != tenant_id:
                    continue
                target_ids.append(jid)
                _JOBS.pop(jid, None)
        else:
            target_ids = list(_JOBS.keys())
            _JOBS.clear()

    # Unblock and clean up approval events for target jobs
    with _APPROVAL_LOCK:
        for jid in target_ids:
            event = _APPROVAL_EVENTS.pop(jid, None)
            if event:
                try:
                    event.set()
                except Exception:
                    pass
            _APPROVAL_DATA.pop(jid, None)

    # Purge job folders from disk
    try:
        root = outputs_root()
        if root.exists():
            for item in list(root.iterdir()):
                if item.is_dir():
                    job_file = item / "job.json"
                    if job_file.exists():
                        if user_id or tenant_id:
                            # Only delete folder if it matches target_ids or has matching metadata
                            if item.name in target_ids:
                                shutil.rmtree(item, ignore_errors=True)
                        else:
                            shutil.rmtree(item, ignore_errors=True)
    except Exception:
        pass

    return len(target_ids)



def list_jobs(user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> dict:
    """Return all jobs as a dict keyed by job_id, newest first.
    Filters by user_id and/or tenant_id when provided for strict multi-tenant isolation.
    """
    with _LOCK:
        records = list(_JOBS.values())
    if tenant_id:
        records = [r for r in records if getattr(r, "tenant_id", "default") == tenant_id]
    if user_id:
        records = [r for r in records if getattr(r, "user_id", "shamith") == user_id]
    records.sort(key=lambda r: r.created_at or "", reverse=True)
    return {rec.job_id: rec.model_dump() for rec in records}


def save_job(rec: JobRecord) -> None:
    """Persist a job record atomically so a crash mid-write can't corrupt it."""
    out_dir = Path(rec.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "job.json"
    tmp = out_dir / f"job.json.{os.getpid()}.tmp"
    tmp.write_text(rec.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, target)


def subscribe(job_id: str) -> asyncio.Queue:
    """Register an SSE subscriber. Must be called from the event loop thread."""
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    with _EVENTS_LOCK:
        _JOB_EVENTS.setdefault(job_id, []).append((loop, q))
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    with _EVENTS_LOCK:
        subscribers = _JOB_EVENTS.get(job_id)
        if not subscribers:
            return
        _JOB_EVENTS[job_id] = [(l, sq) for (l, sq) in subscribers if sq is not q]
        if not _JOB_EVENTS[job_id]:
            del _JOB_EVENTS[job_id]


# ---------------------------------------------------------------------------
# Human-in-the-Loop Synchronization
# ---------------------------------------------------------------------------

_APPROVAL_LOCK = threading.Lock()
_APPROVAL_EVENTS: Dict[str, threading.Event] = {}
_APPROVAL_DATA: Dict[str, Dict[str, Any]] = {}


def wait_for_approval(job_id: str, timeout: int = 7200) -> Optional[Dict[str, Any]]:
    """Block the worker thread until human approval or rejection is received."""
    event = threading.Event()
    with _APPROVAL_LOCK:
        _APPROVAL_EVENTS[job_id] = event
        _APPROVAL_DATA.pop(job_id, None)
    
    signaled = event.wait(timeout=timeout)
    with _APPROVAL_LOCK:
        _APPROVAL_EVENTS.pop(job_id, None)
        data = _APPROVAL_DATA.pop(job_id, None)
    return data if signaled else None


def resolve_approval(job_id: str, payload: Dict[str, Any]) -> bool:
    """Signal the blocked worker thread that human approval or revision was submitted."""
    with _APPROVAL_LOCK:
        event = _APPROVAL_EVENTS.get(job_id)
        if not event:
            return False
        _APPROVAL_DATA[job_id] = payload
        event.set()
        return True


# Load persisted jobs at import time
_load_persisted_jobs()

