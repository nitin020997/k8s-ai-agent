from kubernetes import client, config
from typing import Optional


def load_kube_config():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def collect_logs(namespace: str, pod_name: str, container: Optional[str] = None, tail_lines: int = 100) -> dict:
    load_kube_config()
    v1 = client.CoreV1Api()

    kwargs = {"namespace": namespace, "tail_lines": tail_lines}
    if container:
        kwargs["container"] = container

    try:
        logs = v1.read_namespaced_pod_log(name=pod_name, **kwargs)
    except Exception as e:
        logs = f"Error fetching logs: {e}"

    # also try previous container logs (useful for CrashLoopBackOff)
    previous_logs = None
    try:
        previous_logs = v1.read_namespaced_pod_log(name=pod_name, previous=True, tail_lines=50, **{k: v for k, v in kwargs.items() if k != "tail_lines"})
    except Exception:
        pass

    return {
        "pod": pod_name,
        "namespace": namespace,
        "current_logs": logs,
        "previous_logs": previous_logs,
    }
