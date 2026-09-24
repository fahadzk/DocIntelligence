from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.application.search import SearchService
from app.main import get_search_service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["search"])
models_router = APIRouter(prefix="/api/models", tags=["models"])


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: UUID | None = None


class AskQuery(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class PassageResponse(BaseModel):
    id: UUID
    project_id: UUID
    document_id: UUID
    display_name: str
    file_type: str
    label: str
    page_number: int | None
    paragraph_number: int | None
    segment_index: int
    start_offset: int
    end_offset: int
    text: str
    match_type: str | None = None


class IndexStatusResponse(BaseModel):
    document_id: UUID
    display_name: str
    document_status: str
    status: str | None
    stage: str | None
    error_message: str | None
    index_version: str | None
    indexed_hash: str | None
    updated_at: str | None


class SearchResponse(BaseModel):
    results: list[PassageResponse]


class CitedEvidence(BaseModel):
    number: int
    passage: PassageResponse


class AnswerResponse(BaseModel):
    answer: str
    supported: bool
    evidence: list[CitedEvidence]


class ModelResponse(BaseModel):
    status: str
    error: str | None
    name: str
    size_mb: int
    source: str


class ModelsResponse(BaseModel):
    embeddings: ModelResponse
    answers: ModelResponse


def service() -> SearchService:
    return get_search_service()


@router.get("/index/status", response_model=list[IndexStatusResponse])
def index_status(project_id: UUID, search: SearchService = Depends(service)):
    return search.statuses(project_id)


@router.post("/index/rebuild")
def rebuild_index(project_id: UUID, search: SearchService = Depends(service)):
    import threading
    search.documents.require_project(project_id)
    def work():
        search.repository.rebuild_fts()
        for document in search.documents.list(project_id):
            if document.status == "ready":
                search.index_document(project_id, document.id, force=True)
    threading.Thread(target=work, daemon=True, name="index-rebuild").start()
    return {"status": "indexing"}


@router.post("/search", response_model=SearchResponse)
def search_project(project_id: UUID, body: SearchQuery, search: SearchService = Depends(service)):
    return {"results": search.search(project_id, body.query, body.document_id)}


@router.get("/evidence/{passage_id}", response_model=PassageResponse)
def get_evidence(project_id: UUID, passage_id: UUID, search: SearchService = Depends(service)):
    return search.evidence(project_id, passage_id)


@router.post("/ask", response_model=AnswerResponse)
def ask_project(project_id: UUID, body: AskQuery, search: SearchService = Depends(service)):
    return search.ask(project_id, body.question)


@models_router.get("", response_model=ModelsResponse)
def models(search: SearchService = Depends(service)):
    return search.model_status()


@models_router.post("/{kind}/setup", response_model=ModelResponse)
def setup_model(kind: str, search: SearchService = Depends(service)):
    search.provision(kind)
    return search.model_status()[kind]
