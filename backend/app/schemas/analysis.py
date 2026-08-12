from pydantic import BaseModel


class RepositoryStructureSignals(BaseModel):
    has_tests: bool
    has_ci: bool
    has_dockerfile: bool
    has_compose: bool
    has_env_example: bool
    has_license: bool
    has_gitignore: bool
    has_contributing: bool
