from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.saved_profiles as api
from app.config import Settings
from app.db.database import get_session
from app.db.repositories.saved_profiles import LatestAnalysis, SavedProfilesLimitReachedError
from app.main import create_app

ORIGIN = "http://localhost:3000"
JSON = {"Origin": ORIGIN, "Content-Type": "application/json"}
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


class FakeSession:
    commits = 0
    rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, _value) -> None:
        return None


def profile(name: str = "octocat"):
    return SimpleNamespace(id=uuid4(), github_username=name, github_username_normalized=name.lower(), created_at=NOW)


@pytest.fixture
def client(monkeypatch):
    settings = Settings(_env_file=None, environment="test", auth_enabled=False, cors_allowed_origins=ORIGIN, frontend_origin=ORIGIN)
    application = create_app(settings)
    session = FakeSession()

    async def fake_session():
        yield session

    application.dependency_overrides[get_session] = fake_session
    application.dependency_overrides[api.require_user] = lambda: SimpleNamespace(id=uuid4())
    test_client = TestClient(application)
    test_client.session = session  # type: ignore[attr-defined]
    return test_client


def test_the_list_returns_each_profile_with_the_latest_known_score(client, monkeypatch) -> None:
    saved = [profile("Octocat"), profile("ghost")]

    async def fake_list(_session, _user_id):
        return saved

    async def fake_latest(_session, names):
        assert names == ["octocat", "ghost"]
        return {"octocat": LatestAnalysis(score=61, analyzed_at=NOW)}

    monkeypatch.setattr(api, "list_saved_profiles", fake_list)
    monkeypatch.setattr(api, "latest_analyses", fake_latest)

    body = client.get("/api/v1/workspace/saved-profiles").json()

    assert body["limit"] == 50
    assert [(item["username"], item["latest_score"]) for item in body["profiles"]] == [("Octocat", 61), ("ghost", None)]
    assert body["profiles"][1]["latest_analyzed_at"] is None


@pytest.mark.parametrize(("created", "status"), [(True, 201), (False, 200)])
def test_saving_returns_201_for_a_new_profile_and_200_for_one_that_was_already_saved(client, monkeypatch, created, status) -> None:
    async def fake_save(_session, _user_id, username):
        return profile(username), created

    async def fake_latest(_session, _names):
        return {}

    monkeypatch.setattr(api, "save_profile", fake_save)
    monkeypatch.setattr(api, "latest_analyses", fake_latest)

    response = client.post("/api/v1/workspace/saved-profiles", json={"username": " octocat "}, headers=JSON)

    assert response.status_code == status
    assert response.json()["username"] == "octocat"
    assert client.session.commits == 1


def test_a_write_needs_the_application_origin_and_json(client) -> None:
    body = {"username": "octocat"}

    assert client.post("/api/v1/workspace/saved-profiles", json=body, headers={"Origin": "https://evil.example", "Content-Type": "application/json"}).status_code == 403
    # A body that is not JSON never gets as far as the origin check; a delete has no body, so it shows the rule.
    assert client.delete(f"/api/v1/workspace/saved-profiles/{uuid4()}", headers={"Origin": ORIGIN, "Content-Type": "text/plain"}).status_code == 415
    assert client.delete(f"/api/v1/workspace/saved-profiles/{uuid4()}", headers={"Origin": "https://evil.example", "Content-Type": "application/json"}).status_code == 403


@pytest.mark.parametrize("bad", ["", "a b", "-user:bob", "alice-", "x" * 40, "ali/ce"])
def test_only_valid_github_logins_are_accepted(client, bad) -> None:
    assert client.post("/api/v1/workspace/saved-profiles", json={"username": bad}, headers=JSON).status_code == 422
    assert client.session.commits == 0


def test_unknown_fields_are_rejected(client) -> None:
    assert client.post("/api/v1/workspace/saved-profiles", json={"username": "octocat", "extra": 1}, headers=JSON).status_code == 422


def test_reaching_the_cap_is_a_conflict_with_a_clear_message(client, monkeypatch) -> None:
    async def fake_save(*_args):
        raise SavedProfilesLimitReachedError

    monkeypatch.setattr(api, "save_profile", fake_save)

    response = client.post("/api/v1/workspace/saved-profiles", json={"username": "octocat"}, headers=JSON)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "saved_profiles_limit_reached"
    assert client.session.rollbacks == 1


def test_removing_a_profile_is_204_and_an_unknown_one_is_404(client, monkeypatch) -> None:
    results = iter([True, False])

    async def fake_delete(*_args):
        return next(results)

    monkeypatch.setattr(api, "delete_saved_profile", fake_delete)

    assert client.delete(f"/api/v1/workspace/saved-profiles/{uuid4()}", headers=JSON).status_code == 204
    assert client.delete(f"/api/v1/workspace/saved-profiles/{uuid4()}", headers=JSON).status_code == 404


def test_without_a_session_nothing_is_available() -> None:
    settings = Settings(_env_file=None, environment="test", auth_enabled=False, cors_allowed_origins=ORIGIN, frontend_origin=ORIGIN)
    application = create_app(settings)

    async def fake_session():
        yield FakeSession()

    application.dependency_overrides[get_session] = fake_session

    assert TestClient(application).get("/api/v1/workspace/saved-profiles").status_code == 401
