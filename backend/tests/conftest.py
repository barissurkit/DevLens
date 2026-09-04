from collections.abc import Iterator

import pytest

from app.main import app
from app.rate_limit import RateLimiter


@pytest.fixture(autouse=True)
def isolate_application_rate_limiter() -> Iterator[None]:
    app.state.rate_limiter = RateLimiter()
    yield
