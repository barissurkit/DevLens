import pytest
from app.schemas.analysis import (
    ExcludedPortfolioRepository,
    PortfolioRepositoryExclusionReason,
    PortfolioRepositorySelection,
)
from app.schemas.github import GitHubRepository
from app.services.portfolio_repository_selection import (
    select_portfolio_repositories,
)


def create_repository(
    name: str,
    *,
    archived: bool = False,
    fork: bool = False,
    stars: int = 0,
    forks: int = 0,
    html_url: str | None = None,
) -> GitHubRepository:
    return GitHubRepository.model_validate(
        {
            "name": name,
            "description": None,
            "html_url": (
                f"https://github.com/octocat/{name}"
                if html_url is None
                else html_url
            ),
            "language": None,
            "stargazers_count": stars,
            "forks_count": forks,
            "topics": [],
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-02-20T15:30:00Z",
            "archived": archived,
            "fork": fork,
            "default_branch": "main",
        }
    )


def test_selects_normal_repository_and_returns_v1_policy_version() -> None:
    repository = create_repository("portfolio-project")

    result = select_portfolio_repositories([repository])

    assert result.version == "v1"
    assert result.selected == [repository]
    assert result.excluded == []


@pytest.mark.parametrize(
    ("repository", "expected_reason"),
    [
        (
            create_repository("forked-project", fork=True),
            PortfolioRepositoryExclusionReason.FORK_REPOSITORY,
        ),
        (
            create_repository("archived-project", archived=True),
            PortfolioRepositoryExclusionReason.ARCHIVED_REPOSITORY,
        ),
    ],
)
def test_excludes_repository_for_single_condition(
    repository: GitHubRepository,
    expected_reason: PortfolioRepositoryExclusionReason,
) -> None:
    result = select_portfolio_repositories([repository])

    assert result.selected == []
    assert result.excluded == [
        ExcludedPortfolioRepository(
            repository=repository,
            reasons=[expected_reason],
        )
    ]


def test_preserves_all_exclusion_reasons_in_policy_order() -> None:
    repository = create_repository(
        "archived-fork",
        archived=True,
        fork=True,
    )

    result = select_portfolio_repositories([repository])

    assert result.excluded[0].reasons == [
        PortfolioRepositoryExclusionReason.FORK_REPOSITORY,
        PortfolioRepositoryExclusionReason.ARCHIVED_REPOSITORY,
    ]


def test_empty_input_returns_empty_typed_result() -> None:
    result = select_portfolio_repositories([])

    assert result == PortfolioRepositorySelection(
        version="v1",
        selected=[],
        excluded=[],
    )


def test_mixed_input_is_partitioned_in_neutral_name_order() -> None:
    repositories = [
        create_repository("zeta-normal"),
        create_repository("middle-fork", fork=True),
        create_repository("Alpha-normal"),
        create_repository("beta-archived", archived=True),
        create_repository("also-both", archived=True, fork=True),
    ]

    result = select_portfolio_repositories(repositories)

    assert [repository.name for repository in result.selected] == [
        "Alpha-normal",
        "zeta-normal",
    ]
    assert [
        excluded.repository.name for excluded in result.excluded
    ] == [
        "also-both",
        "beta-archived",
        "middle-fork",
    ]
    assert [excluded.reasons for excluded in result.excluded] == [
        [
            PortfolioRepositoryExclusionReason.FORK_REPOSITORY,
            PortfolioRepositoryExclusionReason.ARCHIVED_REPOSITORY,
        ],
        [PortfolioRepositoryExclusionReason.ARCHIVED_REPOSITORY],
        [PortfolioRepositoryExclusionReason.FORK_REPOSITORY],
    ]


def test_input_order_does_not_change_normalized_output() -> None:
    repositories = [
        create_repository("charlie"),
        create_repository("alpha", archived=True),
        create_repository("bravo", fork=True),
    ]

    forward = select_portfolio_repositories(repositories)
    reversed_input = select_portfolio_repositories(
        list(reversed(repositories))
    )

    assert forward.model_dump() == reversed_input.model_dump()


def test_rejects_duplicate_repository_identity() -> None:
    repositories = [
        create_repository(
            "first-name",
            html_url="https://github.com/octocat/shared-repository",
        ),
        create_repository(
            "second-name",
            html_url="HTTPS://GITHUB.COM/OCTOCAT/SHARED-REPOSITORY",
        ),
    ]

    with pytest.raises(
        ValueError,
        match=(
            "Duplicate repository identities are not supported: "
            "https://github.com/octocat/shared-repository"
        ),
    ):
        select_portfolio_repositories(repositories)


def test_popularity_metrics_do_not_affect_eligibility_or_order() -> None:
    low_popularity = [
        create_repository("bravo", stars=0, forks=0),
        create_repository("alpha", stars=0, forks=0),
    ]
    high_popularity = [
        create_repository("bravo", stars=1_000_000, forks=500_000),
        create_repository("alpha", stars=750_000, forks=250_000),
    ]

    low_result = select_portfolio_repositories(low_popularity)
    high_result = select_portfolio_repositories(high_popularity)

    assert [repository.name for repository in low_result.selected] == [
        "alpha",
        "bravo",
    ]
    assert [repository.name for repository in high_result.selected] == [
        "alpha",
        "bravo",
    ]
    assert low_result.excluded == []
    assert high_result.excluded == []


def test_selection_result_has_typed_serializable_shape() -> None:
    selected = create_repository("selected")
    excluded = create_repository("excluded", fork=True)

    result = select_portfolio_repositories([excluded, selected])

    assert isinstance(result, PortfolioRepositorySelection)
    assert isinstance(result.excluded[0], ExcludedPortfolioRepository)
    assert result.model_dump(mode="json") == {
        "version": "v1",
        "selected": [selected.model_dump(mode="json")],
        "excluded": [
            {
                "repository": excluded.model_dump(mode="json"),
                "reasons": ["fork_repository"],
            }
        ],
    }
