import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.projects import Project
from app.infrastructure.migrations import migrate


class SqliteProjectRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        migrate(self._database_path)

    def list(self) -> list[Project]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [self._to_project(row) for row in rows]

    def get(self, project_id: UUID) -> Project | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (str(project_id),)).fetchone()
        return self._to_project(row) if row else None

    def create(self, name: str, description: str | None) -> Project:
        now = datetime.now(timezone.utc)
        project = Project(uuid4(), name, description, now, now)
        with self._connect() as connection:
            connection.execute("INSERT INTO projects VALUES (?, ?, ?, ?, ?)", self._values(project))
        return project

    def update(self, project_id: UUID, name: str | None, description: str | None, update_description: bool) -> Project | None:
        project = self.get(project_id)
        if project is None:
            return None
        updated = Project(project.id, name if name is not None else project.name,
                          description if update_description else project.description,
                          project.created_at, datetime.now(timezone.utc))
        with self._connect() as connection:
            connection.execute("UPDATE projects SET name=?, description=?, updated_at=? WHERE id=?",
                               (updated.name, updated.description, updated.updated_at.isoformat(), str(project_id)))
        return updated

    def delete(self, project_id: UUID) -> bool:
        with self._connect() as connection:
            return connection.execute("DELETE FROM projects WHERE id = ?", (str(project_id),)).rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _values(project: Project) -> tuple[str, str, str | None, str, str]:
        return (str(project.id), project.name, project.description, project.created_at.isoformat(), project.updated_at.isoformat())

    @staticmethod
    def _to_project(row: sqlite3.Row) -> Project:
        return Project(UUID(row["id"]), row["name"], row["description"], datetime.fromisoformat(row["created_at"]), datetime.fromisoformat(row["updated_at"]))
