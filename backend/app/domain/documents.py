from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Document:
    id: UUID
    project_id: UUID
    display_name: str
    original_filename: str
    file_type: str
    size_bytes: int
    content_hash: str
    status: str
    stage: str
    error_code: str | None
    error_message: str | None
    page_count: int | None
    original_name: str
    created_at: datetime
    updated_at: datetime


class DocumentError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
