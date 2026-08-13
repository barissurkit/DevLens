import pytest

from app.schemas.analysis import PortfolioAggregation, RepositoryCategory
from app.services.portfolio_intelligence import build_portfolio_intelligence


SIGNAL_LABELS: tuple[tuple[str, str], ...] = (
    ("readme_exists", "README exists"),
    ("readme_title", "README title"),
    ("readme_description", "README description"),
    ("readme_installation", "README installation"),
    ("readme_usage", "README usage"),
    ("readme_technologies", "README technologies"),
    ("readme_requirements", "README requirements"),
    ("tests_structure", "Tests structure"),
    ("ci_workflow", "CI workflow"),
    ("gitignore", ".gitignore"),
    ("license", "LICENSE"),
    ("contributing", "CONTRIBUTING"),
)


def create_aggregation(
    *,
    successful_repository_count: int = 0,
    failed_repository_count: int = 0,
    partial_evidence_repository_count: int = 0,
    default_signal_count: int = 0,
    signal_counts: dict[str, int] | None = None,
    technology_distribution: list[tuple[str, int]] | None = None,
    category_distribution: list[tuple[RepositoryCategory, int]] | None = None,
    primary_category_distribution: (
        list[tuple[RepositoryCategory, int]] | None
    ) = None,
) -> PortfolioAggregation:
    resolved_signal_counts = {
        key: default_signal_count for key, _label in SIGNAL_LABELS
    }
    resolved_signal_counts.update(signal_counts or {})

    return PortfolioAggregation.model_validate(
        {
            "selection_version": "selection-v1",
            "selected_repository_count": (
                successful_repository_count + failed_repository_count
            ),
            "successful_repository_count": successful_repository_count,
            "failed_repository_count": failed_repository_count,
            "has_failures": failed_repository_count > 0,
            "partial_evidence_repository_count": (
                partial_evidence_repository_count
            ),
            "technology_distribution": [
                {
                    "technology": technology,
                    "repository_count": repository_count,
                }
                for technology, repository_count in (
                    technology_distribution or []
                )
            ],
            "category_distribution": [
                {
                    "category": category,
                    "repository_count": repository_count,
                }
                for category, repository_count in (category_distribution or [])
            ],
            "primary_category_distribution": [
                {
                    "category": category,
                    "repository_count": repository_count,
                }
                for category, repository_count in (
                    primary_category_distribution or []
                )
            ],
            "portfolio_signals": [
                {
                    "key": key,
                    "label": label,
                    "detected_repository_count": resolved_signal_counts[key],
                }
                for key, label in SIGNAL_LABELS
            ],
            "repository_score_distribution": [
                {
                    "min_score": 0,
                    "max_score": 24,
                    "repository_count": successful_repository_count,
                },
                {"min_score": 25, "max_score": 49, "repository_count": 0},
                {"min_score": 50, "max_score": 74, "repository_count": 0},
                {"min_score": 75, "max_score": 100, "repository_count": 0},
            ],
        }
    )


def insight(
    key: str,
    message: str,
    detected_repository_count: int,
    analyzed_repository_count: int,
) -> dict[str, str | int]:
    return {
        "key": key,
        "message": message,
        "detected_repository_count": detected_repository_count,
        "analyzed_repository_count": analyzed_repository_count,
    }


def test_empty_portfolio_returns_only_the_minimum_size_limitation() -> None:
    aggregation = create_aggregation()
    aggregation.portfolio_signals = []

    result = build_portfolio_intelligence(aggregation)

    assert result.model_dump(mode="json") == {
        "version": "v1",
        "strength_signals": [],
        "improvement_signals": [],
        "recurring_technologies": [],
        "dominant_areas": [],
        "limitations": [
            "Portfolio-level patterns require at least two successfully "
            "analyzed repositories."
        ],
    }


def test_single_repository_does_not_create_portfolio_patterns() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=1,
            default_signal_count=1,
            technology_distribution=[("FastAPI", 1)],
            category_distribution=[(RepositoryCategory.BACKEND, 1)],
            primary_category_distribution=[(RepositoryCategory.BACKEND, 1)],
        )
    )

    assert result.model_dump(mode="json") == {
        "version": "v1",
        "strength_signals": [],
        "improvement_signals": [],
        "recurring_technologies": [],
        "dominant_areas": [],
        "limitations": [
            "Portfolio-level patterns require at least two successfully "
            "analyzed repositories."
        ],
    }


@pytest.mark.parametrize(
    ("successful_count", "detected_count", "expected_present"),
    [
        (6, 3, True),
        (2, 2, True),
        (2, 1, False),
        (6, 2, False),
    ],
)
def test_strength_requires_half_the_portfolio_and_two_detections(
    successful_count: int,
    detected_count: int,
    expected_present: bool,
) -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=successful_count,
            signal_counts={"readme_exists": detected_count},
        )
    )

    assert (
        "readme_exists" in [item.key for item in result.strength_signals]
    ) is expected_present


@pytest.mark.parametrize(
    ("successful_count", "detected_count", "expected_present"),
    [
        (6, 2, True),
        (6, 3, False),
        (2, 0, False),
    ],
)
def test_improvement_requires_less_than_half_and_three_repositories(
    successful_count: int,
    detected_count: int,
    expected_present: bool,
) -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=successful_count,
            default_signal_count=successful_count // 2,
            signal_counts={"readme_usage": detected_count},
        )
    )

    assert (
        "readme_usage" in [item.key for item in result.improvement_signals]
    ) is expected_present


def test_improvement_messages_distinguish_zero_from_limited_presence() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            default_signal_count=3,
            signal_counts={
                "readme_installation": 0,
                "readme_usage": 2,
            },
        )
    )

    assert [
        item.model_dump(mode="json") for item in result.improvement_signals
    ] == [
        insight(
            "readme_installation",
            "No README installation-section signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "readme_usage",
            "README usage-section signals were detected in only a limited "
            "portion of the successfully analyzed public repositories.",
            2,
            6,
        ),
    ]


@pytest.mark.parametrize(
    ("failed_count", "expected_limitation"),
    [
        (
            1,
            "1 selected repository could not be analyzed and was excluded "
            "from portfolio intelligence.",
        ),
        (
            2,
            "2 selected repositories could not be analyzed and were excluded "
            "from portfolio intelligence.",
        ),
    ],
)
def test_failures_use_only_successes_as_the_insight_denominator(
    failed_count: int,
    expected_limitation: str,
) -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            failed_repository_count=failed_count,
            default_signal_count=3,
            signal_counts={"readme_usage": 0},
        )
    )

    usage_insight = next(
        item
        for item in result.improvement_signals
        if item.key == "readme_usage"
    )
    assert usage_insight.model_dump(mode="json") == insight(
        "readme_usage",
        "No README usage-section signal was detected across the successfully "
        "analyzed public repositories.",
        0,
        6,
    )
    assert result.limitations == [expected_limitation]


def test_partial_evidence_suppresses_structure_but_not_readme_improvements() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            partial_evidence_repository_count=1,
            default_signal_count=3,
            signal_counts={
                "readme_usage": 0,
                "tests_structure": 0,
                "ci_workflow": 0,
                "license": 0,
            },
        )
    )

    assert [
        item.model_dump(mode="json") for item in result.improvement_signals
    ] == [
        insight(
            "readme_usage",
            "No README usage-section signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        )
    ]


def test_partial_evidence_preserves_positive_structure_strength() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            partial_evidence_repository_count=1,
            signal_counts={"tests_structure": 4},
        )
    )

    assert [
        item.model_dump(mode="json") for item in result.strength_signals
    ] == [
        insight(
            "tests_structure",
            "Test-directory structure signals were detected across multiple "
            "successfully analyzed public repositories.",
            4,
            6,
        )
    ]


@pytest.mark.parametrize(
    ("partial_count", "expected_limitation"),
    [
        (
            1,
            "1 successfully analyzed repository has partial structure "
            "evidence; absence-based structure and repository-hygiene insights "
            "may be incomplete.",
        ),
        (
            2,
            "2 successfully analyzed repositories have partial structure "
            "evidence; absence-based structure and repository-hygiene insights "
            "may be incomplete.",
        ),
    ],
)
def test_partial_evidence_limitation_has_stable_number_agreement(
    partial_count: int,
    expected_limitation: str,
) -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            partial_evidence_repository_count=partial_count,
            default_signal_count=3,
        )
    )

    assert result.limitations == [expected_limitation]


def test_recurring_technologies_use_threshold_and_neutral_ordering() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            technology_distribution=[
                ("Scikit-learn", 3),
                ("React", 1),
                ("Pandas", 2),
                ("FastAPI", 2),
            ],
        )
    )

    assert [
        item.model_dump(mode="json") for item in result.recurring_technologies
    ] == [
        {"technology": "FastAPI", "repository_count": 2},
        {"technology": "Pandas", "repository_count": 2},
        {"technology": "Scikit-learn", "repository_count": 3},
    ]


def test_single_repeated_primary_category_is_the_dominant_area() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            primary_category_distribution=[
                (RepositoryCategory.OTHER, 2),
                (RepositoryCategory.FRONTEND, 1),
                (RepositoryCategory.BACKEND, 3),
            ],
        )
    )

    assert [item.model_dump(mode="json") for item in result.dominant_areas] == [
        {"category": "Backend", "repository_count": 3}
    ]


def test_tied_dominant_areas_follow_category_enum_order() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=5,
            primary_category_distribution=[
                (RepositoryCategory.FRONTEND, 2),
                (RepositoryCategory.MACHINE_LEARNING, 1),
                (RepositoryCategory.BACKEND, 2),
            ],
        )
    )

    assert [item.model_dump(mode="json") for item in result.dominant_areas] == [
        {"category": "Backend", "repository_count": 2},
        {"category": "Frontend", "repository_count": 2},
    ]


def test_other_is_excluded_before_the_dominant_count_is_selected() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            primary_category_distribution=[
                (RepositoryCategory.OTHER, 4),
                (RepositoryCategory.BACKEND, 2),
            ],
        )
    )

    assert [item.model_dump(mode="json") for item in result.dominant_areas] == [
        {"category": "Backend", "repository_count": 2}
    ]


def test_other_does_not_create_dominance_when_technical_areas_do_not_recur(
) -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            primary_category_distribution=[
                (RepositoryCategory.OTHER, 4),
                (RepositoryCategory.BACKEND, 1),
                (RepositoryCategory.FRONTEND, 1),
            ],
        )
    )

    assert result.dominant_areas == []


def test_dominant_areas_ignore_multi_label_category_distribution() -> None:
    result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=5,
            category_distribution=[
                (RepositoryCategory.MACHINE_LEARNING, 5),
            ],
            primary_category_distribution=[
                (RepositoryCategory.OTHER, 3),
                (RepositoryCategory.BACKEND, 2),
            ],
        )
    )

    assert [item.model_dump(mode="json") for item in result.dominant_areas] == [
        {"category": "Backend", "repository_count": 2}
    ]


def test_rule_registry_preserves_candidate_exclusions_messages_and_order() -> None:
    strength_result = build_portfolio_intelligence(
        create_aggregation(
            successful_repository_count=6,
            default_signal_count=3,
            signal_counts={"contributing": 6},
        )
    )
    improvement_result = build_portfolio_intelligence(
        create_aggregation(successful_repository_count=6)
    )

    assert [
        item.model_dump(mode="json")
        for item in strength_result.strength_signals
    ] == [
        insight(
            "readme_exists",
            "Root README content was available across multiple successfully "
            "analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_title",
            "README title signals were detected across multiple successfully "
            "analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_description",
            "README description signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_installation",
            "README installation-section signals were detected across "
            "multiple successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_usage",
            "README usage-section signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_technologies",
            "README technology-section signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "readme_requirements",
            "README requirements-section signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "tests_structure",
            "Test-directory structure signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "ci_workflow",
            "GitHub Actions workflow signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "gitignore",
            ".gitignore file signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
        insight(
            "license",
            "Supported license filename signals were detected across multiple "
            "successfully analyzed public repositories.",
            3,
            6,
        ),
    ]
    assert [
        item.model_dump(mode="json")
        for item in improvement_result.improvement_signals
    ] == [
        insight(
            "readme_exists",
            "No root README content was available across the successfully "
            "analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "readme_description",
            "No meaningful README description signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "readme_installation",
            "No README installation-section signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "readme_usage",
            "No README usage-section signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "readme_requirements",
            "No README requirements-section signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "tests_structure",
            "No test-directory structure signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "ci_workflow",
            "No GitHub Actions workflow signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
        insight(
            "license",
            "No supported license filename signal was detected across the "
            "successfully analyzed public repositories.",
            0,
            6,
        ),
    ]


def test_missing_required_signal_key_is_rejected() -> None:
    aggregation = create_aggregation(successful_repository_count=2)
    aggregation.portfolio_signals = aggregation.portfolio_signals[:-1]

    with pytest.raises(ValueError) as error:
        build_portfolio_intelligence(aggregation)

    assert str(error.value) == (
        "Portfolio aggregation is missing required signal keys: contributing"
    )


def test_duplicate_signal_key_is_rejected() -> None:
    aggregation = create_aggregation(successful_repository_count=2)
    aggregation.portfolio_signals.append(
        aggregation.portfolio_signals[0].model_copy()
    )

    with pytest.raises(ValueError) as error:
        build_portfolio_intelligence(aggregation)

    assert str(error.value) == (
        "Duplicate portfolio signal key: readme_exists"
    )


def test_result_is_deterministic_with_version_and_stable_limitation_order() -> None:
    aggregation = create_aggregation(
        successful_repository_count=1,
        failed_repository_count=2,
        partial_evidence_repository_count=1,
        default_signal_count=1,
    )

    first = build_portfolio_intelligence(aggregation)
    second = build_portfolio_intelligence(aggregation)

    assert second == first
    assert first.version == "v1"
    assert first.limitations == [
        "2 selected repositories could not be analyzed and were excluded "
        "from portfolio intelligence.",
        "1 successfully analyzed repository has partial structure evidence; "
        "absence-based structure and repository-hygiene insights may be "
        "incomplete.",
        "Portfolio-level patterns require at least two successfully analyzed "
        "repositories.",
    ]
