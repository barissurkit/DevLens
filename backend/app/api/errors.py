import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from app.clients.gemini import (
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUpstreamError,
)
from app.services.github.client import (
    GitHubMalformedResponseError,
    GitHubRepositoryPaginationLimitExceeded,
    GitHubRequestBudgetExceeded,
)


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
            "GitHub'a geçici olarak erişilemiyor.",
        )

    if isinstance(error, httpx.RequestError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "github_unavailable",
            "GitHub'a geçici olarak erişilemiyor.",
        )

    if isinstance(error, httpx.HTTPStatusError):
        github_status = error.response.status_code

        if github_status == status.HTTP_404_NOT_FOUND:
            return _error(
                status.HTTP_404_NOT_FOUND,
                "github_user_not_found",
                "GitHub kullanıcısı bulunamadı.",
            )

        if github_status in {
            status.HTTP_403_FORBIDDEN,
            status.HTTP_429_TOO_MANY_REQUESTS,
        }:
            return _error(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "github_rate_limit",
                "GitHub istek limiti aşıldı.",
            )

        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub beklenmeyen bir upstream hatası döndürdü.",
        )

    if isinstance(error, ValidationError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub geçersiz bir yanıt döndürdü.",
        )

    if isinstance(error, GitHubMalformedResponseError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub geçersiz bir yanıt döndürdü.",
        )

    if isinstance(error, GitHubRequestBudgetExceeded):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub analiz bütçesi aşıldı.",
        )

    if isinstance(error, GitHubRepositoryPaginationLimitExceeded):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            "github_upstream_error",
            "GitHub repository listesi analiz sınırına ulaştı.",
        )

    raise error


def map_ai_suggestions_exception(error: Exception) -> HTTPException:
    if isinstance(error, GeminiRateLimitError):
        return _error(status.HTTP_429_TOO_MANY_REQUESTS, "ai_provider_rate_limited", "AI sağlayıcısı şu anda yoğun veya kota sınırında; lütfen daha sonra tekrar deneyin.")
    if isinstance(error, GeminiTimeoutError):
        return _error(status.HTTP_504_GATEWAY_TIMEOUT, "ai_timeout", "AI önerileri zaman aşımına uğradı; lütfen tekrar deneyin.")
    if isinstance(error, GeminiInvalidResponseError):
        return _error(status.HTTP_502_BAD_GATEWAY, "ai_invalid_response", "AI öneri servisi geçersiz bir yanıt döndürdü.")
    if isinstance(error, (GeminiNotConfiguredError, GeminiUnavailableError, GeminiUpstreamError)):
        return _error(status.HTTP_503_SERVICE_UNAVAILABLE, "ai_unavailable", "AI öneri servisi şu anda kullanılamıyor.")
    raise error
