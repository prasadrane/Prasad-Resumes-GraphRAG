"""
fts_search.py — Embedded SQLite Full-Text Search (FTS5) Engine.

Provides sub-millisecond, zero-dependency, ranked full-text search over resume entities
and stories with BM25 relevance ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional

from src.config import ROOT_DIR, OUTPUT_DIR_PATH

logger = logging.getLogger(__name__)


@dataclass
class FTSResult:
    """FTS5 search result item."""
    title: str
    content: str
    rank: float = 0.0


class FTS5SearchEngine:
    """
    SQLite FTS5 Full-Text Search indexer and query engine.
    """

    CREATE_TABLE_SQL = """
        CREATE VIRTUAL TABLE IF NOT EXISTS resume_fts USING fts5(
            title,
            content,
            tokenize='porter'
        );
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (OUTPUT_DIR_PATH / "resume_fts.db")
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite FTS5 virtual table."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(self.CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def index_documents(self, documents: List[Dict[str, str]]) -> int:
        """Clear and re-index a list of document dicts with 'title' and 'content'."""
        if not documents:
            return 0

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("DELETE FROM resume_fts;")
            for doc in documents:
                title = doc.get("title", "General")
                content = doc.get("content", "")
                if content:
                    conn.execute(
                        "INSERT INTO resume_fts(title, content) VALUES (?, ?);",
                        (title, content),
                    )
            conn.commit()
            return len(documents)
        finally:
            conn.close()

    def search(self, query: str, limit: int = 5) -> List[FTSResult]:
        """Execute FTS5 search returning matching documents ordered by BM25 rank."""
        if not query or not query.strip():
            return []

        # Sanitize query for FTS5 syntax (escape special chars)
        clean_q = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
        if not clean_q:
            return []

        fts_query = " ".join(f'"{token}"' for token in clean_q.split() if token)

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                SELECT title, content, bm25(resume_fts) AS rank
                FROM resume_fts
                WHERE resume_fts MATCH ?
                ORDER BY rank
                LIMIT ?;
                """,
                (fts_query, limit),
            )
            rows = cursor.fetchall()
            return [FTSResult(title=r[0], content=r[1], rank=float(r[2])) for r in rows]
        except Exception as exc:
            logger.warning("[FTS5] Search error for query '%s': %s", query, exc)
            return []
        finally:
            conn.close()
