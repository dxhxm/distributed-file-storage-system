"""
user_storage.py
===============
SQLite persistence service for the authentication and user management schema.
Implements the 'users' table alongside existing cluster metadata per Section 19/26:
- id: TEXT PRIMARY KEY (UUID4)
- username: TEXT UNIQUE NOT NULL
- hashed_password: TEXT NOT NULL (bcrypt hash)
- role: TEXT NOT NULL (USER, ADMIN, SYSTEM)
- created_at: TEXT NOT NULL (ISO 8601 UTC string)
- is_active: INTEGER NOT NULL DEFAULT 1 (Boolean integer)
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.user_model import Role, User


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Resolves the database file path based on STORAGE_DIR environment or default."""
    if custom_path:
        db_dir = os.path.dirname(custom_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        return custom_path

    storage_dir = os.environ.get("STORAGE_DIR", "Storage")
    os.makedirs(storage_dir, exist_ok=True)
    return os.path.join(storage_dir, "metadata.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Creates a configured sqlite3 connection with Row factory enabled."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initializes the SQLite database and ensures the 'users' table exists
    with unique constraints and required column schema.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'USER',
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
            """)
    finally:
        conn.close()


def create_user(
    user: User,
    user_id: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inserts a new user record into the 'users' database store.

    Args:
        user: Validated User Pydantic model instance.
        user_id: Optional explicit user ID; defaults to generated UUID4.
        db_path: Optional SQLite DB path override.

    Returns:
        Dictionary representing the persisted user record.

    Raises:
        ValueError: If a user with the same username already exists.
    """
    init_db(db_path)
    record_id = user_id or str(uuid.uuid4())
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    
    if isinstance(user.created_at, datetime):
        created_at_str = user.created_at.isoformat()
    else:
        created_at_str = datetime.now(timezone.utc).isoformat()

    is_active_int = 1 if user.is_active else 0

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, username, hashed_password, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (record_id, user.username, user.hashed_password, role_str, created_at_str, is_active_int)
            )
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: users.username" in str(e) or "unique" in str(e).lower():
            raise ValueError(f"User with username '{user.username}' already exists") from e
        raise
    finally:
        conn.close()

    return {
        "id": record_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "role": role_str,
        "created_at": created_at_str,
        "is_active": bool(is_active_int)
    }


def get_user_by_username(username: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single user record by unique username."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password, role, created_at, is_active FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "hashed_password": row["hashed_password"],
            "role": row["role"],
            "created_at": row["created_at"],
            "is_active": bool(row["is_active"])
        }
    finally:
        conn.close()


def get_user_by_id(user_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single user record by primary key id."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password, role, created_at, is_active FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "hashed_password": row["hashed_password"],
            "role": row["role"],
            "created_at": row["created_at"],
            "is_active": bool(row["is_active"])
        }
    finally:
        conn.close()


def list_users(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns a list of all user records in the database store."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password, role, created_at, is_active FROM users ORDER BY created_at ASC")
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "username": r["username"],
                "hashed_password": r["hashed_password"],
                "role": r["role"],
                "created_at": r["created_at"],
                "is_active": bool(r["is_active"])
            }
            for r in rows
        ]
    finally:
        conn.close()


def delete_user(username: str, db_path: Optional[str] = None) -> bool:
    """Deletes a user record by username. Returns True if a record was deleted, False otherwise."""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return cursor.rowcount > 0
    finally:
        conn.close()
