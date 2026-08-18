"""Persistent Assessment Store — SQLite database for Infrastructure & ISO 27001 Assessments."""

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "/data")
ASSESSMENTS_DIR = os.path.join(DATA_DIR, "assessments")
DB_PATH = os.path.join(ASSESSMENTS_DIR, "assessments.db")


class AssessmentStore:
    _lock = threading.Lock()

    def __init__(self):
        os.makedirs(ASSESSMENTS_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS infrastructure_assessments (
                        id TEXT PRIMARY KEY,
                        project_name TEXT NOT NULL,
                        system_scope TEXT,
                        overall_score REAL NOT NULL,
                        risk_level TEXT,
                        compliance_status TEXT,
                        total_controls INTEGER,
                        passed_controls INTEGER,
                        failed_controls INTEGER,
                        report_data TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_assessments_created_at
                    ON infrastructure_assessments(created_at DESC)
                """)
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to initialize Assessment SQLite database: {e}")
            finally:
                conn.close()

    def save_assessment(
        self,
        report_data: Dict[str, Any],
        project_name: Optional[str] = None,
        system_scope: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> str:
        aid = assessment_id or str(uuid.uuid4())[:8]
        now = time.time()
        
        # Extract summary metrics from report_data
        summary = report_data.get("summary", {})
        overall_score = float(summary.get("overall_score", report_data.get("compliance_score", 0.0)))
        risk_level = str(summary.get("overall_risk", report_data.get("risk_level", "Medium")))
        compliance_status = str(summary.get("status", "Completed"))
        total_controls = int(summary.get("total_controls", len(report_data.get("controls", []))))
        passed_controls = int(summary.get("passed", 0))
        failed_controls = int(summary.get("failed", 0))
        pname = project_name or report_data.get("project_name") or f"Assessment-{aid}"
        scope = system_scope or report_data.get("system_scope") or "General Infrastructure"

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO infrastructure_assessments (
                        id, project_name, system_scope, overall_score, risk_level,
                        compliance_status, total_controls, passed_controls, failed_controls,
                        report_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    aid,
                    pname,
                    scope,
                    overall_score,
                    risk_level,
                    compliance_status,
                    total_controls,
                    passed_controls,
                    failed_controls,
                    json.dumps(report_data, ensure_ascii=False),
                    now
                ))
                conn.commit()
                logger.info(f"Saved assessment {aid} to SQLite successfully (Score: {overall_score})")
                return aid
            except Exception as e:
                logger.error(f"Failed to save assessment {aid} to SQLite: {e}")
                return aid
            finally:
                conn.close()

    def list_assessments(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, project_name, system_scope, overall_score, risk_level,
                           compliance_status, total_controls, passed_controls, failed_controls,
                           created_at
                    FROM infrastructure_assessments
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "id": row["id"],
                        "project_name": row["project_name"],
                        "system_scope": row["system_scope"],
                        "overall_score": row["overall_score"],
                        "risk_level": row["risk_level"],
                        "compliance_status": row["compliance_status"],
                        "total_controls": row["total_controls"],
                        "passed_controls": row["passed_controls"],
                        "failed_controls": row["failed_controls"],
                        "created_at": row["created_at"]
                    })
                return results
            except Exception as e:
                logger.error(f"Failed to list assessments from SQLite: {e}")
                return []
            finally:
                conn.close()

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM infrastructure_assessments WHERE id = ?
                """, (assessment_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                report = json.loads(row["report_data"]) if row["report_data"] else {}
                return {
                    "id": row["id"],
                    "project_name": row["project_name"],
                    "system_scope": row["system_scope"],
                    "overall_score": row["overall_score"],
                    "risk_level": row["risk_level"],
                    "compliance_status": row["compliance_status"],
                    "total_controls": row["total_controls"],
                    "passed_controls": row["passed_controls"],
                    "failed_controls": row["failed_controls"],
                    "created_at": row["created_at"],
                    "report_data": report
                }
            except Exception as e:
                logger.error(f"Failed to get assessment {assessment_id} from SQLite: {e}")
                return None
            finally:
                conn.close()

    def delete_assessment(self, assessment_id: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM infrastructure_assessments WHERE id = ?", (assessment_id,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to delete assessment {assessment_id}: {e}")
                return False
            finally:
                conn.close()


# Global singleton
assessment_store = AssessmentStore()
