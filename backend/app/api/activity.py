from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.application.activity import ActivityService
from app.main import get_activity_service

router = APIRouter(prefix="/api/projects/{project_id}/activity", tags=["activity"])


class ActivityEventResponse(BaseModel):
    id: UUID
    project_id: UUID
    document_id: UUID | None
    action: str
    level: str
    message: str
    details: dict
    duration_ms: int | None
    created_at: datetime


def service() -> ActivityService:
    return get_activity_service()


@router.get("", response_model=list[ActivityEventResponse])
def list_activity(project_id: UUID, limit: int = Query(default=200, ge=1, le=500),
                  activity: ActivityService = Depends(service)):
    return activity.list(project_id, limit)
