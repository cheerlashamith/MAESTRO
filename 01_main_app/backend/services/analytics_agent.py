"""Optional background agent that reacts to poor YouTube performance.

Disabled by default. Enable with features.enable_analytics_agent in config.json.

It is deliberately conservative: a freshly uploaded video always has few views,
so judging one too early makes the agent generate a new video every cycle, whose
own low view count then triggers the next. Two guards prevent that runaway — a
minimum video age before a video can be called a low performer, and a hard cap
on how many jobs may be submitted per day.
"""
import json
import re
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from backend.core.config import get_config, feature_enabled
from backend.services.youtube_upload import get_all_analytics
from backend.services.brain_manager import BrainManager
from backend.core.schemas import TaskType, GenerateRequest, Mode, VisualStyle
from backend.services.pipeline import submit_job

_DEFAULTS = {
    "interval_seconds": 3600,
    "low_view_threshold": 50,
    "min_video_age_hours": 72,
    "max_jobs_per_day": 2,
}

# Rolling record of agent-submitted job timestamps, used for the daily cap.
_submitted_at: List[datetime] = []


def _settings() -> Dict[str, Any]:
    cfg = get_config().get("analytics_agent", {})
    out = dict(_DEFAULTS)
    for key, default in _DEFAULTS.items():
        value = cfg.get(key, default)
        try:
            out[key] = max(0, int(value))
        except (TypeError, ValueError):
            out[key] = default
    out["interval_seconds"] = max(60, out["interval_seconds"])
    return out


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _budget_remaining(max_per_day: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    _submitted_at[:] = [t for t in _submitted_at if t > cutoff]
    return max(0, max_per_day - len(_submitted_at))


def _low_performers(analytics: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Videos old enough to be judged that are still below the view threshold."""
    threshold = settings["low_view_threshold"]
    min_age = timedelta(hours=settings["min_video_age_hours"])
    now = datetime.now(timezone.utc)
    out = []

    for item in analytics:
        if not isinstance(item, dict):
            continue
        try:
            views = int(item.get("views") or 0)
        except (TypeError, ValueError):
            continue
        if views >= threshold:
            continue

        uploaded = _parse_iso(item.get("uploaded_at") or item.get("published_at"))
        if uploaded is None:
            # No timestamp means we can't tell a stale flop from a fresh upload.
            # Skipping is the safe choice; guessing restarts the runaway loop.
            continue
        if now - uploaded < min_age:
            continue
        out.append(item)

    return out


def _extract_json(raw: str) -> Dict[str, Any] | None:
    """Pull the first JSON object out of an LLM response.

    Non-greedy from the first "{" so trailing prose can't swallow the object,
    with a greedy retry for nested structures.
    """
    for pattern in (r"\{.*?\}", r"\{.*\}"):
        match = re.search(pattern, raw, re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def analyze_and_restrategize(analytics_data) -> bool:
    """Ask the brain for a better topic and queue one job. Returns True if queued."""
    if not analytics_data:
        return False

    settings = _settings()
    low_performers = _low_performers(analytics_data, settings)
    if not low_performers:
        print("[AnalyticsAgent] No videos old enough to be judged low-performing.")
        return False

    if _budget_remaining(settings["max_jobs_per_day"]) <= 0:
        print(
            f"[AnalyticsAgent] Daily job cap reached "
            f"({settings['max_jobs_per_day']}/day). Skipping this cycle."
        )
        return False

    failed_topics = [str(a.get("topic", "")) for a in low_performers if a.get("topic")]
    if not failed_topics:
        return False

    prompt = f"""You are an expert YouTube strategist. The following topics performed poorly (low views):
{', '.join(failed_topics)}

Please suggest ONE new, highly engaging trending topic in technology or programming that is guaranteed to get high views.
Also suggest 5 SEO keywords for it.

Return ONLY a JSON object:
{{
    "new_topic": "Topic Name",
    "keywords": "keyword1, keyword2, ...",
    "reasoning": "Why this will work better"
}}
"""
    try:
        raw = BrainManager.ask(prompt, TaskType.PLANNING)
        strategy = _extract_json(raw)
        if not strategy:
            print("[AnalyticsAgent] Model did not return a usable JSON object. Skipping.")
            return False

        new_topic = str(strategy.get("new_topic") or "").strip()
        if not new_topic:
            print("[AnalyticsAgent] Model returned no topic. Skipping.")
            return False

        print(f"[AnalyticsAgent] New Strategy: {strategy.get('reasoning')}")

        req = GenerateRequest(
            mode=Mode.autonomous,
            topic=new_topic,
            notes=str(strategy.get("keywords") or ""),
            visual_style=VisualStyle.pexels,
        )

        print(f"[AnalyticsAgent] Submitting new autonomous job for topic: {req.topic}")
        submit_job(req)
        _submitted_at.append(datetime.now(timezone.utc))
        return True

    except Exception as e:
        print(f"[AnalyticsAgent] Failed to restrategize: {e}")
        return False


def agent_loop() -> None:
    settings = _settings()
    print(
        f"[AnalyticsAgent] Started. interval={settings['interval_seconds']}s "
        f"threshold={settings['low_view_threshold']} views "
        f"min_age={settings['min_video_age_hours']}h "
        f"cap={settings['max_jobs_per_day']}/day"
    )
    while True:
        settings = _settings()
        try:
            res = get_all_analytics()
            analytics = res.get("analytics", []) if isinstance(res, dict) else []
            print(f"[AnalyticsAgent] Found {len(analytics)} uploaded videos.")
            if analytics:
                analyze_and_restrategize(analytics)
        except Exception as e:
            print(f"[AnalyticsAgent] Error in agent loop: {e}")

        time.sleep(settings["interval_seconds"])


def start_analytics_agent() -> bool:
    """Start the agent thread only if explicitly enabled in config."""
    if not feature_enabled("enable_analytics_agent", False):
        print("[AnalyticsAgent] Disabled (set features.enable_analytics_agent to true to enable).")
        return False
    threading.Thread(target=agent_loop, daemon=True, name="AnalyticsAgent").start()
    return True
