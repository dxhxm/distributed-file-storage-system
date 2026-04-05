"""
test_leader_failure.py
======================
Automated test scenario: Leader failure

Steps:
  1. Start 3 nodes (A, B, C)
  2. Identify current leader
  3. Stop leader node
  4. Wait for election timeout
  5. Verify:
     - Former leader marked DEAD (by remaining nodes)
     - Election triggered automatically
     - New leader selected consistently across remaining nodes

Expected:
System always maintains a valid leader.

Run from project root:
    python test_leader_failure.py
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
        except Exception:
            pass
        time.sleep(0.5)
    return False

def get_leader(url):
    try:
        r = requests.get(f"{url}/leader", timeout=1)
        return r.json().get("leader")
    except:
        return None

def get_node_status(url):
    try:
        r = requests.get(f"{url}/node-status", timeout=1)
        return r.json()
    except:
        return {}

def separator(title=""):
    print(f"\n{'='*55}")
    if title:
        print(f"  {title}")
    print('='*55)

# STEP 1
separator("STEP 1: Starting 3 nodes and waiting for initial leader election")
for name, script in zip(BASE.keys(), ["nodes/nodeA.py", "nodes/nodeB.py", "nodes/nodeC.py"]):
    start_node(name, script)

all_up = all(wait_for_node(name, url) for name, url in BASE.items())
if not all_up:
    print("[TEST] Failed to start nodes.")
    sys.exit(1)

# STEP 2
leader = None
for _ in range(15):
    leaders = set()
    for name, url in BASE.items():
        l = get_leader(url)
        if l: leaders.add(l)
    
    if len(leaders) == 1:
        leader = list(leaders)[0]
        break
    time.sleep(1)

if not leader:
    print("[TEST] Failed to elect initial leader.")
    sys.exit(1)

print(f"\n[TEST] ---> CURRENT LEADER IDENTIFIED: {leader} <---")

# STEP 3
separator(f"STEP 2 & 3: Terminating Leader Node ({leader})")
processes[leader].terminate()
processes[leader].wait()
lost_leader = leader
del BASE[lost_leader]

# STEP 4 Wait for election
separator("Wait 4s for election timeout and new leader selection...")
time.sleep(4)

# STEP 5 Verify
separator("VERIFYING SYSTEM STATE")

# 1. Check if former leader is marked DEAD by remaining
former_leader_dead = True
for name, url in BASE.items():
    stats = get_node_status(url)
    if stats.get(lost_leader) != "DEAD":
        former_leader_dead = False
        print(f"  [FAIL] {name} does not explicitly mark {lost_leader} as DEAD.")

# 2. Check new leader consistency
new_leaders = set()
for name, url in BASE.items():
    l = get_leader(url)
    if l: new_leaders.add(l)
    print(f"  {name} reports leader = {l}")

new_leader_selected = len(new_leaders) == 1 and list(new_leaders)[0] is not None
if new_leader_selected:
    print(f"\n[TEST] ---> NEW LEADER ELECTED: {list(new_leaders)[0]} <---")

separator("RESULTS")
print(f"  Former leader marked DEAD: {'PASS' if former_leader_dead else 'FAIL'}")
print(f"  New leader valid & consistent: {'PASS' if new_leader_selected else 'FAIL'}")

if former_leader_dead and new_leader_selected:
    print("\n  ALL TESTS PASSED: Fault tolerance + consensus integration works!")
else:
    print("\n  TESTS FAILED.")

for p in processes.values():
    try: p.terminate()
    except: pass
