"""Focused extraction boundary; segments retain source references."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import zipfile

import fitz
from docx import Document as DocxDocument
from docx.table import Table

from app.domain.documents import DocumentError


@dataclass(frozen=True)
class Extraction:
    segments: list[dict]
    page_count: int | None


class Extractor(Protocol):
    def extract(self, path: Path, file_type: str) -> Extraction: ...


class LocalExtractor:
    def extract(self, path: Path, file_type: str) -> Extraction:
        try:
            if file_type == "pdf":
                return self._pdf(path)
            if file_type == "docx":
                return self._docx(path)
            if file_type in ("txt", "md"):
                return self._plain(path, file_type)
        except DocumentError:
            raise
        except (UnicodeError, OSError) as error:
            raise DocumentError("UNREADABLE_FILE", "This file could not be read.") from error
        raise DocumentError("UNSUPPORTED_TYPE", "This file type is not supported.")

    def _pdf(self, path: Path) -> Extraction:
        try:
            pdf = fitz.open(path)
            if pdf.needs_pass:
                pdf.close()
                raise DocumentError("PASSWORD_REQUIRED", "This PDF is password protected.")
            segments = []
            for page_index, page in enumerate(pdf):
                text = page.get_text(sort=True).strip()
                if text:
                    segments.append({"index": len(segments), "kind": "page", "label": f"Page {page_index + 1}", "page_number": page_index + 1, "paragraph_number": None, "text": text})
            page_count = len(pdf)
            pdf.close()
        except DocumentError:
            raise
        except (fitz.FileDataError, RuntimeError) as error:
            raise DocumentError("CORRUPT_FILE", "This PDF could not be opened.") from error
        if not segments:
            raise DocumentError("NO_EXTRACTABLE_TEXT", "No readable text was found. Scanned PDFs need OCR, which is not available yet.")
        return Extraction(segments, page_count)

    def _docx(self, path: Path) -> Extraction:
        try:
            if not zipfile.is_zipfile(path):
                raise DocumentError("CORRUPT_FILE", "This DOCX file is not valid.")
            document = DocxDocument(path)
            segments = []
            heading = None
            paragraph_number = 0
            for block in document.iter_inner_content():
                paragraphs = [paragraph for row in block.rows for cell in row.cells for paragraph in cell.paragraphs] if isinstance(block, Table) else [block]
                for paragraph in paragraphs:
                    text = paragraph.text.strip()
                    if not text:
                        continue
                    paragraph_number += 1
                    kind = "heading" if paragraph.style and paragraph.style.name.startswith("Heading") else "paragraph"
                    if kind == "heading":
                        heading = text
                    segments.append({"index": len(segments), "kind": kind, "label": heading or f"Paragraph {paragraph_number}", "page_number": None, "paragraph_number": paragraph_number, "text": text})
        except DocumentError:
            raise
        except (ValueError, KeyError, zipfile.BadZipFile) as error:
            raise DocumentError("CORRUPT_FILE", "This DOCX file could not be opened.") from error
        if not segments:
            raise DocumentError("EMPTY_DOCUMENT", "This document contains no readable text.")
        return Extraction(segments, None)

    def _plain(self, path: Path, file_type: str) -> Extraction:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as error:
            raise DocumentError("UNREADABLE_FILE", "This file is not UTF-8 text.") from error
        if not text.strip():
            raise DocumentError("EMPTY_DOCUMENT", "This document contains no readable text.")
        segments = []
        heading = None
        for number, paragraph in enumerate(text.replace("\r\n", "\n").split("\n\n"), start=1):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            kind = "heading" if file_type == "md" and paragraph.startswith("#") else "paragraph"
            if kind == "heading":
                heading = paragraph.lstrip("# ").strip()
            segments.append({"index": len(segments), "kind": kind, "label": heading or f"Paragraph {number}", "page_number": None, "paragraph_number": number, "text": paragraph})
        return Extraction(segments, None)
