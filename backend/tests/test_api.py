from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_dashboard_endpoints():
    with TestClient(app) as client:
        health = client.get("/api/health")
        dashboard = client.get("/api/dashboard")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["active_findings"] >= 4

