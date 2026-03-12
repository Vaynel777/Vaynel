"""
Pydantic models for Mission Control Master Dashboard
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel


class DeploymentConfig(BaseModel):
    """Deployment instance configuration"""
    id: str  # neo-toshiba, mba2, agent3
    name: str  # Human readable name
    host: str  # IP or hostname
    metrics_port: int  # Port for /metrics endpoint
    admin_port: int  # Port for admin dashboard (8001)
    region: str  # Region/location
    model_tiers: List[str]  # Available model tiers


class GuardrailMetrics(BaseModel):
    """Metrics from a single guardrail"""
    guardrail_type: str  # "rate-limit", "output-validation", "auth", "audit"
    requests_total: int
    requests_blocked: int
    error_rate: float  # 0-1
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class MetricsSnapshot(BaseModel):
    """Metrics from a single deployment instance"""
    deployment_id: str
    timestamp: datetime

    # Availability
    uptime_percent: float
    health_status: str  # "healthy", "degraded", "error"

    # Rate limiting
    rate_limit_current: int  # Current requests this period
    rate_limit_max: int  # Max allowed
    rate_limit_percent: float  # % of limit used

    # Costs
    tokens_used_today: int
    cost_usd_today: float
    cost_usd_month: float

    # Guardrails (breakdown by type)
    guardrails: Dict[str, GuardrailMetrics]

    # Errors
    error_count_hour: int
    error_count_day: int

    # Models
    active_models: int
    total_requests_hour: int


class CriticalEvent(BaseModel):
    """Critical event from a deployment (push to Master)"""
    deployment_id: str
    timestamp: datetime
    event_type: str  # "rate_limit_exceeded", "auth_block", "cost_alert", "anomaly", "error"
    severity: str  # "warning", "critical"
    message: str
    metadata: Dict[str, Any] = {}


class DeploymentStatus(BaseModel):
    """Current status of a single deployment"""
    deployment_id: str
    name: str
    status: str  # "online", "degraded", "offline"
    uptime_percent: float
    last_sync: datetime
    last_event: Optional[datetime]
    metrics: Optional[MetricsSnapshot]
    pending_alerts: int


class MasterDashboardData(BaseModel):
    """Complete data for Master Dashboard"""
    timestamp: datetime
    deployments: List[DeploymentStatus]
    total_cost_month: float
    total_errors_hour: int
    total_rate_limit_blocks_hour: int
    critical_events: List[CriticalEvent]
    sync_status: Dict[str, str]  # deployment_id -> "synced", "pending", "error"
