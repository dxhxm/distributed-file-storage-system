# app/services/consensus.py

import requests


class ConsensusService:
    def __init__(self):
        # Current leader
        self.leader = "Node A"

        # Identity of this node (change when running multiple instances)
        self.current_node = "Node A"

        # Other nodes in the system
        self.nodes = [
            "http://localhost:8001",  # Node B
            "http://localhost:8002"   # Node C
        ]

        # Voting state
        self.votes_received = 0
        self.total_nodes = 3  # including self

    def get_leader(self):
        """
        Returns the current leader
        """
        return self.leader

    def simulate_leader_failure(self):
        """
        Simulate leader failure
        """
        self.leader = None
        return {"message": "Leader failed. Election required."}

    def send_election_requests(self):
        """
        Start election and request votes
        """
        responses = []
        self.votes_received = 1  # vote for self

        for node in self.nodes:
            try:
                res = requests.post(
                    f"{node}/election",
                    json={"candidate": self.current_node}
                )
                data = res.json()

                if data.get("vote_granted"):
                    self.votes_received += 1

                responses.append({
                    "node": node,
                    "response": data
                })

            except Exception as e:
                responses.append({
                    "node": node,
                    "status": "failed",
                    "error": str(e)
                })

        # Majority voting
        if self.votes_received > self.total_nodes // 2:
            self.leader = self.current_node

            # Inform other nodes about new leader
            self.broadcast_new_leader()

        return {
            "votes": self.votes_received,
            "leader": self.leader,
            "responses": responses
        }

    def receive_election_request(self, candidate):
        """
        Handle incoming vote request
        """
        return {
            "vote_granted": True,
            "voted_for": candidate
        }

    def broadcast_new_leader(self):
        """
        Inform other nodes about the new leader
        """
        for node in self.nodes:
            try:
                requests.post(
                    f"{node}/leader",
                    json={"leader": self.current_node}
                )
            except:
                pass

    def update_leader(self, leader):
        """
        Update leader when notified by another node
        """
        self.leader = leader
        return {"message": f"Leader updated to {leader}"}