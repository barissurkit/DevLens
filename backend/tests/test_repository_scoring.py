from collections.abc import Mapping

import pytest
from app.schemas.analysis import (
    DetectedTechnology,
    ReadmeAnalysis,
    RepositoryAnalysis,
    RepositoryCategory,
    RepositoryCategoryMatch,
    RepositoryClassification,
    RepositoryScore,
    RepositoryStructureSignals,
    ScoreDimensionResult,
    TechnologyAnalysis,
)
from app.schemas.github import GitHubRepository
from app.services.repository_scoring import (
    normalize_score,
    score_repository,
)

FULL_README_EVIDENCE: dict[str, object] = {
    "exists": True,
    "content_length": 100,
    "has_title": True,
    "has_description": True,
    "has_installation": True,
    "has_usage": True,
    "has_technologies": True,
    "has_requirements": True,
}

FULL_STRUCTURE_EVIDENCE: dict[str, object] = {
    "has_tests": True,
    "has_ci": True,
    "has_license": True,
    "has_gitignore": True,
    "has_contributing": True,
}


def create_classification(
    category: RepositoryCategory,
) -> RepositoryClassification:
    return RepositoryClassification(
        categories=[
            RepositoryCategoryMatch(
                category=category,
                evidence_score=(0 if category is RepositoryCategory.OTHER else 5),
                evidence=[f"Synthetic category: {category.value}."],
            )
        ],
        primary_category=category,
    )


def create_repository_analysis(
    *,
    readme_overrides: Mapping[str, object] | None = None,
    structure_overrides: Mapping[str, object] | None = None,
    stars: int = 0,
    forks: int = 0,
    technologies: TechnologyAnalysis | None = None,
    classification: RepositoryClassification | None = None,
    tree_truncated: bool = False,
) -> RepositoryAnalysis:
    readme_data: dict[str, object] = {
        "exists": False,
        "content_length": 0,
        "has_title": False,
        "has_description": False,
        "has_installation": False,
        "has_usage": False,
        "has_technologies": False,
        "has_requirements": False,
        "has_images": False,
        "has_demo_link": False,
    }

    if readme_overrides is not None:
        readme_data.update(readme_overrides)

    structure_data: dict[str, object] = {
        "has_tests": False,
        "has_ci": False,
        "has_dockerfile": False,
        "has_compose": False,
        "has_env_example": False,
        "has_license": False,
        "has_gitignore": False,
        "has_contributing": False,
    }

    if structure_overrides is not None:
        structure_data.update(structure_overrides)

    if technologies is None:
        technologies = TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        )

    if classification is None:
        classification = create_classification(RepositoryCategory.OTHER)

    repository = GitHubRepository.model_validate(
        {
            "name": "devlens",
            "description": None,
            "html_url": "https://github.com/octocat/devlens",
            "language": "Python",
            "stargazers_count": stars,
            "forks_count": forks,
            "topics": [],
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-02-20T15:30:00Z",
            "archived": False,
            "fork": False,
            "default_branch": "main",
        }
    )

    return RepositoryAnalysis(
        repository=repository,
        readme=ReadmeAnalysis.model_validate(readme_data),
        structure=RepositoryStructureSignals.model_validate(structure_data),
        tree_truncated=tree_truncated,
        technologies=technologies,
        classification=classification,
    )


def get_dimension(
    score: RepositoryScore,
    key: str,
) -> ScoreDimensionResult:
    return next(dimension for dimension in score.dimensions if dimension.key == key)


def test_score_repository_returns_perfect_v1_score() -> None:
    result = score_repository(
        create_repository_analysis(
            readme_overrides=FULL_README_EVIDENCE,
            structure_overrides=FULL_STRUCTURE_EVIDENCE,
        )
    )

    assert result.version == "v1"
    assert result.overall_score == 100
    assert result.is_partial is False
    assert result.limitations == []

    assert [
        (
            dimension.key,
            dimension.label,
            dimension.points_earned,
            dimension.points_possible,
            dimension.score,
        )
        for dimension in result.dimensions
    ] == [
        ("documentation", "Documentation", 50, 50, 100),
        (
            "testing_automation",
            "Testing & Automation",
            30,
            30,
            100,
        ),
        (
            "repository_hygiene",
            "Repository Hygiene",
            20,
            20,
            100,
        ),
    ]


def test_score_repository_returns_zero_without_evidence() -> None:
    result = score_repository(create_repository_analysis())

    assert result.overall_score == 0
    assert all(dimension.points_earned == 0 for dimension in result.dimensions)
    assert all(dimension.score == 0 for dimension in result.dimensions)


def test_documentation_only_score_uses_exact_rule_points() -> None:
    result = score_repository(
        create_repository_analysis(
            readme_overrides={
                "exists": True,
                "has_title": True,
                "has_description": True,
            }
        )
    )

    documentation = get_dimension(result, "documentation")

    assert documentation.points_earned == 21
    assert documentation.points_possible == 50
    assert documentation.score == 42
    assert result.overall_score == 21


def test_tests_structure_awards_18_points() -> None:
    result = score_repository(
        create_repository_analysis(
            structure_overrides={
                "has_tests": True,
                "has_ci": False,
            }
        )
    )

    testing = get_dimension(result, "testing_automation")

    assert testing.points_earned == 18
    assert testing.points_possible == 30
    assert result.overall_score == 18


def test_ci_workflow_awards_12_points() -> None:
    result = score_repository(
        create_repository_analysis(
            structure_overrides={
                "has_tests": False,
                "has_ci": True,
            }
        )
    )

    testing = get_dimension(result, "testing_automation")

    assert testing.points_earned == 12
    assert testing.points_possible == 30
    assert result.overall_score == 12


@pytest.mark.parametrize(
    (
        "field_name",
        "rule_key",
        "expected_points",
    ),
    [
        ("has_gitignore", "gitignore", 8),
        ("has_license", "license", 7),
        ("has_contributing", "contributing", 5),
    ],
)
def test_repository_hygiene_rules_use_exact_points(
    field_name: str,
    rule_key: str,
    expected_points: int,
) -> None:
    result = score_repository(
        create_repository_analysis(
            structure_overrides={field_name: True},
        )
    )

    hygiene = get_dimension(result, "repository_hygiene")
    rule = next(item for item in hygiene.rules if item.key == rule_key)

    assert hygiene.points_earned == expected_points
    assert result.overall_score == expected_points
    assert rule.passed is True
    assert rule.points_earned == expected_points
    assert rule.points_possible == expected_points


def test_dimension_score_is_normalized_to_zero_through_100() -> None:
    result = score_repository(
        create_repository_analysis(
            readme_overrides={
                "exists": True,
                "has_description": True,
                "has_installation": True,
            }
        )
    )

    documentation = get_dimension(result, "documentation")

    assert documentation.points_earned == 25
    assert documentation.points_possible == 50
    assert documentation.score == 50


def test_normalization_uses_integer_half_up_rounding() -> None:
    assert (
        normalize_score(
            points_earned=1,
            points_possible=8,
        )
        == 13
    )
    assert (
        normalize_score(
            points_earned=1,
            points_possible=6,
        )
        == 17
    )
    assert (
        normalize_score(
            points_earned=0,
            points_possible=8,
        )
        == 0
    )
    assert (
        normalize_score(
            points_earned=8,
            points_possible=8,
        )
        == 100
    )


def test_overall_score_stays_within_boundaries() -> None:
    analyses = [
        create_repository_analysis(),
        create_repository_analysis(
            readme_overrides=FULL_README_EVIDENCE,
            structure_overrides=FULL_STRUCTURE_EVIDENCE,
        ),
        create_repository_analysis(
            readme_overrides={
                "exists": True,
                "has_usage": True,
            },
            structure_overrides={
                "has_ci": True,
                "has_license": True,
            },
        ),
    ]

    for analysis in analyses:
        result = score_repository(analysis)

        assert 0 <= result.overall_score <= 100


def test_score_result_explains_and_preserves_rule_math() -> None:
    result = score_repository(
        create_repository_analysis(
            readme_overrides={"exists": True},
        )
    )

    expected_rules = [
        (
            "documentation",
            [
                ("readme_exists", 8),
                ("readme_title", 5),
                ("readme_description", 8),
                ("readme_installation", 9),
                ("readme_usage", 9),
                ("readme_technologies", 6),
                ("readme_requirements", 5),
            ],
        ),
        (
            "testing_automation",
            [
                ("tests_structure", 18),
                ("ci_workflow", 12),
            ],
        ),
        (
            "repository_hygiene",
            [
                ("gitignore", 8),
                ("license", 7),
                ("contributing", 5),
            ],
        ),
    ]

    for dimension, expected in zip(
        result.dimensions,
        expected_rules,
        strict=True,
    ):
        expected_dimension_key, expected_rule_points = expected

        assert dimension.key == expected_dimension_key
        assert [
            (rule.key, rule.points_possible) for rule in dimension.rules
        ] == expected_rule_points

        assert sum(rule.points_earned for rule in dimension.rules) == dimension.points_earned
        assert sum(rule.points_possible for rule in dimension.rules) == dimension.points_possible

        for rule in dimension.rules:
            assert rule.evidence
            assert rule.points_earned in {
                0,
                rule.points_possible,
            }

    assert sum(dimension.points_earned for dimension in result.dimensions) == result.overall_score
    assert sum(dimension.points_possible for dimension in result.dimensions) == 100

    documentation = get_dimension(result, "documentation")

    assert documentation.rules[0].model_dump() == {
        "key": "readme_exists",
        "label": "README exists",
        "passed": True,
        "points_earned": 8,
        "points_possible": 8,
        "evidence": "Root README.md content was available.",
    }


def test_score_repository_is_deterministic() -> None:
    analysis = create_repository_analysis(
        readme_overrides={
            "exists": True,
            "has_title": True,
            "has_usage": True,
        },
        structure_overrides={
            "has_ci": True,
            "has_license": True,
        },
        tree_truncated=True,
    )

    first = score_repository(analysis)
    second = score_repository(analysis)

    assert first.model_dump() == second.model_dump()


def test_excluded_evidence_does_not_change_v1_score() -> None:
    baseline = score_repository(
        create_repository_analysis(
            readme_overrides={
                "exists": True,
                "content_length": 10,
            }
        )
    )

    many_technologies = TechnologyAnalysis(
        dependencies=[
            "fastapi",
            "pandas",
            "pytest",
            "react",
            "redis",
        ],
        technologies=[
            DetectedTechnology(
                name="FastAPI",
                category="Backend",
                source_dependency="fastapi",
            ),
            DetectedTechnology(
                name="Pandas",
                category="Data & ML",
                source_dependency="pandas",
            ),
            DetectedTechnology(
                name="pytest",
                category="Testing",
                source_dependency="pytest",
            ),
            DetectedTechnology(
                name="React",
                category="Frontend",
                source_dependency="react",
            ),
            DetectedTechnology(
                name="Redis",
                category="Database",
                source_dependency="redis",
            ),
        ],
    )

    excluded_evidence_result = score_repository(
        create_repository_analysis(
            readme_overrides={
                "exists": True,
                "content_length": 10_000,
                "has_images": True,
                "has_demo_link": True,
            },
            structure_overrides={
                "has_dockerfile": True,
                "has_compose": True,
                "has_env_example": True,
            },
            stars=1_000_000,
            forks=500_000,
            technologies=many_technologies,
        )
    )

    assert excluded_evidence_result == baseline


def test_classification_does_not_change_quality_score() -> None:
    machine_learning = score_repository(
        create_repository_analysis(
            readme_overrides={"exists": True},
            classification=create_classification(RepositoryCategory.MACHINE_LEARNING),
        )
    )
    frontend = score_repository(
        create_repository_analysis(
            readme_overrides={"exists": True},
            classification=create_classification(RepositoryCategory.FRONTEND),
        )
    )

    assert machine_learning == frontend


def test_truncated_tree_marks_score_partial_without_adjustment() -> None:
    result = score_repository(
        create_repository_analysis(
            structure_overrides={"has_tests": True},
            tree_truncated=True,
        )
    )

    testing = get_dimension(result, "testing_automation")

    assert result.overall_score == 18
    assert testing.points_earned == 18
    assert result.is_partial is True
    assert result.limitations == [
        "Repository tree response was truncated; structure-based signals may be incomplete."
    ]
