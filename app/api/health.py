from fastapi import APIRouter
from app.services import health_service

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Node is alive"
    }


@router.get("/nodes/status")
async def get_node_status():
    nodes = health_service.get_all_nodes()
    return {
        "nodes": nodes
    }


@router.post("/nodes/update")
async def update_node(node_name: str, status: str):
    updated = health_service.update_node_status(node_name, status)

    if updated:
        return {"message": f"{node_name} updated to {status}"}
    else:
        return {"error": "Node not found"}