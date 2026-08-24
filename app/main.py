import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Ensure project root is in sys.path for direct module resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.consensus import router as consensus_router, consensus_service
from app.api import health
from app.api import time_sync
from app.api import replicate_routes
from app.services.time_sync import start_periodic_sync, start_clock_slew
from app.services.health_service import start_heartbeat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start periodic time synchronization background task
    asyncio.create_task(start_periodic_sync(interval=30))
    print("INFO: Periodic Time Synchronization Task Started.")

    # Start the clock slew background task
    asyncio.create_task(start_clock_slew())
    print("INFO: Clock Slew Task Started.")

    # Start background heartbeat health checks
    start_heartbeat()
    print("INFO: Health Heartbeat Loop Started.")

    # Start Raft consensus background tasks
    print(f"[startup] Starting background Raft consensus loop for node: {consensus_service.current_node}")
    consensus_service.start_background_tasks()
    print("[startup] Background Raft consensus thread started.")

    yield


app = FastAPI(
    title="Distributed File Storage System",
    description="Base FastAPI server for distributed nodes",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Web UI cross-node communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(health.router, tags=["Health & Fault Tolerance"])
app.include_router(consensus_router, tags=["Consensus"])
app.include_router(time_sync.router, tags=["Time Synchronization"])
app.include_router(replicate_routes.router, tags=["Replication"])


@app.get("/")
async def root():
    return {"message": "Distributed File Storage System Node Running"}