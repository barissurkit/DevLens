import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock

import httpx
from starlette.requests import Request

from app.main import create_app
from app.main import app
from app.api.github import get_github_client
from app.rate_limit import RateLimiter, anonymous_principal, principal_for
from app.schemas.github import GitHubUser


@dataclass
class FakeClock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


def run(coro):
    return asyncio.run(coro)


def test_token_bucket_capacity_refill_and_retry_after() -> None:
    clock = FakeClock()
    limiter = RateLimiter(clock=clock)

    assert run(_acquire_many(limiter, "portfolio_analysis", "anon:a", 3)) == [None] * 3
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) == 60
    clock.value = 30
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) == 30
    clock.value = 60
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None


def test_full_refill_is_pruned_without_changing_fresh_semantics() -> None:
    clock = FakeClock()
    limiter = RateLimiter(clock=clock, max_states=1)
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None
    clock.value = 60
    assert run(limiter.acquire("portfolio_analysis", "anon:b")) is None
    assert limiter.state_count == 1


def test_active_state_is_retained_and_unseen_key_fails_closed() -> None:
    clock = FakeClock()
    limiter = RateLimiter(clock=clock, max_states=1)
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None
    assert run(limiter.acquire("portfolio_analysis", "anon:b")) == 180
    assert limiter.state_count == 1
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) == 60


def test_concurrent_boundary_is_atomic() -> None:
    limiter = RateLimiter(clock=lambda: 0.0)
    results = run(_concurrent_acquisitions(limiter))
    assert results.count(None) == 3
    assert results.count(60) == 1


def test_principals_normalize_ip_and_ignore_forwarded_header() -> None:
    request = Request({"type": "http", "client": ("2001:0db8:0:0:0:0:0:1", 1234), "headers": [(b"x-forwarded-for", b"203.0.113.9")]})
    assert anonymous_principal(request) == "anon:2001:db8::1"
    assert principal_for(request)[0] == "anon:2001:db8::1"


def test_create_app_has_independent_limiter_instances() -> None:
    first = create_app()
    second = create_app()
    assert first.state.rate_limiter is not second.state.rate_limiter


def test_github_lookup_returns_structured_429_before_provider_call() -> None:
    client = AsyncMock()
    client.get_user.return_value = GitHubUser.model_validate(
        {
            "id": 1,
            "login": "octocat",
            "name": None,
            "avatar_url": "https://avatars.example/octocat.png",
            "bio": None,
            "public_repos": 0,
            "followers": 0,
            "following": 0,
            "html_url": "https://github.com/octocat",
            "created_at": "2025-01-01T00:00:00Z",
        }
    )

    async def override() -> AsyncMock:
        return client

    app.dependency_overrides[get_github_client] = override
    try:
        response = run(_lookup_requests())
    finally:
        app.dependency_overrides.clear()

    assert [item.status_code for item in response] == [200] * 5 + [429]
    assert response[-1].json() == {
        "detail": {
            "code": "rate_limited",
            "message": "Çok fazla istek gönderildi. Lütfen daha sonra tekrar deneyin.",
        }
    }
    assert response[-1].headers["Retry-After"].isdigit()
    assert client.get_user.await_count == 5


async def _acquire_many(limiter: RateLimiter, bucket: str, principal: str, count: int) -> list[int | None]:
    return [await limiter.acquire(bucket, principal) for _ in range(count)]


async def _concurrent_acquisitions(limiter: RateLimiter) -> list[int | None]:
    return await asyncio.gather(
        *(limiter.acquire("portfolio_analysis", "anon:a") for _ in range(4))
    )


async def _lookup_requests() -> list[httpx.Response]:
    transport = httpx.ASGITransport(app=app, client=("192.0.2.10", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return [
            await client.get("/api/v1/github/users/octocat")
            for _ in range(6)
        ]
