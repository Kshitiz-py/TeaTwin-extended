"""
Health Monitor — Post-commit CMSD service health checker.
Polls the CMSD Twin Service /api/summary endpoint. If 3 consecutive 500s
are detected, triggers automatic git revert to roll back agent changes.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from .config import REPORTS_DIR

logger = logging.getLogger("ai-agent.health-monitor")

# Default CMSD Twin Service URL (overridable)
CMSD_SERVICE_URL = "http://cmsd-twin:8002"


class HealthMonitor:
    """Monitors CMSD Twin Service health after code generation commits."""

    def __init__(self, service_url: str | None = None, failure_threshold: int = 3):
        self.service_url = (service_url or CMSD_SERVICE_URL).rstrip("/")
        self.failure_threshold = failure_threshold

    async def check_health(self) -> dict[str, Any]:
        """
        Single health check. Returns {healthy, status_code, message, latency_ms}.
        Tries /api/summary first, falls back to /api/layout.
        """
        endpoints = ["/api/summary", "/api/layout", "/api/health"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for ep in endpoints:
                try:
                    start = time.time()
                    resp = await client.get(f"{self.service_url}{ep}")
                    latency = round((time.time() - start) * 1000, 1)

                    if resp.status_code < 500:
                        return {
                            "healthy": True,
                            "status_code": resp.status_code,
                            "endpoint": ep,
                            "latency_ms": latency,
                        }
                    # 5xx — try next endpoint
                except Exception:
                    continue

            # All endpoints failed
            return {
                "healthy": False,
                "status_code": None,
                "endpoint": None,
                "latency_ms": None,
                "message": "All health endpoints unreachable",
            }

    async def monitor_after_commit(
        self,
        git_manager,  # GitManager instance for rollback
        max_wait_seconds: int = 30,
        check_interval: int = 3,
    ) -> dict[str, Any]:
        """
        Monitor service health after a commit.
        If failures exceed threshold, trigger git revert.
        Returns monitoring report.
        """
        failures = 0
        checks = []
        start_time = time.time()

        logger.info(f"Starting post-commit health monitoring (max {max_wait_seconds}s)")

        while (time.time() - start_time) < max_wait_seconds:
            await asyncio.sleep(check_interval)

            result = await self.check_health()
            checks.append(result)

            if result["healthy"]:
                logger.info(f"Service healthy after {failures} failures")
                return {
                    "outcome": "healthy",
                    "failure_count": failures,
                    "total_checks": len(checks),
                    "checks": checks,
                    "rolled_back": False,
                }

            failures += 1
            logger.warning(f"Health check failed ({failures}/{self.failure_threshold})")

            if failures >= self.failure_threshold:
                logger.error(f"Health threshold reached — triggering rollback!")

                # Attempt rollback
                rollback_result = {"attempted": False, "success": False}
                try:
                    rollback_result = git_manager.revert_last_commit()
                    logger.info(f"Rollback result: {rollback_result}")
                except Exception as e:
                    rollback_result = {"attempted": True, "success": False, "error": str(e)}

                return {
                    "outcome": "rolled_back",
                    "failure_count": failures,
                    "total_checks": len(checks),
                    "checks": checks,
                    "rolled_back": rollback_result.get("reverted", False),
                    "rollback_details": rollback_result,
                }

        # Timed out without reaching healthy state or threshold
        return {
            "outcome": "timeout",
            "failure_count": failures,
            "total_checks": len(checks),
            "checks": checks,
            "rolled_back": False,
            "message": f"Health monitoring timed out after {max_wait_seconds}s with {failures}/{self.failure_threshold} failures",
        }


# Singleton
health_monitor = HealthMonitor()
