from __future__ import annotations
import hmac
import uuid
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Body, File, UploadFile, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core.config import (
    project_root,
    get_config,
    save_config,
    outputs_root,
    redact_config,
    merge_preserving_secrets,
    api_token,
)
from backend.core.schemas import (
    GenerateRequest,
    JobStatus,
    ApprovalActionRequest,
    YouTubeOptimizeRequest,
    YouTubePublishRequest,
)
from backend.core.job_store import (
    get_job,
    list_jobs,
    subscribe,
    unsubscribe,
    cancel_job as core_cancel_job,
    pause_job as core_pause_job,
    resume_job as core_resume_job,
    delete_job_permanently,
    clear_all_jobs,
)
from backend.services.pipeline import submit_job, regenerate_job
from backend.services.analytics_agent import start_analytics_agent
from backend.services.youtube_scheduler import (
    start_scheduler_daemon,
    schedule_upload,
    list_scheduled,
    cancel_scheduled,
)
from backend.services.youtube_auth import (
    get_auth_url,
    handle_oauth_callback,
    get_channel_profile,
    disconnect_channel,
)
from backend.services.youtube_optimizer import optimize_metadata
from backend.services.youtube_upload import get_all_analytics, upload_video_to_youtube

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

TOKEN_COOKIE = "autocourse_token"


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler_daemon()
    start_analytics_agent()
    yield


app = FastAPI(title="MAESTRO API", version="1.0.0", lifespan=lifespan)
ROOT = project_root()
FRONTEND = ROOT / "frontend_v2" / "dist"


def _is_within(child: Path, parent: Path) -> bool:
    """True if child is parent itself or nested inside it.

    A plain startswith() comparison is not enough: "outputs_evil/x" starts with
    "outputs" but lives outside it. The separator makes the boundary explicit,
    and the lowercase compare keeps Windows' case-insensitive paths working.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        pass
    c = str(child).replace("\\", "/").rstrip("/").lower()
    p = str(parent).replace("\\", "/").rstrip("/").lower()
    return c == p or c.startswith(p + "/")


def require_api_token(request: Request) -> None:
    """Guard privileged endpoints when AUTOCOURSE_API_TOKEN is set.

    Unset (the default) disables the check entirely, which is correct for the
    intended 127.0.0.1 usage. Set it before exposing the server on a network.
    """
    expected = api_token()
    if not expected:
        return

    supplied = request.headers.get("X-API-Token", "")
    if not supplied:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
    if not supplied:
        supplied = request.cookies.get(TOKEN_COOKIE, "") or (request.query_params.get("token") or "")

    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Missing or invalid API token. Set the X-API-Token header.")

app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
assets_dir = FRONTEND / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


# ---------------------------------------------------------------------------
# Core & System Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    cfg = get_config()
    return {
        "ok": True,
        "project": cfg.get("project_name", "MAESTRO"),
        "full_name": cfg.get("project_full_name", "Multi-Agent Autonomous Engine for Scalable Transmedia Production & Orchestration"),
        "planner_model": cfg.get("providers", {}).get("planner_model", "qwen3:14b"),
        "coding_model": cfg.get("providers", {}).get("coding_model", "qwen2.5:7b"),
        "utility_model": cfg.get("providers", {}).get("utility_model", "gemma3:4b"),
        "ollama_url": cfg.get("providers", {}).get("ollama_url", "http://127.0.0.1:11434"),
    }


@app.get("/api/modes")
def modes():
    return {
        "modes": [
            {"id": "manual_course", "name": "Manual Course Mode", "visuals": "Manim Course / Local Clips", "batch": True},
            {"id": "story", "name": "Story Mode", "visuals": "ComfyUI Story", "batch": False},
            {"id": "youtube_extract", "name": "YouTube Extraction Mode", "visuals": "Auto selected", "batch": False},
            {"id": "autonomous", "name": "Autonomous Mode", "visuals": "Auto selected", "batch": True},
        ],
        "visual_styles": ["manim_course", "comfyui_story", "pexels", "hybrid"],
    }


# ---------------------------------------------------------------------------
# Job Management Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/jobs")
def create(req: GenerateRequest, request: Request):
    try:
        from backend.services.iam_service import IAMService
        current_u = IAMService.get_current_user()
        uid = req.user_id or (current_u.get("username") if current_u else "shamith")
        tid = req.tenant_id or "default"
        return submit_job(req, user_id=uid, tenant_id=tid)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/jobs")
def jobs(user_id: Optional[str] = Query(None), tenant_id: Optional[str] = Query(None)):
    """List jobs with optional multi-tenant and user scoping."""
    return list_jobs(user_id=user_id, tenant_id=tenant_id)


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    return rec


@app.delete("/api/jobs")
def api_clear_all_jobs(user_id: Optional[str] = Query(None), tenant_id: Optional[str] = Query(None)):
    """Stop running tasks and permanently purge jobs from UI and disk. Scoped by user_id/tenant_id if provided."""
    count = clear_all_jobs(user_id=user_id, tenant_id=tenant_id)
    scope_str = f" for user '{user_id}'" if user_id else ""
    return {"ok": True, "message": f"Successfully cleared and purged {count} tasks{scope_str}.", "cleared_count": count}


@app.delete("/api/jobs/{job_id}")
def api_delete_job(job_id: str):
    """Permanently delete a single job record and its output files."""
    success = delete_job_permanently(job_id)
    if not success:
        raise HTTPException(404, "Job not found")
    return {"ok": True, "message": f"Job {job_id} deleted."}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    success = core_cancel_job(job_id, reason="Stopped by Admin Console")
    if not success:
        return {"ok": False, "message": "Job is already completed, failed, or cancelled."}
    return {"ok": True, "message": "Job successfully stopped and cancelled."}


@app.post("/api/jobs/{job_id}/pause")
def api_pause_job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    success = core_pause_job(job_id)
    if not success:
        return {"ok": False, "message": "Job cannot be paused in its current state."}
    return {"ok": True, "message": "Job paused."}


@app.post("/api/jobs/{job_id}/resume")
def api_resume_job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    success = core_resume_job(job_id)
    if not success:
        return {"ok": False, "message": "Job cannot be resumed in its current state."}
    return {"ok": True, "message": "Job resumed."}


@app.post("/api/jobs/{job_id}/approve")
def api_approve_job(job_id: str, payload: ApprovalActionRequest):
    """Human-in-the-Loop review endpoint: approve, revise, or reject."""
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")

    from backend.core.job_store import resolve_approval, update_job
    
    if payload.action == "reject":
        update_job(job_id, status=JobStatus.cancelled, message="Rejected by user in review gate.", current_task="Cancelled", current_model="")
        resolve_approval(job_id, {"action": "reject"})
        return {"ok": True, "message": "Job rejected and cancelled."}

    success = resolve_approval(job_id, payload.model_dump())
    if not success:
        return {"ok": False, "message": "Job is not waiting for approval or has already resumed."}

    return {"ok": True, "message": f"Action '{payload.action}' successfully registered."}


class FeedbackRequest(BaseModel):
    feedback: str


@app.post("/api/jobs/{job_id}/regenerate")
def api_regenerate_job(job_id: str, req: FeedbackRequest):
    try:
        return regenerate_job(job_id, req.feedback)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/jobs/{job_id}/upload")
def api_upload_job(job_id: str, payload: Optional[YouTubePublishRequest] = None):
    try:
        if payload:
            res = upload_video_to_youtube(
                job_id=job_id,
                title=payload.title,
                description=payload.description,
                tags=payload.tags,
                privacy_status=payload.privacy_status,
                schedule_time=payload.schedule_time,
                schedule_mode=payload.schedule_mode,
                thumbnail_path=payload.thumbnail_path
            )
        else:
            res = upload_video_to_youtube(job_id=job_id)
        return res
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
        
    TERMINAL = (JobStatus.completed, JobStatus.failed, JobStatus.cancelled)

    async def event_generator():
        # Subscribe before the initial snapshot so an update landing in between
        # is queued rather than dropped.
        q = subscribe(job_id)
        try:
            current = get_job(job_id)
            if current is None:
                return
            yield f"data: {current.model_dump_json()}\n\n"
            if current.status in TERMINAL:
                return
            while True:
                job = await q.get()
                yield f"data: {job.model_dump_json()}\n\n"
                # Cancelled is terminal too; without it the stream hung forever.
                if job.status in TERMINAL:
                    break
        finally:
            unsubscribe(job_id, q)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# YouTube OAuth, Publishing & Scheduling Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/youtube/status")
def api_youtube_status():
    """Get channel connection status and profile details."""
    return get_channel_profile()


@app.get("/api/youtube/auth/url")
def api_youtube_auth_url(request: Request, redirect_uri: Optional[str] = None):
    """Generate Google OAuth 2.0 authorization URL."""
    try:
        if not redirect_uri:
            # Default to standard loopback callback route
            base_url = str(request.base_url).rstrip("/")
            redirect_uri = f"{base_url}/api/youtube/oauth2callback"
        
        auth_url = get_auth_url(redirect_uri)
        return {"auth_url": auth_url, "redirect_uri": redirect_uri}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/api/youtube/oauth2callback")
def api_youtube_oauth2callback(request: Request, code: str = Query(...), state: Optional[str] = None):
    """OAuth callback endpoint handling Google redirect."""
    try:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/youtube/oauth2callback"
        handle_oauth_callback(code, redirect_uri)
        return RedirectResponse(url="/user/publisher?connected=true")
    except Exception as e:
        print(f"[OAuth Callback Error] {e}")
        return RedirectResponse(url=f"/user/publisher?error={str(e)}")


@app.post("/api/youtube/auth/disconnect")
def api_youtube_disconnect():
    """Disconnect YouTube channel by removing cached credentials."""
    return disconnect_channel()


@app.post("/api/youtube/optimize")
def api_youtube_optimize(req: YouTubeOptimizeRequest):
    """AI metadata & SEO generation (titles, description, tags, category, thumbnail)."""
    try:
        return optimize_metadata(
            topic=req.topic,
            script=req.script,
            keywords=req.keywords,
            visual_style=req.visual_style,
            video_path=req.video_path
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/youtube/publish")
def api_youtube_publish(req: YouTubePublishRequest):
    """Immediate publish or schedule upload for a video."""
    try:
        video_path = req.video_path
        if not video_path and req.job_id:
            job_rec = get_job(req.job_id)
            if job_rec:
                # An empty "videos" list must not IndexError — a batch job that
                # produced nothing reaches here with videos == [].
                videos = job_rec.files.get("videos")
                video_path = job_rec.files.get("final_video") or (
                    videos[0] if isinstance(videos, list) and videos else None
                )

        if not video_path:
            raise HTTPException(400, "video_path or valid job_id is required.")

        is_immediate = (req.privacy_status != "scheduled") and (req.schedule_time is None)

        record = schedule_upload(
            video_path=video_path,
            title=req.title,
            description=req.description,
            tags=req.tags,
            category_id=req.category_id,
            privacy_status=req.privacy_status,
            schedule_time=req.schedule_time,
            schedule_mode=req.schedule_mode,
            thumbnail_path=req.thumbnail_path,
            job_id=req.job_id,
            immediate=is_immediate
        )
        return record
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/youtube/queue")
def api_youtube_queue():
    """List all scheduled and published items in queue."""
    return {"queue": list_scheduled()}


@app.delete("/api/youtube/queue/{schedule_id}")
def api_youtube_cancel_queue(schedule_id: str):
    """Cancel a scheduled upload."""
    success = cancel_scheduled(schedule_id)
    if not success:
        raise HTTPException(400, "Could not cancel scheduled item (it may already be uploading or completed).")
    return {"success": True, "message": "Scheduled upload cancelled."}


@app.post("/api/youtube/upload-thumbnail")
async def api_youtube_upload_thumbnail(file: UploadFile = File(...)):
    """Upload a custom thumbnail image for a video."""
    try:
        thumb_dir = outputs_root() / "thumbnails"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or "thumb.jpg").suffix or ".jpg"
        save_name = f"{uuid.uuid4().hex[:10]}{ext}"
        target_path = thumb_dir / save_name

        content = await file.read()
        target_path.write_bytes(content)

        return {"success": True, "thumbnail_path": str(target_path.resolve()), "filename": save_name}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/youtube/analytics")
@app.get("/api/admin/youtube-analytics")
def api_youtube_analytics():
    """Get channel metrics and statistics for all uploaded videos."""
    try:
        return get_all_analytics()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/youtube/trigger-autonomous")
def api_trigger_autonomous(force: bool = Query(default=True)):
    """Trigger an on-demand closed-loop autonomous channel cycle immediately."""
    from backend.services.analytics_agent import trigger_autonomous_cycle
    try:
        result = trigger_autonomous_cycle(force=force)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------------------------
# Admin & Configuration Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/plugins", dependencies=[Depends(require_api_token)])
def get_plugins():
    from backend.services.brain_manager import BrainManager
    return BrainManager.get_plugin_health()


@app.get("/api/config", dependencies=[Depends(require_api_token)])
def get_configuration():
    """Return the configuration with every API key/secret masked.

    The browser never receives real credentials. POST accepts the mask back
    unchanged, which means "keep the stored value".
    """
    return redact_config(get_config())


@app.post("/api/config", dependencies=[Depends(require_api_token)])
def update_configuration(new_cfg: dict = Body(...)):
    if not isinstance(new_cfg, dict):
        raise HTTPException(400, "Configuration must be a JSON object")
    # Merge over the stored config so masked secrets aren't written back as "********"
    # and so keys the client didn't send are preserved rather than dropped.
    save_config(merge_preserving_secrets(new_cfg, get_config()))
    return {"status": "success", "message": "Configuration updated"}


@app.get("/api/admin/metrics", dependencies=[Depends(require_api_token)])
def get_metrics():
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    jobs_dict = list_jobs()
    jobs_arr = list(jobs_dict.values())
    active_statuses = {JobStatus.planning, JobStatus.rendering, JobStatus.assembling}
    active_jobs = [j for j in jobs_arr if j.get("status") in [s.value for s in active_statuses]]
    queued_jobs = [j for j in jobs_arr if j.get("status") == JobStatus.queued.value]
    
    return {
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024**3), 1),
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "active_workers": len(active_jobs),
        "queued_jobs": len(queued_jobs)
    }


@app.get("/api/admin/cache", dependencies=[Depends(require_api_token)])
def get_cache():
    from backend.services.cache_manager import CacheManager
    return CacheManager.get_cache_stats()


@app.get("/api/download")
def download(path: str = Query(..., description="Absolute path to a generated file"), filename: Optional[str] = Query(None)):
    """Download a generated file by absolute path. Only files inside the outputs directory are allowed."""
    try:
        file_path = Path(path).resolve()
    except Exception:
        raise HTTPException(400, "Invalid path")

    outputs_dir = outputs_root().resolve()

    if not _is_within(file_path, outputs_dir):
        raise HTTPException(403, "Access denied: file must be inside the outputs directory.")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"File not found: {file_path}")

    save_name = filename or file_path.name
    if file_path.suffix.lower() == ".mp4" and not save_name.lower().endswith(".mp4"):
        save_name = f"{save_name}.mp4"

    return FileResponse(
        file_path,
        filename=save_name,
        media_type="video/mp4" if file_path.suffix.lower() == ".mp4" else "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{save_name}"',
            "Content-Type": "video/mp4" if file_path.suffix.lower() == ".mp4" else "application/octet-stream",
        }
    )


@app.get("/api/jobs/{job_id}/download")
@app.get("/api/jobs/{job_id}/download/{filename}")
def download_job_video(job_id: str, filename: Optional[str] = None):
    """Download the completed MP4 video for a job with a clean, named filename."""
    import json
    job_dir = (outputs_root() / job_id).resolve()
    video_path = job_dir / "final_video.mp4"

    if not video_path.exists():
        job_json = job_dir / "job.json"
        if job_json.exists():
            try:
                data = json.loads(job_json.read_text(encoding="utf-8"))
                v = data.get("files", {}).get("final_video") or (data.get("files", {}).get("videos") or [None])[0]
                if v and Path(v).exists():
                    video_path = Path(v)
            except Exception:
                pass

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(404, f"Final video not found for job {job_id}")

    if not filename:
        topic = "video"
        job_json = job_dir / "job.json"
        if job_json.exists():
            try:
                data = json.loads(job_json.read_text(encoding="utf-8"))
                topic = data.get("request", {}).get("topic") or "video"
            except Exception:
                pass
        clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in topic).strip("_")
        filename = f"{clean_name}.mp4"
    elif not filename.lower().endswith(".mp4"):
        filename = f"{filename}.mp4"

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "video/mp4",
        }
    )


@app.get("/api/jobs/{job_id}/thumbnail")
def get_job_thumbnail(job_id: str):
    """Serve a high-quality thumbnail image for the specified job.
    Prioritizes existing thumbnail/slide images, or dynamically extracts a 1080p frame from final_video.mp4."""
    import json
    job_dir = (outputs_root() / job_id).resolve()
    if not job_dir.exists() or not job_dir.is_dir():
        raise HTTPException(404, "Job directory not found")

    # 1. Check for existing thumbnail/slide files
    candidates = ["thumbnail.jpg", "final_video_thumb.jpg", "slide_00.png", "slide_00.jpg", "thumb.jpg"]
    for name in candidates:
        candidate = job_dir / name
        if candidate.exists() and candidate.is_file():
            media_type = "image/png" if candidate.suffix.lower() == ".png" else "image/jpeg"
            return FileResponse(
                candidate,
                media_type=media_type,
                headers={"Content-Disposition": "inline", "Cache-Control": "public, max-age=86400"}
            )

    # 2. Check if video exists and extract frame dynamically using OpenCV
    video_path = job_dir / "final_video.mp4"
    if not video_path.exists():
        job_json = job_dir / "job.json"
        if job_json.exists():
            try:
                data = json.loads(job_json.read_text(encoding="utf-8"))
                v = data.get("files", {}).get("final_video") or (data.get("files", {}).get("videos") or [None])[0]
                if v and Path(v).exists():
                    video_path = Path(v)
            except Exception:
                pass

    if video_path.exists():
        try:
            from backend.services.youtube_optimizer import extract_video_thumbnail
            thumb_path = job_dir / "thumbnail.jpg"
            extracted = extract_video_thumbnail(str(video_path), str(thumb_path))
            if extracted and Path(extracted).exists():
                return FileResponse(
                    Path(extracted),
                    media_type="image/jpeg",
                    headers={"Content-Disposition": "inline", "Cache-Control": "public, max-age=86400"}
                )
        except Exception as e:
            print(f"[Thumbnail] Dynamic extraction error for job {job_id}: {e}")

    # 3. Fallback to any PNG or JPG in the job directory
    for img in sorted(job_dir.glob("*.png")):
        return FileResponse(img, media_type="image/png", headers={"Content-Disposition": "inline"})
    for img in sorted(job_dir.glob("*.jpg")):
        return FileResponse(img, media_type="image/jpeg", headers={"Content-Disposition": "inline"})

    raise HTTPException(404, "No thumbnail available for this job")


@app.get("/api/jobs/{job_id}/video")
def stream_job_video(job_id: str):
    """Stream the generated MP4 video for in-browser theater playback."""
    import json
    job_dir = (outputs_root() / job_id).resolve()
    video_path = job_dir / "final_video.mp4"
    if not video_path.exists():
        job_json = job_dir / "job.json"
        if job_json.exists():
            try:
                data = json.loads(job_json.read_text(encoding="utf-8"))
                v = data.get("files", {}).get("final_video") or (data.get("files", {}).get("videos") or [None])[0]
                if v and Path(v).exists():
                    video_path = Path(v)
            except Exception:
                pass

    if not video_path.exists():
        raise HTTPException(404, f"Final video not found for job {job_id}")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={"Content-Disposition": "inline", "Accept-Ranges": "bytes"}
    )



# ---------------------------------------------------------------------------
# IAM (Identity & Access Management) Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/iam/roles")
def get_iam_roles():
    from backend.services.iam_service import IAMService
    return {"roles": IAMService.get_roles()}


@app.post("/api/iam/roles")
def create_iam_role(payload: dict = Body(...)):
    from backend.services.iam_service import IAMService
    try:
        return IAMService.create_role(
            name=payload["name"],
            slug=payload["slug"],
            description=payload.get("description", ""),
            permissions=payload.get("permissions", []),
            scopes=payload.get("scopes", {})
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@app.put("/api/iam/roles/{role_slug}")
def update_iam_role_permissions(role_slug: str, payload: dict = Body(...)):
    from backend.services.iam_service import IAMService
    try:
        return IAMService.update_role_permissions(
            role_slug=role_slug,
            permissions=payload.get("permissions", []),
            scopes=payload.get("scopes")
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/iam/permissions")
def get_iam_permissions():
    from backend.services.iam_service import IAMService
    return {"permissions": IAMService.get_permissions()}


@app.get("/api/iam/matrix")
def get_iam_matrix():
    from backend.services.iam_service import IAMService
    return IAMService.get_permission_matrix()


@app.post("/api/iam/matrix")
def save_iam_matrix(payload: dict = Body(...)):
    from backend.services.iam_service import IAMService
    try:
        role_slug = payload.get("role_slug")
        permissions = payload.get("permissions", [])
        scopes = payload.get("scopes", {})
        return IAMService.update_role_permissions(role_slug, permissions, scopes)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/iam/users")
def get_iam_users():
    from backend.services.iam_service import IAMService
    return {"users": IAMService.get_users()}


@app.get("/api/iam/current-user")
def get_current_user():
    from backend.services.iam_service import IAMService
    return IAMService.get_current_user()


@app.post("/api/iam/switch-user")
def switch_user(payload: dict = Body(...)):
    from backend.services.iam_service import IAMService
    try:
        return IAMService.switch_user(payload.get("username", "shamith"))
    except Exception as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# AI Studio Visual Workflow Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/studio/workflows")
def get_studio_workflows():
    from backend.services.studio_service import StudioService
    return {"workflows": StudioService.get_workflows()}


@app.get("/api/studio/workflows/{workflow_id}")
def get_studio_workflow(workflow_id: str):
    from backend.services.studio_service import StudioService
    wf = StudioService.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@app.post("/api/studio/workflows")
def save_studio_workflow(payload: dict = Body(...)):
    from backend.services.studio_service import StudioService
    try:
        return StudioService.save_workflow(payload)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/studio/workflows/{workflow_id}")
def delete_studio_workflow(workflow_id: str):
    from backend.services.studio_service import StudioService
    ok = StudioService.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(404, "Workflow not found or cannot be deleted")
    return {"success": True}


@app.get("/api/studio/node-types")
def get_studio_node_types():
    from backend.services.studio_service import StudioService
    return {"node_types": StudioService.get_node_types()}


@app.post("/api/studio/workflows/{workflow_id}/run")
def run_studio_workflow(workflow_id: str, overrides: Optional[dict] = Body(default=None)):
    from backend.services.studio_service import StudioService
    try:
        return StudioService.run_workflow(workflow_id, overrides)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------------------------------------------------------
# Provider & Engine Connectivity & Testing Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/providers/health")
def get_providers_health():
    from backend.services.provider_service import ProviderService
    return ProviderService.get_all_provider_health()


@app.post("/api/providers/test")
def test_provider(payload: dict = Body(...)):
    from backend.services.provider_service import ProviderService
    provider = payload.get("provider", "").lower()
    url = payload.get("url")
    key = payload.get("api_key")
    if provider == "ollama":
        return ProviderService.test_ollama(url)
    elif provider == "comfyui":
        return ProviderService.test_comfyui(url)
    elif provider in ("moneyprinter", "mpt"):
        return ProviderService.test_moneyprinter(url)
    elif provider == "openai":
        return ProviderService.test_openai(key)
    elif provider == "pexels":
        return ProviderService.test_pexels(key)
    else:
        raise HTTPException(400, f"Unknown provider '{provider}'")


@app.post("/api/providers/connect")
def connect_provider(payload: dict = Body(...)):
    from backend.services.provider_service import ProviderService
    provider = payload.get("provider", "").lower()
    url = payload.get("url")
    root_path = payload.get("root_path")
    return ProviderService.start_or_connect(provider, url=url, root_path=root_path)




# ---------------------------------------------------------------------------
# Frontend Catch-All Route
# ---------------------------------------------------------------------------

@app.get('/{full_path:path}')
def catch_all(full_path: str, token: Optional[str] = None):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='API route not found')

    def _respond(response):
        # Visiting the app once with ?token=... stores it so the UI's own API
        # calls pass require_api_token. No-op when no token is configured.
        expected = api_token()
        if expected and token and hmac.compare_digest(token, expected):
            response.set_cookie(TOKEN_COOKIE, expected, httponly=True, samesite="strict")
        return response

    # Resolve and confine to FRONTEND: "../../config.json" would otherwise escape.
    frontend_dir = FRONTEND.resolve()
    if full_path:
        try:
            file_path = (frontend_dir / full_path).resolve()
        except Exception:
            file_path = None
        if file_path and _is_within(file_path, frontend_dir) and file_path.is_file():
            return _respond(FileResponse(file_path))

    index_file = frontend_dir / 'index.html'
    if index_file.exists():
        return _respond(FileResponse(index_file))
    return JSONResponse(status_code=404, content={'error': 'Frontend build not found. Run npm run build in frontend_v2'})
