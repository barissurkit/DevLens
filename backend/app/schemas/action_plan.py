from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionPlanStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


def clean_text(value: str) -> str:
    return value.strip()


class ActionPlanTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return clean_text(value) if isinstance(value, str) else value


class ActionPlanTaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ActionPlanStatus | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return clean_text(value) if isinstance(value, str) else value


class ActionPlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str | None
    status: ActionPlanStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ActionPlanResponse(BaseModel):
    tasks: list[ActionPlanTaskResponse]
