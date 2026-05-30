import os
import httpx
import json
from typing import Optional

from backend.tools.pod_inspector import inspect_pods
from backend.tools.logs_collector import collect_logs
from backend.tools.events_analyzer import get_events
from backend.tools.deployment_inspector import inspect_deployment, list_deployments
from backend.tools.network_inspector import inspect_services, check_endpoints
from backend.tools import mock_data

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are an expert Kubernetes Site Reliability Engineer (SRE).
You are given evidence from a Kubernetes cluster investigation including pod status, logs, events, deployments, and network info.
Your job is to:
1. Identify the root cause of the problem
2. Assign a confidence score (0-100)
3. List the specific signals that led to your conclusion
4. Provide actionable fix recommendations with kubectl commands or YAML patches

Respond in this exact JSON format:
{
  "root_cause": "short description of the root cause",
  "confidence": 85,
  "signals": ["signal 1", "signal 2"],
  "fix_recommendations": [
    {
      "description": "what to do",
      "command": "kubectl command or YAML snippet"
    }
  ],
  "summary": "1-2 sentence plain English explanation"
}"""


def gather_evidence(namespace: str, pod_name: Optional[str] = None, deployment_name: Optional[str] = None) -> dict:
    if MOCK_MODE:
        return {
            "pods": mock_data.MOCK_PODS,
            "services": mock_data.MOCK_SERVICES,
            "events": mock_data.MOCK_EVENTS,
            "logs": mock_data.MOCK_LOGS,
            "deployment": mock_data.MOCK_DEPLOYMENT_DETAIL,
        }

    evidence = {}
    evidence["pods"] = inspect_pods(namespace=namespace, pod_name=pod_name)
    evidence["services"] = inspect_services(namespace=namespace)
    evidence["events"] = get_events(namespace=namespace, pod_name=pod_name)

    if pod_name:
        evidence["logs"] = collect_logs(namespace=namespace, pod_name=pod_name)

    if deployment_name:
        evidence["deployment"] = inspect_deployment(namespace=namespace, deployment_name=deployment_name)
    else:
        evidence["deployments"] = list_deployments(namespace=namespace)

    return evidence


def analyze_with_llm(evidence: dict) -> dict:
    evidence_text = json.dumps(evidence, indent=2, default=str)

    user_message = f"""Investigate this Kubernetes cluster evidence and identify the root cause:

<evidence>
{evidence_text}
</evidence>

Respond with JSON only."""

    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    # strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    return json.loads(content.strip())


def investigate(namespace: str, pod_name: Optional[str] = None, deployment_name: Optional[str] = None) -> dict:
    evidence = gather_evidence(namespace=namespace, pod_name=pod_name, deployment_name=deployment_name)
    analysis = analyze_with_llm(evidence)
    return {
        "namespace": namespace,
        "pod_name": pod_name,
        "deployment_name": deployment_name,
        "evidence": evidence,
        "analysis": analysis,
    }
