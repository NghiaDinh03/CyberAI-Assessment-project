"""Persistent Session Store — File-based with auto-expiry TTL."""

import json
import os
import time
import logging
import threading
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_DIR = os.getenv("DATA_PATH", "/data") + "/sessions"
SESSION_TTL = 86400
MAX_HISTORY_PER_SESSION = 20


class SessionStore:
    _lock = threading.Lock()

    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return os.path.join(SESSIONS_DIR, f"{safe_id}.json")

    def save(self, session_id: str, data: dict):
        with self._lock:
            try:
                data["updated_at"] = time.time()
                if "created_at" not in data:
                    data["created_at"] = time.time()
                with open(self._session_path(session_id), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Failed to save session {session_id}: {e}")

    def load(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("updated_at", 0) > SESSION_TTL:
                self.delete(session_id)
                return {}
            return data
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return {}

    def delete(self, session_id: str):
        path = self._session_path(session_id)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to delete session {session_id}: {e}")

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.load(session_id).get("messages", [])

    def add_message(self, session_id: str, role: str, content: str):
        data = self.load(session_id)
        if "messages" not in data:
            data["messages"] = []
        data["messages"].append({"role": role, "content": content, "timestamp": time.time()})
        if len(data["messages"]) > MAX_HISTORY_PER_SESSION:
            data["messages"] = data["messages"][-MAX_HISTORY_PER_SESSION:]
        self.save(session_id, data)

    def get_context_messages(self, session_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for LLM context (role + content only)."""
        history = self.get_history(session_id)
        recent = history[-max_messages:] if len(history) > max_messages else history
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def clear_history(self, session_id: str):
        data = self.load(session_id)
        data["messages"] = []
        self.save(session_id, data)

    def cleanup_expired(self):
        now = time.time()
        cleaned = 0
        try:
            for f in os.listdir(SESSIONS_DIR):
                if f.endswith(".json"):
                    path = os.path.join(SESSIONS_DIR, f)
                    try:
                        with open(path, "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                        if now - data.get("updated_at", 0) > SESSION_TTL:
                            os.remove(path)
                            cleaned += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Session cleanup error: {e}")
        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} expired sessions")
        return cleaned

    def list_sessions(self) -> List[Dict]:
        sessions = []
        try:
            for f in os.listdir(SESSIONS_DIR):
                if f.endswith(".json"):
                    session_id = f.replace(".json", "")
                    data = self.load(session_id)
                    if data:
                        sessions.append({
                            "session_id": session_id,
                            "messages_count": len(data.get("messages", [])),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                        })
        except Exception as e:
            logger.warning(f"List sessions error: {e}")
        return sessions
