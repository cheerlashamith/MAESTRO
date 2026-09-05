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

# Pre-seeded Default Enterprise Workflows
DEFAULT_WORKFLOWS = [
    {
        "id": "wf-full-course",
        "name": "Full Syllabus Course Video Pipeline",
        "description": "Generates animated academic course videos with Manim animations, EdgeTTS narration, and MPT composition.",
        "category": "Education & Courses",
        "icon": "BookOpen",
        "status": "published",
        "version": "1.2.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Topic & Syllabus Input", "position_x": 80, "position_y": 140, "config": {"mode": "manual_course", "topic": "Binary Search Trees"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Ollama Curriculum Planner", "position_x": 380, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-manim", "label": "Manim Animation Engine", "position_x": 680, "position_y": 80, "config": {"resolution": "1080p", "fps": 30}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Andrew Multilingual Voice", "position_x": 680, "position_y": 240, "config": {"voice": "en-US-AndrewMultilingualNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "MoneyPrinterTurbo Assembly", "position_x": 980, "position_y": 140, "config": {"aspect": "16:9", "subtitle_enabled": False, "bgm_volume": 0.05}},
            {"id": "node-6", "node_type_id": "nt-seo", "label": "YouTube SEO & Metadata", "position_x": 1260, "position_y": 140, "config": {"generate_thumbnail": True}},
            {"id": "node-7", "node_type_id": "nt-publisher", "label": "YouTube Publishing Gateway", "position_x": 1540, "position_y": 140, "config": {"privacy": "private"}},
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
        "id": "wf-viral-story",
        "name": "Viral Story Shorts Pipeline (ComfyUI)",
        "description": "Generates 9:16 vertical short-form stories using ComfyUI SD3.5 visual diffusion and dramatic narration.",
        "category": "Story & Shorts",
        "icon": "Wand2",
        "status": "published",
        "version": "1.0.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "Story Prompt Input", "position_x": 80, "position_y": 140, "config": {"mode": "story", "topic": "The Mystery of the Clockwork Kingdom"}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Creative Narrative Planner", "position_x": 380, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-comfyui", "label": "ComfyUI SD3.5 Generator", "position_x": 680, "position_y": 80, "config": {"aspect": "9:16", "steps": 20, "cfg": 4.0}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Jenny Neural Story Voice", "position_x": 680, "position_y": 240, "config": {"voice": "en-US-JennyNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "MPT Vertical Video Assembly", "position_x": 980, "position_y": 140, "config": {"aspect": "9:16", "subtitle_enabled": True, "bgm_volume": 0.08}},
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
        "id": "wf-youtube-repurpose",
        "name": "YouTube URL Repurposing & B-Roll Pipeline",
        "description": "Extracts transcripts from YouTube videos, rewrites them for clarity, and compiles fresh Pexels footage.",
        "category": "Repurposing",
        "icon": "MonitorPlay",
        "status": "published",
        "version": "1.1.0",
        "nodes": [
            {"id": "node-1", "node_type_id": "nt-input", "label": "YouTube URL Source", "position_x": 80, "position_y": 140, "config": {"mode": "youtube_extract", "topic": ""}},
            {"id": "node-2", "node_type_id": "nt-planner", "label": "Transcript & Lesson Rewriter", "position_x": 380, "position_y": 140, "config": {"model": "qwen2.5:7b"}},
            {"id": "node-3", "node_type_id": "nt-pexels", "label": "Pexels B-Roll Matcher", "position_x": 680, "position_y": 80, "config": {"max_clips": 6}},
            {"id": "node-4", "node_type_id": "nt-tts", "label": "Narrator Audio Engine", "position_x": 680, "position_y": 240, "config": {"voice": "en-US-AndrewMultilingualNeural"}},
            {"id": "node-5", "node_type_id": "nt-assembly", "label": "MPT Master Assembly", "position_x": 980, "position_y": 140, "config": {"aspect": "16:9", "subtitle_enabled": True}},
            {"id": "node-6", "node_type_id": "nt-publisher", "label": "YouTube Scheduler", "position_x": 1260, "position_y": 140, "config": {"privacy": "scheduled"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "node-1", "target": "node-2"},
            {"id": "e2-3", "source": "node-2", "target": "node-3"},
            {"id": "e2-4", "source": "node-2", "target": "node-4"},
            {"id": "e3-5", "source": "node-3", "target": "node-5"},
            {"id": "e4-5", "source": "node-4", "target": "node-5"},
            {"id": "e5-6", "source": "node-5", "target": "node-6"},
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
        Executes a workflow by converting its node configuration into an AutoCourse GenerateRequest
        and starting the end-to-end background pipeline with full auto-publish & sub-step chaining.
        """
        from backend.services.iam_service import IAMService
        wf = cls.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        overrides = overrides or {}
        nodes = {n["id"]: n for n in wf.get("nodes", [])}

        # Extract parameters across nodes
        input_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-input"), None)
        assembly_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-assembly"), None)
        tts_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-tts"), None)
        publisher_node = next((n for n in nodes.values() if n.get("node_type_id") == "nt-publisher"), None)
        has_approval_node = any(n.get("node_type_id") == "nt-approval" for n in nodes.values())

        # Determine Mode
        raw_mode = overrides.get("mode") or (input_node.get("config", {}).get("mode") if input_node else "manual_course")
        if raw_mode in ("manual", "manual_course"):
            mode = Mode.manual_course
        elif raw_mode == "story":
            mode = Mode.story
        elif raw_mode in ("youtube", "youtube_extract"):
            mode = Mode.youtube_extract
        else:
            mode = Mode.autonomous

        # Determine Visual Style
        has_comfy = any(n.get("node_type_id") == "nt-comfyui" for n in nodes.values())
        has_pexels = any(n.get("node_type_id") == "nt-pexels" for n in nodes.values())
        if mode == Mode.story or has_comfy:
            visual_style = VisualStyle.comfyui_story
        elif has_pexels or mode in (Mode.autonomous, Mode.youtube_extract):
            visual_style = VisualStyle.pexels
        else:
            visual_style = VisualStyle.manim_course

        topic = overrides.get("topic") or (input_node.get("config", {}).get("topic") if input_node else "")
        if not topic:
            topic = "Modern AI & Full Stack Architecture Tutorial"

        aspect = overrides.get("aspect") or (assembly_node.get("config", {}).get("aspect") if assembly_node else ("9:16" if mode == Mode.story else "16:9"))
        voice = overrides.get("voice") or (tts_node.get("config", {}).get("voice") if tts_node else ("en-US-JennyNeural" if mode == Mode.story else "en-US-AndrewMultilingualNeural"))
        
        # Autonomous / Approval gate control
        # If user explicitly requested autonomous mode, or if workflow doesn't have an nt-approval node, bypass approval
        is_autonomous = overrides.get("autonomous", False)
        if is_autonomous:
            require_approval = False
            auto_publish = True
        else:
            require_approval = overrides.get("require_approval", has_approval_node)
            has_publisher = any(n.get("node_type_id") == "nt-publisher" for n in nodes.values())
            auto_publish = overrides.get("auto_publish", has_publisher)

        publish_privacy = overrides.get("publish_privacy") or (publisher_node.get("config", {}).get("privacy") if publisher_node else "private")
        publish_schedule_time = overrides.get("publish_schedule_time")

        current_u = IAMService.get_current_user()
        user_id = overrides.get("user_id") or (current_u.get("username") if current_u else "shamith")
        tenant_id = overrides.get("tenant_id") or "default"

        req = GenerateRequest(
            mode=mode,
            topic=topic,
            youtube_url=topic if mode == Mode.youtube_extract else None,
            visual_style=visual_style,
            aspect=aspect,
            voice=voice,
            subtitle_enabled=assembly_node.get("config", {}).get("subtitle_enabled") if assembly_node else None,
            bgm_volume=assembly_node.get("config", {}).get("bgm_volume", 0.05) if assembly_node else 0.05,
            require_approval=require_approval,
            auto_publish=auto_publish,
            publish_privacy=publish_privacy,
            publish_schedule_time=publish_schedule_time,
            user_id=user_id,
            tenant_id=tenant_id
        )

        job_record = submit_job(req, user_id=user_id, tenant_id=tenant_id)
        return {
            "job_id": job_record.job_id,
            "workflow_id": workflow_id,
            "workflow_name": wf.get("name"),
            "status": job_record.status.value,
            "topic": topic,
            "output_dir": job_record.output_dir,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "auto_publish": auto_publish,
            "require_approval": require_approval
        }
