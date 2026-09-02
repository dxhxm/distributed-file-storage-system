import os
import shutil
import hashlib
import requests
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse

from app.services.replication_service import replicate_file, is_node_alive
from app.models.config import NODES, CURRENT_NODE

router = APIRouter()

STORAGE_DIR = os.environ.get("STORAGE_DIR", "Storage")

# Ensure the storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)


@router.get("/files/{file_id}")
async def download_file(file_id: str):
    """Download a file by file_id or filename, proxying across alive replica nodes if needed."""
    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)

    # Base node storage mappings for local replica detection
    node_storage_paths = {
        "Node A": os.path.join(os.getcwd(), "nodes", "Node1", "Storage"),
        "Node B": os.path.join(os.getcwd(), "nodes", "Node2", "Storage"),
        "Node C": os.path.join(os.getcwd(), "nodes", "Node3", "Storage"),
    }

    # 1. Resolve target filename from file_id
    target_filename = None
    all_candidate_dirs = [storage_dir] + list(node_storage_paths.values())
    for d in all_candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                if not fname.startswith(".") and os.path.isfile(os.path.join(d, fname)):
                    computed_id = f"file-{hashlib.md5(fname.encode()).hexdigest()[:8]}"
                    if file_id == computed_id or file_id == fname:
                        target_filename = fname
                        break
        if target_filename:
            break

    if not target_filename:
        target_filename = file_id

    # 2. Check current node local storage
    local_path = os.path.join(storage_dir, target_filename)
    if os.path.exists(local_path) and os.path.isfile(local_path):
        return FileResponse(
            path=local_path,
            filename=target_filename,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{target_filename}"'}
        )

    # 3. Check peer node storage paths directly
    for node_name, path in node_storage_paths.items():
        peer_file = os.path.join(path, target_filename)
        if os.path.exists(peer_file) and os.path.isfile(peer_file):
            return FileResponse(
                path=peer_file,
                filename=target_filename,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{target_filename}"'}
            )

    # 4. Check peer nodes over HTTP proxy if not found in local paths
    for node_url in NODES:
        if node_url != CURRENT_NODE and is_node_alive(node_url):
            try:
                resp = requests.get(f"{node_url}/files/{file_id}", timeout=3)
                if resp.status_code == 200:
                    return Response(
                        content=resp.content,
                        media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{target_filename}"'}
                    )
            except Exception:
                pass

    # 5. If no alive node holds the replica, return clear replica error
    raise HTTPException(
        status_code=404,
        detail=f"File replica unavailable: No active storage node holds a valid replica for '{target_filename}'."
    )


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file and remove its replicas across all cluster nodes."""
    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)

    # Base node storage mappings for local replica detection
    node_storage_paths = {
        "Node A": os.path.join(os.getcwd(), "nodes", "Node1", "Storage"),
        "Node B": os.path.join(os.getcwd(), "nodes", "Node2", "Storage"),
        "Node C": os.path.join(os.getcwd(), "nodes", "Node3", "Storage"),
    }

    # 1. Resolve target filename from file_id
    target_filename = None
    all_candidate_dirs = [storage_dir] + list(node_storage_paths.values())
    for d in all_candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                if not fname.startswith(".") and os.path.isfile(os.path.join(d, fname)):
                    computed_id = f"file-{hashlib.md5(fname.encode()).hexdigest()[:8]}"
                    if file_id == computed_id or file_id == fname:
                        target_filename = fname
                        break
        if target_filename:
            break

    if not target_filename:
        target_filename = file_id

    # 2. Check if the file exists in any storage location and delete
    deleted_any = False

    # Remove from current node local storage
    local_path = os.path.join(storage_dir, target_filename)
    if os.path.exists(local_path) and os.path.isfile(local_path):
        try:
            os.remove(local_path)
            deleted_any = True
        except Exception:
            pass

    # Remove from peer node storage paths directly
    for _, path in node_storage_paths.items():
        peer_file = os.path.join(path, target_filename)
        if os.path.exists(peer_file) and os.path.isfile(peer_file):
            try:
                os.remove(peer_file)
                deleted_any = True
            except Exception:
                pass

    # Propagate delete to peer HTTP nodes (for separate process/container runs)
    for node_url in NODES:
        if node_url != CURRENT_NODE and is_node_alive(node_url):
            try:
                resp = requests.delete(f"{node_url}/files/{target_filename}", timeout=2)
                if resp.status_code == 200:
                    deleted_any = True
            except Exception:
                pass

    if not deleted_any:
        raise HTTPException(
            status_code=404,
            detail=f"File not found: '{target_filename}' does not exist in cluster."
        )

    return {
        "message": "File deleted successfully",
        "filename": target_filename,
        "file_id": file_id
    }


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


@router.post("/files/upload")
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a file and replicate it to peer nodes."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

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
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    storage_dir = os.environ.get("STORAGE_DIR", STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"message": "File replicated successfully", "filename": file.filename}

