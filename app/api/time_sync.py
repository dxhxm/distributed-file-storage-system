from fastapi import APIRouter
from app.services import time_sync

router = APIRouter()

@router.get("/time")
async def get_time():
    return {"node_time": time_sync.get_current_node_time()}

@router.post("/sync-time")
async def sync_time(target_time: float):
    return time_sync.synchronize_clock(target_time)

@router.get("/fetch-neighbor/{node_id}")
async def trigger_fetch(node_id: str):
    return await time_sync.fetch_remote_time(node_id)