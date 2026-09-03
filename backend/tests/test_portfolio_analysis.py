import asyncio
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from app.schemas.analysis import (
    ExcludedPortfolioRepository,
    PortfolioRepositoryAnalysis,
    PortfolioRepositoryExclusionReason,
    PortfolioRepositoryFailure,
    PortfolioRepositoryFailureCode,
    PortfolioRepositoryResult,
    PortfolioRepositorySelection,
    ReadmeAnalysis,
    RepositoryAnalysis,
    RepositoryCategory,
    RepositoryCategoryMatch,
    RepositoryClassification,
    RepositoryStructureSignals,
    TechnologyAnalysis,
)
from app.schemas.github import GitHubRepository
from app.services.github.client import GitHubClient
from app.services.github.client import GitHubMalformedResponseError
import app.services.portfolio_analysis as portfolio_analysis_module
from app.services.portfolio_analysis import (
    DEFAULT_MAX_CONCURRENCY,
    analyze_portfolio_repositories,
)
from app.services.repository_scoring import score_repository


def create_repository(
    name: str,
    *,
    archived: bool = False,
    fork: bool = False,
) -> GitHubRepository:
    return GitHubRepository.model_validate(
        {
            "name": name,
            "description": None,
            "html_url": f"https://github.com/octocat/{name}",
            "language": "Python",
            "stargazers_count": 0,
            "forks_count": 0,
            "topics": [],
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-02-20T15:30:00Z",
            "archived": archived,
            "fork": fork,
            "default_branch": "main",
        }
    )


def create_selection(
    repositories: list[GitHubRepository],
    *,
    excluded: list[ExcludedPortfolioRepository] | None = None,
    version: str = "v1",
) -> PortfolioRepositorySelection:
    return PortfolioRepositorySelection(
        version=version,
        selected=repositories,
        excluded=[] if excluded is None else excluded,
    )


def create_analysis(
    repository: GitHubRepository,
    *,
    tree_truncated: bool = False,
) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        repository=repository,
        readme=ReadmeAnalysis(
            exists=False,
            content_length=0,
            has_title=False,
            has_description=False,
            has_installation=False,
            has_usage=False,
            has_technologies=False,
            has_requirements=False,
            has_images=False,
            has_demo_link=False,
        ),
        structure=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
        tree_truncated=tree_truncated,
        technologies=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        classification=RepositoryClassification(
            categories=[
                RepositoryCategoryMatch(
                    category=RepositoryCategory.OTHER,
                    evidence_score=0,
                    evidence=["No supported category evidence was detected."],
                )
            ],
            primary_category=RepositoryCategory.OTHER,
        ),
    )


def create_timeout(repository: GitHubRepository) -> httpx.ReadTimeout:
    request = httpx.Request(
        "GET",
        f"https://api.github.com/repos/octocat/{repository.name}",
    )
    return httpx.ReadTimeout(
        "Synthetic GitHub timeout.",
        request=request,
    )


def test_empty_selection_returns_typed_result_without_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyze_mock = AsyncMock()
    score_mock = Mock()
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection([], version="selection-v1"),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert result == PortfolioRepositoryAnalysis(
        selection_version="selection-v1",
        repositories=[],
        failures=[],
        has_failures=False,
    )
    analyze_mock.assert_not_awaited()
    score_mock.assert_not_called()


def test_single_repository_analysis_attaches_existing_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository("alpha")
    analysis = create_analysis(repository, tree_truncated=True)
    score = score_repository(analysis)
    client = AsyncMock(spec=GitHubClient)
    analyze_mock = AsyncMock(return_value=analysis)
    score_mock = Mock(return_value=score)
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection([repository]),
            client=client,
        )
    )

    assert result.repositories == [
        PortfolioRepositoryResult(
            repository=repository,
            analysis=analysis,
            score=score,
        )
    ]
    assert result.failures == []
    assert result.has_failures is False
    assert result.repositories[0].score.is_partial is True
    analyze_mock.assert_awaited_once_with(
        owner="octocat",
        repository=repository,
        client=client,
    )
    score_mock.assert_called_once_with(analysis)


def test_multiple_selected_repositories_are_analyzed_and_scored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]
    analyses = {
        repository.name: create_analysis(repository)
        for repository in repositories
    }

    async def fake_analyze_repository(
        *,
        owner: str,
        repository: GitHubRepository,
        client: GitHubClient,
    ) -> RepositoryAnalysis:
        assert owner == "octocat"
        return analyses[repository.name]

    score_mock = Mock(side_effect=score_repository)
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        fake_analyze_repository,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection(repositories),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert [item.repository.name for item in result.repositories] == [
        "alpha",
        "bravo",
        "charlie",
    ]
    assert [item.analysis for item in result.repositories] == list(
        analyses.values()
    )
    assert all(item.score.version == "v1" for item in result.repositories)
    assert score_mock.call_count == 3


def test_excluded_repositories_are_not_analyzed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = create_repository("selected")
    excluded = create_repository("excluded-fork", fork=True)
    analysis = create_analysis(selected)
    client = AsyncMock(spec=GitHubClient)
    analyze_mock = AsyncMock(return_value=analysis)
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )

    selection = create_selection(
        [selected],
        excluded=[
            ExcludedPortfolioRepository(
                repository=excluded,
                reasons=[
                    PortfolioRepositoryExclusionReason.FORK_REPOSITORY,
                ],
            )
        ],
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=selection,
            client=client,
        )
    )

    assert [item.repository for item in result.repositories] == [selected]
    analyze_mock.assert_awaited_once_with(
        owner="octocat",
        repository=selected,
        client=client,
    )


def test_success_output_order_is_stable_under_reverse_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]
    analyses = {
        repository.name: create_analysis(repository)
        for repository in repositories
    }

    async def exercise() -> tuple[PortfolioRepositoryAnalysis, list[str]]:
        releases = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        started = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        completed = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        completion_order: list[str] = []

        async def fake_analyze_repository(
            *,
            owner: str,
            repository: GitHubRepository,
            client: GitHubClient,
        ) -> RepositoryAnalysis:
            started[repository.name].set()
            await releases[repository.name].wait()
            completion_order.append(repository.name)
            completed[repository.name].set()
            return analyses[repository.name]

        monkeypatch.setattr(
            portfolio_analysis_module,
            "analyze_repository",
            fake_analyze_repository,
        )

        task = asyncio.create_task(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection(repositories),
                client=AsyncMock(spec=GitHubClient),
                max_concurrency=3,
            )
        )

        for repository in repositories:
            await asyncio.wait_for(
                started[repository.name].wait(),
                timeout=1,
            )

        for repository in reversed(repositories):
            releases[repository.name].set()
            await asyncio.wait_for(
                completed[repository.name].wait(),
                timeout=1,
            )

        return await asyncio.wait_for(task, timeout=1), completion_order

    result, completion_order = asyncio.run(exercise())

    assert completion_order == ["charlie", "bravo", "alpha"]
    assert [item.repository.name for item in result.repositories] == [
        "alpha",
        "bravo",
        "charlie",
    ]


def test_repository_concurrency_is_bounded_at_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository(f"repository-{index}")
        for index in range(5)
    ]

    async def exercise() -> tuple[int, int, PortfolioRepositoryAnalysis]:
        active = 0
        maximum_active = 0
        limit_reached = asyncio.Event()
        release = asyncio.Event()

        async def fake_analyze_repository(
            *,
            owner: str,
            repository: GitHubRepository,
            client: GitHubClient,
        ) -> RepositoryAnalysis:
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)

            if active == 2:
                limit_reached.set()

            try:
                await release.wait()
                return create_analysis(repository)
            finally:
                active -= 1

        monkeypatch.setattr(
            portfolio_analysis_module,
            "analyze_repository",
            fake_analyze_repository,
        )

        task = asyncio.create_task(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection(repositories),
                client=AsyncMock(spec=GitHubClient),
                max_concurrency=2,
            )
        )

        await asyncio.wait_for(limit_reached.wait(), timeout=1)
        active_at_limit = active
        release.set()
        result = await asyncio.wait_for(task, timeout=1)

        return active_at_limit, maximum_active, result

    active_at_limit, maximum_active, result = asyncio.run(exercise())

    assert active_at_limit == 2
    assert maximum_active == 2
    assert len(result.repositories) == 5


def test_operational_timeout_is_isolated_from_successful_repositories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]

    async def fake_analyze_repository(
        *,
        owner: str,
        repository: GitHubRepository,
        client: GitHubClient,
    ) -> RepositoryAnalysis:
        if repository.name == "bravo":
            raise create_timeout(repository)

        return create_analysis(repository)

    score_mock = Mock(side_effect=score_repository)
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        fake_analyze_repository,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection(repositories),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert [item.repository.name for item in result.repositories] == [
        "alpha",
        "charlie",
    ]
    assert result.failures == [
        PortfolioRepositoryFailure(
            repository=repositories[1],
            code=PortfolioRepositoryFailureCode.GITHUB_TIMEOUT,
            message=(
                "GitHub request timed out during repository analysis."
            ),
        )
    ]
    assert result.has_failures is True
    assert score_mock.call_count == 2


def test_malformed_provider_response_is_isolated_from_successful_repositories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [create_repository("valid"), create_repository("malformed")]

    async def fake_analyze_repository(*, owner, repository, client):
        if repository.name == "malformed":
            raise GitHubMalformedResponseError("invalid tree")
        return create_analysis(repository)

    monkeypatch.setattr(
        portfolio_analysis_module, "analyze_repository", fake_analyze_repository
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection(repositories),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert [item.repository.name for item in result.repositories] == ["valid"]
    assert result.failures[0].code == PortfolioRepositoryFailureCode.GITHUB_UPSTREAM_ERROR
    assert result.has_failures is True


@pytest.mark.parametrize(
    "status_code",
    [httpx.codes.FORBIDDEN, httpx.codes.TOO_MANY_REQUESTS],
)
def test_rate_limit_is_returned_as_stable_typed_failure(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    repository = create_repository("rate-limited")
    request = httpx.Request(
        "GET",
        "https://api.github.com/repos/octocat/rate-limited",
    )
    response = httpx.Response(
        status_code,
        request=request,
    )
    analyze_mock = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Synthetic rate limit response.",
            request=request,
            response=response,
        )
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection([repository]),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert result.repositories == []
    assert result.failures == [
        PortfolioRepositoryFailure(
            repository=repository,
            code=PortfolioRepositoryFailureCode.GITHUB_RATE_LIMIT,
            message=(
                "GitHub API rate limit prevented repository analysis."
            ),
        )
    ]
    assert result.has_failures is True


@pytest.mark.parametrize(
    ("error_kind", "expected_code", "expected_message"),
    [
        (
            "not_found",
            PortfolioRepositoryFailureCode.GITHUB_REPOSITORY_NOT_FOUND,
            "GitHub repository was not found during analysis.",
        ),
        (
            "upstream",
            PortfolioRepositoryFailureCode.GITHUB_UPSTREAM_ERROR,
            (
                "GitHub returned an unexpected response during "
                "repository analysis."
            ),
        ),
        (
            "request_error",
            PortfolioRepositoryFailureCode.GITHUB_UNAVAILABLE,
            "GitHub was unavailable during repository analysis.",
        ),
    ],
)
def test_other_operational_errors_have_stable_typed_failures(
    monkeypatch: pytest.MonkeyPatch,
    error_kind: str,
    expected_code: PortfolioRepositoryFailureCode,
    expected_message: str,
) -> None:
    repository = create_repository("operational-failure")
    request = httpx.Request(
        "GET",
        "https://api.github.com/repos/octocat/operational-failure",
    )

    if error_kind == "request_error":
        error: httpx.HTTPError = httpx.ConnectError(
            "Synthetic connection failure.",
            request=request,
        )
    else:
        status_code = (
            httpx.codes.NOT_FOUND
            if error_kind == "not_found"
            else httpx.codes.SERVICE_UNAVAILABLE
        )
        response = httpx.Response(status_code, request=request)
        error = httpx.HTTPStatusError(
            "Synthetic GitHub HTTP failure.",
            request=request,
            response=response,
        )

    score_mock = Mock()
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        AsyncMock(side_effect=error),
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection([repository]),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert result.repositories == []
    assert result.failures == [
        PortfolioRepositoryFailure(
            repository=repository,
            code=expected_code,
            message=expected_message,
        )
    ]
    assert result.has_failures is True
    score_mock.assert_not_called()


def test_failure_output_order_is_stable_under_reverse_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]

    async def exercise() -> tuple[PortfolioRepositoryAnalysis, list[str]]:
        releases = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        started = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        completed = {
            repository.name: asyncio.Event()
            for repository in repositories
        }
        completion_order: list[str] = []

        async def fake_analyze_repository(
            *,
            owner: str,
            repository: GitHubRepository,
            client: GitHubClient,
        ) -> RepositoryAnalysis:
            started[repository.name].set()
            await releases[repository.name].wait()
            completion_order.append(repository.name)
            completed[repository.name].set()
            raise create_timeout(repository)

        monkeypatch.setattr(
            portfolio_analysis_module,
            "analyze_repository",
            fake_analyze_repository,
        )

        task = asyncio.create_task(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection(repositories),
                client=AsyncMock(spec=GitHubClient),
                max_concurrency=3,
            )
        )

        for repository in repositories:
            await asyncio.wait_for(
                started[repository.name].wait(),
                timeout=1,
            )

        for repository in reversed(repositories):
            releases[repository.name].set()
            await asyncio.wait_for(
                completed[repository.name].wait(),
                timeout=1,
            )

        return await asyncio.wait_for(task, timeout=1), completion_order

    result, completion_order = asyncio.run(exercise())

    assert completion_order == ["charlie", "bravo", "alpha"]
    assert [failure.repository.name for failure in result.failures] == [
        "alpha",
        "bravo",
        "charlie",
    ]


def test_unexpected_analyzer_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository("broken-analysis")
    analyze_mock = AsyncMock(
        side_effect=RuntimeError("Unexpected analyzer defect."),
    )
    score_mock = Mock()
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Unexpected analyzer defect",
    ):
        asyncio.run(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection([repository]),
                client=AsyncMock(spec=GitHubClient),
            )
        )

    score_mock.assert_not_called()


def test_unexpected_error_cancels_and_drains_sibling_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("broken-analysis"),
        create_repository("pending-analysis"),
    ]

    async def exercise() -> bool:
        sibling_started = asyncio.Event()
        sibling_cancelled = asyncio.Event()

        async def fake_analyze_repository(
            *,
            owner: str,
            repository: GitHubRepository,
            client: GitHubClient,
        ) -> RepositoryAnalysis:
            if repository.name == "broken-analysis":
                await sibling_started.wait()
                raise RuntimeError("Unexpected analyzer defect.")

            sibling_started.set()

            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                sibling_cancelled.set()
                raise

            raise AssertionError("Pending analysis should have been cancelled.")

        monkeypatch.setattr(
            portfolio_analysis_module,
            "analyze_repository",
            fake_analyze_repository,
        )

        with pytest.raises(
            RuntimeError,
            match="Unexpected analyzer defect",
        ):
            await analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection(repositories),
                client=AsyncMock(spec=GitHubClient),
            )

        return sibling_cancelled.is_set()

    assert asyncio.run(exercise()) is True


def test_unexpected_scoring_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_repository("broken-score")
    analysis = create_analysis(repository)
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        AsyncMock(return_value=analysis),
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        Mock(side_effect=RuntimeError("Unexpected scoring defect.")),
    )

    with pytest.raises(
        RuntimeError,
        match="Unexpected scoring defect",
    ):
        asyncio.run(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection([repository]),
                client=AsyncMock(spec=GitHubClient),
            )
        )


def test_all_operational_failures_return_empty_successes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = [
        create_repository("alpha"),
        create_repository("bravo"),
        create_repository("charlie"),
    ]

    async def fake_analyze_repository(
        *,
        owner: str,
        repository: GitHubRepository,
        client: GitHubClient,
    ) -> RepositoryAnalysis:
        raise create_timeout(repository)

    score_mock = Mock()
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        fake_analyze_repository,
    )
    monkeypatch.setattr(
        portfolio_analysis_module,
        "score_repository",
        score_mock,
    )

    result = asyncio.run(
        analyze_portfolio_repositories(
            owner="octocat",
            selection=create_selection(repositories),
            client=AsyncMock(spec=GitHubClient),
        )
    )

    assert result.repositories == []
    assert [failure.repository for failure in result.failures] == repositories
    assert all(
        failure.code is PortfolioRepositoryFailureCode.GITHUB_TIMEOUT
        for failure in result.failures
    )
    assert result.has_failures is True
    score_mock.assert_not_called()


@pytest.mark.parametrize("max_concurrency", [0, -1])
def test_non_positive_concurrency_is_rejected_before_work_starts(
    monkeypatch: pytest.MonkeyPatch,
    max_concurrency: int,
) -> None:
    repository = create_repository("alpha")
    analyze_mock = AsyncMock()
    monkeypatch.setattr(
        portfolio_analysis_module,
        "analyze_repository",
        analyze_mock,
    )

    with pytest.raises(
        ValueError,
        match="max_concurrency must be greater than zero",
    ):
        asyncio.run(
            analyze_portfolio_repositories(
                owner="octocat",
                selection=create_selection([repository]),
                client=AsyncMock(spec=GitHubClient),
                max_concurrency=max_concurrency,
            )
        )

    analyze_mock.assert_not_awaited()


def test_default_repository_concurrency_is_three() -> None:
    assert DEFAULT_MAX_CONCURRENCY == 3
