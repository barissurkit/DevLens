import re
from dataclasses import dataclass

from app.schemas.analysis import (
    RepositoryCategory,
    RepositoryCategoryMatch,
    RepositoryClassification,
    RepositoryClassificationInput,
)

STRUCTURE_EVIDENCE_WEIGHT = 1
DESCRIPTION_EVIDENCE_WEIGHT = 3
TOPIC_EVIDENCE_WEIGHT = 5
MINIMUM_EVIDENCE_SCORE = 4
TECHNOLOGY_EVIDENCE_WEIGHT = 4
README_EVIDENCE_WEIGHT = 2

CATEGORY_PRIORITY: tuple[RepositoryCategory, ...] = (
    RepositoryCategory.MACHINE_LEARNING,
    RepositoryCategory.DATA_SCIENCE,
    RepositoryCategory.BACKEND,
    RepositoryCategory.FRONTEND,
    RepositoryCategory.FULL_STACK,
    RepositoryCategory.DEVOPS,
    RepositoryCategory.DATA_ENGINEERING,
    RepositoryCategory.CLI_DEVELOPER_TOOL,
    RepositoryCategory.LEARNING_EXPERIMENT,
    RepositoryCategory.OTHER,
)

CATEGORY_PRIORITY_INDEX = {category: index for index, category in enumerate(CATEGORY_PRIORITY)}
STRUCTURE_SIGNAL_LABELS: dict[str, str] = {
    "has_ci": "CI workflow",
    "has_dockerfile": "Dockerfile",
    "has_compose": "Compose",
}


@dataclass(frozen=True, slots=True)
class ClassificationRule:
    category: RepositoryCategory
    topics: frozenset[str]
    technologies: frozenset[str] = frozenset()
    text_phrases: frozenset[str] = frozenset()
    structure_signals: frozenset[str] = frozenset()


CLASSIFICATION_RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        category=RepositoryCategory.MACHINE_LEARNING,
        topics=frozenset({"machine learning"}),
        technologies=frozenset(
            {
                "Scikit-learn",
                "TensorFlow",
                "PyTorch",
                "PyTorch Lightning",
                "XGBoost",
                "CatBoost",
            }
        ),
        text_phrases=frozenset(
            {
                "machine learning",
                "classification model",
                "regression model",
                "model training",
                "predictive model",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.DATA_SCIENCE,
        topics=frozenset({"data science"}),
        technologies=frozenset(
            {
                "Pandas",
                "NumPy",
                "Matplotlib",
                "Seaborn",
            }
        ),
        text_phrases=frozenset(
            {
                "data analysis",
                "data visualization",
                "statistical analysis",
                "exploratory analysis",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.BACKEND,
        topics=frozenset(
            {
                "backend",
                "rest api",
                "fastapi",
                "django",
                "flask",
            }
        ),
        technologies=frozenset(
            {
                "FastAPI",
                "Django",
                "Flask",
                "SQLAlchemy",
            }
        ),
        text_phrases=frozenset(
            {
                "rest api",
                "backend service",
                "web api",
                "api server",
                "server side",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.FRONTEND,
        topics=frozenset(
            {
                "frontend",
                "react",
                "nextjs",
                "vue",
                "angular",
                "tailwindcss",
            }
        ),
        technologies=frozenset(
            {
                "React",
                "Next.js",
                "Vue",
                "Angular",
                "Tailwind CSS",
            }
        ),
        text_phrases=frozenset(
            {
                "frontend",
                "user interface",
                "single page application",
                "client side",
                "web interface",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.DEVOPS,
        topics=frozenset(
            {
                "devops",
                "infrastructure as code",
                "terraform",
                "kubernetes",
                "ci cd",
            }
        ),
        structure_signals=frozenset(
            {
                "has_ci",
                "has_dockerfile",
                "has_compose",
            }
        ),
        text_phrases=frozenset(
            {
                "infrastructure as code",
                "deployment automation",
                "continuous integration",
                "continuous deployment",
                "container orchestration",
                "ci/cd tooling",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.DATA_ENGINEERING,
        topics=frozenset(
            {
                "data engineering",
                "data pipeline",
                "etl",
                "airflow",
                "apache airflow",
                "spark",
                "apache spark",
                "kafka",
            }
        ),
        text_phrases=frozenset(
            {
                "data engineering",
                "data pipeline",
                "etl pipeline",
                "data ingestion",
                "stream processing",
                "batch processing",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.CLI_DEVELOPER_TOOL,
        topics=frozenset(
            {
                "cli",
                "command line",
                "command line interface",
                "developer tool",
                "terminal tool",
            }
        ),
        text_phrases=frozenset(
            {
                "command line interface",
                "command line tool",
                "developer tool",
                "terminal tool",
                "cli application",
            }
        ),
    ),
    ClassificationRule(
        category=RepositoryCategory.LEARNING_EXPERIMENT,
        topics=frozenset(
            {
                "learning",
                "tutorial",
                "practice",
                "exercise",
                "bootcamp",
                "course",
                "experiment",
                "playground",
            }
        ),
        text_phrases=frozenset(
            {
                "learning project",
                "tutorial",
                "practice project",
                "coding exercise",
                "bootcamp",
                "course project",
                "experimental project",
                "playground",
            }
        ),
    ),
)


def _normalize_text(text: str) -> str:
    normalized = text.casefold()
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("_", " ")
    return " ".join(normalized.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return re.search(pattern, text) is not None


def _normalize_topic(topic: str) -> str:
    return _normalize_text(topic)


def classify_repository(
    classification_input: RepositoryClassificationInput,
) -> RepositoryClassification:
    normalized_topics: set[str] = set()

    for topic in classification_input.topics:
        normalized_topic = _normalize_topic(topic)

        if normalized_topic:
            normalized_topics.add(normalized_topic)

    detected_technologies = {
        technology.name for technology in classification_input.technology_analysis.technologies
    }
    enabled_structure_signals = {
        signal_name
        for signal_name, enabled in classification_input.structure_signals.model_dump().items()
        if enabled
    }

    matches: list[RepositoryCategoryMatch] = []

    normalized_description = _normalize_text(classification_input.description or "")
    normalized_readme = _normalize_text(classification_input.readme_content or "")

    for rule in CLASSIFICATION_RULES:
        matching_topics = sorted(normalized_topics.intersection(rule.topics))
        matching_technologies = sorted(detected_technologies.intersection(rule.technologies))
        matching_description_phrases = sorted(
            phrase
            for phrase in rule.text_phrases
            if _contains_phrase(normalized_description, phrase)
        )

        topic_evidence = [f"GitHub topic: {topic}" for topic in matching_topics]
        technology_evidence = [
            f"Detected technology: {technology}" for technology in matching_technologies
        ]
        description_evidence = [
            f'Description phrase: "{phrase}"' for phrase in matching_description_phrases
        ]
        matching_readme_phrases = sorted(
            phrase for phrase in rule.text_phrases if _contains_phrase(normalized_readme, phrase)
        )
        matching_structure_signals = sorted(
            enabled_structure_signals.intersection(rule.structure_signals)
        )
        structure_evidence = [
            f"Structure signal: {STRUCTURE_SIGNAL_LABELS[signal]}"
            for signal in matching_structure_signals
        ]
        readme_evidence = [f'README phrase: "{phrase}"' for phrase in matching_readme_phrases]
        evidence = (
            topic_evidence
            + technology_evidence
            + description_evidence
            + readme_evidence
            + structure_evidence
        )
        evidence_score = (
            len(matching_topics) * TOPIC_EVIDENCE_WEIGHT
            + len(matching_technologies) * TECHNOLOGY_EVIDENCE_WEIGHT
            + len(matching_description_phrases) * DESCRIPTION_EVIDENCE_WEIGHT
            + len(matching_readme_phrases) * README_EVIDENCE_WEIGHT
            + len(matching_structure_signals) * STRUCTURE_EVIDENCE_WEIGHT
        )

        if evidence_score >= MINIMUM_EVIDENCE_SCORE:
            matches.append(
                RepositoryCategoryMatch(
                    category=rule.category,
                    evidence_score=evidence_score,
                    evidence=evidence,
                )
            )

    matches_by_category = {match.category: match for match in matches}

    backend_match = matches_by_category.get(RepositoryCategory.BACKEND)
    frontend_match = matches_by_category.get(RepositoryCategory.FRONTEND)

    if backend_match is not None and frontend_match is not None:
        matches.append(
            RepositoryCategoryMatch(
                category=RepositoryCategory.FULL_STACK,
                evidence_score=(backend_match.evidence_score + frontend_match.evidence_score),
                evidence=[
                    "Derived category: Backend and Frontend both met the evidence threshold."
                ],
            )
        )

    matches.sort(
        key=lambda match: (
            -match.evidence_score,
            CATEGORY_PRIORITY_INDEX[match.category],
        )
    )

    if matches:
        return RepositoryClassification(
            categories=matches,
            primary_category=matches[0].category,
        )

    return RepositoryClassification(
        categories=[
            RepositoryCategoryMatch(
                category=RepositoryCategory.OTHER,
                evidence_score=0,
                evidence=["No meaningful classification evidence found."],
            )
        ],
        primary_category=RepositoryCategory.OTHER,
    )
