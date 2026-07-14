"""
Mock SAP API — Provides Master Data for the Digital Twin
Serves: Resources, Parts, BOMs, Process Plans, Calendars, Orders, Layouts, Connections
"""

import sys
import os

# Add parent to path so shared config is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .routes import (
    resources,
    parts,
    boms,
    process_plans,
    calendars,
    orders,
    layouts,
    connections,
)

app = FastAPI(
    title="Mock SAP API",
    description="SAP Master Data API for CMSD Digital Twin — factory_digital_twin DB",
    version="1.0.0",
)

# CORS — allow dashboard + CMSD twin service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(resources.router, prefix="/api/sap/v1")
app.include_router(parts.router, prefix="/api/sap/v1")
app.include_router(boms.router, prefix="/api/sap/v1")
app.include_router(process_plans.router, prefix="/api/sap/v1")
app.include_router(calendars.router, prefix="/api/sap/v1")
app.include_router(orders.router, prefix="/api/sap/v1")
app.include_router(layouts.router, prefix="/api/sap/v1")
app.include_router(connections.router, prefix="/api/sap/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mock-sap-api", "port": 8001}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)