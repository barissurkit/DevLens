from datetime import datetime

import pytest
from app.schemas.github import GitHubUser
from pydantic import ValidationError


def create_github_user_payload() -> dict[str, object]:
    return {
        "login": "octocat",
        "name": "The Octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
        "bio": "GitHub mascot",
        "public_repos": 8,
        "followers": 10000,
        "following": 9,
        "html_url": "https://github.com/octocat",
        "created_at": "2011-01-25T18:44:36Z",
    }


def test_github_user_normalizes_login_and_created_at() -> None:
    user = GitHubUser.model_validate(create_github_user_payload())

    assert user.username == "octocat"
    assert isinstance(user.created_at, datetime)
    assert user.created_at.isoformat() == "2011-01-25T18:44:36+00:00"

    serialized = user.model_dump()

    assert serialized["username"] == "octocat"
    assert "login" not in serialized


def test_github_user_accepts_nullable_fields() -> None:
    payload = create_github_user_payload()
    payload["name"] = None
    payload["bio"] = None

    user = GitHubUser.model_validate(payload)

    assert user.name is None
    assert user.bio is None


def test_github_user_rejects_missing_required_field() -> None:
    payload = create_github_user_payload()
    payload.pop("login")

    with pytest.raises(ValidationError) as error:
        GitHubUser.model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("login",)


"""
Yalnızca GitHubUser schema davranışını test eder.
"""
