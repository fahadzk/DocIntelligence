import hashlib
import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.domain.documents import Document, DocumentError
from app.infrastructure.extractors import Extractor
from app.infrastructure.sqlite_document_repository import SqliteDocumentRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository

logger = logging.getLogger(__name__)
SUPPORTED = {"pdf", "docx", "txt", "md"}


class DocumentService:
    def __init__(self, repository: SqliteDocumentRepository, projects: SqliteProjectRepository, extractor: Extractor, data_dir: Path, max_bytes: int):
        self.repository = repository
        self.projects = projects
        self.extractor = extractor
        self.storage = data_dir / "documents"
        self.max_bytes = max_bytes
        self.on_ready = None
        self.on_delete = None
        self.repository.interrupt_incomplete()

    def require_project(self, project_id: UUID) -> None:
        if self.projects.get(project_id) is None:
            raise DocumentError("PROJECT_NOT_FOUND", "The requested project could not be found.", 404)

    def _directory(self, project_id: UUID, document_id: UUID) -> Path:
        return self.storage / str(project_id) / str(document_id)

    def _original(self, document: Document) -> Path:
        return self._directory(document.project_id, document.id) / document.original_name

    def _content(self, document: Document) -> Path:
        return self._directory(document.project_id, document.id) / "content.json"

    def _checked(self, document: Document) -> Document:
        if document.status == "ready" and (not self._original(document).is_file() or not self._content(document).is_file()):
            self.repository.update(document.project_id, document.id, "failed", "integrity", "MISSING_ARTIFACT", "A stored file is missing. Remove and import this document again.")
            return self.repository.get(document.project_id, document.id)  # type: ignore[return-value]
        return document

    def list(self, project_id: UUID) -> list[Document]:
        self.require_project(project_id)
        return [self._checked(item) for item in self.repository.list(project_id)]

    def get(self, project_id: UUID, document_id: UUID) -> Document:
        self.require_project(project_id)
        document = self.repository.get(project_id, document_id)
        if document is None:
            raise DocumentError("DOCUMENT_NOT_FOUND", "The requested document could not be found.", 404)
        return self._checked(document)

    def register(self, project_id: UUID, upload: UploadFile) -> Document:
        self.require_project(project_id)
        filename = (upload.filename or "").replace(chr(92), "/").split("/")[-1].strip()
        file_type = Path(filename).suffix.lower().lstrip(".")
        if file_type == "markdown":
            file_type = "md"
        if not filename or file_type not in SUPPORTED:
            raise DocumentError("UNSUPPORTED_TYPE", "Choose a PDF, DOCX, TXT, or Markdown file.", 415)
        document_id = uuid4()
        directory = self._directory(project_id, document_id)
        directory.mkdir(parents=True, exist_ok=False)
        temporary = directory / "upload.tmp"
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("wb") as target:
                while chunk := upload.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise DocumentError("FILE_TOO_LARGE", f"Files must be smaller than {self.max_bytes // (1024 * 1024)} MB.", 413)
                    digest.update(chunk)
                    target.write(chunk)
            if size == 0:
                raise DocumentError("EMPTY_FILE", "This file is empty.")
            existing = self.repository.find_hash(project_id, digest.hexdigest())
            if existing:
                raise DocumentError("DUPLICATE_DOCUMENT", f"This file is already in the project as {existing.display_name}.", 409)
            with temporary.open("rb") as source:
                signature = source.read(8)
            if file_type == "pdf" and not signature.startswith(b"%PDF-"):
                raise DocumentError("CORRUPT_FILE", "This file is not a valid PDF.")
            if file_type == "docx" and not signature.startswith(b"PK"):
                if signature == bytes([208, 207, 17, 224, 161, 177, 26, 225]):
                    raise DocumentError("PASSWORD_REQUIRED", "This Word file appears to be password protected.")
                raise DocumentError("CORRUPT_FILE", "This file is not a valid DOCX.")
            original_name = f"original.{file_type}"
            os.replace(temporary, directory / original_name)
            now = datetime.now(timezone.utc)
            document = Document(document_id, project_id, filename, filename, file_type, size, digest.hexdigest(), "processing", "extracting", None, None, None, original_name, now, now)
            try:
                self.repository.create(document)
            except sqlite3.IntegrityError as error:
                raise DocumentError("DUPLICATE_DOCUMENT", "This file is already in the project.", 409) from error
            return document
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

    def process(self, project_id: UUID, document_id: UUID) -> None:
        document = self.repository.get(project_id, document_id)
        if document is None:
            return
        try:
            result = self.extractor.extract(self._original(document), document.file_type)
            content = self._content(document)
            temporary = content.with_suffix(".tmp")
            temporary.write_text(json.dumps({"segments": result.segments}, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, content)
            self.repository.update(project_id, document_id, "ready", "complete", page_count=result.page_count)
            if self.on_ready:
                self.on_ready(project_id, document_id)
        except DocumentError as error:
            self.repository.update(project_id, document_id, "failed", "extraction", error.code, error.message)
        except Exception:
            logger.exception("Document extraction failed for %s", document_id)
            self.repository.update(project_id, document_id, "failed", "extraction", "PROCESSING_ERROR", "Processing failed. Retry this document.")

    def content(self, project_id: UUID, document_id: UUID) -> dict:
        document = self.get(project_id, document_id)
        if document.status != "ready":
            raise DocumentError("DOCUMENT_NOT_READY", "This document is not ready to read.", 409)
        return json.loads(self._content(document).read_text(encoding="utf-8"))

    def original(self, project_id: UUID, document_id: UUID) -> Path:
        document = self.get(project_id, document_id)
        path = self._original(document)
        if not path.is_file():
            raise DocumentError("MISSING_ARTIFACT", "The retained original is missing.", 409)
        return path

    def retry(self, project_id: UUID, document_id: UUID) -> Document:
        document = self.get(project_id, document_id)
        if document.status != "failed" or document.error_code not in {"INTERRUPTED", "PROCESSING_ERROR"} or not self._original(document).is_file():
            raise DocumentError("RETRY_UNAVAILABLE", "This document cannot be retried. Import it again.", 409)
        self.repository.update(project_id, document_id, "processing", "extracting")
        return self.get(project_id, document_id)

    def delete(self, project_id: UUID, document_id: UUID) -> None:
        self.get(project_id, document_id)
        if self.on_delete:
            self.on_delete(project_id, document_id)
        directory = self._directory(project_id, document_id)
        if directory.exists():
            shutil.rmtree(directory)
        self.repository.delete(project_id, document_id)

    def delete_project_documents(self, project_id: UUID) -> None:
        for document in self.repository.list(project_id):
            self.delete(project_id, document.id)
