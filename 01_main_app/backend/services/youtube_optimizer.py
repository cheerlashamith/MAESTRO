"""
YouTube SEO and Metadata Optimizer.

Uses BrainManager (AI LLM) to generate:
- 3 Click-worthy, high-CTR viral titles
- Comprehensive SEO description with chapters, summary, hashtags & CTA
- 15-20 High ranking search tags
- Category recommendation
- Video thumbnail extraction via OpenCV
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.schemas import TaskType, YouTubeOptimizeResponse
from backend.services.brain_manager import BrainManager


def extract_video_thumbnail(video_path: str, output_thumbnail_path: Optional[str] = None) -> Optional[str]:
    """
    Extract a high-quality frame from the video at ~25% duration to serve as a thumbnail.
    """
    if not video_path:
        return None

    v_path = Path(video_path)
    if not v_path.exists() or not v_path.is_file():
        return None

    if not output_thumbnail_path:
        output_thumbnail_path = str(v_path.parent / f"{v_path.stem}_thumb.jpg")

    try:
        import cv2

        cap = cv2.VideoCapture(str(v_path))
        if not cap.isOpened():
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return None

        # Capture frame at ~25% timestamp
        target_frame = max(1, int(total_frames * 0.25))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        success, frame = cap.read()

        if not success:
            # Fallback to first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, frame = cap.read()

        cap.release()

        if success and frame is not None:
            Path(output_thumbnail_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_thumbnail_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            return str(Path(output_thumbnail_path).resolve())

    except Exception as e:
        print(f"[YouTubeOptimizer] Thumbnail extraction error: {e}")

    return None


def _fallback_metadata(topic: str, keywords: str) -> Dict[str, Any]:
    cleaned_topic = topic.strip() or "Comprehensive Guide & Tutorial"
    tags_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    if "AutoCourse" not in tags_list:
        tags_list.append("AutoCourse")
    if "Education" not in tags_list:
        tags_list.append("Education")
    if "Tutorial" not in tags_list:
        tags_list.append("Tutorial")

    return {
        "titles": [
            f"Master {cleaned_topic} in Minutes! (Complete Guide)",
            f"{cleaned_topic} Explained Simply - Everything You Need to Know",
            f"The Ultimate {cleaned_topic} Tutorial (Beginner to Pro)"
        ],
        "description": f"""🚀 Welcome to this comprehensive tutorial on {cleaned_topic}!

In this video, we break down core concepts, practical examples, and essential takeaways to help you master {cleaned_topic} quickly and effectively.

📌 What You'll Learn:
• Core foundations and key principles of {cleaned_topic}
• Step-by-step breakdown with visual explanations
• Practical tips and best practices for real-world application

⏱️ Timestamps:
00:00 - Introduction & Overview
00:30 - Core Concepts Explained
01:45 - Deep Dive & Visual Breakdown
03:00 - Summary & Next Steps

🔔 Don't forget to LIKE, SUBSCRIBE, and hit the NOTIFICATION BELL to never miss an update!
💬 Drop your questions and feedback in the comments below!

#{''.join(c for c in cleaned_topic.title() if c.isalnum())} #Education #Tutorial #TechSkills #Learning
""",
        "tags": tags_list[:20],
        "category_id": "27"
    }


def optimize_metadata(
    topic: str,
    script: Optional[str] = "",
    keywords: Optional[str] = "",
    visual_style: Optional[str] = "manim_course",
    video_path: Optional[str] = None
) -> YouTubeOptimizeResponse:
    """
    Generate optimized YouTube title, description, tags, and category.
    """
    topic_clean = (topic or "").strip()
    script_snippet = (script or "")[:1500].strip()
    keywords_clean = (keywords or "").strip()

    prompt = f"""You are an elite YouTube SEO & Viral Growth Strategist.
Given the video topic and script below, generate high-CTR metadata tailored for YouTube search and recommendation algorithms.

Topic: {topic_clean}
Visual Style: {visual_style}
Keywords: {keywords_clean}
Script Excerpt: {script_snippet}

Requirements:
1. "titles": Array of exactly 3 different click-worthy, viral titles under 95 characters. Use power hooks, brackets/numbers, or emotional intrigue.
2. "description": A complete, beautifully formatted SEO video description containing:
   - Hook line and brief overview (2 sentences)
   - Bullet points of key topics covered
   - Timestamp chapter breakdown (e.g. 00:00 Intro, etc.)
   - Call to action (Subscribe, Like, Comment)
   - 4-6 high-traffic hashtags (e.g. #Programming #Tutorial)
3. "tags": Array of 15 to 20 highly searched YouTube tags and long-tail keyword phrases.
4. "category_id": Recommended YouTube category ID ("27" for Education, "28" for Science & Technology).

Return ONLY a valid JSON object matching this schema:
{{
  "titles": ["Title 1", "Title 2", "Title 3"],
  "description": "Full description text...",
  "tags": ["tag1", "tag2", "tag3"],
  "category_id": "27"
}}
"""

    meta = None
    try:
        raw_response = BrainManager.ask(prompt, TaskType.KEYWORDS)
        # Parse JSON
        m = re.search(r"(\{.*\})", raw_response, re.DOTALL)
        if m:
            meta = json.loads(m.group(1))
        else:
            meta = json.loads(raw_response)
    except Exception as e:
        print(f"[YouTubeOptimizer] AI generation fallback triggered: {e}")
        meta = _fallback_metadata(topic_clean, keywords_clean)

    # Validate / sanitize parsed metadata
    titles = meta.get("titles") if isinstance(meta.get("titles"), list) and len(meta.get("titles")) > 0 else [f"{topic_clean} Tutorial"]
    description = meta.get("description") or f"Tutorial covering {topic_clean}."
    tags = meta.get("tags") if isinstance(meta.get("tags"), list) else [topic_clean, "Education"]
    category_id = str(meta.get("category_id", "27"))

    # Extract thumbnail if video_path provided
    thumb_path = None
    if video_path:
        thumb_path = extract_video_thumbnail(video_path)

    return YouTubeOptimizeResponse(
        titles=titles,
        description=description,
        tags=tags,
        category_id=category_id,
        suggested_thumbnail_path=thumb_path
    )
