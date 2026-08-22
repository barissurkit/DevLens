import httpx
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import map_github_exception
from app.config import get_settings
from app.schemas.github import GitHubUser
from app.services.github.client import GitHubClient

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub"],
)


async def get_github_client() -> GitHubClient:
    return GitHubClient(get_settings())


@router.get("/users/{username}", response_model=GitHubUser)
async def get_github_user(
    username: str,
    client: GitHubClient = Depends(get_github_client),
) -> GitHubUser:
    try:
        return await client.get_user(username)
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
    ) as exc:
        raise map_github_exception(exc) from exc
