from fastapi import FastAPI

app = FastAPI(
    title="Distributed File Storage System",
    description="Base FastAPI server for distributed nodes",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {
        "message": "Distributed File Storage System Node Running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }