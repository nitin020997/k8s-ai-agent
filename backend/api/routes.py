from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time

from backend.agents.investigator import investigate
from backend.tools.argocd_tools import (
    list_argocd_apps,
    get_argocd_app,
    get_argocd_app_diff,
    get_argocd_app_history,
    sync_argocd_app,
    rollback_argocd_app,
)

router = APIRouter()

# in-memory store for investigation history (replace with DB for production)
investigation_store: dict = {}


class InvestigateRequest(BaseModel):
    namespace: str = "default"
    pod_name: Optional[str] = None
    deployment_name: Optional[str] = None
    argocd_app: Optional[str] = None


class SyncRequest(BaseModel):
    revision: Optional[str] = None
    prune: bool = False
    dry_run: bool = False


class RollbackRequest(BaseModel):
    revision_id: int


@router.post("/investigate")
def trigger_investigation(req: InvestigateRequest):
    inv_id = str(uuid.uuid4())
    try:
        result = investigate(
            namespace=req.namespace,
            pod_name=req.pod_name,
            deployment_name=req.deployment_name,
            argocd_app=req.argocd_app,
        )
        record = {
            "id": inv_id,
            "timestamp": time.time(),
            "status": "completed",
            **result,
        }
        investigation_store[inv_id] = record
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigation/{inv_id}")
def get_investigation(inv_id: str):
    record = investigation_store.get(inv_id)
    if not record:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return record


@router.get("/history")
def get_history():
    return {
        "investigations": sorted(
            investigation_store.values(), key=lambda x: x["timestamp"], reverse=True
        )
    }


@router.get("/health")
def health():
    return {"status": "ok"}


# ── Argo CD routes ────────────────────────────────────────────────────────────

@router.get("/argocd/apps")
def argocd_list_apps(project: Optional[str] = None):
    try:
        return list_argocd_apps(project=project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/argocd/apps/{app_name}")
def argocd_get_app(app_name: str):
    try:
        return get_argocd_app(app_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/argocd/apps/{app_name}/diff")
def argocd_app_diff(app_name: str):
    try:
        return get_argocd_app_diff(app_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/argocd/apps/{app_name}/history")
def argocd_app_history(app_name: str):
    try:
        return get_argocd_app_history(app_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/argocd/apps/{app_name}/sync")
def argocd_sync(app_name: str, req: SyncRequest = SyncRequest()):
    try:
        return sync_argocd_app(app_name, revision=req.revision, prune=req.prune, dry_run=req.dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/argocd/apps/{app_name}/rollback")
def argocd_rollback(app_name: str, req: RollbackRequest):
    try:
        return rollback_argocd_app(app_name, revision_id=req.revision_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
