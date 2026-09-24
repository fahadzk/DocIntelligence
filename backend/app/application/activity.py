from uuid import UUID

from app.domain.documents import DocumentError
from app.infrastructure.activity_repository import ActivityRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository


class ActivityService:
    def __init__(self, repository: ActivityRepository, projects: SqliteProjectRepository):
        self.repository = repository
        self.projects = projects

    def record(self, project_id: UUID, action: str, message: str, *, details: dict | None = None,
               document_id: UUID | None = None, duration_ms: int | None = None,
               level: str = "info") -> None:
        self.repository.record(project_id, action, message, details, document_id, duration_ms, level)

    def list(self, project_id: UUID, limit: int = 200) -> list[dict]:
        if self.projects.get(project_id) is None:
            raise DocumentError("PROJECT_NOT_FOUND", "The requested project could not be found.", 404)
        return self.repository.list(project_id, limit)

    def remove_document(self, project_id: UUID, document_id: UUID) -> None:
        self.repository.purge_document(project_id, document_id)
