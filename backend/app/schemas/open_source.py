from datetime import datetime

from pydantic import BaseModel, Field


class OpenSourceContribution(BaseModel):
    """Merged pull requests a person has made to one public repository they do not own."""

    repository: str = Field(description="owner/name")
    html_url: str
    stars: int | None = Field(default=None, ge=0, description="None when the repository could not be looked up.")
    merged_count: int = Field(ge=1)
    latest_title: str
    latest_url: str
    latest_merged_at: datetime | None = None


class OpenSourceContributions(BaseModel):
    """Contributions to other people's repositories. They are shown next to the portfolio and never scored."""

    username: str
    total_merged: int = Field(ge=0, description="Merged pull requests that were found (at most the search window).")
    repository_count: int = Field(ge=0)
    contributions: list[OpenSourceContribution]
    is_truncated: bool = Field(description="More merged pull requests exist than the search window covers.")
