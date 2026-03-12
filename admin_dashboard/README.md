# Admin Dashboard - Per-Deployment Monitoring

**Status:** ✅ Complete
**Port:** 8001 (per instance)
**Last Updated:** 2026-03-12

---

## Overview

The Admin Dashboard is a per-deployment monitoring interface that shows detailed metrics, guardrail performance, and audit trails for a single OpenClaw instance. It runs on port 8001 on each deployment machine and reports aggregate metrics back to the Master Dashboard every 5 minutes.

---

## Architecture

### Deployment
```
Each Instance (neo-toshiba, mba2, agent3)
├── Master Dashboard (port 8000) - Overview of all 3
├── Admin Dashboard (port 8001) - Detail of this instance
│   ├── GuardrailCollector - collects metrics from Phase 3 guardrails
│   ├── EventPusher - pushes critical events to Master
│   └── FastAPI backend + HTML frontend
```

### Sync Strategy
- **Metrics Pull (5-min):** Master pulls `/metrics` endpoint from each instance
- **Events Push (real-time):** Instance pushes critical events to Master immediately
- **Health Checks (1-min):** Master polls `/health` for connection status

---

## Quick Start

### Prerequisites
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Admin Dashboard
```bash
# Set environment variables
export DEPLOYMENT_ID="neo-toshiba"
export MASTER_HOST="192.168.1.1"  # Master dashboard IP
export MASTER_PORT=8000

# Start server
bash start.sh
```

Access:
- **Dashboard:** http://localhost:8001
- **API:** http://localhost:8001/api/dashboard
- **Metrics (for Master):** http://localhost:8001/metrics
- **API Docs:** http://localhost:8001/docs

---

## API Endpoints

### Health & Status
- `GET /health` — Health check (status, deployment_id, connected_to_master)
- `GET /status` — Detailed status (collector/pusher initialized, queued events)

### Metrics (Called by Master every 5 min)
- `GET /metrics` — Current metrics snapshot (uptime, rate limits, costs, guardrails, etc.)
- `GET /metrics/history?hours=24` — Time-series metrics (placeholder)

### Audit Trail
- `GET /events?limit=100` — Recent audit events
- `GET /events/blocks?limit=20` — Recent guardrail blocks

### Dashboard
- `GET /api/dashboard` — Complete dashboard data (metrics + events + blocks)

### Critical Event Endpoints
- `POST /notify/rate_limit_exceeded` — Notify Master of rate limit exceeded
- `POST /notify/auth_block` — Notify Master of auth block
- `POST /notify/cost_alert` — Notify Master of cost anomaly
- `POST /notify/anomaly` — Notify Master of system anomaly

---

## Components

### `app.py` (FastAPI Backend)
Main server with endpoints:
- Startup: Initialize `GuardrailCollector` and `EventPusher`
- `/metrics` — Collects guardrail metrics and returns them
- `/api/dashboard` — Aggregates metrics, events, and blocks into single response
- `/notify/*` — Endpoints to trigger critical event pushes

**Configuration (env vars):**
```bash
DEPLOYMENT_ID      # e.g., "neo-toshiba"
MASTER_HOST        # e.g., "192.168.1.1"
MASTER_PORT        # e.g., 8000
```

### `guardrail_collector.py` (Metrics Collection)
Collects metrics from Phase 3 guardrails:

**Interface:**
```python
collector = GuardrailCollector(deployment_id, guardrail_enforcer=None)

# Collect guardrail metrics (rate-limit, auth, output-validation, audit)
metrics = collector.collect_guardrail_metrics()
# Returns: {"rate-limit": GuardrailDetail, "auth": GuardrailDetail, ...}

# Collect audit events
events = collector.collect_audit_events(limit=100)
# Returns: [AuditEvent, ...]

# Collect blocked requests (filtered from audit trail)
blocks = collector.collect_blocked_requests(limit=20)
# Returns: [AuditEvent, ...]
```

**Guardrail Metrics (per guardrail):**
```python
class GuardrailDetail:
    guardrail_type: str          # "rate-limit", "auth", "output-validation", "audit"
    requests_total: int
    requests_blocked: int
    error_rate: float
    latency_p50_ms: float        # Percentile latencies
    latency_p95_ms: float
    latency_p99_ms: float
```

### `event_pusher.py` (Event Push to Master)
Pushes critical events to Master in real-time:

**Interface:**
```python
pusher = EventPusher(deployment_id, master_host, master_port)

# Push critical events
await pusher.push_rate_limit_exceeded(model_id, current, limit)
await pusher.push_auth_block(model_id, tool_name, reason)
await pusher.push_cost_alert(cost_today, cost_limit)
await pusher.push_anomaly(anomaly_type, description, severity)
```

**Features:**
- Retry queue with max 3 retries for failed pushes
- Background retry loop (configurable interval, default 10 sec)
- Non-blocking (uses asyncio task)

### `dashboard.html` (Frontend)
Single-page app with Liquid Glass theme:

**Sections:**
1. **Header:** Back button, deployment name, status indicator
2. **Health Status:** 6 KPIs (status, uptime, requests/hr, error rate, cost today, cost month)
3. **Guardrails Metrics:** Cards for each guardrail showing requests, blocks, error rate, latencies
4. **Charts:** Request trends, error trends, cost breakdown (with Chart.js)
5. **Audit Trail:** Live feed of last 50 events
6. **Model Tier Usage:** Breakdown of requests/cost per model tier

---

## Integration with Phase 3 Guardrails

The `GuardrailCollector` automatically discovers and collects metrics from all Phase 3 guardrails by:

1. **Interface inspection:** Looks for `.getMetrics()` method on guardrail objects
2. **Type detection:** Identifies guardrail type by class name:
   - `RateLimitGuardrail` → `"rate-limit"`
   - `AuthorizationGuardrail` → `"auth"`
   - `OutputValidationGuardrail` → `"output-validation"`
   - `AuditTrailGuardrail` → `"audit"`

3. **Metric extraction:** Parses raw metrics into standardized `GuardrailDetail` objects with latency percentiles

---

## Configuration Files

### Environment Variables
Set these before starting the admin dashboard:

```bash
export DEPLOYMENT_ID="neo-toshiba"       # This deployment's ID
export MASTER_HOST="192.168.1.1"         # Master dashboard IP/hostname
export MASTER_PORT=8000                  # Master dashboard port (usually 8000)
```

### Startup Script (`start.sh`)
Handles:
- Creating virtual environment
- Installing dependencies
- Setting defaults for env vars
- Running uvicorn on port 8001 with auto-reload

---

## Testing

### Start locally
```bash
export DEPLOYMENT_ID="test-instance"
export MASTER_HOST="127.0.0.1"
export MASTER_PORT=8000

bash start.sh
# Runs on http://localhost:8001
```

### Health check
```bash
curl http://localhost:8001/health
```

### Get metrics (what Master pulls)
```bash
curl http://localhost:8001/metrics | jq .
```

### Get dashboard data
```bash
curl http://localhost:8001/api/dashboard | jq .
```

### Get recent events
```bash
curl http://localhost:8001/events?limit=10 | jq .
```

### Simulate rate limit alert
```bash
curl -X POST http://localhost:8001/notify/rate_limit_exceeded \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek-tier1",
    "current": 1050,
    "limit": 1000
  }'
```

---

## Deployment Targets

### neo-toshiba (Docker)
```bash
# Copy to instance
scp -r ./admin_dashboard openclaw@192.168.1.33:/opt/openclaw/

# SSH and run
ssh openclaw@192.168.1.33
cd /opt/openclaw/admin_dashboard

export DEPLOYMENT_ID="neo-toshiba"
export MASTER_HOST="192.168.1.1"
export MASTER_PORT=8000

bash start.sh
```

### mba2 (macOS)
```bash
# Copy to instance
scp -r ./admin_dashboard sarah@192.168.1.56:~/openaclaw/

# SSH and run
ssh sarah@192.168.1.56
cd ~/openclaw/admin_dashboard

export DEPLOYMENT_ID="mba2"
export MASTER_HOST="192.168.1.1"
export MASTER_PORT=8000

bash start.sh
```

### agent3 (future)
```bash
# Same pattern once deployed
```

---

## Phase 4: Integration Tasks

Once Admin Dashboard is running on all instances:

1. **Wire Guardrail Metrics**
   - Ensure Phase 3 guardrails are initialized with `.getMetrics()` interface
   - Test `/metrics` endpoint returns proper guardrail data

2. **Set Up Metric Sync Cron (Master)**
   ```bash
   # On VM, add to crontab -e:
   */5 * * * * curl -s http://192.168.1.33:8001/metrics | \
     curl -X POST -d @- http://localhost:8000/api/metrics/neo-toshiba 2>&1 >> /tmp/mc_sync.log
   ```

3. **Test End-to-End**
   - Start Master Dashboard: `http://localhost:8000`
   - Start Admin Dashboard: `http://localhost:8001`
   - Click deployment card on Master → should link to Admin Dashboard
   - Verify metrics update every 5 minutes
   - Trigger critical event on Admin → should appear on Master within seconds

4. **Deploy to All Instances**
   - Copy to neo-toshiba, mba2, agent3
   - Start on each via systemd/LaunchAgent
   - Update crons for metric sync

---

## Troubleshooting

### Dashboard shows "Offline"
1. Check Master is running: `curl http://localhost:8000/health`
2. Check Admin is running: `curl http://localhost:8001/health`
3. Check network connectivity: `ping 192.168.1.33`

### Metrics not updating
1. Check `/metrics` endpoint accessible: `curl http://localhost:8001/metrics`
2. Check Master cron is running: `cat /tmp/mc_sync.log`
3. Check consecutive failures: `curl http://localhost:8000/status`

### Events not pushing to Master
1. Check EventPusher initialized: `curl http://localhost:8001/status`
2. Check Master receiving events: `curl http://localhost:8000/api/events`
3. Check Master network accessible: `curl http://<MASTER_HOST>:<MASTER_PORT>/health`

### Guardrail metrics empty
1. Ensure Phase 3 guardrails initialized on startup
2. Check guardrail implements `.getMetrics()` interface
3. Check guardrail_enforcer is passed to collector: `collector = GuardrailCollector(deployment_id, guardrail_enforcer=<your enforcer>)`

---

## Monitoring

### Check admin dashboard health
```bash
curl http://localhost:8001/status | jq .
```

### View recent events
```bash
curl http://localhost:8001/events?limit=20 | jq .
```

### View all guardrail metrics
```bash
curl http://localhost:8001/metrics | jq '.guardrails'
```

---

## Development

### Run with auto-reload
```bash
bash start.sh
# Already enabled in start.sh
```

### Access API docs
```
http://localhost:8001/docs  (Swagger UI)
http://localhost:8001/redoc (ReDoc)
```

### Check logs
```bash
# If running in foreground, see logs in terminal
# If running as background service, check service logs:
tail -f ~/openclaw/admin_dashboard/logs/admin.log
```

---

## Files

```
admin_dashboard/
├── __init__.py                  # Package init
├── app.py                       # FastAPI application (port 8001)
├── models.py                    # Pydantic models
├── guardrail_collector.py       # Collects guardrail metrics
├── event_pusher.py              # Pushes events to Master
├── dashboard.html               # Frontend (Liquid Glass theme)
├── requirements.txt             # Python dependencies
├── start.sh                     # Startup script
└── README.md                    # This file
```

---

**Summary:** Admin Dashboard provides detailed per-deployment monitoring with real-time guardrail metrics, audit trails, and critical event alerts. Runs on port 8001 on each instance, reports to Master on port 8000 every 5 minutes, and triggers alerts immediately for critical events.

Built with ❤️ for OpenClaw AaaS monitoring (Phase 4.1).
