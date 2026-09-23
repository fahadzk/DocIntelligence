from uuid import UUID

from app.domain.projects import Project
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository


class ProjectService:
    def __init__(self, repository: SqliteProjectRepository) -> None:
        self._repository = repository

    def list_projects(self) -> list[Project]: return self._repository.list()
    def get_project(self, project_id: UUID) -> Project | None: return self._repository.get(project_id)
    def create_project(self, name: str, description: str | None) -> Project: return self._repository.create(name, description)
    def update_project(self, project_id: UUID, name: str | None, description: str | None, update_description: bool) -> Project | None:
        return self._repository.update(project_id, name, description, update_description)
    def delete_project(self, project_id: UUID) -> bool: return self._repository.delete(project_id)
