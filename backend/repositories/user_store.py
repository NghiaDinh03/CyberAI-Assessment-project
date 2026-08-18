"""Persistent User Store — SQLite database for user accounts and role-based access control."""

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "/data")
AUTH_DIR = os.path.join(DATA_DIR, "auth")
DB_PATH = os.path.join(AUTH_DIR, "users.db")


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generate salted PBKDF2-HMAC-SHA256 password hash."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return dk.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify password against stored hash."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(dk.hex(), password_hash)


class UserStore:
    _lock = threading.RLock()

    def __init__(self):
        os.makedirs(AUTH_DIR, exist_ok=True)
        self._init_db()
        self._seed_default_users()

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
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        full_name TEXT,
                        role TEXT NOT NULL DEFAULT 'user',
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
                """)
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to initialize Users SQLite database: {e}")
            finally:
                conn.close()

    def _seed_default_users(self):
        """Seed default admin and auditor accounts if they don't exist."""
        default_users = [
            {
                "username": "admin",
                "email": "admin@cyberai.vn",
                "password": "Admin@123456",
                "full_name": "CyberAI Administrator",
                "role": "admin"
            },
            {
                "username": "auditor",
                "email": "auditor@cyberai.vn",
                "password": "Auditor@123456",
                "full_name": "Lead ISO Auditor",
                "role": "auditor"
            }
        ]
        for u in default_users:
            if not self.get_user_by_username(u["username"]):
                self.create_user(
                    username=u["username"],
                    email=u["email"],
                    password=u["password"],
                    full_name=u["full_name"],
                    role=u["role"]
                )
                logger.info(f"Seeded default user '{u['username']}' ({u['role']})")

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user"
    ) -> Optional[Dict[str, Any]]:
        uid = str(uuid.uuid4())[:8]
        now = time.time()
        pwd_hash, salt = hash_password(password)
        fname = full_name or username

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash, salt, full_name, role, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (uid, username.strip().lower(), email.strip().lower() if email else None, pwd_hash, salt, fname, role, now, now))
                conn.commit()
                return self.get_user_by_id(uid)
            except sqlite3.IntegrityError as ie:
                logger.warning(f"User creation duplicate error: {ie}")
                return None
            except Exception as e:
                logger.error(f"Failed to create user {username}: {e}")
                return None
            finally:
                conn.close()

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username.strip().lower(), username.strip().lower()))
                row = cursor.fetchone()
                if not row:
                    return None
                return dict(row)
            except Exception as e:
                logger.error(f"Failed to get user by username {username}: {e}")
                return None
            finally:
                conn.close()

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email, full_name, role, is_active, created_at, updated_at FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return dict(row)
            except Exception as e:
                logger.error(f"Failed to get user by id {user_id}: {e}")
                return None
            finally:
                conn.close()

    def list_users(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email, full_name, role, is_active, created_at FROM users ORDER BY created_at ASC")
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"Failed to list users: {e}")
                return []
            finally:
                conn.close()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.get("is_active"):
            return None
        if verify_password(password, user["password_hash"], user["salt"]):
            # Return safe user dictionary without password hash / salt
            return {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "created_at": user["created_at"]
            }
        return None


# Global singleton
user_store = UserStore()
