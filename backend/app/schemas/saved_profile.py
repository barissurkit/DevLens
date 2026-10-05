from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

LOGIN_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$"


class SavedProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=39, pattern=LOGIN_PATTERN)

    @field_validator("username", mode="before")
    @classmethod
    def trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SavedProfileResponse(BaseModel):
    id: UUID
    username: str
    saved_at: datetime
    # From the latest stored analysis of that profile; None when it has not been analysed (or has no score) yet.
    latest_score: int | None = None
    latest_analyzed_at: datetime | None = None


class SavedProfilesResponse(BaseModel):
    profiles: list[SavedProfileResponse]
    limit: int
