"""SQLite repository for dynamic security standard control descriptions.

Stores requirement and assessment criteria descriptions for ISO 27001, TCVN 11930,
and custom standards in SQLite database `/data/control_descriptions.db`.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_DIR = os.getenv("DATA_DIR", "/data")
DB_PATH = os.path.join(DB_DIR, "control_descriptions.db")
SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data_control_descriptions.json")


class ControlDescriptionsStore:
    """Thread-safe SQLite storage for security control descriptions."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._seed_if_empty()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS control_descriptions (
                    control_id TEXT PRIMARY KEY,
                    requirement_vi TEXT NOT NULL,
                    criteria_vi TEXT NOT NULL,
                    requirement_en TEXT NOT NULL,
                    criteria_en TEXT NOT NULL,
                    standard TEXT DEFAULT 'iso27001',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _seed_if_empty(self) -> None:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as count FROM control_descriptions")
            row = cur.fetchone()
            if row and row["count"] > 0:
                return

        if os.path.exists(SEED_PATH):
            try:
                with open(SEED_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                with self._get_conn() as conn:
                    for cid, item in data.items():
                        std = "tcvn11930" if cid.startswith("TCVN_") or cid.startswith("C.") else "iso27001"
                        conn.execute("""
                            INSERT OR REPLACE INTO control_descriptions 
                            (control_id, requirement_vi, criteria_vi, requirement_en, criteria_en, standard)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            cid,
                            item.get("requirement_vi", ""),
                            item.get("criteria_vi", ""),
                            item.get("requirement_en", ""),
                            item.get("criteria_en", ""),
                            std
                        ))
                    conn.commit()
                logger.info("Seeded %d control descriptions into SQLite database", len(data))
            except Exception as e:
                logger.error("Failed to seed control descriptions: %s", e)

    def get_all(self, locale: str = "vi", standard: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Return a mapping of control_id -> {requirement, criteria} for the requested locale."""
        query = "SELECT control_id, requirement_vi, criteria_vi, requirement_en, criteria_en, standard FROM control_descriptions"
        params: List[Any] = []
        if standard:
            query += " WHERE standard = ?"
            params.append(standard)

        result: Dict[str, Dict[str, str]] = {}
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            for row in cur.fetchall():
                cid = row["control_id"]
                if locale == "en":
                    req = row["requirement_en"] or row["requirement_vi"]
                    crit = row["criteria_en"] or row["criteria_vi"]
                else:
                    req = row["requirement_vi"]
                    crit = row["criteria_vi"]
                result[cid] = {
                    "requirement": req,
                    "criteria": crit,
                }
        return result

    def get_by_id(self, control_id: str, locale: str = "vi") -> Optional[Dict[str, str]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT control_id, requirement_vi, criteria_vi, requirement_en, criteria_en, standard
                FROM control_descriptions WHERE control_id = ?
            """, (control_id,))
            row = cur.fetchone()
            if not row:
                return None
            if locale == "en":
                req = row["requirement_en"] or row["requirement_vi"]
                crit = row["criteria_en"] or row["criteria_vi"]
            else:
                req = row["requirement_vi"]
                crit = row["criteria_vi"]
            return {"control_id": control_id, "requirement": req, "criteria": crit, "standard": row["standard"]}

    def save(
        self,
        control_id: str,
        requirement_vi: str,
        criteria_vi: str,
        requirement_en: str = "",
        criteria_en: str = "",
        standard: str = "iso27001"
    ) -> Dict[str, Any]:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO control_descriptions
                (control_id, requirement_vi, criteria_vi, requirement_en, criteria_en, standard, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(control_id) DO UPDATE SET
                    requirement_vi = excluded.requirement_vi,
                    criteria_vi = excluded.criteria_vi,
                    requirement_en = excluded.requirement_en,
                    criteria_en = excluded.criteria_en,
                    standard = excluded.standard,
                    updated_at = CURRENT_TIMESTAMP
            """, (control_id, requirement_vi, criteria_vi, requirement_en, criteria_en, standard))
            conn.commit()
        return {"control_id": control_id, "status": "saved"}

    def delete(self, control_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM control_descriptions WHERE control_id = ?", (control_id,))
            conn.commit()
            return cur.rowcount > 0


# Global singleton instance
control_descriptions_store = ControlDescriptionsStore()
