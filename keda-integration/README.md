# KEDA Integration for K8s AI Agent

KEDA (Kubernetes-based Event Driven Autoscaling) integration that enables the AI agent to:
- Monitor queue depths and event sources
- Automatically scale workloads to/from zero based on events
- Manage ScaledObjects and TriggerAuthentication resources

## What is KEDA?

KEDA is a CNCF graduated project that extends Kubernetes' native autoscaling (HPA) with event-driven scaling. It bridges external event sources (queues, streams, databases) to Kubernetes pod scaling — including scaling **all the way to zero** when idle.

### Architecture

```
External Event Source  →  KEDA Operator  →  HPA  →  Deployment (0..N replicas)
(Kafka, SQS, Redis…)      (metrics adapter)
```

KEDA has two main components:
1. **keda-operator** — watches `ScaledObject` / `ScaledJob` CRDs, drives the HPA
2. **keda-metrics-apiserver** — acts as a Kubernetes External Metrics API server

### Core CRDs

| CRD | Purpose |
|-----|---------|
| `ScaledObject` | Scale a Deployment/StatefulSet based on event metrics |
| `ScaledJob` | Scale Kubernetes Jobs (one job per event batch) |
| `TriggerAuthentication` | Store scaler credentials (secrets, env vars, pod identity) |
| `ClusterTriggerAuthentication` | Cluster-scoped TriggerAuthentication |

## Scalers Supported (60+)

**Message Queues:** Kafka, RabbitMQ, ActiveMQ, Artemis, NATS JetStream, Pulsar, Beanstalkd, Solace  
**AWS:** SQS, Kinesis, DynamoDB, DynamoDB Streams, CloudWatch  
**Azure:** Service Bus, Event Hub, Queue Storage, Blob Storage, Pipelines, Monitor, Log Analytics  
**GCP:** Pub/Sub, Cloud Tasks, Stackdriver, GCS  
**Databases:** PostgreSQL, MySQL, MSSQL, MongoDB, CouchDB, Cassandra, Elasticsearch, OpenSearch, InfluxDB, Redis, Redis Streams  
**Observability:** Prometheus, Datadog, New Relic, Graphite, Loki, Dynatrace, Splunk  
**Kubernetes-native:** CPU/Memory, Kubernetes Workload, Kubernetes Resource, Cron (time-based)  
**Other:** GitHub Actions Runners, Selenium Grid, Temporal, etcd, External (gRPC/HTTP)

## Example: Scale on Queue Depth

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: ai-agent-worker-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: ai-agent-worker
  minReplicaCount: 0        # scale to zero when idle
  maxReplicaCount: 20
  cooldownPeriod: 30
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: pending_k8s_agent_tasks
        threshold: "5"        # 1 replica per 5 pending tasks
        query: sum(pending_k8s_agent_tasks)
```

## Example: Scale on Redis Queue

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: redis-worker-scaler
spec:
  scaleTargetRef:
    name: task-worker
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: task_queue
        listLength: "10"
```

## K8s AI Agent + KEDA Use Cases

1. **Auto-scale AI inference workers** based on request queue depth
2. **Scale to zero** overnight / during low traffic to save costs
3. **Burst to N replicas** when Prometheus shows pending tasks spike
4. **Schedule-based scaling** via the Cron scaler for predictable traffic
