"""
SQLite 기반 저장소. 파일 하나(app.db)로 돌아가서 별도 DB 설치가 필요 없음.
나중에 원진이 진짜 DB(Postgres/Supabase 등)로 옮길 때는 이 파일의 함수
시그니처만 유지하면 main.py는 거의 안 건드려도 됨.
"""

import sqlite3
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

DB_PATH = Path(__file__).parent / "app.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            rent_due_date TEXT,
            rent_amount TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(room_id, name)
        );
        CREATE TABLE IF NOT EXISTS chores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            assignee TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            source TEXT DEFAULT 'manual'
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    # 데모 방 하나 미리 심어두기 -> 처음 켰을 때부터 화면에 뭔가 보이게
    row = c.execute("SELECT id FROM rooms WHERE code = ?", ("demo",)).fetchone()
    if not row:
        due = (date.today() + timedelta(days=6)).isoformat()
        c.execute(
            "INSERT INTO rooms (code, rent_due_date, rent_amount) VALUES (?, ?, ?)",
            ("demo", due, "$800"),
        )
        room_id = c.lastrowid
        c.execute(
            "INSERT INTO chores (room_id, title, assignee, due_date, completed, source) "
            "VALUES (?,?,?,?,?,?)",
            (room_id, "설거지", "원진", date.today().isoformat(), 0, "manual"),
        )
        c.execute(
            "INSERT INTO chores (room_id, title, assignee, due_date, completed, source) "
            "VALUES (?,?,?,?,?,?)",
            (room_id, "쓰레기 버리기", "성진", date.today().isoformat(), 1, "manual"),
        )
        conn.commit()
    conn.close()


def get_or_create_room(code: str) -> sqlite3.Row:
    conn = get_conn()
    row = conn.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
    if not row:
        conn.execute("INSERT INTO rooms (code) VALUES (?)", (code,))
        conn.commit()
        row = conn.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()
    conn.close()
    return row


def get_or_create_user(room_id: int, name: str) -> sqlite3.Row:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE room_id = ? AND name = ?", (room_id, name)
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO users (room_id, name) VALUES (?, ?)", (room_id, name)
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE room_id = ? AND name = ?", (room_id, name)
        ).fetchone()
    conn.close()
    return row


def add_message(room_id: int, sender: str, content: str) -> sqlite3.Row:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO messages (room_id, sender, content) VALUES (?, ?, ?)",
        (room_id, sender, content),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row


def get_messages(room_id: int, limit: int = 100):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE room_id = ? ORDER BY id ASC LIMIT ?",
        (room_id, limit),
    ).fetchall()
    conn.close()
    return rows


def add_chore(room_id: int, title: str, assignee: Optional[str], due_date: Optional[str], source: str = "manual") -> sqlite3.Row:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO chores (room_id, title, assignee, due_date, source) VALUES (?,?,?,?,?)",
        (room_id, title, assignee, due_date, source),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chores WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row


def get_chores(room_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chores WHERE room_id = ? ORDER BY completed ASC, id DESC", (room_id,)
    ).fetchall()
    conn.close()
    return rows


def complete_chore(chore_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    conn.execute("UPDATE chores SET completed = 1 WHERE id = ?", (chore_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM chores WHERE id = ?", (chore_id,)).fetchone()
    conn.close()
    return row


def set_rent(room_id: int, due_date: str, amount: str):
    conn = get_conn()
    conn.execute(
        "UPDATE rooms SET rent_due_date = ?, rent_amount = ? WHERE id = ?",
        (due_date, amount, room_id),
    )
    conn.commit()
    conn.close()
