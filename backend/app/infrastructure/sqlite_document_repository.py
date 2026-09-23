import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.domain.documents import Document
from app.infrastructure.migrations import migrate


class SqliteDocumentRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        migrate(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _document(row: sqlite3.Row) -> Document:
        return Document(
            UUID(row["id"]), UUID(row["project_id"]), row["display_name"],
            row["original_filename"], row["file_type"], row["size_bytes"],
            row["content_hash"], row["status"], row["stage"], row["error_code"],
            row["error_message"], row["page_count"], row["original_name"],
            datetime.fromisoformat(row["created_at"]), datetime.fromisoformat(row["updated_at"]),
        )

    def create(self, document: Document) -> None:
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(document.id), str(document.project_id), document.display_name,
                document.original_filename, document.file_type, document.size_bytes,
                document.content_hash, document.status, document.stage, document.error_code,
                document.error_message, document.page_count, document.original_name,
                document.created_at.isoformat(), document.updated_at.isoformat(),
            ))

    def list(self, project_id: UUID) -> list[Document]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC", (str(project_id),)).fetchall()
        return [self._document(row) for row in rows]

    def get(self, project_id: UUID, document_id: UUID) -> Document | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE project_id=? AND id=?", (str(project_id), str(document_id))).fetchone()
        return self._document(row) if row else None

    def find_hash(self, project_id: UUID, digest: str) -> Document | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE project_id=? AND content_hash=?", (str(project_id), digest)).fetchone()
        return self._document(row) if row else None

    def update(self, project_id: UUID, document_id: UUID, status: str, stage: str, error_code: str | None = None, error_message: str | None = None, page_count: int | None = None) -> None:
        with self._connect() as connection:
            connection.execute("""
                UPDATE documents SET status=?, stage=?, error_code=?, error_message=?, page_count=?, updated_at=?
                WHERE project_id=? AND id=?
            """, (status, stage, error_code, error_message, page_count, datetime.now(timezone.utc).isoformat(), str(project_id), str(document_id)))

    def delete(self, project_id: UUID, document_id: UUID) -> bool:
        with self._connect() as connection:
            return connection.execute("DELETE FROM documents WHERE project_id=? AND id=?", (str(project_id), str(document_id))).rowcount > 0

    def interrupt_incomplete(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                UPDATE documents SET status='failed', stage='interrupted', error_code='INTERRUPTED',
                error_message='Processing stopped before completion. Retry to continue.', updated_at=?
                WHERE status='processing'
            """, (datetime.now(timezone.utc).isoformat(),))
