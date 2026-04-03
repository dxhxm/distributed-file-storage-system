# app/services/consensus.py

import os
import requests
import threading
import time
import logging

# Configure structured logger for this module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("consensus")


class ConsensusService:
    def __init__(self):
        # Node mapping: name -> URL (shared across all instances)
        self.node_urls = {
            "Node A": "http://localhost:8000",
            "Node B": "http://localhost:8001",
            "Node C": "http://localhost:8002"
        }

        # Identity of this node — read from environment variable
        self.current_node = os.environ.get("NODE_NAME", "Node A")
        if self.current_node not in self.node_urls:
            raise ValueError(
                f"NODE_NAME '{self.current_node}' is not in the known node list: {list(self.node_urls.keys())}"
            )

        # Initial leader assumption (highest priority = Node C > B > A)
        self.leader = "Node A"

        # Track node availability
        self.node_status = {name: "ALIVE" for name in self.node_urls}

        # Other nodes in the system (derived from node_urls)
        self.nodes = [url for name, url in self.node_urls.items() if name != self.current_node]

        # Voting state
        self.votes_received = 0
        self.total_nodes = len(self.node_urls)

        # Election synchronization: prevent multiple simultaneous elections
        self.election_in_progress = False
        self.election_lock = threading.Lock()
        # NOTE: background health monitoring is started explicitly via
        # FastAPI's @app.on_event("startup") — not auto-started here.

        logger.info(
            "ConsensusService initialized | node=%s | leader=%s | cluster=%s",
            self.current_node, self.leader, list(self.node_urls.keys())
        )

    def get_leader(self):
        """
        Returns the current leader
        """
        return self.leader

    def simulate_leader_failure(self):
        """
        Simulate leader failure
        """
        logger.warning("[LEADER FAILURE] Simulated failure triggered on %s", self.current_node)
        self.leader = None
        return {"message": "Leader failed. Election required."}

    def get_node_priority(self, node_name):
        """
        Extract the node ID letter and return its ordinal value
        for priority comparison (e.g. 'Node C' -> ord('C') = 67).
        Higher value = higher priority.
        """
        parts = node_name.strip().split()
        if len(parts) == 2:
            return ord(parts[1])
        return 0

    def get_highest_alive_node(self):
        """
        Return the name of the highest-priority ALIVE node.
        Priority: Node C > Node B > Node A (by alphabetical ID, descending).
        """
        alive_nodes = [
            name for name, status in self.node_status.items()
            if status == "ALIVE"
        ]
        if not alive_nodes:
            return None
        return max(alive_nodes, key=self.get_node_priority)

    def send_election_requests(self):
        """
        Deterministic leader election: elect the highest-priority ALIVE node.
        Uses election_in_progress flag to prevent concurrent elections.
        """
        with self.election_lock:
            if self.election_in_progress:
                logger.info("[ELECTION] Already in progress — ignoring new trigger on %s", self.current_node)
                return {
                    "message": "Election already in progress",
                    "leader": self.leader
                }
            self.election_in_progress = True

        logger.info("[ELECTION STARTED] %s is starting a deterministic election...", self.current_node)
        responses = []

        try:
            new_leader = self.get_highest_alive_node()
            if not new_leader:
                logger.error("[ELECTION] No ALIVE nodes available. Cannot elect a leader.")
                return {"message": "No alive nodes", "leader": None}

            logger.info("[ELECTION] Highest-priority ALIVE node: %s -> elected as new leader.", new_leader)
            self.leader = new_leader
            logger.info("[NEW LEADER SELECTED] leader=%s (elected by %s)", new_leader, self.current_node)

            for name, url in self.node_urls.items():
                if name == self.current_node:
                    continue
                if self.node_status.get(name) == "DEAD":
                    logger.debug("[ELECTION] Skipping notification to %s (DEAD)", name)
                    continue

                try:
                    res = requests.post(
                        f"{url}/leader",
                        json={"leader": new_leader},
                        timeout=2
                    )
                    responses.append({
                        "node": name,
                        "response": res.json()
                    })
                except Exception as e:
                    logger.warning("[ELECTION] Failed to notify %s of new leader: %s", name, e)
                    self.update_node_status(name, "DEAD")
                    responses.append({
                        "node": name,
                        "status": "failed",
                        "error": str(e)
                    })

        finally:
            with self.election_lock:
                self.election_in_progress = False
            logger.info("[ELECTION COMPLETE] election_in_progress reset on %s", self.current_node)

        return {
            "elected_leader": self.leader,
            "responses": responses
        }

    def receive_election_request(self, candidate):
        """
        Handle incoming vote request using Bully Algorithm logic.
        Grant vote only if:
          - Candidate has higher priority than this node (higher ID), OR
          - No leader currently exists
        """
        candidate_priority = self.get_node_priority(candidate)
        self_priority = self.get_node_priority(self.current_node)

        vote_granted = (candidate_priority > self_priority) or (self.leader is None)

        if vote_granted:
            logger.info(
                "[VOTE GRANTED] %s grants vote to %s (priority %d vs self %d, leader=%s)",
                self.current_node, candidate, candidate_priority, self_priority, self.leader
            )
        else:
            logger.info(
                "[VOTE DENIED] %s denies vote to %s (priority %d <= self %d)",
                self.current_node, candidate, candidate_priority, self_priority
            )

        return {
            "vote_granted": vote_granted,
            "voted_for": candidate if vote_granted else None,
            "reason": (
                "candidate has higher priority" if candidate_priority > self_priority
                else "no leader exists" if self.leader is None
                else "candidate has lower or equal priority"
            )
        }

    def broadcast_new_leader(self, leader=None, max_retries=3):
        """
        Inform all ALIVE nodes about the new leader.
        Retries up to max_retries times on failure before marking the node DEAD.
        """
        leader_to_announce = leader or self.current_node
        logger.info("[BROADCAST] Announcing new leader '%s' to all ALIVE nodes", leader_to_announce)

        for name, url in self.node_urls.items():
            if name == self.current_node:
                continue
            if self.node_status.get(name) == "DEAD":
                logger.debug("[BROADCAST] Skipping %s (DEAD)", name)
                continue

            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    res = requests.post(
                        f"{url}/leader",
                        json={"leader": leader_to_announce},
                        timeout=2
                    )
                    if res.status_code == 200:
                        logger.info(
                            "[BROADCAST] %s acknowledged new leader '%s' (attempt %d/%d)",
                            name, leader_to_announce, attempt, max_retries
                        )
                        success = True
                        break
                    else:
                        logger.warning(
                            "[BROADCAST] %s returned HTTP %d on attempt %d/%d",
                            name, res.status_code, attempt, max_retries
                        )
                except Exception as e:
                    logger.warning(
                        "[BROADCAST] Failed to reach %s on attempt %d/%d: %s",
                        name, attempt, max_retries, e
                    )

                if attempt < max_retries:
                    time.sleep(1)

            if not success:
                logger.error(
                    "[BROADCAST] %s unreachable after %d attempts. Marking DEAD.",
                    name, max_retries
                )
                self.update_node_status(name, "DEAD")

    def update_leader(self, leader):
        """
        Update leader when notified by another node
        """
        previous = self.leader
        self.leader = leader
        logger.info("[LEADER UPDATE] %s: leader changed %s -> %s", self.current_node, previous, leader)
        return {"message": f"Leader updated to {leader}"}

    def update_node_status(self, node_name, status):
        """
        Update the tracked status of a node and log transitions.
        """
        previous = self.node_status.get(node_name)
        if previous != status:
            if status == "DEAD":
                logger.warning("[NODE STATUS] %s marked DEAD (was %s)", node_name, previous)
            else:
                logger.info("[NODE STATUS] %s marked ALIVE (was %s)", node_name, previous)
            self.node_status[node_name] = status

    def start_health_check(self):
        """
        Start the background health check thread
        """
        thread = threading.Thread(target=self.check_nodes_health_loop, daemon=True)
        thread.start()
        logger.info("[HEALTH CHECK] Background monitoring thread started by %s", self.current_node)

    def check_nodes_health_loop(self):
        """
        Periodically check the health of all nodes
        """
        logger.info("[HEALTH CHECK] Monitoring loop active on %s (interval=5s)", self.current_node)
        while True:
            try:
                for name in self.node_urls.keys():
                    if name != self.current_node:
                        self.check_node_health(name)
            except Exception as e:
                logger.error("[HEALTH CHECK] Unexpected error in monitoring loop: %s", e)
            time.sleep(5)

    def check_node_health(self, node_name):
        """
        Check if a specific node is reachable and healthy
        """
        node_url = self.node_urls.get(node_name)
        if not node_url:
            return

        try:
            response = requests.get(f"{node_url}/health", timeout=2)
            if response.status_code == 200:
                self.update_node_status(node_name, "ALIVE")
            else:
                raise Exception(f"Node returned status code {response.status_code}")
        except Exception as e:
            if self.node_status.get(node_name) == "ALIVE":
                logger.warning("[HEALTH CHECK] %s is unreachable: %s", node_name, e)

            self.update_node_status(node_name, "DEAD")

            if self.leader == node_name:
                logger.warning(
                    "[LEADER FAILURE DETECTED] %s is DOWN. Current node: %s",
                    node_name, self.current_node
                )
                self.leader = None
                highest = self.get_highest_alive_node()
                if highest == self.current_node:
                    logger.info(
                        "[ELECTION TRIGGER] %s has highest priority among ALIVE nodes -> starting election.",
                        self.current_node
                    )
                    self.send_election_requests()
                else:
                    logger.info(
                        "[ELECTION DEFER] %s defers election to higher-priority node: %s",
                        self.current_node, highest
                    )