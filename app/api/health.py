import time
from fastapi import APIRouter, HTTPException
from app.services import health_service

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        from app.api.consensus import consensus_service
        node_id = getattr(consensus_service, "current_node", "Node A") if consensus_service else "Node A"
    except Exception:
        node_id = "Node A"

    return {
        "status": "ok",
        "message": "Node is alive",
        "node_id": node_id,
        "timestamp": time.time()
    }


@router.get("/cluster/status")
async def get_cluster_status():
    return health_service.get_cluster_status()


@router.get("/nodes")
async def get_nodes():
    return health_service.get_nodes_info()


@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    node = health_service.get_node_info(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return node


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


@router.get("/nodes/check")
async def check_nodes():
    nodes = health_service.check_all_nodes()
    return {
        "nodes": nodes
    }