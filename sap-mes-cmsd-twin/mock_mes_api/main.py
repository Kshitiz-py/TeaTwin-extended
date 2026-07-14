"""
Mock MES API — Provides Live Operational Data for the Digital Twin
Serves: Resource Status, Jobs, Inventory, Incidents
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .routes import resource_status, jobs, inventory, incidents

app = FastAPI(
    title="Mock MES API",
    description="MES Operational Data API for CMSD Digital Twin — factory_digital_twin DB",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resource_status.router, prefix="/api/mes/v1")
app.include_router(jobs.router, prefix="/api/mes/v1")
app.include_router(inventory.router, prefix="/api/mes/v1")
app.include_router(incidents.router, prefix="/api/mes/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "mock-mes-api", "port": 8002}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)