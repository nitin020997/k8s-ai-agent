from kubernetes import client, config
from typing import Optional


def load_kube_config():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def get_events(namespace: str, pod_name: Optional[str] = None) -> dict:
    load_kube_config()
    v1 = client.CoreV1Api()

    field_selector = f"involvedObject.name={pod_name}" if pod_name else None
    events = v1.list_namespaced_event(namespace=namespace, field_selector=field_selector)

    parsed = []
    for e in events.items:
        parsed.append({
            "reason": e.reason,
            "message": e.message,
            "type": e.type,
            "count": e.count,
            "first_time": str(e.first_timestamp),
            "last_time": str(e.last_timestamp),
            "involved_object": e.involved_object.name,
            "kind": e.involved_object.kind,
        })

    # sort warnings first
    parsed.sort(key=lambda x: (x["type"] != "Warning", -(x["count"] or 0)))
    return {"namespace": namespace, "events": parsed}
