"""Low-overhead structured operational logging written asynchronously to disk."""
from __future__ import annotations

import json
import logging
import queue
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from uuid import UUID


class JsonLineFormatter(logging.Formatter):
    """Emit one privacy-safe JSON record per line for efficient local inspection."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", "application"),
            "message": record.getMessage(),
            "project_id": getattr(record, "project_id", None),
            "document_id": getattr(record, "document_id", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "details": getattr(record, "details", {}),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


class OperationalLogger:
    """Queues structured events so caller threads never wait on file I/O."""

    def __init__(self, data_dir: Path, level: str = "INFO"):
        log_directory = data_dir / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        self.path = log_directory / "document-intelligence.jsonl"
        self._queue: queue.SimpleQueue[logging.LogRecord | None] = queue.SimpleQueue()
        self._logger = logging.getLogger("document_intelligence.operations")
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self._logger.handlers.clear()
        self._logger.propagate = False
        self._logger.addHandler(QueueHandler(self._queue))
        self._root = logging.getLogger()
        self._root_handler = QueueHandler(self._queue)
        self._root.addHandler(self._root_handler)
        file_handler = RotatingFileHandler(self.path, maxBytes=10 * 1024 * 1024,
                                           backupCount=5, encoding="utf-8")
        file_handler.setFormatter(JsonLineFormatter())
        self._listener = QueueListener(self._queue, file_handler, respect_handler_level=True)
        self._listener.start()

    def record(self, project_id: UUID, action: str, message: str, *, details: dict | None = None,
               document_id: UUID | None = None, duration_ms: int | None = None,
               level: str = "info") -> None:
        severity = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(severity, message, extra={
            "event": action,
            "project_id": str(project_id),
            "document_id": str(document_id) if document_id else None,
            "duration_ms": duration_ms,
            "details": details or {},
        })

    def close(self) -> None:
        self._root.removeHandler(self._root_handler)
        self._listener.stop()