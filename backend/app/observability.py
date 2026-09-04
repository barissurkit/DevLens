"""Small, application-local observability primitives for production logs."""

from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

REQUEST_ID: ContextVar[str | None] = ContextVar("devlens_request_id", default=None)

_SAFE_FIELDS = {
    "event",
    "request_id",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "provider",
    "provider_status",
    "operation",
    "upstream_status",
    "attempt",
    "error_category",
    "cache_state",
    "result",
    "model",
    "response_bytes",
    "rate_limit_limit",
    "rate_limit_remaining",
    "rate_limit_reset",
    "rate_limit_resource",
    "rate_limit_used",
    "retry_after_seconds",
    "principal_kind",
}


def current_request_id() -> str | None:
    return REQUEST_ID.get()


def new_request_id() -> str:
    return str(uuid4())


def is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


class JsonFormatter(logging.Formatter):
    """Emit only allowlisted scalar application fields as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _SAFE_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                fields[key] = value
        if "request_id" not in fields:
            request_id = current_request_id()
            if request_id is not None:
                fields["request_id"] = request_id
        if record.exc_info:
            fields["exception"] = record.exc_info[0].__name__
        return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    """Configure the app logger without changing third-party logger settings."""

    app_logger = logging.getLogger("app")
    if getattr(app_logger, "_devlens_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    # Keep propagation enabled so test/runtime log collectors can inspect the
    # same records. Uvicorn does not configure the root logger for `app`.
    app_logger.propagate = True
    app_logger._devlens_configured = True  # type: ignore[attr-defined]


def emit_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    safe_fields = {key: value for key, value in fields.items() if key in _SAFE_FIELDS}
    safe_fields["event"] = event
    safe_fields.setdefault("request_id", current_request_id())
    logger.log(level, event, extra={key: value for key, value in safe_fields.items() if value is not None})


def elapsed_ms(started_at: float) -> int:
    return max(0, round((time.monotonic() - started_at) * 1000))
