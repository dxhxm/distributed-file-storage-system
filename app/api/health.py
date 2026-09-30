import time
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from app.api.dependencies import AuthenticatedUser, require_admin, require_role
from app.models.user_model import Role
from app.models.node_model import NodeActionRequest, AddNodeRequest, UpdateNodeRequest
from app.services import health_service

router = APIRouter()


@router.get("/health")
async def health_check(
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
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
async def get_cluster_status(
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
    return health_service.get_cluster_status()


@router.get("/nodes")
async def get_nodes(
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
    return health_service.get_nodes_info()


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
    node = health_service.get_node_info(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return node


@router.get("/nodes/status")
async def get_node_status(
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
    nodes = health_service.get_all_nodes()
    return {
        "nodes": nodes
    }


@router.post("/nodes/update")
async def update_node(
    node_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    payload: Optional[UpdateNodeRequest] = Body(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    target_node = (payload.node_name if payload and payload.node_name else node_name) or ""
    target_status = (payload.status if payload and payload.status else status) or ""
    if not target_node or not target_status:
        raise HTTPException(status_code=400, detail="node_name and status are required")
    updated = health_service.update_node_status(target_node, target_status)

    if updated:
        return {"message": f"{target_node} updated to {target_status}"}
    else:
        return {"error": "Node not found"}


@router.post("/nodes/remove")
@router.delete("/nodes/remove")
async def remove_node_endpoint(
    node_name: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    payload: Optional[NodeActionRequest] = Body(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    target = (
        (payload.node_name if payload and payload.node_name else None)
        or (payload.node_id if payload and payload.node_id else None)
        or node_name
        or node_id
        or ""
    )
    if not target:
        raise HTTPException(status_code=400, detail="node_name or node_id is required")
    removed = health_service.remove_node(target)
    if removed:
        return {"message": f"Node '{target}' removed successfully", "node_id": target, "status": "REMOVED"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{target}' not found")


@router.post("/nodes/{node_id}/remove")
@router.delete("/nodes/{node_id}")
async def remove_node_by_path(
    node_id: str,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    removed = health_service.remove_node(node_id)
    if removed:
        return {"message": f"Node '{node_id}' removed successfully", "node_id": node_id, "status": "REMOVED"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")


@router.post("/nodes/cordon")
async def cordon_node_endpoint(
    node_name: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    payload: Optional[NodeActionRequest] = Body(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    target = (
        (payload.node_name if payload and payload.node_name else None)
        or (payload.node_id if payload and payload.node_id else None)
        or node_name
        or node_id
        or ""
    )
    if not target:
        raise HTTPException(status_code=400, detail="node_name or node_id is required")
    cordoned = health_service.cordon_node(target)
    if cordoned:
        return {"message": f"Node '{target}' cordoned successfully", "node_id": target, "status": "CORDONED"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{target}' not found")


@router.post("/nodes/{node_id}/cordon")
async def cordon_node_by_path(
    node_id: str,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    cordoned = health_service.cordon_node(node_id)
    if cordoned:
        return {"message": f"Node '{node_id}' cordoned successfully", "node_id": node_id, "status": "CORDONED"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")


@router.post("/nodes/uncordon")
async def uncordon_node_endpoint(
    node_name: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    payload: Optional[NodeActionRequest] = Body(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    target = (
        (payload.node_name if payload and payload.node_name else None)
        or (payload.node_id if payload and payload.node_id else None)
        or node_name
        or node_id
        or ""
    )
    if not target:
        raise HTTPException(status_code=400, detail="node_name or node_id is required")
    uncordoned = health_service.uncordon_node(target)
    if uncordoned:
        return {"message": f"Node '{target}' uncordoned successfully", "node_id": target, "status": "ALIVE"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{target}' not found")


@router.post("/nodes/{node_id}/uncordon")
async def uncordon_node_by_path(
    node_id: str,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    uncordoned = health_service.uncordon_node(node_id)
    if uncordoned:
        return {"message": f"Node '{node_id}' uncordoned successfully", "node_id": node_id, "status": "ALIVE"}
    else:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")


@router.post("/nodes/add")
async def add_node_endpoint(
    node_name: Optional[str] = Query(None),
    url: Optional[str] = Query(None),
    display_name: Optional[str] = Query(None),
    payload: Optional[AddNodeRequest] = Body(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    target_name = (payload.node_name if payload and payload.node_name else node_name) or ""
    target_url = (payload.url if payload and payload.url else url) or ""
    target_display = payload.display_name if payload and payload.display_name else display_name
    if not target_name or not target_url:
        raise HTTPException(status_code=400, detail="node_name and url are required")
    health_service.add_node(target_name, target_url, target_display)
    return {"message": f"Node '{target_name}' added successfully", "node_name": target_name, "url": target_url}


@router.get("/nodes/check")
async def check_nodes(
    current_user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN, Role.SYSTEM)),
):
    nodes = health_service.check_all_nodes()
    return {
        "nodes": nodes
    }