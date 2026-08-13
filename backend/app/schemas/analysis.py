from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.github import GitHubRepository


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


TechnologyCategory = Literal[
    "Data & ML",
    "Backend",
    "Frontend",
    "Testing",
    "Database",
]


class DetectedTechnology(BaseModel):
    name: str
    category: TechnologyCategory
    source_dependency: str


class TechnologyAnalysis(BaseModel):
    dependencies: list[str]
    technologies: list[DetectedTechnology]


class RepositoryClassificationInput(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    topics: list[str] = Field(default_factory=list)
    readme_content: str | None = None
    technology_analysis: TechnologyAnalysis
    structure_signals: RepositoryStructureSignals


class RepositoryCategory(StrEnum):
    MACHINE_LEARNING = "Machine Learning"
    DATA_SCIENCE = "Data Science"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    FULL_STACK = "Full Stack"
    DEVOPS = "DevOps"
    DATA_ENGINEERING = "Data Engineering"
    CLI_DEVELOPER_TOOL = "CLI / Developer Tool"
    LEARNING_EXPERIMENT = "Learning / Experiment"
    OTHER = "Other"


class RepositoryCategoryMatch(BaseModel):
    category: RepositoryCategory
    evidence_score: int = Field(ge=0)
    evidence: list[str] = Field(min_length=1)


class RepositoryClassification(BaseModel):
    categories: list[RepositoryCategoryMatch] = Field(min_length=1)
    primary_category: RepositoryCategory


class RepositoryAnalysis(BaseModel):
    repository: GitHubRepository
    readme: ReadmeAnalysis
    structure: RepositoryStructureSignals
    tree_truncated: bool
    technologies: TechnologyAnalysis
    classification: RepositoryClassification


class ScoreRuleResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    passed: bool
    points_earned: int = Field(ge=0)
    points_possible: int = Field(gt=0)
    evidence: str = Field(min_length=1)


class ScoreDimensionResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    points_earned: int = Field(ge=0)
    points_possible: int = Field(gt=0)
    score: int = Field(ge=0, le=100)
    rules: list[ScoreRuleResult] = Field(min_length=1)


class RepositoryScore(BaseModel):
    version: str = Field(min_length=1)
    overall_score: int = Field(ge=0, le=100)
    dimensions: list[ScoreDimensionResult] = Field(min_length=1)
    is_partial: bool
    limitations: list[str]
