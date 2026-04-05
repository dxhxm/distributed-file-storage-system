import os
import uvicorn
import os

os.environ["NODE_NAME"] = "Node C"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8002,
        reload=False
    )
    os.environ["NODE_NAME"] = "Node C"
    os.environ["NODE_NEIGHBORS"] = '["http://127.0.0.1:8000", "http://127.0.0.1:8001"]'
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, reload=True)
