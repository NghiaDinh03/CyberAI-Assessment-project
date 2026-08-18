"""JSON-backed override store for system prompts.

File: ``$DATA_PATH/prompts_overrides.json`` (default: ``./data/prompts_overrides.json``).

Thread-safe single-process store. Reads on every call (cheap — small file),
writes are atomic (temp + rename).
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional

from . import defaults

logger = logging.getLogger(__name__)

_DATA_PATH = os.getenv("DATA_PATH", "./data")
_STORE_FILE = Path(_DATA_PATH) / "prompts_overrides.json"
_LOCK = threading.RLock()

MAX_PROMPT_LEN = 20_000  # safety cap per prompt


class PromptStore:
    """Lightweight JSON store. Use module-level helpers for the singleton."""

    def __init__(self, path: Path = _STORE_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if isinstance(v, str)}
        except Exception as exc:
            logger.warning("prompt store read failed (%s) — falling back to defaults", exc)
        return {}

    def _write(self, data: Dict[str, str]) -> None:
        # Atomic write: temp file in same dir → os.replace
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False,
            dir=str(self.path.parent), prefix=".prompts.", suffix=".tmp",
        ) as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tmp_name = tf.name
        os.replace(tmp_name, self.path)

    def get(self, key: str) -> str:
        meta = defaults.REGISTRY.get(key)
        if not meta:
            raise KeyError(f"Unknown prompt key: {key}")
        with _LOCK:
            overrides = self._load()
        return overrides.get(key, meta["default"])

    def list(self) -> List[Dict]:
        with _LOCK:
            overrides = self._load()
        items: List[Dict] = []
        for key, meta in defaults.REGISTRY.items():
            current = overrides.get(key, meta["default"])
            items.append({
                "key": key,
                "title": meta["title"],
                "description": meta["description"],
                "group": meta["group"],
                "default": meta["default"],
                "current": current,
                "is_overridden": key in overrides,
                "required_placeholders": meta.get("required_placeholders", []),
                "length": len(current),
            })
        return items

    def set(self, key: str, value: str) -> Dict:
        meta = defaults.REGISTRY.get(key)
        if not meta:
            raise KeyError(f"Unknown prompt key: {key}")
        if not isinstance(value, str):
            raise ValueError("Prompt value must be a string")
        if len(value) > MAX_PROMPT_LEN:
            raise ValueError(f"Prompt exceeds max length {MAX_PROMPT_LEN}")
        for ph in meta.get("required_placeholders", []):
            if ph not in value:
                raise ValueError(f"Missing required placeholder: {ph}")
        with _LOCK:
            data = self._load()
            data[key] = value
            self._write(data)
        return {"key": key, "length": len(value), "is_overridden": True}

    def reset(self, key: str) -> Dict:
        meta = defaults.REGISTRY.get(key)
        if not meta:
            raise KeyError(f"Unknown prompt key: {key}")
        with _LOCK:
            data = self._load()
            removed = data.pop(key, None) is not None
            self._write(data)
        return {"key": key, "is_overridden": False, "was_overridden": removed}


# ── Module-level singleton API ─────────────────────────────────────────────
_singleton: Optional[PromptStore] = None


def _get_store() -> PromptStore:
    global _singleton
    if _singleton is None:
        with _LOCK:
            if _singleton is None:
                _singleton = PromptStore()
    return _singleton


def get_prompt(key: str) -> str:
    """Return the current prompt text (override if present, else default)."""
    return _get_store().get(key)


def list_prompts() -> List[Dict]:
    return _get_store().list()


def set_prompt(key: str, value: str) -> Dict:
    return _get_store().set(key, value)


def reset_prompt(key: str) -> Dict:
    return _get_store().reset(key)
