"""A README badge that shows a developer's latest DevLens portfolio score.

The badge is served from stored analysis snapshots only: it never calls GitHub or the AI provider, so
embedding it in a README cannot consume analysis capacity. It is deliberately not rate limited per IP,
because GitHub proxies README images through a handful of shared addresses.
"""

import re
import time
from datetime import timedelta
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Response

from app.api.github import get_analysis_snapshot_cache_service
from app.db.normalization import GITHUB_USERNAME_MAX_LENGTH, normalize_github_username
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService

router = APIRouter(prefix="/api/v1/badge", tags=["Badge"])

BADGE_MAX_AGE = timedelta(days=60)
BADGE_CACHE_SECONDS = 600
_LOGIN = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,38}$")

GREEN, AMBER, ROSE, GREY = "#047857", "#b45309", "#be123c", "#64748b"

_memo: dict[str, tuple[float, str]] = {}
_MEMO_LIMIT = 2048


def badge_color(score: int) -> str:
    if score >= 75:
        return GREEN
    if score >= 50:
        return AMBER
    return ROSE


def render_badge(value: str, color: str, label: str = "DevLens") -> str:
    """A flat two-part badge. Widths are estimated from the text length; all text is escaped."""
    label_width = 14 + 6 * len(label)
    value_width = 14 + 6.4 * len(value)
    total = label_width + value_width
    label, value_text = escape(label), escape(value)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.0f}" height="20" role="img" '
        f'aria-label="{label}: {value_text}">'
        f"<title>{label}: {value_text}</title>"
        f'<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".12"/>'
        f'<stop offset="1" stop-opacity=".12"/></linearGradient>'
        f'<clipPath id="r"><rect width="{total:.0f}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{label_width:.0f}" height="20" fill="#334155"/>'
        f'<rect x="{label_width:.0f}" width="{value_width:.0f}" height="20" fill="{color}"/>'
        f'<rect width="{total:.0f}" height="20" fill="url(#s)"/></g>'
        f'<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{label_width / 2:.1f}" y="14">{label}</text>'
        f'<text x="{label_width + value_width / 2:.1f}" y="14">{value_text}</text></g></svg>'
    )


@router.get("/{username}.svg", include_in_schema=True)
async def get_score_badge(
    username: str,
    cache: AnalysisSnapshotCacheService = Depends(get_analysis_snapshot_cache_service),
) -> Response:
    try:
        login = normalize_github_username(username)
    except ValueError:
        login = ""
    headers = {
        "Content-Type": "image/svg+xml; charset=utf-8",
        "Cache-Control": f"public, max-age={BADGE_CACHE_SECONDS}",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    }
    if not login or len(login) > GITHUB_USERNAME_MAX_LENGTH or not _LOGIN.match(login):
        return Response(render_badge("geçersiz kullanıcı", GREY), status_code=404, headers=headers)

    now = time.monotonic()
    memoized = _memo.get(login)
    if memoized is not None and memoized[0] > now:
        return Response(memoized[1], headers=headers)

    cached = await cache.get_fresh_analysis(username=login, request_kind="badge", max_age=BADGE_MAX_AGE)
    score = cached.analysis.score.overall_score if cached is not None and cached.analysis.score.is_available else None
    svg = render_badge(f"{score}/100", badge_color(score)) if score is not None else render_badge("analiz et", GREY)
    if len(_memo) >= _MEMO_LIMIT:
        _memo.clear()
    _memo[login] = (now + BADGE_CACHE_SECONDS / 2, svg)
    return Response(svg, headers=headers)
