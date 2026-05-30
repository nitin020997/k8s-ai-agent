from kubernetes import client, config


def load_kube_config():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def inspect_services(namespace: str) -> dict:
    load_kube_config()
    v1 = client.CoreV1Api()
    services = v1.list_namespaced_service(namespace=namespace)

    return {
        "services": [
            {
                "name": svc.metadata.name,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "ports": [
                    {"port": p.port, "target_port": str(p.target_port), "protocol": p.protocol}
                    for p in (svc.spec.ports or [])
                ],
                "selector": svc.spec.selector or {},
            }
            for svc in services.items
        ]
    }


def check_endpoints(namespace: str, service_name: str) -> dict:
    load_kube_config()
    v1 = client.CoreV1Api()

    try:
        ep = v1.read_namespaced_endpoints(name=service_name, namespace=namespace)
    except Exception as e:
        return {"error": str(e)}

    subsets = []
    for subset in (ep.subsets or []):
        addresses = [a.ip for a in (subset.addresses or [])]
        not_ready = [a.ip for a in (subset.not_ready_addresses or [])]
        ports = [p.port for p in (subset.ports or [])]
        subsets.append({"ready_addresses": addresses, "not_ready_addresses": not_ready, "ports": ports})

    return {
        "service": service_name,
        "namespace": namespace,
        "subsets": subsets,
        "has_endpoints": any(s["ready_addresses"] for s in subsets),
    }
