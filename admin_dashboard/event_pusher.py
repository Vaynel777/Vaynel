"""
Event Pusher - Sends critical events from Admin Dashboard to Master Dashboard
Implements the "push" part of hybrid sync strategy
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventPusher:
    """Pushes critical events to Master Dashboard (port 8000)"""

    def __init__(self, deployment_id: str, master_host: str = "localhost", master_port: int = 8000):
        self.deployment_id = deployment_id
        self.master_url = f"http://{master_host}:{master_port}/api/events"
        self.timeout = aiohttp.ClientTimeout(total=5)
        self.retry_queue: list = []

    async def push_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        metadata: Dict[str, Any] = None,
        retry: bool = True,
    ) -> bool:
        """Push critical event to Master Dashboard"""
        event = {
            "deployment_id": self.deployment_id,
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "metadata": metadata or {},
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.master_url}?deployment_id={self.deployment_id}",
                    json=event,
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Event pushed: {event_type} [{severity}]")
                        return True
                    else:
                        logger.warning(f"⚠️ Event push failed (HTTP {resp.status}): {event_type}")
                        if retry:
                            self._enqueue_retry(event)
                        return False

        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Event push timeout: {event_type}")
            if retry:
                self._enqueue_retry(event)
            return False
        except Exception as e:
            logger.error(f"❌ Event push error: {e}")
            if retry:
                self._enqueue_retry(event)
            return False

    def _enqueue_retry(self, event: dict):
        """Queue event for retry"""
        self.retry_queue.append({
            "event": event,
            "retry_count": 0,
            "next_retry": datetime.utcnow().timestamp() + 30,
        })
        logger.info(f"📋 Queued for retry: {event['event_type']} (queue size: {len(self.retry_queue)})")

    async def process_retry_queue(self):
        """Process queued events with exponential backoff"""
        current_time = datetime.utcnow().timestamp()
        failed = []

        for item in self.retry_queue:
            if item["next_retry"] <= current_time:
                success = await self.push_event(
                    event_type=item["event"]["event_type"],
                    severity=item["event"]["severity"],
                    message=item["event"]["message"],
                    metadata=item["event"]["metadata"],
                    retry=False,
                )

                if not success:
                    item["retry_count"] += 1
                    if item["retry_count"] < 5:
                        item["next_retry"] = current_time + (60 * (item["retry_count"] + 1))
                        failed.append(item)
                    else:
                        logger.error(f"❌ Event abandoned after 5 retries: {item['event']['event_type']}")
            else:
                failed.append(item)

        self.retry_queue = failed

    async def run_retry_loop(self, interval_seconds: int = 30):
        """Run continuous retry loop"""
        logger.info(f"🔄 Event pusher retry loop started (interval: {interval_seconds}s)")
        try:
            while True:
                await self.process_retry_queue()
                await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Retry loop error: {e}")


_pusher: Optional[EventPusher] = None


def init_pusher(deployment_id: str, master_host: str = "localhost", master_port: int = 8000):
    global _pusher
    _pusher = EventPusher(deployment_id, master_host, master_port)
    return _pusher


def get_pusher() -> Optional[EventPusher]:
    return _pusher


async def start_pusher():
    if _pusher:
        asyncio.create_task(_pusher.run_retry_loop())
