"""
Mock Kubernetes data for demo/testing without a real cluster.
Set MOCK_MODE=true in .env to use this.
"""

MOCK_PODS = {
    "pods": [
        {
            "name": "webapp-7d9f8b6c4-xk2pq",
            "namespace": "default",
            "phase": "Running",
            "conditions": [
                {"type": "Ready", "status": "False", "reason": "ContainersNotReady"}
            ],
            "container_statuses": [
                {
                    "name": "webapp",
                    "ready": False,
                    "restart_count": 14,
                    "state": {
                        "waiting": True,
                        "reason": "CrashLoopBackOff",
                        "message": "back-off 5m0s restarting failed container",
                    },
                }
            ],
            "node_name": "node-1",
            "labels": {"app": "webapp", "version": "v2"},
        }
    ]
}

MOCK_LOGS = {
    "pod": "webapp-7d9f8b6c4-xk2pq",
    "namespace": "default",
    "current_logs": (
        "2024-01-15T10:23:01Z INFO  Starting application...\n"
        "2024-01-15T10:23:02Z INFO  Connecting to database at db:5432\n"
        "2024-01-15T10:23:02Z ERROR Failed to connect to database: connection refused\n"
        "2024-01-15T10:23:02Z FATAL Application startup failed\n"
    ),
    "previous_logs": (
        "2024-01-15T10:18:01Z INFO  Starting application...\n"
        "2024-01-15T10:18:02Z ERROR Failed to connect to database: connection refused\n"
        "2024-01-15T10:18:02Z FATAL Application startup failed\n"
    ),
}

MOCK_EVENTS = {
    "namespace": "default",
    "events": [
        {
            "reason": "BackOff",
            "message": "Back-off restarting failed container webapp in pod webapp-7d9f8b6c4-xk2pq",
            "type": "Warning",
            "count": 42,
            "first_time": "2024-01-15T10:00:00+00:00",
            "last_time": "2024-01-15T10:23:05+00:00",
            "involved_object": "webapp-7d9f8b6c4-xk2pq",
            "kind": "Pod",
        },
        {
            "reason": "Failed",
            "message": "Error: failed to start container: exit code 1",
            "type": "Warning",
            "count": 14,
            "first_time": "2024-01-15T10:00:00+00:00",
            "last_time": "2024-01-15T10:22:50+00:00",
            "involved_object": "webapp-7d9f8b6c4-xk2pq",
            "kind": "Pod",
        },
    ],
}

MOCK_DEPLOYMENTS = {
    "deployments": [
        {
            "name": "webapp",
            "desired": 3,
            "ready": 0,
            "available": 0,
        }
    ]
}

MOCK_DEPLOYMENT_DETAIL = {
    "name": "webapp",
    "namespace": "default",
    "replicas_desired": 3,
    "replicas_ready": 0,
    "replicas_available": 0,
    "replicas_unavailable": 3,
    "conditions": [
        {
            "type": "Available",
            "status": "False",
            "reason": "MinimumReplicasUnavailable",
            "message": "Deployment does not have minimum availability.",
        }
    ],
    "containers": [
        {
            "name": "webapp",
            "image": "myapp:v2",
            "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}},
            "liveness_probe": True,
            "readiness_probe": True,
        }
    ],
    "strategy": "RollingUpdate",
}

MOCK_SERVICES = {
    "services": [
        {
            "name": "webapp-svc",
            "type": "ClusterIP",
            "cluster_ip": "10.96.1.100",
            "ports": [{"port": 80, "target_port": "8080", "protocol": "TCP"}],
            "selector": {"app": "webapp"},
        }
    ]
}
