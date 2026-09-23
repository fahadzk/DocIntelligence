from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.application.projects import ProjectService
from app.main import get_project_service
from app.main import get_document_service

router = APIRouter(prefix="/api/projects", tags=["projects"])

def service() -> ProjectService: return get_project_service()
def not_found() -> HTTPException: return HTTPException(404, detail={"code": "PROJECT_NOT_FOUND", "message": "The requested project could not be found."})

@router.get("", response_model=list[ProjectResponse])
def list_projects(project_service: ProjectService = Depends(service)):
    return project_service.list_projects()

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, project_service: ProjectService = Depends(service)):
    return project_service.create_project(payload.name.strip(), payload.description)

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID, project_service: ProjectService = Depends(service)):
    project = project_service.get_project(project_id)
    if project is None:
        raise not_found()
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: UUID, payload: ProjectUpdate, project_service: ProjectService = Depends(service)):
    result = project_service.update_project(project_id, payload.name.strip() if payload.name else None, payload.description, "description" in payload.model_fields_set)
    if result is None:
        raise not_found()
    return result

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, project_service: ProjectService = Depends(service)) -> Response:
    if project_service.get_project(project_id) is None:
        raise not_found()
    get_document_service().delete_project_documents(project_id)
    project_service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
