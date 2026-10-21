from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_health_schema_in_openapi():
    schema = client.get("/openapi.json").json()
    assert set(schema["components"]["schemas"]["HealthResponse"]["properties"]) == {"status", "version"}
