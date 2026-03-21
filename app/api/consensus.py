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