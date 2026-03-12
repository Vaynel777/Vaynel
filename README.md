# Mission Control Master Dashboard - Phase 4.1
## Advanced Monitoring & Analytics for AaaS Deployments

**Status:** ✅ Phase 1-2 Complete (Master Backend + Frontend)
**Last Updated:** 2026-03-12
**Components Built:**
- ✅ Master Dashboard FastAPI backend (port 8000)
- ✅ Metrics aggregator (5-min hybrid sync)
- ✅ SQLite database schema
- ✅ Master dashboard frontend (Liquid Glass theme)
- ⏳ Admin dashboard template (Phase 3)
- ⏳ Deployment integration (Phase 4)

---

## Quick Start

### Prerequisites
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Master Dashboard
```bash
bash start.sh
# Opens http://localhost:8000
```

Access:
- **Dashboard:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger)
- **Health Check:** http://localhost:8000/health

---

## Architecture Overview

### Master Dashboard (Port 8000) - This Machine (VM)

```
┌─────────────────────────────────────────────────────────────┐
│                 MASTER DASHBOARD (Port 8000)                 │
│                   FastAPI + Liquid Glass UI                  │
├─────────────────────────────────────────────────────────────┤
│                                                                │
│  KPIs (6):                                                    │
│  - Total Cost (Month)                                         │
│  - Rate Limit Blocks (1h)                                     │
│  - Errors (1h)                                                │
│  - Deployments Online / Total                                 │
│  - Critical Alerts                                            │
│  - Average Uptime                                             │
│                                                                │
│  Deployment Cards (3):                                        │
│  - Neo-Toshiba ────────────────┐  (Click → Drill-Down)      │
│  - MBA2 (Sarah) ───────────────┤                             │
│  - Agent 3 ────────────────────┘                             │
│                                                                │
│  Recent Critical Events (Feed)                                │
│  - Rate limit exceeded                                        │
│  - Auth block                                                 │
│  - Cost alert                                                 │
│  - Anomaly detected                                           │
│                                                                │
├─────────────────────────────────────────────────────────────┤
│ BACKEND SERVICES:                                              │
│ - Metrics Aggregator (polls /metrics every 5 min)            │
│ - Critical Event Receiver (HTTP POST from subsets)           │
│ - Database (SQLite, 4 tables: deployments, metrics,          │
│   events, sync_status)                                        │
└─────────────────────────────────────────────────────────────┘
```

### Admin Dashboard (Port 8001) - Per Deployment

```
Deployed on:
- neo-toshiba:8001  (Docker container)
- mba2:8001         (macOS)
- agent3:8001       (Future)

Shows:
- Local guardrail metrics (rate-limit, auth, output-validation, audit)
- Detailed graphs + trends
- Rate limit usage per model
- Auth failures + trends
- Cost per tool
- Audit trail live feed
- Health + error rates

Reports Back to Master:
- Critical events (PUSH, real-time)
- Metric aggregates (PULL, 5-min)
- Health checks (PULL, 1-min)
```

---

## Hybrid Sync Strategy

### 5-Minute Metric Pull (Aggregation)
**What:** Master pulls aggregate metrics from each instance `/metrics` endpoint

**Frequency:** Every 5 minutes

**Data:**
```json
{
  "deployment_id": "neo-toshiba",
  "timestamp": "2026-03-12T12:00:00Z",
  "uptime_percent": 99.5,
  "health_status": "healthy",
  "rate_limit_current": 450,
  "rate_limit_max": 1000,
  "rate_limit_percent": 45.0,
  "tokens_used_today": 50000,
  "cost_usd_today": 1.50,
  "cost_usd_month": 35.00,
  "guardrails": {
    "rate-limit": {
      "requests_total": 1000,
      "requests_blocked": 10,
      "error_rate": 0.01,
      "p50_latency_ms": 45.2,
      "p95_latency_ms": 120.5,
      "p99_latency_ms": 250.0
    },
    "auth": { ... },
    "output-validation": { ... },
    "audit": { ... }
  },
  "error_count_hour": 5,
  "error_count_day": 23,
  "active_models": 4,
  "total_requests_hour": 2000
}
```

**Resources:** ~5-10 KB/request × 3 instances × 12 times/hour = ~2-4 MB/day

### Real-Time Critical Event Push
**What:** Instance sends critical event to Master via HTTP POST

**When:** Immediately on critical guardrail events:
- Rate limit exceeded
- Auth block on sensitive tool
- Cost anomaly detected
- System anomaly detected
- High error rate

**Data:**
```json
{
  "deployment_id": "neo-toshiba",
  "event_type": "rate_limit_exceeded",
  "severity": "critical",
  "message": "DeepSeek tier1 rate limit exceeded (1000/1000 requests in 1min)",
  "metadata": {
    "model_id": "deepseek-tier1",
    "limit": 1000,
    "current": 1050,
    "percent": 105,
    "window_seconds": 60
  }
}
```

**Resources:** Variable (only on critical events), ~1-5 events/hour typical

**Resilience:**
- Polling survives temporary failures (will retry next 5-min cycle)
- Events have retry logic (POST if failed)
- No persistent connections (memory light)

---

## API Endpoints

### Core
- `GET /health` — Master health check
- `GET /status` — Detailed sync status per deployment
- `GET /` — Serve dashboard.html

### Deployments
- `POST /api/deployments` — Register a new deployment
- `GET /api/deployments` — List all deployments with current status

### Metrics
- `GET /api/metrics/{deployment_id}` — Latest metrics snapshot
- `GET /api/metrics/{deployment_id}/history?hours=24` — Time series
- `GET /api/costs/{deployment_id}?days=30` — Cost breakdown by day

### Events
- `GET /api/events?deployment_id=neo-toshiba&limit=50` — Get events
- `POST /api/events?deployment_id=neo-toshiba` — Receive critical event (pushed from subset)

### Dashboard
- `GET /api/dashboard` — Complete data for Master Dashboard frontend

---

## Database Schema

### Deployments
```sql
deployments {
  id: TEXT PRIMARY KEY,
  name: TEXT,
  host: TEXT,
  metrics_port: INT,
  admin_port: INT,
  region: TEXT,
  model_tiers: JSON,
  created_at: TIMESTAMP,
  updated_at: TIMESTAMP
}
```

### Metrics History (Time Series)
```sql
metrics_history {
  id: INT PRIMARY KEY,
  deployment_id: FK,
  timestamp: TEXT,
  uptime_percent: REAL,
  health_status: TEXT,
  rate_limit_current/max/percent: INT/INT/REAL,
  tokens_used_today: INT,
  cost_usd_today/month: REAL,
  error_count_hour/day: INT,
  active_models: INT,
  total_requests_hour: INT,
  guardrails_json: JSON  -- All guardrail metrics
  INDEX: (deployment_id, timestamp DESC)
}
```

### Events (Critical)
```sql
events {
  id: INT PRIMARY KEY,
  deployment_id: FK,
  timestamp: TEXT,
  event_type: TEXT,
  severity: TEXT,
  message: TEXT,
  metadata_json: JSON,
  acknowledged: BOOL
  INDEX: (deployment_id, timestamp DESC)
  INDEX: (event_type)
}
```

### Sync Status (Polling State)
```sql
sync_status {
  deployment_id: FK PRIMARY KEY,
  last_sync_time: TEXT,
  last_sync_status: TEXT,
  last_sync_error: TEXT,
  consecutive_failures: INT
}
```

---

## Configuration

### Deployments (`deployments.json`)
Define instance details:
```json
{
  "deployments": [
    {
      "id": "neo-toshiba",
      "name": "Neo Toshiba",
      "host": "192.168.1.33",
      "metrics_port": 8001,
      "admin_port": 8001,
      "region": "Singapore",
      "model_tiers": ["codex-tier0", "deepseek-tier1", "deepseek-tier2", "deepseek-tier3"]
    }
  ]
}
```

**Note:** Run `python3 init_deployments.py` after updating to register in DB.

---

## Phase 3-4: Admin Dashboard & Integration

### ✅ Phase 3: Admin Dashboard Template
**Deployed on each instance (port 8001), shows:**
- Local guardrail metrics (rate-limit, auth, output-validation, audit)
- Detailed graphs: request trends, error trends, cost breakdown
- Live audit trail feed (last 50 events)
- Health status + error rates
- Model tier breakdown with cost per tier

**Template location:** `admin_dashboard/`
- `app.py` — FastAPI backend (metrics, events, dashboard endpoints)
- `guardrail_collector.py` — Collects metrics from Phase 3 guardrails
- `event_pusher.py` — Pushes critical events to Master in real-time
- `dashboard.html` — Frontend with Liquid Glass theme + Chart.js graphs
- `requirements.txt`, `start.sh`, `README.md` — Setup and docs

**Deployment targets:**
- neo-toshiba (Docker) — `bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 127.0.0.1 8000`
- mba2 (macOS) — `bash admin_dashboard/deploy.sh mba2 192.168.1.56 127.0.0.1 8000`
- agent3 (future) — Same pattern

### ✅ Phase 4: Integration & Deployment
**Completed:**
1. ✅ Metric sync cron (every 5 minutes)
2. ✅ Event pusher (real-time to Master)
3. ✅ Deployment script (`admin_dashboard/deploy.sh`)
4. ✅ End-to-end test suite (`test-e2e.sh`)
5. ✅ Integration guide (`PHASE_4_INTEGRATION.md`)

**Testing:**
```bash
# Local validation (before deploying to instances)
bash test-e2e.sh
# Tests: health checks, API endpoints, event pushing, metric sync, frontend loading

# Deploy to instances
bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 192.168.1.1 8000
bash admin_dashboard/deploy.sh mba2 192.168.1.56 192.168.1.1 8000
```

**Details:** See `PHASE_4_INTEGRATION.md` for full checklist and step-by-step instructions.

---

## Testing

### Start Master
```bash
bash start.sh
```

### Register Test Deployments
```bash
# Already done if running start.sh (uses deployments.json)
curl -X POST http://localhost:8000/api/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "id": "neo-toshiba",
    "name": "Neo Toshiba",
    "host": "192.168.1.33",
    "metrics_port": 8001,
    "admin_port": 8001,
    "region": "Singapore",
    "model_tiers": []
  }'
```

### Simulate Metrics Poll
```bash
curl http://localhost:8000/api/metrics/neo-toshiba
```

### Simulate Critical Event
```bash
curl -X POST "http://localhost:8000/api/events?deployment_id=neo-toshiba" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "rate_limit_exceeded",
    "severity": "critical",
    "message": "Rate limit exceeded on tier1",
    "metadata": {"limit": 1000, "current": 1050}
  }'
```

### View Dashboard
Open http://localhost:8000 in browser

---

## Files

```
mission_control_master/
├── __init__.py                  # Package init
├── app.py                       # FastAPI application (port 8000)
├── models.py                    # Pydantic models
├── database.py                  # SQLite schema + queries
├── aggregator.py                # Metrics polling + event receiver
├── dashboard.html               # Frontend (Liquid Glass theme)
├── deployments.json             # Deployment config
├── init_deployments.py          # Load config into DB
├── requirements.txt             # Python deps
├── start.sh                     # Startup script
├── README.md                    # This file
└── data.db                      # SQLite database (auto-created)
```

---

## Troubleshooting

### Dashboard shows "Offline"
1. Check Master is running: `curl http://localhost:8000/health`
2. Check if deployments registered: `curl http://localhost:8000/api/deployments`
3. Check if instance `/metrics` endpoint reachable
4. View aggregator logs: `tail start.log`

### Metrics not updating
1. Ensure instance has `/metrics` endpoint at configured host:port
2. Check sync status: `curl http://localhost:8000/status`
3. Check consecutive_failures in DB: `sqlite3 mission_control_master/data.db "SELECT * FROM sync_status"`

### Events not showing
1. Check Master received event: `curl http://localhost:8000/api/events`
2. Check event was POSTed correctly from instance

---

## Monitoring

### Check aggregator health
```bash
curl http://localhost:8000/status | jq .
```

### View last 10 metrics
```bash
curl http://localhost:8000/api/metrics/neo-toshiba/history?hours=24 | jq .
```

### View recent events
```bash
curl http://localhost:8000/api/events?limit=20 | jq .
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
http://localhost:8000/docs  (Swagger UI)
http://localhost:8000/redoc (ReDoc)
```

---

**Next steps:** See Phase 3-4 plan above for Admin Dashboard template and deployment integration.

Built with ❤️ for OpenClaw AaaS monitoring.
