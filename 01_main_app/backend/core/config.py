from __future__ import annotations
import copy
import json
import os
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_PATH = ROOT / "config.example.json"

# Placeholder returned by the API instead of a real secret. Sending it back
# unchanged on POST /api/config means "keep the stored value".
SECRET_MASK = "********"

# Any config key ending in one of these is treated as a secret and never sent to
# the browser in cleartext.
_SECRET_SUFFIXES = ("_api_key", "_secret", "_token", "_password")

# Environment variables take precedence over config.json so keys can be supplied
# without ever being written to disk.
_ENV_PROVIDER_KEYS = {
    "OPENAI_API_KEY": "openai_api_key",
    "GEMINI_API_KEY": "gemini_api_key",
    "GROQ_API_KEY": "groq_api_key",
    "PEXELS_API_KEY": "pexels_api_key",
}

# Service URLs live under "paths" in existing config.json files but every reader
# looks them up under "providers". Normalising both ways keeps old configs
# working and makes the env var overrides actually take effect.
_URL_KEYS = ("ollama_url", "comfyui_url")

_ENV_URL_KEYS = {
    "OLLAMA_URL": "ollama_url",
    "COMFYUI_URL": "comfyui_url",
}


def is_secret_key(key: str) -> bool:
    return key.lower().endswith(_SECRET_SUFFIXES)


@lru_cache(maxsize=1)
def _build_config() -> dict:
    # Safely load local .env files if present (never committed to git)
    for env_path in (ROOT / ".env", ROOT.parent / ".env"):
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            except Exception:
                pass

    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH
    cfg = json.loads(path.read_text(encoding="utf-8"))

    cfg.setdefault("providers", {})
    cfg.setdefault("paths", {})
    cfg.setdefault("features", {})

    # Service URLs: mirror between paths.* and providers.* so either layout works.
    for key in _URL_KEYS:
        value = cfg["providers"].get(key) or cfg["paths"].get(key)
        if value:
            cfg["providers"][key] = value
            cfg["paths"][key] = value

    for env_name, key in _ENV_URL_KEYS.items():
        value = os.environ.get(env_name)
        if value:
            cfg["providers"][key] = value
            cfg["paths"][key] = value

    if os.environ.get("MPT_URL"):
        cfg["paths"]["moneyprinter_api_url"] = os.environ["MPT_URL"]

    # Secrets from the environment override whatever is on disk.
    for env_name, key in _ENV_PROVIDER_KEYS.items():
        value = os.environ.get(env_name)
        if value:
            cfg["providers"][key] = value

    return cfg


def get_config() -> dict:
    """Return the effective configuration.

    A deep copy is returned so a caller mutating the result can't poison the
    cached configuration for the rest of the process.
    """
    return copy.deepcopy(_build_config())


def reload_config() -> None:
    _build_config.cache_clear()


# Backwards compatibility for callers that used get_config.cache_clear().
get_config.cache_clear = reload_config  # type: ignore[attr-defined]


def redact_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Deep copy of cfg with every secret value replaced by SECRET_MASK.

    Empty values stay empty so the UI can tell "not configured" from "hidden".
    """
    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: (SECRET_MASK if is_secret_key(k) and v else _walk(v))
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [_walk(v) for v in node]
        return node

    return _walk(copy.deepcopy(cfg))


def merge_preserving_secrets(incoming: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a client-submitted config over the stored one.

    A secret arriving as the mask (or empty) means the client never saw the real
    value, so the stored one is kept. Without this, saving settings from the
    admin UI would overwrite every API key with "********".
    """
    merged = copy.deepcopy(existing)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_preserving_secrets(value, merged[key])
        elif is_secret_key(key) and (value in (SECRET_MASK, "", None)):
            continue  # Keep the stored secret
        else:
            merged[key] = value
    return merged


def save_config(new_cfg: dict) -> None:
    """Persist configuration atomically, then invalidate the cache.

    Secrets supplied via environment variables are stripped before writing so
    they are never copied into config.json as a side effect of saving settings.
    """
    cfg = copy.deepcopy(new_cfg)
    providers = cfg.get("providers")
    if isinstance(providers, dict):
        for env_name, key in _ENV_PROVIDER_KEYS.items():
            env_value = os.environ.get(env_name)
            if env_value and providers.get(key) == env_value:
                providers.pop(key, None)

    tmp = CONFIG_PATH.with_suffix(f".json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)
    reload_config()


def api_token() -> str:
    """Optional shared secret for privileged endpoints.

    Unset (the default) means no auth, which is correct for the intended
    localhost-only usage. Set AUTOCOURSE_API_TOKEN before binding to 0.0.0.0.
    """
    return os.environ.get("AUTOCOURSE_API_TOKEN", "").strip()


def feature_enabled(name: str, default: bool = False) -> bool:
    value = get_config().get("features", {}).get(name, default)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def project_root() -> Path:
    return ROOT


def outputs_root() -> Path:
    cfg = get_config()
    out = cfg.get("paths", {}).get("outputs_dir", "outputs")
    p = ROOT / out
    p.mkdir(parents=True, exist_ok=True)
    return p
