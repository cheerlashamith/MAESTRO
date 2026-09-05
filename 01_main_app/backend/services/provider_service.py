"""
Enterprise Provider & Engine Connectivity Service for AutoCourse Studio.

Provides live diagnostic checks and dynamic status testing for:
- Ollama Local LLM
- ComfyUI Portable Diffusion Engine
- MoneyPrinterTurbo Assembly Service
- OpenAI / Cloud LLMs
- Pexels Stock Video API
- Manim Mathematical Rendering Engine
- Edge-TTS Voiceover Engine
"""
from __future__ import annotations
import shutil
import sys
import subprocess
import requests
from typing import Any, Dict
from backend.core.config import get_config


class ProviderService:
    @classmethod
    def test_ollama(cls, url: str = None) -> Dict[str, Any]:
        cfg = get_config()
        url = (url or cfg.get("providers", {}).get("ollama_url") or "http://127.0.0.1:11434").rstrip("/")
        try:
            r = requests.get(f"{url}/api/tags", timeout=4)
            if r.status_code == 200:
                data = r.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {"ok": True, "status": "Online", "url": url, "models": models, "latency_ms": int(r.elapsed.total_seconds() * 1000)}
            return {"ok": False, "status": f"HTTP {r.status_code}", "url": url, "models": []}
        except Exception as e:
            return {"ok": False, "status": "Offline / Unreachable", "url": url, "error": str(e), "models": []}

    @classmethod
    def test_comfyui(cls, url: str = None) -> Dict[str, Any]:
        cfg = get_config()
        url = (url or cfg.get("paths", {}).get("comfyui_url") or "http://127.0.0.1:8188").rstrip("/")
        try:
            r = requests.get(f"{url}/system_stats", timeout=4)
            if r.status_code == 200:
                data = r.json()
                devices = data.get("devices", [])
                vram = devices[0].get("vram_total", 0) if devices else 0
                return {
                    "ok": True,
                    "status": "Online",
                    "url": url,
                    "latency_ms": int(r.elapsed.total_seconds() * 1000),
                    "devices": [d.get("name") for d in devices],
                    "vram_gb": round(vram / (1024**3), 1) if vram else None,
                }
            return {"ok": False, "status": f"HTTP {r.status_code}", "url": url}
        except Exception as e:
            return {"ok": False, "status": "Offline", "url": url, "error": str(e)}

    @classmethod
    def test_moneyprinter(cls, url: str = None) -> Dict[str, Any]:
        cfg = get_config()
        url = (url or cfg.get("paths", {}).get("moneyprinter_api_url") or "http://127.0.0.1:8080").rstrip("/")
        try:
            r = requests.get(f"{url}/docs", timeout=4)
            if r.status_code == 200:
                return {"ok": True, "status": "Online", "url": url, "latency_ms": int(r.elapsed.total_seconds() * 1000)}
            return {"ok": False, "status": f"HTTP {r.status_code}", "url": url}
        except Exception as e:
            return {"ok": False, "status": "Offline", "url": url, "error": str(e)}

    @classmethod
    def test_openai(cls, api_key: str = None) -> Dict[str, Any]:
        cfg = get_config()
        key = api_key or cfg.get("providers", {}).get("openai_api_key", "")
        if not key:
            return {"ok": False, "status": "Not Configured", "message": "No OpenAI API key supplied."}
        try:
            headers = {"Authorization": f"Bearer {key}"}
            r = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
            if r.status_code == 200:
                return {"ok": True, "status": "Valid", "message": "Connected successfully to OpenAI API."}
            return {"ok": False, "status": "Invalid Key", "message": f"OpenAI returned status {r.status_code}"}
        except Exception as e:
            return {"ok": False, "status": "Connection Error", "error": str(e)}

    @classmethod
    def test_pexels(cls, api_key: str = None) -> Dict[str, Any]:
        cfg = get_config()
        key = api_key or cfg.get("providers", {}).get("pexels_api_key", "")
        if not key:
            return {"ok": False, "status": "Not Configured", "message": "No Pexels API key supplied."}
        try:
            headers = {"Authorization": key}
            r = requests.get("https://api.pexels.com/videos/search?query=nature&per_page=1", headers=headers, timeout=5)
            if r.status_code == 200:
                return {"ok": True, "status": "Valid", "message": "Connected successfully to Pexels API."}
            return {"ok": False, "status": "Invalid Key", "message": f"Pexels returned status {r.status_code}"}
        except Exception as e:
            return {"ok": False, "status": "Connection Error", "error": str(e)}

    @classmethod
    def test_manim(cls) -> Dict[str, Any]:
        manim_path = shutil.which("manim")
        return {
            "ok": manim_path is not None,
            "status": "Installed" if manim_path else "Not in PATH",
            "path": manim_path or "N/A",
        }

    @classmethod
    def test_edgetts(cls) -> Dict[str, Any]:
        try:
            import edge_tts
            return {"ok": True, "status": "Installed", "version": getattr(edge_tts, "__version__", "Available")}
        except ImportError:
            return {"ok": False, "status": "Not Installed"}

    @classmethod
    def get_all_provider_health(cls) -> Dict[str, Any]:
        return {
            "ollama": cls.test_ollama(),
            "comfyui": cls.test_comfyui(),
            "moneyprinter": cls.test_moneyprinter(),
            "openai": cls.test_openai(),
            "pexels": cls.test_pexels(),
            "manim": cls.test_manim(),
            "edge_tts": cls.test_edgetts(),
        }
