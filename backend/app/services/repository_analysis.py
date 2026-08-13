from app.schemas.analysis import (
    RepositoryAnalysis,
    RepositoryClassificationInput,
)
from app.schemas.github import GitHubFileContent, GitHubRepository
from app.services.github.client import GitHubClient
from app.services.readme_analysis import analyze_readme
from app.services.repository_classification import classify_repository
from app.services.repository_structure import detect_structure_signals
from app.services.technology_detection import analyze_dependency_manifests


def _content_for(
    files: dict[str, GitHubFileContent | None],
    path: str,
) -> str | None:
    github_file = files[path]

    if github_file is None:
        return None

    return github_file.content


async def analyze_repository(
    *,
    owner: str,
    repository: GitHubRepository,
    client: GitHubClient,
) -> RepositoryAnalysis:
    """Compose the existing analyzers into one repository-level result."""

    important_files = await client.get_important_files(
        owner=owner,
        repository=repository.name,
        ref=repository.default_branch,
    )
    repository_tree = await client.get_repository_tree(
        owner=owner,
        repository=repository.name,
        ref=repository.default_branch,
    )

    readme_content = _content_for(important_files, "README.md")

    readme_analysis = analyze_readme(readme_content)
    technology_analysis = analyze_dependency_manifests(
        requirements_content=_content_for(
            important_files,
            "requirements.txt",
        ),
        pyproject_content=_content_for(
            important_files,
            "pyproject.toml",
        ),
        package_json_content=_content_for(
            important_files,
            "package.json",
        ),
    )
    structure_signals = detect_structure_signals(repository_tree.paths)

    classification = classify_repository(
        RepositoryClassificationInput(
            name=repository.name,
            description=repository.description,
            topics=repository.topics,
            readme_content=readme_content,
            technology_analysis=technology_analysis,
            structure_signals=structure_signals,
        )
    )

    return RepositoryAnalysis(
        repository=repository,
        readme=readme_analysis,
        structure=structure_signals,
        tree_truncated=repository_tree.truncated,
        technologies=technology_analysis,
        classification=classification,
    )
