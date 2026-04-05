"""
Node B runner — launches the distributed node on port 8001
"""
import os
import sys

# Add project root to Python path so 'app' package is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set environment variables BEFORE importing the app
os.environ["NODE_NAME"] = "Node B"
os.environ["CURRENT_NODE_URL"] = "http://localhost:8001"
os.environ["STORAGE_DIR"] = os.path.join(PROJECT_ROOT, "nodes", "Node2", "Storage")

# Ensure storage directory exists
os.makedirs(os.environ["STORAGE_DIR"], exist_ok=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001)
