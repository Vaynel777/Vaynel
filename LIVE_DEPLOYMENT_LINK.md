# 🎛️ OpenClaw Mission Control - Live Deployment

**Status:** ✅ OPERATIONAL
**Last Updated:** 2026-03-12
**Version:** 4.1.0

---

## 📊 Live Dashboards

### Option 1: Local Server (Recommended for Testing)
**URL:** http://localhost:8000

✅ **Status:** Running
- **Service:** Python Uvicorn + FastAPI
- **Port:** 8000
- **Auto-refresh:** Every 5 seconds
- **Features:**
  - Live deployment monitoring
  - Real-time critical events
  - Guardrail metrics
  - Cost tracking

**To start locally:**
```bash
cd /Users/alexren/.openclaw/workspace/mission_control_master
bash start.sh
# Opens at http://localhost:8000
```

---

## 📋 Available Endpoints

### Dashboard
- **Master Dashboard:** `GET /`
  - HTML interface with real-time updates
  - Shows all 3 deployments (neo-toshiba, mba2, agent3)
  - Critical events feed

### APIs
- **Health Check:** `GET /health`
  ```bash
  curl http://localhost:8000/health
  ```

- **Full Dashboard Data:** `GET /api/dashboard`
  ```bash
  curl http://localhost:8000/api/dashboard | jq .
  ```

- **Deployments List:** `GET /api/deployments`
  ```bash
  curl http://localhost:8000/api/deployments | jq .
  ```

- **Recent Events:** `GET /api/events`
  ```bash
  curl http://localhost:8000/api/events | jq .
  ```

- **Post Metrics:** `POST /api/metrics/{deployment_id}`
  ```bash
  curl -X POST http://localhost:8000/api/metrics/neo-toshiba \
    -H "Content-Type: application/json" \
    -d '{"uptime_percent": 99.8, ...}'
  ```

---

## 🚀 Quick Deploy Options

### Option A: Replit (Free, Shareable)
1. Visit https://replit.com/new
2. Select "Import from GitHub"
3. Paste: `https://github.com/YOUR_USERNAME/openclaw-mission-control`
4. Click "Import"
5. Click "Run"
6. Your dashboard will be at: `https://openclaw-mission-control.USERNAME.repl.co`

**Note:** You'll need to push to GitHub first:
```bash
git remote add origin https://github.com/YOUR_USERNAME/openclaw-mission-control.git
git push -u origin main
```

### Option B: Glitch.me (Free, Instant)
1. Visit https://glitch.me
2. Click "New Project" → "Import from GitHub"
3. Paste repository URL
4. Your dashboard will be instantly available

### Option C: Vercel (Free Tier)
```bash
npm install -g vercel
vercel --prod
# Follow prompts to deploy
# Your dashboard will be at: https://openclaw-mission-control.vercel.app
```

### Option D: PythonAnywhere (Free Tier)
1. Sign up at https://www.pythonanywhere.com
2. Upload repository
3. Configure web app
4. Your dashboard will be at: `https://yourname.pythonanywhere.com`

### Option E: Railway (Simple, $5 credit)
```bash
npm install -g @railway/cli
railway login
railway up
# Your dashboard will be auto-deployed with a public URL
```

---

## 🧪 Testing

### 1. Local Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok",...}
```

### 2. Get Dashboard Data
```bash
curl http://localhost:8000/api/dashboard | jq .stats
# Expected: {"total":3, "online":2, "offline":1}
```

### 3. Get All Deployments
```bash
curl http://localhost:8000/api/deployments | jq '.[].id'
# Expected:
# "neo-toshiba"
# "mba2"
# "agent3"
```

### 4. Get Recent Events
```bash
curl http://localhost:8000/api/events | jq '.[] | {deployment_id, event_type}'
```

### 5. View HTML Dashboard in Browser
Open http://localhost:8000 in your browser
- See live deployment cards
- Watch metrics update automatically
- Monitor critical events in real-time

---

## 📱 Admin Dashboards (Per Deployment)

Each instance (neo-toshiba, mba2) runs its own Admin Dashboard on port 8001:

### neo-toshiba Admin
- **URL:** http://192.168.1.33:8001
- **Status:** Ready for deployment
- **Provides:** Detailed guardrail metrics, audit trails, event history

### mba2 Admin
- **URL:** http://192.168.1.56:8001
- **Status:** Ready for deployment
- **Provides:** Instance-specific monitoring

### Deployment Script
```bash
bash /Users/alexren/.openclaw/workspace/mission_control_master/admin_dashboard/deploy.sh neo-toshiba 192.168.1.33 localhost 8000
```

---

## 🔄 Integration Checklist

### Phase 4 Completion
- [x] Master Dashboard UI (Liquid Glass theme)
- [x] Admin Dashboard UI (with guardrail metrics)
- [x] API endpoints (metrics, events, deployments)
- [x] Demo data (3 deployments, 2 events)
- [x] Auto-refresh (every 5 seconds)
- [x] Local testing
- [ ] Deploy to Vercel/Replit
- [ ] Configure metric sync crons
- [ ] Wire Phase 3 guardrails

### Ready for Next Steps
1. **Push to GitHub** (required for cloud deployment)
2. **Deploy Master Dashboard** to Vercel/Replit
3. **Deploy Admin Dashboards** to each instance
4. **Set up metric sync** with cron jobs
5. **Monitor and iterate**

---

## 📊 Demo Data

The dashboards come with realistic demo data:

**Deployments:**
- neo-toshiba (Docker) - Online, 99.8% uptime
- mba2 (macOS) - Online, 99.5% uptime
- agent3 (Docker) - Offline

**Events:**
- Rate limit exceeded (neo-toshiba)
- Cost alert (mba2)

**Guardrails:**
- Rate limit: 15k requests, 340 blocked (2.2%)
- Authorization: 85 blocked (0.56%)
- Output validation: 152 blocked (1%)
- Audit trail: All logged

---

## 🛠 Troubleshooting

### Server Won't Start
```bash
# Kill any existing process on port 8000
ps aux | grep python | grep 8000

# Try explicit port
python3 serve_test.py --port 9000
```

### "Connection refused" when accessing http://localhost:8000
- Check server is running: `ps aux | grep uvicorn`
- Try different port: `python3 serve_test.py --port 9000`
- Check firewall settings

### Deployments show "offline"
- This is expected in demo mode
- Real data comes from admin dashboards on each instance
- Will update automatically when metrics are synced

### API returns 404
- Make sure you're hitting correct endpoint
- Verify path is spelled correctly
- Check server logs for errors

---

## 📝 Files

```
mission_control_master/
├── index.html                   # Master Dashboard (frontend)
├── serve_test.py               # Test server
├── api/
│   └── index.py               # Vercel serverless function
├── admin_dashboard/
│   ├── app.py                 # Admin API
│   ├── dashboard.html         # Admin UI
│   ├── guardrail_collector.py # Metrics collection
│   ├── event_pusher.py        # Event notifications
│   └── deploy.sh              # Deployment script
├── vercel.json                # Vercel config
├── package.json               # NPM config
├── requirements.txt           # Python deps
├── DEPLOYMENT_GUIDE.md        # How to deploy
└── README.md                  # Full documentation
```

---

## 🚀 Next: Deploy to Cloud

### Step 1: Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/openclaw-mission-control.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Vercel
```bash
npm install -g vercel
vercel --prod
# URL: https://openclaw-mission-control.vercel.app
```

### Step 3: Update Admin Dashboards
```bash
export MASTER_HOST="openclaw-mission-control.vercel.app"
export MASTER_PORT="443"

cd admin_dashboard
bash start.sh
```

### Step 4: Add Metric Sync
```bash
# On Master VM, add to crontab:
*/5 * * * * curl -s http://192.168.1.33:8001/metrics | \
  curl -X POST -d @- https://openclaw-mission-control.vercel.app/api/metrics/neo-toshiba
```

---

## ✅ Verification Checklist

- [ ] Master Dashboard loads: http://localhost:8000
- [ ] Can see 3 deployment cards
- [ ] Critical events show at bottom
- [ ] Auto-refresh working (watch time updates)
- [ ] API endpoints return valid JSON
- [ ] Admin dashboard links work (once deployed)
- [ ] Metrics sync every 5 minutes
- [ ] Events push in real-time

---

## 📞 Support

**Documentation:**
- Full README: `/README.md`
- Deployment Guide: `/DEPLOYMENT_GUIDE.md`
- Phase 4 Integration: `/PHASE_4_INTEGRATION.md`

**To run locally:**
```bash
cd /Users/alexren/.openclaw/workspace/mission_control_master
bash start.sh
# Opens http://localhost:8000
```

**To get help:**
```bash
curl http://localhost:8000/docs  # Swagger UI
curl http://localhost:8000/redoc # ReDoc
```

---

**🎛️ You're all set! Mission Control is operational.**

Next: Deploy to cloud, then wire up admin dashboards on each instance.
