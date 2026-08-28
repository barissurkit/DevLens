import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock

import httpx
import pytest
from app.api.github import get_github_client
from app.main import app
from app.schemas.github import GitHubUser
from app.services.github.client import GitHubClient


def create_github_user() -> GitHubUser:
    return GitHubUser.model_validate(
        {
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
            "bio": None,
            "public_repos": 8,
            "followers": 10000,
            "following": 9,
            "html_url": "https://github.com/octocat",
            "created_at": "2011-01-25T18:44:36Z",
        }
    )


def request_app(path: str) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(path)

    return asyncio.run(send_request())


def use_mock_client(mock_client: AsyncMock) -> None:
    async def override_github_client() -> AsyncMock:
        return mock_client

    app.dependency_overrides[get_github_client] = override_github_client


# bu fixture her testten sonra FastAPI dependency override'larını temizler.
@pytest.fixture(
    autouse=True  # autouse=True ile test fonksiyonuna parametre olarak yazılmasa bile her testte otomatik çalıştırır.
)
def clear_dependency_overrides() -> Iterator[None]:
    yield  # testin çalışmasına izin verir.
    app.dependency_overrides.clear()  # test bittikten sonra bütün dependency override kayıtlarını siler


"""
Fixture başlar
    → yield
    → test çalışır
    → test tamamlanır
    → app.dependency_overrides.clear()
"""


def create_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request(
        "GET",
        "https://api.github.com/users/octocat",
    )
    response = httpx.Response(status_code, request=request)

    return httpx.HTTPStatusError(
        "GitHub request failed.",
        request=request,
        response=response,
    )


def test_get_github_user_returns_serialized_user() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_user.return_value = create_github_user()
    use_mock_client(mock_client)

    response = request_app("/api/v1/github/users/octocat")

    assert response.status_code == 200

    payload = response.json()

    assert payload["username"] == "octocat"
    assert isinstance(payload["created_at"], str)
    assert payload["created_at"].startswith("2011-01-25T18:44:36")
    mock_client.get_user.assert_awaited_once_with("octocat")


def test_get_github_user_returns_404_when_user_does_not_exist() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_user.side_effect = create_status_error(404)
    use_mock_client(mock_client)

    response = request_app("/api/v1/github/users/missing-user")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "github_user_not_found",
            "message": "GitHub kullanıcısı bulunamadı.",
        }
    }


def test_get_github_user_returns_429_for_rate_limit() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_user.side_effect = create_status_error(429)
    use_mock_client(mock_client)

    response = request_app("/api/v1/github/users/octocat")

    assert response.status_code == 429
    assert response.json() == {
        "detail": {
            "code": "github_rate_limit",
            "message": "GitHub istek limiti aşıldı.",
        }
    }


def test_get_github_user_returns_502_for_upstream_error() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_user.side_effect = create_status_error(500)
    use_mock_client(mock_client)

    response = request_app("/api/v1/github/users/octocat")

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "github_upstream_error",
            "message": "GitHub beklenmeyen bir upstream hatası döndürdü.",
        }
    }


def test_get_github_user_returns_503_for_timeout() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    request = httpx.Request(
        "GET",
        "https://api.github.com/users/octocat",
    )
    mock_client.get_user.side_effect = httpx.ReadTimeout(
        "GitHub request timed out.",
        request=request,
    )
    use_mock_client(mock_client)

    response = request_app("/api/v1/github/users/octocat")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "github_timeout",
            "message": "GitHub'a geçici olarak erişilemiyor.",
        }
    }
