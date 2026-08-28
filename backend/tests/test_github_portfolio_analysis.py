import asyncio
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import app.services.github_portfolio_analysis as application_module
from app.schemas.analysis import (
    GitHubPortfolioAnalysis,
    PortfolioRepositoryAnalysis,
    PortfolioRepositoryFailureCode,
)
from app.schemas.github import (
    GitHubFileContent,
    GitHubRepository,
    GitHubRepositoryTree,
    GitHubUser,
)
from app.services.github.client import (
    IMPORTANT_REPOSITORY_FILE_PATHS,
    GitHubClient,
)
from app.services.github_portfolio_analysis import analyze_github_portfolio


def create_user(*, public_repos: int = 0) -> GitHubUser:
    return GitHubUser.model_validate(
        {
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://avatars.example/octocat.png",
            "bio": "A synthetic GitHub profile.",
            "public_repos": public_repos,
            "followers": 10,
            "following": 2,
            "html_url": "https://github.com/octocat",
            "created_at": "2011-01-25T18:44:36Z",
        }
    )


def create_repository(
    name: str,
    *,
    archived: bool = False,
    fork: bool = False,
) -> GitHubRepository:
    return GitHubRepository.model_validate(
        {
            "name": name,
            "description": (
                "A deterministic backend application for portfolio analysis."
            ),
            "html_url": f"https://github.com/octocat/{name}",
            "language": "Python",
            "stargazers_count": 0,
            "forks_count": 0,
            "topics": ["backend"],
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-02-20T15:30:00Z",
            "archived": archived,
            "fork": fork,
            "default_branch": "main",
        }
    )


def create_file(path: str, content: str) -> GitHubFileContent:
    return GitHubFileContent(
        path=path,
        name=path,
        content=content,
        size=len(content.encode("utf-8")),
        sha=f"sha-{path}",
    )


def create_files(
    repository_name: str,
    *,
    rich_evidence: bool,
) -> dict[str, GitHubFileContent | None]:
    files: dict[str, GitHubFileContent | None] = {
        path: None for path in IMPORTANT_REPOSITORY_FILE_PATHS
    }

    if not rich_evidence:
        return files

    files["README.md"] = create_file(
        "README.md",
        (
            f"# {repository_name}\n\n"
            "This repository provides a deterministic backend application "
            "service for analyzing public portfolio evidence.\n\n"
            "## Installation\n\n"
            "Install the project dependencies.\n\n"
            "## Usage\n\n"
            "Run the application service.\n"
        ),
    )
    files["requirements.txt"] = create_file(
        "requirements.txt",
        "fastapi>=0.115\npytest>=8\n",
    )
    return files


def create_client(
    repositories: list[GitHubRepository],
    *,
    failed_repository_names: set[str] | None = None,
    partial_repository_names: set[str] | None = None,
    rich_evidence: bool = False,
) -> AsyncMock:
    failed_names = failed_repository_names or set()
    partial_names = partial_repository_names or set()
    client = AsyncMock(spec=GitHubClient)
    client.get_user.return_value = create_user(
        public_repos=len(repositories)
    )
    client.get_repositories.return_value = repositories

    async def get_important_files(
        *,
        owner: str,
        repository: str,
        ref: str | None = None,
    ) -> dict[str, GitHubFileContent | None]:
        if repository in failed_names:
            request = httpx.Request(
                "GET",
                f"https://api.github.com/repos/{owner}/{repository}",
            )
            raise httpx.ReadTimeout(
                "Synthetic repository timeout.",
                request=request,
            )

        return create_files(
            repository,
            rich_evidence=rich_evidence,
        )

    async def get_repository_tree(
        owner: str,
        repository: str,
        ref: str,
    ) -> GitHubRepositoryTree:
        paths = ["src/main.py"]

        if rich_evidence:
            paths = [
                "README.md",
                "tests/test_application.py",
                ".github/workflows/ci.yml",
                ".gitignore",
                "LICENSE",
            ]

        return GitHubRepositoryTree(
            paths=paths,
            truncated=repository in partial_names,
        )

    client.get_important_files.side_effect = get_important_files
    client.get_repository_tree.side_effect = get_repository_tree
    return client


def test_successful_end_to_end_application_flow() -> None:
    repositories = [
        create_repository("zeta"),
        create_repository("forked", fork=True),
        create_repository("alpha"),
        create_repository("archived", archived=True),
    ]
    client = create_client(repositories, rich_evidence=True)

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert isinstance(result, GitHubPortfolioAnalysis)
    assert result.user == create_user(public_repos=4)
    assert [item.name for item in result.selection.selected] == [
        "alpha",
        "zeta",
    ]
    assert [
        item.repository.name for item in result.selection.excluded
    ] == ["archived", "forked"]
    assert [
        item.repository.name
        for item in result.repository_analysis.repositories
    ] == ["alpha", "zeta"]
    assert result.repository_analysis.failures == []
    assert result.aggregation.successful_repository_count == 2
    assert result.aggregation.failed_repository_count == 0
    assert result.intelligence.strength_signals
    assert result.score.is_available is True
    assert result.score.scored_repository_count == 2
    assert result.score.overall_score is not None

    client.get_user.assert_awaited_once_with("octocat")
    client.get_repositories.assert_awaited_once_with("octocat")
    assert {
        call.kwargs["repository"]
        for call in client.get_important_files.await_args_list
    } == {"alpha", "zeta"}
    assert {
        call.kwargs["repository"]
        for call in client.get_repository_tree.await_args_list
    } == {"alpha", "zeta"}

    serialized = result.model_dump(mode="json")
    assert set(serialized) == {
        "user",
        "selection",
        "repository_analysis",
        "aggregation",
        "intelligence",
        "score",
    }
    readme = serialized["repository_analysis"]["repositories"][0][
        "analysis"
    ]["readme"]
    assert "content" not in readme


def test_zero_public_repositories_returns_successful_no_data_result() -> None:
    client = create_client([])

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert result.selection.selected == []
    assert result.selection.excluded == []
    assert result.repository_analysis.repositories == []
    assert result.repository_analysis.failures == []
    assert result.aggregation.successful_repository_count == 0
    assert result.intelligence.strength_signals == []
    assert result.intelligence.limitations
    assert result.score.is_available is False
    assert result.score.overall_score is None
    client.get_user.assert_awaited_once_with("octocat")
    client.get_repositories.assert_awaited_once_with("octocat")
    client.get_important_files.assert_not_awaited()
    client.get_repository_tree.assert_not_awaited()


def test_all_repositories_excluded_returns_successful_no_data_result() -> None:
    repositories = [
        create_repository("forked", fork=True),
        create_repository("archived", archived=True),
    ]
    client = create_client(repositories)

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert result.selection.selected == []
    assert len(result.selection.excluded) == 2
    assert result.repository_analysis.repositories == []
    assert result.aggregation.selected_repository_count == 0
    assert result.score.is_available is False
    client.get_important_files.assert_not_awaited()
    client.get_repository_tree.assert_not_awaited()


def test_user_fetch_failure_stops_the_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "https://api.github.com/users/missing")
    response = httpx.Response(404, request=request)
    error = httpx.HTTPStatusError(
        "Synthetic user not found.",
        request=request,
        response=response,
    )
    client = AsyncMock(spec=GitHubClient)
    client.get_user.side_effect = error
    selection_mock = Mock()
    repository_analysis_mock = AsyncMock()
    aggregation_mock = Mock()
    intelligence_mock = Mock()
    score_mock = Mock()
    monkeypatch.setattr(
        application_module,
        "select_portfolio_repositories",
        selection_mock,
    )
    monkeypatch.setattr(
        application_module,
        "analyze_portfolio_repositories",
        repository_analysis_mock,
    )
    monkeypatch.setattr(
        application_module,
        "aggregate_portfolio",
        aggregation_mock,
    )
    monkeypatch.setattr(
        application_module,
        "build_portfolio_intelligence",
        intelligence_mock,
    )
    monkeypatch.setattr(
        application_module,
        "score_portfolio",
        score_mock,
    )

    with pytest.raises(httpx.HTTPStatusError, match="user not found"):
        asyncio.run(
            analyze_github_portfolio(
                username="missing",
                client=client,
            )
        )

    client.get_user.assert_awaited_once_with("missing")
    client.get_repositories.assert_not_awaited()
    selection_mock.assert_not_called()
    repository_analysis_mock.assert_not_awaited()
    aggregation_mock.assert_not_called()
    intelligence_mock.assert_not_called()
    score_mock.assert_not_called()


def test_repository_list_failure_stops_the_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request(
        "GET",
        "https://api.github.com/users/octocat/repos",
    )
    client = AsyncMock(spec=GitHubClient)
    client.get_user.return_value = create_user()
    client.get_repositories.side_effect = httpx.ReadTimeout(
        "Synthetic repository list timeout.",
        request=request,
    )
    selection_mock = Mock()
    repository_analysis_mock = AsyncMock()
    aggregation_mock = Mock()
    intelligence_mock = Mock()
    score_mock = Mock()
    monkeypatch.setattr(
        application_module,
        "select_portfolio_repositories",
        selection_mock,
    )
    monkeypatch.setattr(
        application_module,
        "analyze_portfolio_repositories",
        repository_analysis_mock,
    )
    monkeypatch.setattr(
        application_module,
        "aggregate_portfolio",
        aggregation_mock,
    )
    monkeypatch.setattr(
        application_module,
        "build_portfolio_intelligence",
        intelligence_mock,
    )
    monkeypatch.setattr(
        application_module,
        "score_portfolio",
        score_mock,
    )

    with pytest.raises(httpx.ReadTimeout, match="repository list timeout"):
        asyncio.run(
            analyze_github_portfolio(
                username="octocat",
                client=client,
            )
        )

    client.get_user.assert_awaited_once_with("octocat")
    client.get_repositories.assert_awaited_once_with("octocat")
    selection_mock.assert_not_called()
    repository_analysis_mock.assert_not_awaited()
    aggregation_mock.assert_not_called()
    intelligence_mock.assert_not_called()
    score_mock.assert_not_called()


def test_partial_repository_execution_preserves_successes_and_failure() -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]
    client = create_client(
        repositories,
        failed_repository_names={"charlie"},
        rich_evidence=True,
    )

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert len(result.repository_analysis.repositories) == 2
    assert len(result.repository_analysis.failures) == 1
    assert (
        result.repository_analysis.failures[0].code
        is PortfolioRepositoryFailureCode.GITHUB_TIMEOUT
    )
    assert result.aggregation.successful_repository_count == 2
    assert result.aggregation.failed_repository_count == 1
    assert all(
        signal.analyzed_repository_count == 2
        for signal in result.intelligence.strength_signals
    )
    assert result.score.scored_repository_count == 2
    assert result.score.is_available is True
    assert result.score.is_partial is True


def test_partial_structure_evidence_is_preserved_in_final_result() -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
    ]
    client = create_client(
        repositories,
        partial_repository_names={"bravo"},
        rich_evidence=True,
    )

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert result.repository_analysis.has_failures is False
    assert result.aggregation.partial_evidence_repository_count == 1
    assert result.intelligence.limitations == [
        "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yokluğa dayalı "
        "yapı ve repository hijyeni içgörüleri eksik olabilir."
    ]
    assert result.score.is_available is True
    assert result.score.is_partial is True
    assert result.score.limitations == [
        "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı "
        "skor kanıtı eksik olabilir."
    ]


def test_single_success_after_failures_keeps_score_unavailable() -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]
    client = create_client(
        repositories,
        failed_repository_names={"bravo", "charlie"},
        rich_evidence=True,
    )

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert result.aggregation.successful_repository_count == 1
    assert result.aggregation.failed_repository_count == 2
    assert result.score.scored_repository_count == 1
    assert result.score.is_available is False
    assert result.score.overall_score is None
    assert result.score.is_partial is True


def test_all_selected_repository_failures_return_typed_result() -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]
    client = create_client(
        repositories,
        failed_repository_names={"alpha", "bravo", "charlie"},
    )

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert result.repository_analysis.repositories == []
    assert len(result.repository_analysis.failures) == 3
    assert result.aggregation.successful_repository_count == 0
    assert result.aggregation.failed_repository_count == 3
    assert result.intelligence.strength_signals == []
    assert len(result.intelligence.limitations) == 2
    assert result.score.is_available is False
    assert result.score.overall_score is None
    assert result.score.is_partial is True
    assert len(result.score.limitations) == 2
    client.get_repository_tree.assert_not_awaited()


def test_max_concurrency_override_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = create_client([])
    repository_analysis = PortfolioRepositoryAnalysis(
        selection_version="v1",
        repositories=[],
        failures=[],
        has_failures=False,
    )
    analysis_mock = AsyncMock(return_value=repository_analysis)
    monkeypatch.setattr(
        application_module,
        "analyze_portfolio_repositories",
        analysis_mock,
    )

    result = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
            max_concurrency=7,
        )
    )

    analysis_mock.assert_awaited_once_with(
        owner="octocat",
        selection=result.selection,
        client=client,
        max_concurrency=7,
    )


def test_application_result_is_deterministic() -> None:
    repositories = [
        create_repository("bravo"),
        create_repository("alpha"),
    ]
    client = create_client(repositories, rich_evidence=True)

    first = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )
    second = asyncio.run(
        analyze_github_portfolio(
            username="octocat",
            client=client,
        )
    )

    assert second == first
    assert client.get_user.await_count == 2
    assert client.get_repositories.await_count == 2
