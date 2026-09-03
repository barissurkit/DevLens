import asyncio
import base64

import httpx
import pytest
from app.config import Settings
from app.schemas.github import GitHubFileContent, GitHubRepository, GitHubUser
from app.services.github.client import (
    IMPORTANT_REPOSITORY_FILE_PATHS,
    MAX_FILE_SIZE_BYTES,
    MAX_REPOSITORY_PAGES,
    MAX_TREE_ENTRIES,
    REPOSITORIES_PER_PAGE,
    GitHubMalformedResponseError,
    GitHubRequestBudget,
    GitHubClient,
    decode_github_file_content,
    use_github_request_budget,
)


def test_get_important_files_returns_found_and_missing_files() -> None:
    captured_requests: list[httpx.Request] = []
    available_files = {
        "README.md": ("IyBEZXZMZW5z", 9),
        "package.json": ("e30=", 2),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        path = request.url.path.rsplit("/", maxsplit=1)[-1]

        if path not in available_files:
            return httpx.Response(
                404,
                json={"message": "Not Found"},
            )

        content, size = available_files[path]
        payload = create_github_file_payload()
        payload.update(
            {
                "path": path,
                "name": path,
                "content": content,
                "size": size,
                "sha": f"sha-{path}",
            }
        )

        return httpx.Response(200, json=payload)

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.get_important_files(
            owner="octocat",
            repository="devlens",
            ref="main",
        )
    )

    assert list(result) == list(IMPORTANT_REPOSITORY_FILE_PATHS)

    readme = result["README.md"]
    package_json = result["package.json"]

    assert isinstance(readme, GitHubFileContent)
    assert readme.content == "# DevLens"

    assert result["requirements.txt"] is None
    assert result["pyproject.toml"] is None

    assert isinstance(package_json, GitHubFileContent)
    assert package_json.content == "{}"

    assert len(captured_requests) == 4
    assert all(request.url.params["ref"] == "main" for request in captured_requests)


def test_get_file_content_rejects_file_over_size_limit() -> None:
    payload = create_github_file_payload()
    payload["size"] = MAX_FILE_SIZE_BYTES + 1
    payload["content"] = "not-valid-base64!"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        ValueError,
        match="exceeds the maximum size",
    ):
        asyncio.run(
            client.get_file_content(
                owner="octocat",
                repository="devlens",
                path="README.md",
                ref="main",
            )
        )


def test_decode_github_file_content_returns_utf8_text() -> None:
    result = decode_github_file_content(
        content="IyBEZXZM\nZW5z",
        encoding="base64",
    )

    assert result == "# DevLens"


def test_decode_github_file_content_preserves_utf8_bom_for_parser_boundary() -> None:
    content = base64.b64encode("\ufeffbeautifulsoup4==4.12.2".encode("utf-8")).decode(
        "ascii"
    )

    assert decode_github_file_content(content, "base64") == "\ufeffbeautifulsoup4==4.12.2"


def test_decode_github_file_content_rejects_unsupported_encoding() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported GitHub file encoding",
    ):
        decode_github_file_content(
            content="# DevLens",
            encoding="utf-8",
        )


def test_decode_github_file_content_rejects_invalid_base64() -> None:
    with pytest.raises(
        ValueError,
        match="not valid Base64-encoded UTF-8 text",
    ):
        decode_github_file_content(
            content="not-valid-base64!",
            encoding="base64",
        )


def create_settings(github_token: str | None = None) -> Settings:
    return Settings(
        _env_file=None,
        github_api_base_url="https://api.github.com",
        github_token=github_token,
    )


def create_github_user_payload() -> dict[str, object]:
    return {
        "id": 583231,
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


def create_github_file_payload() -> dict[str, object]:
    return {
        "type": "file",
        "path": "README.md",
        "name": "README.md",
        "content": "IyBEZXZMZW5z",
        "encoding": "base64",
        "size": 9,
        "sha": "abc123",
    }


def test_get_file_content_returns_decoded_normalized_model() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(
            200,
            json=create_github_file_payload(),
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.get_file_content(
            owner="octocat",
            repository="devlens",
            path="README.md",
            ref="main",
        )
    )

    assert isinstance(result, GitHubFileContent)
    assert result.path == "README.md"
    assert result.name == "README.md"
    assert result.content == "# DevLens"
    assert result.size == 9
    assert result.sha == "abc123"

    assert captured_request is not None
    assert captured_request.url.path == ("/repos/octocat/devlens/contents/README.md")
    assert captured_request.url.params["ref"] == "main"


def test_get_file_content_returns_none_when_file_is_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"message": "Not Found"},
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.get_file_content(
            owner="octocat",
            repository="devlens",
            path="requirements.txt",
            ref="main",
        )
    )

    assert result is None


def create_github_tree_payload(
    *,
    truncated: bool = False,
) -> dict[str, object]:
    return {
        "sha": "tree-sha",
        "truncated": truncated,
        "tree": [
            {"path": "README.md", "type": "blob"},
            {"path": "backend", "type": "tree"},
            {"path": "backend/tests/test_api.py", "type": "blob"},
            {"path": "vendor/library", "type": "commit"},
        ],
    }


def test_get_repository_tree_returns_paths_and_completeness() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request

        return httpx.Response(
            200,
            json=create_github_tree_payload(),
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.get_repository_tree(
            owner="octocat",
            repository="devlens",
            ref="main",
        )
    )

    assert result.paths == [
        "README.md",
        "backend/tests/test_api.py",
    ]
    assert result.truncated is False

    assert captured_request is not None
    assert captured_request.url.path == ("/repos/octocat/devlens/git/trees/main")
    assert captured_request.url.params["recursive"] == "1"


def test_get_repository_tree_preserves_truncated_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=create_github_tree_payload(truncated=True),
        )

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(
        client.get_repository_tree(
            owner="octocat",
            repository="devlens",
            ref="main",
        )
    )

    assert result.paths == [
        "README.md",
        "backend/tests/test_api.py",
    ]
    assert result.truncated is True


@pytest.mark.parametrize(
    ("entry_count", "expected_truncated"),
    [(MAX_TREE_ENTRIES - 1, False), (MAX_TREE_ENTRIES, False), (MAX_TREE_ENTRIES + 1, True)],
)
def test_get_repository_tree_caps_path_processing_at_boundary(
    entry_count: int,
    expected_truncated: bool,
) -> None:
    payload = create_github_tree_payload()
    payload["tree"] = [
        {"path": f"src/{index}.py", "type": "blob"}
        for index in range(entry_count)
    ]

    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )

    result = asyncio.run(
        client.get_repository_tree(
            owner="octocat", repository="devlens", ref="main"
        )
    )

    assert len(result.paths) == min(entry_count, MAX_TREE_ENTRIES)
    assert result.truncated is expected_truncated


def test_provider_request_budget_stops_calls_after_exhaustion() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=create_github_user_payload())

    client = GitHubClient(
        create_settings(), transport=httpx.MockTransport(handler)
    )
    budget = GitHubRequestBudget(limit=1)

    with use_github_request_budget(budget):
        asyncio.run(client.get_user("octocat"))
        with pytest.raises(RuntimeError, match="budget exhausted"):
            asyncio.run(client.get_user("octocat"))

    assert calls == 1


def test_malformed_user_response_has_typed_provider_error() -> None:
    client = GitHubClient(
        create_settings(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"id": "wrong"})
        ),
    )

    with pytest.raises(GitHubMalformedResponseError):
        asyncio.run(client.get_user("octocat"))


"""
httpx: python ile HTTP request gönderen dependency.
"""
