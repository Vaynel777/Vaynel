#!/usr/bin/env python3
"""
Phase 4 Integration - Metric Collector Cron
Runs every 5 minutes on Master Dashboard VM to poll /metrics from each Admin Dashboard
Stores results in Master's SQLite database via HTTP POST
"""
import asyncio
import logging
import json
from datetime import datetime
import aiohttp
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
DEPLOYMENTS = [
    {"id": "neo-toshiba", "host": "192.168.1.33", "port": 8001},
    {"id": "mba2", "host": "192.168.1.56", "port": 8001},
    {"id": "agent3", "host": "192.168.1.100", "port": 8001},
]

MASTER_URL = "http://localhost:8000/api/metrics"
TIMEOUT = 10  # seconds
RETRIES = 2


async def poll_metrics_from_instance(session: aiohttp.ClientSession, deployment: dict) -> dict:
    """
    Poll /metrics endpoint from a single Admin Dashboard instance

    Returns:
        {
            "deployment_id": "neo-toshiba",
            "status": "success|error|timeout",
            "metrics": {...},
            "timestamp": "2026-03-12T..."
        }
    """
    deployment_id = deployment["id"]
    url = f"http://{deployment['host']}:{deployment['port']}/metrics"

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            if response.status == 200:
                metrics = await response.json()
                logger.info(f"✅ Polled {deployment_id}: {response.status}")
                return {
                    "deployment_id": deployment_id,
                    "status": "success",
                    "metrics": metrics,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.warning(f"⚠️  {deployment_id}: HTTP {response.status}")
                return {
                    "deployment_id": deployment_id,
                    "status": "error",
                    "error": f"HTTP {response.status}",
                    "timestamp": datetime.utcnow().isoformat(),
                }

    except asyncio.TimeoutError:
        logger.warning(f"⏱️  {deployment_id}: Timeout after {TIMEOUT}s")
        return {
            "deployment_id": deployment_id,
            "status": "timeout",
            "error": f"Timeout after {TIMEOUT}s",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ {deployment_id}: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def post_metrics_to_master(session: aiohttp.ClientSession, deployment_id: str, metrics: dict) -> bool:
    """
    POST collected metrics to Master Dashboard /api/metrics/{deployment_id}

    Returns:
        True if successful, False otherwise
    """
    try:
        url = f"{MASTER_URL}/{deployment_id}"
        async with session.post(url, json=metrics, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            if response.status in [200, 201]:
                logger.info(f"📤 Posted metrics to Master for {deployment_id}")
                return True
            else:
                logger.warning(f"⚠️  Master rejected {deployment_id}: HTTP {response.status}")
                return False

    except Exception as e:
        logger.error(f"❌ Failed to post metrics to Master: {e}")
        return False


async def run_collection_cycle():
    """
    Run one complete cycle: poll all instances and post to Master
    """
    logger.info("=" * 60)
    logger.info("📊 Starting metric collection cycle")
    logger.info("=" * 60)

    async with aiohttp.ClientSession() as session:
        # Poll all instances in parallel
        tasks = [poll_metrics_from_instance(session, dep) for dep in DEPLOYMENTS]
        results = await asyncio.gather(*tasks)

        # Track results
        success_count = 0
        error_count = 0

        # Post each result to Master
        for result in results:
            if result["status"] == "success":
                success_count += 1
                posted = await post_metrics_to_master(
                    session,
                    result["deployment_id"],
                    result["metrics"]
                )
                if not posted:
                    error_count += 1

            else:
                error_count += 1
                logger.warning(f"Skipping post for {result['deployment_id']}: {result.get('error')}")

        # Summary
        logger.info(f"✅ Cycle complete: {success_count} success, {error_count} errors")
        logger.info("=" * 60)


def main():
    """Entry point - can be called from cron"""
    try:
        asyncio.run(run_collection_cycle())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
