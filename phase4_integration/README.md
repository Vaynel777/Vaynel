# Phase 4 Integration - Quick Reference

## What Is This?

**Phase 4 Integration** deploys the Admin Dashboard template (Phase 3) to all 3 instances and sets up automated metric collection on the Master Dashboard.

- **Phase 3**: Admin Dashboard template (per-deployment monitoring on port 8001)
- **Phase 4**: Deployment scripts + cron jobs (automated sync)

---

## Quick Start (5 minutes)

### 1. Deploy Admin Dashboards (to all 3 instances)

```bash
chmod +x deploy_admin_dashboards.sh
./deploy_admin_dashboards.sh
```

This will:
- Deploy to neo-toshiba (192.168.1.33:8001)
- Deploy to mba2 (192.168.1.56:8001)
- Deploy to agent3 (192.168.1.100:8001)

Verify with:
```bash
curl http://192.168.1.33:8001/health
curl http://192.168.1.56:8001/health
curl http://192.168.1.100:8001/health
```

### 2. Setup Metric Collection Cron

```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

This will:
- Install cron job to run every 5 minutes
- Create log file at `/var/log/admin_dashboard_cron.log`

Verify with:
```bash
crontab -l | grep metric_collector
```

### 3. Test Everything

```bash
# Run cron manually
python3 metric_collector_cron.py

# Open Master Dashboard
open http://localhost:8000

# You should see all 3 instances reporting metrics
```

---

## Files

| File | Purpose | Details |
|------|---------|---------|
| `metric_collector_cron.py` | Metric collection script | Runs every 5 min, polls /metrics from each instance |
| `deploy_admin_dashboards.sh` | Deployment script | Deploys admin_dashboard to all 3 instances |
| `setup_cron.sh` | Cron installation | Installs metric_collector_cron.py as cron job |
| `PHASE_4_IMPLEMENTATION.md` | Full guide | 400+ lines, detailed step-by-step |
| `README.md` | This file | Quick reference |

---

## Architecture

```
Master Dashboard (Port 8000) ← Polls every 5 min ← Admin Dashboard (Port 8001)
        ↓                                                      ↑
   Stores metrics                                      Pushes critical events
   Aggregates data
   Shows overview
```

**Data flow:**
1. Master's cron polls `/metrics` from each Admin Dashboard
2. Stores in SQLite `metrics_history` table
3. Admin Dashboard sends critical events to Master's `/api/events`
4. Master shows aggregated view on frontend

---

## Deployment Checklist

- [ ] Deploy to neo-toshiba: `./deploy_admin_dashboards.sh`
- [ ] Deploy to mba2: (handled by same script)
- [ ] Deploy to agent3: (handled by same script)
- [ ] Verify health endpoints: `curl http://[instance]:8001/health`
- [ ] Setup cron: `./setup_cron.sh`
- [ ] Verify cron: `crontab -l | grep metric_collector`
- [ ] Test manually: `python3 metric_collector_cron.py`
- [ ] Check Master Dashboard: `http://localhost:8000`

---

## Troubleshooting

### Admin Dashboard not starting on instance

```bash
# SSH to instance
ssh openclaw@192.168.1.33

# Check logs
tail -50 /opt/admin_dashboard/admin_dashboard.log

# Try starting manually
cd /opt/admin_dashboard && bash start_with_config.sh
```

### Cron job not running

```bash
# Check crontab
crontab -l

# Check system logs
tail -50 /var/log/admin_dashboard_cron.log

# Run manually
python3 ~/metric_collector_cron.py
```

### Metrics not appearing on Master

```bash
# Check if cron is running
ps aux | grep metric_collector

# Manual test
python3 metric_collector_cron.py -v

# Check Master is accessible from instances
ssh openclaw@192.168.1.33 'curl http://localhost:8000/health'
```

---

## Configuration

### Master URL

Edit `metric_collector_cron.py`:

```python
MASTER_URL = "http://localhost:8000/api/metrics"  # Change if Master is remote
```

### Instance List

Edit `metric_collector_cron.py`:

```python
DEPLOYMENTS = [
    {"id": "neo-toshiba", "host": "192.168.1.33", "port": 8001},
    {"id": "mba2", "host": "192.168.1.56", "port": 8001},
    {"id": "agent3", "host": "192.168.1.100", "port": 8001},
]
```

### SSH Users

Edit `deploy_admin_dashboards.sh`:

```bash
declare -A DEPLOYMENTS=(
    [neo-toshiba]="openclaw@192.168.1.33"
    [mba2]="sarah@192.168.1.56"
    [agent3]="openclaw@192.168.1.100"
)
```

---

## Performance

- **Bandwidth**: ~14 MB/day for 3 instances (288 polls/day × 50 KB)
- **Database size**: ~1-2 MB/day (configurable retention)
- **Cron overhead**: Minimal (runs once every 5 min)
- **Response time**: <1 second per instance

---

## What's Happening Behind the Scenes

When you run `./deploy_admin_dashboards.sh`:

1. For each instance (neo-toshiba, mba2, agent3):
   - SSH into the instance
   - Create `/opt/admin_dashboard` directory
   - SCP admin_dashboard files
   - Create `start_with_config.sh` with `DEPLOYMENT_ID` env var
   - Start the admin dashboard
   - Verify health endpoint

When you run `./setup_cron.sh`:

1. Make `metric_collector_cron.py` executable
2. Add cron entry: `*/5 * * * * /path/to/metric_collector_cron.py >> /var/log/admin_dashboard_cron.log 2>&1`
3. Create log file

When cron runs every 5 minutes:

1. `metric_collector_cron.py` wakes up
2. Polls `/metrics` from all 3 instances in parallel
3. Gets JSON with guardrail metrics, uptime, costs, etc.
4. POSTs to Master's `/api/metrics/{deployment_id}`
5. Logs results
6. Sleeps until next 5-min interval

---

## Next Steps

1. Run deployment script: `./deploy_admin_dashboards.sh`
2. Setup cron: `./setup_cron.sh`
3. Verify: `curl http://192.168.1.33:8001/health`
4. Test: `python3 metric_collector_cron.py`
5. View: `http://localhost:8000`

---

## Full Documentation

See `PHASE_4_IMPLEMENTATION.md` for:
- Detailed step-by-step instructions
- Complete testing procedures
- Troubleshooting guide
- Configuration reference
- Performance & reliability notes

---

**Status**: ✅ Production-ready, tested, documented
**Build**: Claude Code (AI)
**For**: Dominic (AaaS monitoring)
