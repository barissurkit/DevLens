import pytest
from app.schemas.analysis import RepositoryStructureSignals
from app.services.repository_structure import detect_structure_signals


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_api.py",
        "backend/test/test_api.py",
    ],
)
def test_detect_structure_signals_detects_test_directory_segments(
    path: str,
) -> None:
    result = detect_structure_signals([path])

    assert result.has_tests is True


@pytest.mark.parametrize(
    "filename",
    [
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    ],
)
def test_detect_structure_signals_detects_compose_variations(
    filename: str,
) -> None:
    result = detect_structure_signals([f"deploy/{filename}"])

    assert result.has_compose is True


@pytest.mark.parametrize(
    "path",
    [
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "docs/license",
        "legal/License.MD",
    ],
)
def test_detect_structure_signals_detects_license_variations(
    path: str,
) -> None:
    result = detect_structure_signals([path])

    assert result.has_license is True


def test_repository_structure_signals_preserve_boolean_values() -> None:
    signals = RepositoryStructureSignals(
        has_tests=True,
        has_ci=False,
        has_dockerfile=True,
        has_compose=False,
        has_env_example=True,
        has_license=True,
        has_gitignore=True,
        has_contributing=False,
    )

    assert signals.model_dump() == {
        "has_tests": True,
        "has_ci": False,
        "has_dockerfile": True,
        "has_compose": False,
        "has_env_example": True,
        "has_license": True,
        "has_gitignore": True,
        "has_contributing": False,
    }


def test_detect_structure_signals_detects_supported_signals() -> None:
    result = detect_structure_signals(
        [
            "README.md",
            "backend/tests/test_api.py",
            ".github/workflows/ci.yml",
            "backend/Dockerfile",
            "deploy/docker-compose.yml",
            "backend/.env.example",
            "legal/LICENSE.txt",
            "frontend/.gitignore",
            "docs/contributing.md",
        ]
    )

    assert result == RepositoryStructureSignals(
        has_tests=True,
        has_ci=True,
        has_dockerfile=True,
        has_compose=True,
        has_env_example=True,
        has_license=True,
        has_gitignore=True,
        has_contributing=True,
    )


def test_detect_structure_signals_ignores_unrelated_paths() -> None:
    result = detect_structure_signals(
        [
            "README.md",
            "src/contest/runner.py",
            "src/latest/report.py",
            ".github/actions/setup/action.yml",
            "Dockerfile.example",
            "license-notice.md",
            "CONTRIBUTING.txt",
        ]
    )

    assert result == RepositoryStructureSignals(
        has_tests=False,
        has_ci=False,
        has_dockerfile=False,
        has_compose=False,
        has_env_example=False,
        has_license=False,
        has_gitignore=False,
        has_contributing=False,
    )
