import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import Settings
from app.main import app
from app.rate_limit import SlidingWindowLimiter, limiter

client = TestClient(app)
AGENT = "http://agent.test"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def clean_limiter():
    limiter.reset()
    yield
    limiter.reset()


def use_settings(monkeypatch, **overrides):
    settings = Settings(ai_agent_url=AGENT, api_key="", **overrides)
    monkeypatch.setattr("app.rate_limit.get_settings", lambda: settings)
    monkeypatch.setattr("app.security.get_settings", lambda: settings)
    monkeypatch.setattr("app.routers.risk.get_settings", lambda: settings)


# --- limiter unit tests ---------------------------------------------------

def test_limiter_allows_up_to_limit_then_blocks():
    lim = SlidingWindowLimiter(clock=FakeClock())
    assert [lim.check("a", 3) for _ in range(3)] == [None, None, None]
    assert lim.check("a", 3) is not None


def test_limiter_reports_time_until_oldest_hit_expires():
    clock = FakeClock()
    lim = SlidingWindowLimiter(clock=clock)
    lim.check("a", 1)
    clock.now += 20
    assert lim.check("a", 1) == pytest.approx(40.0)


def test_limiter_recovers_after_window():
    clock = FakeClock()
    lim = SlidingWindowLimiter(clock=clock)
    for _ in range(2):
        lim.check("a", 2)
    assert lim.check("a", 2) is not None
    clock.now += 61
    assert lim.check("a", 2) is None


def test_limiter_rejected_requests_do_not_extend_the_block():
    clock = FakeClock()
    lim = SlidingWindowLimiter(clock=clock)
    lim.check("a", 1)
    for _ in range(5):
        assert lim.check("a", 1) is not None
    clock.now += 61
    assert lim.check("a", 1) is None


def test_limiter_counts_clients_separately():
    lim = SlidingWindowLimiter(clock=FakeClock())
    lim.check("a", 1)
    assert lim.check("a", 1) is not None
    assert lim.check("b", 1) is None


# --- endpoint tests -------------------------------------------------------

@respx.mock
def test_risk_score_returns_429_with_retry_after_over_limit(monkeypatch):
    use_settings(monkeypatch, risk_rate_limit_per_minute=2)
    respx.post(f"{AGENT}/score").mock(
        return_value=Response(200, json={"address": "G", "score": 10, "flagged": False})
    )
    body = {"address": "GABC"}
    assert client.post("/risk/score", json=body).status_code == 200
    assert client.post("/risk/score", json=body).status_code == 200

    blocked = client.post("/risk/score", json=body)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert respx.calls.call_count == 2  # the blocked call never reached the agent


@respx.mock
def test_rate_limit_disabled_when_zero(monkeypatch):
    use_settings(monkeypatch, risk_rate_limit_per_minute=0)
    respx.post(f"{AGENT}/score").mock(
        return_value=Response(200, json={"address": "G", "score": 1, "flagged": False})
    )
    for _ in range(5):
        assert client.post("/risk/score", json={"address": "GABC"}).status_code == 200


def test_health_is_never_rate_limited(monkeypatch):
    use_settings(monkeypatch, risk_rate_limit_per_minute=1)
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_bad_api_key_does_not_use_up_the_limit(monkeypatch):
    use_settings(monkeypatch, risk_rate_limit_per_minute=1)
    monkeypatch.setattr(
        "app.security.get_settings", lambda: Settings(api_key="s3cret")
    )
    for _ in range(3):
        assert client.post("/risk/score", json={"address": "G"}).status_code == 401
    assert limiter._hits == {}
