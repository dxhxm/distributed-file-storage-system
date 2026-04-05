"""
Node A runner — launches the distributed node on port 8000
"""
import os
import sys

# Add project root to Python path so 'app' package is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set environment variables BEFORE importing the app
os.environ["NODE_NAME"] = "Node A"
os.environ["CURRENT_NODE_URL"] = "http://localhost:8000"
os.environ["STORAGE_DIR"] = os.path.join(PROJECT_ROOT, "nodes", "Node1", "Storage")

# Ensure storage directory exists
os.makedirs(os.environ["STORAGE_DIR"], exist_ok=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
