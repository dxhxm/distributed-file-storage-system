import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import time_sync
from app.services.time_sync import start_periodic_sync
from app.api import consensus

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_periodic_sync("nodeB", interval=30))
    print("INFO: Periodic Time Synchronization Task Started.")
    yield
    

app = FastAPI(
    title="Distributed File Storage System",
    description="Base FastAPI server for distributed nodes",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(time_sync.router, tags=["Time Synchronization"])
app.include_router(consensus.router, tags=["Consensus"])

@app.get("/")
async def root():
    return {"message": "Distributed File Storage System Node Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}