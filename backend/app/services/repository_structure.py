from app.schemas.analysis import RepositoryStructureSignals

TEST_DIRECTORY_NAMES: frozenset[str] = frozenset({"test", "tests"})

COMPOSE_FILENAMES: frozenset[str] = frozenset(
    {
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    }
)

LICENSE_FILENAMES: frozenset[str] = frozenset(
    {
        "license",
        "license.md",
        "license.txt",
    }
)

WORKFLOW_FILE_SUFFIXES: tuple[str, ...] = (".yml", ".yaml")


def detect_structure_signals(
    paths: list[str],
) -> RepositoryStructureSignals:
    has_tests = False
    has_ci = False
    has_dockerfile = False
    has_compose = False
    has_env_example = False
    has_license = False
    has_gitignore = False
    has_contributing = False

    for path in paths:
        segments = [segment for segment in path.split("/") if segment]

        if not segments:
            continue

        directory_segments = segments[:-1]
        filename = segments[-1]
        normalized_filename = filename.lower()

        has_tests = has_tests or any(
            segment in TEST_DIRECTORY_NAMES for segment in directory_segments
        )

        has_ci = has_ci or (
            len(segments) == 3
            and segments[:2] == [".github", "workflows"]
            and filename.endswith(WORKFLOW_FILE_SUFFIXES)
        )

        has_dockerfile = has_dockerfile or filename == "Dockerfile"
        has_compose = has_compose or filename in COMPOSE_FILENAMES
        has_env_example = has_env_example or filename == ".env.example"
        has_license = has_license or normalized_filename in LICENSE_FILENAMES
        has_gitignore = has_gitignore or filename == ".gitignore"
        has_contributing = has_contributing or normalized_filename == "contributing.md"

    return RepositoryStructureSignals(
        has_tests=has_tests,
        has_ci=has_ci,
        has_dockerfile=has_dockerfile,
        has_compose=has_compose,
        has_env_example=has_env_example,
        has_license=has_license,
        has_gitignore=has_gitignore,
        has_contributing=has_contributing,
    )
