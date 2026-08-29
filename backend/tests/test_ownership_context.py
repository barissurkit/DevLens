import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi import Request, Response

import app.api.auth as auth_api
from app.auth.ownership import derive_viewer_context, is_owner
from app.config import Settings
from app.db.models import User
from app.db.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.schemas.analysis import GitHubPortfolioAnalysisResponse, ViewerContext
from app.schemas.github import GitHubUser
def target(*, github_user_id: int, username: str = "same-login") -> GitHubUser:
    return GitHubUser.model_validate({
        "id": github_user_id, "login": username, "name": None,
        "avatar_url": "https://avatars.example/user.png", "bio": None,
        "public_repos": 0, "followers": 0, "following": 0,
        "html_url": f"https://github.com/{username}",
        "created_at": "2025-01-01T00:00:00Z",
    })


def authenticated_user(*, github_user_id: int, login: str = "same-login") -> User:
    return User(github_user_id=github_user_id, github_login=login)


def test_ownership_uses_immutable_github_id_not_login() -> None:
    user = authenticated_user(github_user_id=1)
    assert not is_owner(authenticated_user=user, target_github_user=target(github_user_id=2))
    assert derive_viewer_context(authenticated_user=user, target_github_user=target(github_user_id=2)).mode == "explore"


def test_username_changes_do_not_change_owner_identity() -> None:
    user = authenticated_user(github_user_id=1, login="old-login")
    assert is_owner(authenticated_user=user, target_github_user=target(github_user_id=1, username="new-login"))


def test_cached_analysis_context_is_recomputed_for_each_viewer() -> None:
    target_user = target(github_user_id=1)
    owner = authenticated_user(github_user_id=1)
    other = authenticated_user(github_user_id=2)
    assert derive_viewer_context(authenticated_user=owner, target_github_user=target_user).is_owner
    assert not derive_viewer_context(authenticated_user=None, target_github_user=target_user).is_owner
    assert not derive_viewer_context(authenticated_user=other, target_github_user=target_user).is_owner


def test_client_supplied_context_cannot_change_backend_derivation() -> None:
    context = derive_viewer_context(authenticated_user=None, target_github_user=target(github_user_id=2))
    assert context.model_dump() == {"is_owner": False, "mode": "explore"}


def test_snapshot_serialization_excludes_viewer_context() -> None:
    from test_analysis_endpoint import create_result

    class Session:
        def add(self, row: object) -> None:
            self.row = row

        async def flush(self) -> None:
            self.row.created_at = datetime.now(timezone.utc)

    analysis = create_result()
    response = GitHubPortfolioAnalysisResponse(
        **analysis.model_dump(), viewer_context=ViewerContext(is_owner=True, mode="my_workspace")
    )
    session = Session()
    record = asyncio.run(
        AnalysisSnapshotRepository(session).create(github_username="same-login", analysis=response)
    )
    assert "viewer_context" not in session.row.analysis_payload
    assert record.analysis.user.github_user_id == 1


def test_optional_analysis_session_clears_invalid_cookie(monkeypatch) -> None:
    class Session:
        async def __aenter__(self) -> "Session":
            return self

        async def __aexit__(self, exception_type, exception, traceback) -> None:
            return None

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://local/test",
        auth_cookie_secure=False,
    )
    monkeypatch.setattr(auth_api, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_api, "get_session_factory", lambda _: lambda: Session())
    monkeypatch.setattr(auth_api, "get_user_by_session_token", AsyncMock(return_value=None))
    request = Request({"type": "http", "headers": [(b"cookie", b"devlens_session=expired")]})
    response = Response()

    assert asyncio.run(auth_api.get_optional_authenticated_user(request, response)) is None
    assert 'devlens_session="";' in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
