from kubernetes import client, config
from typing import Optional


def load_kube_config():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def inspect_pods(namespace: str = "default", pod_name: Optional[str] = None) -> dict:
    load_kube_config()
    v1 = client.CoreV1Api()

    if pod_name:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        return _parse_pod(pod)

    pods = v1.list_namespaced_pod(namespace=namespace)
    return {"pods": [_parse_pod(p) for p in pods.items]}


def _parse_pod(pod) -> dict:
    container_statuses = []
    if pod.status.container_statuses:
        for cs in pod.status.container_statuses:
            state = {}
            if cs.state.running:
                state = {"running": True, "started_at": str(cs.state.running.started_at)}
            elif cs.state.waiting:
                state = {"waiting": True, "reason": cs.state.waiting.reason, "message": cs.state.waiting.message}
            elif cs.state.terminated:
                state = {
                    "terminated": True,
                    "reason": cs.state.terminated.reason,
                    "exit_code": cs.state.terminated.exit_code,
                    "message": cs.state.terminated.message,
                }
            container_statuses.append({
                "name": cs.name,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "state": state,
            })

    return {
        "name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "phase": pod.status.phase,
        "conditions": [
            {"type": c.type, "status": c.status, "reason": c.reason}
            for c in (pod.status.conditions or [])
        ],
        "container_statuses": container_statuses,
        "node_name": pod.spec.node_name,
        "labels": pod.metadata.labels or {},
    }
