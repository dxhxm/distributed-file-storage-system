from fastapi import FastAPI
from app.api.consensus import router as consensus_router, consensus_service
import threading

app = FastAPI(
    title="Distributed File Storage System",
    description="Base FastAPI server for distributed nodes",
    version="1.0.0"
)

# Register routes
app.include_router(consensus_router)


@app.on_event("startup")
async def start_raft_consensus():
    """
    FastAPI startup event: starts background threads for Raft consensus
    """
    print(f"[startup] Starting background Raft consensus loop for node: {consensus_service.current_node}")
    consensus_service.start_background_tasks()
    print("[startup] Background Raft consensus thread started.")


@app.get("/")
async def root():
    return {
        "message": "Distributed File Storage System Node Running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }