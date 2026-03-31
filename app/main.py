import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import time_sync
from app.services.time_sync import start_periodic_sync

# 1. Define the Lifespan (The "Brain" of the Node)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: This kicks off the background heart-beat
    # Every 30 seconds, this node will now reach out to nodeB to sync
    asyncio.create_task(start_periodic_sync("nodeB", interval=30))
    print("INFO: Periodic Time Synchronization Task Started.")
    yield
    # SHUTDOWN: Logic here if you need to close database connections later

# 2. Initialize the App ONCE with the lifespan
app = FastAPI(
    title="Distributed File Storage System",
    description="Base FastAPI server for distributed nodes",
    version="1.0.0",
    lifespan=lifespan
)

# 3. Register Routers
app.include_router(time_sync.router, tags=["Time Synchronization"])

@app.get("/")
async def root():
    return {"message": "Distributed File Storage System Node Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}