from __future__ import annotations
import json
import hashlib
import time
from pathlib import Path
from typing import Optional
from backend.core.config import get_config, project_root

CACHE_DIR = project_root() / "cache"

# 0 or negative means entries never expire.
DEFAULT_EXPIRATION_DAYS = 7


class CacheManager:
    """Disk cache for LLM responses, keyed by model + task + prompt + versions.

    Entries expire after brain_manager.cache_expiration_days. Without expiry a
    stale response is returned forever, which is what made prompt-template edits
    appear to have no effect.
    """

    @staticmethod
    def _is_enabled() -> bool:
        return bool(get_config().get("features", {}).get("enable_cache", True))

    @staticmethod
    def _expiration_seconds() -> float:
        raw = get_config().get("brain_manager", {}).get("cache_expiration_days", DEFAULT_EXPIRATION_DAYS)
        try:
            days = float(raw)
        except (TypeError, ValueError):
            days = DEFAULT_EXPIRATION_DAYS
        return days * 86400.0 if days > 0 else 0.0

    @staticmethod
    def _get_key(model_name: str, task_type: str, prompt: str, prompt_version: str = "1.0", system_prompt_version: str = "1.0") -> str:
        raw = f"{model_name}|{task_type}|{prompt}|{prompt_version}|{system_prompt_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_expired(path: Path, data: dict) -> bool:
        max_age = CacheManager._expiration_seconds()
        if max_age <= 0:
            return False
        # Entries written before cache_at existed fall back to the file mtime.
        cached_at = data.get("cached_at")
        if not isinstance(cached_at, (int, float)):
            try:
                cached_at = path.stat().st_mtime
            except OSError:
                return True
        return (time.time() - float(cached_at)) > max_age

    @staticmethod
    def get(model_name: str, task_type: str, prompt: str, prompt_version: str = "1.0", system_prompt_version: str = "1.0") -> Optional[str]:
        if not CacheManager._is_enabled():
            return None

        key = CacheManager._get_key(model_name, task_type, prompt, prompt_version, system_prompt_version)
        path = CACHE_DIR / task_type / f"{key}.json"

        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None

        if CacheManager._is_expired(path, data):
            try:
                path.unlink()
            except OSError:
                pass
            return None

        result = data.get("result")
        return result if isinstance(result, str) else None

    @staticmethod
    def set(model_name: str, task_type: str, prompt: str, result: str, prompt_version: str = "1.0", system_prompt_version: str = "1.0") -> None:
        if not CacheManager._is_enabled():
            return

        key = CacheManager._get_key(model_name, task_type, prompt, prompt_version, system_prompt_version)
        folder = CACHE_DIR / task_type
        folder.mkdir(parents=True, exist_ok=True)

        path = folder / f"{key}.json"
        payload = {"result": result, "cached_at": time.time(), "model": model_name}
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"[CacheManager] Could not write cache entry: {e}")

    @staticmethod
    def purge_expired() -> int:
        """Delete expired entries. Returns the number removed."""
        max_age = CacheManager._expiration_seconds()
        if max_age <= 0 or not CACHE_DIR.exists():
            return 0
        removed = 0
        cutoff = time.time() - max_age
        for path in CACHE_DIR.glob("*/*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                pass
        return removed

    @staticmethod
    def get_cache_stats() -> dict:
        total_size = 0
        total_files = 0
        expired = 0
        tasks = {}
        max_age = CacheManager._expiration_seconds()
        cutoff = time.time() - max_age if max_age > 0 else None

        if CACHE_DIR.exists():
            for task_dir in CACHE_DIR.iterdir():
                if not task_dir.is_dir():
                    continue
                count = 0
                size = 0
                for f in task_dir.glob("*.json"):
                    try:
                        stat = f.stat()
                    except OSError:
                        continue
                    count += 1
                    size += stat.st_size
                    if cutoff is not None and stat.st_mtime < cutoff:
                        expired += 1
                tasks[task_dir.name] = {"count": count, "size_bytes": size}
                total_files += count
                total_size += size

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "expired_files": expired,
            "expiration_days": max_age / 86400.0 if max_age > 0 else 0,
            "enabled": CacheManager._is_enabled(),
            "tasks": tasks,
        }
