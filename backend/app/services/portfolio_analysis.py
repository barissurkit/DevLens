import asyncio

import httpx

from app.schemas.analysis import (
    PortfolioRepositoryAnalysis,
    PortfolioRepositoryFailure,
    PortfolioRepositoryFailureCode,
    PortfolioRepositoryResult,
    PortfolioRepositorySelection,
)
from app.schemas.github import GitHubRepository
from app.services.github.client import GitHubClient
from app.services.repository_analysis import analyze_repository
from app.services.repository_scoring import score_repository

DEFAULT_MAX_CONCURRENCY = 3


def _operational_failure(
    *,
    repository: GitHubRepository,
    error: (
        httpx.TimeoutException
        | httpx.RequestError
        | httpx.HTTPStatusError
    ),
) -> PortfolioRepositoryFailure:
    if isinstance(error, httpx.TimeoutException):
        code = PortfolioRepositoryFailureCode.GITHUB_TIMEOUT
        message = "GitHub request timed out during repository analysis."
    elif isinstance(error, httpx.RequestError):
        code = PortfolioRepositoryFailureCode.GITHUB_UNAVAILABLE
        message = "GitHub was unavailable during repository analysis."
    elif (
        isinstance(error, httpx.HTTPStatusError)
        and error.response.status_code == httpx.codes.NOT_FOUND
    ):
        code = PortfolioRepositoryFailureCode.GITHUB_REPOSITORY_NOT_FOUND
        message = "GitHub repository was not found during analysis."
    elif (
        isinstance(error, httpx.HTTPStatusError)
        and error.response.status_code
        in {
            httpx.codes.FORBIDDEN,
            httpx.codes.TOO_MANY_REQUESTS,
        }
    ):
        code = PortfolioRepositoryFailureCode.GITHUB_RATE_LIMIT
        message = "GitHub API rate limit prevented repository analysis."
    else:
        code = PortfolioRepositoryFailureCode.GITHUB_UPSTREAM_ERROR
        message = "GitHub returned an unexpected response during repository analysis."

    return PortfolioRepositoryFailure(
        repository=repository,
        code=code,
        message=message,
    )


async def _analyze_selected_repository(
    *,
    owner: str,
    repository: GitHubRepository,
    client: GitHubClient,
    semaphore: asyncio.Semaphore,
) -> PortfolioRepositoryResult | PortfolioRepositoryFailure:
    async with semaphore:
        try:
            analysis = await analyze_repository(
                owner=owner,
                repository=repository,
                client=client,
            )
        except (
            httpx.TimeoutException,
            httpx.RequestError,
            httpx.HTTPStatusError,
        ) as error:
            return _operational_failure(
                repository=repository,
                error=error,
            )

        score = score_repository(analysis)

        return PortfolioRepositoryResult(
            repository=repository,
            analysis=analysis,
            score=score,
        )


async def analyze_portfolio_repositories(
    *,
    owner: str,
    selection: PortfolioRepositorySelection,
    client: GitHubClient,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> PortfolioRepositoryAnalysis:
    """Analyze and score selected repositories with bounded concurrency."""

    if max_concurrency <= 0:
        raise ValueError("max_concurrency must be greater than zero.")

    if not selection.selected:
        return PortfolioRepositoryAnalysis(
            selection_version=selection.version,
            repositories=[],
            failures=[],
            has_failures=False,
        )

    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        asyncio.create_task(
            _analyze_selected_repository(
                owner=owner,
                repository=repository,
                client=client,
                semaphore=semaphore,
            )
        )
        for repository in selection.selected
    ]

    try:
        completed = await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    repositories = [
        result
        for result in completed
        if isinstance(result, PortfolioRepositoryResult)
    ]
    failures = [
        result
        for result in completed
        if isinstance(result, PortfolioRepositoryFailure)
    ]

    return PortfolioRepositoryAnalysis(
        selection_version=selection.version,
        repositories=repositories,
        failures=failures,
        has_failures=bool(failures),
    )
