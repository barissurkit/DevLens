import asyncio

import httpx
from app.config import Settings
from app.services.github.client import GitHubClient


def create_settings(github_token: str | None = None) -> Settings:
    return Settings(
        _env_file=None,
        github_api_base_url="https://api.github.com",
        github_token=github_token,
    )


def test_request_without_token_has_no_authorization_header() -> None:
    captured_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = request.headers

        return httpx.Response(200, json={"login": "octocat"})

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(client.get_user("octocat"))

    assert captured_headers is not None
    assert "authorization" not in captured_headers


def test_request_with_token_uses_bearer_authorization_header() -> None:
    captured_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = request.headers

        return httpx.Response(200, json={"login": "octocat"})

    client = GitHubClient(
        create_settings(github_token="test-token"),
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(client.get_user("octocat"))

    assert captured_headers is not None
    assert captured_headers["authorization"] == "Bearer test-token"


def test_get_user_returns_raw_json_and_uses_expected_request_details() -> None:
    captured_request: httpx.Request | None = None
    expected_payload = {
        "login": "octocat",
        "id": 583231,
        "html_url": "https://github.com/octocat",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(200, json=expected_payload)

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.get_user("octocat"))

    assert result == expected_payload
    assert captured_request is not None
    assert str(captured_request.url) == "https://api.github.com/users/octocat"
    assert captured_request.headers["accept"] == "application/vnd.github+json"
    assert captured_request.headers["user-agent"] == "DevLens/0.1.0"
    assert captured_request.headers["x-github-api-version"] == "2026-03-10"


"""
httpx: python ile HTTP request gönderen dependency.
"""
