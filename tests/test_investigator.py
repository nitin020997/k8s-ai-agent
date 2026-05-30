import os
import json
import pytest
from unittest.mock import patch, MagicMock

os.environ["MOCK_MODE"] = "true"
os.environ["OPENROUTER_API_KEY"] = "test-key"

from backend.agents.investigator import gather_evidence, analyze_with_llm, investigate
from backend.tools import mock_data


def test_gather_evidence_mock_mode():
    evidence = gather_evidence(namespace="default", pod_name="webapp-xyz")
    assert "pods" in evidence
    assert "events" in evidence
    assert "logs" in evidence
    assert "services" in evidence


def test_mock_pods_have_crashloopbackoff():
    evidence = gather_evidence(namespace="default")
    pod = evidence["pods"]["pods"][0]
    state = pod["container_statuses"][0]["state"]
    assert state.get("reason") == "CrashLoopBackOff"


def test_mock_events_contain_warnings():
    evidence = gather_evidence(namespace="default")
    warning_events = [e for e in evidence["events"]["events"] if e["type"] == "Warning"]
    assert len(warning_events) > 0


def test_mock_logs_contain_error():
    evidence = gather_evidence(namespace="default", pod_name="webapp-xyz")
    assert "ERROR" in evidence["logs"]["current_logs"]


def test_mock_deployment_unavailable():
    evidence = gather_evidence(namespace="default", deployment_name="webapp")
    dep = evidence["deployment"]
    assert dep["replicas_ready"] == 0
    assert dep["replicas_unavailable"] == 3


MOCK_LLM_RESPONSE = {
    "root_cause": "Database connection refused causing CrashLoopBackOff",
    "confidence": 92,
    "signals": [
        "Container restart count: 14",
        "Error log: Failed to connect to database: connection refused",
        "Event: BackOff (count: 42)",
    ],
    "fix_recommendations": [
        {
            "description": "Check if the database service is running",
            "command": "kubectl get svc db -n default",
        },
        {
            "description": "Check database pod logs",
            "command": "kubectl logs -l app=db -n default --tail=50",
        },
    ],
    "summary": "The webapp is crash-looping because it cannot connect to the database at db:5432. The database service may be down or misconfigured.",
}


def test_analyze_with_llm():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(MOCK_LLM_RESPONSE)}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        result = analyze_with_llm({"pods": mock_data.MOCK_PODS})

    assert result["root_cause"] == MOCK_LLM_RESPONSE["root_cause"]
    assert result["confidence"] == 92
    assert len(result["signals"]) == 3
    assert len(result["fix_recommendations"]) == 2


def test_full_investigation_pipeline():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(MOCK_LLM_RESPONSE)}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        result = investigate(namespace="default", pod_name="webapp-xyz")

    assert result["namespace"] == "default"
    assert "evidence" in result
    assert "analysis" in result
    assert result["analysis"]["confidence"] == 92


def test_llm_handles_markdown_fenced_json():
    fenced = f"```json\n{json.dumps(MOCK_LLM_RESPONSE)}\n```"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": fenced}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response):
        result = analyze_with_llm({})

    assert result["root_cause"] == MOCK_LLM_RESPONSE["root_cause"]
