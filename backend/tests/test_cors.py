import asyncio

import httpx
from fastapi import FastAPI
from httpx import ASGITransport

from app.config import Settings
from app.main import create_app


def test_allowed_origin_receives_exact_cors_headers() -> None:
    application = create_app(
        Settings(_env_file=None, cors_allowed_origins="https://frontend.example")
    )

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=application), base_url="http://test"
        ) as client:
            return await client.options(
                "/health",
                headers={
                    "Origin": "https://frontend.example",
                    "Access-Control-Request-Method": "GET",
                },
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"


def test_untrusted_origin_does_not_receive_allow_origin() -> None:
    application = create_app(
        Settings(_env_file=None, cors_allowed_origins="https://frontend.example")
    )

    cors_middleware = next(
        middleware
        for middleware in application.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert "https://untrusted.example" not in cors_middleware.kwargs["allow_origins"]


def test_cors_app_factory_returns_fastapi_application() -> None:
    assert isinstance(create_app(Settings(_env_file=None)), FastAPI)
