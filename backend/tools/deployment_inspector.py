from kubernetes import client, config


def load_kube_config():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def inspect_deployment(namespace: str, deployment_name: str) -> dict:
    load_kube_config()
    apps_v1 = client.AppsV1Api()

    try:
        dep = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
    except Exception as e:
        return {"error": str(e)}

    conditions = [
        {"type": c.type, "status": c.status, "reason": c.reason, "message": c.message}
        for c in (dep.status.conditions or [])
    ]

    containers = [
        {
            "name": c.name,
            "image": c.image,
            "resources": {
                "requests": c.resources.requests if c.resources else None,
                "limits": c.resources.limits if c.resources else None,
            },
            "liveness_probe": bool(c.liveness_probe),
            "readiness_probe": bool(c.readiness_probe),
        }
        for c in dep.spec.template.spec.containers
    ]

    return {
        "name": dep.metadata.name,
        "namespace": dep.metadata.namespace,
        "replicas_desired": dep.spec.replicas,
        "replicas_ready": dep.status.ready_replicas,
        "replicas_available": dep.status.available_replicas,
        "replicas_unavailable": dep.status.unavailable_replicas,
        "conditions": conditions,
        "containers": containers,
        "strategy": dep.spec.strategy.type,
    }


def list_deployments(namespace: str) -> dict:
    load_kube_config()
    apps_v1 = client.AppsV1Api()
    deps = apps_v1.list_namespaced_deployment(namespace=namespace)
    return {
        "deployments": [
            {
                "name": d.metadata.name,
                "desired": d.spec.replicas,
                "ready": d.status.ready_replicas,
                "available": d.status.available_replicas,
            }
            for d in deps.items
        ]
    }
