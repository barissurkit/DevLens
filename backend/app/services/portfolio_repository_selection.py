from app.schemas.analysis import (
    ExcludedPortfolioRepository,
    PortfolioRepositoryExclusionReason,
    PortfolioRepositorySelection,
)
from app.schemas.github import GitHubRepository

PORTFOLIO_REPOSITORY_SELECTION_VERSION = "v1"


def _repository_identity(repository: GitHubRepository) -> str:
    return repository.html_url.casefold()


def _repository_sort_key(
    repository: GitHubRepository,
) -> tuple[str, str, str, str]:
    return (
        repository.name.casefold(),
        repository.name,
        repository.html_url.casefold(),
        repository.html_url,
    )


def _validate_unique_repositories(
    repositories: list[GitHubRepository],
) -> None:
    seen_identities: set[str] = set()
    duplicate_identities: set[str] = set()

    for repository in repositories:
        identity = _repository_identity(repository)

        if identity in seen_identities:
            duplicate_identities.add(identity)
        else:
            seen_identities.add(identity)

    if duplicate_identities:
        identities = ", ".join(sorted(duplicate_identities))
        raise ValueError(
            "Duplicate repository identities are not supported: "
            f"{identities}"
        )


def _exclusion_reasons(
    repository: GitHubRepository,
) -> list[PortfolioRepositoryExclusionReason]:
    reasons: list[PortfolioRepositoryExclusionReason] = []

    if repository.fork:
        reasons.append(
            PortfolioRepositoryExclusionReason.FORK_REPOSITORY
        )

    if repository.archived:
        reasons.append(
            PortfolioRepositoryExclusionReason.ARCHIVED_REPOSITORY
        )

    return reasons


def select_portfolio_repositories(
    repositories: list[GitHubRepository],
) -> PortfolioRepositorySelection:
    """Apply the deterministic V1 portfolio eligibility policy."""

    _validate_unique_repositories(repositories)

    selected: list[GitHubRepository] = []
    excluded: list[ExcludedPortfolioRepository] = []

    for repository in sorted(repositories, key=_repository_sort_key):
        reasons = _exclusion_reasons(repository)

        if reasons:
            excluded.append(
                ExcludedPortfolioRepository(
                    repository=repository,
                    reasons=reasons,
                )
            )
        else:
            selected.append(repository)

    return PortfolioRepositorySelection(
        version=PORTFOLIO_REPOSITORY_SELECTION_VERSION,
        selected=selected,
        excluded=excluded,
    )
