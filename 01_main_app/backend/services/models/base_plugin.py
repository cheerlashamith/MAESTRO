import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from backend.core.schemas import TaskType
from backend.services.ollama_client import call_ollama_api

class AIModelPlugin(ABC):
    def __init__(self):
        self.total_requests = 0
        self.total_failures = 0
        self.last_successful_request = 0.0
        self.last_failure = 0.0
        self.total_response_time = 0.0
        self.consecutive_failures = 0

    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def supports_task(self, task: TaskType) -> bool:
        pass

    def is_healthy(self) -> bool:
        if self.consecutive_failures >= 3:
            return False
        from backend.services.ollama_client import _ollama_is_up
        return _ollama_is_up(0.4)

    def reset_health(self):
        """Reset failure counters — called on server startup."""
        self.consecutive_failures = 0
        self.total_failures = 0

    def generate(self, prompt: str, timeout: int = None) -> Dict[str, Any]:
        self.total_requests += 1
        start = time.time()
        try:
            res = call_ollama_api(prompt, self.model_name(), timeout)
            elapsed = time.time() - start
            
            self.consecutive_failures = 0  # Reset on success
            self.last_successful_request = time.time()
            self.total_response_time += elapsed
            
            return {
                "text": res,
                "metrics": {
                    "response_time": round(elapsed, 2),
                    "tokens": len(res) // 4
                }
            }
        except Exception as e:
            self.total_failures += 1
            self.consecutive_failures += 1
            self.last_failure = time.time()
            raise e

    def get_health_stats(self) -> Dict[str, Any]:
        avg = 0.0
        successes = self.total_requests - self.total_failures
        if successes > 0:
            avg = self.total_response_time / successes
            
        return {
            "model": self.model_name(),
            "healthy": self.is_healthy(),
            "requests": self.total_requests,
            "failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "avg_time": round(avg, 2)
        }
