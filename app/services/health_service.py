# In-memory node storage

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

import httpx

def check_node_health(node_name, url):
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
        status = check_node_health(node, url)
        nodes_status[node] = status

    return nodes_status