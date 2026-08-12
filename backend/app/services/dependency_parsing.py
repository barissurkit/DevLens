import json
import re

import tomllib

PYTHON_PACKAGE_SEPARATOR_PATTERN = re.compile(r"[-_.]+")
PACKAGE_JSON_DEPENDENCY_SECTIONS: tuple[str, ...] = (
    "dependencies",
    "devDependencies",
)


def normalize_python_dependency_name(name: str) -> str:
    return PYTHON_PACKAGE_SEPARATOR_PATTERN.sub(
        "-",
        name.strip().casefold(),
    )


def normalize_npm_dependency_name(name: str) -> str:
    return name.strip().casefold()


PYTHON_REQUIREMENT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"(?:\[[A-Za-z0-9._,-]+\])?"
    r"(?:\s*(?:===|==|~=|!=|<=|>=|<|>)\s*[^;,\s]+"
    r"(?:\s*,\s*(?:===|==|~=|!=|<=|>=|<|>)"
    r"\s*[^;,\s]+)*)?"
    r"(?:\s*;\s*.+)?$"
)

REQUIREMENTS_IGNORED_PREFIXES: tuple[str, ...] = (
    "-r ",
    "--requirement ",
    "-c ",
    "--constraint ",
    "--index-url ",
    "--extra-index-url ",
    "--find-links ",
    "-e ",
    "--editable ",
    "git+",
    "http://",
    "https://",
)


def parse_requirements(content: str) -> list[str]:
    dependencies: list[str] = []
    seen_dependencies: set[str] = set()

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.casefold().startswith(REQUIREMENTS_IGNORED_PREFIXES):
            continue

        declaration = re.split(
            r"\s+#",
            line,
            maxsplit=1,
        )[0].strip()

        match = PYTHON_REQUIREMENT_PATTERN.fullmatch(declaration)

        if match is None:
            raise ValueError(f"Unsupported requirements.txt entry: {raw_line.strip()}")

        dependency = normalize_python_dependency_name(match.group("name"))

        if dependency not in seen_dependencies:
            seen_dependencies.add(dependency)
            dependencies.append(dependency)

    return dependencies


def parse_package_json(content: str) -> list[str]:
    if not content.strip():
        return []

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("package.json contains invalid JSON.") from error

    if not isinstance(payload, dict):
        raise ValueError("package.json root must be a JSON object.")

    dependencies: list[str] = []
    seen_dependencies: set[str] = set()

    for section_name in PACKAGE_JSON_DEPENDENCY_SECTIONS:
        section = payload.get(section_name)

        if section is None:
            continue

        if not isinstance(section, dict):
            raise ValueError(f"package.json {section_name} must be a JSON object.")

        for dependency_name, version in section.items():
            if not dependency_name.strip():
                raise ValueError("package.json dependency names must not be empty.")

            if not isinstance(version, str):
                raise ValueError("package.json dependency versions must be strings.")

            dependency = normalize_npm_dependency_name(dependency_name)

            if dependency not in seen_dependencies:
                seen_dependencies.add(dependency)
                dependencies.append(dependency)

    return dependencies


def _append_python_dependency(
    dependency_name: str,
    dependencies: list[str],
    seen_dependencies: set[str],
) -> None:
    dependency = normalize_python_dependency_name(dependency_name)

    if not dependency:
        raise ValueError("Python dependency name must not be empty.")

    if dependency not in seen_dependencies:
        seen_dependencies.add(dependency)
        dependencies.append(dependency)


def _collect_poetry_dependency_table(
    table: object,
    *,
    source: str,
    dependencies: list[str],
    seen_dependencies: set[str],
) -> None:
    if not isinstance(table, dict):
        raise ValueError(f"pyproject.toml {source} must be a TOML table.")

    for dependency_name in table:
        if not isinstance(dependency_name, str) or not dependency_name.strip():
            raise ValueError("Poetry dependency names must be non-empty strings.")

        if dependency_name.casefold() == "python":
            continue

        _append_python_dependency(
            dependency_name,
            dependencies,
            seen_dependencies,
        )


def parse_pyproject_toml(content: str) -> list[str]:
    if not content.strip():
        return []

    try:
        payload = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise ValueError("pyproject.toml contains invalid TOML.") from error

    dependencies: list[str] = []
    seen_dependencies: set[str] = set()

    project = payload.get("project")

    if project is not None:
        if not isinstance(project, dict):
            raise ValueError("pyproject.toml project must be a TOML table.")

        declarations = project.get("dependencies", [])

        if not isinstance(declarations, list) or not all(
            isinstance(declaration, str) for declaration in declarations
        ):
            raise ValueError("pyproject.toml project.dependencies must be an array of strings.")

        for declaration in declarations:
            match = PYTHON_REQUIREMENT_PATTERN.fullmatch(declaration.strip())

            if match is None:
                raise ValueError(
                    f"Unsupported pyproject.toml dependency declaration: {declaration}"
                )

            _append_python_dependency(
                match.group("name"),
                dependencies,
                seen_dependencies,
            )

    tool = payload.get("tool")

    if tool is None:
        return dependencies

    if not isinstance(tool, dict):
        raise ValueError("pyproject.toml tool must be a TOML table.")

    poetry = tool.get("poetry")

    if poetry is None:
        return dependencies

    if not isinstance(poetry, dict):
        raise ValueError("pyproject.toml tool.poetry must be a TOML table.")

    _collect_poetry_dependency_table(
        poetry.get("dependencies", {}),
        source="tool.poetry.dependencies",
        dependencies=dependencies,
        seen_dependencies=seen_dependencies,
    )

    groups = poetry.get("group", {})

    if not isinstance(groups, dict):
        raise ValueError("pyproject.toml tool.poetry.group must be a TOML table.")

    for group_name, group in groups.items():
        if not isinstance(group, dict):
            raise ValueError(f"pyproject.toml tool.poetry.group.{group_name} must be a TOML table.")

        _collect_poetry_dependency_table(
            group.get("dependencies", {}),
            source=(f"tool.poetry.group.{group_name}.dependencies"),
            dependencies=dependencies,
            seen_dependencies=seen_dependencies,
        )

    return dependencies
