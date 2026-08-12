from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.github import GitHubUser
from app.services.github.client import GitHubClient

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub"],
)


def get_github_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GitHubClient:
    return GitHubClient(settings)


@router.get("/users/{username}", response_model=GitHubUser)
async def get_github_user(
    username: str,
    client: Annotated[GitHubClient, Depends(get_github_client)],
) -> GitHubUser:
    try:
        return await client.get_user(username)

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub service timed out.",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub service is unavailable.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        github_status = exc.response.status_code

        if github_status == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub user not found.",
            ) from exc

        if github_status in {
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        }:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceed.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub service returned an unexpected response.",
        ) from exc

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub service returned an invalid response.",
        ) from exc
