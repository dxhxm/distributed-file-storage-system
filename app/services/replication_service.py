import requests
from app.models.config import NODES, CURRENT_NODE
from app.services.jwt_service import get_system_auth_headers


def is_node_alive(node):
    """Check if a node is alive by hitting its /health endpoint."""
    try:
        res = requests.get(f"{node}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


def replicate_file(file_path, filename):
    """Replicate a file to all alive peer nodes with SYSTEM role authentication."""
    for node in NODES:
        if node == CURRENT_NODE:
            continue

        # Skip dead nodes
        if not is_node_alive(node):
            print(f"[REPLICATION] {node} is DOWN - skipping")
            continue

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                headers = get_system_auth_headers()
                response = requests.post(f"{node}/replicate", files=files, headers=headers)

            print(f"[REPLICATION] Sent to {node} - Status: {response.status_code}")

        except Exception as e:
            print(f"[REPLICATION] Failed to send to {node}: {e}")