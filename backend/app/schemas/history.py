from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HistoryCategoryScore(BaseModel):
    key: str
    label: str
    score: int


class HistoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    github_user_id: int
    github_username: str
    captured_at: datetime
    analysis_version: str
    analysis_schema_version: str
    portfolio_score: int | None
    category_scores: list[HistoryCategoryScore]
    passed_checks: list[str]
    failed_checks: list[str]


class HistoryDelta(BaseModel):
    portfolio_score: int | None
    category_scores: list[dict[str, int | str]]
    newly_passing_checks: list[str]
    newly_failing_checks: list[str]
    comparable: bool
    note: str | None = None


class HistoryResponse(BaseModel):
    latest: HistoryRecord | None
    previous: HistoryRecord | None
    comparison: HistoryDelta | None
    history: list[HistoryRecord]
