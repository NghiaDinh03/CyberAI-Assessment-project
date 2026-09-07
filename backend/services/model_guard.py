"""Model Guard — verifies local model availability across Ollama and local storage."""

import os
import logging
import threading
from typing import Dict, List
import requests

from core.config import settings

logger = logging.getLogger(__name__)


class ModelGuard:
    _lock = threading.RLock()
    _state: Dict[str, str] = {}

    @classmethod
    def refresh(cls) -> Dict[str, str]:
        """Check availability of all required models in Ollama and local disk."""
        base_dir = os.getenv("MODELS_PATH", "./models")
        summary = {}

        # Fetch available models from Ollama
        ollama_models = set()
        try:
            from services.cloud_llm_service import get_ollama_models
            ollama_models = {m.lower() for m in get_ollama_models(timeout=3)}
        except Exception as exc:
            logger.debug(f"[ModelGuard] Failed to fetch Ollama models: {exc}")

        for model_id in settings.required_model_ids:
            clean_id = model_id.strip()
            clean_lower = clean_id.lower()
            base_name = clean_lower.split(":")[0]

            is_present = False

            # 1. Check Ollama models (exact match or tag prefix)
            if clean_lower in ollama_models or any(om == base_name or om.startswith(base_name + ":") for om in ollama_models):
                is_present = True

            # 2. Check local GGUF files as fallback
            if not is_present:
                path = cls._resolve_model_path(base_dir, clean_id)
                if path:
                    is_present = True

            summary[clean_id] = "present" if is_present else "missing"

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

    @classmethod
    def get_missing_models(cls) -> List[str]:
        state = cls.status()
        return [m for m, status in state.items() if status != "present"]

    @classmethod
    def auto_pull_missing(cls, timeout: int = 600) -> Dict[str, bool]:
        """Automatically pull any missing models via Ollama API."""
        missing = cls.get_missing_models()
        results = {}
        if not missing:
            return results

        candidate_urls = [
            (getattr(settings, "OLLAMA_URL", "http://ollama:11434") or "http://ollama:11434").rstrip("/"),
            "http://host.docker.internal:11434",
            "http://ollama:11434",
            "http://127.0.0.1:11434",
        ]

        for model_id in missing:
            pulled = False
            for url in candidate_urls:
                try:
                    logger.info(f"[ModelGuard] Auto-pulling missing model '{model_id}' from {url}...")
                    resp = requests.post(
                        f"{url}/api/pull",
                        json={"name": model_id, "stream": False},
                        timeout=timeout,
                    )
                    if resp.status_code == 200:
                        logger.info(f"[ModelGuard] Successfully pulled '{model_id}'")
                        pulled = True
                        break
                except Exception as exc:
                    logger.warning(f"[ModelGuard] Pull '{model_id}' failed via {url}: {exc}")
            results[model_id] = pulled

        # Refresh cached status after pulling
        cls.refresh()
        return results

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
