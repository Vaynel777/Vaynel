# Mission Control Master Dashboard - Quick Start

## 30-Second Start

```bash
cd ~/.openclaw/workspace/mission_control_master
bash start.sh
```

Then open **http://localhost:8000** in your browser.

---

## What You'll See

- 3 deployment cards (neo-toshiba, mba2, agent3) showing as "offline" (expected)
- 6 KPIs showing 0 (will populate when instances report metrics)
- Empty events feed
- "Last sync" showing current time

This is **normal** — instances will start reporting metrics once Phase 3 Admin Dashboards are deployed.

---

## Test the API

### Health Check
```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"ok","registered_deployments":3,"aggregator_running":true}`

### Get All Deployments
```bash
curl http://localhost:8000/api/deployments | jq .
```

### Check Sync Status
```bash
curl http://localhost:8000/status | jq .
```

### Simulate Metrics from an Instance
```bash
curl -X POST "http://localhost:8000/api/metrics/neo-toshiba" \
  -H "Content-Type: application/json" \
  -d '{
    "uptime_percent": 99.5,
    "health_status": "healthy",
    "rate_limit_current": 450,
    "rate_limit_max": 1000,
    "rate_limit_percent": 45.0,
    "tokens_used_today": 50000,
    "cost_usd_today": 1.50,
    "cost_usd_month": 35.00,
    "error_count_hour": 5,
    "error_count_day": 23,
    "active_models": 4,
    "total_requests_hour": 2000,
    "guardrails": {}
  }'
```

**Watch dashboard update** — refresh http://localhost:8000

### Send a Critical Event
```bash
curl -X POST "http://localhost:8000/api/events?deployment_id=neo-toshiba" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "rate_limit_exceeded",
    "severity": "critical",
    "message": "DeepSeek tier1 rate limit exceeded",
    "metadata": {"limit": 1000, "current": 1050}
  }'
```

**Events will appear** in "Recent Critical Events" feed

---

## File Locations

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend (the server) |
| `dashboard.html` | Frontend (what you see) |
| `database.py` | SQLite database code |
| `aggregator.py` | Polling + event receiver |
| `deployments.json` | Instance configuration |
| `README.md` | Full documentation |
| `data.db` | Database (auto-created) |

---

## Stop the Server

Press **Ctrl+C** in the terminal where `bash start.sh` is running.

---

## Next Steps (Tomorrow)

See **PHASE_4_1_STATUS.md** for:
- Phase 3 Admin Dashboard plan
- Phase 4 Integration plan
- Estimated effort

Or read **README.md** for:
- Full API documentation
- Database schema
- Architecture details
- Troubleshooting

---

## Quick Notes

- **Master Dashboard** = http://localhost:8000 (overview of all 3 instances)
- **Admin Dashboard** = http://[instance-ip]:8001 (per-deployment details) — **Coming Phase 3**
- **API Docs** = http://localhost:8000/docs (Swagger)
- **Default port** = 8000 (configurable in app.py if needed)

---

**Ready to go!** 🚀
