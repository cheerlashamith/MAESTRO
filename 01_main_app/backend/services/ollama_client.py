from __future__ import annotations
import requests
from backend.core.config import get_config

def get_ollama_url() -> str:
    cfg = get_config()
    return cfg.get("providers", {}).get("ollama_url", "http://127.0.0.1:11434")

def call_ollama_api(prompt: str, model: str, timeout: int = None) -> str:
    """Low-level HTTP client to call Ollama's /api/generate endpoint."""
    if timeout is None:
        timeout = get_config().get("brain_manager", {}).get("timeout_seconds", 30)
    url = get_ollama_url() + "/api/generate"

    def ensure_ollama_running():
        try:
            requests.get(get_ollama_url(), timeout=1.5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        import subprocess, os, time
        # Write logs to file to prevent block
        log_file = open(get_config().get("paths", {}).get("outputs_dir", "outputs") + "/ollama.log", "w", encoding="utf-8")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_file,
            stderr=log_file,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        for _ in range(60):
            time.sleep(1)
            try:
                requests.get(get_ollama_url(), timeout=2)
                return
            except requests.exceptions.ConnectionError:
                pass
        raise RuntimeError("Ollama did not start within 60 seconds.")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.35,
            "top_p": 0.9,
            "num_ctx": 2048,   # Smaller context = faster model load + inference
            "num_predict": 1500, # Cap output tokens to avoid runaway generation
        },
    }
    try:
        ensure_ollama_running()
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(f"Ollama is not running at {get_ollama_url()}. Start it with: ollama serve") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"Ollama request for model {model} timed out after {timeout}s.") from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"Ollama returned an error for {model}: {exc.response.text}") from exc
