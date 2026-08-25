import asyncio
import json
import logging
from uuid import UUID

import httpx

from app.main import app
from app.observability import JsonFormatter, emit_event


def test_health_requests_receive_distinct_server_generated_request_ids(
    caplog,
) -> None:
    async def run() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get("/health"), await client.get("/health")

    first, second = asyncio.run(run())
    first_id = first.headers["x-request-id"]
    second_id = second.headers["x-request-id"]

    UUID(first_id)
    UUID(second_id)
    assert first_id != second_id
    assert first.json() == {"status": "ok"}

    events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "request.completed"
        and getattr(record, "request_id", None) in {first_id, second_id}
    ]
    assert len(events) == 2
    assert {record.method for record in events} == {"GET"}
    assert {record.route for record in events} == {"/health"}
    assert {record.status_code for record in events} == {200}
    assert all(isinstance(record.duration_ms, int) and record.duration_ms >= 0 for record in events)


def test_structured_formatter_allowlists_fields_and_excludes_payloads() -> None:
    logger = logging.getLogger("app.observability.test")
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        1,
        "safe event",
        (),
        None,
        extra={
            "event": "test.event",
            "request_id": "00000000-0000-0000-0000-000000000001",
            "duration_ms": 12,
            "GEMINI_API_KEY": "TEST_GEMINI_SECRET_SHOULD_NOT_APPEAR",
            "body": "TEST_RAW_PAYLOAD_SHOULD_NOT_APPEAR",
        },
    )

    parsed = json.loads(JsonFormatter().format(record))

    assert parsed["event"] == "test.event"
    assert parsed["request_id"] == "00000000-0000-0000-0000-000000000001"
    assert parsed["duration_ms"] == 12
    serialized = json.dumps(parsed)
    assert "TEST_GEMINI_SECRET_SHOULD_NOT_APPEAR" not in serialized
    assert "TEST_RAW_PAYLOAD_SHOULD_NOT_APPEAR" not in serialized


def test_emit_event_uses_request_context_without_logging_arbitrary_fields(caplog) -> None:
    logger = logging.getLogger("app.observability.test")

    emit_event(
        logger,
        "test.safe",
        request_id="00000000-0000-0000-0000-000000000002",
        operation="health",
        forbidden_payload="TEST_PAYLOAD_SHOULD_NOT_APPEAR",
    )

    record = next(record for record in caplog.records if record.getMessage() == "test.safe")
    assert record.request_id == "00000000-0000-0000-0000-000000000002"
    assert not hasattr(record, "forbidden_payload")
    assert "TEST_PAYLOAD_SHOULD_NOT_APPEAR" not in caplog.text
