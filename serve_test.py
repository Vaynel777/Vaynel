#!/usr/bin/env python3
"""
Simple test server for OpenClaw Mission Control Dashboard
Can be deployed to:
- Replit
- Glitch
- PythonAnywhere
- Heroku
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

app = FastAPI(title="OpenClaw Mission Control", version="4.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo data
DEPLOYMENTS = {
    "neo-toshiba": {
        "id": "neo-toshiba",
        "host": "192.168.1.33",
        "port": 8001,
        "type": "docker",
        "status": "online",
        "last_sync": datetime.utcnow().isoformat(),
        "metrics": {
            "uptime_percent": 99.8,
            "total_requests_hour": 1850,
            "error_count_hour": 3,
            "cost_usd_today": 12.45,
        }
    },
    "mba2": {
        "id": "mba2",
        "host": "192.168.1.56",
        "type": "macos",
        "status": "online",
        "metrics": {
            "uptime_percent": 99.5,
            "total_requests_hour": 1250,
            "error_count_hour": 2,
            "cost_usd_today": 8.20,
        }
    },
    "agent3": {
        "id": "agent3",
        "type": "docker",
        "status": "offline",
        "metrics": None
    }
}

EVENTS = [
    {
        "deployment_id": "neo-toshiba",
        "event_type": "rate_limit_exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "critical",
        "details": {"model_id": "deepseek-tier1", "current": 1050, "limit": 1000}
    }
]

# HTML Dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Mission Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #15152b 50%, #0f1425 100%);
            min-height: 100vh;
            color: #ffffff;
        }
        .header {
            padding: 30px 40px;
            background: rgba(20, 20, 40, 0.5);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(100, 150, 255, 0.1);
        }
        .logo {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4ff, #9d4edd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 24px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(0, 212, 255, 0.3);
            box-shadow: 0 20px 40px rgba(0, 212, 255, 0.1);
        }
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 12px;
        }
        .status.online {
            background: rgba(34, 197, 94, 0.1);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .status.offline {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .stat {
            display: inline-block;
            margin-right: 20px;
            font-size: 12px;
        }
        .stat-value {
            font-weight: 700;
            color: #00d4ff;
            font-size: 16px;
        }
        .info {
            background: rgba(100, 150, 255, 0.1);
            border: 1px solid rgba(100, 150, 255, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
            font-size: 13px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🎛️ OpenClaw Mission Control</div>
        <p style="font-size: 12px; color: #94a3b8; margin-top: 8px;">Phase 4.1 - Master & Admin Dashboards</p>
    </div>

    <div class="container">
        <div class="info">
            ✅ <strong>Demo Status:</strong> Dashboard is running and receiving metrics from deployments. 
            <br/>📊 <strong>API Endpoints:</strong> /api/dashboard, /api/deployments, /api/events
            <br/>🔄 <strong>Auto-refresh:</strong> Every 5 seconds
        </div>

        <h2 style="margin-bottom: 20px; font-size: 20px;">Registered Deployments</h2>
        <div class="cards" id="deployments"></div>

        <h2 style="margin-bottom: 20px; margin-top: 40px; font-size: 20px;">Recent Critical Events</h2>
        <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; padding: 24px;">
            <div id="events"></div>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();

                // Render deployments
                const depHtml = data.deployments.map(d => `
                    <div class="card">
                        <div class="card-title">${d.id}</div>
                        ${d.metrics ? `
                            <div class="stat">
                                <div class="stat-value">${d.metrics.uptime_percent}%</div>
                                <div>Uptime</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value">${d.metrics.total_requests_hour}</div>
                                <div>Requests/hr</div>
                            </div>
                        ` : ''}
                        <div class="status ${d.status}">${d.status.toUpperCase()}</div>
                    </div>
                `).join('');
                document.getElementById('deployments').innerHTML = depHtml;

                // Render events
                const eventsHtml = (data.critical_events || []).slice(0, 10).map(e => `
                    <div style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 12px;">
                        <div style="color: #00d4ff; font-weight: 600; margin-bottom: 4px;">${e.event_type}</div>
                        <div style="color: #94a3b8;">${e.deployment_id || 'system'} • ${new Date(e.timestamp).toLocaleTimeString()}</div>
                    </div>
                `).join('');
                document.getElementById('events').innerHTML = eventsHtml || '<div style="color: #64748b; text-align: center; padding: 40px;">No events</div>';
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('deployments').innerHTML = '<div style="grid-column: 1/-1; padding: 20px; color: #ef4444;">⚠️ Failed to load dashboard</div>';
            }
        }

        loadDashboard();
        setInterval(loadDashboard, 5000);
    </script>
</body>
</html>
"""

@app.get("/")
async def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "openclaw-mission-control",
        "version": "4.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/dashboard")
async def get_dashboard():
    online = sum(1 for d in DEPLOYMENTS.values() if d["status"] == "online")
    return {
        "deployments": list(DEPLOYMENTS.values()),
        "stats": {
            "total": len(DEPLOYMENTS),
            "online": online,
            "offline": len(DEPLOYMENTS) - online
        },
        "critical_events": EVENTS,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/deployments")
async def get_deployments():
    return list(DEPLOYMENTS.values())

@app.post("/api/metrics/{deployment_id}")
async def post_metrics(deployment_id: str, request: Request):
    if deployment_id in DEPLOYMENTS:
        DEPLOYMENTS[deployment_id]["last_sync"] = datetime.utcnow().isoformat()
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
