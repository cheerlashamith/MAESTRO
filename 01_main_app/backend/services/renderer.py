"""
Auto-renderer bridge.

Starts the correct rendering engine for each mode and collects the produced MP4 clips.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from backend.core.config import project_root, get_config


def _project_root() -> Path:
    return project_root()


def _run_subprocess(cmd: List[str], cwd: Path, timeout: int = 3600) -> None:
    """Run a subprocess command and stream output to stdout."""
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )
    try:
        stdout, _ = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"Command failed with code {proc.returncode}:\n{stdout[-2000:]}")
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")


def render_manim_course(scenes_json: Path, progress_callback=None) -> List[Path]:
    """
    Copy the generated scenes_course.json into the Manim engine folder and render all scenes.
    Returns a list of rendered MP4 clip paths in scene order.
    """
    engine_dir = _project_root() / "engines" / "manim_course_mode"
    if not engine_dir.exists():
        raise RuntimeError(f"Manim engine not found at {engine_dir}")

    target_json = engine_dir / "scenes_course.json"
    shutil.copy2(str(scenes_json), str(target_json))

    if progress_callback:
        progress_callback("Rendering Manim course clips...")

    _run_subprocess([sys.executable, "render_all.py"], cwd=engine_dir, timeout=20)

    clips_dir = engine_dir / "generated" / "clips"
    if not clips_dir.exists():
        raise RuntimeError("Manim did not produce clips. Check render_all.py output.")

    clips = sorted(clips_dir.glob("*.mp4"), key=lambda p: p.name)
    return clips


def render_comfyui_story(scenes_json: Path, progress_callback=None) -> List[Path]:
    """
    Copy the generated scenes_story.json into the story engine folder and generate images/clips.
    Returns a list of rendered MP4 clip paths in scene order.
    """
    engine_dir = _project_root() / "engines" / "story_mode"
    if not engine_dir.exists():
        raise RuntimeError(f"Story engine not found at {engine_dir}")

    target_json = engine_dir / "scenes_story.json"
    shutil.copy2(str(scenes_json), str(target_json))

    if progress_callback:
        progress_callback("Generating ComfyUI story clips...")

    # Ensure workflow file exists
    workflow_path = engine_dir / "workflows" / "sd3.5_simple_example_api.json"
    if not workflow_path.exists():
        raise RuntimeError(
            f"ComfyUI workflow file missing: {workflow_path}. "
            "Export it from ComfyUI and place it there."
        )

    _run_subprocess(
        [sys.executable, "generate_story_materials.py", "--scenes", "scenes_story.json"],
        cwd=engine_dir,
        timeout=25,
    )

    clips_dir = engine_dir / "generated" / "clips"
    if not clips_dir.exists():
        raise RuntimeError("Story engine did not produce clips. Check ComfyUI connection.")

    clips = sorted(clips_dir.glob("*.mp4"), key=lambda p: p.name)
    return clips


def _pexels_search_videos(query: str, api_key: str, per_page: int = 10) -> List[str]:
    """Search Pexels for video URLs matching a query."""
    import requests
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        urls = []
        for video in data.get("videos", []):
            # Pick the highest quality MP4 file
            files = sorted(
                [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4"],
                key=lambda f: f.get("width", 0) * f.get("height", 0),
                reverse=True,
            )
            if files:
                urls.append(files[0]["link"])
        return urls
    except Exception as exc:
        raise RuntimeError(f"Pexels search failed: {exc}") from exc


def _download_video(url: str, out_path: Path) -> Path:
    """Download a video from a URL to a local path."""
    import requests
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return out_path


def fetch_pexels_clips(keywords: str, api_key: str, output_dir: Path, count: int = 6, progress_callback=None) -> List[Path]:
    """Download Pexels stock clips based on comma-separated keywords."""
    if not api_key:
        raise RuntimeError("Pexels API key is missing. Add it to MPT config.toml or AutoCourse config.json.")

    queries = [q.strip() for q in keywords.split(",") if q.strip()][:5]
    if not queries:
        queries = ["education"]

    clips_dir = output_dir / "pexels_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    urls: List[str] = []
    for q in queries:
        if progress_callback:
            progress_callback(f"Searching Pexels for: {q}")
        urls.extend(_pexels_search_videos(q, api_key, per_page=3))
        if len(urls) >= count:
            break

    if not urls:
        raise RuntimeError("No Pexels clips found. Check your API key and internet connection.")

    clips: List[Path] = []
    for i, url in enumerate(urls[:count], 1):
        if progress_callback:
            progress_callback(f"Downloading Pexels clip {i}/{len(urls[:count])}")
        out = clips_dir / f"pexels_{i:02d}.mp4"
        clips.append(_download_video(url, out))
        time.sleep(0.3)

    return clips


def detect_aspect_from_clips(clips: List[Path]) -> str:
    """Return '16:9' or '9:16' based on the first clip."""
    import cv2  # optional dependency
    if not clips:
        return "16:9"
    cap = cv2.VideoCapture(str(clips[0]))
    if not cap.isOpened():
        return "16:9"
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if h > w:
        return "9:16"
    return "16:9"
