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
async def start_background_monitoring():
    """
    FastAPI startup event: starts background threads for:
      - Leader health checking
      - Node status updates (ALIVE / DEAD tracking)
    Runs automatically when the node starts.
    """
    print(f"[startup] Starting background leader monitoring for node: {consensus_service.current_node}")
    thread = threading.Thread(
        target=consensus_service.check_nodes_health_loop,
        daemon=True,
        name="leader-health-monitor"
    )
    thread.start()
    print("[startup] Background health monitoring thread started.")


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