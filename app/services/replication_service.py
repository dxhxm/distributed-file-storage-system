import requests
from app.config import NODES, CURRENT_NODE

def replicate_file(file_path, filename):
    for node in NODES:
        if node == CURRENT_NODE:
            continue  

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post(f"{node}/replicate", files=files)

            print(f"Sent to {node} - Status: {response.status_code}")

        except Exception as e:
            print(f"Failed to send to {node}: {e}")