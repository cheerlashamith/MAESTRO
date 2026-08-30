from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Mode(str, Enum):
    manual_course = "manual_course"
    story = "story"
    youtube_extract = "youtube_extract"
    autonomous = "autonomous"

class VisualStyle(str, Enum):
    manim_course = "manim_course"
    comfyui_story = "comfyui_story"
    pexels = "pexels"
    hybrid = "hybrid"

class JobStatus(str, Enum):
    queued = "queued"
    planning = "planning"
    rendering = "rendering"
    assembling = "assembling"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class TaskType(str, Enum):
    PLANNING = "planning"
    CODE = "code"
    STORY = "story"
    KEYWORDS = "keywords"
    CLASSIFY = "classify"
    SYLLABUS = "syllabus"
    ENRICHMENT = "enrichment"

class GenerateRequest(BaseModel):
    mode: Mode
    topic: str = Field(default="", min_length=0)
    visual_style: VisualStyle = VisualStyle.manim_course
    syllabus_subject: Optional[str] = None
    selected_units: List[str] = []
    youtube_url: Optional[str] = None
    script_override: Optional[str] = None
    keywords_override: Optional[str] = None
    notes: Optional[str] = None
    # Optional rendering preferences
    aspect: Optional[str] = None  # "16:9" or "9:16"
    voice: Optional[str] = None
    subtitle_enabled: Optional[bool] = None
    bgm_volume: Optional[float] = None
    feedback: Optional[str] = None
    previous_plan: Optional[Dict[str, Any]] = None
    # YouTube Auto-Publishing & Scheduling
    auto_publish: bool = False
    publish_privacy: Optional[str] = "private"  # "public" | "unlisted" | "private" | "scheduled"
    publish_schedule_time: Optional[str] = None  # ISO 8601 string e.g. "2026-09-01T10:00:00Z"
    publish_schedule_mode: Optional[str] = "local"  # "local" | "native"
    publish_title: Optional[str] = None
    publish_description: Optional[str] = None
    publish_tags: Optional[List[str]] = None
    publish_category_id: Optional[str] = "27"  # Default 27 (Education)
    publish_thumbnail_path: Optional[str] = None

class YouTubeOptimizeRequest(BaseModel):
    topic: str
    script: Optional[str] = ""
    keywords: Optional[str] = ""
    visual_style: Optional[str] = "manim_course"
    video_path: Optional[str] = None

class YouTubeOptimizeResponse(BaseModel):
    titles: List[str]
    description: str
    tags: List[str]
    category_id: str = "27"
    suggested_thumbnail_path: Optional[str] = None

class YouTubePublishRequest(BaseModel):
    job_id: Optional[str] = None
    video_path: Optional[str] = None
    title: str
    description: str
    tags: List[str] = []
    category_id: str = "27"
    privacy_status: str = "private"  # "public", "unlisted", "private", "scheduled"
    schedule_time: Optional[str] = None  # ISO 8601 string
    schedule_mode: str = "local"  # "local" or "native"
    thumbnail_path: Optional[str] = None

class YouTubeScheduleRequest(YouTubePublishRequest):
    pass

class ScheduledUploadRecord(BaseModel):
    schedule_id: str
    job_id: Optional[str] = None
    video_path: str
    title: str
    description: str
    tags: List[str] = []
    category_id: str = "27"
    privacy_status: str = "private"
    schedule_time: Optional[str] = None
    schedule_mode: str = "local"
    thumbnail_path: Optional[str] = None
    status: str = "scheduled"  # "scheduled", "uploading", "completed", "failed", "cancelled"
    progress: int = 0
    message: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    uploaded_at: Optional[str] = None
    error: Optional[str] = None

class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    request: GenerateRequest
    output_dir: str
    message: str = ""
    files: Dict[str, Any] = {}
    progress_percentage: int = 0
    current_task: str = ""
    current_model: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    youtube_video_id: Optional[str] = None
    uploaded_at: Optional[str] = None
    youtube_url: Optional[str] = None
    scheduled_upload_id: Optional[str] = None
