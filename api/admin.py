"""
Admin Dashboard API - Vercel Serverless Function
"""

import json
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
DEPLOYMENT_ID = os.getenv("DEPLOYMENT_ID", "demo-instance")
MASTER_HOST = os.getenv("MASTER_HOST", "localhost")
MASTER_PORT = os.getenv("MASTER_PORT", "8000")

# In-memory state for demo
METRICS_STATE = {
    "deployment_id": DEPLOYMENT_ID,
    "uptime_percent": 99.8,
    "requests_hour": 1850,
    "error_count_hour": 3,
    "cost_usd_today": 12.45,
    "cost_usd_month": 285.60
}

EVENTS = []


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "deployment_id": DEPLOYMENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "connected_to_master": True
    }


@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "status": "ok",
        "deployment_id": DEPLOYMENT_ID,
        "collector_initialized": True,
        "pusher_initialized": True,
        "queued_events": len(EVENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """Get current metrics snapshot"""
    return {
        "deployment_id": DEPLOYMENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "health_status": "online",
        "uptime_percent": METRICS_STATE["uptime_percent"],
        "total_requests_hour": METRICS_STATE["requests_hour"],
        "error_count_hour": METRICS_STATE["error_count_hour"],
        "cost_usd_today": METRICS_STATE["cost_usd_today"],
        "cost_usd_month": METRICS_STATE["cost_usd_month"],
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
            },
            "output-validation": {
                "guardrail_type": "output-validation",
                "requests_total": 15200,
                "requests_blocked": 152,
                "error_rate": 0.0005,
                "p50_latency_ms": 22.1,
                "p95_latency_ms": 68.5,
                "p99_latency_ms": 185.3
            },
            "audit": {
                "guardrail_type": "audit",
                "requests_total": 15200,
                "requests_blocked": 0,
                "error_rate": 0.0,
                "p50_latency_ms": 5.3,
                "p95_latency_ms": 12.1,
                "p99_latency_ms": 34.7
            }
        }
    }


@app.get("/events")
async def get_events(limit: int = 100):
    """Get recent events"""
    return {
        "events": EVENTS[-limit:],
        "count": len(EVENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/notify/rate_limit_exceeded")
async def notify_rate_limit(data: dict):
    """Notify of rate limit exceeded"""
    event = {
        "deployment_id": DEPLOYMENT_ID,
        "event_type": "rate_limit_exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "critical",
        "details": data
    }
    EVENTS.append(event)
    return {"status": "notified"}


@app.post("/notify/auth_block")
async def notify_auth_block(data: dict):
    """Notify of auth block"""
    event = {
        "deployment_id": DEPLOYMENT_ID,
        "event_type": "auth_block",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "high",
        "details": data
    }
    EVENTS.append(event)
    return {"status": "notified"}


@app.post("/notify/cost_alert")
async def notify_cost_alert(data: dict):
    """Notify of cost alert"""
    event = {
        "deployment_id": DEPLOYMENT_ID,
        "event_type": "cost_alert",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "warning",
        "details": data
    }
    EVENTS.append(event)
    return {"status": "notified"}


@app.post("/notify/anomaly")
async def notify_anomaly(data: dict):
    """Notify of anomaly"""
    event = {
        "deployment_id": DEPLOYMENT_ID,
        "event_type": "anomaly",
        "timestamp": datetime.utcnow().isoformat(),
        "severity": data.get("severity", "warning"),
        "details": data
    }
    EVENTS.append(event)
    return {"status": "notified"}


@app.get("/api/dashboard")
async def get_dashboard():
    """Get complete dashboard data"""
    metrics = await get_metrics()
    return {
        "deployment_id": DEPLOYMENT_ID,
        "metrics": metrics,
        "recent_events": EVENTS[-50:],
        "blocked_requests": [e for e in EVENTS if e.get("event_type") == "auth_block"][-20:],
        "status_ok": True,
        "timestamp": datetime.utcnow().isoformat()
    }


# Catch-all for static files
@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    """Serve static files"""
    if full_path.endswith(".html") or full_path == "":
        try:
            with open("admin_dashboard/dashboard.html", "r") as f:
                return f.read()
        except:
            return JSONResponse({"error": "Dashboard not found"}, status_code=404)

    return JSONResponse({"error": "Not found"}, status_code=404)
