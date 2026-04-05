import requests
from app.config import NODES, CURRENT_NODE


def is_node_alive(node):
    try:
        res = requests.get(f"{node}/health", timeout=2)
        return res.status_code == 200
    except:
        return False


def replicate_file(file_path, filename):
    for node in NODES:

        if node == CURRENT_NODE:
            continue  

        
        if not is_node_alive(node):
            print(f" Skipping {node} (DOWN)")
            continue

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post(f"{node}/replicate", files=files)

            print(f" Sent to {node} - Status: {response.status_code}")

        except Exception as e:
            print(f" Failed to send to {node}: {e}")