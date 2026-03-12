# Phase 4.1 Integration & Deployment

**Status:** Ready for Implementation
**Date:** 2026-03-12
**Target:** Complete end-to-end monitoring (Master + Admin Dashboards + Real-time Events)

---

## Checklist

### Phase 3 Completion ✅
- [x] Admin Dashboard FastAPI backend (`app.py`)
- [x] Guardrail metrics collector (`guardrail_collector.py`)
- [x] Event pusher for Master (`event_pusher.py`)
- [x] Admin Dashboard frontend (`dashboard.html`)
- [x] Dependencies and startup (`requirements.txt`, `start.sh`)
- [x] Documentation (`README.md`)

### Phase 4 Tasks

#### 1. Local Testing
- [ ] Start Master Dashboard: `cd ~/mission_control_master && bash start.sh`
- [ ] Start Admin Dashboard: `cd ~/mission_control_master/admin_dashboard && DEPLOYMENT_ID=test MASTER_HOST=127.0.0.1 MASTER_PORT=8000 bash start.sh`
- [ ] Verify Master health: `curl http://localhost:8000/health`
- [ ] Verify Admin health: `curl http://localhost:8001/health`
- [ ] Simulate metrics: `curl http://localhost:8001/metrics | jq .`
- [ ] Simulate event: `curl -X POST http://localhost:8001/notify/rate_limit_exceeded -d '{"model_id":"test","current":1050,"limit":1000}' -H "Content-Type: application/json"`
- [ ] Verify event on Master: `curl http://localhost:8000/api/events | jq .`

#### 2. Deployment to Instances
- [ ] Deploy to neo-toshiba: `bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 192.168.1.1 8000`
- [ ] Deploy to mba2: `bash admin_dashboard/deploy.sh mba2 192.168.1.56 192.168.1.1 8000`
- [ ] Verify health on neo-toshiba: `curl http://192.168.1.33:8001/health`
- [ ] Verify health on mba2: `curl http://192.168.1.56:8001/health`

#### 3. Metric Sync Setup
- [ ] Start cron on Master VM: Runs every 5 minutes to pull metrics from all 3 instances
- [ ] Verify cron logs: `tail -f /tmp/mc_sync.log`
- [ ] Check that metrics appear on Master dashboard

#### 4. Event Pusher Integration
- [ ] Wire Phase 3 guardrails to event pusher
- [ ] Trigger critical event on instance: `curl -X POST http://192.168.1.33:8001/notify/rate_limit_exceeded ...`
- [ ] Verify event appears on Master within seconds

#### 5. End-to-End Testing
- [ ] Open Master Dashboard: http://localhost:8000
- [ ] Verify all 3 deployment cards show status
- [ ] Click deployment card → navigates to admin dashboard at http://<host>:8001
- [ ] Admin dashboard shows detailed guardrail metrics
- [ ] Master dashboard updates every 5 seconds
- [ ] New events appear in Master within 1 second

#### 6. Documentation
- [ ] Update `~/openaclaw/workspace/memory/aaas.md` with Phase 4 completion notes
- [ ] Update `~/openclaw/workspace/memory/changelog.md` with session notes
- [ ] Create deployment guide for each instance

---

## Detailed Steps

### 1. Local Testing (5-10 minutes)

**Terminal 1: Start Master Dashboard**
```bash
cd ~/mission_control_master
bash start.sh
# Expected: 🚀 Master Dashboard starting on port 8000
# Open http://localhost:8000 in browser
```

**Terminal 2: Start Admin Dashboard**
```bash
cd ~/mission_control_master/admin_dashboard
export DEPLOYMENT_ID="test-instance"
export MASTER_HOST="127.0.0.1"
export MASTER_PORT=8000
bash start.sh
# Expected: ✅ Admin Dashboard ready for test-instance
# Open http://localhost:8001 in browser
```

**Terminal 3: Test API calls**

Health checks:
```bash
# Master health
curl http://localhost:8000/health
# Expected: {"status":"ok","registered_deployments":3,"aggregator_running":true}

# Admin health
curl http://localhost:8001/health
# Expected: {"status":"ok","deployment_id":"test-instance","timestamp":"..."}
```

Get metrics:
```bash
# Get admin metrics (what Master pulls)
curl http://localhost:8001/metrics | jq .
# Expected: deployment_id, timestamp, health_status, uptime_percent, guardrails, etc.
```

Simulate critical event:
```bash
# Trigger rate limit alert
curl -X POST "http://localhost:8001/notify/rate_limit_exceeded" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek-tier1",
    "current": 1050,
    "limit": 1000
  }'
# Expected: {"status":"notified"}

# Verify on Master (wait a few seconds for push to complete)
curl http://localhost:8000/api/events | jq '.critical_events[0]'
# Expected: rate_limit_exceeded event with timestamp from this second
```

---

### 2. Deploy to Instances (15-20 minutes)

**Deploy to neo-toshiba (Docker):**
```bash
cd ~/mission_control_master
bash admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 192.168.1.1 8000
# This will:
# - Copy admin_dashboard/ to /opt/openclaw/admin_dashboard
# - Install dependencies
# - Set up systemd service
# - Configure cron for 5-min metric sync
# - Create log directory
```

**Deploy to mba2 (macOS):**
```bash
bash admin_dashboard/deploy.sh mba2 192.168.1.56 192.168.1.1 8000
# This will:
# - Copy admin_dashboard/ to ~/openclaw/admin_dashboard
# - Install dependencies
# - Set up LaunchAgent
# - Configure cron for 5-min metric sync
# - Create log directory
```

**Verify deployments:**
```bash
# neo-toshiba
curl http://192.168.1.33:8001/health
# Expected: {"status":"ok","deployment_id":"neo-toshiba",...}

# mba2
curl http://192.168.1.56:8001/health
# Expected: {"status":"ok","deployment_id":"mba2",...}
```

---

### 3. Metric Sync Setup (5 minutes)

On Master VM (where port 8000 runs), ensure cron jobs are set up:

```bash
# View current cron
crontab -l

# Add if not already present (this syncs metrics every 5 minutes)
# For neo-toshiba (Docker)
*/5 * * * * curl -s http://192.168.1.33:8001/metrics | curl -X POST -d @- -H "Content-Type: application/json" http://localhost:8000/api/metrics/neo-toshiba 2>&1 >> /tmp/mc_sync.log

# For mba2
*/5 * * * * curl -s http://192.168.1.56:8001/metrics | curl -X POST -d @- -H "Content-Type: application/json" http://localhost:8000/api/metrics/mba2 2>&1 >> /tmp/mc_sync.log

# To add these:
crontab -e
# Add the 2 lines above, save and exit
```

**Verify cron is running:**
```bash
# Watch sync log
tail -f /tmp/mc_sync.log
# Expected: curl output every 5 minutes showing metric post success
```

---

### 4. Event Pusher Integration (5 minutes)

When a critical guardrail event occurs on an instance, the `EventPusher` automatically sends it to Master.

**Test manually:**
```bash
# On instance (or via curl)
curl -X POST "http://192.168.1.33:8001/notify/rate_limit_exceeded" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek-tier1",
    "current": 1050,
    "limit": 1000
  }'

# On Master, check events (should arrive within 1 second)
curl http://localhost:8000/api/events?deployment_id=neo-toshiba | jq '.critical_events[0]'
# Expected: {"deployment_id":"neo-toshiba","event_type":"rate_limit_exceeded",...}
```

---

### 5. End-to-End Testing (10 minutes)

**1. Open Master Dashboard**
- Navigate to http://localhost:8000
- Should see 3 deployment cards: neo-toshiba, mba2, agent3

**2. Check deployment status**
- If metrics already synced: cards should show "online" with uptime %
- If not yet synced: cards show "offline" (normal, wait 5 min for cron)
- KPIs should update as metrics come in

**3. Click deployment card**
- Click neo-toshiba card
- Should navigate to http://192.168.1.33:8001 (admin dashboard)
- Shows detailed guardrail metrics for this deployment

**4. Trigger event and watch propagation**
- On admin dashboard, trigger critical event: `/notify/rate_limit_exceeded`
- Switch back to Master dashboard
- New event should appear in "Recent Critical Events" within 1 second
- Severity badge should show "critical"

**5. Auto-refresh test**
- Both dashboards should auto-refresh every 5 seconds
- Check console doesn't have errors

---

## Troubleshooting

### "Admin Dashboard shows offline"
1. Check Master is running: `curl http://localhost:8000/health`
2. Check Admin is running: `curl http://localhost:8001/health`
3. Check network: `ping 192.168.1.33`
4. Check Master can reach Admin: `curl http://192.168.1.33:8001/health`

### "Metrics not updating on Master"
1. Check cron is running: `crontab -l`
2. Check cron log: `tail /tmp/mc_sync.log`
3. Check metric endpoint on Admin: `curl http://192.168.1.33:8001/metrics`
4. Check Master received metric: `curl http://localhost:8000/api/metrics/neo-toshiba`

### "Events not pushing to Master"
1. Check EventPusher initialized: `curl http://192.168.1.33:8001/status` (should show pusher_initialized: true)
2. Check retry queue: look at queued_events count
3. Check network: `ping 192.168.1.1` (Master host from instance)
4. Check Master firewall: `curl http://192.168.1.1:8000/health` from instance

### "Guardrail metrics empty"
1. Check Phase 3 guardrails are initialized
2. Check guardrails implement `.getMetrics()` interface
3. Check GuardrailCollector has access to guardrail_enforcer
4. Check app.py startup logs for collector errors

---

## File Structure After Phase 4

```
~/.openclaw/workspace/mission_control_master/
├── app.py                           # Master Dashboard backend
├── models.py                        # Master models
├── database.py                      # Master database
├── aggregator.py                    # Master aggregator
├── dashboard.html                   # Master frontend
├── deployments.json                 # Deployment config
├── requirements.txt                 # Master dependencies
├── start.sh                         # Master startup
├── README.md                        # Master docs
├── QUICKSTART.md
├── PHASE_4_1_STATUS.md
├── PHASE_4_INTEGRATION.md           # This file
├── data.db                          # Master database (auto-created)
└── admin_dashboard/
    ├── app.py                       # Admin backend (port 8001)
    ├── models.py                    # Admin models
    ├── guardrail_collector.py       # Guardrail metric collection
    ├── event_pusher.py              # Event push to Master
    ├── dashboard.html               # Admin frontend
    ├── requirements.txt
    ├── start.sh
    ├── deploy.sh                    # Deployment script
    ├── README.md
    ├── __init__.py
    └── (on instances) venv/         # Virtual env
                      logs/          # Log files
                      admin-dashboard.service (systemd) or .plist (macOS)
```

---

## Success Criteria

Phase 4 is complete when:

1. ✅ Master Dashboard shows all 3 deployments with correct status
2. ✅ Each deployment card links to detailed admin dashboard (port 8001)
3. ✅ Admin dashboard displays guardrail metrics with correct values
4. ✅ Metrics sync every 5 minutes (verify via Master `/api/metrics/{id}`)
5. ✅ Critical events push in real-time (< 1 second to Master)
6. ✅ Both dashboards auto-refresh without errors
7. ✅ All 3 instances can run admin dashboard (neo-toshiba, mba2, agent3)
8. ✅ Logs are available for debugging (`/tmp/mc_sync.log`, `~/openclaw/admin_dashboard/logs/`)

---

## Next: Post-Phase 4

Once Phase 4 is complete:

1. **Ongoing monitoring:** Dashboard running 24/7, receiving metrics every 5 min, events in real-time
2. **Alerting:** Can set up Telegram/email alerts for critical events (integrate with existing Telegram bot)
3. **Historical analysis:** Time-series database can be queried for trends
4. **Scaling:** If more instances added (agent3+), just add to `deployments.json` and re-run crons

---

**Reference:** See `README.md` for full documentation, `QUICKSTART.md` for quick start, and `PHASE_4_1_STATUS.md` for architectural decisions.

Built with ❤️ for OpenClaw AaaS monitoring.
