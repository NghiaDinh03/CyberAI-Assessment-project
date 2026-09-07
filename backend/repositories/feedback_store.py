"""Persistent Audit Feedback Store — SQLite database for Lead Auditor Golden Cases & Feedback Loop."""

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "./data")
ASSESSMENTS_DIR = os.path.join(DATA_DIR, "assessments")
DB_PATH = os.path.join(ASSESSMENTS_DIR, "audit_feedback.db")


class AuditFeedbackStore:
    _lock = threading.RLock()
    _instance: Optional["AuditFeedbackStore"] = None

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "AuditFeedbackStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_feedback_exemplars (
                        id TEXT PRIMARY KEY,
                        control_id TEXT NOT NULL,
                        standard TEXT NOT NULL DEFAULT 'iso27001',
                        input_fact_summary TEXT NOT NULL,
                        initial_ai_verdict TEXT,
                        expert_verdict TEXT NOT NULL,
                        expert_rationale TEXT NOT NULL,
                        auditor_username TEXT DEFAULT 'auditor',
                        metadata TEXT,
                        created_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_control
                    ON audit_feedback_exemplars(control_id, standard)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_created_at
                    ON audit_feedback_exemplars(created_at DESC)
                """)
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to initialize Audit Feedback SQLite database: {e}")
            finally:
                conn.close()

    def save_feedback(
        self,
        control_id: str,
        expert_verdict: str,
        expert_rationale: str,
        input_fact_summary: str = "",
        initial_ai_verdict: Optional[str] = None,
        standard: str = "iso27001",
        auditor_username: str = "auditor",
        metadata: Optional[Dict[str, Any]] = None,
        feedback_id: Optional[str] = None,
    ) -> str:
        fid = feedback_id or f"fb-{uuid.uuid4().hex[:8]}"
        now = time.time()
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO audit_feedback_exemplars (
                        id, control_id, standard, input_fact_summary, initial_ai_verdict,
                        expert_verdict, expert_rationale, auditor_username, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fid,
                    str(control_id).strip(),
                    str(standard).strip().lower(),
                    str(input_fact_summary).strip(),
                    str(initial_ai_verdict).strip() if initial_ai_verdict else None,
                    str(expert_verdict).strip().lower(),
                    str(expert_rationale).strip(),
                    str(auditor_username).strip(),
                    meta_str,
                    now,
                ))
                conn.commit()
                logger.info(f"[FeedbackStore] Saved feedback '{fid}' for control '{control_id}' (Verdict: {expert_verdict})")
                return fid
            except Exception as e:
                logger.error(f"[FeedbackStore] Error saving feedback: {e}")
                raise
            finally:
                conn.close()

    def get_feedback_by_control(
        self,
        control_id: str,
        standard: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if standard:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE control_id = ? AND standard = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(control_id).strip(), str(standard).strip().lower(), limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE control_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(control_id).strip(), limit))
            
            rows = cursor.fetchall()
            results = []
            for r in rows:
                meta = {}
                try:
                    if r["metadata"]:
                        meta = json.loads(r["metadata"])
                except Exception:
                    pass
                results.append({
                    "id": r["id"],
                    "control_id": r["control_id"],
                    "standard": r["standard"],
                    "input_fact_summary": r["input_fact_summary"],
                    "initial_ai_verdict": r["initial_ai_verdict"],
                    "expert_verdict": r["expert_verdict"],
                    "expert_rationale": r["expert_rationale"],
                    "auditor_username": r["auditor_username"],
                    "metadata": meta,
                    "created_at": r["created_at"],
                })
            return results
        finally:
            conn.close()

    def get_few_shot_exemplars(
        self,
        control_id: str,
        standard: Optional[str] = None,
        limit: int = 2,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent golden cases to inject as In-Context Few-Shot examples into Agent 2 prompt."""
        feedbacks = self.get_feedback_by_control(control_id, standard=standard, limit=limit)
        return feedbacks

    def format_few_shot_prompt(
        self,
        control_ids: List[str],
        standard: Optional[str] = None,
        max_exemplars: int = 3,
    ) -> str:
        """Format historical feedback exemplars into a prompt section for Agent 2."""
        all_exemplars = []
        for cid in control_ids:
            exs = self.get_few_shot_exemplars(cid, standard=standard, limit=1)
            all_exemplars.extend(exs)
            if len(all_exemplars) >= max_exemplars:
                break

        if not all_exemplars:
            return ""

        lines = ["\n--- HỌC TĂNG CƯỜNG TỪ LỊCH SỬ KIỂM TOÁN VIÊN (FEW-SHOT EXAMPLES) ---"]
        for ex in all_exemplars[:max_exemplars]:
            lines.append(f"• Control {ex['control_id']}:")
            if ex.get('input_fact_summary'):
                lines.append(f"  Thực tế ghi nhận: {ex['input_fact_summary'][:200]}")
            lines.append(f"  Kết luận chuẩn chuyên gia: {ex['expert_verdict'].upper()}")
            lines.append(f"  Căn cứ kiểm toán: {ex['expert_rationale'][:300]}")
        lines.append("--- HẾT MẪU ĐỐI SOÁT ---")
        return "\n".join(lines)

    def get_all_feedback(
        self,
        standard: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if standard:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE standard = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(standard).strip().lower(), limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [{
                "id": r["id"],
                "control_id": r["control_id"],
                "standard": r["standard"],
                "input_fact_summary": r["input_fact_summary"],
                "initial_ai_verdict": r["initial_ai_verdict"],
                "expert_verdict": r["expert_verdict"],
                "expert_rationale": r["expert_rationale"],
                "auditor_username": r["auditor_username"],
                "created_at": r["created_at"],
            } for r in rows]
        finally:
            conn.close()

    def delete_feedback(self, feedback_id: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM audit_feedback_exemplars WHERE id = ?", (feedback_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()
