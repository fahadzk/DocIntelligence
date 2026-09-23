from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name cannot be blank.")
        return stripped


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Project name cannot be blank.")
        return value.strip() if value is not None else None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    code: str
    message: str
