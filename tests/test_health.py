import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import Settings
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture
def agent_url(monkeypatch):
    monkeypatch.setattr(
        "app.routers.health.get_settings",
        lambda: Settings(ai_agent_url="http://agent.test"),
    )
    return "http://agent.test"


@respx.mock
def test_ready_ok_when_agent_healthy(agent_url):
    respx.get(f"{agent_url}/health").mock(
        return_value=Response(200, json={"status": "ok"})
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"ai_agent": "ok"}}


@respx.mock
def test_ready_503_when_agent_unreachable(agent_url):
    respx.get(f"{agent_url}/health").mock(side_effect=httpx.ConnectError("down"))
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"ai_agent": "unreachable"},
    }


@respx.mock
def test_ready_503_when_agent_returns_error(agent_url):
    respx.get(f"{agent_url}/health").mock(return_value=Response(500))
    assert client.get("/health/ready").status_code == 503


@respx.mock
def test_ready_503_when_agent_times_out(agent_url):
    respx.get(f"{agent_url}/health").mock(side_effect=httpx.ReadTimeout("slow"))
    assert client.get("/health/ready").status_code == 503


@respx.mock
def test_ready_is_public_when_api_key_configured(agent_url, monkeypatch):
    monkeypatch.setattr(
        "app.security.get_settings", lambda: Settings(api_key="s3cret")
    )
    respx.get(f"{agent_url}/health").mock(return_value=Response(200))
    assert client.get("/health/ready").status_code == 200
