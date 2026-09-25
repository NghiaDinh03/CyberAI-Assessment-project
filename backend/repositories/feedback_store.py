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
                        created_at REAL NOT NULL,
                        split TEXT NOT NULL DEFAULT 'few_shot',
                        label_status TEXT NOT NULL DEFAULT 'approved'
                    )
                """)
                # Idempotent migration for existing tables
                cursor.execute("PRAGMA table_info(audit_feedback_exemplars)")
                cols = {row["name"] for row in cursor.fetchall()}
                if "split" not in cols:
                    cursor.execute("ALTER TABLE audit_feedback_exemplars ADD COLUMN split TEXT NOT NULL DEFAULT 'few_shot'")
                if "label_status" not in cols:
                    cursor.execute("ALTER TABLE audit_feedback_exemplars ADD COLUMN label_status TEXT NOT NULL DEFAULT 'approved'")

                # Auto-flag legacy non_compliant records as 'needs_label_review'
                cursor.execute("""
                    UPDATE audit_feedback_exemplars
                    SET label_status = 'needs_label_review'
                    WHERE LOWER(expert_verdict) = 'non_compliant'
                      AND label_status = 'approved'
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_control
                    ON audit_feedback_exemplars(control_id, standard)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_created_at
                    ON audit_feedback_exemplars(created_at DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_split
                    ON audit_feedback_exemplars(split, standard)
                """)
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to initialize Audit Feedback SQLite database: {e}")
            finally:
                conn.close()

    @staticmethod
    def _row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
        meta = {}
        try:
            if r["metadata"]:
                meta = json.loads(r["metadata"])
        except Exception:
            pass
        keys = r.keys()
        return {
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
            "split": r["split"] if "split" in keys else "few_shot",
            "label_status": r["label_status"] if "label_status" in keys else "approved",
        }

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
        split: str = "few_shot",
        label_status: Optional[str] = None,
    ) -> str:
        fid = feedback_id or f"fb-{uuid.uuid4().hex[:8]}"
        now = time.time()
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        ev_clean = str(expert_verdict).strip().lower()

        # Enforce legacy protection: non_compliant must be flagged for review
        if label_status is None:
            if ev_clean == "non_compliant":
                label_status = "needs_label_review"
            else:
                label_status = "approved"

        clean_split = str(split).strip().lower() if split else "few_shot"

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO audit_feedback_exemplars (
                        id, control_id, standard, input_fact_summary, initial_ai_verdict,
                        expert_verdict, expert_rationale, auditor_username, metadata, created_at,
                        split, label_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fid,
                    str(control_id).strip(),
                    str(standard).strip().lower(),
                    str(input_fact_summary).strip(),
                    str(initial_ai_verdict).strip() if initial_ai_verdict else None,
                    ev_clean,
                    str(expert_rationale).strip(),
                    str(auditor_username).strip(),
                    meta_str,
                    now,
                    clean_split,
                    label_status,
                ))
                conn.commit()
                logger.info(f"[FeedbackStore] Saved feedback '{fid}' for control '{control_id}' (Verdict: {expert_verdict}, Split: {clean_split})")
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
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_few_shot_exemplars(
        self,
        control_id: str,
        standard: Optional[str] = None,
        limit: int = 2,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent golden cases to inject as In-Context Few-Shot examples into Agent 2 prompt.
        
        STRICT ANTI-LEAKAGE: Only retrieves exemplars assigned to split='few_shot' with label_status='approved'.
        Never returns records reserved for test evaluation split."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if standard:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE control_id = ? AND standard = ?
                      AND split = 'few_shot'
                      AND (label_status IS NULL OR label_status = 'approved')
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(control_id).strip(), str(standard).strip().lower(), limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE control_id = ?
                      AND split = 'few_shot'
                      AND (label_status IS NULL OR label_status = 'approved')
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(control_id).strip(), limit))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

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
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_evaluation_records(
        self,
        standard: Optional[str] = None,
        split: str = "test",
        include_pending_review: bool = False,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Retrieve evaluation records marked for a specific split (default: 'test').

        ANTI-LEAKAGE INVARIANT:
        When split='test', records allocated to few-shot are strictly excluded."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            status_filter = "" if include_pending_review else "AND (label_status IS NULL OR label_status = 'approved')"
            if standard and standard.lower() != "all":
                cursor.execute(f"""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE standard = ? AND split = ? {status_filter}
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(standard).strip().lower(), str(split).strip().lower(), limit))
            else:
                cursor.execute(f"""
                    SELECT * FROM audit_feedback_exemplars
                    WHERE split = ? {status_filter}
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (str(split).strip().lower(), limit))

            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]
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


# Singleton instance for evaluation and module-level access
feedback_store = AuditFeedbackStore.get_instance()

