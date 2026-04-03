import os
import uvicorn

os.environ["NODE_NAME"] = "Node C"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8002,
        reload=False
    )