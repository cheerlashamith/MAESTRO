"""
24/7 Autonomous Channel Director Agent for MAESTRO.

Provides closed-loop reinforcement strategy:
1. Harvests real-time YouTube video telemetry (views, likes, comments, velocity).
2. Winners Strategy (Double-Down): When a video succeeds (> threshold views or high like/view ratio),
   the director formulates an intelligent sequel or deep dive in the SAME mode to capture audience momentum.
3. Underperformers Strategy (Diagnose, Live Update & Pivot):
   - Automatically refreshes live YouTube metadata (titles, tags) on the existing video via YouTube Data API v3.
   - Pivots the next video into an alternate mode (cycles between manual_course, story, youtube_extract, autonomous).
4. Full Autopilot: Submits generation jobs with auto_publish=True and require_approval=False
   so production, rendering, optimization, and upload happen 100% hands-free without human intervention.
"""
from __future__ import annotations
import json
import re
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.core.config import get_config, feature_enabled
from backend.services.youtube_upload import get_all_analytics
from backend.services.youtube_auth import get_authenticated_service, is_authenticated
from backend.services.youtube_optimizer import optimize_metadata
from backend.services.brain_manager import BrainManager
from backend.core.schemas import TaskType, GenerateRequest, Mode, VisualStyle
from backend.services.pipeline import submit_job

_DEFAULTS = {
    "interval_seconds": 3600,       # Check every hour
    "low_view_threshold": 50,       # Below 50 views after min_age is low-performing
    "high_view_threshold": 200,     # Above 200 views or >4% like ratio is a winner
    "min_video_age_hours": 48,      # Evaluate after 48 hours
    "max_jobs_per_day": 3,          # Up to 3 autonomous uploads daily
    "publish_privacy": "private",   # Set to "public" for 100% unattended live publishing
}

_submitted_at: List[datetime] = []
_agent_thread: Optional[threading.Thread] = None


def _settings() -> Dict[str, Any]:
    cfg = get_config().get("analytics_agent", {})
    out = dict(_DEFAULTS)
    for key, default in _DEFAULTS.items():
        value = cfg.get(key, default)
        try:
            if isinstance(default, int):
                out[key] = max(0, int(value))
            elif isinstance(default, str):
                out[key] = str(value)
        except (TypeError, ValueError):
            out[key] = default
    out["interval_seconds"] = max(60, out["interval_seconds"])
    return out


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _budget_remaining(max_per_day: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    _submitted_at[:] = [t for t in _submitted_at if t > cutoff]
    return max(0, max_per_day - len(_submitted_at))


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    for pattern in (r"\{.*?\}", r"\{.*\}"):
        match = re.search(pattern, raw, re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _classify_performance(analytics: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    min_age = timedelta(hours=settings["min_video_age_hours"])
    low_thresh = settings["low_view_threshold"]
    high_thresh = settings["high_view_threshold"]

    winners = []
    underperformers = []

    for item in analytics:
        if not isinstance(item, dict):
            continue
        views = int(item.get("views") or 0)
        likes = int(item.get("likes") or 0)
        like_ratio = likes / max(1, views)

        # High engagement / high views winner
        if views >= high_thresh or (views >= 30 and like_ratio >= 0.05):
            winners.append(item)
            continue

        uploaded = _parse_iso(item.get("uploaded_at") or item.get("published_at"))
        if uploaded and (now - uploaded >= min_age) and views < low_thresh:
            underperformers.append(item)

    return {"winners": winners, "underperformers": underperformers}


def _try_refresh_live_metadata(video_id: str, current_topic: str) -> bool:
    """Rescue an underperforming video by updating its title and tags on YouTube."""
    if not is_authenticated() or not video_id:
        return False
    try:
        opt = optimize_metadata(topic=current_topic)
        if not opt or not opt.titles:
            return False

        youtube = get_authenticated_service()
        # Fetch current snippet
        vid_req = youtube.videos().list(part="snippet", id=video_id)
        vid_res = vid_req.execute()
        items = vid_res.get("items", [])
        if not items:
            return False

        snippet = items[0]["snippet"]
        new_title = opt.titles[1] if len(opt.titles) > 1 else opt.titles[0]
        snippet["title"] = new_title[:100]
        snippet["tags"] = opt.tags[:20]

        youtube.videos().update(
            part="snippet",
            body={"id": video_id, "snippet": snippet}
        ).execute()

        print(f"[AnalyticsAgent] Rescued video {video_id} with updated title: '{new_title}'")
        return True
    except Exception as e:
        print(f"[AnalyticsAgent] Could not refresh live video {video_id} metadata: {e}")
        return False


def trigger_autonomous_cycle(force: bool = False) -> Dict[str, Any]:
    """
    Executes a single autonomous channel director cycle.
    Evaluates live YouTube analytics, makes strategic content decisions,
    and queues an autonomous video generation with auto-publishing.
    """
    settings = _settings()
    remaining_budget = _budget_remaining(settings["max_jobs_per_day"])

    if remaining_budget <= 0 and not force:
        msg = f"Daily autonomous job cap reached ({settings['max_jobs_per_day']}/day). Skipping cycle."
        print(f"[AnalyticsAgent] {msg}")
        return {"success": False, "reason": msg}

    # Fetch live telemetry
    res = get_all_analytics()
    analytics = res.get("analytics", []) if isinstance(res, dict) else []
    classification = _classify_performance(analytics, settings)
    winners = classification["winners"]
    underperformers = classification["underperformers"]

    print(f"[AnalyticsAgent] Telemetry Harvest: {len(analytics)} videos, {len(winners)} winners, {len(underperformers)} underperformers.")

    strategy_decision = "cold_start"
    selected_mode = Mode.manual_course
    selected_style = VisualStyle.manim_course
    new_topic = ""
    keywords = ""

    # Strategy 1: Double down on winners
    if winners:
        strategy_decision = "double_down"
        top_winner = max(winners, key=lambda w: int(w.get("views") or 0))
        win_topic = top_winner.get("topic") or top_winner.get("title", "Computer Science Architecture")

        prompt = f"""You are an expert YouTube Content Director.
Our recent video on '{win_topic}' was a massive breakout winner with high views and engagement.
Formulate ONE high-yield sequel, advanced continuation, or related deep-dive topic to capture audience momentum.
Choose the best mode out of: "manual_course", "story", "youtube_extract", "autonomous".

Return ONLY a JSON object:
{{
    "new_topic": "Specific Video Title / Topic",
    "mode": "manual_course",
    "keywords": "kw1, kw2, kw3, kw4, kw5",
    "reasoning": "Why this sequel will capture viewers"
}}
"""
        try:
            raw = BrainManager.ask(prompt, TaskType.PLANNING)
            parsed = _extract_json(raw)
            if parsed and parsed.get("new_topic"):
                new_topic = str(parsed["new_topic"]).strip()
                keywords = str(parsed.get("keywords", ""))
                mode_str = str(parsed.get("mode", "manual_course")).lower()
                selected_mode = Mode(mode_str) if mode_str in [m.value for m in Mode] else Mode.manual_course
        except Exception as e:
            print(f"[AnalyticsAgent] Error generating sequel topic: {e}")

    # Strategy 2: Diagnose & Pivot from underperformers
    elif underperformers:
        strategy_decision = "pivot_mode"
        # Refresh live metadata for top underperformer
        top_flop = underperformers[0]
        if top_flop.get("youtube_video_id"):
            _try_refresh_live_metadata(top_flop["youtube_video_id"], top_flop.get("topic", ""))

        failed_titles = [str(u.get("topic") or u.get("title", "")) for u in underperformers[:3]]
        prompt = f"""You are an expert YouTube Channel Strategist.
The following topics recently underperformed (low click-through and views):
{', '.join(failed_titles)}

We need to pivot to a fresh, viral, high-velocity topic in programming, AI, or software design.
Select the best production mode out of: "story" (cinematic narrative shorts), "manual_course" (algorithmic tutorial), or "autonomous" (tech breakthrough).

Return ONLY a JSON object:
{{
    "new_topic": "New Breakthrough Topic",
    "mode": "story",
    "keywords": "keyword1, keyword2, keyword3, keyword4",
    "reasoning": "Why this topic and format will reverse the decline"
}}
"""
        try:
            raw = BrainManager.ask(prompt, TaskType.PLANNING)
            parsed = _extract_json(raw)
            if parsed and parsed.get("new_topic"):
                new_topic = str(parsed["new_topic"]).strip()
                keywords = str(parsed.get("keywords", ""))
                mode_str = str(parsed.get("mode", "story")).lower()
                selected_mode = Mode(mode_str) if mode_str in [m.value for m in Mode] else Mode.story
        except Exception as e:
            print(f"[AnalyticsAgent] Error generating pivot topic: {e}")

    # Strategy 3: Cold Start / Initial Channel Seeding
    if not new_topic:
        strategy_decision = "seeding"
        candidate_topics = [
            ("Mastering Microservices & Distributed Event Buses", Mode.manual_course),
            ("The Day the World's Financial Algorithms Stopped", Mode.story),
            ("Clean Architecture & Domain Driven Design in Practice", Mode.manual_course),
            ("Inside the Quantum Computing Revolution", Mode.autonomous),
        ]
        import random
        choice = random.choice(candidate_topics)
        new_topic, selected_mode = choice
        keywords = "software architecture, system design, high performance, algorithms"

    # Style mapping
    if selected_mode == Mode.story:
        selected_style = VisualStyle.comfyui_story
        aspect = "9:16"
        voice = "en-US-JennyNeural"
    elif selected_mode in (Mode.autonomous, Mode.youtube_extract):
        selected_style = VisualStyle.pexels
        aspect = "16:9"
        voice = "en-US-AndrewMultilingualNeural"
    else:
        selected_style = VisualStyle.manim_course
        aspect = "16:9"
        voice = "en-US-AndrewMultilingualNeural"

    print(f"[AnalyticsAgent] Executing Strategy '{strategy_decision}': Topic='{new_topic}' | Mode={selected_mode.value}")

    req = GenerateRequest(
        mode=selected_mode,
        topic=new_topic,
        notes=keywords,
        visual_style=selected_style,
        aspect=aspect,
        voice=voice,
        require_approval=False,       # Zero-touch 24/7 autonomous
        auto_publish=True,           # Upload automatically via scheduler daemon
        publish_privacy=settings.get("publish_privacy", "private"),
        publish_category_id="27",
        user_id="autonomous_director",
        tenant_id="default"
    )

    job_rec = submit_job(req, user_id="autonomous_director", tenant_id="default")
    _submitted_at.append(datetime.now(timezone.utc))

    return {
        "success": True,
        "job_id": job_rec.job_id,
        "strategy": strategy_decision,
        "topic": new_topic,
        "mode": selected_mode.value,
        "auto_publish": True,
        "budget_remaining": _budget_remaining(settings["max_jobs_per_day"])
    }


def agent_loop() -> None:
    settings = _settings()
    print(
        f"[AnalyticsAgent] 24/7 Channel Director Active. "
        f"interval={settings['interval_seconds']}s | "
        f"cap={settings['max_jobs_per_day']}/day | "
        f"privacy={settings['publish_privacy']}"
    )
    while True:
        try:
            trigger_autonomous_cycle()
        except Exception as e:
            print(f"[AnalyticsAgent] Error in autonomous loop: {e}")

        settings = _settings()
        time.sleep(settings["interval_seconds"])


def start_analytics_agent() -> bool:
    """Start the autonomous director thread if enabled in config."""
    global _agent_thread
    if not feature_enabled("enable_analytics_agent", False):
        print("[AnalyticsAgent] Standby mode. Enable in config.json features.enable_analytics_agent.")
        return False

    if _agent_thread and _agent_thread.is_alive():
        return True

    _agent_thread = threading.Thread(target=agent_loop, daemon=True, name="AnalyticsDirectorAgent")
    _agent_thread.start()
    return True
