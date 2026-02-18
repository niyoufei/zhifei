from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

from passlib.context import CryptContext


AUTH_DIR = Path("backend/data/auth")
AUTH_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = AUTH_DIR / "users.db"

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            daily_limit INTEGER NOT NULL DEFAULT 50
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(email: str, password: str) -> Dict[str, Any]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    pwd = pwd_ctx.hash(password)
    cur.execute("INSERT INTO users(email, password_hash, balance, daily_limit) VALUES (?, ?, ?, ?)", (email, pwd, 0, 50))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return {"id": user_id, "email": email, "balance": 0, "daily_limit": 50}


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def verify_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    if not pwd_ctx.verify(password, user["password_hash"]):
        return None
    return user


def update_balance(user_id: int, delta: int) -> int:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (delta, user_id))
    conn.commit()
    cur.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return int(row["balance"]) if row else 0


def log_charge(user_id: int, action: str, cost: int):
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            cost INTEGER NOT NULL,
            ts TEXT NOT NULL
        )
        """
    )
    cur.execute(
        "INSERT INTO charges(user_id, action, cost, ts) VALUES (?, ?, ?, datetime('now'))",
        (user_id, action, cost),
    )
    conn.commit()
    conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def update_daily_limit(user_id: int, limit: int) -> int:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET daily_limit = ? WHERE id = ?", (limit, user_id))
    conn.commit()
    cur.execute("SELECT daily_limit FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return int(row["daily_limit"]) if row else 0


def list_users(limit: int = 100) -> list[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, email, balance, daily_limit FROM users ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_charges(limit: int = 100) -> list[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM charges ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_charges_by_user(user_id: int, limit: int = 100) -> list[dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM charges WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_user_actions_since(user_id: int, since_seconds: int) -> int:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as c FROM charges WHERE user_id = ? AND ts >= datetime('now', ?)",
        (user_id, f"-{int(since_seconds)} seconds"),
    )
    row = cur.fetchone()
    conn.close()
    return int(row["c"]) if row else 0
