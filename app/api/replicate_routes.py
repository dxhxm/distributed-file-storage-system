import os
import shutil
from fastapi import APIRouter, UploadFile, File

from app.services.replication_service import replicate_file

router = APIRouter()

STORAGE_DIR = os.environ.get("STORAGE_DIR", "Storage")

# Ensure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a file and replicate it to peer nodes."""
    file_path = os.path.join(STORAGE_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Replicate to other alive nodes
    replicate_file(file_path, file.filename)

    return {"message": "File uploaded & replicated", "filename": file.filename}


@router.post("/replicate")
async def receive_replica(file: UploadFile = File(...)):
    """Receive a replicated file from a peer node."""
    file_path = os.path.join(STORAGE_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"message": "File replicated successfully", "filename": file.filename}
