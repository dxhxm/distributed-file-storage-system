import os
import shutil
import hashlib
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File

from app.services.replication_service import replicate_file

router = APIRouter()

STORAGE_DIR = os.environ.get("STORAGE_DIR", "Storage")

# Ensure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)


@router.get("/files")
async def list_files():
    """List all stored files with replica distribution, size, and health status."""
    try:
        from app.api.consensus import consensus_service
        current_node = getattr(consensus_service, "current_node", "Node A") if consensus_service else "Node A"
    except Exception:
        current_node = os.environ.get("NODE_NAME", "Node A")

    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)

    # Base node storage mappings for local replica detection
    node_storage_paths = {
        "Node A": os.path.join(os.getcwd(), "nodes", "Node1", "Storage"),
        "Node B": os.path.join(os.getcwd(), "nodes", "Node2", "Storage"),
        "Node C": os.path.join(os.getcwd(), "nodes", "Node3", "Storage"),
    }

    files = []
    seen_filenames = set()

    # Collect filenames from current storage and known node storage paths
    candidate_dirs = [storage_dir] + list(node_storage_paths.values())
    for d in candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                if not fname.startswith(".") and os.path.isfile(os.path.join(d, fname)):
                    seen_filenames.add(fname)

    total_size = 0
    for filename in sorted(seen_filenames):
        # Find primary file path
        primary_path = os.path.join(storage_dir, filename)
        if not os.path.exists(primary_path):
            for d in node_storage_paths.values():
                candidate = os.path.join(d, filename)
                if os.path.exists(candidate):
                    primary_path = candidate
                    break

        file_size = os.path.getsize(primary_path) if os.path.exists(primary_path) else 0
        total_size += file_size

        # Check replicas
        replicas = []
        for node_name, path in node_storage_paths.items():
            if os.path.exists(os.path.join(path, filename)):
                replicas.append(node_name)

        if not replicas:
            replicas = [current_node]

        # Determine status
        if len(replicas) >= 2:
            status = "REPLICATED"
        else:
            status = "SYNCING"

        # Deterministic file ID
        file_id = f"file-{hashlib.md5(filename.encode()).hexdigest()[:8]}"

        files.append({
            "file_id": file_id,
            "name": filename,
            "size": file_size,
            "replicas": replicas,
            "status": status
        })

    return {
        "files": files,
        "total_files": len(files),
        "total_size_bytes": total_size
    }


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a file and replicate it to peer nodes."""
    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Replicate to other alive nodes
    replicate_file(file_path, file.filename)

    return {"message": "File uploaded & replicated", "filename": file.filename}


@router.post("/replicate")
async def receive_replica(file: UploadFile = File(...)):
    """Receive a replicated file from a peer node."""
    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"message": "File replicated successfully", "filename": file.filename}

