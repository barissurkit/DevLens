import pytest
from app.schemas.analysis import (
    DetectedTechnology,
    PortfolioAggregation,
    PortfolioRepositoryAnalysis,
    PortfolioRepositoryFailure,
    PortfolioRepositoryFailureCode,
    PortfolioRepositoryResult,
    ReadmeAnalysis,
    RepositoryAnalysis,
    RepositoryCategory,
    RepositoryCategoryMatch,
    RepositoryClassification,
    RepositoryScore,
    RepositoryStructureSignals,
    ScoreDimensionResult,
    ScoreRuleResult,
    TechnologyAnalysis,
)
from app.schemas.github import GitHubRepository
from app.services.portfolio_aggregation import aggregate_portfolio


def create_repository(name: str) -> GitHubRepository:
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
            "archived": False,
            "fork": False,
            "default_branch": "main",
        }
    )


def create_score(
    overall_score: int,
    *,
    is_partial: bool = False,
) -> RepositoryScore:
    return RepositoryScore(
        version="v1",
        overall_score=overall_score,
        dimensions=[
            ScoreDimensionResult(
                key="synthetic",
                label="Synthetic",
                points_earned=overall_score,
                points_possible=100,
                score=overall_score,
                rules=[
                    ScoreRuleResult(
                        key="synthetic",
                        label="Synthetic",
                        passed=overall_score > 0,
                        points_earned=overall_score,
                        points_possible=100,
                        evidence="Synthetic repository score.",
                    )
                ],
            )
        ],
        is_partial=is_partial,
        limitations=(
            ["Synthetic partial evidence."] if is_partial else []
        ),
    )


def create_result(
    name: str,
    *,
    technology_names: tuple[str, ...] = (),
    categories: tuple[RepositoryCategory, ...] = (
        RepositoryCategory.OTHER,
    ),
    primary_category: RepositoryCategory = RepositoryCategory.OTHER,
    readme_flags: frozenset[str] = frozenset(),
    structure_flags: frozenset[str] = frozenset(),
    overall_score: int = 0,
    score_is_partial: bool = False,
    tree_truncated: bool = False,
) -> PortfolioRepositoryResult:
    repository = create_repository(name)
    analysis = RepositoryAnalysis(
        repository=repository,
        readme=ReadmeAnalysis(
            exists="exists" in readme_flags,
            content_length=(100 if "exists" in readme_flags else 0),
            has_title="has_title" in readme_flags,
            has_description="has_description" in readme_flags,
            has_installation="has_installation" in readme_flags,
            has_usage="has_usage" in readme_flags,
            has_technologies="has_technologies" in readme_flags,
            has_requirements="has_requirements" in readme_flags,
            has_images=False,
            has_demo_link=False,
        ),
        structure=RepositoryStructureSignals(
            has_tests="has_tests" in structure_flags,
            has_ci="has_ci" in structure_flags,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license="has_license" in structure_flags,
            has_gitignore="has_gitignore" in structure_flags,
            has_contributing="has_contributing" in structure_flags,
        ),
        tree_truncated=tree_truncated,
        technologies=TechnologyAnalysis(
            dependencies=[],
            technologies=[
                DetectedTechnology(
                    name=technology,
                    category="Frontend",
                    source_dependency=f"synthetic-{index}",
                )
                for index, technology in enumerate(technology_names)
            ],
        ),
        classification=RepositoryClassification(
            categories=[
                RepositoryCategoryMatch(
                    category=category,
                    evidence_score=(
                        0 if category is RepositoryCategory.OTHER else 1
                    ),
                    evidence=[f"Synthetic {category.value} evidence."],
                )
                for category in categories
            ],
            primary_category=primary_category,
        ),
    )

    return PortfolioRepositoryResult(
        repository=repository,
        analysis=analysis,
        score=create_score(
            overall_score,
            is_partial=score_is_partial,
        ),
    )


def create_failure(name: str) -> PortfolioRepositoryFailure:
    return PortfolioRepositoryFailure(
        repository=create_repository(name),
        code=PortfolioRepositoryFailureCode.GITHUB_TIMEOUT,
        message="GitHub request timed out during repository analysis.",
    )


def create_portfolio_analysis(
    repositories: list[PortfolioRepositoryResult],
    *,
    failures: list[PortfolioRepositoryFailure] | None = None,
    selection_version: str = "v1",
) -> PortfolioRepositoryAnalysis:
    resolved_failures = [] if failures is None else failures
    return PortfolioRepositoryAnalysis(
        selection_version=selection_version,
        repositories=repositories,
        failures=resolved_failures,
        has_failures=bool(resolved_failures),
    )


def test_empty_portfolio_returns_canonical_zero_aggregation() -> None:
    result = aggregate_portfolio(create_portfolio_analysis([]))

    assert result == PortfolioAggregation.model_validate(
        {
            "selection_version": "v1",
            "selected_repository_count": 0,
            "successful_repository_count": 0,
            "failed_repository_count": 0,
            "has_failures": False,
            "partial_evidence_repository_count": 0,
            "technology_distribution": [],
            "category_distribution": [],
            "primary_category_distribution": [],
            "portfolio_signals": [
                {
                    "key": "readme_exists",
                    "label": "README mevcut",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_title",
                    "label": "README başlığı",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_description",
                    "label": "README açıklaması",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_installation",
                    "label": "README kurulumu",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_usage",
                    "label": "README kullanımı",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_technologies",
                    "label": "README teknolojileri",
                    "detected_repository_count": 0,
                },
                {
                    "key": "readme_requirements",
                    "label": "README gereksinimleri",
                    "detected_repository_count": 0,
                },
                {
                    "key": "tests_structure",
                    "label": "Test Yapısı",
                    "detected_repository_count": 0,
                },
                {
                    "key": "ci_workflow",
                    "label": "CI İş Akışı",
                    "detected_repository_count": 0,
                },
                {
                    "key": "gitignore",
                    "label": ".gitignore",
                    "detected_repository_count": 0,
                },
                {
                    "key": "license",
                    "label": "LICENSE",
                    "detected_repository_count": 0,
                },
                {
                    "key": "contributing",
                    "label": "CONTRIBUTING",
                    "detected_repository_count": 0,
                },
            ],
            "repository_score_distribution": [
                {
                    "min_score": 0,
                    "max_score": 24,
                    "repository_count": 0,
                },
                {
                    "min_score": 25,
                    "max_score": 49,
                    "repository_count": 0,
                },
                {
                    "min_score": 50,
                    "max_score": 74,
                    "repository_count": 0,
                },
                {
                    "min_score": 75,
                    "max_score": 100,
                    "repository_count": 0,
                },
            ],
        }
    )


def test_repository_counts_include_three_successes_and_two_failures() -> None:
    portfolio_analysis = create_portfolio_analysis(
        [
            create_result("alpha"),
            create_result("bravo"),
            create_result("charlie"),
        ],
        failures=[
            create_failure("delta"),
            create_failure("echo"),
        ],
    )
    portfolio_analysis.has_failures = False

    result = aggregate_portfolio(portfolio_analysis)

    assert result.successful_repository_count == 3
    assert result.failed_repository_count == 2
    assert result.selected_repository_count == 5
    assert result.has_failures is True


def test_technology_distribution_counts_repositories_in_neutral_order() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    technology_names=("React", "FastAPI"),
                ),
                create_result(
                    "bravo",
                    technology_names=("React", "Pandas"),
                ),
                create_result("charlie", technology_names=("React",)),
            ]
        )
    )

    assert [
        (usage.technology, usage.repository_count)
        for usage in result.technology_distribution
    ] == [
        ("FastAPI", 1),
        ("Pandas", 1),
        ("React", 3),
    ]


def test_technology_distribution_deduplicates_within_a_repository() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    technology_names=("React", "React"),
                ),
                create_result("bravo", technology_names=("React",)),
            ]
        )
    )

    assert [
        (usage.technology, usage.repository_count)
        for usage in result.technology_distribution
    ] == [("React", 2)]


def test_multi_label_categories_follow_canonical_enum_order() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    categories=(
                        RepositoryCategory.MACHINE_LEARNING,
                        RepositoryCategory.DATA_SCIENCE,
                    ),
                    primary_category=RepositoryCategory.MACHINE_LEARNING,
                ),
                create_result(
                    "bravo",
                    categories=(
                        RepositoryCategory.BACKEND,
                        RepositoryCategory.MACHINE_LEARNING,
                    ),
                    primary_category=RepositoryCategory.BACKEND,
                ),
            ]
        )
    )

    assert [
        (usage.category, usage.repository_count)
        for usage in result.category_distribution
    ] == [
        (RepositoryCategory.MACHINE_LEARNING, 2),
        (RepositoryCategory.DATA_SCIENCE, 1),
        (RepositoryCategory.BACKEND, 1),
    ]
    assert sum(
        usage.repository_count for usage in result.category_distribution
    ) > result.successful_repository_count


def test_category_distribution_deduplicates_within_a_repository() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    categories=(
                        RepositoryCategory.MACHINE_LEARNING,
                        RepositoryCategory.MACHINE_LEARNING,
                    ),
                    primary_category=RepositoryCategory.MACHINE_LEARNING,
                ),
                create_result(
                    "bravo",
                    categories=(RepositoryCategory.MACHINE_LEARNING,),
                    primary_category=RepositoryCategory.MACHINE_LEARNING,
                ),
            ]
        )
    )

    assert [
        (usage.category, usage.repository_count)
        for usage in result.category_distribution
    ] == [(RepositoryCategory.MACHINE_LEARNING, 2)]


def test_primary_category_counts_total_successful_repositories() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    categories=(RepositoryCategory.MACHINE_LEARNING,),
                    primary_category=RepositoryCategory.MACHINE_LEARNING,
                ),
                create_result(
                    "bravo",
                    categories=(RepositoryCategory.FRONTEND,),
                    primary_category=RepositoryCategory.FRONTEND,
                ),
                create_result("charlie"),
            ]
        )
    )

    assert [
        (usage.category, usage.repository_count)
        for usage in result.primary_category_distribution
    ] == [
        (RepositoryCategory.MACHINE_LEARNING, 1),
        (RepositoryCategory.FRONTEND, 1),
        (RepositoryCategory.OTHER, 1),
    ]
    assert sum(
        usage.repository_count
        for usage in result.primary_category_distribution
    ) == result.successful_repository_count


def test_portfolio_signals_return_all_twelve_positive_evidence_counts() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    readme_flags=frozenset(
                        {
                            "exists",
                            "has_title",
                            "has_description",
                            "has_installation",
                        }
                    ),
                    structure_flags=frozenset(
                        {"has_tests", "has_ci", "has_gitignore"}
                    ),
                ),
                create_result(
                    "bravo",
                    readme_flags=frozenset(
                        {
                            "exists",
                            "has_description",
                            "has_usage",
                            "has_technologies",
                        }
                    ),
                    structure_flags=frozenset(
                        {"has_ci", "has_license"}
                    ),
                ),
                create_result(
                    "charlie",
                    readme_flags=frozenset(
                        {
                            "has_title",
                            "has_installation",
                            "has_usage",
                            "has_requirements",
                        }
                    ),
                    structure_flags=frozenset(
                        {
                            "has_tests",
                            "has_gitignore",
                            "has_license",
                            "has_contributing",
                        }
                    ),
                ),
            ]
        )
    )

    assert [
        (signal.key, signal.detected_repository_count)
        for signal in result.portfolio_signals
    ] == [
        ("readme_exists", 2),
        ("readme_title", 2),
        ("readme_description", 2),
        ("readme_installation", 2),
        ("readme_usage", 2),
        ("readme_technologies", 1),
        ("readme_requirements", 1),
        ("tests_structure", 2),
        ("ci_workflow", 2),
        ("gitignore", 2),
        ("license", 2),
        ("contributing", 1),
    ]


def test_failures_do_not_contribute_evidence_categories_or_scores() -> None:
    repositories = [
        create_result(
            "alpha",
            technology_names=("React",),
            categories=(RepositoryCategory.FRONTEND,),
            primary_category=RepositoryCategory.FRONTEND,
            readme_flags=frozenset({"exists"}),
            structure_flags=frozenset({"has_tests"}),
            overall_score=24,
        ),
        create_result(
            "bravo",
            technology_names=("FastAPI",),
            categories=(RepositoryCategory.BACKEND,),
            primary_category=RepositoryCategory.BACKEND,
            structure_flags=frozenset({"has_ci"}),
            overall_score=75,
        ),
    ]
    without_failures = aggregate_portfolio(
        create_portfolio_analysis(repositories)
    )
    with_failures = aggregate_portfolio(
        create_portfolio_analysis(
            repositories,
            failures=[
                create_failure("charlie"),
                create_failure("delta"),
                create_failure("echo"),
            ],
        )
    )

    assert with_failures.technology_distribution == (
        without_failures.technology_distribution
    )
    assert with_failures.category_distribution == (
        without_failures.category_distribution
    )
    assert with_failures.primary_category_distribution == (
        without_failures.primary_category_distribution
    )
    assert with_failures.portfolio_signals == without_failures.portfolio_signals
    assert with_failures.repository_score_distribution == (
        without_failures.repository_score_distribution
    )
    assert sum(
        bucket.repository_count
        for bucket in with_failures.repository_score_distribution
    ) == 2
    assert all(
        usage.category is not RepositoryCategory.OTHER
        for usage in with_failures.category_distribution
    )


def test_partial_evidence_count_uses_repository_score_abstraction() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    "alpha",
                    score_is_partial=False,
                    tree_truncated=True,
                ),
                create_result(
                    "bravo",
                    score_is_partial=True,
                    readme_flags=frozenset({"exists"}),
                ),
                create_result("charlie", score_is_partial=True),
            ]
        )
    )

    assert result.partial_evidence_repository_count == 2
    assert result.successful_repository_count == 3
    assert result.portfolio_signals[0].detected_repository_count == 1


@pytest.mark.parametrize(
    ("score", "expected_bucket_index"),
    [
        (0, 0),
        (24, 0),
        (25, 1),
        (49, 1),
        (50, 2),
        (74, 2),
        (75, 3),
        (100, 3),
    ],
)
def test_repository_score_boundary_belongs_to_exactly_one_bucket(
    score: int,
    expected_bucket_index: int,
) -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [create_result("boundary", overall_score=score)]
        )
    )

    counts = [
        bucket.repository_count
        for bucket in result.repository_score_distribution
    ]
    assert counts == [
        int(index == expected_bucket_index) for index in range(4)
    ]


def test_all_score_boundaries_produce_complete_bucket_totals() -> None:
    boundary_scores = (0, 24, 25, 49, 50, 74, 75, 100)
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [
                create_result(
                    f"repository-{index}",
                    overall_score=score,
                )
                for index, score in enumerate(boundary_scores)
            ]
        )
    )

    assert [
        (
            bucket.min_score,
            bucket.max_score,
            bucket.repository_count,
        )
        for bucket in result.repository_score_distribution
    ] == [
        (0, 24, 2),
        (25, 49, 2),
        (50, 74, 2),
        (75, 100, 2),
    ]
    assert sum(
        bucket.repository_count
        for bucket in result.repository_score_distribution
    ) == result.successful_repository_count


def test_reversed_repository_input_produces_identical_aggregation() -> None:
    repositories = [
        create_result(
            "alpha",
            technology_names=("React", "FastAPI"),
            categories=(
                RepositoryCategory.FRONTEND,
                RepositoryCategory.FULL_STACK,
            ),
            primary_category=RepositoryCategory.FRONTEND,
            readme_flags=frozenset({"exists", "has_usage"}),
            overall_score=24,
        ),
        create_result(
            "bravo",
            technology_names=("Pandas", "FastAPI"),
            categories=(
                RepositoryCategory.DATA_SCIENCE,
                RepositoryCategory.BACKEND,
            ),
            primary_category=RepositoryCategory.DATA_SCIENCE,
            structure_flags=frozenset({"has_tests", "has_license"}),
            overall_score=50,
            score_is_partial=True,
        ),
        create_result(
            "charlie",
            technology_names=("React",),
            categories=(RepositoryCategory.OTHER,),
            primary_category=RepositoryCategory.OTHER,
            structure_flags=frozenset({"has_ci"}),
            overall_score=100,
        ),
    ]
    failures = [create_failure("delta"), create_failure("echo")]

    forward = aggregate_portfolio(
        create_portfolio_analysis(repositories, failures=failures)
    )
    reverse = aggregate_portfolio(
        create_portfolio_analysis(
            list(reversed(repositories)),
            failures=list(reversed(failures)),
        )
    )

    assert reverse == forward


def test_selection_version_is_preserved() -> None:
    result = aggregate_portfolio(
        create_portfolio_analysis(
            [create_result("alpha")],
            selection_version="selection-v42",
        )
    )

    assert result.selection_version == "selection-v42"
