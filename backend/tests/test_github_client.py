import asyncio

import httpx
import pytest
from app.config import Settings
from app.schemas.github import GitHubRepository, GitHubUser
from app.services.github.client import (
    MAX_REPOSITORY_PAGES,
    REPOSITORIES_PER_PAGE,
    GitHubClient,
)


def create_settings(github_token: str | None = None) -> Settings:
    return Settings(
        _env_file=None,
        github_api_base_url="https://api.github.com",
        github_token=github_token,
    )


def create_github_user_payload() -> dict[str, object]:
    return {
        "login": "octocat",
        "name": "The Octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
        "bio": None,
        "public_repos": 8,
        "followers": 10000,
        "following": 9,
        "html_url": "https://github.com/octocat",
        "created_at": "2011-01-25T18:44:36Z",
    }


def test_request_without_token_has_no_authorization_header() -> None:
    captured_headers: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_headers
        captured_headers = request.headers

        return httpx.Response(200, json=create_github_user_payload())

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

        return httpx.Response(200, json=create_github_user_payload())

    client = GitHubClient(
        create_settings(github_token="test-token"),
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(client.get_user("octocat"))

    assert captured_headers is not None
    assert captured_headers["authorization"] == "Bearer test-token"


def test_get_user_returns_normalized_model_and_uses_expected_request_details() -> None:
    captured_request: httpx.Request | None = None
    expected_payload = create_github_user_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(200, json=expected_payload)

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.get_user("octocat"))

    assert isinstance(result, GitHubUser)
    assert result.username == "octocat"
    assert captured_request is not None
    assert str(captured_request.url) == "https://api.github.com/users/octocat"
    assert captured_request.headers["accept"] == "application/vnd.github+json"
    assert captured_request.headers["user-agent"] == "DevLens/0.1.0"
    assert captured_request.headers["x-github-api-version"] == "2026-03-10"


def create_github_repository_payload(
    index: int = 1,
) -> dict[str, object]:
    return {
        "name": f"repository-{index}",
        "description": None,
        "html_url": (f"https://github.com/octocat/repository-{index}"),
        "language": None,
        "stargazers_count": index,
        "forks_count": 0,
        "topics": ["portfolio"],
        "created_at": "2025-01-10T12:00:00Z",
        "updated_at": "2025-02-20T15:30:00Z",
        "archived": False,
        "fork": False,
        "default_branch": "main",
    }


def test_get_repositories_returns_normalized_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[create_github_repository_payload()],
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.get_repositories("octocat"))

    assert len(result) == 1
    assert isinstance(result[0], GitHubRepository)
    assert result[0].name == "repository-1"
    assert result[0].primary_language is None
    assert result[0].stars == 1
    assert result[0].forks == 0


def test_get_repositories_follows_pagination() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        page = int(request.url.params["page"])

        if page == 1:
            payload = [
                create_github_repository_payload(index)
                for index in range(1, REPOSITORIES_PER_PAGE + 1)
            ]
            return httpx.Response(
                200,
                json=payload,
                headers={
                    "Link": (
                        "<https://api.github.com/users/octocat/repos"
                        '?per_page=100&page=2>; rel="next"'
                    )
                },
            )

        return httpx.Response(
            200,
            json=[create_github_repository_payload(101)],
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.get_repositories("octocat"))

    assert len(result) == 101
    assert [request.url.params["page"] for request in captured_requests] == [
        "1",
        "2",
    ]
    assert all(request.url.params["per_page"] == "100" for request in captured_requests)


def test_get_repositories_stops_at_maximum_page_limit() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        next_page = request_count + 1

        return httpx.Response(
            200,
            json=[create_github_repository_payload(request_count)],
            headers={
                "Link": (
                    "<https://api.github.com/users/octocat/repos"
                    f'?per_page=100&page={next_page}>; rel="next"'
                )
            },
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        RuntimeError,
        match="pagination limit exceeded",
    ):
        asyncio.run(client.get_repositories("octocat"))

    assert request_count == MAX_REPOSITORY_PAGES


def test_get_repositories_rejects_non_list_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": "Unexpected response"},
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        TypeError,
        match="must be a JSON array",
    ):
        asyncio.run(client.get_repositories("octocat"))


"""
httpx: python ile HTTP request gönderen dependency.
"""
