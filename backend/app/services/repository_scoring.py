from collections.abc import Callable
from dataclasses import dataclass

from app.schemas.analysis import (
    RepositoryAnalysis,
    RepositoryScore,
    ScoreDimensionResult,
    ScoreRuleResult,
)

SCORING_VERSION = "v1"
SCORING_MAX_POINTS = 100

TREE_TRUNCATION_LIMITATION = (
    "Repository tree yanıtı kısaltıldı; yapı tabanlı sinyaller eksik olabilir."
)


@dataclass(frozen=True, slots=True)
class ScoringRuleDefinition:
    key: str
    label: str
    points_possible: int
    evaluate: Callable[[RepositoryAnalysis], bool]
    passed_evidence: str
    failed_evidence: str


@dataclass(frozen=True, slots=True)
class ScoringDimensionDefinition:
    key: str
    label: str
    rules: tuple[ScoringRuleDefinition, ...]


SCORING_DIMENSIONS: tuple[ScoringDimensionDefinition, ...] = (
    ScoringDimensionDefinition(
        key="documentation",
        label="Dokümantasyon",
        rules=(
            ScoringRuleDefinition(
                key="readme_exists",
                label="README mevcut",
                points_possible=8,
                evaluate=lambda analysis: analysis.readme.exists,
                passed_evidence="Kök README.md içeriği kullanılabilir durumdaydı.",
                failed_evidence="Kök README.md içeriği kullanılabilir değildi.",
            ),
            ScoringRuleDefinition(
                key="readme_title",
                label="Başlık",
                points_possible=5,
                evaluate=lambda analysis: analysis.readme.has_title,
                passed_evidence=("Birinci seviye README başlığı sinyali tespit edildi."),
                failed_evidence=("Birinci seviye README başlığı sinyali tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="readme_description",
                label="Açıklama",
                points_possible=8,
                evaluate=lambda analysis: analysis.readme.has_description,
                passed_evidence=("Anlamlı bir README giriş sinyali tespit edildi."),
                failed_evidence=("Anlamlı bir README giriş sinyali tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="readme_installation",
                label="Kurulum",
                points_possible=9,
                evaluate=lambda analysis: analysis.readme.has_installation,
                passed_evidence=("Tanınan bir README kurulum bölümü başlığı tespit edildi."),
                failed_evidence=("Tanınan bir README kurulum bölümü başlığı tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="readme_usage",
                label="Kullanım",
                points_possible=9,
                evaluate=lambda analysis: analysis.readme.has_usage,
                passed_evidence=("Tanınan bir README kullanım bölümü başlığı tespit edildi."),
                failed_evidence=("Tanınan bir README kullanım bölümü başlığı tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="readme_technologies",
                label="Teknolojiler",
                points_possible=6,
                evaluate=lambda analysis: analysis.readme.has_technologies,
                passed_evidence=("Tanınan bir README teknolojiler bölümü başlığı tespit edildi."),
                failed_evidence=("Tanınan bir README teknolojiler bölümü başlığı tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="readme_requirements",
                label="Gereksinimler",
                points_possible=5,
                evaluate=lambda analysis: analysis.readme.has_requirements,
                passed_evidence=("Tanınan bir README gereksinimleri bölümü başlığı tespit edildi."),
                failed_evidence=("Tanınan bir README gereksinimleri bölümü başlığı tespit edilmedi."),
            ),
        ),
    ),
    ScoringDimensionDefinition(
        key="testing_automation",
        label="Test ve Otomasyon",
        rules=(
            ScoringRuleDefinition(
                key="tests_structure",
                label="Test Yapısı",
                points_possible=18,
                evaluate=lambda analysis: analysis.structure.has_tests,
                passed_evidence=("Test dizini yapısı sinyali tespit edildi."),
                failed_evidence=("Test dizini yapısı sinyali tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="ci_workflow",
                label="CI İş Akışı",
                points_possible=12,
                evaluate=lambda analysis: analysis.structure.has_ci,
                passed_evidence=("Bir GitHub Actions iş akışı dosyası sinyali tespit edildi."),
                failed_evidence=("GitHub Actions iş akışı dosyası sinyali tespit edilmedi."),
            ),
        ),
    ),
    ScoringDimensionDefinition(
        key="repository_hygiene",
        label="Repository Hijyeni",
        rules=(
            ScoringRuleDefinition(
                key="gitignore",
                label=".gitignore",
                points_possible=8,
                evaluate=lambda analysis: analysis.structure.has_gitignore,
                passed_evidence=".gitignore dosyası sinyali tespit edildi.",
                failed_evidence=".gitignore dosyası sinyali tespit edilmedi.",
            ),
            ScoringRuleDefinition(
                key="license",
                label="LICENSE",
                points_possible=7,
                evaluate=lambda analysis: analysis.structure.has_license,
                passed_evidence=("Desteklenen bir lisans dosyası adı sinyali tespit edildi."),
                failed_evidence=("Desteklenen lisans dosyası adı sinyali tespit edilmedi."),
            ),
            ScoringRuleDefinition(
                key="contributing",
                label="CONTRIBUTING",
                points_possible=5,
                evaluate=lambda analysis: analysis.structure.has_contributing,
                passed_evidence=("Bir CONTRIBUTING.md dosyası sinyali tespit edildi."),
                failed_evidence=("CONTRIBUTING.md dosyası sinyali tespit edilmedi."),
            ),
        ),
    ),
)


def normalize_score(
    *,
    points_earned: int,
    points_possible: int,
) -> int:
    if points_possible <= 0:
        raise ValueError("points_possible must be greater than zero.")

    if points_earned < 0 or points_earned > points_possible:
        raise ValueError("points_earned must be between zero and points_possible.")

    return (points_earned * SCORING_MAX_POINTS + points_possible // 2) // points_possible


def _score_rule(
    analysis: RepositoryAnalysis,
    definition: ScoringRuleDefinition,
) -> ScoreRuleResult:
    passed = definition.evaluate(analysis)

    return ScoreRuleResult(
        key=definition.key,
        label=definition.label,
        passed=passed,
        points_earned=definition.points_possible if passed else 0,
        points_possible=definition.points_possible,
        evidence=(definition.passed_evidence if passed else definition.failed_evidence),
    )


def _score_dimension(
    analysis: RepositoryAnalysis,
    definition: ScoringDimensionDefinition,
) -> ScoreDimensionResult:
    rules = [_score_rule(analysis, rule_definition) for rule_definition in definition.rules]

    points_earned = sum(rule.points_earned for rule in rules)
    points_possible = sum(rule.points_possible for rule in rules)

    return ScoreDimensionResult(
        key=definition.key,
        label=definition.label,
        points_earned=points_earned,
        points_possible=points_possible,
        score=normalize_score(
            points_earned=points_earned,
            points_possible=points_possible,
        ),
        rules=rules,
    )


def score_repository(
    analysis: RepositoryAnalysis,
) -> RepositoryScore:
    dimensions = [_score_dimension(analysis, definition) for definition in SCORING_DIMENSIONS]

    points_possible = sum(dimension.points_possible for dimension in dimensions)

    if points_possible != SCORING_MAX_POINTS:
        raise RuntimeError("V1 scoring rules must total 100 possible points.")

    overall_score = sum(dimension.points_earned for dimension in dimensions)

    limitations = [TREE_TRUNCATION_LIMITATION] if analysis.tree_truncated else []

    return RepositoryScore(
        version=SCORING_VERSION,
        overall_score=overall_score,
        dimensions=dimensions,
        is_partial=analysis.tree_truncated,
        limitations=limitations,
    )
