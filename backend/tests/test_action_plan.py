from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.action_plan import require_workspace_origin
from app.config import Settings
from app.schemas.action_plan import ActionPlanStatus, ActionPlanTaskCreate, ActionPlanTaskUpdate


def request_with_settings(settings: Settings) -> Request:
    request = Request({"type": "http", "method": "POST", "path": "/"})
    request.scope["app"] = type("App", (), {"state": type("State", (), {"settings": settings})()})()
    return request


def test_action_plan_input_trims_text_and_forbids_client_ownership() -> None:
    task = ActionPlanTaskCreate(title="  Improve README  ", description="  Add usage  ")
    assert task.title == "Improve README"
    assert task.description == "Add usage"
    with pytest.raises(ValueError):
        ActionPlanTaskCreate(title="Task", user_id=uuid4())


def test_action_plan_update_has_strict_status_vocabulary() -> None:
    assert ActionPlanTaskUpdate(status=ActionPlanStatus.DONE).status == ActionPlanStatus.DONE
    with pytest.raises(ValueError):
        ActionPlanTaskUpdate(status="blocked")


def test_action_plan_mutations_require_exact_origin_and_json() -> None:
    settings = Settings(_env_file=None, frontend_origin="https://devlens.example", cors_allowed_origins="https://devlens.example")
    request = request_with_settings(settings)
    require_workspace_origin(request, "https://devlens.example", "application/json")
    with pytest.raises(HTTPException) as invalid_origin:
        require_workspace_origin(request, "https://evil.example", "application/json")
    assert invalid_origin.value.status_code == 403
    with pytest.raises(HTTPException) as missing_origin:
        require_workspace_origin(request, None, "application/json")
    assert missing_origin.value.status_code == 403
    with pytest.raises(HTTPException) as wrong_content_type:
        require_workspace_origin(request, "https://devlens.example", "application/x-www-form-urlencoded")
    assert wrong_content_type.value.status_code == 415
