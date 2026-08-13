from datetime import datetime

import pytest
from app.schemas.github import GitHubFileContent, GitHubRepository, GitHubRepositoryTree, GitHubUser
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


def create_github_repository_payload() -> dict[str, object]:
    return {
        "name": "devlens",
        "description": "Developer portfolio intelligence",
        "html_url": "https://github.com/octocat/devlens",
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 7,
        "topics": ["github", "portfolio"],
        "created_at": "2025-01-10T12:00:00Z",
        "updated_at": "2025-02-20T15:30:00Z",
        "archived": False,
        "fork": True,
        "default_branch": "main",
    }


def test_github_repository_maps_fields_and_datetimes() -> None:
    repository = GitHubRepository.model_validate(create_github_repository_payload())

    assert repository.primary_language == "Python"
    assert repository.stars == 42
    assert repository.forks == 7
    assert isinstance(repository.created_at, datetime)
    assert isinstance(repository.updated_at, datetime)


def test_github_repository_accepts_nullable_fields_and_preserves_flags() -> None:
    payload = create_github_repository_payload()
    payload["description"] = None
    payload["language"] = None
    payload["archived"] = True

    repository = GitHubRepository.model_validate(payload)

    assert repository.description is None
    assert repository.primary_language is None
    assert repository.archived is True
    assert repository.fork is True


def test_github_file_content_preserves_normalized_fields() -> None:
    github_file = GitHubFileContent(
        path="README.md",
        name="README.md",
        content="# DevLens",
        size=9,
        sha="abc123",
    )

    assert github_file.path == "README.md"
    assert github_file.name == "README.md"
    assert github_file.content == "# DevLens"
    assert github_file.size == 9
    assert github_file.sha == "abc123"


def test_github_repository_tree_preserves_paths_and_completeness() -> None:
    repository_tree = GitHubRepositoryTree(
        paths=[
            "README.md",
            "backend/tests/test_api.py",
        ],
        truncated=True,
    )

    assert repository_tree.model_dump() == {
        "paths": [
            "README.md",
            "backend/tests/test_api.py",
        ],
        "truncated": True,
    }


"""
Yalnızca GitHubUser schema davranışını test eder.
"""
