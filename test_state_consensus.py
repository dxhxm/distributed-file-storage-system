"""
test_state_consensus.py
========================
Automated test scenario: State Replication Consensus (Raft)

Steps:
  1. Start Node A, Node B, Node C
  2. Wait for leader election (up to 5s)
  3. Determine the Leader
  4. Propose a JSON state change block to the Leader
  5. Wait for replication (up to 3s)
  6. Verify all 3 nodes have the committed state
  7. Kill Node B
  8. Propose another state change
  9. Verify remaining nodes (A, C) commit the new state.

Run from project root:
    python test_state_consensus.py
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
    print(f"\n[TEST] Starting {name} via {script}...")
    proc = subprocess.Popen(
        [PYTHON, script],
        cwd=".",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes[name] = proc
    return proc

def wait_for_node(name, url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=1)
            if r.status_code == 200:
                print(f"[TEST] {name} is UP at {url}")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def get_leader_from_all():
    leaders = set()
    actual_leader = None
    for name, url in BASE.items():
        try:
            r = requests.get(f"{url}/leader", timeout=1)
            l = r.json().get("leader")
            if l:
                leaders.add(l)
        except:
            pass
    if len(leaders) == 1:
        return list(leaders)[0]
    return None

def get_state(url):
    try:
        r = requests.get(f"{url}/state", timeout=1)
        return r.json()
    except Exception:
        return {}

def separator(title=""):
    print(f"\n{'='*55}")
    if title:
        print(f"  {title}")
    print('='*55)

separator("STEP 1: Starting 3 nodes")
start_node("Node A", "nodes/nodeA.py")
start_node("Node B", "nodes/nodeB.py")
start_node("Node C", "nodes/nodeC.py")

separator("STEP 2: Waiting for nodes to start...")
all_up = all(wait_for_node(name, url) for name, url in BASE.items())
if not all_up:
    print("[TEST] Failed to start all nodes.")
    for p in processes.values(): p.terminate()
    sys.exit(1)

separator("STEP 3: Wait for Raft Leader Election")
leader = None
for _ in range(15):
    leader = get_leader_from_all()
    if leader:
        break
    time.sleep(1)

if not leader:
    print("[TEST] Leader election failed.")
    for p in processes.values(): p.terminate()
    sys.exit(1)

print(f"[TEST] Cluster elected Leader: {leader}")

separator("STEP 4: Propose state change to the Leader")
leader_url = BASE[leader]
payload1 = {"filename": "test.txt", "action": "UPLOAD", "size": 1024}
print(f"[TEST] Proposing to {leader}: {payload1}")

r = requests.post(f"{leader_url}/propose", json=payload1)
print(f"[TEST] Propose Response: {r.json()}")

separator("STEP 5: Wait until all nodes have applied state (up to 10s)")
for _ in range(10):
    all_replicated = True
    for name, url in BASE.items():
        st = get_state(url)
        sm = st.get("state_machine", [])
        if not sm or sm[-1] != payload1:
            all_replicated = False
            break
    if all_replicated:
        break
    time.sleep(1)

separator("STEP 6: Verify all nodes have applied state")
verification_passed = True
for name, url in BASE.items():
    st = get_state(url)
    sm = st.get("state_machine", [])
    print(f"  {name} State Machine: {sm}")
    if len(sm) == 0 or sm[0] != payload1:
        verification_passed = False

separator("STEP 7: Kill Node B")
print("[TEST] Terminating Node B...")
processes["Node B"].terminate()
processes["Node B"].wait()

# If Node B was leader, wait for an election!
if leader == "Node B":
    print("[TEST] Node B was Leader! Waiting for new election...")
    time.sleep(4)
    del BASE["Node B"]
    leader = None
    for _ in range(10):
        leader = get_leader_from_all()
        if leader:
            break
        time.sleep(1)
    if not leader:
        print("[TEST] Failed to elect new leader")
        for p in processes.values(): p.terminate()
        sys.exit(1)
    print(f"[TEST] New Leader is: {leader}")
    leader_url = BASE[leader]
else:
    del BASE["Node B"]
    time.sleep(1)

separator("STEP 8: Propose another state change")
payload2 = {"filename": "hello.txt", "action": "DELETE"}
print(f"[TEST] Proposing to {leader}: {payload2}")
requests.post(f"{leader_url}/propose", json=payload2)

separator("STEP 9: Wait and Verify remaining nodes (up to 10s)")
for _ in range(10):
    all_replicated = True
    for name, url in BASE.items():
        st = get_state(url)
        sm = st.get("state_machine", [])
        if len(sm) < 2 or sm[-1] != payload2:
            all_replicated = False
            break
    if all_replicated:
        break
    time.sleep(1)

final_passed = True
for name, url in BASE.items():
    st = get_state(url)
    sm = st.get("state_machine", [])
    print(f"  {name} State Machine: {sm}")
    if len(sm) < 2 or sm[1] != payload2:
        final_passed = False

separator("RESULTS")
print(f"  Initial Replication to 3 Nodes: {'PASS' if verification_passed else 'FAIL'}")
print(f"  Secondary Replication to 2 Nodes: {'PASS' if final_passed else 'FAIL'}")

if verification_passed and final_passed:
    print("\n  ALL TESTS PASSED: Raft State Replication works perfectly!")
else:
    print("\n  SOME TESTS FAILED.")

for p in processes.values():
    try: p.terminate()
    except: pass
