import json
import logging

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.observability import JsonFormatter
from app.db import get_session
from app.main import app
from tests.test_api import pilot

__all__ = ["pilot"]


def test_metrics_count_requests_by_route_template(client, pilot):
    client.get(f"/api/v1/projects/{pilot['project']}/graph")
    client.get("/api/v1/projects/999/graph")
    body = client.get("/metrics").text
    assert 'route="/api/v1/projects/{project_id}/graph",status="200"' in body
    assert 'route="/api/v1/projects/{project_id}/graph",status="404"' in body
    assert "pult_http_request_duration_seconds_bucket" in body
    assert 'route="/metrics"' not in body


def test_request_id_is_echoed_or_generated(client, pilot):
    assert client.get("/api/health", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
    assert len(client.get("/api/health").headers["X-Request-ID"]) == 32
    forged = client.get("/api/health", headers={"X-Request-ID": "a" * 65}).headers["X-Request-ID"]
    assert forged != "a" * 65
    assert len(forged) == 32


def test_access_log_is_json_with_fields(client, pilot, caplog):
    with caplog.at_level(logging.INFO, logger="pult.access"):
        client.get("/api/health")
    record = next(r for r in caplog.records if r.name == "pult.access")
    entry = json.loads(JsonFormatter().format(record))
    assert entry["route"] == "/api/health"
    assert entry["status"] == 200
    assert entry["duration_ms"] >= 0


def test_ready_reports_database(client, pilot):
    assert client.get("/api/ready").json() == {"status": "ready", "database": "ok"}


def test_ready_fails_without_database():
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("select 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_session] = BrokenSession
    try:
        response = TestClient(app).get("/api/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
