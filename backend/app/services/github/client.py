from typing import cast

import httpx

from app.config import Settings

DEFAULT_TIMEOUT_SECONDS = 10.0
GITHUB_API_VERSION = "2026-03-10"


class GitHubClient:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base_url = settings.github_api_base_url.rstrip("/")
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevLens/0.1.0",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        self._transport = transport

        if settings.github_token:
            self._headers["Authorization"] = f"Bearer {settings.github_token}"

    async def get_user(self, username: str) -> dict[str, object]:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS),
            transport=self._transport,
        ) as client:
            response = await client.get(f"users/{username}")
            response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("GitHub user response must be a JSON object.")

        return cast(dict[str, object], payload)
