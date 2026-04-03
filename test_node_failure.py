"""
test_node_failure.py
=====================
Automated test scenario: Node B failure

Steps:
  1. Start Node A (port 8000), Node B (port 8001), Node C (port 8002)
  2. Wait for all nodes to be ready
  3. Verify all 3 are healthy
  4. Kill Node B
  5. Wait for health check interval (~7s)
  6. Verify:
     - Node A reports Node B as DEAD via GET /node-status (if endpoint exists)
     - Cluster still responds (no crash)
     - GET /leader on remaining nodes is consistent

Run from project root:
    python test_node_failure.py
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
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                print(f"[TEST] {name} is UP at {url}")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print(f"[TEST] TIMEOUT: {name} did not start within {timeout}s")
    return False


def check_health(name, url):
    try:
        r = requests.get(f"{url}/health", timeout=2)
        status = "HEALTHY" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        status = f"UNREACHABLE ({e})"
    print(f"  {name}: {status}")
    return status == "HEALTHY"


def get_leader(name, url):
    try:
        r = requests.get(f"{url}/leader", timeout=2)
        return r.json().get("leader", "unknown")
    except Exception:
        return "UNREACHABLE"


def get_internal_status(url):
    try:
        r = requests.get(f"{url}/node-status", timeout=2)
        return r.json()
    except Exception:
        return {}


def separator(title=""):
    print(f"\n{'='*55}")
    if title:
        print(f"  {title}")
    print('='*55)


# ──────────────────────────────────────────────────────────
# STEP 1: Start all 3 nodes
# ──────────────────────────────────────────────────────────
separator("STEP 1: Starting 3 nodes")
start_node("Node A", "nodes/nodeA.py")
start_node("Node B", "nodes/nodeB.py")
start_node("Node C", "nodes/nodeC.py")

# ──────────────────────────────────────────────────────────
# STEP 2: Wait for all nodes to be ready
# ──────────────────────────────────────────────────────────
separator("STEP 2: Waiting for nodes to be ready...")
all_up = all(wait_for_node(name, url) for name, url in BASE.items())
if not all_up:
    print("[TEST] Not all nodes started. Aborting.")
    for p in processes.values():
        p.terminate()
    sys.exit(1)

# ──────────────────────────────────────────────────────────
# STEP 3: Verify all nodes healthy
# ──────────────────────────────────────────────────────────
separator("STEP 3: Health check — all nodes")
for name, url in BASE.items():
    check_health(name, url)

print("\n[TEST] Current leader on each node:")
for name, url in BASE.items():
    leader = get_leader(name, url)
    print(f"  {name} believes leader = {leader}")

# ──────────────────────────────────────────────────────────
# STEP 4: Kill Node B
# ──────────────────────────────────────────────────────────
separator("STEP 4: Killing Node B")
processes["Node B"].terminate()
processes["Node B"].wait()
print("[TEST] Node B process terminated.")

# ──────────────────────────────────────────────────────────
# STEP 5: Wait for health-check interval (~7 seconds)
# ──────────────────────────────────────────────────────────
separator("STEP 5: Waiting 8s for health-check to detect failure...")
time.sleep(8)

# ──────────────────────────────────────────────────────────
# STEP 6: Verify fault tolerance
# ──────────────────────────────────────────────────────────
separator("STEP 6: Verifying cluster state after Node B failure")

# Node B should be DEAD (unreachable)
print("\n  Health check:")
node_b_dead = not check_health("Node B", BASE["Node B"])
check_health("Node A", BASE["Node A"])
check_health("Node C", BASE["Node C"])

# Remaining nodes should still respond with a leader
print("\n  Leaders reported by remaining nodes:")
leader_a = get_leader("Node A", BASE["Node A"])
leader_c = get_leader("Node C", BASE["Node C"])
print(f"  Node A believes leader = {leader_a}")
print(f"  Node C believes leader = {leader_c}")

# Verify internal status on remaining nodes
print("\n  Internal cluster status (as seen by Node A):")
status_a = get_internal_status(BASE["Node A"])
for n, s in status_a.items():
    print(f"    {n}: {s}")

node_b_marked_dead = status_a.get("Node B") == "DEAD"

# ──────────────────────────────────────────────────────────
# Results
# ──────────────────────────────────────────────────────────
separator("TEST RESULTS")
results = {
    "Node B marked DEAD (unreachable)": node_b_dead,
    "Node A still responding":          check_health("Node A", BASE["Node A"]),
    "Node C still responding":          check_health("Node C", BASE["Node C"]),
    "Node B marked DEAD in Node A status": node_b_marked_dead,
    "Cluster has a consistent leader":  (leader_a == leader_c and leader_a not in (None, "UNREACHABLE")),
}

all_passed = True
for check, passed in results.items():
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {check}")
    if not passed:
        all_passed = False

separator()
if all_passed:
    print("  ALL TESTS PASSED - Fault tolerance working correctly.")
else:
    print("  SOME TESTS FAILED - Review logs above.")

# ──────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────
separator("Cleanup: Stopping remaining nodes")
for name, proc in processes.items():
    try:
        proc.terminate()
        print(f"  Stopped {name}")
    except Exception:
        pass
