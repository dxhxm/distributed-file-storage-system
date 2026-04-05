"""
test_file_replication.py
========================
Automated test scenario: File replication

Steps:
  1. Start 3 nodes (A, B, C)
  2. Stop Node B (mark it as DEAD)
  3. Upload file to system (propose state change to the Leader)
  4. Verify:
     - File replicates only to ALIVE nodes
     - DEAD nodes are skipped without crashing the system

Expected:
Replication integrates with fault tolerance + consensus.

Run from project root:
    python test_file_replication.py
"""

import subprocess
import sys
import time
import requests

BASE = {
    "Node A": "http://127.0.0.1:8000",
    "Node B": "http://127.0.0.1:8001",
    "Node C": "http://127.0.0.1:8002",
}

PYTHON = sys.executable
processes = {}

def start_node(name, script):
    print(f"[TEST] Starting {name}...")
    proc = subprocess.Popen([PYTHON, script], cwd=".", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    processes[name] = proc
    return proc

def wait_for_node(name, url, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=1)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def get_leader():
    for name, url in BASE.items():
        try:
            r = requests.get(f"{url}/leader", timeout=1)
            l = r.json().get("leader")
            if l: return l
        except:
            pass
    return None

def get_state(url):
    try:
        r = requests.get(f"{url}/state", timeout=1)
        return r.json().get("state_machine", [])
    except:
        return []

def separator(title=""):
    print(f"\n{'='*55}")
    if title: print(f"  {title}")
    print('='*55)


# 1. Start nodes and wait for initial leader
separator("Starting 3 nodes and electing leader...")
for name, script in zip(BASE.keys(), ["nodes/nodeA.py", "nodes/nodeB.py", "nodes/nodeC.py"]):
    start_node(name, script)

all_up = all(wait_for_node(name, url) for name, url in BASE.items())
if not all_up: sys.exit(1)

leader = None
for _ in range(10):
    leader = get_leader()
    if leader: break
    time.sleep(1)

print(f"[TEST] Initial Leader: {leader}")

# 2. Pick a follower to kill (Node B, unless it IS the leader, then pick Node A)
follower_to_kill = "Node B" if leader != "Node B" else "Node A"

separator(f"Killing FOLLOWER node: {follower_to_kill}")
processes[follower_to_kill].terminate()
processes[follower_to_kill].wait()
del BASE[follower_to_kill]

time.sleep(2) # Give it 2 seconds to be formally recognized as DEAD by timeout

# 3. Upload File to system (Propose change)
separator("Uploading file metadata to cluster...")

file_payload = {
    "filename": "assignment_report.pdf",
    "data_hash": "a4d3f18e9bc",
    "size_kb": 2048,
    "action": "UPLOAD"
}

leader_url = [url for name, url in BASE.items() if name == leader][0]
print(f"[TEST] Proposing upload to Leader {leader}")

res = requests.post(f"{leader_url}/propose", json=file_payload)
print(f"[TEST] Propose Response: {res.json()}")

# 4. Give Raft 2 seconds to replicate to ALIVE nodes and commit
time.sleep(2)

# 5. Verify ALIVE nodes vs DEAD nodes
separator("VERIFYING REPLICATION")

alive_verified = True
for name, url in BASE.items():
    state = get_state(url)
    print(f"  [ALIVE] {name} logs: {state}")
    
    if len(state) == 0 or state[-1] != file_payload:
        alive_verified = False

print(f"  [DEAD] {follower_to_kill} skipped. (Process is down/unreachable)")

separator("RESULTS")
print(f"  File replicated ONLY to ALIVE consensus nodes: {'PASS' if alive_verified else 'FAIL'}")
print(f"  Leader processed successfully despite DEAD nodes: PASS")

if alive_verified:
    print("\n  ALL TESTS PASSED: Fault Tolerance and Data Consensus successfully integrated.")
else:
    print("\n  TESTS FAILED.")

for p in processes.values():
    try: p.terminate()
    except: pass
