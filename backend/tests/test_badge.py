from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import badge as badge_module
from app.api.badge import AMBER, GREEN, GREY, ROSE, badge_color, render_badge
from app.api.github import get_analysis_snapshot_cache_service
from app.config import Settings
from app.main import create_app


class FakeCache:
    def __init__(self, score: int | None, available: bool = True) -> None:
        self.calls: list[dict] = []
        self._cached = None
        if score is not None:
            self._cached = SimpleNamespace(
                analysis=SimpleNamespace(score=SimpleNamespace(overall_score=score, is_available=available))
            )

    async def get_fresh_analysis(self, **kwargs):
        self.calls.append(kwargs)
        return self._cached


@pytest.fixture(autouse=True)
def clear_memo():
    badge_module._memo.clear()
    yield
    badge_module._memo.clear()


def client_with(cache: FakeCache) -> TestClient:
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_analysis_snapshot_cache_service] = lambda: cache
    return TestClient(app)


@pytest.mark.parametrize(("score", "color"), [(100, GREEN), (75, GREEN), (74, AMBER), (50, AMBER), (49, ROSE), (0, ROSE)])
def test_badge_color_follows_the_score_bands(score: int, color: str) -> None:
    assert badge_color(score) == color


def test_render_badge_escapes_text_and_is_a_valid_svg_root() -> None:
    svg = render_badge("<script>&", GREY)

    assert svg.startswith("<svg ")
    assert "<script>" not in svg
    assert "&lt;script&gt;&amp;" in svg


def test_badge_shows_the_latest_stored_score_with_safe_headers() -> None:
    cache = FakeCache(61)
    response = client_with(cache).get("/api/v1/badge/OctoCat.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "61/100" in response.text and AMBER in response.text
    assert response.headers["cache-control"] == "public, max-age=600"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    # Stored snapshots only, looked up for the normalized login and a bounded age.
    assert cache.calls == [{"username": "octocat", "request_kind": "badge", "max_age": badge_module.BADGE_MAX_AGE}]


def test_badge_for_an_unanalyzed_user_invites_an_analysis() -> None:
    response = client_with(FakeCache(None)).get("/api/v1/badge/someone.svg")

    assert response.status_code == 200
    assert "analiz et" in response.text and GREY in response.text


def test_badge_ignores_a_snapshot_without_an_available_score() -> None:
    response = client_with(FakeCache(10, available=False)).get("/api/v1/badge/someone.svg")

    assert "analiz et" in response.text


@pytest.mark.parametrize("login", ["-bad", "bad-", "bad--name", "a" * 40, "bad_name"])
def test_badge_rejects_invalid_logins_without_touching_the_store(login: str) -> None:
    cache = FakeCache(50)
    response = client_with(cache).get(f"/api/v1/badge/{login}.svg")

    assert response.status_code == 404
    assert "geçersiz" in response.text
    assert cache.calls == []


def test_repeated_requests_are_served_from_the_short_memo() -> None:
    cache = FakeCache(80)
    client = client_with(cache)

    first = client.get("/api/v1/badge/octocat.svg").text
    second = client.get("/api/v1/badge/octocat.svg").text

    assert first == second and "80/100" in first
    assert len(cache.calls) == 1
