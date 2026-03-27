from fastapi import APIRouter
from app.services import time_sync
from app.services.time_sync import fetch_remote_time, get_current_node_time
from datetime import datetime

router = APIRouter()

@router.get("/time")
async def get_time():
    current_timestamp=time_sync.get_current_node_time
    readable_format=datetime.fromtimestamp(current_timestamp).strftime("%H:%M:%S")
    return {"node_time": current_timestamp,
            "readable_time":readable_format,
            "timezone":"Local System time"
            }

@router.post("/sync-time")
async def sync_time(target_time: float):
    return time_sync.synchronize_clock(target_time)

@router.get("/fetch-neighbor/{node_id}")
async def trigger_fetch(node_id: str):
    return await time_sync.fetch_remote_time(node_id)

@router.get("/sync-with-leader/{node_id}")
async def trigger_sync(node_id:str):
    """Command this node to synchronize its clock with a leader."""
    return await time_sync.perform_sync(node_id)