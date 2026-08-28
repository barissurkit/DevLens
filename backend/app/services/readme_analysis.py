import re
from urllib.parse import urlparse

from app.schemas.analysis import ReadmeAnalysis

MARKDOWN_HEADING_PATTERN = re.compile(
    r"^ {0,3}(?P<markers>#{1,6})[ \t]+(?P<text>.+?)[ \t]*$",
    re.MULTILINE,
)

INSTALLATION_SECTION_HEADINGS: frozenset[str] = frozenset(
    {
        "installation",
        "install",
        "setup",
        "getting started",
        "kurulum",
    }
)

USAGE_SECTION_HEADINGS: frozenset[str] = frozenset(
    {
        "usage",
        "how to use",
        "examples",
        "example",
        "kullanım",
    }
)

TECHNOLOGIES_SECTION_HEADINGS: frozenset[str] = frozenset(
    {
        "technologies",
        "technology",
        "tech stack",
        "stack",
        "built with",
        "teknolojiler",
    }
)

REQUIREMENTS_SECTION_HEADINGS: frozenset[str] = frozenset(
    {
        "requirements",
        "prerequisites",
        "dependencies",
        "gereksinimler",
    }
)

MIN_DESCRIPTION_LENGTH = 40

NON_PROSE_PARAGRAPH_PREFIXES: tuple[str, ...] = (
    "![",
    "[![",
    "```",
    "~~~",
    "- ",
    "* ",
    "+ ",
    ">",
    "|",
)

MARKDOWN_IMAGE_PATTERN = re.compile(
    r"!\[[^\]\n]*\]\("
    r"\s*[^)\s]+"
    r"(?:[ \t]+[\"'][^\"'\n]*[\"'])?"
    r"\s*\)"
)

HTML_IMAGE_PATTERN = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*"
    r"(?:\"[^\"]+\"|'[^']+'|[^\s>]+)"
    r"[^>]*>",
    re.IGNORECASE,
)

DEMO_LINK_TEXT_KEYWORDS: frozenset[str] = frozenset(
    {
        "demo",
        "live",
        "deployment",
        "website",
    }
)

DEPLOYMENT_HOST_SUFFIXES: tuple[str, ...] = (
    "vercel.app",
    "netlify.app",
    "github.io",
    "render.com",
    "railway.app",
)

MARKDOWN_LINK_PATTERN = re.compile(
    r"(?<!!)\[(?!\!)(?P<text>[^\]\n]+)\]\("
    r"\s*(?P<url>https?://[^\s)]+)"
    r"(?:[ \t]+[\"'][^\"'\n]*[\"'])?"
    r"\s*\)",
    re.IGNORECASE,
)

HTTP_URL_PATTERN = re.compile(
    r"https?://[^\s<>()]+",
    re.IGNORECASE,
)


def _is_deployment_url(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname
    except ValueError:
        return False

    if hostname is None:
        return False

    normalized_hostname = hostname.casefold().rstrip(".")

    return any(
        normalized_hostname == suffix or normalized_hostname.endswith(f".{suffix}")
        for suffix in DEPLOYMENT_HOST_SUFFIXES
    )


def _link_text_has_demo_keyword(link_text: str) -> bool:
    words = set(re.findall(r"\w+", link_text.casefold()))

    return bool(words & DEMO_LINK_TEXT_KEYWORDS)


def _has_demo_link(content: str) -> bool:
    content_without_images = MARKDOWN_IMAGE_PATTERN.sub(
        "",
        content,
    )
    content_without_images = HTML_IMAGE_PATTERN.sub(
        "",
        content_without_images,
    )

    for match in MARKDOWN_LINK_PATTERN.finditer(content_without_images):
        if _link_text_has_demo_keyword(match.group("text")):
            return True

    return any(
        _is_deployment_url(match.group(0))
        for match in HTTP_URL_PATTERN.finditer(content_without_images)
    )


def _has_image_reference(content: str) -> bool:
    return (
        MARKDOWN_IMAGE_PATTERN.search(content) is not None
        or HTML_IMAGE_PATTERN.search(content) is not None
    )


def _normalize_heading_text(heading_text: str) -> str:
    return " ".join(heading_text.casefold().split())


def _normalize_readme_content(content: str) -> str:
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_content.split("\n")

    start = 0
    end = len(lines)

    while start < end and not lines[start].strip():
        start += 1

    while end > start and not lines[end - 1].strip():
        end -= 1

    return "\n".join(lines[start:end])


def _extract_markdown_headings(
    content: str,
) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []

    for match in MARKDOWN_HEADING_PATTERN.finditer(content):
        markers = match.group("markers")
        heading_text = re.sub(
            r"[ \t]+#+[ \t]*$",
            "",
            match.group("text"),
        ).strip()

        if heading_text:
            headings.append((len(markers), heading_text))

    return headings


def _extract_readme_intro(content: str) -> str:
    title_found = False
    intro_lines: list[str] = []

    for line in content.splitlines():
        heading_match = MARKDOWN_HEADING_PATTERN.fullmatch(line)

        if heading_match is not None:
            level = len(heading_match.group("markers"))

            if not title_found:
                if level == 1:
                    title_found = True

                continue

            break

        if title_found:
            intro_lines.append(line)

    return "\n".join(intro_lines)


def _has_meaningful_description(content: str) -> bool:
    intro = _extract_readme_intro(content)
    paragraphs = re.split(r"\n[ \t]*\n+", intro)

    for paragraph in paragraphs:
        paragraph_text = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())

        if len(paragraph_text) < MIN_DESCRIPTION_LENGTH:
            continue

        normalized_paragraph = paragraph_text.casefold()

        if paragraph_text.startswith(NON_PROSE_PARAGRAPH_PREFIXES):
            continue

        if normalized_paragraph.startswith("<img"):
            continue

        return True

    return False


def analyze_readme(content: str | None) -> ReadmeAnalysis:
    exists = content is not None
    normalized_content = "" if content is None else _normalize_readme_content(content)

    content_length = len(normalized_content.strip())

    headings = _extract_markdown_headings(normalized_content)
    normalized_heading_texts = {
        _normalize_heading_text(heading_text) for _, heading_text in headings
    }

    has_installation = bool(normalized_heading_texts & INSTALLATION_SECTION_HEADINGS)
    has_usage = bool(normalized_heading_texts & USAGE_SECTION_HEADINGS)
    has_technologies = bool(normalized_heading_texts & TECHNOLOGIES_SECTION_HEADINGS)
    has_requirements = bool(normalized_heading_texts & REQUIREMENTS_SECTION_HEADINGS)
    has_title = any(level == 1 for level, _ in headings)
    has_description = _has_meaningful_description(normalized_content)
    has_images = _has_image_reference(normalized_content)
    has_demo_link = _has_demo_link(normalized_content)

    return ReadmeAnalysis(
        exists=exists,
        content_length=content_length,
        has_title=has_title,
        has_description=has_description,
        has_installation=has_installation,
        has_usage=has_usage,
        has_technologies=has_technologies,
        has_requirements=has_requirements,
        has_images=has_images,
        has_demo_link=has_demo_link,
    )
