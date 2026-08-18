"""Persistent Session Store — SQLite database with user-scoped chat history and multi-device persistence."""

import asyncio
import os
import sqlite3
import time
import logging
import threading
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "/data")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
DB_PATH = os.path.join(SESSIONS_DIR, "chat_history.db")
SESSION_TTL = 30 * 86400  # 30 days persistent history
MAX_HISTORY_PER_SESSION = 50


class SessionStore:
    _lock = threading.RLock()

    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        model TEXT,
                        provider TEXT,
                        timestamp REAL NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id 
                    ON chat_messages(session_id)
                """)
                # Automatic schema migrations for existing databases
                cursor.execute("PRAGMA table_info(sessions)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "user_id" not in columns:
                    cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
                    logger.info("Migrated SQLite sessions table: added user_id column")
                if "title" not in columns:
                    cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
                    logger.info("Migrated SQLite sessions table: added title column")

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                    ON sessions(user_id)
                """)

                cursor.execute("PRAGMA table_info(chat_messages)")
                msg_columns = [row["name"] for row in cursor.fetchall()]
                if "model" not in msg_columns:
                    cursor.execute("ALTER TABLE chat_messages ADD COLUMN model TEXT")
                if "provider" not in msg_columns:
                    cursor.execute("ALTER TABLE chat_messages ADD COLUMN provider TEXT")
                if "metadata" not in msg_columns:
                    cursor.execute("ALTER TABLE chat_messages ADD COLUMN metadata TEXT")

                conn.commit()
            except Exception as e:
                logger.error(f"Failed to initialize SQLite database in SessionStore: {e}")
            finally:
                conn.close()

    def save(self, session_id: str, data: dict, user_id: Optional[str] = None):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = time.time()
                created_at = data.get("created_at", now)
                updated_at = data.get("updated_at", now)
                title = data.get("title")

                # If title is not set, derive from first user message
                messages = data.get("messages", [])
                if not title and messages:
                    for m in messages:
                        if m.get("role") == "user" and m.get("content"):
                            title = str(m["content"])[:60].strip()
                            break

                # Upsert session metadata
                cursor.execute("""
                    INSERT INTO sessions (session_id, user_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET 
                        updated_at = ?,
                        title = COALESCE(?, title),
                        user_id = COALESCE(?, user_id)
                """, (session_id, user_id, title, created_at, updated_at, updated_at, title, user_id))

                # Clear old messages for this session
                cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

                # Insert new messages
                for msg in messages:
                    msg_time = msg.get("timestamp", now)
                    if isinstance(msg_time, str):
                        try:
                            msg_time = float(msg_time)
                        except ValueError:
                            msg_time = now
                    cursor.execute("""
                        INSERT INTO chat_messages (session_id, role, content, model, provider, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        msg.get("role"),
                        msg.get("content") if isinstance(msg.get("content"), str) else str(msg.get("content") or ""),
                        msg.get("model"),
                        msg.get("provider"),
                        msg_time
                    ))

                # Keep only MAX_HISTORY_PER_SESSION messages
                cursor.execute("""
                    DELETE FROM chat_messages 
                    WHERE session_id = ? 
                      AND id NOT IN (
                          SELECT id FROM chat_messages 
                          WHERE session_id = ? 
                          ORDER BY timestamp DESC 
                          LIMIT ?
                      )
                """, (session_id, session_id, MAX_HISTORY_PER_SESSION))

                conn.commit()
            except Exception as e:
                logger.error(f"Failed to save session {session_id} to SQLite: {e}")
            finally:
                conn.close()

    def load(self, session_id: str, user_id: Optional[str] = None) -> dict:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT session_id, user_id, title, created_at, updated_at FROM sessions WHERE session_id = ? AND (user_id = ? OR user_id IS NULL)",
                    (session_id, user_id)
                )
            else:
                cursor.execute(
                    "SELECT session_id, user_id, title, created_at, updated_at FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
            session_row = cursor.fetchone()
            if not session_row:
                return {}

            created_at, updated_at = session_row["created_at"], session_row["updated_at"]
            title = session_row["title"] or "Cuộc trò chuyện"
            s_user_id = session_row["user_id"]

            # Load messages
            cursor.execute("""
                SELECT role, content, model, provider, timestamp FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,))
            rows = cursor.fetchall()

            messages = []
            for r in rows:
                messages.append({
                    "role": r["role"],
                    "content": r["content"],
                    "model": r["model"],
                    "provider": r["provider"],
                    "timestamp": r["timestamp"]
                })

            return {
                "id": session_id,
                "session_id": session_id,
                "user_id": s_user_id,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "messages": messages,
                "count": len(messages)
            }
        except Exception as e:
            logger.warning(f"Failed to load session {session_id} from SQLite: {e}")
            return {}
        finally:
            conn.close()

    def delete(self, session_id: str, user_id: Optional[str] = None):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("DELETE FROM sessions WHERE session_id = ? AND (user_id = ? OR user_id IS NULL)", (session_id, user_id))
                else:
                    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
                conn.commit()
            except Exception as e:
                logger.warning(f"Failed to delete session {session_id} from SQLite: {e}")
            finally:
                conn.close()

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.load(session_id).get("messages", [])

    def add_message(self, session_id: str, role: str, content: str, user_id: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = time.time()

                # Derive title if this is first message
                title = None
                if role == "user":
                    title = content[:60].strip()

                # Upsert session
                cursor.execute("""
                    INSERT INTO sessions (session_id, user_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET 
                        updated_at = ?,
                        title = COALESCE(?, title),
                        user_id = COALESCE(?, user_id)
                """, (session_id, user_id, title, now, now, now, title, user_id))

                # Insert new message
                cursor.execute("""
                    INSERT INTO chat_messages (session_id, role, content, model, provider, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, role, content, model, provider, now))

                # Keep only MAX_HISTORY_PER_SESSION messages
                cursor.execute("""
                    DELETE FROM chat_messages 
                    WHERE session_id = ? 
                      AND id NOT IN (
                          SELECT id FROM chat_messages 
                          WHERE session_id = ? 
                          ORDER BY timestamp DESC 
                          LIMIT ?
                      )
                """, (session_id, session_id, MAX_HISTORY_PER_SESSION))

                conn.commit()
            except Exception as e:
                logger.error(f"Failed to add message to session {session_id} in SQLite: {e}")
            finally:
                conn.close()

    def get_context_messages(self, session_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for LLM context (role + content only)."""
        history = self.get_history(session_id)
        recent = history[-max_messages:] if len(history) > max_messages else history
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    async def add_message_async(self, session_id: str, role: str, content: str, user_id: Optional[str] = None):
        await asyncio.to_thread(self.add_message, session_id, role, content, user_id)

    def clear_history(self, session_id: str, user_id: Optional[str] = None):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
                cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (time.time(), session_id))
                conn.commit()
            except Exception as e:
                logger.warning(f"Failed to clear history for session {session_id} in SQLite: {e}")
            finally:
                conn.close()

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        conn = self._get_connection()
        sessions = []
        try:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT s.session_id, s.user_id, s.title, s.created_at, s.updated_at, COUNT(m.id) as messages_count
                    FROM sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    WHERE s.user_id = ? OR s.user_id IS NULL
                    GROUP BY s.session_id
                    ORDER BY s.updated_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT s.session_id, s.user_id, s.title, s.created_at, s.updated_at, COUNT(m.id) as messages_count
                    FROM sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    GROUP BY s.session_id
                    ORDER BY s.updated_at DESC
                """)
            rows = cursor.fetchall()
            for r in rows:
                title = r["title"]
                if not title:
                    title = f"Chat {time.strftime('%d/%m %H:%M', time.localtime(r['created_at']))}"
                sessions.append({
                    "id": r["session_id"],
                    "session_id": r["session_id"],
                    "user_id": r["user_id"],
                    "title": title,
                    "count": r["messages_count"],
                    "messages_count": r["messages_count"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "time": time.strftime("%d/%m/%Y, %H:%M", time.localtime(r["updated_at"]))
                })
        except Exception as e:
            logger.warning(f"List sessions error in SQLite: {e}")
        finally:
            conn.close()
        return sessions
