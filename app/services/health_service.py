# In-memory node storage
import httpx
import time
import threading

nodes_status = {
    "nodeA": "ALIVE",
    "nodeB": "ALIVE",
    "nodeC": "ALIVE"
}

NODE_URLS = {
    "nodeA": "http://127.0.0.1:8000",
    "nodeB": "http://127.0.0.1:8001",
    "nodeC": "http://127.0.0.1:8002"
}

def get_all_nodes():
    return nodes_status


def update_node_status(node_name, status):
    if node_name in nodes_status:
        nodes_status[node_name] = status
        return True
    return False

def check_node_health(url, retries=3):
    for _ in range(retries):
        try:
            response = httpx.get(f"{url}/health", timeout=2.0)
            if response.status_code == 200:
                return "ALIVE"
        except:
            pass

    return "DEAD"

def check_all_nodes():
    global nodes_status

    for node, url in NODE_URLS.items():
        new_status = check_node_health(url)

        # Only update if status changed
        if nodes_status[node] != new_status:
            print(f"[STATUS CHANGE] {node}: {nodes_status[node]} → {new_status}")

        nodes_status[node] = new_status

    return nodes_status

def heartbeat_loop():
    while True:
        check_all_nodes()
        time.sleep(5)  # every 5 seconds


def start_heartbeat():
    thread = threading.Thread(target=heartbeat_loop, daemon=True)
    thread.start()
