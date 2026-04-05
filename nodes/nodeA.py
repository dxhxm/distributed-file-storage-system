import os
import uvicorn
import os

os.environ["NODE_NAME"] = "Node A"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )
    os.environ["NODE_NAME"] = "Node A"
    os.environ["NODE_NEIGHBORS"] = '["http://127.0.0.1:8001", "http://127.0.0.1:8002"]'
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
