from app.schemas.analysis import GitHubPortfolioAnalysis
from app.services.github.client import GitHubClient
from app.services.portfolio_aggregation import aggregate_portfolio
from app.services.portfolio_analysis import (
    DEFAULT_MAX_CONCURRENCY,
    analyze_portfolio_repositories,
)
from app.services.portfolio_intelligence import build_portfolio_intelligence
from app.services.portfolio_repository_selection import (
    select_portfolio_repositories,
)
from app.services.github.client import (
    GitHubRequestBudget,
    use_github_request_budget,
)
from app.services.portfolio_scoring import score_portfolio


async def analyze_github_portfolio(
    *,
    username: str,
    client: GitHubClient,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
) -> GitHubPortfolioAnalysis:
    """Run the complete deterministic portfolio analysis use case."""

    with use_github_request_budget(GitHubRequestBudget()):
        user = await client.get_user(username)
        repositories = await client.get_repositories(username)
        selection = select_portfolio_repositories(repositories)
        repository_analysis = await analyze_portfolio_repositories(
            owner=username,
            selection=selection,
            client=client,
            max_concurrency=max_concurrency,
        )
    aggregation = aggregate_portfolio(repository_analysis)
    intelligence = build_portfolio_intelligence(aggregation)
    score = score_portfolio(aggregation)

    return GitHubPortfolioAnalysis(
        user=user,
        selection=selection,
        repository_analysis=repository_analysis,
        aggregation=aggregation,
        intelligence=intelligence,
        score=score,
    )
