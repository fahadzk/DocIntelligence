"""Versioned SQLite migrations that retain Phase 1 projects."""
import sqlite3
from pathlib import Path


def migrate(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "projects" not in tables:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute("PRAGMA user_version = 1")
        canonical = Path(__file__).resolve().parents[3] / "data" / "document_intelligence.sqlite3"
        legacy = Path(__file__).resolve().parents[2] / "data" / "document_intelligence.sqlite3"
        if database_path.resolve() == canonical and legacy.is_file() and "documents" not in tables:
            with sqlite3.connect(legacy) as old:
                for row in old.execute("SELECT id, name, description, created_at, updated_at FROM projects"):
                    connection.execute("INSERT OR IGNORE INTO projects VALUES (?, ?, ?, ?, ?)", row)
        if "documents" not in tables:
            connection.execute("""
                CREATE TABLE documents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    display_name TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT,
                    page_count INTEGER,
                    original_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, content_hash)
                )
            """)
            connection.execute("CREATE INDEX documents_project_idx ON documents(project_id, created_at)")
            connection.execute("PRAGMA user_version = 2")
        elif connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            connection.execute("PRAGMA user_version = 2")
