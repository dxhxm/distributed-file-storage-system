import uvicorn
import os

if __name__ == "__main__":
    os.environ["NODE_NAME"] = "Node B"
    os.environ["NODE_NEIGHBORS"] = '["http://127.0.0.1:8000", "http://127.0.0.1:8002"]'
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)