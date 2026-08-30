from __future__ import annotations
import importlib
import pkgutil
from typing import List, Optional
from backend.core.schemas import TaskType
from backend.services.models.base_plugin import AIModelPlugin
from backend.services.cache_manager import CacheManager
from backend.core.config import get_config

class BrainManager:
    _plugins: List[AIModelPlugin] = []
    _initialized = False

    @classmethod
    def _load_plugins(cls):
        if cls._initialized:
            return
        
        # Discover and instantiate all plugins in backend.services.models
        import backend.services.models as models_pkg
        
        for _, module_name, _ in pkgutil.iter_modules(models_pkg.__path__):
            if module_name == "base_plugin":
                continue
                
            module = importlib.import_module(f"backend.services.models.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, AIModelPlugin) and attr is not AIModelPlugin:
                    plugin = attr()
                    plugin.reset_health()  # Fresh start — no stale failure state
                    cls._plugins.append(plugin)
                    
        cls._initialized = True

    @classmethod
    def _get_model_for_task(cls, task_type: TaskType) -> List[AIModelPlugin]:
        cls._load_plugins()
        return [p for p in cls._plugins if p.supports_task(task_type)]

    @classmethod
    def ask(cls, prompt: str, task_type: TaskType, timeout: int = None, prompt_version: str = None, system_prompt_version: str = None) -> str:
        cfg = get_config().get("brain_manager", {})
        timeout = timeout or cfg.get("timeout_seconds", 900)
        prompt_version = prompt_version or cfg.get("prompt_version", "1.0")
        system_prompt_version = system_prompt_version or cfg.get("system_prompt_version", "1.0")
        
        # Fallback chain based on task type capability reported by healthy plugins
        capable_plugins = [p for p in cls._get_model_for_task(task_type) if p.is_healthy()]
        
        # Optional routing logic (length based) could be injected here
        cfg = get_config().get("providers", {})
        default_llm = cfg.get("default_llm", "ollama").lower()
        preferred = []

        if default_llm in ["openai", "gpt-4o-mini"]:
            preferred = [p for p in capable_plugins if p.model_name() == "gpt-4o-mini"]
        elif task_type in [TaskType.PLANNING, TaskType.STORY, TaskType.SYLLABUS]:
            target = cfg.get("planner_model", "qwen2.5:7b")
            preferred = [p for p in capable_plugins if p.model_name() == target]
        elif task_type == TaskType.CODE:
            target = cfg.get("coding_model", "qwen2.5:7b")
            if len(prompt) > 2500:
                target = cfg.get("planner_model", "qwen2.5:7b") # Large code -> planner
            preferred = [p for p in cls._plugins if p.model_name() == target]
            capable_plugins = list(set(capable_plugins + preferred))
        elif task_type in [TaskType.KEYWORDS, TaskType.CLASSIFY, TaskType.ENRICHMENT]:
            target = cfg.get("utility_model", "gemma3:4b")
            preferred = [p for p in capable_plugins if p.model_name() == target]

        fallback_chain = preferred + [p for p in capable_plugins if p not in preferred]
        
        if not fallback_chain:
            raise RuntimeError(f"No AI model plugin supports task type: {task_type.value}")
            
        # Execute with Fallback & Caching
        last_error = None
        for plugin in fallback_chain:
            try:
                # Cache Check
                cached = CacheManager.get(plugin.model_name(), task_type.value, prompt, prompt_version, system_prompt_version)
                if cached:
                    return cached
                    
                # Generate
                result_obj = plugin.generate(prompt, timeout=timeout)
                text = result_obj.get("text", "")
                metrics = result_obj.get("metrics", {})
                
                print(f"[BrainManager] Success | Model: {plugin.model_name()} | Task: {task_type.value} | Time: {metrics.get('response_time')}s | Tokens: {metrics.get('tokens')}")
                
                # Save Cache
                CacheManager.set(plugin.model_name(), task_type.value, prompt, text, prompt_version, system_prompt_version)
                
                return text
            except Exception as e:
                last_error = e
                print(f"[BrainManager] Plugin {plugin.model_name()} failed for {task_type.value}: {e}. Trying fallback...")
                
        raise RuntimeError(f"Brain Manager failed all fallbacks for {task_type.value}. Last error: {last_error}")

    @classmethod
    def get_plugin_health(cls) -> List[dict]:
        cls._load_plugins()
        return [p.get_health_stats() for p in cls._plugins]
