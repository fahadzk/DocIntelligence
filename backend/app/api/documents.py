from datetime import datetime
import threading
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.application.documents import DocumentService
from app.domain.documents import DocumentError
from app.main import get_document_service, get_search_service

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


class DocumentResponse(BaseModel):
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
    created_at: datetime
    updated_at: datetime


class SegmentResponse(BaseModel):
    index: int
    kind: str
    label: str
    page_number: int | None
    paragraph_number: int | None
    text: str


class ContentResponse(BaseModel):
    segments: list[SegmentResponse]


class ImportOutcome(BaseModel):
    filename: str
    document: DocumentResponse | None = None
    error_code: str | None = None
    error_message: str | None = None


def service() -> DocumentService:
    return get_document_service()


@router.post("", response_model=list[ImportOutcome])
def import_documents(project_id: UUID, background: BackgroundTasks, files: list[UploadFile] = File(...), documents: DocumentService = Depends(service)):
    documents.require_project(project_id)
    outcomes = []
    for upload in files:
        try:
            document = documents.register(project_id, upload)
            background.add_task(documents.process, project_id, document.id)
            outcomes.append(ImportOutcome(filename=upload.filename or "", document=DocumentResponse.model_validate(document, from_attributes=True)))
        except DocumentError as error:
            outcomes.append(ImportOutcome(filename=upload.filename or "", error_code=error.code, error_message=error.message))
    return outcomes


@router.get("", response_model=list[DocumentResponse])
def list_documents(project_id: UUID, documents: DocumentService = Depends(service)):
    return documents.list(project_id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(project_id: UUID, document_id: UUID, documents: DocumentService = Depends(service)):
    return documents.get(project_id, document_id)


@router.get("/{document_id}/content", response_model=ContentResponse)
def get_content(project_id: UUID, document_id: UUID, documents: DocumentService = Depends(service)):
    return documents.content(project_id, document_id)


@router.get("/{document_id}/chunks")
def chunks(project_id: UUID, document_id: UUID):
    return get_search_service().chunks(project_id, document_id)

@router.post("/{document_id}/reindex")
def reindex(project_id: UUID, document_id: UUID):
    search = get_search_service()
    search.documents.get(project_id, document_id)
    threading.Thread(target=search.index_document, args=(project_id, document_id, True), daemon=True, name=f"reindex-{document_id}").start()
    return {"status": "indexing"}

@router.post("/{document_id}/embeddings")
def reembed(project_id: UUID, document_id: UUID):
    search = get_search_service()
    search.documents.get(project_id, document_id)
    threading.Thread(target=search.reembed_document, args=(project_id, document_id), daemon=True, name=f"reembed-{document_id}").start()
    return {"status": "embedding"}

@router.get("/{document_id}/original")
def get_original(project_id: UUID, document_id: UUID, documents: DocumentService = Depends(service)):
    document = documents.get(project_id, document_id)
    path = documents.original(project_id, document_id)
    media_types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain; charset=utf-8", "md": "text/markdown; charset=utf-8"}
    return FileResponse(path, media_type=media_types[document.file_type], filename=document.original_filename, content_disposition_type="inline")


@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry_document(project_id: UUID, document_id: UUID, background: BackgroundTasks, documents: DocumentService = Depends(service)):
    document = documents.retry(project_id, document_id)
    background.add_task(documents.process, project_id, document_id)
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(project_id: UUID, document_id: UUID, documents: DocumentService = Depends(service)):
    documents.delete(project_id, document_id)
    return Response(status_code=204)

