"""Project-scoped passage and FTS persistence."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.infrastructure.migrations import migrate


class SearchRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        migrate(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def status(self, project_id: str) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT d.id AS document_id, d.display_name, d.status AS document_status,
                    i.status, i.stage, i.error_message, i.index_version,
                    i.content_hash AS indexed_hash, i.updated_at
                FROM documents d LEFT JOIN document_indexes i ON i.document_id=d.id
                WHERE d.project_id=? ORDER BY d.created_at DESC
            """, (project_id,)).fetchall()
        return [dict(row) for row in rows]

    def rebuild_fts(self) -> None:
        """FTS is derived entirely from passages and can be recreated safely."""
        with self.connect() as connection:
            connection.execute("DROP TABLE IF EXISTS passages_fts")
            connection.execute("CREATE VIRTUAL TABLE passages_fts USING fts5(id UNINDEXED, project_id UNINDEXED, text, tokenize='unicode61')")
            connection.execute("INSERT INTO passages_fts (id, project_id, text) SELECT id, project_id, text FROM passages")

    def mark(self, project_id: str, document_id: str, status: str, stage: str,
             version: str, content_hash: str, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO document_indexes VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    status=excluded.status, stage=excluded.stage,
                    index_version=excluded.index_version, content_hash=excluded.content_hash,
                    error_message=excluded.error_message, updated_at=excluded.updated_at
            """, (document_id, project_id, status, stage, version, content_hash,
                  error, datetime.now(timezone.utc).isoformat()))

    def replace(self, project_id: str, document_id: str, passages: list[dict],
                version: str, content_hash: str) -> None:
        with self.connect() as connection:
            ids = [row[0] for row in connection.execute(
                "SELECT id FROM passages WHERE project_id=? AND document_id=?",
                (project_id, document_id))]
            connection.executemany("DELETE FROM passages_fts WHERE id=?", [(item,) for item in ids])
            connection.execute("DELETE FROM passages WHERE project_id=? AND document_id=?", (project_id, document_id))
            connection.executemany("""
                INSERT INTO passages VALUES (:id, :project_id, :document_id, :segment_index,
                    :chunk_index, :label, :page_number, :paragraph_number,
                    :start_offset, :end_offset, :text, :content_hash, :index_version)
            """, passages)
            connection.executemany(
                "INSERT INTO passages_fts (id, project_id, text) VALUES (?, ?, ?)",
                [(item["id"], project_id, item["text"]) for item in passages])
            connection.execute("""
                INSERT INTO document_indexes VALUES (?, ?, 'ready', 'complete', ?, ?, NULL, ?)
                ON CONFLICT(document_id) DO UPDATE SET status='ready', stage='complete',
                    index_version=excluded.index_version, content_hash=excluded.content_hash,
                    error_message=NULL, updated_at=excluded.updated_at
            """, (document_id, project_id, version, content_hash,
                  datetime.now(timezone.utc).isoformat()))

    def delete(self, project_id: str, document_id: str) -> None:
        with self.connect() as connection:
            ids = [row[0] for row in connection.execute(
                "SELECT id FROM passages WHERE project_id=? AND document_id=?",
                (project_id, document_id))]
            connection.executemany("DELETE FROM passages_fts WHERE id=?", [(item,) for item in ids])
            connection.execute("DELETE FROM passages WHERE project_id=? AND document_id=?", (project_id, document_id))
            connection.execute("DELETE FROM document_indexes WHERE project_id=? AND document_id=?", (project_id, document_id))

    def get(self, project_id: str, passage_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("""
                SELECT p.*, d.display_name, d.file_type FROM passages p
                JOIN documents d ON d.id=p.document_id AND d.project_id=p.project_id
                JOIN document_indexes i ON i.document_id=d.id
                WHERE p.project_id=? AND p.id=? AND d.status='ready' AND i.status='ready'
                    AND i.index_version=p.index_version AND i.content_hash=d.content_hash
            """, (project_id, passage_id)).fetchone()
        return dict(row) if row else None

    def keyword(self, project_id: str, query: str, limit: int = 30) -> list[str]:
        import re
        terms = re.findall(r"\w+", query, re.UNICODE)[:12]
        if not terms:
            return []
        expression = " OR ".join(f'"{term}"' for term in terms)
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT f.id FROM passages_fts f
                JOIN passages p ON p.id=f.id AND p.project_id=f.project_id
                JOIN documents d ON d.id=p.document_id
                JOIN document_indexes i ON i.document_id=d.id
                WHERE passages_fts MATCH ? AND f.project_id=? AND d.status='ready'
                    AND i.status='ready' AND i.index_version=p.index_version
                    AND i.content_hash=d.content_hash
                ORDER BY bm25(passages_fts) LIMIT ?
            """, (expression, project_id, limit)).fetchall()
        return [row[0] for row in rows]

    def valid_ids(self, project_id: str) -> set[str]:
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT p.id FROM passages p JOIN documents d ON d.id=p.document_id
                JOIN document_indexes i ON i.document_id=d.id
                WHERE p.project_id=? AND d.status='ready' AND i.status='ready'
                    AND i.content_hash=d.content_hash AND i.index_version=p.index_version
            """, (project_id,)).fetchall()
        return {row[0] for row in rows}
