"""Model Guard — verifies local GGUF availability and caches LocalAI health."""

import os
import threading
from typing import Dict

from core.config import settings


class ModelGuard:
    _lock = threading.Lock()
    _state: Dict[str, str] = {}

    @classmethod
    def refresh(cls) -> Dict[str, str]:
        base_dir = os.getenv("MODELS_PATH", "./models")
        summary = {}
        for model_id in settings.required_model_ids:
            path = cls._resolve_model_path(base_dir, model_id)
            summary[model_id] = "present" if path else "missing"

        with cls._lock:
            cls._state = summary
        return summary

    @classmethod
    def status(cls) -> Dict[str, str]:
        with cls._lock:
            return cls._state.copy() if cls._state else cls.refresh()

    @classmethod
    def is_ready(cls) -> bool:
        state = cls.status()
        return all(v == "present" for v in state.values())

    @staticmethod
    def _resolve_model_path(base_dir: str, model_id: str) -> str:
        candidates = [
            os.path.join(base_dir, model_id),
            os.path.join(base_dir, os.path.basename(model_id)),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""
