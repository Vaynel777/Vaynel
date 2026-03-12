# Phase 4 Implementation Guide - Integration & Deployment

## Overview

Phase 4 deploys the Admin Dashboard template (Phase 3) to all 3 instances and sets up automated metric collection on the Master Dashboard.

**Current Status**: ✅ Phase 3 Complete | ⏳ Phase 4 Ready to Deploy

---

## Architecture Recap

```
Master Dashboard (Port 8000)
├── Frontend: dashboard.html (overview of all 3 instances)
├── Backend: app.py (FastAPI)
├── Database: SQLite (metrics_history, events, sync_status)
├── Aggregator: aggregator.py (receives metrics from instances)
└── Cron: metric_collector_cron.py (polls /metrics every 5 min)

Each Instance (Port 8001)
├── Admin Dashboard Frontend: dashboard.html (detailed local view)
├── Backend: app.py (FastAPI)
├── Collectors: guardrail_collector.py (from Phase 3 guardrails)
├── Pusher: event_pusher.py (sends critical events to Master)
└── Models: models.py (Pydantic validation)
```

---

## Phase 4 Tasks (Sequential)

### 1. Deploy Admin Dashboard to neo-toshiba

```bash
# On Master Dashboard VM:
cd ~/.openclaw/workspace/mission_control_master/phase4_integration

# Make deploy script executable
chmod +x deploy_admin_dashboards.sh

# Run deployment (deploys to all 3 instances)
./deploy_admin_dashboards.sh
```

**What this does:**
- SSHs into neo-toshiba (`openclaw@192.168.1.33`)
- Copies admin_dashboard/ to `/opt/admin_dashboard`
- Creates startup wrapper with `DEPLOYMENT_ID=neo-toshiba`
- Starts admin dashboard on port 8001
- Sets `MASTER_HOST=127.0.0.1` (change to your Master IP if remote)

**Verify:**
```bash
curl http://192.168.1.33:8001/health
# Expected: {"status":"ok","deployment_id":"neo-toshiba",...}
```

---

### 2. Deploy Admin Dashboard to mba2

The `deploy_admin_dashboards.sh` script handles all 3 instances automatically.

**Verify:**
```bash
curl http://192.168.1.56:8001/health
# Expected: {"status":"ok","deployment_id":"mba2",...}
```

---

### 3. Deploy Admin Dashboard to agent3

Same script, all 3 instances deployed in one go.

**Verify:**
```bash
curl http://192.168.1.100:8001/health
# Expected: {"status":"ok","deployment_id":"agent3",...}
```

---

### 4. Setup Metric Collection Cron

```bash
# On Master Dashboard VM:
cd ~/.openclaw/workspace/mission_control_master/phase4_integration

# Make cron setup script executable
chmod +x setup_cron.sh

# Install cron job
./setup_cron.sh
```

**What this does:**
- Makes `metric_collector_cron.py` executable
- Adds cron entry: `*/5 * * * * /path/to/metric_collector_cron.py >> /var/log/admin_dashboard_cron.log 2>&1`
- Creates log file for monitoring

**Verify:**
```bash
crontab -l | grep metric_collector
# Should see the cron entry

# Or manually run once:
python3 ~/.openclaw/workspace/mission_control_master/phase4_integration/metric_collector_cron.py
```

---

### 5. End-to-End Testing

#### Test 1: Check Master Dashboard sees instances

```bash
# Start Master Dashboard (if not already running)
cd ~/.openclaw/workspace/mission_control_master
bash start.sh

# Open in browser:
http://localhost:8000
```

**Expected:**
- 3 deployment cards showing (neo-toshiba, mba2, agent3)
- Initially showing "offline" or "unknown" status

#### Test 2: Manually trigger metric collection

```bash
# Run the cron script manually:
python3 ~/.openclaw/workspace/mission_control_master/phase4_integration/metric_collector_cron.py

# Watch the output:
# ✅ Polled neo-toshiba: 200
# ✅ Polled mba2: 200
# ✅ Polled agent3: 200
# 📤 Posted metrics to Master for neo-toshiba
# 📤 Posted metrics to Master for mba2
# 📤 Posted metrics to Master for agent3
```

#### Test 3: Refresh Master Dashboard

```bash
# Go to http://localhost:8000 in browser
# You should see:
# - Deployment cards showing "healthy" or "degraded"
# - KPI boxes updating with metrics
# - Guardrail status showing blocks/errors
# - Recent events appearing
```

#### Test 4: Click a deployment card to drill down

```bash
# From Master Dashboard (http://localhost:8000)
# Click on a deployment card (neo-toshiba, mba2, or agent3)
# Should redirect to:
# http://192.168.1.33:8001  (neo-toshiba)
# http://192.168.1.56:8001  (mba2)
# http://192.168.1.100:8001 (agent3)

# You should see:
# - Health status (uptime, errors, costs)
# - Guardrail breakdown (rate-limit, auth, output-validation, audit)
# - Audit trail (recent events)
# - Model tier usage
# - Request/error/cost charts
```

#### Test 5: Trigger a critical event

```bash
# From neo-toshiba admin dashboard:
curl -X POST "http://192.168.1.33:8001/notify/rate_limit_exceeded?model_id=tier0-codex&current=1050&limit=1000"

# This should:
# 1. Trigger event_pusher on neo-toshiba
# 2. POST to Master's /api/events endpoint
# 3. Event appears in Master Dashboard's "Recent Critical Events" feed
```

---

## File Structure

```
mission_control_master/
├── app.py                          (Master backend)
├── dashboard.html                  (Master frontend)
├── database.py                     (SQLite)
├── aggregator.py                   (Polling + event receiver)
├── models.py                       (Pydantic types for Master)
├── deployments.json                (Instance config)
├── requirements.txt                (Python deps)
├── start.sh                        (Master startup)
├── admin_dashboard/
│   ├── app.py                      (Admin backend)
│   ├── dashboard.html              (Admin frontend)
│   ├── models.py                   (Pydantic types for Admin)
│   ├── guardrail_collector.py      (Metric collector)
│   ├── event_pusher.py             (Event pusher)
│   ├── requirements.txt
│   ├── start.sh
│   └── __init__.py
└── phase4_integration/
    ├── metric_collector_cron.py    (Runs every 5 min on Master)
    ├── deploy_admin_dashboards.sh  (Deploy to all 3 instances)
    ├── setup_cron.sh               (Install cron job)
    └── README.md                   (This file)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Master Dashboard running on port 8000
- [ ] Admin Dashboard code complete (Phase 3)
- [ ] SSH keys configured for neo-toshiba, mba2, agent3
- [ ] Network connectivity verified to all instances

### Deployment

- [ ] Run `deploy_admin_dashboards.sh` (deploys to all 3)
- [ ] Verify each instance running (curl /health)
- [ ] Run `setup_cron.sh` to install metric cron job
- [ ] Verify cron job in crontab

### Post-Deployment Testing

- [ ] Master Dashboard shows all 3 instances
- [ ] Manually run metric_collector_cron.py
- [ ] Verify metrics appear on Master Dashboard
- [ ] Click deployment card and view Admin Dashboard
- [ ] Trigger critical event and verify it appears on Master

---

## Troubleshooting

### Admin Dashboard not starting on instance

```bash
# SSH to instance
ssh openclaw@192.168.1.33

# Check logs
tail -50 /opt/admin_dashboard/admin_dashboard.log

# Try starting manually
cd /opt/admin_dashboard
bash start.sh
```

### Cron job not running

```bash
# Check crontab
crontab -l | grep metric_collector

# Check system logs
grep CRON /var/log/system.log | tail -20

# Check if Python script is executable
ls -la ~/.openclaw/workspace/mission_control_master/phase4_integration/metric_collector_cron.py

# Try running manually
python3 ~/.openclaw/workspace/mission_control_master/phase4_integration/metric_collector_cron.py
```

### Metrics not appearing on Master Dashboard

```bash
# Check Master logs
tail -50 ~/.openclaw/workspace/mission_control_master/logs/*.log

# Verify Admin Dashboard is accessible
curl http://192.168.1.33:8001/metrics

# Check if metrics are being posted to Master
curl http://localhost:8000/status | jq .

# Run cron script manually with debug
python3 -u ~/.openclaw/workspace/mission_control_master/phase4_integration/metric_collector_cron.py
```

### Admin Dashboard can't reach Master

**Issue**: Admin Dashboard can't connect to Master for event pushing

**Solution**:
1. Verify `MASTER_HOST` is set correctly (should be Master's IP, not 127.0.0.1)
2. Check firewall allows port 8000 from instances
3. Verify Master is running: `curl http://[MASTER_IP]:8000/health`

---

## Next Steps

### Immediate

1. **Deploy Phase 3 Admin Dashboards** to all 3 instances
2. **Setup cron job** for metric collection
3. **Test end-to-end** using testing checklist above

### Future Enhancements

- [ ] Add time-series data to Admin Dashboard (chart history)
- [ ] Implement drill-down from Master to Admin (currently manual URL)
- [ ] Add alerting rules (e.g., "alert if error rate > 5%")
- [ ] Setup LaunchAgent on instances to auto-restart on crash
- [ ] Add SSL/TLS for cross-instance communication
- [ ] Implement authentication for dashboard access
- [ ] Add webhook integrations (Slack, PagerDuty, etc.)

---

## Integration Points

### Master Dashboard ↔ Admin Dashboard

**Polling (every 5 min):**
- Master's `metric_collector_cron.py` polls Admin's `/metrics` endpoint
- Stores in Master's SQLite `metrics_history` table
- Frontend auto-refreshes and displays aggregated data

**Event Pushing (real-time):**
- Admin Dashboard detects critical events
- Calls `event_pusher.push_event()` which POSTs to Master's `/api/events`
- Master stores in `events` table
- Master frontend shows in "Recent Critical Events" feed

**Cross-Instance Communication:**
- Admin Dashboard at http://[instance-ip]:8001 is public (accessible from Master)
- Master Dashboard at http://[master-ip]:8000 must be accessible from instances
- Both use standard HTTP/JSON (no persistent connections)

---

## Configuration

### Master Dashboard

Edit `mission_control_master/deployments.json`:

```json
{
  "deployments": [
    {
      "id": "neo-toshiba",
      "host": "192.168.1.33",
      "metrics_port": 8001,
      "admin_port": 8001,
      "tiers": ["tier0-codex", "tier1-deepseek", "tier2-deepseek"]
    },
    ...
  ]
}
```

### Admin Dashboard

Environment variables (set in `start_with_config.sh` during deployment):

```bash
export DEPLOYMENT_ID="neo-toshiba"           # Instance name
export MASTER_HOST="192.168.1.100"           # Master IP (change if remote)
export MASTER_PORT=8000                      # Master port
```

### Cron Job

Edit `phase4_integration/metric_collector_cron.py`:

```python
DEPLOYMENTS = [
    {"id": "neo-toshiba", "host": "192.168.1.33", "port": 8001},
    {"id": "mba2", "host": "192.168.1.56", "port": 8001},
    {"id": "agent3", "host": "192.168.1.100", "port": 8001},
]
MASTER_URL = "http://localhost:8000/api/metrics"
```

---

## Performance & Reliability

### Bandwidth

- **Polling (5-min interval)**: ~2-4 MB/day per instance
  - Each metrics call ~40-50 KB (includes guardrail stats, audit log)
  - 288 calls/day × 50 KB = ~14 MB/day for 3 instances

- **Event pushing**: Minimal (~1 KB per critical event)

### Failure Modes

- **Instance offline**: Polling times out (10s timeout), Master retries next cycle
- **Master offline**: Admin Dashboard queues events, retries with exponential backoff
- **Network partition**: No data loss (polling survives), just delayed

### Auto-Recovery

- **Admin Dashboard crash**: Restart manually or via LaunchAgent
- **Cron job failure**: No impact to dashboards (just delayed metrics)
- **Master crash**: Instances continue running, sync pauses until Master restarts

---

## Monitoring

### Check Master Status

```bash
curl http://localhost:8000/status | jq .
```

Response:
```json
{
  "timestamp": "2026-03-12T...",
  "registered_deployments": 3,
  "online_deployments": 3,
  "aggregator_running": true,
  "last_sync": "2026-03-12T..."
}
```

### Check Cron Job Status

```bash
# View logs
tail -100 /var/log/admin_dashboard_cron.log

# Count successes
grep "✅" /var/log/admin_dashboard_cron.log | wc -l

# Count errors
grep "❌\|⚠️" /var/log/admin_dashboard_cron.log | wc -l
```

### Check Instance Health

```bash
# From Master VM
for host in 192.168.1.33 192.168.1.56 192.168.1.100; do
  echo "Checking $host:8001..."
  curl -s http://$host:8001/health | jq .
done
```

---

## Estimated Timeline

- **Deployment**: 10-15 minutes (script runs 3-5 min per instance)
- **Cron setup**: 2-3 minutes
- **Testing**: 10-15 minutes
- **Total**: 25-35 minutes

---

## Built By

Claude Code (AI) for Dominic
Date: 2026-03-12
Phase: 4 (Integration & Deployment)

---
