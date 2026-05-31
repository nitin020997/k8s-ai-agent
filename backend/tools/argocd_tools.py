import os
import httpx
from typing import Optional

def _argocd_url() -> str:
    return os.getenv("ARGOCD_URL", "https://localhost:8888")

_token_cache: dict = {}


def _get_client() -> httpx.Client:
    token = _resolve_token()
    return httpx.Client(
        base_url=_argocd_url(),
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=15,
    )


def _resolve_token() -> str:
    static_token = os.getenv("ARGOCD_TOKEN", "")
    if static_token:
        return static_token
    if _token_cache.get("token"):
        return _token_cache["token"]
    username = os.getenv("ARGOCD_USERNAME", "admin")
    password = os.getenv("ARGOCD_PASSWORD", "")
    resp = httpx.post(
        f"{_argocd_url()}/api/v1/session",
        json={"username": username, "password": password},
        verify=False,
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["token"]
    _token_cache["token"] = token
    return token


def list_argocd_apps(project: Optional[str] = None) -> dict:
    """List all Argo CD applications with sync and health status."""
    with _get_client() as client:
        params = {}
        if project:
            params["projects"] = project
        resp = client.get("/api/v1/applications", params=params)
        resp.raise_for_status()
        raw = resp.json().get("items", [])

    apps = []
    for app in raw:
        meta = app.get("metadata", {})
        status = app.get("status", {})
        apps.append({
            "name": meta.get("name"),
            "namespace": meta.get("namespace"),
            "project": app.get("spec", {}).get("project"),
            "repo": app.get("spec", {}).get("source", {}).get("repoURL"),
            "path": app.get("spec", {}).get("source", {}).get("path"),
            "target_revision": app.get("spec", {}).get("source", {}).get("targetRevision", "HEAD"),
            "dest_server": app.get("spec", {}).get("destination", {}).get("server"),
            "dest_namespace": app.get("spec", {}).get("destination", {}).get("namespace"),
            "sync_status": status.get("sync", {}).get("status"),
            "sync_revision": status.get("sync", {}).get("revision"),
            "health_status": status.get("health", {}).get("status"),
            "health_message": status.get("health", {}).get("message"),
            "operation_state": status.get("operationState", {}).get("phase") if status.get("operationState") else None,
        })

    return {"total": len(apps), "apps": apps}


def get_argocd_app(app_name: str) -> dict:
    """Get detailed status and resource tree for a specific Argo CD app."""
    with _get_client() as client:
        resp = client.get(f"/api/v1/applications/{app_name}")
        resp.raise_for_status()
        app = resp.json()

        tree_resp = client.get(f"/api/v1/applications/{app_name}/resource-tree")
        tree_resp.raise_for_status()
        tree = tree_resp.json()

    meta = app.get("metadata", {})
    status = app.get("status", {})
    spec = app.get("spec", {})

    resources = []
    for r in status.get("resources", []):
        resources.append({
            "group": r.get("group"),
            "kind": r.get("kind"),
            "name": r.get("name"),
            "namespace": r.get("namespace"),
            "sync_status": r.get("status"),
            "health_status": r.get("health", {}).get("status") if r.get("health") else None,
            "health_message": r.get("health", {}).get("message") if r.get("health") else None,
        })

    return {
        "name": meta.get("name"),
        "project": spec.get("project"),
        "repo": spec.get("source", {}).get("repoURL"),
        "path": spec.get("source", {}).get("path"),
        "target_revision": spec.get("source", {}).get("targetRevision", "HEAD"),
        "dest_server": spec.get("destination", {}).get("server"),
        "dest_namespace": spec.get("destination", {}).get("namespace"),
        "sync_status": status.get("sync", {}).get("status"),
        "sync_revision": status.get("sync", {}).get("revision"),
        "health_status": status.get("health", {}).get("status"),
        "health_message": status.get("health", {}).get("message"),
        "conditions": status.get("conditions", []),
        "operation_state": status.get("operationState"),
        "resources": resources,
        "node_count": len(tree.get("nodes", [])),
    }


def get_argocd_app_diff(app_name: str) -> dict:
    """Get the diff between desired (Git) and live (cluster) state for an app."""
    with _get_client() as client:
        resp = client.get(f"/api/v1/applications/{app_name}/managed-resources")
        resp.raise_for_status()
        data = resp.json()

    diffs = []
    for item in data.get("items", []):
        if not item:
            continue
        has_diff = item.get("diff") and item.get("diff").strip()
        diffs.append({
            "group": item.get("group"),
            "kind": item.get("kind"),
            "name": item.get("name"),
            "namespace": item.get("namespace"),
            "sync_status": item.get("status"),
            "has_diff": bool(has_diff),
            "diff": item.get("diff") if has_diff else None,
            "live_state": item.get("liveState"),
            "target_state": item.get("targetState"),
        })

    out_of_sync = [d for d in diffs if d["sync_status"] == "OutOfSync"]
    return {
        "app_name": app_name,
        "total_resources": len(diffs),
        "out_of_sync_count": len(out_of_sync),
        "out_of_sync_resources": out_of_sync,
        "all_resources": diffs,
    }


def sync_argocd_app(app_name: str, revision: Optional[str] = None, prune: bool = False, dry_run: bool = False) -> dict:
    """Trigger a sync for an Argo CD app."""
    body: dict = {}
    if revision:
        body["revision"] = revision
    if prune:
        body["prune"] = True
    if dry_run:
        body["dryRun"] = True

    with _get_client() as client:
        resp = client.post(f"/api/v1/applications/{app_name}/sync", json=body)
        resp.raise_for_status()
        result = resp.json()

    status = result.get("status", {})
    return {
        "app_name": app_name,
        "sync_status": status.get("sync", {}).get("status"),
        "health_status": status.get("health", {}).get("status"),
        "operation_state": result.get("operation"),
        "message": "Sync triggered successfully",
    }


def rollback_argocd_app(app_name: str, revision_id: int) -> dict:
    """Rollback an Argo CD app to a previous deployed revision by history ID."""
    with _get_client() as client:
        resp = client.post(f"/api/v1/applications/{app_name}/rollback", json={"id": revision_id})
        resp.raise_for_status()
        result = resp.json()

    status = result.get("status", {})
    return {
        "app_name": app_name,
        "sync_status": status.get("sync", {}).get("status"),
        "health_status": status.get("health", {}).get("status"),
        "message": f"Rollback to revision {revision_id} triggered",
    }


def get_argocd_app_history(app_name: str) -> dict:
    """Get deployment history for an Argo CD app."""
    with _get_client() as client:
        resp = client.get(f"/api/v1/applications/{app_name}/revisions")
        if resp.status_code == 404:
            # fallback: get from app status
            app_resp = client.get(f"/api/v1/applications/{app_name}")
            app_resp.raise_for_status()
            history = app_resp.json().get("status", {}).get("history", [])
        else:
            resp.raise_for_status()
            history = resp.json().get("items", [])

    return {
        "app_name": app_name,
        "history": [
            {
                "id": h.get("id"),
                "revision": h.get("revision"),
                "deployed_at": h.get("deployedAt"),
                "source": h.get("source", {}),
            }
            for h in history
        ],
    }
