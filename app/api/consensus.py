from fastapi import APIRouter, Depends, Request
from app.services.consensus import ConsensusService
from app.api.dependencies import AuthenticatedUser, require_admin, require_system

router = APIRouter()
consensus_service = ConsensusService()

@router.get("/leader")
def get_leader():
    """Get current leader"""
    return {"leader": consensus_service.leader_id}

@router.get("/state")
def get_state():
    """Get the current committed state machine log"""
    with consensus_service.lock:
        return {
            "state_machine": consensus_service.state_machine,
            "commit_index": consensus_service.commit_index,
            "term": consensus_service.current_term,
            "leader_id": consensus_service.leader_id
        }

@router.post("/propose")
async def propose_state_change(request: Request):
    """
    Client endpoint to propose a generic JSON data block.
    Only the Leader will accept this.
    """
    data = await request.json()
    return consensus_service.propose(data)

@router.post("/raft/request-vote")
async def raft_request_vote(
    request: Request,
    current_system: AuthenticatedUser = Depends(require_system),
):
    """Raft RequestVote RPC - Restricted to SYSTEM role inter-node callers."""
    data = await request.json()
    return consensus_service.handle_request_vote(
        data.get("term"),
        data.get("candidate_id"),
        data.get("last_log_index"),
        data.get("last_log_term")
    )

@router.post("/raft/append-entries")
async def raft_append_entries(
    request: Request,
    current_system: AuthenticatedUser = Depends(require_system),
):
    """Raft AppendEntries RPC - Restricted to SYSTEM role inter-node callers."""
    data = await request.json()
    return consensus_service.handle_append_entries(
        data.get("term"),
        data.get("leader_id"),
        data.get("prev_log_index"),
        data.get("prev_log_term"),
        data.get("entries", []),
        data.get("leader_commit")
    )

from app.services.health_service import get_all_nodes

@router.get("/node-status")
def get_node_status():
    """Return local node's internal view"""
    status_map = {
        "nodeA": "Node A",
        "nodeB": "Node B",
        "nodeC": "Node C"
    }
    raw_status = get_all_nodes()
    return {status_map.get(k, k): v for k, v in raw_status.items()}

@router.post("/fail-leader")
def fail_leader(
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """Simulate leader failure by stopping its background loop - Restricted to ADMIN."""
    consensus_service.running = False
    return {"message": "Node background thread stopped. It will no longer respond to Raft elections or heartbeats."}


from typing import Optional
from fastapi import Body, HTTPException, Query
from app.models.cluster_config_model import UpdateClusterConfigRequest, ClusterConfigResponse


@router.get("/cluster/config", response_model=ClusterConfigResponse)
def get_cluster_config_endpoint(
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Get active cluster configuration tunables (election timeouts, heartbeat interval).
    Restricted to ADMIN role.
    """
    config = consensus_service.get_cluster_config()
    return ClusterConfigResponse(**config)


@router.post("/cluster/config", response_model=ClusterConfigResponse)
@router.put("/cluster/config", response_model=ClusterConfigResponse)
def update_cluster_config_endpoint(
    payload: Optional[UpdateClusterConfigRequest] = Body(None),
    election_timeout_min: Optional[float] = Query(None),
    election_timeout_max: Optional[float] = Query(None),
    heartbeat_interval: Optional[float] = Query(None),
    health_check_interval: Optional[float] = Query(None),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Update active cluster configuration tunables with validation.
    Restricted to ADMIN role.
    """
    req_min = payload.election_timeout_min if payload and payload.election_timeout_min is not None else election_timeout_min
    req_max = payload.election_timeout_max if payload and payload.election_timeout_max is not None else election_timeout_max
    req_hb = payload.heartbeat_interval if payload and payload.heartbeat_interval is not None else heartbeat_interval
    req_hc = payload.health_check_interval if payload and payload.health_check_interval is not None else health_check_interval

    # Validate non-negative numbers if passed via query params
    for name, val in [
        ("election_timeout_min", req_min),
        ("election_timeout_max", req_max),
        ("heartbeat_interval", req_hb),
        ("health_check_interval", req_hc),
    ]:
        if val is not None and val <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration value for {name}: {val}. Must be greater than 0."
            )

    try:
        updated = consensus_service.update_cluster_config(
            election_timeout_min=req_min,
            election_timeout_max=req_max,
            heartbeat_interval=req_hb,
            health_check_interval=req_hc,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cluster configuration: {str(exc)}"
        ) from exc

    return ClusterConfigResponse(
        **updated,
        message="Cluster configuration updated successfully"
    )