from fastapi import APIRouter
from app.services.consensus import ConsensusService

router = APIRouter()

consensus_service = ConsensusService()

@router.get("/leader")
def get_leader():
    """
    API to get the current leader
    """
    leader = consensus_service.get_leader()
    return {"leader": leader}


@router.post("/start-election")
def start_election():
    """
    Node A triggers election requests to other nodes
    """
    result = consensus_service.send_election_requests()
    return {
        "message": "Election messages sent",
        "responses": result
    }


@router.post("/election")
def receive_election():
    """
    Endpoint for other nodes to receive election request
    """
    return consensus_service.receive_election_request()