from fastapi import APIRouter
from app.services import time_sync

router = APIRouter()

@router.get("/time")
async def get_time():
    return {"node_time": time_sync.get_current_node_time()}

@router.post("/sync-time")
async def sync_time(target_time: float):
    return time_sync.synchronize_clock(target_time)