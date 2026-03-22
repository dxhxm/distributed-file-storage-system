# app/services/consensus.py

import requests


class ConsensusService:
    def __init__(self):
        # Hardcoded leader (simple version)
        self.leader = "Node A"

        # Define other nodes (simulate distributed system)
        self.nodes = [
            "http://localhost:8001",  # Node B
            "http://localhost:8002"   # Node C
        ]

    def get_leader(self):
        """
        Returns the current leader of the system
        """
        return self.leader

    def send_election_requests(self):
        """
        Send election request to all other nodes
        """
        responses = []

        for node in self.nodes:
            try:
                res = requests.post(f"{node}/election")
                responses.append({
                    "node": node,
                    "status": res.json()
                })
            except Exception as e:
                responses.append({
                    "node": node,
                    "status": "failed",
                    "error": str(e)
                })

        return responses

    def receive_election_request(self):
        """
        Handle incoming election request
        """
        return {
            "message": "Election request received"
        }