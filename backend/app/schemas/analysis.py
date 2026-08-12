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


class ReadmeAnalysis(BaseModel):
    exists: bool
    content_length: int
    has_title: bool
    has_description: bool
    has_installation: bool
    has_usage: bool
    has_technologies: bool
    has_requirements: bool
    has_images: bool
    has_demo_link: bool
