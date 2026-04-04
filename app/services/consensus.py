import os
import requests
import threading
import time
import logging
import random

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("raft")

class State:
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"

class ConsensusService:
    def __init__(self):
        self.node_urls = {
            "Node A": "http://localhost:8000",
            "Node B": "http://localhost:8001",
            "Node C": "http://localhost:8002"
        }
        self.current_node = os.environ.get("NODE_NAME", "Node A")
        if self.current_node not in self.node_urls:
            raise ValueError(f"Unknown NODE_NAME: {self.current_node}")

        self.peers = {k: v for k, v in self.node_urls.items() if k != self.current_node}
        self.lock = threading.Lock()

        # Persistent state on all servers (simulated in memory)
        self.current_term = 0
        self.voted_for = None
        self.log = [] # List of {"term": int, "data": Any}
        
        # Volatile state on all servers
        self.commit_index = -1
        self.last_applied = -1
        self.state_machine = [] # Applied JSON data blocks
        
        # Volatile state on leaders
        self.next_index = {p: 0 for p in self.peers}
        self.match_index = {p: -1 for p in self.peers}
        
        self.node_status = {name: "ALIVE" for name in self.peers}
        self.node_status[self.current_node] = "ALIVE"

        self.state = State.FOLLOWER
        self.leader_id = None
        
        # Timers / election config
        # Scaled up timeouts so they work consistently in a single-machine testing environment
        self.election_timeout_range = (2.0, 4.0) 
        self.heartbeat_interval = 0.5
        self.last_heartbeat_time = time.time()
        
        self.running = True
        logger.info(f"Raft Consensus Node Initialized: {self.current_node}")

    def get_last_log_index(self):
        return len(self.log) - 1

    def get_last_log_term(self):
        idx = self.get_last_log_index()
        if idx >= 0:
            return self.log[idx]["term"]
        return 0

    def start_background_tasks(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="Raft-Loop")
        self.thread.start()

    def _run_loop(self):
        while self.running:
            with self.lock:
                state = self.state
            
            if state in (State.FOLLOWER, State.CANDIDATE):
                self._check_election_timeout()
            elif state == State.LEADER:
                self._send_heartbeats()
                
            time.sleep(0.1)

    def _get_randomized_timeout(self):
        if not hasattr(self, '_current_timeout'):
            self._current_timeout = random.uniform(*self.election_timeout_range)
        return self._current_timeout

    def _reset_election_timeout(self):
        self.last_heartbeat_time = time.time()
        self._current_timeout = random.uniform(*self.election_timeout_range)

    def _check_election_timeout(self):
        with self.lock:
            elapsed = time.time() - self.last_heartbeat_time
            if elapsed > self._get_randomized_timeout():
                # Transition to candidate
                self.state = State.CANDIDATE
                self.current_term += 1
                self.voted_for = self.current_node
                self._reset_election_timeout()
                
                term = self.current_term
                last_log_index = self.get_last_log_index()
                last_log_term = self.get_last_log_term()
                
                logger.info(f"==> ELECTION TIMEOUT! Becoming candidate for Term {term} <==")
                
                # Asynchronously request votes
                threading.Thread(
                    target=self._run_election, 
                    args=(term, last_log_index, last_log_term),
                    daemon=True
                ).start()

    def _run_election(self, term, last_log_index, last_log_term):
        votes = 1 # vote for self
        
        for peer, url in self.peers.items():
            try:
                payload = {
                    "term": term,
                    "candidate_id": self.current_node,
                    "last_log_index": last_log_index,
                    "last_log_term": last_log_term
                }
                res = requests.post(f"{url}/raft/request-vote", json=payload, timeout=1.0)
                if res.status_code == 200:
                    data = res.json()
                    
                    with self.lock:
                        if data["term"] > self.current_term:
                            self.current_term = data["term"]
                            self.state = State.FOLLOWER
                            self.voted_for = None
                            return
                        if self.state == State.CANDIDATE and self.current_term == term and data["vote_granted"]:
                            votes += 1
            except Exception:
                pass

        with self.lock:
            if self.state == State.CANDIDATE and self.current_term == term:
                if votes > (len(self.node_urls) // 2):
                    logger.info(f"*** ELECTION WON *** Elected as LEADER for Term {term}")
                    self.state = State.LEADER
                    self.leader_id = self.current_node
                    
                    next_idx = self.get_last_log_index() + 1
                    for p in self.peers:
                        self.next_index[p] = next_idx
                        self.match_index[p] = -1
                    
                    # Immediately send out heartbeat
                    threading.Thread(target=self._send_heartbeats_unlocked, daemon=True).start()

    def _send_heartbeats(self):
        with self.lock:
            if self.state != State.LEADER:
                return
            elapsed = time.time() - self.last_heartbeat_time
            if elapsed < self.heartbeat_interval:
                return
            self.last_heartbeat_time = time.time()

        self._send_heartbeats_unlocked()

    def _send_heartbeats_unlocked(self):
        for peer, url in self.peers.items():
            threading.Thread(target=self._send_append_entries_to_peer, args=(peer, url), daemon=True).start()

    def _send_append_entries_to_peer(self, peer, url):
        with self.lock:
            if self.state != State.LEADER:
                return
            term = self.current_term
            leader_id = self.current_node
            leader_commit = self.commit_index
            
            next_idx = self.next_index[peer]
            prev_log_index = next_idx - 1
            prev_log_term = 0
            if prev_log_index >= 0 and prev_log_index < len(self.log):
                prev_log_term = self.log[prev_log_index]["term"]
                
            entries = self.log[next_idx:]
            
        payload = {
            "term": term,
            "leader_id": leader_id,
            "prev_log_index": prev_log_index,
            "prev_log_term": prev_log_term,
            "entries": entries,
            "leader_commit": leader_commit
        }
        
        try:
            res = requests.post(f"{url}/raft/append-entries", json=payload, timeout=1.0)
            if res.status_code == 200:
                self.node_status[peer] = "ALIVE"
                data = res.json()
                with self.lock:
                    if self.state != State.LEADER or self.current_term != term:
                        return
                    if data["term"] > self.current_term:
                        self.current_term = data["term"]
                        self.state = State.FOLLOWER
                        self.voted_for = None
                        return
                        
                    if data["success"]:
                        if entries:
                            self.match_index[peer] = prev_log_index + len(entries)
                            self.next_index[peer] = self.match_index[peer] + 1
                            self._update_commit_index()
                    else:
                        # Follower rejected due to log inconsistency, backpedal next_index
                        self.next_index[peer] = max(0, self.next_index[peer] - 1)
        except Exception:
            self.node_status[peer] = "DEAD"

    def _update_commit_index(self):
        # A leader can only commit entries from its current term
        for N in range(self.get_last_log_index(), self.commit_index, -1):
            if self.log[N]["term"] != self.current_term:
                continue
            count = 1 # Self
            for p, m_idx in self.match_index.items():
                if m_idx >= N:
                    count += 1
            if count > (len(self.node_urls) // 2):
                self.commit_index = N
                self._apply_logs()
                break

    def _apply_logs(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.state_machine.append(entry["data"])
            logger.info(f"--> [COMMITTED STATE] State Machine Applied Log[{self.last_applied}]: {entry['data']}")

    def handle_request_vote(self, term, candidate_id, last_log_index, last_log_term):
        with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.state = State.FOLLOWER
                self.voted_for = None
                
            vote_granted = False
            
            if term == self.current_term:
                if self.voted_for is None or self.voted_for == candidate_id:
                    my_last_term = self.get_last_log_term()
                    my_last_index = self.get_last_log_index()
                    
                    if last_log_term > my_last_term or (last_log_term == my_last_term and last_log_index >= my_last_index):
                        vote_granted = True
                        self.voted_for = candidate_id
                        self._reset_election_timeout()
                        logger.info(f"Granted vote to {candidate_id} for Term {term}")

            return {"term": self.current_term, "vote_granted": vote_granted}

    def handle_append_entries(self, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit):
        with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.state = State.FOLLOWER
                self.voted_for = None
                
            if term < self.current_term:
                return {"term": self.current_term, "success": False}
                
            self._reset_election_timeout()
            self.leader_id = leader_id
            self.state = State.FOLLOWER
            
            # Raft log consistency check
            if prev_log_index >= 0:
                if prev_log_index >= len(self.log):
                    return {"term": self.current_term, "success": False}
                if self.log[prev_log_index]["term"] != prev_log_term:
                    # Truncate conflicting entries
                    self.log = self.log[:prev_log_index]
                    return {"term": self.current_term, "success": False}
                    
            # Safe to append entries
            if entries:
                insert_idx = prev_log_index + 1
                self.log = self.log[:insert_idx] + entries
                logger.debug(f"Appended {len(entries)} entries from Leader {leader_id}")

            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, self.get_last_log_index())
                self._apply_logs()
                    
            return {"term": self.current_term, "success": True}

    def propose(self, data):
        with self.lock:
            if self.state != State.LEADER:
                return {"success": False, "error": "Not Leader", "leader_id": self.leader_id}
                
            entry = {"term": self.current_term, "data": data}
            self.log.append(entry)
            idx = self.get_last_log_index()
            logger.info(f"[PROPOSE] Received new data block: {data}. Appended to uncommitted log at index {idx}")
            
        threading.Thread(target=self._send_heartbeats_unlocked, daemon=True).start()
        return {"success": True, "index": idx, "term": self.current_term}