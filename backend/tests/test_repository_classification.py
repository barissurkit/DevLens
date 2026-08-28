from app.schemas.analysis import (
    DetectedTechnology,
    RepositoryCategory,
    RepositoryCategoryMatch,
    RepositoryClassification,
    RepositoryClassificationInput,
    RepositoryStructureSignals,
    TechnologyAnalysis,
)
from app.services.repository_classification import classify_repository


def test_repository_classification_preserves_typed_matches() -> None:
    classification = RepositoryClassification(
        categories=[
            RepositoryCategoryMatch(
                category=RepositoryCategory.MACHINE_LEARNING,
                evidence_score=8,
                evidence=[
                    "Technology: Scikit-learn",
                    "Topic: machine-learning",
                ],
            ),
            RepositoryCategoryMatch(
                category=RepositoryCategory.DATA_SCIENCE,
                evidence_score=5,
                evidence=["Technology: Pandas"],
            ),
        ],
        primary_category=RepositoryCategory.MACHINE_LEARNING,
    )

    assert classification.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert [match.category for match in classification.categories] == [
        RepositoryCategory.MACHINE_LEARNING,
        RepositoryCategory.DATA_SCIENCE,
    ]
    assert classification.categories[0].evidence_score == 8
    assert classification.categories[0].evidence


def test_repository_classification_input_combines_evidence_sources() -> None:
    classification_input = RepositoryClassificationInput(
        name="ml-api",
        description="A machine learning prediction API",
        topics=["machine-learning"],
        readme_content="# ML API\n\nBuilt with Scikit-learn.",
        technology_analysis=TechnologyAnalysis(
            dependencies=["scikit-learn"],
            technologies=[
                DetectedTechnology(
                    name="Scikit-learn",
                    category="Data & ML",
                    source_dependency="scikit-learn",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=True,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=True,
            has_contributing=False,
        ),
    )

    assert classification_input.name == "ml-api"
    assert classification_input.topics == ["machine-learning"]
    assert classification_input.technology_analysis.technologies[0].name == "Scikit-learn"
    assert classification_input.structure_signals.has_tests is True


def test_classify_repository_returns_other_without_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="empty-repository",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert len(result.categories) == 1
    assert result.categories[0].category is RepositoryCategory.OTHER
    assert result.categories[0].evidence_score == 0
    assert result.categories[0].evidence == ["Anlamlı bir sınıflandırma kanıtı bulunamadı."]


def test_classify_repository_uses_normalized_machine_learning_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="ml-project",
        description=None,
        topics=["  Machine-Learning  "],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert result.categories[0].category is RepositoryCategory.MACHINE_LEARNING
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: machine learning"]


def test_classify_repository_supports_multiple_topic_categories() -> None:
    classification_input = RepositoryClassificationInput(
        name="ml-data-project",
        description=None,
        topics=[
            "data-science",
            "machine_learning",
        ],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert [match.category for match in result.categories] == [
        RepositoryCategory.MACHINE_LEARNING,
        RepositoryCategory.DATA_SCIENCE,
    ]
    assert result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert all(match.evidence_score == 5 for match in result.categories)
    assert all(match.evidence for match in result.categories)


def test_classify_repository_uses_machine_learning_technology() -> None:
    classification_input = RepositoryClassificationInput(
        name="prediction-service",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["scikit-learn"],
            technologies=[
                DetectedTechnology(
                    name="Scikit-learn",
                    category="Data & ML",
                    source_dependency="scikit-learn",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert result.categories[0].evidence_score == 4
    assert result.categories[0].evidence == ["Tespit edilen teknoloji: Scikit-learn"]


def test_classify_repository_uses_data_science_technologies() -> None:
    classification_input = RepositoryClassificationInput(
        name="data-analysis",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["numpy", "pandas"],
            technologies=[
                DetectedTechnology(
                    name="Pandas",
                    category="Data & ML",
                    source_dependency="pandas",
                ),
                DetectedTechnology(
                    name="NumPy",
                    category="Data & ML",
                    source_dependency="numpy",
                ),
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DATA_SCIENCE
    assert result.categories[0].evidence_score == 8
    assert result.categories[0].evidence == [
        "Tespit edilen teknoloji: NumPy",
        "Tespit edilen teknoloji: Pandas",
    ]


def test_primary_category_uses_highest_evidence_score() -> None:
    classification_input = RepositoryClassificationInput(
        name="ml-data-project",
        description=None,
        topics=["machine-learning"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["numpy", "pandas"],
            technologies=[
                DetectedTechnology(
                    name="Pandas",
                    category="Data & ML",
                    source_dependency="pandas",
                ),
                DetectedTechnology(
                    name="NumPy",
                    category="Data & ML",
                    source_dependency="numpy",
                ),
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert [match.category for match in result.categories] == [
        RepositoryCategory.DATA_SCIENCE,
        RepositoryCategory.MACHINE_LEARNING,
    ]
    assert result.primary_category is RepositoryCategory.DATA_SCIENCE
    assert result.categories[0].evidence_score == 8
    assert result.categories[1].evidence_score == 5


def test_classify_repository_uses_backend_technology() -> None:
    classification_input = RepositoryClassificationInput(
        name="backend-api",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["fastapi"],
            technologies=[
                DetectedTechnology(
                    name="FastAPI",
                    category="Backend",
                    source_dependency="fastapi",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.BACKEND
    assert result.categories[0].evidence_score == 4
    assert result.categories[0].evidence == ["Tespit edilen teknoloji: FastAPI"]


def test_classify_repository_uses_frontend_technology() -> None:
    classification_input = RepositoryClassificationInput(
        name="web-interface",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["react"],
            technologies=[
                DetectedTechnology(
                    name="React",
                    category="Frontend",
                    source_dependency="react",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.FRONTEND
    assert result.categories[0].evidence_score == 4
    assert result.categories[0].evidence == ["Tespit edilen teknoloji: React"]


def test_classify_repository_derives_full_stack_category() -> None:
    classification_input = RepositoryClassificationInput(
        name="full-stack-app",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["fastapi", "react"],
            technologies=[
                DetectedTechnology(
                    name="FastAPI",
                    category="Backend",
                    source_dependency="fastapi",
                ),
                DetectedTechnology(
                    name="React",
                    category="Frontend",
                    source_dependency="react",
                ),
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert [match.category for match in result.categories] == [
        RepositoryCategory.FULL_STACK,
        RepositoryCategory.BACKEND,
        RepositoryCategory.FRONTEND,
    ]
    assert result.primary_category is RepositoryCategory.FULL_STACK
    assert result.categories[0].evidence_score == 8
    assert result.categories[0].evidence == [
        "Türetilen kategori: Backend ve Frontend kanıt eşiğini birlikte karşıladı."
    ]


def test_classify_repository_uses_explicit_devops_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="infrastructure-tooling",
        description=None,
        topics=["DevOps"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DEVOPS
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: devops"]


def test_dockerfile_alone_does_not_produce_devops_category() -> None:
    classification_input = RepositoryClassificationInput(
        name="containerized-application",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=True,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert RepositoryCategory.DEVOPS not in {match.category for match in result.categories}


def test_classify_repository_uses_data_engineering_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="event-pipeline",
        description=None,
        topics=["Data-Pipeline"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DATA_ENGINEERING
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: data pipeline"]


def test_classify_repository_uses_cli_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="terminal-helper",
        description=None,
        topics=["Command-Line"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.CLI_DEVELOPER_TOOL
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: command line"]


def test_classify_repository_uses_explicit_learning_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="python-exercises",
        description=None,
        topics=["BootCamp"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.LEARNING_EXPERIMENT
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: bootcamp"]


def test_classify_repository_uses_backend_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="service-api",
        description=None,
        topics=["REST-API"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.BACKEND
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: rest api"]


def test_classify_repository_uses_frontend_topic() -> None:
    classification_input = RepositoryClassificationInput(
        name="web-interface",
        description=None,
        topics=["FrontEnd"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.FRONTEND
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == ["GitHub konusu: frontend"]


def test_description_phrase_contributes_machine_learning_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="churn-predictor",
        description="A classification model for customer churn.",
        topics=["machine-learning"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert result.categories[0].evidence_score == 8
    assert result.categories[0].evidence == [
        "GitHub konusu: machine learning",
        'Açıklama ifadesi: "classification model"',
    ]


def test_readme_phrase_contributes_machine_learning_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="prediction-project",
        description=None,
        topics=[],
        readme_content="# Project\n\nUses a regression model.",
        technology_analysis=TechnologyAnalysis(
            dependencies=["scikit-learn"],
            technologies=[
                DetectedTechnology(
                    name="Scikit-learn",
                    category="Data & ML",
                    source_dependency="scikit-learn",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert result.categories[0].evidence_score == 6
    assert result.categories[0].evidence == [
        "Tespit edilen teknoloji: Scikit-learn",
        'README ifadesi: "regression model"',
    ]


def test_weak_readme_phrase_alone_does_not_reach_threshold() -> None:
    classification_input = RepositoryClassificationInput(
        name="ambiguous-project",
        description=None,
        topics=[],
        readme_content="This project contains a regression model.",
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert result.categories[0].category is RepositoryCategory.OTHER


def test_data_analysis_description_supports_data_science() -> None:
    classification_input = RepositoryClassificationInput(
        name="sales-analysis",
        description="Data analysis for identifying sales trends.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["pandas"],
            technologies=[
                DetectedTechnology(
                    name="Pandas",
                    category="Data & ML",
                    source_dependency="pandas",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DATA_SCIENCE
    assert result.categories[0].evidence_score == 7
    assert result.categories[0].evidence == [
        "Tespit edilen teknoloji: Pandas",
        'Açıklama ifadesi: "data analysis"',
    ]


def test_database_text_does_not_produce_data_science() -> None:
    classification_input = RepositoryClassificationInput(
        name="migration-tool",
        description="A database migration utility.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert RepositoryCategory.DATA_SCIENCE not in {match.category for match in result.categories}


def test_general_models_text_does_not_produce_machine_learning() -> None:
    classification_input = RepositoryClassificationInput(
        name="preferences-app",
        description="This application models user preferences.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert RepositoryCategory.MACHINE_LEARNING not in {
        match.category for match in result.categories
    }


def test_backend_description_supports_backend_technology() -> None:
    classification_input = RepositoryClassificationInput(
        name="orders-api",
        description="A REST API for managing customer orders.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["fastapi"],
            technologies=[
                DetectedTechnology(
                    name="FastAPI",
                    category="Backend",
                    source_dependency="fastapi",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.BACKEND
    assert result.categories[0].evidence_score == 7
    assert result.categories[0].evidence == [
        "Tespit edilen teknoloji: FastAPI",
        'Açıklama ifadesi: "rest api"',
    ]


def test_frontend_description_supports_frontend_technology() -> None:
    classification_input = RepositoryClassificationInput(
        name="dashboard-ui",
        description="A user interface for monitoring application metrics.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=["react"],
            technologies=[
                DetectedTechnology(
                    name="React",
                    category="Frontend",
                    source_dependency="react",
                )
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.FRONTEND
    assert result.categories[0].evidence_score == 7
    assert result.categories[0].evidence == [
        "Tespit edilen teknoloji: React",
        'Açıklama ifadesi: "user interface"',
    ]


def test_structure_signals_support_explicit_devops_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="deployment-tooling",
        description=None,
        topics=["devops"],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=True,
            has_dockerfile=True,
            has_compose=True,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DEVOPS
    assert result.categories[0].evidence_score == 8
    assert result.categories[0].evidence == [
        "GitHub konusu: devops",
        "Yapı sinyali: CI İş Akışı",
        "Yapı sinyali: Compose",
        "Yapı sinyali: Dockerfile",
    ]


def test_structure_signals_alone_do_not_produce_devops() -> None:
    classification_input = RepositoryClassificationInput(
        name="containerized-application",
        description=None,
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=True,
            has_dockerfile=True,
            has_compose=True,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.OTHER
    assert RepositoryCategory.DEVOPS not in {match.category for match in result.categories}


def test_devops_description_combines_with_structure_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="deployment-automation",
        description="Deployment automation for web services.",
        topics=[],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=True,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DEVOPS
    assert result.categories[0].evidence_score == 4
    assert result.categories[0].evidence == [
        'Açıklama ifadesi: "deployment automation"',
        "Yapı sinyali: CI İş Akışı",
    ]


def test_text_sources_combine_for_data_engineering() -> None:
    classification_input = RepositoryClassificationInput(
        name="warehouse-loader",
        description="An ETL pipeline for warehouse processing.",
        topics=[],
        readme_content=("# Warehouse Loader\n\nProvides data ingestion from external systems."),
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.DATA_ENGINEERING
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == [
        'Açıklama ifadesi: "etl pipeline"',
        'README ifadesi: "data ingestion"',
    ]


def test_text_sources_combine_for_cli_tool() -> None:
    classification_input = RepositoryClassificationInput(
        name="project-helper",
        description="A command-line tool for project setup.",
        topics=[],
        readme_content=("# Project Helper\n\nA developer tool for automating repetitive tasks."),
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.CLI_DEVELOPER_TOOL
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == [
        'Açıklama ifadesi: "command line tool"',
        'README ifadesi: "developer tool"',
    ]


def test_explicit_text_sources_produce_learning_category() -> None:
    classification_input = RepositoryClassificationInput(
        name="python-practice",
        description="Created during a Python bootcamp.",
        topics=[],
        readme_content=("# Python Practice\n\nA tutorial covering core Python concepts."),
        technology_analysis=TechnologyAnalysis(
            dependencies=[],
            technologies=[],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    result = classify_repository(classification_input)

    assert result.primary_category is RepositoryCategory.LEARNING_EXPERIMENT
    assert result.categories[0].evidence_score == 5
    assert result.categories[0].evidence == [
        'Açıklama ifadesi: "bootcamp"',
        'README ifadesi: "tutorial"',
    ]


def test_classification_is_deterministic_and_deduplicates_evidence() -> None:
    classification_input = RepositoryClassificationInput(
        name="duplicate-signals",
        description=None,
        topics=[
            "machine-learning",
            "Machine_Learning",
            "machine-learning",
        ],
        readme_content=None,
        technology_analysis=TechnologyAnalysis(
            dependencies=[
                "scikit-learn",
                "scikit-learn",
            ],
            technologies=[
                DetectedTechnology(
                    name="Scikit-learn",
                    category="Data & ML",
                    source_dependency="scikit-learn",
                ),
                DetectedTechnology(
                    name="Scikit-learn",
                    category="Data & ML",
                    source_dependency="scikit-learn",
                ),
            ],
        ),
        structure_signals=RepositoryStructureSignals(
            has_tests=False,
            has_ci=False,
            has_dockerfile=False,
            has_compose=False,
            has_env_example=False,
            has_license=False,
            has_gitignore=False,
            has_contributing=False,
        ),
    )

    first_result = classify_repository(classification_input)
    second_result = classify_repository(classification_input)

    assert first_result == second_result
    assert first_result.primary_category is RepositoryCategory.MACHINE_LEARNING
    assert first_result.categories[0].evidence_score == 9
    assert first_result.categories[0].evidence == [
        "GitHub konusu: machine learning",
        "Tespit edilen teknoloji: Scikit-learn",
    ]
