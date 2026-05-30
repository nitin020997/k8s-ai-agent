import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

os.environ["MOCK_MODE"] = "true"
os.environ["OPENROUTER_API_KEY"] = "test-key"

from backend.main import app

client = TestClient(app)

MOCK_ANALYSIS = {
    "root_cause": "CrashLoopBackOff due to database connection failure",
    "confidence": 90,
    "signals": ["14 restarts", "connection refused in logs"],
    "fix_recommendations": [{"description": "Check DB", "command": "kubectl get svc db"}],
    "summary": "App can't reach the database.",
}


def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_investigate_endpoint():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": json.dumps(MOCK_ANALYSIS)}}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp):
        res = client.post("/api/v1/investigate", json={"namespace": "default"})

    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["analysis"]["confidence"] == 90


def test_history_endpoint():
    res = client.get("/api/v1/history")
    assert res.status_code == 200
    assert "investigations" in res.json()


def test_get_investigation_not_found():
    res = client.get("/api/v1/investigation/nonexistent-id")
    assert res.status_code == 404


def test_get_investigation_by_id():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": json.dumps(MOCK_ANALYSIS)}}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp):
        create_res = client.post("/api/v1/investigate", json={"namespace": "default"})

    inv_id = create_res.json()["id"]
    res = client.get(f"/api/v1/investigation/{inv_id}")
    assert res.status_code == 200
    assert res.json()["id"] == inv_id
