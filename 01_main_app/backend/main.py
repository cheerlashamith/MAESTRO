from __future__ import annotations
import os
import uuid
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Body, File, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core.config import project_root, get_config, save_config, outputs_root
from backend.core.schemas import (
    GenerateRequest,
    JobStatus,
    YouTubeOptimizeRequest,
    YouTubePublishRequest,
    YouTubeScheduleRequest
)
from backend.core.job_store import get_job, list_jobs, subscribe, unsubscribe
from backend.services.pipeline import submit_job, regenerate_job
from backend.services.analytics_agent import start_analytics_agent
from backend.services.youtube_scheduler import (
    start_scheduler_daemon,
    schedule_upload,
    list_scheduled,
    cancel_scheduled,
    get_scheduled
)
from backend.services.youtube_auth import (
    get_auth_url,
    handle_oauth_callback,
    get_channel_profile,
    disconnect_channel,
    is_authenticated
)
from backend.services.youtube_optimizer import optimize_metadata, extract_video_thumbnail
from backend.services.youtube_upload import get_all_analytics, upload_video_to_youtube

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

app = FastAPI(title="AutoCourse Studio API", version="0.3.0")
ROOT = project_root()
FRONTEND = ROOT / "frontend_v2" / "dist"


@app.on_event("startup")
def startup_event():
    start_scheduler_daemon()
    start_analytics_agent()


# If the dist folder doesn't exist yet, fallback to original frontend to prevent startup errors
if not FRONTEND.exists():
    FRONTEND = ROOT / "frontend"

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
        "project": cfg.get("project_name", "AutoCourse Studio"),
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
def create(req: GenerateRequest):
    try:
        return submit_job(req)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/jobs")
def jobs():
    return list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    return rec


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(404, "Job not found")
    if rec.status in [JobStatus.completed, JobStatus.failed, JobStatus.cancelled]:
        return {"message": "Job already finished or cancelled"}
    
    from backend.core.job_store import update_job
    update_job(job_id, status=JobStatus.cancelled, message="Cancelled by Admin", current_task="Cancelled", current_model="")
    return {"message": "Job cancelled"}


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
        
    async def event_generator():
        q = subscribe(job_id)
        try:
            yield f"data: {get_job(job_id).model_dump_json()}\n\n"
            while True:
                job = await q.get()
                yield f"data: {job.model_dump_json()}\n\n"
                if job.status in [JobStatus.completed, JobStatus.failed]:
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
                video_path = job_rec.files.get("final_video") or (
                    job_rec.files.get("videos", [None])[0] if isinstance(job_rec.files.get("videos"), list) else None
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


# ---------------------------------------------------------------------------
# Admin & Configuration Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/admin/plugins")
def get_plugins():
    from backend.services.brain_manager import BrainManager
    return BrainManager.get_plugin_health()


@app.get("/api/config")
def get_configuration():
    return get_config()


@app.post("/api/config")
def update_configuration(new_cfg: dict = Body(...)):
    save_config(new_cfg)
    return {"status": "success", "message": "Configuration updated"}


@app.get("/api/admin/metrics")
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


@app.get("/api/admin/cache")
def get_cache():
    from backend.services.cache_manager import CacheManager
    return CacheManager.get_cache_stats()


@app.get("/api/download")
def download(path: str = Query(..., description="Absolute path to a generated file")):
    """Download a generated file by absolute path. Only files inside the outputs directory are allowed."""
    try:
        file_path = Path(path).resolve()
    except Exception:
        raise HTTPException(400, "Invalid path")

    outputs_dir = (ROOT / "outputs").resolve()
    
    file_str = str(file_path).replace("\\", "/").lower()
    outputs_str = str(outputs_dir).replace("\\", "/").lower()
    
    if not file_str.startswith(outputs_str):
        raise HTTPException(403, f"Access denied: file must be inside the outputs directory. Got: {file_path}")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"File not found: {file_path}")

    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type="video/mp4" if file_path.suffix == ".mp4" else None,
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'}
    )


# ---------------------------------------------------------------------------
# Frontend Catch-All Route
# ---------------------------------------------------------------------------

@app.get('/{full_path:path}')
def catch_all(full_path: str):
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='API route not found')
        
    file_path = FRONTEND / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
        
    index_file = FRONTEND / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={'error': 'Frontend build not found. Run npm run build in frontend_v2'})
