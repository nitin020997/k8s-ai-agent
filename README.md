# K8s AI Agent

An AI-powered Kubernetes troubleshooting agent that investigates cluster failures, analyzes logs and events, identifies root causes, and suggests fixes.

## Architecture

```
Kubernetes Cluster
       ↓
Investigation Layer (tools/)
  ├── pod_inspector.py      — pod health, crash detection
  ├── logs_collector.py     — current + previous container logs
  ├── events_analyzer.py    — warning events, failure detection
  ├── deployment_inspector.py — rollout status, resource configs
  └── network_inspector.py  — services, endpoints, DNS

       ↓
AI Agent Layer (agents/)
  └── investigator.py       — gathers evidence → LLM analysis → structured result

       ↓
FastAPI Backend (api/)
  └── routes.py             — POST /investigate, GET /history

       ↓
Frontend Dashboard (frontend/)
  └── index.html            — simple HTML/CSS/JS UI
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

3. **Get OpenRouter API key**
   - Sign up at https://openrouter.ai
   - Create an API key (free tier available)
   - Supports Claude, GPT, DeepSeek models

4. **Make sure kubectl is configured**
   ```bash
   kubectl get nodes   # should work
   ```

5. **Run the backend**
   ```bash
   python -m backend.main
   ```

6. **Open the frontend**
   ```
   open frontend/index.html
   ```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/investigate` | Trigger investigation |
| GET | `/api/v1/investigation/{id}` | Get investigation by ID |
| GET | `/api/v1/history` | List all investigations |
| GET | `/api/v1/health` | Health check |

### Example Request
```bash
curl -X POST http://localhost:8000/api/v1/investigate \
  -H "Content-Type: application/json" \
  -d '{"namespace": "default", "pod_name": "my-app-xyz"}'
```

## Supported Failure Types
- CrashLoopBackOff
- ImagePullBackOff / ErrImagePull
- OOMKilled
- Pending pods (resource exhaustion, taints, node selectors)
- Deployment rollout failures
- Service selector mismatches
- DNS / networking issues
- Readiness / liveness probe failures
