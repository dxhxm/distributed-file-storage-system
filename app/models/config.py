import os

# All node URLs must match the ports used by uvicorn in the node runner scripts
NODES = [
    "http://localhost:8000",  # Node A
    "http://localhost:8001",  # Node B
    "http://localhost:8002",  # Node C
]

# Determine current node from environment variable (set in each node runner script)
CURRENT_NODE = os.environ.get("CURRENT_NODE_URL", "http://localhost:8000")