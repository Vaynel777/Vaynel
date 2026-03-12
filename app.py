"""
Mission Control Master Dashboard - FastAPI Backend (Port 8000)
Aggregates metrics and events from all deployments (neo-toshiba, mba2, agent3)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import (
    DeploymentConfig, MetricsSnapshot, CriticalEvent,
    DeploymentStatus, MasterDashboardData
)
from database import (
    register_deployment, get_deployments, get_latest_metrics,
    get_metrics_history, get_recent_events, store_event, get_connection
)
from aggregator import aggregator, CriticalEventReceiver, start_aggregator

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Mission Control Master Dashboard",
    description="Phase 4.1 Advanced Monitoring & Analytics",
    version="1.0.0"
)

# CORS for cross-origin requests (dashboard frontend)
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
    """Start background aggregator on app startup"""
    logger.info("🚀 Mission Control Master starting...")
    await start_aggregator()
    logger.info("✅ Metrics aggregator started")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown aggregator"""
    aggregator.stop()
    logger.info("✅ Metrics aggregator stopped")


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/health")
async def health():
    """Master dashboard health check"""
    deployments = get_deployments()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "registered_deployments": len(deployments),
        "aggregator_running": aggregator.running,
    }


@app.get("/status")
async def status():
    """Detailed status with sync information"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sync_status")
    sync_rows = cursor.fetchall()
    sync_columns = [description[0] for description in cursor.description]
    sync_status = {row[0]: dict(zip(sync_columns, row)) for row in sync_rows}
    conn.close()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "sync_status": sync_status,
    }


# ============================================================================
# DEPLOYMENT MANAGEMENT
# ============================================================================

@app.post("/api/deployments")
async def register_new_deployment(config: DeploymentConfig):
    """Register a new deployment instance"""
    register_deployment(config.id, config.dict())
    logger.info(f"✅ Registered deployment: {config.id}")
    return {"status": "registered", "deployment_id": config.id}


@app.get("/api/deployments")
async def list_deployments() -> List[DeploymentStatus]:
    """List all registered deployments with current status"""
    deployments = get_deployments()
    status_list = []

    for d in deployments:
        metrics = get_latest_metrics(d["id"])
        recent_event = get_recent_events(d["id"], limit=1)

        # Determine status
        if not metrics:
            health_status = "offline"
        else:
            health_status = metrics.get("health_status", "unknown")

        status = DeploymentStatus(
            deployment_id=d["id"],
            name=d["name"],
            status=health_status,
            uptime_percent=metrics.get("uptime_percent", 0) if metrics else 0,
            last_sync=datetime.fromisoformat(metrics["timestamp"]) if metrics else None,
            last_event=datetime.fromisoformat(recent_event[0]["timestamp"]) if recent_event else None,
            metrics=MetricsSnapshot(**metrics) if metrics else None,
            pending_alerts=len(get_recent_events(d["id"], limit=100)) if metrics else 0,
        )
        status_list.append(status)

    return status_list


# ============================================================================
# METRICS & DATA
# ============================================================================

@app.get("/api/metrics/{deployment_id}")
async def get_deployment_metrics(deployment_id: str):
    """Get latest metrics for a deployment"""
    metrics = get_latest_metrics(deployment_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found")
    return metrics


@app.get("/api/metrics/{deployment_id}/history")
async def get_deployment_metrics_history(
    deployment_id: str,
    hours: int = 24
):
    """Get metrics history for a deployment"""
    history = get_metrics_history(deployment_id, hours=hours)
    return {
        "deployment_id": deployment_id,
        "hours": hours,
        "data_points": len(history),
        "metrics": history,
    }


@app.get("/api/events")
async def get_all_events(
    deployment_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
):
    """Get recent critical events, optionally filtered"""
    events = get_recent_events(deployment_id=deployment_id, limit=limit)

    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    return {
        "count": len(events),
        "events": events,
    }


@app.post("/api/events")
async def receive_critical_event(deployment_id: str, event: dict):
    """
    Receive a critical event from a deployment subset
    This implements the "push" part of hybrid sync
    """
    CriticalEventReceiver.receive_event(deployment_id, event)
    return {"status": "received", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/costs/{deployment_id}")
async def get_deployment_costs(
    deployment_id: str,
    days: int = 30,
):
    """Get cost breakdown for a deployment"""
    history = get_metrics_history(deployment_id, hours=days*24)

    if not history:
        return {
            "deployment_id": deployment_id,
            "period_days": days,
            "total_cost": 0,
            "daily_breakdown": [],
        }

    # Aggregate by day
    daily_costs = {}
    for m in history:
        date = m["timestamp"].split("T")[0]
        daily_costs[date] = max(
            daily_costs.get(date, 0),
            m.get("cost_usd_day", 0)
        )

    total_cost = sum(daily_costs.values())

    return {
        "deployment_id": deployment_id,
        "period_days": days,
        "total_cost": total_cost,
        "daily_breakdown": [
            {"date": date, "cost": cost}
            for date, cost in sorted(daily_costs.items(), reverse=True)
        ],
    }


# ============================================================================
# MASTER DASHBOARD DATA
# ============================================================================

@app.get("/api/dashboard")
async def get_master_dashboard() -> MasterDashboardData:
    """Get complete data for Master Dashboard frontend"""
    deployments = get_deployments()
    deployment_statuses = []
    total_cost_month = 0
    total_errors_hour = 0
    total_rate_limit_blocks_hour = 0

    sync_status = {}

    for d in deployments:
        metrics = get_latest_metrics(d["id"])
        recent_events = get_recent_events(d["id"], limit=1)

        if metrics:
            total_cost_month += metrics.get("cost_usd_month", 0)
            total_errors_hour += metrics.get("error_count_hour", 0)

            # Count rate limit blocks
            guardrails = metrics.get("guardrails", {})
            if "rate-limit" in guardrails:
                total_rate_limit_blocks_hour += guardrails["rate-limit"].get("requests_blocked", 0)

            health_status = metrics.get("health_status", "unknown")
        else:
            health_status = "offline"

        status = DeploymentStatus(
            deployment_id=d["id"],
            name=d["name"],
            status=health_status,
            uptime_percent=metrics.get("uptime_percent", 0) if metrics else 0,
            last_sync=datetime.fromisoformat(metrics["timestamp"]) if metrics else None,
            last_event=datetime.fromisoformat(recent_events[0]["timestamp"]) if recent_events else None,
            metrics=None,  # Don't include full metrics in dashboard summary
            pending_alerts=len(get_recent_events(d["id"], limit=100)) if metrics else 0,
        )
        deployment_statuses.append(status)
        sync_status[d["id"]] = "synced" if metrics else "pending"

    # Recent critical events
    recent_critical = get_recent_events(limit=20)
    critical_events = [
        CriticalEvent(
            deployment_id=e.get("deployment_id"),
            timestamp=datetime.fromisoformat(e.get("timestamp")),
            event_type=e.get("event_type"),
            severity=e.get("severity"),
            message=e.get("message"),
            metadata=e.get("metadata_json", {})
        )
        for e in recent_critical
    ]

    return MasterDashboardData(
        timestamp=datetime.utcnow(),
        deployments=deployment_statuses,
        total_cost_month=total_cost_month,
        total_errors_hour=total_errors_hour,
        total_rate_limit_blocks_hour=total_rate_limit_blocks_hour,
        critical_events=critical_events,
        sync_status=sync_status,
    )


# ============================================================================
# STATIC FILES
# ============================================================================

@app.get("/")
async def serve_dashboard():
    """Serve the Master Dashboard HTML"""
    dashboard_path = __file__.parent / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return {"message": "Dashboard not yet created - coming soon!"}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Initialize deployments if not already done
    try:
        get_deployments()
    except Exception:
        pass

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
