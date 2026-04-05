from fastapi import APIRouter, Request
from app.services.consensus import ConsensusService

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
async def raft_request_vote(request: Request):
    """Raft RequestVote RPC"""
    data = await request.json()
    return consensus_service.handle_request_vote(
        data.get("term"),
        data.get("candidate_id"),
        data.get("last_log_index"),
        data.get("last_log_term")
    )

@router.post("/raft/append-entries")
async def raft_append_entries(request: Request):
    """Raft AppendEntries RPC"""
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
def fail_leader():
    """Simulate leader failure by stopping its background loop"""
    consensus_service.running = False
    return {"message": "Node background thread stopped. It will no longer respond to Raft elections or heartbeats."}