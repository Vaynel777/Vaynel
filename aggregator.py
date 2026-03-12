"""
Metrics Aggregator - Polls each deployment's /metrics endpoint every 5 minutes
Implements hybrid sync: critical events push + metric aggregates pull
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Optional
import json

from database import (
    store_metrics, store_event, get_connection,
    get_deployments
)

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Polls deployment instances for metrics and stores in Master DB"""

    def __init__(self, poll_interval_seconds: int = 300):
        """
        Args:
            poll_interval_seconds: How often to poll each instance (default 5 min)
        """
        self.poll_interval = poll_interval_seconds
        self.running = False
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def poll_instance(self, deployment: dict) -> bool:
        """
        Poll a single deployment instance for metrics

        Returns:
            True if successful, False on error
        """
        deployment_id = deployment["id"]
        host = deployment["host"]
        metrics_port = deployment["metrics_port"]
        url = f"http://{host}:{metrics_port}/metrics"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        metrics = await resp.json()
                        metrics["timestamp"] = datetime.utcnow().isoformat()

                        # Store in Master DB
                        store_metrics(deployment_id, metrics)

                        logger.info(f"✅ Synced {deployment_id}: {metrics.get('health_status', 'unknown')}")

                        # Update sync status
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR REPLACE INTO sync_status (
                                deployment_id, last_sync_time, last_sync_status, consecutive_failures
                            ) VALUES (?, ?, ?, ?)
                        """, (deployment_id, datetime.utcnow().isoformat(), "success", 0))
                        conn.commit()
                        conn.close()

                        return True
                    else:
                        logger.warning(f"❌ {deployment_id} HTTP {resp.status}")
                        return False

        except asyncio.TimeoutError:
            logger.warning(f"⏱️  {deployment_id} timeout")
            self._record_sync_failure(deployment_id, "timeout")
            return False
        except Exception as e:
            logger.error(f"❌ {deployment_id} error: {e}")
            self._record_sync_failure(deployment_id, str(e))
            return False

    def _record_sync_failure(self, deployment_id: str, error: str):
        """Record sync failure in DB"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_status (
                deployment_id, last_sync_time, last_sync_status, last_sync_error,
                consecutive_failures
            ) VALUES (
                ?, ?, ?, ?,
                COALESCE((SELECT consecutive_failures + 1 FROM sync_status WHERE deployment_id = ?), 1)
            )
        """, (deployment_id, datetime.utcnow().isoformat(), "error", error, deployment_id))
        conn.commit()
        conn.close()

    async def poll_all_instances(self):
        """Poll all registered deployments in parallel"""
        deployments = get_deployments()
        if not deployments:
            logger.warning("No deployments registered")
            return

        logger.info(f"🔄 Polling {len(deployments)} deployments...")
        tasks = [self.poll_instance(d) for d in deployments]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.info(f"📊 Poll complete: {success_count}/{len(deployments)} successful")

    async def run_continuously(self):
        """Run polling loop continuously"""
        self.running = True
        logger.info(f"🚀 Aggregator started (interval: {self.poll_interval}s)")

        try:
            while self.running:
                await self.poll_all_instances()
                await asyncio.sleep(self.poll_interval)
        except Exception as e:
            logger.error(f"Aggregator error: {e}")
            self.running = False

    def stop(self):
        """Stop the aggregator"""
        self.running = False
        logger.info("🛑 Aggregator stopped")


class CriticalEventReceiver:
    """Receives critical events pushed from deployment instances"""

    @staticmethod
    def receive_event(deployment_id: str, event: dict):
        """
        Receive and store a critical event from a deployment

        Event should include:
        - event_type: rate_limit_exceeded, auth_block, cost_alert, anomaly, error
        - severity: warning or critical
        - message: human readable
        - metadata: dict with additional context
        """
        event["timestamp"] = datetime.utcnow().isoformat()
        store_event(deployment_id, event)

        logger.warning(
            f"🚨 Event from {deployment_id}: {event.get('event_type')} "
            f"[{event.get('severity')}] {event.get('message')}"
        )


# Global aggregator instance
aggregator = MetricsAggregator(poll_interval_seconds=300)  # 5 minutes


async def start_aggregator():
    """Start the aggregator background task"""
    asyncio.create_task(aggregator.run_continuously())
