from __future__ import annotations
import os
import subprocess
import time
import requests
from backend.core.config import get_config, outputs_root

# Generation defaults. Override any of these under providers.ollama_options.
DEFAULT_OPTIONS = {
    "temperature": 0.35,
    "top_p": 0.9,
    "num_ctx": 2048,    # Smaller context = faster model load + inference
    "num_predict": 1500,  # Cap output tokens to avoid runaway generation
}

OLLAMA_STARTUP_TIMEOUT_SECONDS = 3


def get_ollama_url() -> str:
    cfg = get_config()
    return cfg.get("providers", {}).get("ollama_url", "http://127.0.0.1:11434")


def _generation_options() -> dict:
    """Merge configured overrides over DEFAULT_OPTIONS."""
    options = dict(DEFAULT_OPTIONS)
    configured = get_config().get("providers", {}).get("ollama_options")
    if isinstance(configured, dict):
        options.update(configured)
    return options


def _ollama_is_up(timeout: float) -> bool:
    try:
        requests.get(get_ollama_url(), timeout=timeout)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


def ensure_ollama_running() -> None:
    """Start `ollama serve` if it isn't already reachable."""
    if _ollama_is_up(1.5):
        return

    # outputs_root() is an absolute path and creates the directory. The previous
    # relative "outputs/ollama.log" broke whenever the server's working
    # directory wasn't 01_main_app, and the handle was never closed.
    log_path = outputs_root() / "ollama.log"
    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=log_file,
                stderr=log_file,
                **popen_kwargs,
            )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "The 'ollama' executable was not found on PATH. Install it from "
            "https://ollama.com/download, or start it manually with: ollama serve"
        ) from exc

    for _ in range(OLLAMA_STARTUP_TIMEOUT_SECONDS):
        time.sleep(1)
        if _ollama_is_up(2):
            return

    raise RuntimeError(
        f"Ollama did not start within {OLLAMA_STARTUP_TIMEOUT_SECONDS} seconds. "
        f"See {log_path} for details."
    )


def call_ollama_api(prompt: str, model: str, timeout: int = None) -> str:
    """Low-level HTTP client to call Ollama's /api/generate endpoint."""
    if timeout is None:
        timeout = get_config().get("brain_manager", {}).get("timeout_seconds", 30)
    url = get_ollama_url() + "/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": _generation_options(),
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
