"""
Enterprise AI Studio Workflow Service for AutoCourse.
Directly inspired by sasi-erp microservices/studio architecture.

Provides:
- Visual Graph Workflow Definitions (Nodes, Edges, Node Types)
- Live Execution Triggering through AutoCourse Pipeline
- JSON-backed Workflow Store (ready to link SQLite/PostgreSQL later)
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.core.config import project_root, get_config
from backend.core.schemas import GenerateRequest, Mode, VisualStyle
from backend.services.pipeline import submit_job

DATA_DIR = project_root() / "data"
WORKFLOWS_FILE = DATA_DIR / "studio_workflows.json"
NODE_TYPES_FILE = DATA_DIR / "studio_node_types.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Node Library Palette Definitions
DEFAULT_NODE_TYPES = [
    {
        "id": "nt-input",
        "slug": "input_trigger",
        "name": "Topic & Input Trigger",
        "category": "Trigger",
        "description": "Initial trigger node receiving course topic, syllabus unit, or YouTube URL.",
        "icon": "Play",
        "color": "#3b82f6",
        "inputs": [],
        "outputs": ["topic_data"],
        "default_config": {
            "mode": "manual_course",
            "topic": "",
            "syllabus_unit": "Unit 1: Stacks & Queues",
        }
    },
    {
        "id": "nt-planner",
        "slug": "llm_planner",
        "name": "AI Script & Scene Planner",
        "category": "Intelligence",
        "description": "Generates structured slide scenes, voiceover narration scripts, and search terms via Ollama / OpenAI.",
        "icon": "Brain",
        "color": "#8b5cf6",
        "inputs": ["topic_data"],
        "outputs": ["scenes_plan", "script", "keywords"],
        "default_config": {
            "model": "qwen2.5:7b",
            "temperature": 0.7,
            "system_prompt_version": "1.0",
        }
    },
    {
        "id": "nt-manim",
        "slug": "manim_engine",
        "name": "Manim Code & Math Engine",
        "category": "Visual Renderer",
        "description": "Renders high-definition mathematical and algorithmic 2D/3D code animations locally.",
        "icon": "Code2",
        "color": "#10b981",
        "inputs": ["scenes_plan"],
        "outputs": ["video_clips"],
        "default_config": {
            "resolution": "1080p",
            "fps": 30,
            "theme": "dark_modern",
        }
    },
    {
        "id": "nt-comfyui",
        "slug": "comfyui_engine",
        "name": "ComfyUI Diffusion Engine",
        "category": "Visual Renderer",
        "description": "Diffuses visual story scenes using Stable Diffusion 3.5 / Flux locally over ComfyUI API.",
        "icon": "Wand2",
        "color": "#ec4899",
        "inputs": ["scenes_plan"],
        "outputs": ["video_clips"],
        "default_config": {
            "comfyui_url": "http://127.0.0.1:8188",
            "workflow_file": "sd3.5_simple_example_api.json",
            "steps": 20,
            "cfg": 4.0,
            "aspect": "9:16",
        }
    },
    {
        "id": "nt-pexels",
        "slug": "pexels_engine",
        "name": "Pexels B-Roll Engine",
        "category": "Visual Renderer",
        "description": "Searches and fetches 4K/HD stock footage matching topic keywords dynamically.",
        "icon": "Film",
        "color": "#06b6d4",
        "inputs": ["keywords"],
        "outputs": ["video_clips"],
        "default_config": {
            "max_clips": 6,
            "orientation": "landscape",
        }
    },
    {
        "id": "nt-tts",
        "slug": "voiceover_tts",
        "name": "Neural Voiceover TTS",
        "category": "Audio",
        "description": "Synthesizes human-like narration using Edge-TTS multilingual neural voices.",
        "icon": "Mic",
        "color": "#f59e0b",
        "inputs": ["script"],
        "outputs": ["audio_track"],
        "default_config": {
            "voice": "en-US-AndrewMultilingualNeural",
            "rate": "+0%",
            "volume": "+0%",
        }
    },
    {
        "id": "nt-assembly",
        "slug": "mpt_assembly",
        "name": "MoneyPrinterTurbo Assembly",
        "category": "Assembly",
        "description": "Compiles visual clips, synchronized voiceover audio, auto-subtitles, and background music into a master MP4.",
        "icon": "Layers",
        "color": "#6366f1",
        "inputs": ["video_clips", "audio_track"],
        "outputs": ["final_video_mp4"],
        "default_config": {
            "aspect": "16:9",
            "subtitle_enabled": False,
            "bgm_volume": 0.05,
        }
    },
    {
        "id": "nt-approval",
        "slug": "hitl_approval",
        "name": "Human Review Gate",
        "category": "Governance",
        "description": "Pauses execution for human approval and branches to Approved or Rejected.",
        "icon": "UserCheck",
        "color": "#f59e0b",
        "inputs": ["scenes_plan"],
        "outputs": ["approved", "rejected"],
        "default_config": {
            "reviewer_role": "Video Creator",
            "timeout_seconds": 300,
            "auto_approve": False
        }
    },
    {
        "id": "nt-verification",
        "slug": "ai_verification",
        "name": "AI Verification",
        "category": "Intelligence",
        "description": "AI agent validates script accuracy, clarity, and safety compliance.",
        "icon": "Sparkles",
        "color": "#ec4899",
        "inputs": ["script"],
        "outputs": ["verified_data"],
        "default_config": {
            "strictness": "high",
            "check_facts": True
        }
    },
    {
        "id": "nt-seo",
        "slug": "youtube_seo",
        "name": "AI Viral SEO Optimizer",
        "category": "Optimization",
        "description": "Generates viral video titles, searchable descriptions, relevant tags, and selects category.",
        "icon": "Sparkles",
        "color": "#eab308",
        "inputs": ["script", "keywords"],
        "outputs": ["optimized_metadata"],
        "default_config": {
            "generate_thumbnail": True,
            "tag_count": 15,
        }
    },
    {
        "id": "nt-publisher",
        "slug": "youtube_publisher",
        "name": "YouTube Auto-Publisher",
        "category": "Distribution",
        "description": "Directly publishes or schedules video uploads to your connected YouTube Channel.",
        "icon": "Share2",
        "color": "#ef4444",
        "inputs": ["final_video_mp4", "optimized_metadata"],
        "outputs": ["youtube_video_url"],
        "default_config": {
            "privacy": "private",
            "schedule_mode": "local",
        }
    }
]

# Pre-seeded Default Enterprise Workflows for the 4 Video Production Modes
DEFAULT_WORKFLOWS = [
    {
        "id": "wf-manual-course",
        "name": "Manual Course Mode: Syllabus & Algorithm Master",
        "description": "Syllabus-aware academic lecture generator with algorithmic animations, Edge-TTS speech, and human review gate.",
        "category": "Education & Courses",
        "icon": "BookOpen",
        "status": "published",
        "version": "2.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Course Syllabus Input", "position_x": 80, "position_y": 140, "config": {"mode": "manual_course", "topic": "Binary Search Trees Operations"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Curriculum Planner", "position_x": 360, "position_y": 140, "config": {"model": "qwen2.5:7b", "temperature": 0.7}},
            {"id": "node-3", "node_type_id": "nt-approval", "label": "Human Approval Gate", "position_x": 640, "position_y": 140, "config": {"reviewer_role": "Instructor", "auto_approve": False}},
            {"id": "node-4", "node_type_id": "nt-manim", "label": "Vector Slide Engine", "position_x": 920, "position_y": 60, "config": {"resolution": "1080p", "fps": 30}},
            {"id": "node-5", "node_type_id": "nt-tts", "label": "Neural Lecture Voice", "position_x": 920, "position_y": 220, "config": {"voice": "en-US-AndrewMultilingualNeural"}},
            {"id": "node-6", "node_type_id": "nt-assembly", "label": "16:9 Master Multiplexer", "position_x": 1200, "position_y": 140, "config": {"aspect": "16:9", "subtitle_enabled": False, "bgm_volume": 0.05}},
            {"id": "node-7", "node_type_id": "nt-seo", "label": "YouTube SEO & 1080p Thumbnail", "position_x": 1460, "position_y": 140, "config": {"generate_thumbnail": True}},
            {"id": "node-8", "node_type_id": "nt-publisher", "label": "YouTube Channel Publisher", "position_x": 1720, "position_y": 140, "config": {"privacy": "private"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e3-4", "source": "node-3", "target": "node-4", "label": "approved"},
            {"id": "e3-5", "source": "node-3", "target": "node-5", "label": "approved"},
            {"id": "e4-6", "source": "node-4", "target": "node-6"},
            {"id": "e5-6", "source": "node-5", "target": "node-6"},
            {"id": "e6-7", "source": "node-6", "target": "node-7"},
            {"id": "e7-8", "source": "node-7", "target": "node-8"},
        ]
    },
    {
        "id": "wf-viral-story",
        "name": "Viral Story Shorts Mode: AI Cinematic Narratives",
        "description": "9:16 vertical short-form story generator with dramatic pacing, AI visual diffusion, and auto-subtitles.",
        "category": "Story & Shorts",
        "icon": "Wand2",
        "status": "published",
        "version": "2.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Story Prompt Input", "position_x": 80, "position_y": 140, "config": {"mode": "story", "topic": "The Mystery of the Clockwork Kingdom"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Narrative Scene Planner", "position_x": 360, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-comfyui", "label": "Cinematic Visual Generator", "position_x": 660, "position_y": 60, "config": {"aspect": "9:16", "steps": 20, "cfg": 4.0}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Dramatic Neural Voice", "position_x": 660, "position_y": 220, "config": {"voice": "en-US-JennyNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "9:16 Vertical Video Assembly", "position_x": 960, "position_y": 140, "config": {"aspect": "9:16", "subtitle_enabled": True, "bgm_volume": 0.08}},
            {"id": "node-6", "node_type_id": "nt-publisher", "label": "YouTube Shorts Publisher", "position_x": 1260, "position_y": 140, "config": {"privacy": "private"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e2-4", "source": "node-2", "target": "node-4"},
            {"id": "e3-5", "source": "node-3", "target": "node-5"},
            {"id": "e4-5", "source": "node-4", "target": "node-5"},
            {"id": "e5-6", "source": "node-5", "target": "node-6"},
        ]
    },
    {
        "id": "wf-yt-extract",
        "name": "YouTube Extract & Repurpose Mode: URL to Course",
        "description": "Extracts transcripts from YouTube videos, rewrites them into structured lessons, and compiles matching visuals.",
        "category": "Repurposing",
        "icon": "MonitorPlay",
        "status": "published",
        "version": "2.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "YouTube URL Source", "position_x": 80, "position_y": 140, "config": {"mode": "youtube_extract", "youtube_url": "https://www.youtube.com/watch?v=kqtD5dpn9C8", "topic": "Python Programming in 100 Seconds"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Lesson Rewriter", "position_x": 360, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-approval", "label": "Creator Review Gate", "position_x": 640, "position_y": 140, "config": {"reviewer_role": "Editor"}},
            {"id": "node-4", "node_type_id": "nt-pexels", "label": "Smart Visual Matcher", "position_x": 920, "position_y": 60, "config": {"max_clips": 6}},
            {"id": "node-5", "node_type_id": "nt-tts", "label": "Explainer Narration", "position_x": 920, "position_y": 220, "config": {"voice": "en-US-AndrewMultilingualNeural"}},
            {"id": "node-6", "node_type_id": "nt-assembly", "label": "Course Assembler", "position_x": 1200, "position_y": 140, "config": {"aspect": "16:9", "subtitle_enabled": True}},
            {"id": "node-7", "node_type_id": "nt-publisher", "label": "YouTube Publisher", "position_x": 1460, "position_y": 140, "config": {"privacy": "private"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e3-4", "source": "node-3", "target": "node-4", "label": "approved"},
            {"id": "e3-5", "source": "node-3", "target": "node-5", "label": "approved"},
            {"id": "e4-6", "source": "node-4", "target": "node-6"},
            {"id": "e5-6", "source": "node-5", "target": "node-6"},
            {"id": "e6-7", "source": "node-6", "target": "node-7"},
        ]
    },
    {
        "id": "wf-autonomous-channel",
        "name": "Autonomous Channel Engine: 24/7 Autopilot Loop",
        "description": "Zero-touch autonomous video generator driven by YouTube trend intelligence, automated metadata optimization, and scheduled auto-publishing.",
        "category": "YouTube Automation",
        "icon": "Zap",
        "status": "published",
        "version": "2.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Trend & Performance Trigger", "position_x": 80, "position_y": 140, "config": {"mode": "autonomous", "topic": "High-Impact AI Architectures"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Viral Topic & Scene Planner", "position_x": 360, "position_y": 140, "config": {"model": "qwen2.5:7b", "temperature": 0.8}},
            {"id": "node-3", "node_type_id": "nt-manim", "label": "Algorithmic Visual Scenes", "position_x": 660, "position_y": 60, "config": {"resolution": "1080p", "fps": 30}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Neural Audio Narration", "position_x": 660, "position_y": 220, "config": {"voice": "en-US-AndrewMultilingualNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "Direct Video Multiplexer", "position_x": 960, "position_y": 140, "config": {"aspect": "16:9", "bgm_volume": 0.05}},
            {"id": "node-6", "node_type_id": "nt-seo", "label": "AI Metadata & OpenCV Thumbnail", "position_x": 1240, "position_y": 140, "config": {"generate_thumbnail": True, "tag_count": 15}},
            {"id": "node-7", "node_type_id": "nt-publisher", "label": "Auto-Publish Gateway", "position_x": 1520, "position_y": 140, "config": {"privacy": "private"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e2-4", "source": "node-2", "target": "node-4"},
            {"id": "e3-5", "source": "node-3", "target": "node-5"},
            {"id": "e4-5", "source": "node-4", "target": "node-5"},
            {"id": "e5-6", "source": "node-5", "target": "node-6"},
            {"id": "e6-7", "source": "node-6", "target": "node-7"},
        ]
    },
    {
        "id": "wf-ultrafast-direct",
        "name": "Ultrafast 1080p Direct Synthesizer",
        "description": "High-speed local video generation engine using Edge-TTS narration, dynamic Pillow slides, and FFmpeg multiplexing with HITL review.",
        "category": "UltraFast Engines",
        "icon": "Play",
        "status": "published",
        "version": "2.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Course Topic Input", "position_x": 80, "position_y": 140, "config": {"mode": "manual_course", "topic": "Binary Search Tree Operations"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Curriculum Planner", "position_x": 360, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-approval", "label": "Human Approval Gate", "position_x": 640, "position_y": 140, "config": {"reviewer_role": "Instructor"}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Edge-TTS Synthesis", "position_x": 920, "position_y": 140, "config": {"voice": "en-US-GuyNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "DirectSynthesizer Assembly", "position_x": 1200, "position_y": 140, "config": {"aspect": "16:9"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e3-4", "source": "node-3", "target": "node-4", "label": "approved"},
            {"id": "e4-5", "source": "node-4", "target": "node-5"},
        ]
    }
]


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _write_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_studio_initialized():
    """Seed default node types and workflows if not present."""
    if not NODE_TYPES_FILE.exists():
        _write_json(NODE_TYPES_FILE, DEFAULT_NODE_TYPES)
    if not WORKFLOWS_FILE.exists():
        _write_json(WORKFLOWS_FILE, DEFAULT_WORKFLOWS)


ensure_studio_initialized()


from backend.core.db import Database


class StudioService:
    @classmethod
    def get_node_types(cls) -> List[Dict[str, Any]]:
        return _read_json(NODE_TYPES_FILE, DEFAULT_NODE_TYPES)

    @classmethod
    def get_workflows(cls) -> List[Dict[str, Any]]:
        return Database.get_workflows()

    @classmethod
    def get_workflow(cls, workflow_id: str) -> Optional[Dict[str, Any]]:
        return Database.get_workflow(workflow_id)

    @classmethod
    def save_workflow(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        return Database.save_workflow(data)

    @classmethod
    def delete_workflow(cls, workflow_id: str) -> bool:
        return Database.delete_workflow(workflow_id)

    @classmethod
    def run_workflow(cls, workflow_id: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a workflow by dynamically converting all node configurations into a GenerateRequest
        and starting the end-to-end background pipeline with full auto-publish & parameter propagation.
        Zero hardcoded parameters: any model, voice, aspect, prompt, or approval toggle edited
        in the visual graph is immediately honored during runtime execution!
        """
        from backend.services.iam_service import IAMService
        wf = cls.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        overrides = overrides or {}
        nodes = {n["id"]: n for n in wf.get("nodes", [])}

        # 1. Input Node Configuration
        input_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-input"), None)
        input_cfg = input_node.get("config", {}) if input_node else {}

        # 2. Planner Node Configuration
        planner_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-planner"), None)
        planner_cfg = planner_node.get("config", {}) if planner_node else {}

        # 3. Visual Nodes
        has_comfy = any(n.get("node_type_id") == "nt-comfyui" for n in nodes.values())
        has_pexels = any(n.get("node_type_id") == "nt-pexels" for n in nodes.values())
        has_manim = any(n.get("node_type_id") == "nt-manim" for n in nodes.values())

        # 4. Audio / Voice Node
        tts_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-tts"), None)
        tts_cfg = tts_node.get("config", {}) if tts_node else {}

        # 5. Assembly Node
        assembly_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-assembly"), None)
        assembly_cfg = assembly_node.get("config", {}) if assembly_node else {}

        # 6. Governance / Human Approval Node
        approval_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-approval"), None)
        approval_cfg = approval_node.get("config", {}) if approval_node else {}

        # 7. Distribution / YouTube Publisher Node
        publisher_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-publisher"), None)
        publisher_cfg = publisher_node.get("config", {}) if publisher_node else {}
        has_publisher = publisher_node is not None

        # -------------------------------------------------------------------
        # Dynamic Mode & Visual Style Resolution
        # -------------------------------------------------------------------
        raw_mode = overrides.get("mode") or input_cfg.get("mode")
        if not raw_mode:
            if has_comfy:
                raw_mode = "story"
            elif "youtube" in (input_cfg.get("youtube_url") or "") or "extract" in workflow_id:
                raw_mode = "youtube_extract"
            elif "auto" in workflow_id:
                raw_mode = "autonomous"
            else:
                raw_mode = "manual_course"

        if raw_mode in ("manual", "manual_course"):
            mode = Mode.manual_course
        elif raw_mode == "story":
            mode = Mode.story
        elif raw_mode in ("youtube", "youtube_extract"):
            mode = Mode.youtube_extract
        else:
            mode = Mode.autonomous

        if mode == Mode.story or has_comfy:
            visual_style = VisualStyle.comfyui_story
        elif has_pexels or mode in (Mode.autonomous, Mode.youtube_extract):
            visual_style = VisualStyle.pexels
        else:
            visual_style = VisualStyle.manim_course

        # -------------------------------------------------------------------
        # Dynamic Parameters Extracted from Nodes
        # -------------------------------------------------------------------
        topic = (
            overrides.get("topic") 
            or input_cfg.get("topic") 
            or input_cfg.get("youtube_url") 
            or "High-Impact AI & Computing Architecture"
        )

        model_override = overrides.get("model") or planner_cfg.get("model")
        temperature_override = overrides.get("temperature") or planner_cfg.get("temperature")
        system_prompt_override = overrides.get("system_prompt") or planner_cfg.get("system_prompt")

        default_voice = "en-US-JennyNeural" if mode == Mode.story else "en-US-AndrewMultilingualNeural"
        voice = overrides.get("voice") or tts_cfg.get("voice") or default_voice
        voice_rate = overrides.get("rate") or tts_cfg.get("rate")
        voice_volume = overrides.get("volume") or tts_cfg.get("volume")

        default_aspect = "9:16" if mode == Mode.story else "16:9"
        aspect = overrides.get("aspect") or assembly_cfg.get("aspect") or default_aspect
        subtitle_enabled = overrides.get("subtitle_enabled", assembly_cfg.get("subtitle_enabled", mode == Mode.story))
        bgm_volume = overrides.get("bgm_volume", assembly_cfg.get("bgm_volume", 0.05))

        # Autonomous / Human Approval logic
        is_autonomous = overrides.get("autonomous", mode == Mode.autonomous or not approval_node)
        if is_autonomous:
            require_approval = False
            auto_publish = overrides.get("auto_publish", True)
        else:
            require_approval = overrides.get("require_approval", not approval_cfg.get("auto_approve", False) if approval_node else False)
            auto_publish = overrides.get("auto_publish", has_publisher)

        publish_privacy = overrides.get("publish_privacy") or publisher_cfg.get("privacy", "private")
        publish_category_id = overrides.get("publish_category_id") or publisher_cfg.get("category", "27")
        publish_schedule_time = overrides.get("publish_schedule_time")
        publish_schedule_mode = overrides.get("publish_schedule_mode") or publisher_cfg.get("schedule_mode", "local")

        current_u = IAMService.get_current_user()
        user_id = overrides.get("user_id") or (current_u.get("username") if current_u else "shamith")
        tenant_id = overrides.get("tenant_id") or "default"

        resolved_yt_url = (
            overrides.get("youtube_url")
            or input_cfg.get("youtube_url")
            or (topic if (topic and ("http://" in str(topic) or "https://" in str(topic))) else None)
            or "https://www.youtube.com/watch?v=kqtD5dpn9C8"
        )

        req = GenerateRequest(
            mode=mode,
            topic=topic,
            youtube_url=resolved_yt_url if mode == Mode.youtube_extract else (overrides.get("youtube_url") or input_cfg.get("youtube_url")),
            visual_style=visual_style,
            aspect=aspect,
            voice=voice,
            voice_rate=voice_rate,
            voice_volume=voice_volume,
            subtitle_enabled=subtitle_enabled,
            bgm_volume=bgm_volume,
            require_approval=require_approval,
            auto_publish=auto_publish,
            publish_privacy=publish_privacy,
            publish_schedule_time=publish_schedule_time,
            publish_schedule_mode=publish_schedule_mode,
            publish_category_id=publish_category_id,
            user_id=user_id,
            tenant_id=tenant_id,
            model_override=model_override,
            temperature_override=temperature_override,
            system_prompt_override=system_prompt_override,
            workflow_id=workflow_id,
            node_overrides=nodes
        )

        job_record = submit_job(req, user_id=user_id, tenant_id=tenant_id)
        return {
            "job_id": job_record.job_id,
            "workflow_id": workflow_id,
            "workflow_name": wf.get("name"),
            "status": job_record.status.value,
            "topic": topic,
            "mode": mode.value,
            "model": model_override or "default",
            "voice": voice,
            "output_dir": job_record.output_dir,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "auto_publish": auto_publish,
            "require_approval": require_approval
        }
