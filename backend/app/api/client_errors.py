"""Collects unexpected browser errors into the structured application log.

There is no external error tracker: the report ends up next to the request logs, where it can be read in the
hosting dashboard. Reports are small, rate limited and never stored; free text is cut to fixed lengths.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.observability import emit_event
from app.rate_limit import rate_limit_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/client-errors", tags=["Client Errors"])


class ClientErrorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["render", "script", "promise"]
    message: str = Field(max_length=500)
    stack: str | None = Field(default=None, max_length=2000)
    path: str = Field(default="/", max_length=200)


def _single_line(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


@router.post("", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(rate_limit_dependency("client_errors"))])
async def report_client_error(report: ClientErrorReport) -> Response:
    # Only the path is kept: query strings and fragments can carry personal data.
    path = report.path.split("?", 1)[0].split("#", 1)[0]
    emit_event(
        logger,
        "client.error",
        level=logging.WARNING,
        client_error_kind=report.kind,
        client_error_message=_single_line(report.message, 300),
        client_error_stack=_single_line(report.stack, 1200) if report.stack else None,
        client_error_path=path[:120],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
