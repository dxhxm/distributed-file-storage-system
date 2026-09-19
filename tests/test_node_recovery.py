"""
test_node_recovery.py
======================
Automated test scenario: Node recovery

Steps:
  1. Start 3 nodes, elect Leader
  2. Kill a FOLLOWER node (simulating failure)
  3. Upload new files (append logs) while node is DEAD
  4. Restart the failed FOLLOWER node
  5. Verify:
     - The Leader marks the node back as ALIVE
     - The recovered node receives updated leader info automatically
     - The recovered node explicitly synchronizes missing data and rejoins the system

Expected:
System dynamically adapts to node recovery.

Run from project root:
    python test_node_recovery.py
"""

import subprocess
import sys
import time
import os
import signal
import requests

BASE = {
    "Node A": "http://127.0.0.1:8000",
    "Node B": "http://127.0.0.1:8001",
    "Node C": "http://127.0.0.1:8002",
}

PYTHON = sys.executable
processes = {}


def cleanup_ports():
    """Kill any leftover processes on ports 8000-8002 from previous test runs."""
    for port in [8000, 8001, 8002]:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True
            )
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except (ProcessLookupError, ValueError):
                        pass
        except Exception:
            pass
    time.sleep(1)


cleanup_ports()

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

def get_leader(url):
    try:
        return requests.get(f"{url}/leader", timeout=1).json().get("leader")
    except:
        return None

def get_node_status(url):
    try:
        return requests.get(f"{url}/node-status", timeout=1).json()
    except:
        return {}

def get_state(url):
    try:
        return requests.get(f"{url}/state", timeout=1).json().get("state_machine", [])
    except:
        return []

def separator(title=""):
    print(f"\n{'='*55}")
    if title: print(f"  {title}")
    print('='*55)


# 1. Start nodes
separator("Starting 3 nodes and electing leader...")
scripts = {"Node A": "nodes/nodeA.py", "Node B": "nodes/nodeB.py", "Node C": "nodes/nodeC.py"}
for name, script in scripts.items():
    start_node(name, script)

all_up = all(wait_for_node(name, url) for name, url in BASE.items())
if not all_up: sys.exit(1)

leader = None
for _ in range(10):
    leaders = set()
    for n, u in BASE.items():
        l = get_leader(u)
        if l: leaders.add(l)
    if len(leaders) == 1:
        leader = list(leaders)[0]
        break
    time.sleep(1)

print(f"[TEST] Cluster Leader: {leader}")

# 2. Kill FOLLOWER
follower_to_kill = "Node C" if leader != "Node C" else "Node B"
separator(f"Killing FOLLOWER node: {follower_to_kill}")
processes[follower_to_kill].terminate()
processes[follower_to_kill].wait()

time.sleep(2) # Give it 2 seconds to be formally recognized as DEAD by timeout

# 3. Formally upload Data while node is DEAD
leader_url = BASE[leader]
separator("Uploading File 1 while Node is DEAD")
payload1 = {"filename": "data_during_downtime.txt", "action": "UPLOAD"}
print(f"[TEST] Proposing to Leader: {payload1}")
requests.post(f"{leader_url}/propose", json=payload1)

time.sleep(2) # Commit block

# 4. Restart FOLLOWER
separator(f"Restarting Previously Stopped Node: {follower_to_kill}")
start_node(follower_to_kill, scripts[follower_to_kill])
wait_for_node(follower_to_kill, BASE[follower_to_kill])

# 5. Wait for dynamic synchronization
separator("Waiting 4s for dynamic recovery and state synchronization...")
time.sleep(4)

# 6. Verify conditions
separator("VERIFYING RECOVERY")

leader_status_report = get_node_status(leader_url)
is_marked_alive = leader_status_report.get(follower_to_kill) == "ALIVE"
print(f"  Leader marks {follower_to_kill} ALIVE: {'PASS' if is_marked_alive else 'FAIL'}")

recovered_leader_info = get_leader(BASE[follower_to_kill])
recognizes_leader = recovered_leader_info == leader
print(f"  Recovered node explicitly detects Leader {leader}: {'PASS' if recognizes_leader else 'FAIL'}")

recovered_state = get_state(BASE[follower_to_kill])
print(f"  Recovered Node's State Log: {recovered_state}")
fully_synchronized = len(recovered_state) > 0 and recovered_state[-1] == payload1
print(f"  Recovered Node re-synced missing data: {'PASS' if fully_synchronized else 'FAIL'}")

separator("RESULTS")
if is_marked_alive and recognizes_leader and fully_synchronized:
    print("  ALL TESTS PASSED: System dynamically and completely adapts to node recovery.")
else:
    print("  TESTS FAILED.")

for p in processes.values():
    try: p.terminate()
    except: pass
