import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from app.schemas.analysis import RepositoryCategory
from app.schemas.github import (
    GitHubFileContent,
    GitHubRepository,
    GitHubRepositoryTree,
)
from app.services.github.client import (
    IMPORTANT_REPOSITORY_FILE_PATHS,
    GitHubClient,
)
from app.services.repository_analysis import analyze_repository


def create_repository(
    *,
    description: str | None = None,
    topics: list[str] | None = None,
    archived: bool = False,
    fork: bool = False,
) -> GitHubRepository:
    return GitHubRepository.model_validate(
        {
            "name": "devlens",
            "description": description,
            "html_url": "https://github.com/octocat/devlens",
            "language": "Python",
            "stargazers_count": 42,
            "forks_count": 7,
            "topics": [] if topics is None else topics,
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-02-20T15:30:00Z",
            "archived": archived,
            "fork": fork,
            "default_branch": "main",
        }
    )


def create_file(
    path: str,
    content: str,
) -> GitHubFileContent:
    return GitHubFileContent(
        path=path,
        name=path,
        content=content,
        size=len(content.encode("utf-8")),
        sha=f"sha-{path}",
    )


def create_missing_files() -> dict[str, GitHubFileContent | None]:
    return {path: None for path in IMPORTANT_REPOSITORY_FILE_PATHS}


def test_analyze_repository_composes_full_repository() -> None:
    repository = create_repository(
        description="A full stack web interface with a REST API.",
        topics=["backend", "frontend"],
    )
    readme_content = """# DevLens

DevLens provides a full stack web interface and REST API for reviewing repository evidence.

## Installation

Install the dependencies.

## Usage

Run the application.
"""

    important_files = create_missing_files()
    important_files["README.md"] = create_file(
        "README.md",
        readme_content,
    )
    important_files["requirements.txt"] = create_file(
        "requirements.txt",
        "FastAPI>=0.115\npytest>=8\n",
    )
    important_files["pyproject.toml"] = create_file(
        "pyproject.toml",
        '[project]\ndependencies = ["fastapi>=0.115"]\n',
    )
    important_files["package.json"] = create_file(
        "package.json",
        """{
  "dependencies": {
    "react": "^19.0.0",
    "next": "^15.0.0"
  }
}""",
    )

    client = AsyncMock(spec=GitHubClient)
    client.get_important_files.return_value = important_files
    client.get_repository_tree.return_value = GitHubRepositoryTree(
        paths=[
            "README.md",
            "backend/app/main.py",
            "backend/tests/test_api.py",
            ".github/workflows/ci.yml",
            "Dockerfile",
        ],
        truncated=False,
    )

    result = asyncio.run(
        analyze_repository(
            owner="octocat",
            repository=repository,
            client=client,
        )
    )

    assert result.repository == repository

    assert result.readme.exists is True
    assert result.readme.has_title is True
    assert result.readme.has_description is True
    assert result.readme.has_installation is True
    assert result.readme.has_usage is True

    assert result.technologies.dependencies == [
        "fastapi",
        "next",
        "pytest",
        "react",
    ]
    assert {technology.name for technology in result.technologies.technologies} == {
        "FastAPI",
        "Next.js",
        "pytest",
        "React",
    }

    assert result.structure.has_tests is True
    assert result.structure.has_ci is True
    assert result.structure.has_dockerfile is True
    assert result.tree_truncated is False

    assert result.classification.primary_category is RepositoryCategory.FULL_STACK

    backend_match = next(
        match
        for match in result.classification.categories
        if match.category is RepositoryCategory.BACKEND
    )
    assert 'README phrase: "rest api"' in backend_match.evidence

    assert set(result.model_dump()) == {
        "repository",
        "readme",
        "structure",
        "tree_truncated",
        "technologies",
        "classification",
    }

    client.get_important_files.assert_awaited_once_with(
        owner="octocat",
        repository=repository.name,
        ref=repository.default_branch,
    )
    client.get_repository_tree.assert_awaited_once_with(
        owner="octocat",
        repository=repository.name,
        ref=repository.default_branch,
    )


def test_analyze_repository_supports_missing_readme_and_manifests() -> None:
    repository = create_repository(
        archived=True,
        fork=True,
    )
    client = AsyncMock(spec=GitHubClient)
    client.get_important_files.return_value = create_missing_files()
    client.get_repository_tree.return_value = GitHubRepositoryTree(
        paths=["src/main.py"],
        truncated=False,
    )

    result = asyncio.run(
        analyze_repository(
            owner="octocat",
            repository=repository,
            client=client,
        )
    )

    assert result.repository.archived is True
    assert result.repository.fork is True

    assert result.readme.exists is False
    assert result.readme.content_length == 0

    assert result.technologies.dependencies == []
    assert result.technologies.technologies == []

    assert result.classification.primary_category is RepositoryCategory.OTHER


def test_analyze_repository_propagates_github_operational_error() -> None:
    request = httpx.Request(
        "GET",
        "https://api.github.com/repos/octocat/devlens/contents/README.md",
    )
    client = AsyncMock(spec=GitHubClient)
    client.get_important_files.side_effect = httpx.ReadTimeout(
        "GitHub request timed out.",
        request=request,
    )

    with pytest.raises(
        httpx.ReadTimeout,
        match="timed out",
    ):
        asyncio.run(
            analyze_repository(
                owner="octocat",
                repository=create_repository(),
                client=client,
            )
        )


def test_analyze_repository_preserves_partial_tree_evidence() -> None:
    client = AsyncMock(spec=GitHubClient)
    client.get_important_files.return_value = create_missing_files()
    client.get_repository_tree.return_value = GitHubRepositoryTree(
        paths=["backend/tests/test_api.py"],
        truncated=True,
    )

    result = asyncio.run(
        analyze_repository(
            owner="octocat",
            repository=create_repository(),
            client=client,
        )
    )

    assert result.tree_truncated is True
    assert result.structure.has_tests is True
