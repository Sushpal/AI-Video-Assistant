import sqlite3
import bcrypt
import os
import json
import shutil
from datetime import datetime

DB_PATH = "meeting_assistant.db"
CHROMA_DIR = "vector_db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            language TEXT NOT NULL,
            transcript TEXT NOT NULL,
            summary TEXT NOT NULL,
            action_items TEXT NOT NULL,
            key_decisions TEXT NOT NULL,
            open_questions TEXT NOT NULL,
            collection_name TEXT NOT NULL,
            chat_history TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
    print("DB initialized.")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_user(username: str, password: str) -> bool:
    try:
        conn = get_connection()

        hashed_password = hash_password(password)

        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (
                username.strip().lower(),
                hashed_password,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

        print(f"User created: {username}")
        return True

    except sqlite3.IntegrityError:
        print(f"User already exists: {username}")
        return False


def verify_user(username: str, password: str) -> dict | None:
    conn = get_connection()

    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username.strip().lower(),)
    ).fetchone()

    conn.close()

    if row and bcrypt.checkpw(
        password.encode(),
        row["password_hash"].encode()
    ):
        return {
            "id": row["id"],
            "username": row["username"]
        }

    return None


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username.strip().lower(),)
    ).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "username": row["username"]}
    return None


def save_session(
    session_id: str,
    user_id: int,
    title: str,
    source: str,
    language: str,
    transcript: str,
    summary: str,
    action_items: str,
    key_decisions: str,
    open_questions: str,
    collection_name: str,
) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO sessions 
        (id, user_id, title, source, language, transcript, summary,
         action_items, key_decisions, open_questions, collection_name, chat_history, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, user_id, title, source, language, transcript,
            summary, action_items, key_decisions, open_questions,
            collection_name, "[]", datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()
    print(f"Session saved: {session_id}")


def load_session(session_id: str, user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()
    conn.close()
    
    if row:
        # SAFETY FIX: Handling potential JSON errors
        try:
            history = json.loads(row["chat_history"])
        except (json.JSONDecodeError, TypeError):
            history = []

        return {
            "id": row["id"],
            "title": row["title"],
            "source": row["source"],
            "language": row["language"],
            "transcript": row["transcript"],
            "summary": row["summary"],
            "action_items": row["action_items"],
            "key_decisions": row["key_decisions"],
            "open_questions": row["open_questions"],
            "collection_name": row["collection_name"],
            "chat_history": history,
            "created_at": row["created_at"],
        }
    return None


def get_user_sessions(user_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, source, language, created_at FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_chat_history(session_id: str, chat_history: list) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET chat_history = ? WHERE id = ?",
        (json.dumps(chat_history), session_id)
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str, user_id: int) -> None:
    conn = get_connection()

    # collection_name teesuko before delete
    row = conn.execute(
        "SELECT collection_name FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    ).fetchone()

    conn.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    conn.commit()
    conn.close()

    # SAFETY FIX: Check if row exists before accessing it and handle rmtree errors
    if row and row["collection_name"]:
        collection_dir = os.path.join(CHROMA_DIR, row["collection_name"])
        if os.path.exists(collection_dir):
            try:
                shutil.rmtree(collection_dir)
                print(f"ChromaDB collection deleted: {row['collection_name']}")
            except Exception as e:
                print(f"Cleanup warning: Could not remove directory {collection_dir} - {e}")

    print(f"Session deleted: {session_id}")