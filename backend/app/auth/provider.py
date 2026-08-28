from typing import Any

import httpx

from app.config import Settings


class GitHubAuthError(RuntimeError):
    """Raised for a failed GitHub authorization-code exchange."""


class GitHubAuthClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.github_app_client_id or not settings.github_app_client_secret:
            raise GitHubAuthError("GitHub App credentials are not configured.")
        self._settings = settings
        self._transport = transport

    async def exchange_code(self, *, code: str, redirect_uri: str, code_verifier: str) -> str:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0), transport=self._transport
        ) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self._settings.github_app_client_id,
                    "client_secret": self._settings.github_app_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                headers={"Accept": "application/json"},
            )
        if response.status_code >= 400:
            raise GitHubAuthError("GitHub token exchange failed.")
        payload: Any = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
            raise GitHubAuthError("GitHub token exchange returned an invalid response.")
        if payload.get("error"):
            raise GitHubAuthError("GitHub authorization was not accepted.")
        return payload["access_token"]
