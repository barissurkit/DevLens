import logging

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_a_report_is_logged_without_query_string_and_returns_204(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.api.client_errors"):
        response = client().post(
            "/api/v1/client-errors",
            json={"kind": "script", "message": "boom\nsecond line", "stack": "a\n  b", "path": "/u/octocat?token=secret#frag"},
        )

    assert response.status_code == 204
    record = next(item for item in caplog.records if getattr(item, "event", None) == "client.error")
    assert record.client_error_kind == "script"
    assert record.client_error_message == "boom second line"
    assert record.client_error_stack == "a b"
    assert record.client_error_path == "/u/octocat"
    assert "secret" not in str(record.__dict__)


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "script"},
        {"kind": "other", "message": "x"},
        {"kind": "script", "message": "x" * 501},
        {"kind": "script", "message": "x", "extra": 1},
        {"kind": "script", "message": "x", "stack": "s" * 2001},
    ],
)
def test_malformed_or_oversized_reports_are_rejected(payload: dict) -> None:
    assert client().post("/api/v1/client-errors", json=payload).status_code == 422


def test_reports_are_rate_limited_per_client() -> None:
    api = client()
    body = {"kind": "render", "message": "x"}

    codes = [api.post("/api/v1/client-errors", json=body).status_code for _ in range(7)]

    assert codes[:5] == [204] * 5
    assert codes[5] == 429
