import os
import httpx
import json
from typing import Optional

from backend.tools.pod_inspector import inspect_pods
from backend.tools.logs_collector import collect_logs
from backend.tools.events_analyzer import get_events
from backend.tools.deployment_inspector import inspect_deployment, list_deployments
from backend.tools.network_inspector import inspect_services, check_endpoints
from backend.tools.argocd_tools import list_argocd_apps, get_argocd_app, get_argocd_app_diff
from backend.tools import mock_data

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are an expert Kubernetes Site Reliability Engineer (SRE) with deep GitOps knowledge.
You are given evidence from a Kubernetes cluster investigation including pod status, logs, events, deployments, network info, and Argo CD GitOps state.

When Argo CD data is present, consider:
- Whether the issue is a GitOps drift (live state != desired Git state)
- Whether a recent sync introduced the problem (check sync revision and timing)
- Whether the fix should be applied via Git (preferred) or via a direct sync/rollback

Your job is to:
1. Identify the root cause of the problem
2. Assign a confidence score (0-100)
3. List the specific signals that led to your conclusion
4. Provide actionable fix recommendations — prefer GitOps-native fixes (git push, argocd sync, argocd rollback) over direct kubectl patches

Respond in this exact JSON format:
{
  "root_cause": "short description of the root cause",
  "confidence": 85,
  "signals": ["signal 1", "signal 2"],
  "gitops_context": {
    "is_gitops_managed": true,
    "drift_detected": false,
    "recommended_action": "sync | rollback | fix-in-git | none"
  },
  "fix_recommendations": [
    {
      "description": "what to do",
      "command": "kubectl or argocd command or YAML snippet"
    }
  ],
  "summary": "1-2 sentence plain English explanation"
}"""


def gather_evidence(namespace: str, pod_name: Optional[str] = None, deployment_name: Optional[str] = None, argocd_app: Optional[str] = None) -> dict:
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

    # Enrich with Argo CD GitOps state if available
    try:
        if argocd_app:
            evidence["argocd_app"] = get_argocd_app(argocd_app)
            evidence["argocd_diff"] = get_argocd_app_diff(argocd_app)
        else:
            evidence["argocd_apps"] = list_argocd_apps()
    except Exception:
        pass  # Argo CD not available — degrade gracefully

    return evidence


def analyze_with_llm(evidence: dict) -> dict:
    evidence_text = json.dumps(evidence, indent=2, default=str)

    user_message = f"""Investigate this Kubernetes cluster evidence and identify the root cause:

<evidence>
{evidence_text}
</evidence>

Respond with JSON only."""

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        return _call_anthropic(user_message, anthropic_key)
    return _call_openrouter(user_message)


def _call_anthropic(user_message: str, api_key: str) -> dict:
    import anthropic
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    content = message.content[0].text
    return _parse_llm_response(content)


def _call_openrouter(user_message: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
    response = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
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
    return _parse_llm_response(content)


def _parse_llm_response(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


def investigate(namespace: str, pod_name: Optional[str] = None, deployment_name: Optional[str] = None, argocd_app: Optional[str] = None) -> dict:
    evidence = gather_evidence(namespace=namespace, pod_name=pod_name, deployment_name=deployment_name, argocd_app=argocd_app)
    analysis = analyze_with_llm(evidence)
    return {
        "namespace": namespace,
        "pod_name": pod_name,
        "deployment_name": deployment_name,
        "argocd_app": argocd_app,
        "evidence": evidence,
        "analysis": analysis,
    }
