import pytest

from app.schemas.analysis import (
    PortfolioAggregation,
    PortfolioScore,
    PortfolioScoreDimensionResult,
    RepositoryCategory,
)
from app.services.portfolio_scoring import (
    PORTFOLIO_SCORING_DIMENSIONS,
    round_half_up_ratio,
    score_portfolio,
)

SIGNAL_LABELS: tuple[tuple[str, str], ...] = (
    ("readme_exists", "README mevcut"),
    ("readme_title", "README başlığı"),
    ("readme_description", "README açıklaması"),
    ("readme_installation", "README kurulumu"),
    ("readme_usage", "README kullanımı"),
    ("readme_technologies", "README teknolojileri"),
    ("readme_requirements", "README gereksinimleri"),
    ("tests_structure", "Test Yapısı"),
    ("ci_workflow", "CI İş Akışı"),
    ("gitignore", ".gitignore"),
    ("license", "LICENSE"),
    ("contributing", "CONTRIBUTING"),
)


def create_aggregation(
    *,
    successful: int = 0,
    failed: int = 0,
    partial: int = 0,
    default_signal_count: int = 0,
    signal_counts: dict[str, int] | None = None,
    technologies: list[tuple[str, int]] | None = None,
    categories: list[tuple[RepositoryCategory, int]] | None = None,
    primary_categories: list[tuple[RepositoryCategory, int]] | None = None,
    buckets: list[tuple[int, int, int]] | None = None,
) -> PortfolioAggregation:
    counts = {key: default_signal_count for key, _ in SIGNAL_LABELS}
    counts.update(signal_counts or {})

    return PortfolioAggregation.model_validate(
        {
            "selection_version": "selection-v1",
            "selected_repository_count": successful + failed,
            "successful_repository_count": successful,
            "failed_repository_count": failed,
            "has_failures": failed > 0,
            "partial_evidence_repository_count": partial,
            "technology_distribution": [
                {"technology": name, "repository_count": count}
                for name, count in (technologies or [])
            ],
            "category_distribution": [
                {"category": category, "repository_count": count}
                for category, count in (categories or [])
            ],
            "primary_category_distribution": [
                {"category": category, "repository_count": count}
                for category, count in (primary_categories or [])
            ],
            "portfolio_signals": [
                {
                    "key": key,
                    "label": label,
                    "detected_repository_count": counts[key],
                }
                for key, label in SIGNAL_LABELS
            ],
            "repository_score_distribution": [
                {
                    "min_score": minimum,
                    "max_score": maximum,
                    "repository_count": count,
                }
                for minimum, maximum, count in (
                    buckets
                    or [
                        (0, 24, successful),
                        (25, 49, 0),
                        (50, 74, 0),
                        (75, 100, 0),
                    ]
                )
            ],
        }
    )


def dimension(
    score: PortfolioScore,
    key: str,
) -> PortfolioScoreDimensionResult:
    return next(
        item
        for item in score.dimensions
        if item.key == key
    )


def test_policy_has_exact_order_and_weights() -> None:
    assert [
        (
            item.key,
            item.label,
            [(rule.key, rule.label, rule.weight) for rule in item.rules],
        )
        for item in PORTFOLIO_SCORING_DIMENSIONS
    ] == [
        (
            "documentation_consistency",
                "Dokümantasyon Tutarlılığı",
            [
                ("readme_exists", "README mevcut", 8),
                ("readme_title", "README başlığı", 5),
                ("readme_description", "README açıklaması", 8),
                ("readme_installation", "README kurulumu", 9),
                ("readme_usage", "README kullanımı", 9),
                ("readme_technologies", "README teknolojileri", 6),
                ("readme_requirements", "README gereksinimleri", 5),
            ],
        ),
        (
            "testing_automation_adoption",
                "Test ve Otomasyon Kullanımı",
            [
                ("tests_structure", "Test Yapısı", 18),
                ("ci_workflow", "CI İş Akışı", 12),
            ],
        ),
        (
            "repository_hygiene_consistency",
                "Repository Hijyeni Tutarlılığı",
            [
                ("gitignore", ".gitignore", 8),
                ("license", "LICENSE", 7),
                ("contributing", "CONTRIBUTING", 5),
            ],
        ),
    ]
    totals = [
        sum(rule.weight for rule in item.rules)
        for item in PORTFOLIO_SCORING_DIMENSIONS
    ]
    assert totals == [50, 30, 20]
    assert sum(totals) == 100


@pytest.mark.parametrize("successful", [0, 1])
def test_small_portfolio_score_is_unavailable(successful: int) -> None:
    aggregation = create_aggregation(
        successful=successful,
        default_signal_count=successful,
    )
    aggregation.portfolio_signals = []

    result = score_portfolio(aggregation)

    assert result.is_available is False
    assert result.overall_score is None
    assert result.scored_repository_count == successful
    assert result.dimensions == []
    assert result.is_partial is False
    assert result.limitations == [
            "Portföy skoru için en az iki repository'nin başarıyla analiz edilmesi gerekir."
    ]


def test_valid_portfolio_with_zero_evidence_has_available_zero_score() -> None:
    result = score_portfolio(create_aggregation(successful=3))

    assert result.is_available is True
    assert result.overall_score == 0
    assert result.overall_score is not None
    assert [item.points_earned for item in result.dimensions] == [0, 0, 0]


def test_perfect_coverage_returns_one_hundred() -> None:
    result = score_portfolio(
        create_aggregation(successful=3, default_signal_count=3)
    )

    assert result.overall_score == 100
    assert [
        (item.points_earned, item.points_possible, item.score)
        for item in result.dimensions
    ] == [(50, 50, 100), (30, 30, 100), (20, 20, 100)]


def test_documentation_uses_exact_weighted_coverage_math() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=6,
            signal_counts={
                "readme_exists": 4,
                "readme_title": 4,
                "readme_description": 3,
                "readme_installation": 1,
                "readme_usage": 0,
                "readme_technologies": 1,
                "readme_requirements": 0,
            },
        )
    )
    documentation = dimension(result, "documentation_consistency")

    assert documentation.points_earned == 15
    assert documentation.points_possible == 50
    assert documentation.score == 30


def test_testing_uses_exact_weighted_coverage_math() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=4,
            signal_counts={"tests_structure": 2, "ci_workflow": 1},
        )
    )
    testing = dimension(result, "testing_automation_adoption")

    assert (testing.points_earned, testing.points_possible, testing.score) == (
        12,
        30,
        40,
    )


def test_hygiene_uses_exact_weighted_coverage_math() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=4,
            signal_counts={
                "gitignore": 3,
                "license": 2,
                "contributing": 1,
            },
        )
    )
    hygiene = dimension(result, "repository_hygiene_consistency")

    assert (hygiene.points_earned, hygiene.points_possible, hygiene.score) == (
        11,
        20,
        55,
    )


def test_dimension_normalization_rounds_non_exact_value() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=24,
            signal_counts={"ci_workflow": 1},
        )
    )
    testing = dimension(result, "testing_automation_adoption")

    assert testing.points_earned == 1
    assert testing.score == 3


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(0, 3, 0), (1, 4, 0), (1, 2, 1), (3, 2, 2), (91, 6, 15)],
)
def test_round_half_up_ratio(
    numerator: int,
    denominator: int,
    expected: int,
) -> None:
    assert round_half_up_ratio(
        numerator=numerator,
        denominator=denominator,
    ) == expected


@pytest.mark.parametrize("denominator", [0, -1])
def test_round_half_up_rejects_invalid_denominator(denominator: int) -> None:
    with pytest.raises(ValueError, match="denominator must be greater"):
        round_half_up_ratio(numerator=1, denominator=denominator)


def test_round_half_up_rejects_negative_numerator() -> None:
    with pytest.raises(ValueError, match="numerator must be non-negative"):
        round_half_up_ratio(numerator=-1, denominator=2)


def test_dimension_rounds_once_instead_of_rounding_each_rule() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=2,
            signal_counts={key: 1 for key, _ in SIGNAL_LABELS[:7]},
        )
    )

    documentation = dimension(result, "documentation_consistency")
    assert documentation.points_earned == 25


def test_overall_is_the_sum_of_dimension_points() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=4,
            signal_counts={
                "readme_exists": 3,
                "tests_structure": 2,
                "license": 1,
            },
        )
    )

    assert result.overall_score == sum(
        item.points_earned for item in result.dimensions
    )
    assert result.overall_score is not None
    assert 0 <= result.overall_score <= 100


def test_rule_results_are_explainable_and_stably_ordered() -> None:
    result = score_portfolio(
        create_aggregation(
            successful=4,
            signal_counts={"readme_exists": 3, "ci_workflow": 1},
        )
    )

    rules = [rule for item in result.dimensions for rule in item.rules]
    assert [rule.key for rule in rules] == [key for key, _ in SIGNAL_LABELS]
    assert rules[0].model_dump() == {
        "key": "readme_exists",
        "label": "README mevcut",
        "weight": 8,
        "detected_repository_count": 3,
        "analyzed_repository_count": 4,
    }
    assert all(
        0 <= rule.detected_repository_count <= rule.analyzed_repository_count
        for rule in rules
    )


@pytest.mark.parametrize(
    ("failed", "expected_limitation"),
    [
        (
            1,
                "1 seçilen repository analiz edilemedi ve portföy skorundan çıkarıldı.",
        ),
        (
            2,
                "2 seçilen repository analiz edilemedi ve portföy skorundan çıkarıldı.",
        ),
    ],
)
def test_failures_do_not_enter_the_scoring_denominator(
    failed: int,
    expected_limitation: str,
) -> None:
    baseline = score_portfolio(
        create_aggregation(successful=6, signal_counts={"readme_exists": 4})
    )
    result = score_portfolio(
        create_aggregation(
            successful=6,
            failed=failed,
            signal_counts={"readme_exists": 4},
        )
    )

    assert result.overall_score == baseline.overall_score
    assert result.scored_repository_count == 6
    assert result.dimensions[0].rules[0].analyzed_repository_count == 6
    assert result.is_partial is True
    assert result.limitations == [expected_limitation]


@pytest.mark.parametrize(
    ("partial", "expected_limitation"),
    [
        (
            1,
                "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı skor kanıtı eksik olabilir.",
        ),
        (
            2,
                "2 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı skor kanıtı eksik olabilir.",
        ),
    ],
)
def test_partial_evidence_marks_unchanged_score_as_partial(
    partial: int,
    expected_limitation: str,
) -> None:
    baseline = score_portfolio(
        create_aggregation(successful=6, signal_counts={"gitignore": 4})
    )
    result = score_portfolio(
        create_aggregation(
            successful=6,
            partial=partial,
            signal_counts={"gitignore": 4},
        )
    )

    assert result.overall_score == baseline.overall_score
    assert result.is_partial is True
    assert result.limitations == [expected_limitation]


def test_unavailable_failure_and_partial_limitations_have_stable_order() -> None:
    aggregation = create_aggregation(successful=1, failed=2, partial=1)
    aggregation.portfolio_signals = []
    result = score_portfolio(aggregation)

    assert result.is_available is False
    assert result.is_partial is True
    assert result.limitations == [
            "Portföy skoru için en az iki repository'nin başarıyla analiz edilmesi gerekir.",
            "2 seçilen repository analiz edilemedi ve portföy skorundan çıkarıldı.",
            "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı skor kanıtı eksik olabilir.",
    ]


def test_missing_required_signal_is_rejected() -> None:
    aggregation = create_aggregation(successful=2)
    aggregation.portfolio_signals = aggregation.portfolio_signals[:-1]

    with pytest.raises(ValueError, match="missing required scoring signal"):
        score_portfolio(aggregation)


def test_duplicate_signal_is_rejected() -> None:
    aggregation = create_aggregation(successful=2)
    aggregation.portfolio_signals.append(
        aggregation.portfolio_signals[0].model_copy()
    )

    with pytest.raises(ValueError, match="Duplicate portfolio signal key"):
        score_portfolio(aggregation)


def test_signal_count_above_successful_count_is_rejected() -> None:
    aggregation = create_aggregation(successful=2)
    aggregation.portfolio_signals[0].detected_repository_count = 3

    with pytest.raises(ValueError, match="cannot exceed successful"):
        score_portfolio(aggregation)


def test_inconsistent_selected_repository_count_is_rejected() -> None:
    aggregation = create_aggregation(successful=2, failed=1)
    aggregation.selected_repository_count = 2

    with pytest.raises(ValueError, match="selected_repository_count"):
        score_portfolio(aggregation)


def test_inconsistent_has_failures_flag_is_rejected() -> None:
    aggregation = create_aggregation(successful=2, failed=1)
    aggregation.has_failures = False

    with pytest.raises(ValueError, match="has_failures"):
        score_portfolio(aggregation)


def test_partial_count_above_successful_count_is_rejected() -> None:
    aggregation = create_aggregation(successful=2)
    aggregation.partial_evidence_repository_count = 3

    with pytest.raises(
        ValueError,
        match="partial_evidence_repository_count",
    ):
        score_portfolio(aggregation)


def test_technology_distribution_does_not_change_score() -> None:
    base = create_aggregation(successful=3, signal_counts={"readme_exists": 2})
    changed = create_aggregation(
        successful=3,
        signal_counts={"readme_exists": 2},
        technologies=[("FastAPI", 3), ("React", 2)],
    )
    assert score_portfolio(changed) == score_portfolio(base)


def test_category_distributions_do_not_change_score() -> None:
    base = create_aggregation(successful=3, signal_counts={"readme_exists": 2})
    changed = create_aggregation(
        successful=3,
        signal_counts={"readme_exists": 2},
        categories=[(RepositoryCategory.BACKEND, 3)],
        primary_categories=[(RepositoryCategory.FRONTEND, 3)],
    )
    assert score_portfolio(changed) == score_portfolio(base)


def test_repository_score_buckets_do_not_change_portfolio_score() -> None:
    base = create_aggregation(successful=3, signal_counts={"readme_exists": 2})
    changed = create_aggregation(
        successful=3,
        signal_counts={"readme_exists": 2},
        buckets=[(0, 24, 0), (25, 49, 0), (50, 74, 0), (75, 100, 3)],
    )
    assert score_portfolio(changed) == score_portfolio(base)


def test_result_is_deterministic_and_versioned() -> None:
    aggregation = create_aggregation(
        successful=4,
        signal_counts={"readme_exists": 3, "tests_structure": 2},
    )
    first = score_portfolio(aggregation)
    second = score_portfolio(aggregation)

    assert second == first
    assert first.version == "v1"
