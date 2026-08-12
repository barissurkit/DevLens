import pytest
from app.schemas.analysis import (
    DetectedTechnology,
    TechnologyAnalysis,
)
from app.services.technology_detection import (
    analyze_dependency_manifests,
    detect_technologies,
)


def test_technology_analysis_preserves_dependencies_and_technologies() -> None:
    analysis = TechnologyAnalysis(
        dependencies=[
            "fastapi",
            "some-special-library",
        ],
        technologies=[
            DetectedTechnology(
                name="FastAPI",
                category="Backend",
                source_dependency="fastapi",
            )
        ],
    )

    assert analysis.model_dump() == {
        "dependencies": [
            "fastapi",
            "some-special-library",
        ],
        "technologies": [
            {
                "name": "FastAPI",
                "category": "Backend",
                "source_dependency": "fastapi",
            }
        ],
    }


@pytest.mark.parametrize(
    ("dependency", "name", "category"),
    [
        ("pandas", "Pandas", "Data & ML"),
        ("scikit-learn", "Scikit-learn", "Data & ML"),
        ("torch", "PyTorch", "Data & ML"),
        ("fastapi", "FastAPI", "Backend"),
        ("react", "React", "Frontend"),
        ("next", "Next.js", "Frontend"),
        ("pytest", "pytest", "Testing"),
        ("vitest", "Vitest", "Testing"),
    ],
)
def test_detect_technologies_maps_known_dependencies(
    dependency: str,
    name: str,
    category: str,
) -> None:
    result = detect_technologies([dependency])

    assert result.dependencies == [dependency]
    assert result.technologies[0].name == name
    assert result.technologies[0].category == category
    assert result.technologies[0].source_dependency == dependency


def test_detect_technologies_preserves_unknown_dependency() -> None:
    result = detect_technologies(["some-special-library"])

    assert result.dependencies == ["some-special-library"]
    assert result.technologies == []


def test_detect_technologies_removes_duplicates_and_sorts_results() -> None:
    first = detect_technologies(
        [
            "pytest",
            "pandas",
            "fastapi",
            "pytest",
            "some-special-library",
        ]
    )
    second = detect_technologies(
        [
            "some-special-library",
            "fastapi",
            "pandas",
            "pytest",
        ]
    )

    assert first == second
    assert first.dependencies == [
        "fastapi",
        "pandas",
        "pytest",
        "some-special-library",
    ]
    assert [technology.source_dependency for technology in first.technologies] == [
        "fastapi",
        "pandas",
        "pytest",
    ]


def test_analyze_dependency_manifests_combines_all_sources() -> None:
    result = analyze_dependency_manifests(
        requirements_content="""
FastAPI>=0.115
pytest>=8
some-special-library
""",
        pyproject_content="""
[project]
dependencies = [
    "Pandas>=2",
    "pytest>=8",
]
""",
        package_json_content="""
{
  "dependencies": {
    "React": "^19.0.0",
    "next": "15.0.0"
  },
  "devDependencies": {
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0"
  }
}
""",
    )

    assert result.dependencies == [
        "@testing-library/react",
        "fastapi",
        "next",
        "pandas",
        "pytest",
        "react",
        "some-special-library",
        "vitest",
    ]

    assert [technology.source_dependency for technology in result.technologies] == [
        "@testing-library/react",
        "fastapi",
        "next",
        "pandas",
        "pytest",
        "react",
        "vitest",
    ]


def test_analyze_dependency_manifests_accepts_missing_files() -> None:
    result = analyze_dependency_manifests()

    assert result == TechnologyAnalysis(
        dependencies=[],
        technologies=[],
    )


def test_analyze_dependency_manifests_propagates_parse_errors() -> None:
    with pytest.raises(
        ValueError,
        match="package.json contains invalid JSON",
    ):
        analyze_dependency_manifests(package_json_content='{"dependencies":')
