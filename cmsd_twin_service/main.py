"""
CMSD Twin Service — Main entry point.
Starts the CMSDOrchestrator, EventBus, and FastAPI server.
The service remains alive, polls SAP/MES APIs, and exposes the digital twin.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import CMSD_HOST, CMSD_PORT, POLL_INTERVAL
from .event_bus import EventBus
from .orchestrator import CMSDOrchestrator
from .routes import router, init as routes_init

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cmsd-twin")

# ─── FastAPI App ──────────────────────────────────────────────

app = FastAPI(
    title="CMSD Digital Twin Service",
    description="Live CMSD Digital Twin orchestrator — polls SAP + MES APIs, detects changes, streams events.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/cmsd/v1")

# ─── Lifecycle Events ─────────────────────────────────────────

# Global references
_event_bus = EventBus()
_orchestrator = CMSDOrchestrator(event_bus=_event_bus)


@app.on_event("startup")
async def startup():
    """Initialize the orchestrator and start background polling."""
    logger.info("CMSD Twin Service starting up...")
    routes_init(_orchestrator, _event_bus)
    await _orchestrator.start()
    logger.info(f"CMSD Twin Service ready. Polling every {POLL_INTERVAL}s")


@app.on_event("shutdown")
async def shutdown():
    """Gracefully stop the orchestrator."""
    logger.info("CMSD Twin Service shutting down...")
    await _orchestrator.stop()
    logger.info("CMSD Twin Service stopped")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=CMSD_HOST,
        port=CMSD_PORT,
        reload=False,
        log_level="info",
    )