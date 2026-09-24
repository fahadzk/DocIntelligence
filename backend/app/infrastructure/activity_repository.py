"""Durable, project-scoped operational activity records."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.infrastructure.migrations import migrate


class ActivityRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        migrate(database_path)

    def record(self, project_id: UUID, action: str, message: str,
               details: dict | None = None, document_id: UUID | None = None,
               duration_ms: int | None = None, level: str = "info") -> None:
        with sqlite3.connect(self.database_path, timeout=30) as connection:
            connection.execute("""
                INSERT INTO activity_logs (id, project_id, document_id, action, level,
                    message, details, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(uuid4()), str(project_id), str(document_id) if document_id else None,
                  action, level, message, json.dumps(details or {}, ensure_ascii=False),
                  duration_ms, datetime.now(timezone.utc).isoformat()))

    def list(self, project_id: UUID, limit: int = 200) -> list[dict]:
        with sqlite3.connect(self.database_path, timeout=30) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT id, project_id, document_id, action, level, message, details,
                    duration_ms, created_at
                FROM activity_logs WHERE project_id=?
                ORDER BY created_at DESC LIMIT ?
            """, (str(project_id), max(1, min(limit, 500)))).fetchall()
        return [{**dict(row), "details": json.loads(row["details"])} for row in rows]

    def purge_document(self, project_id: UUID, document_id: UUID) -> None:
        # Keep a project audit trail but detach deleted document records.
        with sqlite3.connect(self.database_path, timeout=30) as connection:
            connection.execute("UPDATE activity_logs SET document_id=NULL WHERE project_id=? AND document_id=?",
                               (str(project_id), str(document_id)))
