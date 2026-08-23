# In-memory node storage
import httpx
import time
import threading
from typing import Optional, Dict, Any

nodes_status: Dict[str, str] = {
    "nodeA": "ALIVE",
    "nodeB": "ALIVE",
    "nodeC": "ALIVE"
}

NODE_URLS: Dict[str, str] = {
    "nodeA": "http://127.0.0.1:8000",
    "nodeB": "http://127.0.0.1:8001",
    "nodeC": "http://127.0.0.1:8002"
}

NODE_DISPLAY_NAMES: Dict[str, str] = {
    "nodeA": "Node A",
    "nodeB": "Node B",
    "nodeC": "Node C"
}

last_heartbeats: Dict[str, float] = {
    "nodeA": time.time(),
    "nodeB": time.time(),
    "nodeC": time.time()
}


def _get_consensus_service() -> Optional[Any]:
    try:
        from app.api.consensus import consensus_service
        return consensus_service
    except Exception:
        return None


def get_all_nodes() -> Dict[str, str]:
    return nodes_status


def update_node_status(node_name: str, status: str) -> bool:
    if node_name in nodes_status:
        nodes_status[node_name] = status
        if status == "ALIVE":
            last_heartbeats[node_name] = time.time()
        return True
    return False


def check_node_health(url: str, retries: int = 3) -> str:
    for _ in range(retries):
        try:
            response = httpx.get(f"{url}/health", timeout=2.0)
            if response.status_code == 200:
                return "ALIVE"
        except Exception:
            pass

    return "DEAD"


def check_all_nodes() -> Dict[str, str]:
    global nodes_status, last_heartbeats

    for node, url in NODE_URLS.items():
        new_status = check_node_health(url)

        # Only update if status changed
        if nodes_status[node] != new_status:
            print(f"[STATUS CHANGE] {node}: {nodes_status[node]} → {new_status}")

        nodes_status[node] = new_status
        if new_status == "ALIVE":
            last_heartbeats[node] = time.time()

    return nodes_status


def heartbeat_loop() -> None:
    while True:
        check_all_nodes()
        time.sleep(5)  # every 5 seconds


def start_heartbeat() -> None:
    thread = threading.Thread(target=heartbeat_loop, daemon=True)
    thread.start()


def get_cluster_status() -> Dict[str, Any]:
    cs = _get_consensus_service()

    total_nodes = len(NODE_URLS)
    active_nodes = sum(1 for status in nodes_status.values() if status == "ALIVE")
    leader_id = getattr(cs, "leader_id", None) if cs else None
    term = getattr(cs, "current_term", 0) if cs else 0
    commit_index = getattr(cs, "commit_index", -1) if cs else -1

    # Quorum is majority: > total_nodes // 2
    quorum = (total_nodes // 2) + 1
    
    if active_nodes == total_nodes and leader_id is not None:
        cluster_state = "HEALTHY"
    elif active_nodes >= quorum and leader_id is not None:
        cluster_state = "OPERATIONAL"
    else:
        cluster_state = "NO MAJORITY"

    return {
        "cluster_state": cluster_state,
        "leader_id": leader_id,
        "term": term,
        "commit_index": commit_index,
        "active_nodes": active_nodes,
        "total_nodes": total_nodes,
        "timestamp": time.time()
    }


def get_nodes_info() -> Dict[str, Any]:
    cs = _get_consensus_service()

    current_node = getattr(cs, "current_node", "Node A") if cs else "Node A"
    leader_id = getattr(cs, "leader_id", None) if cs else None
    current_state = getattr(cs, "state", "FOLLOWER") if cs else "FOLLOWER"

    node_list = []
    for key, url in NODE_URLS.items():
        display_name = NODE_DISPLAY_NAMES.get(key, key)
        is_alive = nodes_status.get(key) == "ALIVE"
        status = "ONLINE" if is_alive else "OFFLINE"

        # Determine node state
        if display_name == current_node:
            state = current_state
        elif display_name == leader_id:
            state = "LEADER"
        else:
            state = "FOLLOWER"

        node_list.append({
            "id": display_name,
            "state": state,
            "last_heartbeat": last_heartbeats.get(key, time.time()),
            "status": status,
            "url": url
        })

    return {"nodes": node_list}


def get_node_info(node_id: str) -> Optional[Dict[str, Any]]:
    nodes_info = get_nodes_info()["nodes"]
    cleaned_id = node_id.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    
    for node in nodes_info:
        node_clean = node["id"].lower().replace(" ", "").replace("-", "").replace("_", "")
        if node_clean == cleaned_id or node["id"].lower() == node_id.strip().lower():
            return node
    return None

