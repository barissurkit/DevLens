import asyncio

import httpx
import pytest
from google.genai import errors as genai_errors

from app.clients.gemini import _log_gemini_failure
from app.config import Settings
from app.observability import REQUEST_ID
from app.services.github.client import GitHubClient


def github_user_payload() -> dict[str, object]:
    return {
        "login": "octocat",
        "name": "The Octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/1",
        "bio": None,
        "public_repos": 1,
        "followers": 1,
        "following": 1,
        "html_url": "https://github.com/octocat",
        "created_at": "2011-01-25T18:44:36Z",
    }


@pytest.mark.parametrize("retry_after", ["60", "0", None, "later", "-1"])
def test_github_retry_after_is_allowlisted_only_when_valid(
    retry_after: str | None,
    caplog,
) -> None:
    caplog.set_level("INFO", logger="app")
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {
            "x-ratelimit-limit": "60",
            "x-ratelimit-remaining": "59",
            "x-ratelimit-reset": "1900000000",
            "x-ratelimit-resource": "core",
            "x-ratelimit-used": "1",
        }
        if retry_after is not None:
            headers["retry-after"] = retry_after
        return httpx.Response(200, headers=headers, json=github_user_payload())

    token = REQUEST_ID.set("00000000-0000-0000-0000-000000000010")
    try:
        asyncio.run(
            GitHubClient(
                Settings(_env_file=None, github_token="TEST_GITHUB_SECRET_SHOULD_NOT_APPEAR"),
                transport=httpx.MockTransport(handler),
            ).get_user("octocat")
        )
    finally:
        REQUEST_ID.reset(token)

    record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "github.request.completed"
    )
    assert record.request_id == "00000000-0000-0000-0000-000000000010"
    assert record.rate_limit_limit == 60
    assert record.rate_limit_remaining == 59
    assert record.rate_limit_reset == 1900000000
    assert record.rate_limit_resource == "core"
    assert record.rate_limit_used == 1
    if retry_after in {"60", "0"}:
        assert record.retry_after_seconds == int(retry_after)
    else:
        assert not hasattr(record, "retry_after_seconds")
    assert "TEST_GITHUB_SECRET_SHOULD_NOT_APPEAR" not in caplog.text


@pytest.mark.parametrize(
    ("status_code", "provider_status", "error_category"),
    [
        (429, "RESOURCE_EXHAUSTED", "rate_limit"),
        (403, "PERMISSION_DENIED", "upstream_error"),
    ],
)
def test_gemini_rate_limit_events_keep_semantic_and_provider_status_separate(
    status_code: int,
    provider_status: str,
    error_category: str,
    caplog,
) -> None:
    token = REQUEST_ID.set("00000000-0000-0000-0000-000000000011")
    try:
        _log_gemini_failure(
            error=genai_errors.APIError(
                status_code,
                {"error": {"status": provider_status, "message": "TEST_RAW_ERROR"}},
            ),
            model="gemini-3.6-flash",
            elapsed_ms=42,
            attempt=1,
        )
    finally:
        REQUEST_ID.reset(token)

    record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "gemini.request.completed"
    )
    assert record.error_category == error_category
    assert record.provider_status == provider_status
    assert record.upstream_status == status_code
    assert record.request_id == "00000000-0000-0000-0000-000000000011"
    assert record.attempt == 1
    assert "TEST_RAW_ERROR" not in caplog.text
