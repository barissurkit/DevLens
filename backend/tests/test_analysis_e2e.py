import asyncio
import base64
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from app.api.github import get_github_client
from app.main import app
from app.services.github.client import GitHubClient
from app.config import Settings


def user_payload(username: str = "synthetic-user") -> dict[str, Any]:
    return {
        "login": username,
        "name": "Synthetic User",
        "avatar_url": "https://avatars.example/user.png",
        "bio": "A deterministic test user.",
        "public_repos": 4,
        "followers": 3,
        "following": 2,
        "html_url": f"https://github.com/{username}",
        "created_at": "2025-01-01T00:00:00Z",
    }


def repository_payload(
    name: str,
    *,
    fork: bool = False,
    archived: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": "A small FastAPI portfolio project.",
        "html_url": f"https://github.com/synthetic-user/{name}",
        "language": "Python",
        "stargazers_count": 5,
        "forks_count": 1,
        "topics": ["backend"],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-02-01T00:00:00Z",
        "archived": archived,
        "fork": fork,
        "default_branch": "main",
    }


def full_files() -> dict[str, str]:
    return {
        "README.md": """# Portfolio API

This project provides a REST API for a developer portfolio.

## Installation

Install the dependencies.

## Usage

Run the application.

## Technologies

Built with FastAPI.

## Requirements

Python 3.12 is required.
""",
        "requirements.txt": "fastapi>=0.115\npytest>=8\n",
    }


def minimal_files() -> dict[str, str]:
    return {
        "README.md": "# Small project\n\nA small REST API.\n",
        "requirements.txt": "fastapi>=0.115\n",
    }


def full_tree(*, truncated: bool = False) -> dict[str, Any]:
    return {
        "truncated": truncated,
        "tree": [
            {"path": "README.md", "type": "blob"},
            {"path": "requirements.txt", "type": "blob"},
            {"path": "backend/tests/test_api.py", "type": "blob"},
            {"path": ".github/workflows/ci.yml", "type": "blob"},
            {"path": ".gitignore", "type": "blob"},
            {"path": "LICENSE", "type": "blob"},
        ],
    }


def request_app(payload: object) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post("/api/v1/analysis", json=payload)

    return asyncio.run(send_request())


def use_fake_github(
    repositories: list[dict[str, Any]],
    *,
    files_by_repository: dict[str, dict[str, str]] | None = None,
    trees_by_repository: dict[str, dict[str, Any]] | None = None,
    user_status: int | None = None,
    repository_list_status: int | None = None,
    repository_failures: dict[str, int] | None = None,
    network_error: bool = False,
    unexpected_error: bool = False,
) -> None:
    files_by_repository = files_by_repository or {}
    trees_by_repository = trees_by_repository or {}
    repository_failures = repository_failures or {}

    def handler(request: httpx.Request) -> httpx.Response:
        if unexpected_error:
            raise RuntimeError("programming bug")

        if network_error:
            raise httpx.ConnectError("synthetic network failure", request=request)

        path_parts = request.url.path.strip("/").split("/")

        if path_parts == ["users", "synthetic-user"]:
            if user_status is not None:
                return httpx.Response(user_status, request=request)
            return httpx.Response(200, json=user_payload(), request=request)

        if path_parts == ["users", "synthetic-user", "repos"]:
            if repository_list_status is not None:
                return httpx.Response(repository_list_status, request=request)
            return httpx.Response(200, json=repositories, request=request)

        if len(path_parts) >= 5 and path_parts[0] == "repos":
            repository_name = path_parts[2]
            failure_status = repository_failures.get(repository_name)

            if failure_status is not None:
                return httpx.Response(failure_status, request=request)

            if path_parts[3] == "contents":
                file_path = "/".join(path_parts[4:])
                content = files_by_repository.get(repository_name, {}).get(file_path)
                if content is None:
                    return httpx.Response(404, request=request)

                encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
                return httpx.Response(
                    200,
                    json={
                        "type": "file",
                        "path": file_path,
                        "name": file_path,
                        "content": encoded,
                        "encoding": "base64",
                        "size": len(content.encode("utf-8")),
                        "sha": f"sha-{repository_name}-{file_path}",
                    },
                    request=request,
                )

            if path_parts[3] == "git" and path_parts[4] == "trees":
                return httpx.Response(
                    200,
                    json=trees_by_repository.get(repository_name, full_tree()),
                    request=request,
                )

        return httpx.Response(404, request=request)

    client = GitHubClient(
        Settings(
            _env_file=None,
            github_api_base_url="https://api.github.com",
            github_token=None,
        ),
        transport=httpx.MockTransport(handler),
    )

    async def override_github_client() -> GitHubClient:
        return client

    app.dependency_overrides[get_github_client] = override_github_client


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def portfolio_fixture() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    repositories = [
        repository_payload("alpha"),
        repository_payload("bravo"),
        repository_payload("forked", fork=True),
        repository_payload("archived", archived=True),
        repository_payload("both", fork=True, archived=True),
    ]
    return repositories, {"alpha": full_files(), "bravo": full_files()}


def test_analysis_e2e_runs_real_pipeline_for_multi_repository_portfolio() -> None:
    repositories, files = portfolio_fixture()
    use_fake_github(
        repositories,
        files_by_repository=files,
        trees_by_repository={"bravo": full_tree(truncated=True)},
    )

    response = request_app({"username": "  synthetic-user  "})
    payload = response.json()

    assert response.status_code == 200
    assert payload["user"]["username"] == "synthetic-user"
    assert [item["name"] for item in payload["selection"]["selected"]] == [
        "alpha",
        "bravo",
    ]
    assert len(payload["selection"]["excluded"]) == 3
    both_excluded = next(
        item
        for item in payload["selection"]["excluded"]
        if item["repository"]["name"] == "both"
    )
    assert both_excluded["reasons"] == [
        "fork_repository",
        "archived_repository",
    ]
    assert len(payload["repository_analysis"]["repositories"]) == 2
    assert payload["repository_analysis"]["failures"] == []
    assert payload["aggregation"]["successful_repository_count"] == 2
    assert payload["aggregation"]["partial_evidence_repository_count"] == 1
    assert payload["aggregation"]["technology_distribution"] == [
        {"technology": "FastAPI", "repository_count": 2},
        {"technology": "pytest", "repository_count": 2},
    ]
    assert payload["score"]["is_available"] is True
    assert payload["score"]["is_partial"] is True
    assert payload["score"]["overall_score"] == 95
    assert payload["intelligence"]["recurring_technologies"] == [
        {"technology": "FastAPI", "repository_count": 2},
        {"technology": "pytest", "repository_count": 2},
    ]

    serialized = response.text
    for secret_or_raw_data in (
        "Authorization",
        "Bearer",
        "raw README",
        "requirements.txt",
        "programming bug",
        "/home/",
    ):
        assert secret_or_raw_data not in serialized


def test_analysis_e2e_ignores_malformed_readme_url() -> None:
    repositories = [repository_payload("malformed-readme")]
    files = {
        "malformed-readme": {
            "README.md": (
                "# Malformed README\n\n"
                "This project provides a deterministic backend application "
                "service for analyzing public portfolio evidence.\n\n"
                "Open [http://localhost:3000](http://localhost:3000).\n"
            ),
            "requirements.txt": "fastapi>=0.115\n",
        }
    }
    use_fake_github(repositories, files_by_repository=files)

    response = request_app({"username": "synthetic-user"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["repository_analysis"]["failures"] == []
    assert payload["repository_analysis"]["repositories"][0]["analysis"]["readme"][
        "has_demo_link"
    ] is False


def test_analysis_e2e_ignores_requirements_file_bom() -> None:
    repositories = [repository_payload("bom-requirements")]
    files = {
        "bom-requirements": {
            "README.md": full_files()["README.md"],
            "requirements.txt": (
                "\ufeffbeautifulsoup4==4.12.2\n"
                "requests==2.32.0\n"
            ),
        }
    }
    use_fake_github(repositories, files_by_repository=files)

    response = request_app({"username": "synthetic-user"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["repository_analysis"]["failures"] == []
    assert payload["repository_analysis"]["repositories"][0]["analysis"][
        "technologies"
    ]["dependencies"] == ["beautifulsoup4", "requests"]


def test_analysis_e2e_response_is_deterministic() -> None:
    repositories, files = portfolio_fixture()

    use_fake_github(repositories, files_by_repository=files)
    first = request_app({"username": "synthetic-user"})

    use_fake_github(repositories, files_by_repository=files)
    second = request_app({"username": "synthetic-user"})

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


@pytest.mark.parametrize(
    ("repositories", "expected_excluded"),
    [
        ([], 0),
        (
            [
                repository_payload("forked", fork=True),
                repository_payload("archived", archived=True),
            ],
            2,
        ),
    ],
)
def test_analysis_e2e_preserves_no_eligible_repository_semantics(
    repositories: list[dict[str, Any]],
    expected_excluded: int,
) -> None:
    use_fake_github(repositories)

    response = request_app({"username": "synthetic-user"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["selection"]["selected"] == []
    assert len(payload["selection"]["excluded"]) == expected_excluded
    if expected_excluded:
        assert {
            reason
            for item in payload["selection"]["excluded"]
            for reason in item["reasons"]
        } == {"fork_repository", "archived_repository"}
    assert payload["repository_analysis"]["repositories"] == []
    assert payload["repository_analysis"]["failures"] == []
    assert payload["aggregation"]["successful_repository_count"] == 0
    assert payload["score"]["is_available"] is False
    assert payload["score"]["overall_score"] is None
    assert payload["intelligence"]["strength_signals"] == []


@pytest.mark.parametrize(
    ("failure_count", "expected_score_available", "expected_partial"),
    [(1, True, True), (2, False, True), (3, False, True)],
)
def test_analysis_e2e_preserves_partial_repository_failures(
    failure_count: int,
    expected_score_available: bool,
    expected_partial: bool,
) -> None:
    repositories = [repository_payload(name) for name in ("alpha", "bravo", "charlie")]
    failures = {name: 503 for name in ("alpha", "bravo", "charlie")[:failure_count]}
    use_fake_github(
        repositories,
        files_by_repository={name: full_files() for name in ("alpha", "bravo", "charlie")},
        repository_failures=failures,
    )

    response = request_app({"username": "synthetic-user"})
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["repository_analysis"]["repositories"]) == 3 - failure_count
    assert len(payload["repository_analysis"]["failures"]) == failure_count
    assert payload["aggregation"]["failed_repository_count"] == failure_count
    assert payload["score"]["is_available"] is expected_score_available
    if expected_score_available:
        assert payload["score"]["overall_score"] is not None
    else:
        assert payload["score"]["overall_score"] is None
    assert payload["score"]["is_partial"] is expected_partial


@pytest.mark.parametrize(
    ("user_status", "expected_status", "expected_code", "expected_message"),
    [
        (404, 404, "github_user_not_found", "GitHub kullanıcısı bulunamadı."),
        (429, 429, "github_rate_limit", "GitHub istek limiti aşıldı."),
        (500, 502, "github_upstream_error", "GitHub beklenmeyen bir upstream hatası döndürdü."),
    ],
)
def test_analysis_e2e_maps_github_user_errors(
    user_status: int,
    expected_status: int,
    expected_code: str,
    expected_message: str,
) -> None:
    use_fake_github([], user_status=user_status)

    response = request_app({"username": "synthetic-user"})

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": {"code": expected_code, "message": expected_message}
    }


def test_analysis_e2e_maps_network_unavailable_to_503() -> None:
    use_fake_github([], network_error=True)

    response = request_app({"username": "synthetic-user"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "github_unavailable",
            "message": "GitHub'a geçici olarak erişilemiyor.",
        }
    }


def test_analysis_e2e_does_not_map_unexpected_internal_errors() -> None:
    use_fake_github([], unexpected_error=True)

    with pytest.raises(RuntimeError, match="programming bug"):
        request_app({"username": "synthetic-user"})


def test_analysis_e2e_request_contract_rejects_extra_fields() -> None:
    use_fake_github([])

    response = request_app(
        {"username": "synthetic-user", "max_concurrency": 100}
    )

    assert response.status_code == 422
