"""
conversation_store.py — SQLite-based conversation memory for GraphRAG Q&A sessions.

Each session gets a unique conversation_id with row-per-message storage.
Conversation history is limited to the most recent *limit* messages so the
system prompt stays within token budgets.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class ConversationStore:
    """Thread-safe-ish SQLite store for per-session conversation histories."""

    CREATE_CONVERSATIONS_SQL = """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    CREATE_MESSAGES_SQL = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """
    INSERT_MESSAGE_SQL = """
        INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)
    """
    GET_HISTORY_SQL = """
        SELECT role, content FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Default to output dir — same place GraphRAG artefacts live.
            root = Path(os.environ.get("ROOT_DIR", "."))
            self.db_path = root / "output" / "conversations.db"
        self._ensure_dir()
        self._init_db()

    # ── public API ────────────────────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str) -> int:
        """Record one message in the conversation. Returns message id."""
        conn = self._conn()
        try:
            conv_id = self._get_or_create_conversation(conn, session_id)
            cursor = conn.execute(self.INSERT_MESSAGE_SQL, (conv_id, role, content))
            conn.commit()
            return cursor.lastrowid  # type: ignore[attr-defined]
        finally:
            conn.close()

    def get_history(
        self, session_id: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        """Return recent conversation history as ordered list of dicts."""
        conn = self._conn()
        try:
            # Resolve session_id → conversation_id
            cursor = conn.execute(
                "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return []
            conv_id = row["id"]
            cursor = conn.execute(
                self.GET_HISTORY_SQL,
                (conv_id, limit),
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        finally:
            conn.close()

    def clear_session(self, session_id: str) -> None:
        """Delete all messages and the conversation record for *session_id*."""
        conn = self._conn()
        try:
            conn.execute(
                "DELETE FROM conversations WHERE session_id = ?", (session_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def has_session(self, session_id: str) -> bool:
        """Check whether a session already exists."""
        conn = self._conn()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM conversations WHERE session_id = ?", (session_id,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    # ── internal helpers ──────────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        conn = self._conn()
        try:
            conn.execute(self.CREATE_CONVERSATIONS_SQL)
            conn.execute(self.CREATE_MESSAGES_SQL)
            conn.commit()
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        """Open a new connection each call — SQLite supports concurrent readers."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _get_or_create_conversation(
        conn: sqlite3.Connection, session_id: str
    ) -> int:
        cursor = conn.execute(
            "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]  # type: ignore[no-any-return]
        cursor = conn.execute(
            "INSERT INTO conversations (session_id) VALUES (?)", (session_id,)
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[attr-defined]


# ── singleton helper ────────────────────────────────────────────────────────

_instance: Optional["ConversationStore"] = None


def get_conversation_store(db_path: Optional[str] = None) -> "ConversationStore":
    """Return a shared ConversationStore instance (singleton)."""
    global _instance
    if _instance is None:
        _instance = ConversationStore(db_path=db_path)
    return _instance


def reset_conversation_store() -> None:
    """Reset singleton — useful for tests."""
    global _instance
    _instance = None
