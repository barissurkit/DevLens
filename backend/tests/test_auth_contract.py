import base64
import asyncio
from urllib.parse import parse_qs

import httpx

from app.auth.crypto import decrypt_verifier, encrypt_verifier, sha256_digest
from app.auth.provider import GitHubAuthClient
from app.config import Settings


def encryption_key() -> str:
    return base64.urlsafe_b64encode(b"k" * 32).decode("ascii").rstrip("=")


def test_pkce_verifier_is_authenticated_encrypted_and_round_trips() -> None:
    key = b"k" * 32
    nonce, ciphertext = encrypt_verifier("verifier-value", key)

    assert nonce != b"verifier-value"[:12]
    assert b"verifier-value" not in ciphertext
    assert decrypt_verifier(ciphertext, nonce, key) == "verifier-value"


def test_pkce_decryption_rejects_wrong_key() -> None:
    key = b"k" * 32
    nonce, ciphertext = encrypt_verifier("verifier-value", key)

    try:
        decrypt_verifier(ciphertext, nonce, b"x" * 32)
    except ValueError:
        pass
    else:
        raise AssertionError("wrong encryption key must reject ciphertext")


def test_session_hash_is_fixed_length_digest() -> None:
    assert len(sha256_digest("opaque-session-token")) == 32


def test_github_auth_client_exchanges_code_without_returning_provider_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["data"] = parse_qs(request.content.decode())
        return httpx.Response(200, json={"access_token": "temporary-token"})

    settings = Settings(
        _env_file=None,
        github_app_client_id="client-id",
        github_app_client_secret="client-secret",
        github_app_callback_url="https://api.example/api/v1/auth/github/callback",
        auth_state_encryption_key=encryption_key(),
    )
    token = asyncio.run(
        GitHubAuthClient(settings, transport=httpx.MockTransport(handler)).exchange_code(
            code="authorization-code",
            redirect_uri="https://api.example/auth/callback",
            code_verifier="verifier",
        )
    )

    assert token == "temporary-token"
    assert "temporary-token" not in str(captured["data"])
