"""
Admin Dashboard - Per-Deployment FastAPI Backend (Port 8001)
Deployed on neo-toshiba, mba2, agent3
Reports back to Master Dashboard on port 8000
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import LocalMetrics, AdminDashboardData, AuditEvent
from guardrail_collector import init_collector, get_collector
from event_pusher import init_pusher, get_pusher

# Configuration
DEPLOYMENT_ID = os.environ.get("DEPLOYMENT_ID", "unknown")
MASTER_HOST = os.environ.get("MASTER_HOST", "127.0.0.1")
MASTER_PORT = int(os.environ.get("MASTER_PORT", 8000))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title=f"Admin Dashboard - {DEPLOYMENT_ID}",
    description="Per-deployment detailed monitoring and metrics",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize collectors and pushers on startup"""
    logger.info(f"🚀 Admin Dashboard starting for {DEPLOYMENT_ID}...")

    # Initialize guardrail collector
    # (guardrail_enforcer would be injected from the actual OpenClaw deployment)
    init_collector(DEPLOYMENT_ID, guardrail_enforcer=None)
    logger.info("✅ Guardrail collector initialized")

    # Initialize event pusher
    init_pusher(DEPLOYMENT_ID, master_host=MASTER_HOST, master_port=MASTER_PORT)
    logger.info(f"✅ Event pusher initialized (Master: {MASTER_HOST}:{MASTER_PORT})")


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/health")
async def health():
    """Admin dashboard health check"""
    return {
        "status": "ok",
        "deployment_id": DEPLOYMENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "connected_to_master": f"{MASTER_HOST}:{MASTER_PORT}",
    }


@app.get("/status")
async def status():
    """Detailed status"""
    pusher = get_pusher()
    return {
        "deployment_id": DEPLOYMENT_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "collector_initialized": get_collector() is not None,
        "pusher_initialized": pusher is not None,
        "queued_events": len(pusher.retry_queue) if pusher else 0,
    }


# ============================================================================
# METRICS
# ============================================================================

@app.get("/metrics")
async def get_metrics():
    """
    Get current metrics snapshot
    Called by Master every 5 minutes
    """
    collector = get_collector()
    if not collector:
        return {
            "error": "Collector not initialized",
            "timestamp": datetime.utcnow().isoformat(),
        }

    try:
        # Collect all metrics
        guardrail_metrics = collector.collect_guardrail_metrics()
        audit_events = collector.collect_audit_events(limit=100)
        model_metrics = collector.get_model_tier_metrics()

        # Build response (matches Master's expected format)
        return {
            "deployment_id": DEPLOYMENT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": "healthy",  # TODO: derive from guardrail data
            "uptime_percent": 99.5,  # TODO: calculate
            "rate_limit_current": 0,  # TODO: from rate-limit guardrail
            "rate_limit_max": 1000,  # TODO: config
            "rate_limit_percent": 0.0,  # TODO: calculate
            "tokens_used_today": 0,  # TODO: track
            "cost_usd_today": 0.0,  # TODO: calculate
            "cost_usd_month": 0.0,  # TODO: track
            "error_count_hour": 0,  # TODO: from audit
            "error_count_day": 0,  # TODO: from audit
            "active_models": len(model_metrics),
            "total_requests_hour": 0,  # TODO: from guardrails
            "guardrails": {
                name: detail.dict()
                for name, detail in guardrail_metrics.items()
            },
        }

    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.get("/metrics/history")
async def get_metrics_history(hours: int = 24):
    """Get historical metrics (would use time-series DB in production)"""
    return {
        "deployment_id": DEPLOYMENT_ID,
        "hours": hours,
        "data_points": 0,
        "metrics": [],
    }


# ============================================================================
# EVENTS
# ============================================================================

@app.get("/events")
async def get_events(limit: int = 100):
    """Get recent audit events"""
    collector = get_collector()
    if not collector:
        return {"events": []}

    try:
        events = collector.collect_audit_events(limit=limit)
        return {
            "deployment_id": DEPLOYMENT_ID,
            "count": len(events),
            "events": [e.dict(default=str) for e in events],
        }
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return {"events": [], "error": str(e)}


@app.get("/events/blocks")
async def get_blocks(limit: int = 20):
    """Get recent guardrail blocks"""
    collector = get_collector()
    if not collector:
        return {"blocks": []}

    try:
        blocks = collector.collect_blocked_requests(limit=limit)
        return {
            "deployment_id": DEPLOYMENT_ID,
            "count": len(blocks),
            "blocks": [b.dict(default=str) for b in blocks],
        }
    except Exception as e:
        logger.error(f"Error getting blocks: {e}")
        return {"blocks": [], "error": str(e)}


# ============================================================================
# DASHBOARD
# ============================================================================

@app.get("/api/dashboard")
async def get_dashboard():
    """Get complete dashboard data"""
    collector = get_collector()
    if not collector:
        return {
            "error": "Collector not initialized",
            "timestamp": datetime.utcnow().isoformat(),
        }

    try:
        metrics = await get_metrics()
        events = await get_events(limit=50)
        blocks = await get_blocks(limit=20)

        return {
            "deployment_id": DEPLOYMENT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "recent_events": events.get("events", []),
            "recent_blocks": blocks.get("blocks", []),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# CRITICAL EVENTS (Push to Master)
# ============================================================================

@app.post("/notify/rate_limit_exceeded")
async def notify_rate_limit(model_id: str, current: int, limit: int):
    """Notify Master of rate limit exceeded"""
    pusher = get_pusher()
    if pusher:
        await pusher.push_rate_limit_exceeded(model_id, current, limit)
    return {"status": "notified"}


@app.post("/notify/auth_block")
async def notify_auth_block(model_id: str, tool_name: str, reason: str):
    """Notify Master of auth block"""
    pusher = get_pusher()
    if pusher:
        await pusher.push_auth_block(model_id, tool_name, reason)
    return {"status": "notified"}


@app.post("/notify/cost_alert")
async def notify_cost_alert(cost_today: float, cost_limit: float):
    """Notify Master of cost anomaly"""
    pusher = get_pusher()
    if pusher:
        await pusher.push_cost_alert(cost_today, cost_limit)
    return {"status": "notified"}


@app.post("/notify/anomaly")
async def notify_anomaly(anomaly_type: str, description: str, severity: str = "warning"):
    """Notify Master of anomaly"""
    pusher = get_pusher()
    if pusher:
        await pusher.push_anomaly(anomaly_type, description, severity)
    return {"status": "notified"}


# ============================================================================
# STATIC FILES
# ============================================================================

@app.get("/")
async def serve_dashboard():
    """Serve the Admin Dashboard HTML"""
    dashboard_path = __file__.replace("app.py", "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return {"message": "Dashboard not yet created"}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info(f"Starting Admin Dashboard for {DEPLOYMENT_ID} on port 8001")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
