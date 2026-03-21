class ConsensusService:
    def __init__(self):
        # Hardcoded leader (simple version)
        self.leader = "Node A"

    def get_leader(self):
        """
        Returns the current leader of the system
        """
        return self.leader