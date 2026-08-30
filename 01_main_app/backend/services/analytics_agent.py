import time
import threading
import json
from pathlib import Path

from backend.core.config import project_root, get_config
from backend.services.youtube_upload import get_all_analytics
from backend.services.brain_manager import BrainManager
from backend.core.schemas import TaskType, GenerateRequest, Mode, VisualStyle
from backend.services.pipeline import submit_job

AGENT_INTERVAL_SECONDS = 3600 # Every hour (can be changed to 24 hours in prod)
LOW_VIEW_THRESHOLD = 50

def analyze_and_restategize(analytics_data):
    """
    Take the low-performing videos and ask BrainManager for a new strategy/topic.
    """
    if not analytics_data:
        return
        
    low_performers = [a for a in analytics_data if a["views"] < LOW_VIEW_THRESHOLD]
    if not low_performers:
        print("[AnalyticsAgent] All videos are performing well. No restategize needed.")
        return
        
    # Build a prompt for the brain to restategize
    failed_topics = [a["topic"] for a in low_performers]
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
    raw = BrainManager.ask(prompt, TaskType.PLANNING)
    
    # Simple extraction
    try:
        import re
        # try to extract JSON
        m = re.search(r"(\{.*\})", raw, re.DOTALL)
        if m:
            strategy = json.loads(m.group(1))
        else:
            strategy = json.loads(raw)
            
        print(f"[AnalyticsAgent] New Strategy: {strategy.get('reasoning')}")
        
        # Queue the new job
        req = GenerateRequest(
            mode=Mode.autonomous,
            topic=strategy.get("new_topic", "Top 5 AI Tools"),
            notes=strategy.get("keywords", ""),
            visual_style=VisualStyle.pexels
        )
        
        print(f"[AnalyticsAgent] Submitting new autonomous job for topic: {req.topic}")
        submit_job(req)
        
    except Exception as e:
        print(f"[AnalyticsAgent] Failed to restategize: {e}")

def agent_loop():
    print("[AnalyticsAgent] Starting YouTube Analytics Agent loop...")
    while True:
        try:
            print("[AnalyticsAgent] Fetching YouTube analytics...")
            res = get_all_analytics()
            analytics = res.get("analytics", [])
            print(f"[AnalyticsAgent] Found {len(analytics)} uploaded videos.")
            
            if analytics:
                analyze_and_restategize(analytics)
                
        except Exception as e:
            print(f"[AnalyticsAgent] Error in agent loop: {e}")
            
        time.sleep(AGENT_INTERVAL_SECONDS)

def start_analytics_agent():
    """Start the background thread."""
    t = threading.Thread(target=agent_loop, daemon=True, name="AnalyticsAgent")
    t.start()
