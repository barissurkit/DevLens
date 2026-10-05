"""Merged pull requests a person made to other people's public repositories.

This is evidence the portfolio score deliberately does not use (the score only looks at the person's own
repositories), so it is a separate, read-only view. GitHub's search API allows few requests per minute, so
results are kept in a small in-process cache for the analysis cache lifetime.
"""

import time
from datetime import UTC, datetime
from typing import Any

from app.schemas.open_source import OpenSourceContribution, OpenSourceContributions
from app.services.github.client import GitHubClient, GitHubRequestBudget, use_github_request_budget

MAX_CONTRIBUTIONS = 20
# Only this many repositories are looked up for their star count; the rest is listed without it.
MAX_STAR_LOOKUPS = 12
MAX_CACHE_ENTRIES = 500

_cache: dict[str, tuple[float, OpenSourceContributions]] = {}


def clear_cache() -> None:
    _cache.clear()


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _repository_name(item: dict[str, Any]) -> str | None:
    """``owner/name`` from the API address of the repository the pull request was made to."""

    url = item.get("repository_url")
    marker = "/repos/"
    if not isinstance(url, str) or marker not in url:
        return None
    name = url.split(marker, 1)[1].strip("/")
    return name if name.count("/") == 1 else None


def group_pull_requests(username: str, items: list[dict[str, Any]]) -> list[OpenSourceContribution]:
    """One entry per repository, with the number of merged pull requests and the latest one."""

    groups: dict[str, list[tuple[dict[str, Any], datetime | None]]] = {}
    for item in items:
        name = _repository_name(item)
        title, url = item.get("title"), item.get("html_url")
        if name is None or not isinstance(title, str) or not isinstance(url, str):
            continue
        if name.split("/", 1)[0].lower() == username.lower():
            continue  # a repository of their own is not an outside contribution
        pull_request = item.get("pull_request") if isinstance(item.get("pull_request"), dict) else {}
        merged_at = _parse_time(pull_request.get("merged_at") or item.get("closed_at"))
        groups.setdefault(name, []).append((item, merged_at))

    contributions: list[OpenSourceContribution] = []
    for name, entries in groups.items():
        latest, merged_at = max(entries, key=lambda entry: entry[1] or datetime.min.replace(tzinfo=UTC))
        contributions.append(
            OpenSourceContribution(
                repository=name,
                html_url=f"https://github.com/{name}",
                merged_count=len(entries),
                latest_title=latest["title"][:300],
                latest_url=latest["html_url"],
                latest_merged_at=merged_at,
            )
        )
    return contributions


async def get_open_source_contributions(
    username: str,
    client: GitHubClient,
    *,
    ttl_seconds: int,
) -> OpenSourceContributions:
    key = username.lower()
    cached = _cache.get(key)
    if cached is not None and ttl_seconds > 0 and time.monotonic() - cached[0] < ttl_seconds:
        return cached[1]

    with use_github_request_budget(GitHubRequestBudget()):
        items, truncated = await client.search_merged_pull_requests(username)
        contributions = group_pull_requests(username, items)
        # Look up stars for the repositories with the most merged pull requests first.
        by_activity = sorted(contributions, key=lambda item: (-item.merged_count, item.repository))
        stars = await client.get_star_counts([item.repository for item in by_activity[:MAX_STAR_LOOKUPS]]) if by_activity else {}

    enriched = [item.model_copy(update={"stars": stars.get(item.repository)}) for item in contributions]
    enriched.sort(key=lambda item: (item.stars is None, -(item.stars or 0), -item.merged_count, item.repository))
    result = OpenSourceContributions(
        username=username,
        total_merged=sum(item.merged_count for item in enriched),
        repository_count=len(enriched),
        contributions=enriched[:MAX_CONTRIBUTIONS],
        is_truncated=truncated,
    )

    if ttl_seconds > 0:
        if len(_cache) >= MAX_CACHE_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), result)
    return result
