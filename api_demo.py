"""Demo API for testing - combines master & admin dashboards"""

import json
from datetime import datetime

# Demo deployments
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

def get_dashboard_data():
    """Return complete dashboard data"""
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
