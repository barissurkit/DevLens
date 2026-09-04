"""Process-local application rate limiting."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import math
import time
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, status

from app.db.models import User
from app.observability import current_request_id, emit_event

MAX_RATE_LIMIT_STATES = 4096
RATE_LIMIT_MESSAGE = "Çok fazla istek gönderildi. Lütfen daha sonra tekrar deneyin."


@dataclass(frozen=True)
class RateLimitPolicy:
    capacity: float
    refill_per_second: float
    cost: float = 1.0


@dataclass
class TokenBucketState:
    tokens: float
    last_refill: float


POLICIES: dict[str, RateLimitPolicy] = {
    "portfolio_analysis": RateLimitPolicy(3, 1 / 60),
    "ai_suggestions": RateLimitPolicy(2, 1 / 120),
    "auth_login": RateLimitPolicy(3, 1 / 60),
    "github_lookup": RateLimitPolicy(5, 1 / 20),
}


class RateLimiter:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_states: int = MAX_RATE_LIMIT_STATES,
    ) -> None:
        if max_states < 1:
            raise ValueError("max_states must be positive")
        self._clock = clock
        self._max_states = max_states
        self._states: dict[tuple[str, str], TokenBucketState] = {}
        self._lock = asyncio.Lock()

    @property
    def state_count(self) -> int:
        return len(self._states)

    async def acquire(self, bucket: str, principal: str) -> int | None:
        policy = POLICIES[bucket]
        now = self._clock()
        async with self._lock:
            self._prune_full_states(now)
            key = (bucket, principal)
            state = self._states.get(key)
            if state is None:
                if len(self._states) >= self._max_states:
                    return self._full_map_retry_after(now)
                state = TokenBucketState(policy.capacity, now)
                self._states[key] = state
            else:
                self._refill(state, policy, now)

            if state.tokens < policy.cost:
                return self._retry_after(state, policy)
            state.tokens -= policy.cost
            return None

    def _refill(self, state: TokenBucketState, policy: RateLimitPolicy, now: float) -> None:
        elapsed = max(0.0, now - state.last_refill)
        state.tokens = min(policy.capacity, state.tokens + elapsed * policy.refill_per_second)
        state.last_refill = now

    def _prune_full_states(self, now: float) -> None:
        for key, state in list(self._states.items()):
            policy = POLICIES[key[0]]
            self._refill(state, policy, now)
            if state.tokens >= policy.capacity:
                del self._states[key]

    def _retry_after(self, state: TokenBucketState, policy: RateLimitPolicy) -> int:
        return max(1, math.ceil((policy.cost - state.tokens) / policy.refill_per_second))

    def _full_map_retry_after(self, now: float) -> int:
        retry_values = []
        for key, state in self._states.items():
            policy = POLICIES[key[0]]
            retry_values.append(max(1, math.ceil((policy.capacity - state.tokens) / policy.refill_per_second)))
        return min(retry_values, default=1)


def anonymous_principal(request: Request) -> str:
    host = request.client.host if request.client is not None else None
    try:
        canonical_host = ipaddress.ip_address(host or "").compressed
    except ValueError:
        canonical_host = "unknown"
    return f"anon:{canonical_host}"


def principal_for(request: Request, user: User | None = None) -> tuple[str, str]:
    if user is not None:
        return f"user:{user.id}", "authenticated"
    return anonymous_principal(request), "anonymous"


def _rate_limit_error(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "rate_limited", "message": RATE_LIMIT_MESSAGE},
        headers={"Retry-After": str(retry_after)},
    )


async def enforce_rate_limit(
    request: Request,
    bucket: str,
    user: User | None = None,
) -> None:
    principal, principal_kind = principal_for(request, user)
    retry_after = await request.app.state.rate_limiter.acquire(bucket, principal)
    if retry_after is None:
        return
    route = request.scope.get("route")
    route_name = getattr(route, "path", None) or request.url.path
    emit_event(
        logging.getLogger("app.rate_limit"),
        "rate_limit.rejected",
        bucket=bucket,
        route=route_name,
        request_id=current_request_id(),
        retry_after_seconds=retry_after,
        principal_kind=principal_kind,
    )
    raise _rate_limit_error(retry_after)


def rate_limit_dependency(bucket: str):
    async def dependency(request: Request) -> None:
        await enforce_rate_limit(request, bucket)

    return dependency
