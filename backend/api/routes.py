from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time

from backend.agents.investigator import investigate

router = APIRouter()

# in-memory store for investigation history (replace with DB for production)
investigation_store: dict = {}


class InvestigateRequest(BaseModel):
    namespace: str = "default"
    pod_name: Optional[str] = None
    deployment_name: Optional[str] = None


@router.post("/investigate")
def trigger_investigation(req: InvestigateRequest):
    inv_id = str(uuid.uuid4())
    try:
        result = investigate(
            namespace=req.namespace,
            pod_name=req.pod_name,
            deployment_name=req.deployment_name,
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
