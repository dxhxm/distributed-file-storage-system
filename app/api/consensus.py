# app/api/consensus.py

from fastapi import APIRouter, Request
from app.services.consensus import ConsensusService

router = APIRouter()

consensus_service = ConsensusService()


@router.get("/leader")
def get_leader():
    """
    Get current leader
    """
    return {"leader": consensus_service.get_leader()}


@router.post("/fail-leader")
def fail_leader():
    """
    Simulate leader failure
    """
    return consensus_service.simulate_leader_failure()


@router.post("/start-election")
def start_election():
    """
    Start leader election
    """
    result = consensus_service.send_election_requests()
    return {
        "message": "Election completed",
        "result": result
    }


@router.post("/election")
async def receive_election(request: Request):
    """
    Receive vote request
    """
    body = await request.json()
    candidate = body.get("candidate")

    return consensus_service.receive_election_request(candidate)


@router.post("/leader")
async def update_leader(request: Request):
    """
    Receive new leader announcement
    """
    body = await request.json()
    leader = body.get("leader")

    return consensus_service.update_leader(leader)