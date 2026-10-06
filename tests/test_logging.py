import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_middleware import RequestLoggingMiddleware
from app.main import app

client = TestClient(app)


def access_records(caplog):
    return [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "sorowatch.access"
    ]


def test_request_is_logged_as_json(caplog):
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        response = client.get("/health")
    assert response.status_code == 200

    (record,) = access_records(caplog)
    assert record["event"] == "request"
    assert record["method"] == "GET"
    assert record["path"] == "/health"
    assert record["status"] == 200
    assert record["duration_ms"] >= 0
    assert record["request_id"]


def test_generates_request_id_and_returns_it(caplog):
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        response = client.get("/health")
    (record,) = access_records(caplog)
    assert response.headers["X-Request-ID"] == record["request_id"]


def test_reuses_incoming_request_id(caplog):
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        response = client.get(
            "/health", headers={"X-Request-ID": "trace-abc-123"})
    (record,) = access_records(caplog)
    assert record["request_id"] == "trace-abc-123"
    assert response.headers["X-Request-ID"] == "trace-abc-123"


def test_secrets_and_query_strings_are_not_logged(caplog):
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        client.get("/health?token=hunter2",
                   headers={"X-API-Key": "super-secret"})
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "super-secret" not in text
    assert "hunter2" not in text


def test_unauthorized_responses_are_logged_with_status(caplog, monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        "app.security.get_settings", lambda: Settings(api_key="s3cret")
    )
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        client.get("/events/")
    (record,) = access_records(caplog)
    assert record["status"] == 401
    assert record["path"] == "/events/"


def test_unhandled_errors_are_logged_as_500(caplog):
    broken = FastAPI()
    broken.add_middleware(RequestLoggingMiddleware)

    @broken.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    broken_client = TestClient(broken, raise_server_exceptions=False)
    with caplog.at_level(logging.INFO, logger="sorowatch.access"):
        response = broken_client.get("/boom")
    assert response.status_code == 500
    (record,) = access_records(caplog)
    assert record["status"] == 500
    assert record["path"] == "/boom"
