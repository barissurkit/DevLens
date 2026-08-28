from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    github_login: str
    display_name: str | None
    avatar_url: str | None
    github_html_url: str | None


class MeResponse(BaseModel):
    authenticated: bool
    user: AuthenticatedUserResponse | None


class AuthErrorResponse(BaseModel):
    detail: str = Field(min_length=1)
