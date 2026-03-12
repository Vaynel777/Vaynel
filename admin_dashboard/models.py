"""
Admin Dashboard models - Per-deployment detailed monitoring
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class GuardrailDetail(BaseModel):
    """Detailed metrics from a single guardrail"""
    guardrail_type: str  # "rate-limit", "output-validation", "auth", "audit"
    enabled: bool
    requests_total: int
    requests_blocked: int
    requests_allowed: int
    block_rate: float  # 0-1
    error_count: int
    error_rate: float  # 0-1
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float


class ModelTierMetrics(BaseModel):
    """Metrics for a single model tier"""
    model_id: str
    tier: int  # 0-3
    requests_hour: int
    requests_total: int
    tokens_used_hour: int
    tokens_used_total: int
    cost_hour: float
    cost_day: float
    error_rate: float
    latency_p95_ms: float


class LocalMetrics(BaseModel):
    """Complete local metrics for a deployment"""
    deployment_id: str
    timestamp: datetime

    # System health
    health_status: str  # "healthy", "degraded", "error"
    uptime_percent: float
    memory_percent: float
    cpu_percent: float

    # Rate limiting
    rate_limit_current: int
    rate_limit_max: int
    rate_limit_percent: float

    # Tokens & costs
    tokens_used_hour: int
    tokens_used_day: int
    cost_hour: float
    cost_day: float
    cost_month: float

    # Errors
    error_count_hour: int
    error_count_day: int
    error_rate_hour: float

    # Guardrails breakdown
    guardrails: Dict[str, GuardrailDetail]

    # Models
    active_models: int
    model_tiers: List[ModelTierMetrics]

    # Audit trail
    audit_events_hour: int
    audit_events_total: int


class AuditEvent(BaseModel):
    """Single audit trail event"""
    timestamp: datetime
    event_type: str  # "tool_execution", "guardrail_block", "auth_check", etc.
    action: str  # What happened
    model_id: str  # Which model did it
    tool_name: Optional[str]
    status: str  # "success", "blocked", "error"
    details: Dict[str, Any] = {}


class CriticalEventForMaster(BaseModel):
    """Event to push to Master Dashboard"""
    deployment_id: str
    timestamp: datetime
    event_type: str  # "rate_limit_exceeded", "auth_block", "cost_alert", "anomaly", "error"
    severity: str  # "warning", "critical"
    message: str
    metadata: Dict[str, Any] = {}


class AdminDashboardData(BaseModel):
    """Complete data for Admin Dashboard"""
    deployment_id: str
    timestamp: datetime
    metrics: LocalMetrics
    recent_events: List[AuditEvent]
    recent_blocks: List[AuditEvent]  # Last 20 guardrail blocks
    critical_alerts: List[CriticalEventForMaster]  # Pending alerts to send to Master
