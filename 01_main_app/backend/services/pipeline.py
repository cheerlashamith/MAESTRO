"""
AutoCourse pipeline.

Orchestrates the full end-to-end video generation flow:
  Plan (Ollama + syllabus) -> Render clips (Manim / ComfyUI / Pexels) -> Assemble (MoneyPrinterTurbo API) -> Download final MP4
"""
from __future__ import annotations
import json
import re
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.core.schemas import GenerateRequest, JobStatus, Mode
from backend.core.job_store import create_job, update_job, get_job, wait_for_approval
from backend.core.config import get_config

class JobCancelledException(Exception):
    pass

def _check_cancelled(job_id: str):
    job = get_job(job_id)
    if job and job.status == JobStatus.cancelled:
        raise JobCancelledException("Cancelled by admin")
from backend.services.planner import (
    build_plan,
    build_batch_plans,
    build_youtube_plan,
    next_topic_after,
    regenerate_plan,
)
from backend.services.renderer import render_manim_course, render_comfyui_story, fetch_pexels_clips
from backend.services.mpt_bridge import generate_video as mpt_generate_video


def _safe_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("full_voiceover") or "\n\n".join(value.get("paragraphs", [])) or json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    return str(value)


def _get_rendering_prefs(req: GenerateRequest) -> Dict[str, Any]:
    """Resolve rendering preferences from request or config."""
    cfg = get_config()
    rend = cfg.get("rendering", {})
    mode = req.mode.value if hasattr(req.mode, "value") else str(req.mode)

    if mode in ("story",):
        default_aspect = rend.get("story_aspect", "9:16")
        default_voice = rend.get("story_voice", "en-US-JennyNeural")
    else:
        default_aspect = rend.get("course_aspect", "16:9")
        default_voice = rend.get("course_voice", "en-US-AndrewMultilingualNeural")

    # For Manim course mode, disable MPT subtitles — Manim already renders 
    # text/bullet points on screen. Overlaid subtitles cause the text-merge issue.
    is_manim_course = mode not in ("story",) and req.visual_style.value in ("manim_course", "manim") if hasattr(req, 'visual_style') else False
    
    if req.subtitle_enabled is not None:
        subtitle = req.subtitle_enabled
    elif is_manim_course:
        subtitle = False  # Auto-disable for Manim to prevent text overlap
    else:
        subtitle = rend.get("subtitle_enabled", True)

    return {
        "aspect": req.aspect or default_aspect,
        "voice": req.voice or default_voice,
        "subtitle_enabled": subtitle,
        "bgm_volume": req.bgm_volume if req.bgm_volume is not None else rend.get("bgm_volume", 0.05),
    }


def _write_plan_files(job_dir: Path, plan: Dict[str, Any]) -> Dict[str, str]:
    """Write a single plan to disk."""
    is_story = plan.get("render_mode") == "story" or plan.get("visual_style") == "comfyui_story"
    is_pexels = plan.get("render_mode") == "pexels" or plan.get("video_source") == "pexels"

    if is_pexels:
        plan_name = "scenes_pexels.json"
    elif is_story:
        plan_name = "scenes_story.json"
    else:
        plan_name = "scenes_course.json"

    plan_path = job_dir / plan_name
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    script_path = job_dir / "moneyprinter_video_script.txt"
    keywords_path = job_dir / "moneyprinter_keywords.txt"
    script_path.write_text(_safe_string(plan.get("moneyprinter_script", "")), encoding="utf-8")
    keywords_path.write_text(_safe_string(plan.get("keywords", "")), encoding="utf-8")

    return {
        "plan": str(plan_path),
        "script": str(script_path),
        "keywords": str(keywords_path),
    }


def _add_next_topic_hook(plan: Dict[str, Any], topic_name: str) -> Dict[str, Any]:
    """Append a 'next topic' teaser to the end of the voiceover script."""
    nxt = next_topic_after(topic_name)
    if nxt:
        script = _safe_string(plan.get("moneyprinter_script", "")).strip()
        if not script.endswith("."):
            script += "."
        hook = f"\n\nIn the next video, we will continue with {nxt}. Stay tuned!"
        plan["moneyprinter_script"] = script + hook
    return plan


def _assemble_with_mpt(
    job_dir: Path,
    plan: Dict[str, Any],
    clips: List[Path],
    prefs: Dict[str, Any],
    progress_callback=None,
) -> List[Path]:
    """Call MoneyPrinterTurbo API to assemble the final video with resilient fallback."""
    subject = plan.get("subject", "AutoCourse Video")
    script = _safe_string(plan.get("moneyprinter_script", ""))
    keywords = _safe_string(plan.get("keywords", ""))

    is_pexels = plan.get("render_mode") == "pexels" or plan.get("video_source") == "pexels"
    video_source = "pexels" if is_pexels else "local"

    if not script:
        script = f"Overview of {subject}."

    # 1. Attempt MoneyPrinterTurbo if available
    try:
        from backend.services.mpt_bridge import _is_mpt_api_running
        if _is_mpt_api_running(timeout=1):
            if progress_callback:
                progress_callback("Assembling final video with MoneyPrinterTurbo API...")
            mpt_videos = mpt_generate_video(
                subject=subject,
                script=script,
                keywords=keywords,
                clips=clips,
                output_dir=job_dir,
                aspect=prefs["aspect"],
                voice=prefs["voice"],
                clip_duration=8 if prefs["aspect"] == "9:16" else 10,
                subtitle_enabled=prefs["subtitle_enabled"],
                bgm_volume=prefs["bgm_volume"],
                video_source=video_source,
                progress_callback=progress_callback,
            )
            if mpt_videos and all(Path(v).exists() for v in mpt_videos):
                return mpt_videos
    except Exception as mpt_err:
        print(f"[Pipeline] MPT assembly bypassed ({mpt_err}). Switching to Direct Resilient Video Synthesizer.")

    # 2. Resilient Direct Video Synthesizer (Edge-TTS + Pillow + FFmpeg)
    if progress_callback:
        progress_callback("Synthesizing broadcast video with Direct Neural Engine...")
    from backend.services.direct_synthesizer import synthesize_direct_video
    return synthesize_direct_video(
        job_dir=job_dir,
        plan=plan,
        clips=clips,
        prefs=prefs,
        progress_callback=progress_callback
    )


def _process_single_topic(
    job_id: str,
    topic_name: str,
    plan: Dict[str, Any],
    job_dir: Path,
    prefs: Dict[str, Any],
    pexels_api_key: Optional[str],
    progress_callback=None,
) -> Dict[str, Any]:
    """Render clips and assemble one topic. Returns file dict."""
    files = _write_plan_files(job_dir, plan)

    render_mode = plan.get("render_mode", "")
    visual_style = plan.get("visual_style", "")
    is_story = render_mode == "story" or visual_style == "comfyui_story"
    is_pexels = render_mode == "pexels" or plan.get("video_source") == "pexels" or visual_style == "pexels"

    clips: List[Path] = []
    try:
        if is_story:
            if progress_callback:
                progress_callback(f"Rendering story clips for {topic_name}...")
            clips = render_comfyui_story(Path(files["plan"]), progress_callback)
        elif is_pexels:
            if progress_callback:
                progress_callback(f"Preparing stock visuals for {topic_name}...")
        else:
            if progress_callback:
                progress_callback(f"Rendering Manim course clips for {topic_name}...")
            clips = render_manim_course(Path(files["plan"]), progress_callback)
    except Exception as render_err:
        print(f"[Pipeline] Renderer bypassed or offline: {render_err}. Direct Synthesizer will generate visual scenes.")
        clips = []

    files["clips"] = [str(c) for c in clips]

    final_videos = _assemble_with_mpt(job_dir, plan, clips, prefs, progress_callback)
    files["videos"] = [str(v) for v in final_videos]
    # Set final_video as the primary single output for the download button
    if final_videos:
        files["final_video"] = str(final_videos[0])
    return files


def _handle_auto_publish(job_id: str, req: GenerateRequest, files: Dict[str, Any], plan: Optional[Dict[str, Any]] = None):
    """Trigger automated YouTube publishing/scheduling if enabled on the request."""
    if not getattr(req, "auto_publish", False):
        return
    try:
        from backend.services.youtube_auth import is_authenticated
        if not is_authenticated():
            print(f"[Pipeline] Auto-publish enabled for job {job_id}, but YouTube is not connected. Skipping.")
            return

        video_path = files.get("final_video") or (files.get("videos", [None])[0] if isinstance(files.get("videos"), list) else None)
        if not video_path or not Path(video_path).exists():
            return

        from backend.services.youtube_optimizer import optimize_metadata, extract_video_thumbnail
        from backend.services.youtube_scheduler import schedule_upload

        thumb_path = req.publish_thumbnail_path or extract_video_thumbnail(str(video_path))
        
        title = req.publish_title
        description = req.publish_description
        tags = req.publish_tags
        category_id = req.publish_category_id or "27"

        if not title or not description:
            script_text = plan.get("moneyprinter_script", "") if plan else ""
            keywords_text = plan.get("keywords", "") if plan else (req.notes or "")
            opt = optimize_metadata(
                topic=req.topic or (plan.get("subject") if plan else "AutoCourse Video"),
                script=script_text,
                keywords=keywords_text,
                visual_style=req.visual_style.value if hasattr(req.visual_style, "value") else str(req.visual_style),
                video_path=str(video_path)
            )
            title = title or (opt.titles[0] if opt.titles else req.topic)
            description = description or opt.description
            tags = tags or opt.tags
            category_id = category_id or opt.category_id

        privacy = req.publish_privacy or "private"
        sched_time = req.publish_schedule_time
        sched_mode = req.publish_schedule_mode or "local"
        immediate = (privacy != "scheduled") and (sched_time is None)

        print(f"[Pipeline] Auto-publishing video for job {job_id} to YouTube (immediate={immediate}, title='{title}')...")
        schedule_upload(
            video_path=str(video_path),
            title=title or req.topic or "AutoCourse Video",
            description=description or "Generated by AutoCourse Studio",
            tags=tags or ["AutoCourse", "Education"],
            category_id=category_id,
            privacy_status=privacy,
            schedule_time=sched_time,
            schedule_mode=sched_mode,
            thumbnail_path=thumb_path,
            job_id=job_id,
            immediate=immediate
        )
    except Exception as e:
        print(f"[Pipeline] Auto-publish error for job {job_id}: {e}")


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 ]+", " ", text).strip().replace(" ", "_") or "topic"


def run_job(job_id: str, req: GenerateRequest, output_dir: str):
    """Background thread entry point for a single or batch job."""
    out = Path(output_dir)
    cfg = get_config()
    pexels_api_key = cfg.get("providers", {}).get("pexels_api_key", "")
    prefs = _get_rendering_prefs(req)

    def emit(msg: str, progress: int = 50, task: str = "Processing", model: str = ""):
        _check_cancelled(job_id)
        update_job(job_id, message=msg, progress_percentage=progress, current_task=task, current_model=model)

    try:
        mode = req.mode.value if hasattr(req.mode, "value") else str(req.mode)
        topic = (req.topic or "").strip().lower()

        # -----------------------------------------------------------
        # BATCH COURSE MODE: empty topic, 'all', or starts with 'batch:' / 'unit:'
        # -----------------------------------------------------------
        is_batch = mode == "manual_course" and (
            not topic or 
            topic in ("all", "everything", "full syllabus") or 
            topic.startswith("batch:") or 
            topic.startswith("unit:")
        )
        
        if is_batch:
            update_job(job_id, status=JobStatus.planning, message="Batch mode: initializing syllabus planning")
            
            def plan_progress(msg: str):
                _check_cancelled(job_id)
                # Keep status as planning, just update the message
                update_job(job_id, message=msg, progress_percentage=20, current_task="Planning Batch Scripts", current_model=get_config().get("providers", {}).get("planner_model", "qwen2.5:7b"))
                
            results = build_batch_plans(req, progress_callback=plan_progress)
            update_job(job_id, status=JobStatus.rendering, message=f"Batch mode: rendering and assembling {len(results)} topics")

            all_files = []
            for idx, (topic_name, plan) in enumerate(results, 1):
                _check_cancelled(job_id)
                plan = _add_next_topic_hook(plan, topic_name)
                sub_dir = out / f"topic_{idx:02d}_{_slug(topic_name)}"
                sub_dir.mkdir(parents=True, exist_ok=True)
                emit(f"[{idx}/{len(results)}] Processing {topic_name}")
                files = _process_single_topic(
                    job_id,
                    topic_name,
                    plan,
                    sub_dir,
                    prefs,
                    pexels_api_key,
                    progress_callback=lambda m: emit(f"[{idx}/{len(results)}] {m}", progress=40 + int(60 * (idx/len(results))), task="Rendering & Assembling", model="MoneyPrinterTurbo"),
                )
                all_files.append({"topic": topic_name, "dir": str(sub_dir), **files})

            update_job(
                job_id,
                status=JobStatus.completed,
                message=f"Batch complete: {len(results)} videos generated successfully.",
                files={"batch_topics": all_files},
            )
            return

        # -----------------------------------------------------------
        # SINGLE JOB: one topic / URL / story
        # -----------------------------------------------------------
        update_job(job_id, status=JobStatus.planning, message=f"Planning topic: {req.topic or req.youtube_url or 'auto-selected'}", progress_percentage=10, current_task="Planning & Scripting", current_model=get_config().get("providers", {}).get("planner_model", "qwen2.5:7b"))
        _check_cancelled(job_id)

        if mode == "youtube_extract":
            if not req.youtube_url:
                raise ValueError("YouTube URL is required for YouTube extraction mode.")
            plan = build_youtube_plan(req.youtube_url, req.notes, preferred_model=getattr(req, "model_override", None))
        else:
            plan = build_plan(req)

        _check_cancelled(job_id)
        plan = _add_next_topic_hook(plan, plan.get("subject", req.topic or ""))

        # -----------------------------------------------------------
        # HUMAN-IN-THE-LOOP (HITL) APPROVAL GATE
        # -----------------------------------------------------------
        require_approval = getattr(req, "require_approval", True)
        if require_approval:
            plan_files = _write_plan_files(out, plan)
            update_job(
                job_id,
                status=JobStatus.awaiting_approval,
                message="Script & Scenes generated! Awaiting human review & approval...",
                progress_percentage=30,
                current_task="Human-in-the-Loop Review Gate",
                current_model=get_config().get("providers", {}).get("planner_model", "qwen2.5:7b"),
                files={
                    **plan_files,
                    "script_preview": plan.get("moneyprinter_script", ""),
                    "scenes_preview": plan.get("scenes", []),
                    "keywords_preview": plan.get("keywords", ""),
                    "subject_preview": plan.get("subject", req.topic or "AutoCourse"),
                }
            )

            # Block worker thread until human action (approve / revise / reject)
            approval = wait_for_approval(job_id, timeout=7200)
            _check_cancelled(job_id)

            if not approval:
                raise RuntimeError("Human review session timed out or was cancelled.")

            action = approval.get("action", "approve")
            if action == "reject":
                update_job(job_id, status=JobStatus.cancelled, message="Job cancelled by reviewer.", current_task="Cancelled", current_model="")
                return
            elif action == "revise":
                update_job(job_id, status=JobStatus.planning, message="Revising plan based on your review feedback...", progress_percentage=20)
                req.feedback = approval.get("feedback", "Improve narrative clarity.")
                req.previous_plan = plan
                plan = regenerate_plan(req)
                plan = _add_next_topic_hook(plan, plan.get("subject", req.topic or ""))
            elif action == "approve":
                override = approval.get("script_override")
                if override and override.strip():
                    plan["moneyprinter_script"] = override.strip()
                    (out / "moneyprinter_video_script.txt").write_text(plan["moneyprinter_script"], encoding="utf-8")

            update_job(job_id, message="Human approval received! Rendering video clips...", progress_percentage=35)
        
        update_job(job_id, status=JobStatus.rendering, message=f"Rendering clips...", progress_percentage=50, current_task="Rendering Scenes", current_model="Local Engine")
        
        files = _process_single_topic(
            job_id,
            plan.get("subject", req.topic or "AutoCourse"),
            plan,
            out,
            prefs,
            pexels_api_key,
            progress_callback=lambda m: emit(m, progress=75, task="Assembling Video", model="MoneyPrinterTurbo"),
        )

        update_job(
            job_id,
            status=JobStatus.completed,
            message="Video generated successfully. Download it below.",
            files=files,
            progress_percentage=100,
            current_task="Done",
            current_model=""
        )

        # Trigger auto-publish if enabled
        _handle_auto_publish(job_id, req, files, plan)

    except JobCancelledException as e:
        update_job(job_id, status=JobStatus.cancelled, message=str(e), current_task="Cancelled", current_model="")
    except Exception as e:
        update_job(job_id, status=JobStatus.failed, message=str(e))


def submit_job(req: GenerateRequest, user_id: Optional[str] = None, tenant_id: Optional[str] = None):
    rec = create_job(req, user_id=user_id, tenant_id=tenant_id)
    t = threading.Thread(target=run_job, args=(rec.job_id, req, rec.output_dir), daemon=True)
    t.start()
    return rec


def run_regeneration_job(job_id: str, req: GenerateRequest, output_dir: str):
    """Background thread entry point for regeneration."""
    out = Path(output_dir)
    cfg = get_config()
    pexels_api_key = cfg.get("providers", {}).get("pexels_api_key", "")
    prefs = _get_rendering_prefs(req)

    def emit(msg: str, progress: int = 50, task: str = "Processing", model: str = ""):
        _check_cancelled(job_id)
        update_job(job_id, message=msg, progress_percentage=progress, current_task=task, current_model=model)

    try:
        update_job(job_id, status=JobStatus.planning, message=f"Regenerating plan based on feedback...", progress_percentage=10, current_task="Regenerating", current_model=get_config().get("providers", {}).get("planner_model", "qwen2.5:7b"))
        _check_cancelled(job_id)

        plan = regenerate_plan(req)
        plan = _add_next_topic_hook(plan, plan.get("subject", req.topic or ""))
        
        update_job(job_id, status=JobStatus.rendering, message=f"Rendering new clips...", progress_percentage=50, current_task="Rendering Scenes", current_model="Local Engine")
        
        files = _process_single_topic(
            job_id,
            plan.get("subject", req.topic or "AutoCourse"),
            plan,
            out,
            prefs,
            pexels_api_key,
            progress_callback=lambda m: emit(m, progress=75, task="Assembling Video", model="MoneyPrinterTurbo"),
        )

        update_job(
            job_id,
            status=JobStatus.completed,
            message="Regenerated video successfully.",
            files=files,
            progress_percentage=100,
            current_task="Done",
            current_model=""
        )

    except JobCancelledException as e:
        update_job(job_id, status=JobStatus.cancelled, message=str(e), current_task="Cancelled", current_model="")
    except Exception as e:
        update_job(job_id, status=JobStatus.failed, message=str(e))

def regenerate_job(job_id: str, feedback: str):
    rec = get_job(job_id)
    if not rec:
        raise ValueError("Job not found")
    
    # We need to find the previous plan file.
    plan_path = None
    for file_key in ["plan", "scenes_course.json", "scenes_story.json", "scenes_pexels.json"]:
        if file_key in rec.files:
            plan_path = Path(rec.files[file_key])
            break
    
    if not plan_path and Path(rec.output_dir).exists():
        # Try to find it in output_dir
        for file in Path(rec.output_dir).glob("scenes_*.json"):
            plan_path = file
            break
            
    if not plan_path or not plan_path.exists():
        raise ValueError("Could not find the previous plan JSON file for this job.")

    with open(plan_path, 'r', encoding='utf-8') as f:
        previous_plan = json.load(f)

    rec.request.feedback = feedback
    rec.request.previous_plan = previous_plan
    
    # Reset job state
    update_job(job_id, status=JobStatus.queued, message="Queued for regeneration", progress_percentage=0)
    
    t = threading.Thread(target=run_regeneration_job, args=(job_id, rec.request, rec.output_dir), daemon=True)
    t.start()
    return rec

