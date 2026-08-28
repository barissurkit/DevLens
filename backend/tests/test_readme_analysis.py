import pytest
from app.schemas.analysis import ReadmeAnalysis
from app.services.readme_analysis import _is_deployment_url, analyze_readme


def test_readme_analysis_represents_missing_readme() -> None:
    analysis = ReadmeAnalysis(
        exists=False,
        content_length=0,
        has_title=False,
        has_description=False,
        has_installation=False,
        has_usage=False,
        has_technologies=False,
        has_requirements=False,
        has_images=False,
        has_demo_link=False,
    )

    assert analysis.model_dump() == {
        "exists": False,
        "content_length": 0,
        "has_title": False,
        "has_description": False,
        "has_installation": False,
        "has_usage": False,
        "has_technologies": False,
        "has_requirements": False,
        "has_images": False,
        "has_demo_link": False,
    }


def test_analyze_readme_returns_missing_result_for_none() -> None:
    result = analyze_readme(None)

    assert result == ReadmeAnalysis(
        exists=False,
        content_length=0,
        has_title=False,
        has_description=False,
        has_installation=False,
        has_usage=False,
        has_technologies=False,
        has_requirements=False,
        has_images=False,
        has_demo_link=False,
    )


@pytest.mark.parametrize(
    "content",
    [
        "",
        " \n\t ",
    ],
)
def test_analyze_readme_treats_empty_content_as_existing(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.exists is True
    assert result.content_length == 0
    assert result.has_title is False
    assert result.has_description is False
    assert result.has_installation is False
    assert result.has_usage is False
    assert result.has_technologies is False
    assert result.has_requirements is False
    assert result.has_images is False
    assert result.has_demo_link is False


def test_analyze_readme_normalizes_content_length() -> None:
    result = analyze_readme(" \r\nLine one\r\nLine two\r\n ")

    assert result.exists is True
    assert result.content_length == len("Line one\nLine two")


@pytest.mark.parametrize(
    "content",
    [
        "# DevLens",
        "   # DevLens",
        "# DevLens #",
    ],
)
def test_analyze_readme_detects_level_one_title(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_title is True


@pytest.mark.parametrize(
    "content",
    [
        "## Installation",
        "A paragraph containing # DevLens",
        "    # Indented code",
    ],
)
def test_analyze_readme_rejects_non_title_text(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_title is False


@pytest.mark.parametrize(
    ("heading", "field_name"),
    [
        ("## Setup", "has_installation"),
        ("## Getting Started", "has_installation"),
        ("## How to Use", "has_usage"),
        ("## Tech Stack", "has_technologies"),
        ("## Prerequisites", "has_requirements"),
    ],
)
def test_analyze_readme_detects_english_section_variations(
    heading: str,
    field_name: str,
) -> None:
    result = analyze_readme(heading)

    assert getattr(result, field_name) is True


@pytest.mark.parametrize(
    ("heading", "field_name"),
    [
        ("## Kurulum", "has_installation"),
        ("## Kullanım", "has_usage"),
        ("## Teknolojiler", "has_technologies"),
        ("## Gereksinimler", "has_requirements"),
    ],
)
def test_analyze_readme_detects_turkish_sections(
    heading: str,
    field_name: str,
) -> None:
    result = analyze_readme(heading)

    assert getattr(result, field_name) is True


def test_analyze_readme_does_not_detect_sections_from_substrings() -> None:
    result = analyze_readme(
        """
This application installs dependencies automatically.

## Fullstack Development
"""
    )

    assert result.has_installation is False
    assert result.has_usage is False
    assert result.has_technologies is False
    assert result.has_requirements is False


def test_analyze_readme_detects_meaningful_intro_description() -> None:
    result = analyze_readme(
        """
# DevLens

DevLens analyzes GitHub repositories using deterministic backend rules.
"""
    )

    assert result.has_description is True


@pytest.mark.parametrize(
    "content",
    [
        """
# DevLens

Short description.
""",
        """
This is a sufficiently long paragraph, but the README has no title.
""",
        """
# DevLens

## Installation

This installation paragraph is long enough but is not a project description.
""",
    ],
)
def test_analyze_readme_rejects_non_description_content(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_description is False


@pytest.mark.parametrize(
    "content",
    [
        "![Dashboard](docs/dashboard.png)",
        '<img src="docs/dashboard.png" alt="Dashboard" />',
    ],
)
def test_analyze_readme_detects_image_references(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_images is True


def test_analyze_readme_does_not_treat_normal_link_as_image() -> None:
    result = analyze_readme("[Dashboard screenshot](docs/dashboard.png)")

    assert result.has_images is False


@pytest.mark.parametrize(
    "content",
    [
        "[Live Demo](https://example.com)",
        "[Website](https://example.com)",
        "Try it at https://devlens.vercel.app",
        "[Open application](https://devlens.netlify.app)",
    ],
)
def test_analyze_readme_detects_demo_links(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_demo_link is True


@pytest.mark.parametrize(
    "content",
    [
        "[Source code](https://github.com/octocat/devlens)",
        "Documentation: https://docs.python.org/3/",
        "![Demo screenshot](https://devlens.vercel.app/screenshot.png)",
    ],
)
def test_analyze_readme_rejects_non_demo_links(
    content: str,
) -> None:
    result = analyze_readme(content)

    assert result.has_demo_link is False


def test_is_deployment_url_ignores_malformed_url() -> None:
    assert _is_deployment_url("http://localhost:3000]") is False


def test_analyze_readme_handles_real_world_markdown_url_shape() -> None:
    result = analyze_readme("Open [http://localhost:3000](http://localhost:3000).")

    assert result.has_demo_link is False
    assert result.exists is True
    assert result.content_length > 0


def test_is_deployment_url_preserves_valid_ipv6_url_parsing() -> None:
    assert _is_deployment_url("http://[::1]:8000") is False


def test_analyze_readme_detects_all_supported_signals() -> None:
    content = """
# DevLens

DevLens analyzes GitHub repositories and produces deterministic engineering evidence.

![DevLens dashboard](docs/dashboard.png)

## Installation

Install the backend dependencies.

## Usage

Run the application locally.

## Tech Stack

Python, FastAPI and Next.js.

## Requirements

Python 3.12 or newer.

[Live Demo](https://devlens.vercel.app)
"""

    result = analyze_readme(content)

    assert result == ReadmeAnalysis(
        exists=True,
        content_length=len(content.strip()),
        has_title=True,
        has_description=True,
        has_installation=True,
        has_usage=True,
        has_technologies=True,
        has_requirements=True,
        has_images=True,
        has_demo_link=True,
    )
