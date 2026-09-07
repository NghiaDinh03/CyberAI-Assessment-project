"""Persistent Append-Only Audit Store — SQLite database table for verifiable runtime audit events."""

import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "/data")
ASSESSMENTS_DIR = os.path.join(DATA_DIR, "assessments")
DB_PATH = os.path.join(ASSESSMENTS_DIR, "assessments.db")

# Keys that must NEVER be persisted in audit logs in raw form
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "jwt", "authorization",
    "prompt", "response", "content", "raw_query", "file_content", "text"
}


ALLOWED_METRIC_KEYS = {
    "prompt_tokens", "completion_tokens", "total_tokens", "eval_tokens",
    "total_duration_ns", "load_duration_ns", "prompt_eval_duration_ns", "eval_duration_ns",
    "prompt_eval_count", "eval_count"
}


def _sanitize_payload(obj: Any) -> Any:
    """Recursively scrub raw prompts, tokens, and PII from payload structures."""
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if k_lower in ALLOWED_METRIC_KEYS:
                cleaned[k] = v
            elif any(s in k_lower for s in SENSITIVE_KEYS):
                if isinstance(v, str) and len(v) > 0:
                    cleaned[k] = f"[REDACTED_HASH:{hash_sha256(v)[:12]}]"
                else:
                    cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = _sanitize_payload(v)
        return cleaned
    elif isinstance(obj, list):
        return [_sanitize_payload(item) for item in obj]
    return obj


def hash_sha256(text: str) -> str:
    """Calculate SHA-256 hash of a string without persisting the raw text."""
    import hashlib
    if not isinstance(text, str):
        text = str(text or "")
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


class AuditStore:
    _lock = threading.Lock()
    _instance: Optional["AuditStore"] = None

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._initialized = False

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "AuditStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
            return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        """Lazy database initialization on first read/write."""
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                self._init_db()
                self._initialized = True

    def _init_db(self):
        """Idempotent migration for audit_events table."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    assessment_id TEXT,
                    chat_session_id TEXT,
                    request_id TEXT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    code_version TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_events_assessment_id 
                ON audit_events(assessment_id, created_at ASC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_events_chat_session_id 
                ON audit_events(chat_session_id, created_at ASC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_events_run_id 
                ON audit_events(run_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_events_type 
                ON audit_events(event_type)
            """)
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite audit_events table: {e}")
        finally:
            conn.close()

    def record_event(
        self,
        event_type: str,
        status: str,
        payload: Dict[str, Any],
        run_id: str,
        assessment_id: Optional[str] = None,
        chat_session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        code_version: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> str:
        """Append an immutable audit event to SQLite."""
        self._ensure_db()
        event_id = f"evt_{uuid.uuid4().hex}"
        ts = created_at or datetime.now(timezone.utc).isoformat()
        
        # Enforce sanitization
        sanitized_payload = _sanitize_payload(payload or {})
        payload_str = json.dumps(sanitized_payload, ensure_ascii=False)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_events (
                        event_id, assessment_id, chat_session_id, request_id,
                        run_id, event_type, status, code_version, created_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    assessment_id,
                    chat_session_id,
                    request_id,
                    run_id,
                    event_type,
                    status,
                    code_version,
                    ts,
                    payload_str,
                ))
                conn.commit()
                return event_id
            except Exception as e:
                logger.error(f"[AuditStore] Failed to record audit event {event_type}: {e}")
                return ""
            finally:
                conn.close()

    def get_events_by_assessment(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chronological audit events for a specific assessment."""
        self._ensure_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, event_id, assessment_id, run_id, event_type,
                       status, code_version, created_at, payload_json
                FROM audit_events
                WHERE assessment_id = ?
                ORDER BY id ASC
            """, (assessment_id,))
            rows = cursor.fetchall()
            events = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = {}
                events.append({
                    "id": r["id"],
                    "event_id": r["event_id"],
                    "assessment_id": r["assessment_id"],
                    "run_id": r["run_id"],
                    "event_type": r["event_type"],
                    "status": r["status"],
                    "code_version": r["code_version"],
                    "created_at": r["created_at"],
                    "payload": payload,
                })
            return events
        finally:
            conn.close()

    def get_events_by_session(self, chat_session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all chronological audit events for a chat session."""
        self._ensure_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, event_id, chat_session_id, request_id, run_id, event_type,
                       status, code_version, created_at, payload_json
                FROM audit_events
                WHERE chat_session_id = ?
                ORDER BY id ASC
            """, (chat_session_id,))
            rows = cursor.fetchall()
            events = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = {}
                events.append({
                    "id": r["id"],
                    "event_id": r["event_id"],
                    "chat_session_id": r["chat_session_id"],
                    "request_id": r["request_id"],
                    "run_id": r["run_id"],
                    "event_type": r["event_type"],
                    "status": r["status"],
                    "code_version": r["code_version"],
                    "created_at": r["created_at"],
                    "payload": payload,
                })
            return events
        finally:
            conn.close()

    def get_all_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent audit events for admin inspection."""
        self._ensure_db()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, event_id, assessment_id, chat_session_id, request_id, run_id,
                       event_type, status, code_version, created_at, payload_json
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            events = []
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                except Exception:
                    payload = {}
                events.append({
                    "id": r["id"],
                    "event_id": r["event_id"],
                    "assessment_id": r["assessment_id"],
                    "chat_session_id": r["chat_session_id"],
                    "request_id": r["request_id"],
                    "run_id": r["run_id"],
                    "event_type": r["event_type"],
                    "status": r["status"],
                    "code_version": r["code_version"],
                    "created_at": r["created_at"],
                    "payload": payload,
                })
            return events
        finally:
            conn.close()


audit_store = AuditStore.get_instance()
