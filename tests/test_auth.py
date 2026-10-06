import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def api_key(monkeypatch):
    """Configure a key for the duration of a test."""
    monkeypatch.setattr(
        "app.security.get_settings", lambda: Settings(api_key="s3cret")
    )
    return "s3cret"


def test_health_is_public_even_when_key_is_configured(api_key):
    assert client.get("/health").status_code == 200


def test_protected_route_rejects_missing_key(api_key):
    response = client.get("/events/")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "ApiKey"


def test_protected_route_rejects_wrong_key(api_key):
    response = client.get("/events/", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_protected_route_accepts_correct_key(api_key):
    response = client.get("/events/", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    assert "events" in response.json()


def test_risk_route_is_also_protected(api_key):
    response = client.post("/risk/score", json={"address": "GABC"})
    assert response.status_code == 401


def test_auth_disabled_when_no_key_configured(monkeypatch):
    monkeypatch.setattr("app.security.get_settings",
                        lambda: Settings(api_key=""))
    assert client.get("/events/").status_code == 200
