from app.main import app, health_check


def test_health_check() -> None:
    response = health_check()

    assert response.model_dump() == {"status": "ok"}


def test_only_health_endpoint_is_registered() -> None:
    assert set(app.openapi()["paths"]) == {"/health"}
