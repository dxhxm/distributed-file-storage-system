"""
Node C runner — launches the distributed node on port 8002
"""
import os
import sys

# Add project root to Python path so 'app' package is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set environment variables BEFORE importing the app
os.environ["NODE_NAME"] = "Node C"
os.environ["CURRENT_NODE_URL"] = "http://localhost:8002"
os.environ["STORAGE_DIR"] = os.path.join(PROJECT_ROOT, "nodes", "Node3", "Storage")

# Ensure storage directory exists
os.makedirs(os.environ["STORAGE_DIR"], exist_ok=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002)
