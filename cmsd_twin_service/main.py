"""
CMSD Twin Service — Main entry point.
Starts the CMSDOrchestrator, EventBus, and FastAPI server.
The service starts IDLE — call POST /api/cmsd/v1/start to begin polling.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("cmsd-twin")

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

_event_bus = EventBus()
_orchestrator = CMSDOrchestrator(event_bus=_event_bus, poll_interval=0)


@app.on_event("startup")
async def startup():
    """Initialize the orchestrator (idle) and register routes."""
    logger.info("CMSD Twin Service starting up (idle mode)...")
    routes_init(_orchestrator, _event_bus)
    # NOT starting the orchestrator — wait for POST /api/cmsd/v1/start
    logger.info("CMSD Twin Service ready. Idle — call POST /api/cmsd/v1/start to begin polling.")
    logger.info(f"Poll interval configured: {POLL_INTERVAL}s")


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
