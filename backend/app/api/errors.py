import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError


class APIErrorDetail(BaseModel):
    code: str
    message: str


class APIErrorResponse(BaseModel):
    detail: APIErrorDetail


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=APIErrorDetail(code=code, message=message).model_dump(),
    )


def map_github_exception(error: Exception) -> HTTPException:
    """Map expected GitHub operational failures to the public API contract."""

    if isinstance(error, httpx.TimeoutException):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "github_timeout",
            "GitHub is temporarily unavailable.",
        )

    if isinstance(error, httpx.RequestError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "github_unavailable",
            "GitHub is temporarily unavailable.",
        )

    if isinstance(error, httpx.HTTPStatusError):
        github_status = error.response.status_code

        if github_status == status.HTTP_404_NOT_FOUND:
            return _error(
                status.HTTP_404_NOT_FOUND,
                "github_user_not_found",
                "GitHub user was not found.",
            )

        if github_status in {
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        }:
            return _error(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "github_rate_limit",
                "GitHub rate limit was reached.",
            )

        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub returned an upstream error.",
        )

    if isinstance(error, ValidationError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub returned an invalid response.",
        )

    raise error
