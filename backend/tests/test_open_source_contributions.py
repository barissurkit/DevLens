import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.github import get_github_client
from app.config import Settings
from app.main import create_app
from app.services import open_source_contributions as service
from app.services.github.client import GitHubClient


def settings() -> Settings:
    return Settings(_env_file=None, environment="test", auth_enabled=False, cors_allowed_origins="http://localhost:3000")


def pull_request(repo: str, title: str, merged_at: str, number: int = 1) -> dict:
    owner, name = repo.split("/")
    return {
        "title": title,
        "html_url": f"https://github.com/{repo}/pull/{number}",
        "repository_url": f"https://api.github.com/repos/{repo}",
        "closed_at": merged_at,
        "pull_request": {"merged_at": merged_at},
    }


class FakeGitHub:
    """Answers the search and repository calls; records every request."""

    def __init__(self, items: list[dict], stars: dict[str, int | None], total: int | None = None, search_status: int = 200) -> None:
        self.items, self.stars, self.total, self.search_status = items, stars, total, search_status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/search/issues":
            if self.search_status != 200:
                return httpx.Response(self.search_status, json={"message": "Validation Failed"})
            page = int(request.url.params["page"])
            chunk = self.items[(page - 1) * 100 : page * 100]
            return httpx.Response(200, json={"total_count": self.total if self.total is not None else len(self.items), "items": chunk})
        if path.startswith("/repos/"):
            name = path.removeprefix("/repos/")
            stars = self.stars.get(name)
            if stars is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, json={"stargazers_count": stars})
        return httpx.Response(404)

    def client(self) -> GitHubClient:
        return GitHubClient(settings(), transport=httpx.MockTransport(self.handler))


@pytest.fixture(autouse=True)
def fresh_cache():
    service.clear_cache()
    yield
    service.clear_cache()


def run(fake: FakeGitHub, username: str = "alice", ttl: int = 0):
    return asyncio.run(service.get_open_source_contributions(username, fake.client(), ttl_seconds=ttl))


def test_pull_requests_are_grouped_per_repository_and_ordered_by_stars() -> None:
    fake = FakeGitHub(
        [
            pull_request("big/framework", "Fix docs", "2026-09-01T10:00:00Z", 1),
            pull_request("big/framework", "Fix a crash", "2026-09-20T10:00:00Z", 2),
            pull_request("small/lib", "Add option", "2026-08-01T10:00:00Z", 3),
            pull_request("mid/tool", "Typo", "2026-07-01T10:00:00Z", 4),
        ],
        {"big/framework": 90000, "small/lib": 12, "mid/tool": 3400},
    )

    result = run(fake)

    assert [item.repository for item in result.contributions] == ["big/framework", "mid/tool", "small/lib"]
    top = result.contributions[0]
    assert (top.merged_count, top.stars, top.latest_title) == (2, 90000, "Fix a crash")
    assert top.latest_url.endswith("/pull/2") and top.html_url == "https://github.com/big/framework"
    assert (result.total_merged, result.repository_count, result.is_truncated) == (4, 3, False)


def test_the_search_asks_for_merged_public_pull_requests_to_repositories_of_others() -> None:
    fake = FakeGitHub([], {})

    result = run(fake)

    query = fake.requests[0].url.params["q"]
    assert "type:pr" in query and "author:alice" in query and "is:merged" in query and "is:public" in query and "-user:alice" in query
    assert (result.total_merged, result.contributions, result.is_truncated) == (0, [], False)
    assert len(fake.requests) == 1  # nothing found, so no star lookups


def test_a_repository_that_cannot_be_read_is_listed_without_stars_after_the_others() -> None:
    fake = FakeGitHub(
        [pull_request("gone/repo", "A", "2026-09-01T00:00:00Z", 1), pull_request("kept/repo", "B", "2026-09-02T00:00:00Z", 2)],
        {"kept/repo": 5},
    )

    result = run(fake)

    assert [(item.repository, item.stars) for item in result.contributions] == [("kept/repo", 5), ("gone/repo", None)]


def test_a_repository_owned_by_the_person_is_never_an_outside_contribution() -> None:
    fake = FakeGitHub([pull_request("Alice/own", "Mine", "2026-09-01T00:00:00Z"), pull_request("other/repo", "Theirs", "2026-09-01T00:00:00Z", 2)], {"other/repo": 1})

    assert [item.repository for item in run(fake).contributions] == ["other/repo"]


def test_more_results_than_the_search_window_are_reported_as_truncated() -> None:
    items = [pull_request(f"o{index}/r{index}", f"PR {index}", "2026-09-01T00:00:00Z", index) for index in range(300)]
    fake = FakeGitHub(items, {}, total=450)

    result = run(fake)

    assert [r.url.params["page"] for r in fake.requests if r.url.path == "/search/issues"] == ["1", "2", "3"]
    assert result.total_merged == 300 and result.is_truncated is True
    assert len(result.contributions) == service.MAX_CONTRIBUTIONS
    assert sum(1 for r in fake.requests if r.url.path.startswith("/repos/")) == service.MAX_STAR_LOOKUPS


def test_an_account_github_cannot_search_gives_an_empty_result() -> None:
    result = run(FakeGitHub([], {}, search_status=422))

    assert (result.total_merged, result.contributions) == (0, [])


def test_results_are_cached_for_the_configured_time() -> None:
    fake = FakeGitHub([pull_request("a/b", "T", "2026-09-01T00:00:00Z")], {"a/b": 1})
    client = fake.client()

    first = asyncio.run(service.get_open_source_contributions("alice", client, ttl_seconds=900))
    second = asyncio.run(service.get_open_source_contributions("ALICE", client, ttl_seconds=900))

    assert first is second
    assert len([r for r in fake.requests if r.url.path == "/search/issues"]) == 1


def test_the_endpoint_returns_the_contributions_and_rejects_names_that_are_not_logins() -> None:
    fake = FakeGitHub([pull_request("a/b", "T", "2026-09-01T00:00:00Z")], {"a/b": 7})
    application = create_app(settings())
    application.dependency_overrides[get_github_client] = lambda: fake.client()
    client = TestClient(application)

    ok = client.get("/api/v1/github/users/alice/open-source")
    assert ok.status_code == 200
    body = ok.json()
    assert body["username"] == "alice" and body["contributions"][0]["stars"] == 7

    # The name goes into a search query: a qualifier smuggled in through it must never reach GitHub.
    before = len(fake.requests)
    for bad in ("alice%20is:private", "-user:bob", "alice-"):
        assert client.get(f"/api/v1/github/users/{bad}/open-source").status_code in {404, 422}
    assert len(fake.requests) == before


def test_github_rate_limiting_is_reported_with_the_public_error_contract() -> None:
    fake = FakeGitHub([], {}, search_status=403)
    application = create_app(settings())
    application.dependency_overrides[get_github_client] = lambda: fake.client()

    response = TestClient(application).get("/api/v1/github/users/alice/open-source")

    assert response.status_code == 429
    assert json.loads(response.text)["detail"]["code"] == "github_rate_limit"
