import pytest
from app.services.dependency_parsing import (
    normalize_npm_dependency_name,
    normalize_python_dependency_name,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Pandas", "pandas"),
        ("scikit_learn", "scikit-learn"),
        ("scikit.learn", "scikit-learn"),
        ("pytorch-lightning", "pytorch-lightning"),
    ],
)
def test_normalize_python_dependency_name(
    name: str,
    expected: str,
) -> None:
    assert normalize_python_dependency_name(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("React", "react"),
        (" @Testing-Library/React ", "@testing-library/react"),
        ("@scope/package_name", "@scope/package_name"),
    ],
)
def test_normalize_npm_dependency_name(
    name: str,
    expected: str,
) -> None:
    assert normalize_npm_dependency_name(name) == expected


def test_parse_requirements_extracts_dependency_names() -> None:
    content = """
pandas
numpy==2.0.0
scikit-learn>=1.5
fastapi~=0.115
httpx[http2]>=0.27
pytest>=8.0  # testing
"""

    assert parse_requirements(content) == [
        "pandas",
        "numpy",
        "scikit-learn",
        "fastapi",
        "httpx",
        "pytest",
    ]


def test_parse_requirements_ignores_unsupported_sources() -> None:
    content = """
# Development dependencies

-r requirements-dev.txt
--index-url https://packages.example.com/simple
git+https://github.com/example/package.git
fastapi>=0.115
"""

    assert parse_requirements(content) == ["fastapi"]


def test_parse_requirements_removes_normalized_duplicates() -> None:
    content = """
Pandas
pandas==2.0
scikit_learn>=1.5
scikit-learn
"""

    assert parse_requirements(content) == [
        "pandas",
        "scikit-learn",
    ]


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n\t ",
    ],
)
def test_parse_requirements_accepts_empty_content(
    content: str,
) -> None:
    assert parse_requirements(content) == []


def test_parse_requirements_rejects_malformed_declaration() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported requirements.txt entry",
    ):
        parse_requirements("not a valid requirement")


def test_parse_package_json_extracts_dependencies() -> None:
    content = """
{
  "dependencies": {
    "react": "^19.0.0",
    "next": "15.0.0"
  },
  "devDependencies": {
    "vitest": "^3.0.0"
  }
}
"""

    assert parse_package_json(content) == [
        "react",
        "next",
        "vitest",
    ]


def test_parse_package_json_removes_normalized_duplicates() -> None:
    content = """
{
  "dependencies": {
    "React": "^19.0.0",
    "@Testing-Library/React": "^16.0.0"
  },
  "devDependencies": {
    "react": "^19.0.0",
    "@testing-library/react": "^16.0.0"
  }
}
"""

    assert parse_package_json(content) == [
        "react",
        "@testing-library/react",
    ]


def test_parse_package_json_rejects_malformed_json() -> None:
    with pytest.raises(
        ValueError,
        match="contains invalid JSON",
    ):
        parse_package_json('{"dependencies":')


def test_parse_package_json_accepts_missing_dependency_sections() -> None:
    assert parse_package_json('{"name": "devlens", "private": true}') == []


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n\t ",
    ],
)
def test_parse_package_json_accepts_empty_content(
    content: str,
) -> None:
    assert parse_package_json(content) == []


def test_parse_package_json_rejects_invalid_dependency_section() -> None:
    with pytest.raises(
        ValueError,
        match="dependencies must be a JSON object",
    ):
        parse_package_json('{"dependencies": []}')


def test_parse_pyproject_toml_extracts_project_dependencies() -> None:
    content = """
[project]
dependencies = [
    "FastAPI>=0.115",
    "fastapi==0.115.12",
    "pydantic>=2",
    "httpx[http2]>=0.27",
    "scikit_learn>=1.5",
]
"""

    assert parse_pyproject_toml(content) == [
        "fastapi",
        "pydantic",
        "httpx",
        "scikit-learn",
    ]


def test_parse_pyproject_toml_accepts_empty_dependency_list() -> None:
    content = """
[project]
dependencies = []
"""

    assert parse_pyproject_toml(content) == []


def test_parse_pyproject_toml_accepts_missing_project_table() -> None:
    content = """
[build-system]
requires = ["setuptools"]
"""

    assert parse_pyproject_toml(content) == []


def test_parse_pyproject_toml_rejects_malformed_toml() -> None:
    with pytest.raises(
        ValueError,
        match="contains invalid TOML",
    ):
        parse_pyproject_toml("[project\ndependencies = []")


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n\t ",
    ],
)
def test_parse_pyproject_toml_accepts_empty_content(
    content: str,
) -> None:
    assert parse_pyproject_toml(content) == []


@pytest.mark.parametrize(
    "content",
    [
        """
[project]
dependencies = "fastapi"
""",
        """
[project]
dependencies = [42]
""",
    ],
)
def test_parse_pyproject_toml_rejects_invalid_dependency_structure(
    content: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be an array of strings",
    ):
        parse_pyproject_toml(content)


def test_parse_pyproject_toml_extracts_poetry_dependencies() -> None:
    content = """
[tool.poetry.dependencies]
python = "^3.12"
Pandas = "^2.2"
scikit_learn = { version = "^1.5", optional = true }
"""

    assert parse_pyproject_toml(content) == [
        "pandas",
        "scikit-learn",
    ]


def test_parse_pyproject_toml_extracts_poetry_groups() -> None:
    content = """
[tool.poetry.dependencies]
fastapi = "^0.115"

[tool.poetry.group.dev.dependencies]
PyTest = "^8.0"

[tool.poetry.group.ml.dependencies]
torch = "^2.0"
"""

    assert parse_pyproject_toml(content) == [
        "fastapi",
        "pytest",
        "torch",
    ]


def test_parse_pyproject_toml_removes_cross_format_duplicates() -> None:
    content = """
[project]
dependencies = [
    "fastapi>=0.115",
    "pytest>=8",
]

[tool.poetry.dependencies]
FastAPI = "^0.115"

[tool.poetry.group.dev.dependencies]
PyTest = "^8.0"
"""

    assert parse_pyproject_toml(content) == [
        "fastapi",
        "pytest",
    ]


@pytest.mark.parametrize(
    "content",
    [
        """
[tool.poetry]
dependencies = ["fastapi"]
""",
        """
[tool.poetry.group.dev]
dependencies = ["pytest"]
""",
    ],
)
def test_parse_pyproject_toml_rejects_invalid_poetry_tables(
    content: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be a TOML table",
    ):
        parse_pyproject_toml(content)
