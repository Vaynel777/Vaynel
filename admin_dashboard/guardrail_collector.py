"""
Guardrail Metrics Collector - Aggregates metrics from Phase 3 guardrails
Collects from RateLimitGuardrail, AuthorizationGuardrail, OutputValidationGuardrail, AuditTrailGuardrail
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from models import GuardrailDetail, ModelTierMetrics, LocalMetrics, AuditEvent

logger = logging.getLogger(__name__)


class GuardrailCollector:
    """
    Collects metrics from all Phase 3 guardrails

    Integration points:
    - Each guardrail has .getMetrics() method (from Phase 3 spec)
    - AuditTrailGuardrail provides audit events
    """

    def __init__(self, deployment_id: str, guardrail_enforcer=None):
        """
        Args:
            deployment_id: This deployment's ID
            guardrail_enforcer: Reference to GuardrailEnforcer (from Phase 3)
        """
        self.deployment_id = deployment_id
        self.guardrail_enforcer = guardrail_enforcer
        self.metrics_cache = {}

    def collect_guardrail_metrics(self) -> Dict[str, GuardrailDetail]:
        """
        Collect metrics from all active guardrails

        Returns dict of guardrail_type -> GuardrailDetail
        """
        metrics = {}

        if not self.guardrail_enforcer:
            logger.warning("GuardrailEnforcer not available")
            return metrics

        # Get all guardrails from enforcer
        # Assuming enforcer.guardrails is a list of IGuardrail instances
        for guardrail in getattr(self.guardrail_enforcer, 'guardrails', []):
            try:
                # Get guardrail type
                guardrail_type = self._identify_guardrail_type(guardrail)
                if not guardrail_type:
                    continue

                # Get metrics from guardrail.getMetrics()
                raw_metrics = guardrail.getMetrics()

                # Parse based on type
                detail = self._parse_guardrail_metrics(guardrail_type, raw_metrics)
                metrics[guardrail_type] = detail

                logger.debug(f"Collected metrics: {guardrail_type}")

            except Exception as e:
                logger.error(f"Error collecting guardrail metrics: {e}")

        return metrics

    def _identify_guardrail_type(self, guardrail) -> Optional[str]:
        """Identify guardrail type from instance"""
        class_name = guardrail.__class__.__name__.lower()

        if "ratelimit" in class_name:
            return "rate-limit"
        elif "auth" in class_name:
            return "auth"
        elif "output" in class_name or "validation" in class_name:
            return "output-validation"
        elif "audit" in class_name:
            return "audit"
        else:
            return None

    def _parse_guardrail_metrics(self, guardrail_type: str, raw_metrics: dict) -> GuardrailDetail:
        """Parse raw metrics into GuardrailDetail"""
        return GuardrailDetail(
            guardrail_type=guardrail_type,
            enabled=raw_metrics.get("enabled", True),
            requests_total=raw_metrics.get("requests_total", 0),
            requests_blocked=raw_metrics.get("requests_blocked", 0),
            requests_allowed=raw_metrics.get("requests_allowed", 0),
            block_rate=raw_metrics.get("block_rate", 0.0),
            error_count=raw_metrics.get("error_count", 0),
            error_rate=raw_metrics.get("error_rate", 0.0),
            latency_p50_ms=raw_metrics.get("latency_p50_ms", 0.0),
            latency_p95_ms=raw_metrics.get("latency_p95_ms", 0.0),
            latency_p99_ms=raw_metrics.get("latency_p99_ms", 0.0),
            latency_max_ms=raw_metrics.get("latency_max_ms", 0.0),
        )

    def collect_audit_events(self, limit: int = 100) -> list:
        """
        Collect recent audit events from AuditTrailGuardrail

        Args:
            limit: Max number of events to return

        Returns:
            List of AuditEvent objects
        """
        events = []

        if not self.guardrail_enforcer:
            return events

        try:
            # Find AuditTrailGuardrail
            audit_guardrail = None
            for guardrail in getattr(self.guardrail_enforcer, 'guardrails', []):
                if 'audit' in guardrail.__class__.__name__.lower():
                    audit_guardrail = guardrail
                    break

            if not audit_guardrail:
                logger.debug("AuditTrailGuardrail not found")
                return events

            # Get audit logger
            audit_logger = getattr(audit_guardrail, 'logger', None)
            if not audit_logger:
                return events

            # Get recent events from logger
            # Assuming logger has get_recent_events(limit) method
            raw_events = getattr(audit_logger, 'get_recent_events', lambda x: [])(limit)

            # Convert to AuditEvent objects
            for raw in raw_events:
                try:
                    event = AuditEvent(
                        timestamp=datetime.fromisoformat(raw.get("timestamp", datetime.utcnow().isoformat())),
                        event_type=raw.get("action", "unknown"),
                        action=raw.get("message", ""),
                        model_id=raw.get("modelId", "unknown"),
                        tool_name=raw.get("toolName"),
                        status="success" if raw.get("error") is None else "error",
                        details=raw,
                    )
                    events.append(event)
                except Exception as e:
                    logger.debug(f"Error parsing audit event: {e}")

            logger.debug(f"Collected {len(events)} audit events")
            return events

        except Exception as e:
            logger.error(f"Error collecting audit events: {e}")
            return events

    def collect_blocked_requests(self, limit: int = 20) -> list:
        """
        Collect recent requests blocked by guardrails

        Returns:
            List of AuditEvent objects (filtered to blocks only)
        """
        all_events = self.collect_audit_events(limit=limit*3)  # Get more to filter
        blocked = [e for e in all_events if "block" in e.action.lower() or e.status == "blocked"]
        return blocked[:limit]

    def get_model_tier_metrics(self) -> list:
        """
        Get metrics per model tier

        Returns:
            List of ModelTierMetrics
        """
        # This would integrate with Phase 3's orchestration system
        # For now, return empty list (can be populated from guardrail context)
        return []


# Singleton for use in FastAPI
_collector: Optional[GuardrailCollector] = None


def init_collector(deployment_id: str, guardrail_enforcer=None):
    """Initialize the global collector"""
    global _collector
    _collector = GuardrailCollector(deployment_id, guardrail_enforcer)
    return _collector


def get_collector() -> Optional[GuardrailCollector]:
    """Get the global collector"""
    return _collector
