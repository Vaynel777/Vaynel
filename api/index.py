"""
OpenClaw Mission Control - Combined Master & Admin Dashboard API
Vercel Serverless Function
"""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json
from datetime import datetime

app = FastAPI()

# Add CORS
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
            "health_status": "online",
            "uptime_percent": 99.8,
            "total_requests_hour": 1850,
            "error_count_hour": 3,
            "cost_usd_today": 12.45,
            "cost_usd_month": 285.60,
            "active_models": 4,
            "guardrails": {
                "rate-limit": {
                    "guardrail_type": "rate-limit",
                    "requests_total": 15200,
                    "requests_blocked": 340,
                    "error_rate": 0.001,
                    "p50_latency_ms": 12.5,
                    "p95_latency_ms": 45.3,
                    "p99_latency_ms": 120.8
                },
                "auth": {
                    "guardrail_type": "auth",
                    "requests_total": 15200,
                    "requests_blocked": 85,
                    "error_rate": 0.0002,
                    "p50_latency_ms": 8.2,
                    "p95_latency_ms": 28.4,
                    "p99_latency_ms": 65.2
                }
            }
        }
    },
    "mba2": {
        "id": "mba2",
        "host": "192.168.1.56",
        "port": 8001,
        "type": "macos",
        "status": "online",
        "last_sync": datetime.utcnow().isoformat(),
        "metrics": {
            "health_status": "online",
            "uptime_percent": 99.5,
            "total_requests_hour": 1250,
            "error_count_hour": 2,
            "cost_usd_today": 8.20,
            "cost_usd_month": 195.30,
            "active_models": 3
        }
    },
    "agent3": {
        "id": "agent3",
        "host": "192.168.1.40",
        "port": 8001,
        "type": "docker",
        "status": "offline",
        "last_sync": None,
        "metrics": None
    }
}

EVENTS = [
    {
        "deployment_id": "neo-toshiba",
        "event_type": "rate_limit_exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "critical",
        "details": {
            "model_id": "deepseek-tier1",
            "current": 1050,
            "limit": 1000
        }
    },
    {
        "deployment_id": "mba2",
        "event_type": "cost_alert",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "warning",
        "details": {
            "cost_today": 8.20,
            "cost_limit": 10.00
        }
    }
]


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "openclaw-mission-control"
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """Get complete dashboard data"""
    online_count = sum(1 for d in DEPLOYMENTS.values() if d["status"] == "online")

    return {
        "deployments": list(DEPLOYMENTS.values()),
        "stats": {
            "total": len(DEPLOYMENTS),
            "online": online_count,
            "offline": len(DEPLOYMENTS) - online_count
        },
        "critical_events": EVENTS,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/deployments")
async def get_deployments():
    """Get all deployments"""
    return {
        "deployments": list(DEPLOYMENTS.values()),
        "count": len(DEPLOYMENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get specific deployment"""
    if deployment_id not in DEPLOYMENTS:
        return JSONResponse({"error": "Not found"}, status_code=404)

    return DEPLOYMENTS[deployment_id]


@app.get("/api/events")
async def get_events(limit: int = 20):
    """Get recent events"""
    return {
        "events": EVENTS[-limit:],
        "count": len(EVENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/events")
async def post_event(event: dict):
    """Post new event"""
    EVENTS.append({
        **event,
        "received_at": datetime.utcnow().isoformat()
    })
    if len(EVENTS) > 100:
        EVENTS.pop(0)

    return {"status": "received"}


@app.post("/api/metrics/{deployment_id}")
async def post_metrics(deployment_id: str, request: Request):
    """Receive metrics from deployment"""
    if deployment_id not in DEPLOYMENTS:
        return JSONResponse({"error": "Not found"}, status_code=404)

    try:
        data = await request.json()
        DEPLOYMENTS[deployment_id]["metrics"] = data
        DEPLOYMENTS[deployment_id]["last_sync"] = datetime.utcnow().isoformat()
        DEPLOYMENTS[deployment_id]["status"] = "online"
    except:
        pass

    return {"status": "received"}


# Catch-all for HTML
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve dashboard or API"""
    if full_path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    # Serve dashboard HTML
    try:
        with open("index.html", "r") as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=f.read())
    except:
        return JSONResponse({
            "message": "OpenClaw Mission Control Dashboard",
            "status": "running",
            "endpoints": {
                "/": "Dashboard",
                "/api/dashboard": "Full dashboard data",
                "/api/deployments": "All deployments",
                "/api/events": "Critical events",
                "/health": "Health check"
            }
        })


# Default root
@app.get("/")
async def root():
    """Dashboard root"""
    try:
        with open("index.html", "r") as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=f.read())
    except:
        return {"message": "OpenClaw Mission Control", "status": "running"}
