from dataclasses import dataclass

from app.schemas.analysis import (
    DetectedTechnology,
    TechnologyAnalysis,
    TechnologyCategory,
)
from app.services.dependency_parsing import (
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements,
)


@dataclass(frozen=True, slots=True)
class TechnologyDefinition:
    dependency_name: str
    canonical_name: str
    category: TechnologyCategory


TECHNOLOGY_REGISTRY: tuple[TechnologyDefinition, ...] = (
    TechnologyDefinition("pandas", "Pandas", "Data & ML"),
    TechnologyDefinition("numpy", "NumPy", "Data & ML"),
    TechnologyDefinition("scikit-learn", "Scikit-learn", "Data & ML"),
    TechnologyDefinition("matplotlib", "Matplotlib", "Data & ML"),
    TechnologyDefinition("seaborn", "Seaborn", "Data & ML"),
    TechnologyDefinition("xgboost", "XGBoost", "Data & ML"),
    TechnologyDefinition("catboost", "CatBoost", "Data & ML"),
    TechnologyDefinition("tensorflow", "TensorFlow", "Data & ML"),
    TechnologyDefinition("torch", "PyTorch", "Data & ML"),
    TechnologyDefinition(
        "pytorch-lightning",
        "PyTorch Lightning",
        "Data & ML",
    ),
    TechnologyDefinition("fastapi", "FastAPI", "Backend"),
    TechnologyDefinition("flask", "Flask", "Backend"),
    TechnologyDefinition("django", "Django", "Backend"),
    TechnologyDefinition("uvicorn", "Uvicorn", "Backend"),
    TechnologyDefinition("sqlalchemy", "SQLAlchemy", "Backend"),
    TechnologyDefinition("pydantic", "Pydantic", "Backend"),
    TechnologyDefinition("react", "React", "Frontend"),
    TechnologyDefinition("next", "Next.js", "Frontend"),
    TechnologyDefinition("vue", "Vue", "Frontend"),
    TechnologyDefinition("@angular/core", "Angular", "Frontend"),
    TechnologyDefinition("tailwindcss", "Tailwind CSS", "Frontend"),
    TechnologyDefinition("pytest", "pytest", "Testing"),
    TechnologyDefinition("vitest", "Vitest", "Testing"),
    TechnologyDefinition("jest", "Jest", "Testing"),
    TechnologyDefinition(
        "@testing-library/react",
        "Testing Library for React",
        "Testing",
    ),
    TechnologyDefinition("psycopg", "Psycopg", "Database"),
    TechnologyDefinition("asyncpg", "asyncpg", "Database"),
    TechnologyDefinition("redis", "Redis", "Database"),
)


def detect_technologies(
    dependencies: list[str],
) -> TechnologyAnalysis:
    unique_dependencies = sorted(set(dependencies))
    registry_by_dependency = {
        definition.dependency_name: definition for definition in TECHNOLOGY_REGISTRY
    }

    technologies: list[DetectedTechnology] = []

    for dependency in unique_dependencies:
        definition = registry_by_dependency.get(dependency)

        if definition is None:
            continue

        technologies.append(
            DetectedTechnology(
                name=definition.canonical_name,
                category=definition.category,
                source_dependency=dependency,
            )
        )

    return TechnologyAnalysis(
        dependencies=unique_dependencies,
        technologies=technologies,
    )


def analyze_dependency_manifests(
    *,
    requirements_content: str | None = None,
    pyproject_content: str | None = None,
    package_json_content: str | None = None,
) -> TechnologyAnalysis:
    dependencies: list[str] = []

    if requirements_content is not None:
        dependencies.extend(parse_requirements(requirements_content))

    if pyproject_content is not None:
        dependencies.extend(parse_pyproject_toml(pyproject_content))

    if package_json_content is not None:
        dependencies.extend(parse_package_json(package_json_content))

    return detect_technologies(dependencies)
