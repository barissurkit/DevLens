import httpx
from fastapi import HTTPException, status
from pydantic import ValidationError


def map_github_exception(error: Exception) -> HTTPException:
    """Map expected GitHub operational failures to the public API contract."""

    if isinstance(error, httpx.TimeoutException):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub service timed out.",
        )

    if isinstance(error, httpx.RequestError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub service is unavailable.",
        )

    if isinstance(error, httpx.HTTPStatusError):
        github_status = error.response.status_code

        if github_status == status.HTTP_404_NOT_FOUND:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub user not found.",
            )

        if github_status in {
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        }:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceed.",
            )

        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub service returned an unexpected response.",
        )

    if isinstance(error, ValidationError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub service returned an invalid response.",
        )

    raise error
