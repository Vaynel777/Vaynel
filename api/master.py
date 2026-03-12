"""
Master Dashboard API - Vercel Serverless Function
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

# In-memory storage for demo (would use persistent storage in production)
DEPLOYMENTS = {
    "neo-toshiba": {
        "id": "neo-toshiba",
        "host": "192.168.1.33",
        "port": 8001,
        "type": "docker",
        "status": "initializing",
        "last_sync": None,
        "metrics": None
    },
    "mba2": {
        "id": "mba2",
        "host": "192.168.1.56",
        "port": 8001,
        "type": "macos",
        "status": "initializing",
        "last_sync": None,
        "metrics": None
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

CRITICAL_EVENTS = []


@app.get("/health")
async def health():
    """Health check endpoint"""
    online_count = sum(1 for d in DEPLOYMENTS.values() if d["status"] == "online")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "registered_deployments": len(DEPLOYMENTS),
        "online_deployments": online_count,
        "aggregator_running": True
    }


@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "status": "ok",
        "deployments": {
            dep_id: {
                "status": dep["status"],
                "last_sync": dep["last_sync"],
                "metrics_available": dep["metrics"] is not None
            }
            for dep_id, dep in DEPLOYMENTS.items()
        },
        "critical_events_pending": len(CRITICAL_EVENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/deployments")
async def get_deployments():
    """Get all registered deployments"""
    return {
        "deployments": list(DEPLOYMENTS.values()),
        "count": len(DEPLOYMENTS),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get specific deployment details"""
    if deployment_id not in DEPLOYMENTS:
        return JSONResponse({"error": "Deployment not found"}, status_code=404)

    return DEPLOYMENTS[deployment_id]


@app.post("/api/metrics/{deployment_id}")
async def post_metrics(deployment_id: str):
    """Receive metrics from admin dashboard"""
    if deployment_id not in DEPLOYMENTS:
        return JSONResponse({"error": "Deployment not found"}, status_code=404)

    # Update deployment
    DEPLOYMENTS[deployment_id]["status"] = "online"
    DEPLOYMENTS[deployment_id]["last_sync"] = datetime.utcnow().isoformat()
    DEPLOYMENTS[deployment_id]["metrics"] = {
        "health_status": "online",
        "uptime_percent": 99.5,
        "requests_hour": 1250,
        "error_rate": 0.002
    }

    return {"status": "received", "deployment_id": deployment_id}


@app.get("/api/metrics/{deployment_id}")
async def get_metrics(deployment_id: str):
    """Get metrics for specific deployment"""
    if deployment_id not in DEPLOYMENTS:
        return JSONResponse({"error": "Deployment not found"}, status_code=404)

    return DEPLOYMENTS[deployment_id].get("metrics", {})


@app.post("/api/events")
async def post_event(event: dict):
    """Receive critical event from admin dashboard"""
    CRITICAL_EVENTS.append({
        **event,
        "received_at": datetime.utcnow().isoformat()
    })
    # Keep only last 100 events
    if len(CRITICAL_EVENTS) > 100:
        CRITICAL_EVENTS.pop(0)

    return {"status": "received"}


@app.get("/api/events")
async def get_events(deployment_id: str = None, limit: int = 50):
    """Get recent critical events"""
    events = CRITICAL_EVENTS

    if deployment_id:
        events = [e for e in events if e.get("deployment_id") == deployment_id]

    return {
        "critical_events": events[-limit:],
        "count": len(events),
        "timestamp": datetime.utcnow().isoformat()
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
        "critical_events": CRITICAL_EVENTS[-20:],
        "timestamp": datetime.utcnow().isoformat()
    }


# Catch-all for static files
@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    """Serve static files"""
    if full_path.endswith(".html") or full_path == "":
        # Serve main dashboard
        try:
            with open("dashboard.html", "r") as f:
                return f.read()
        except:
            return JSONResponse({"error": "Dashboard not found"}, status_code=404)

    return JSONResponse({"error": "Not found"}, status_code=404)
