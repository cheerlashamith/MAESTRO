import time
import requests
from typing import Dict, Any
from backend.core.schemas import TaskType
from backend.core.config import get_config
from backend.services.models.base_plugin import AIModelPlugin


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3


def configured_openai_model() -> str:
    """The model from providers.openai_model, falling back to gpt-4o-mini.

    Shared with BrainManager so its routing matches whatever this plugin reports.
    """
    value = get_config().get("providers", {}).get("openai_model")
    return str(value).strip() if value else DEFAULT_OPENAI_MODEL


class OpenAIGpt4oMiniPlugin(AIModelPlugin):
    """
    Ultra-low cost OpenAI plugin with token conservation.

    Defaults to gpt-4o-mini; set providers.openai_model to use another model.
    """
    def model_name(self) -> str:
        return configured_openai_model()

    def supports_task(self, task: TaskType) -> bool:
        return True  # High precision, supports all pipeline tasks

    def is_healthy(self) -> bool:
        cfg = get_config().get("providers", {})
        api_key = cfg.get("openai_api_key")
        if not api_key:
            return False
        return super().is_healthy()

    def generate(self, prompt: str, timeout: int = None) -> Dict[str, Any]:
        cfg = get_config().get("providers", {})
        api_key = cfg.get("openai_api_key")
        if not api_key:
            raise ValueError("OpenAI API Key is not configured in config.json")

        self.total_requests += 1
        start = time.time()

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }

        try:
            temperature = float(cfg.get("openai_temperature", DEFAULT_TEMPERATURE))
        except (TypeError, ValueError):
            temperature = DEFAULT_TEMPERATURE

        # Token conservation prompt instruction
        payload = {
            "model": configured_openai_model(),
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise, high-efficiency AI engine. Output direct results without conversational intro or filler text to minimize tokens."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }

        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout or 45
            )
            if r.status_code != 200:
                raise RuntimeError(f"OpenAI API error ({r.status_code}): {r.text}")

            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", len(text) // 4)
            elapsed = time.time() - start

            self.consecutive_failures = 0
            self.last_successful_request = time.time()
            self.total_response_time += elapsed

            return {
                "text": text,
                "metrics": {
                    "response_time": round(elapsed, 2),
                    "tokens": total_tokens
                }
            }
        except Exception as e:
            self.total_failures += 1
            self.consecutive_failures += 1
            self.last_failure = time.time()
            raise e
