import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.projects import ProjectService
from app.application.documents import DocumentService
from app.application.search import SearchService
from app.config.settings import get_settings
from app.domain.documents import DocumentError
from app.infrastructure.operational_logging import OperationalLogger
from app.infrastructure.extractors import LocalExtractor
from app.infrastructure.sqlite_document_repository import SqliteDocumentRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.search_repository import SearchRepository
import threading

logging.basicConfig(level=get_settings().log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@lru_cache
def get_project_service() -> ProjectService:
    repository = SqliteProjectRepository(get_settings().database_path)
    repository.initialize()
    return ProjectService(repository)


@lru_cache
def get_operational_logger() -> OperationalLogger:
    settings = get_settings()
    return OperationalLogger(settings.data_dir, settings.log_level)


@lru_cache
def get_document_service() -> DocumentService:
    settings = get_settings()
    return DocumentService(
        SqliteDocumentRepository(settings.database_path),
        SqliteProjectRepository(settings.database_path),
        LocalExtractor(),
        settings.data_dir,
        settings.max_document_bytes,
        get_operational_logger(),
    )


@lru_cache
def get_search_service() -> SearchService:
    settings = get_settings()
    documents = get_document_service()
    service = SearchService(documents, SearchRepository(settings.database_path), settings.data_dir, settings.model_dir,
                            operations=get_operational_logger())
    def schedule_index(project_id, document_id):
        threading.Thread(target=service.index_document, args=(project_id, document_id),
                         daemon=True, name=f"index-{document_id}").start()
    documents.on_ready = schedule_index
    documents.on_delete = service.remove_document
    return service


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_operational_logger()
    get_project_service()
    get_document_service()
    search_service = get_search_service()
    threading.Thread(target=search_service.ensure_indexes, daemon=True, name="index-recovery").start()
    logger.info("Document Intelligence backend started")
    yield
    get_operational_logger().close()
    logger.info("Document Intelligence backend stopped")


app = FastAPI(title="Document Intelligence", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5174"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(HTTPException)
async def application_error(_: Request, error: HTTPException) -> JSONResponse:
    if isinstance(error.detail, dict) and "code" in error.detail:
        return JSONResponse(content=error.detail, status_code=error.status_code)
    return JSONResponse(content={"code": "REQUEST_ERROR", "message": str(error.detail)}, status_code=error.status_code)


@app.exception_handler(DocumentError)
async def document_error(_: Request, error: DocumentError) -> JSONResponse:
    return JSONResponse(content={"code": error.code, "message": error.message}, status_code=error.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    first = error.errors()[0]
    message = str(first.get("msg", "The request is invalid."))
    return JSONResponse(content={"code": "VALIDATION_ERROR", "message": message}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(_: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return JSONResponse(content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}, status_code=500)


@app.get("/health")
def health() -> dict[str, str]:
    """Readiness endpoint consumed by Electron before showing the workspace."""
    return {
        "status": "ok",
        "service": "document-intelligence-backend",
        "version": app.version,
        "environment": get_settings().environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


from app.api.projects import router as projects_router  # noqa: E402
from app.api.documents import router as documents_router  # noqa: E402
from app.api.search import router as search_router, models_router  # noqa: E402
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(models_router)
