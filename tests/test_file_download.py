"""
test_file_download.py
=====================
Automated test suite for GET /files/{file_id} download endpoint:
1. Tests direct local download by file_id and filename.
2. Tests cross-node replica proxying when file is on another node.
3. Tests explicit 404 error message when replica is unavailable.
"""

import os
import hashlib
from fastapi.testclient import TestClient

# Ensure test storage directories exist
os.makedirs("Storage", exist_ok=True)
os.makedirs(os.path.join("nodes", "Node2", "Storage"), exist_ok=True)
os.makedirs(os.path.join("nodes", "Node3", "Storage"), exist_ok=True)

from app.main import app

client = TestClient(app)

def test_download_flow():
    print("\n=== Running DFSS File Download Backend Tests ===\n")

    # 1. Test local file download
    test_filename = "download_test_local.txt"
    test_content = b"Distributed fault-tolerant file storage system content payload 12345"
    local_path = os.path.join("Storage", test_filename)
    with open(local_path, "wb") as f:
        f.write(test_content)

    file_id = f"file-{hashlib.md5(test_filename.encode()).hexdigest()[:8]}"

    # Download by file_id
    res_id = client.get(f"/files/{file_id}")
    assert res_id.status_code == 200, f"Expected 200, got {res_id.status_code}"
    assert res_id.content == test_content, "Downloaded content must match written payload"
    assert "attachment" in res_id.headers.get("content-disposition", "").lower()
    print("  ✓ PASS: Direct local file download by file_id succeeds with correct content & headers.")

    # Download by filename
    res_name = client.get(f"/files/{test_filename}")
    assert res_name.status_code == 200, f"Expected 200, got {res_name.status_code}"
    assert res_name.content == test_content
    print("  ✓ PASS: Direct local file download by filename succeeds.")

    # 2. Test cross-node replica fallback (file only in Node2 Storage)
    peer_filename = "peer_replica_file.bin"
    peer_content = b"Binary replica stored exclusively on Node B"
    peer_path = os.path.join("nodes", "Node2", "Storage", peer_filename)
    with open(peer_path, "wb") as f:
        f.write(peer_content)

    peer_file_id = f"file-{hashlib.md5(peer_filename.encode()).hexdigest()[:8]}"

    # Request from current node (which lacks local copy in Storage/)
    if os.path.exists(os.path.join("Storage", peer_filename)):
        os.remove(os.path.join("Storage", peer_filename))

    res_peer = client.get(f"/files/{peer_file_id}")
    assert res_peer.status_code == 200, f"Expected 200 from replica fallback, got {res_peer.status_code}"
    assert res_peer.content == peer_content, "Replica content must match peer storage"
    print("  ✓ PASS: Serving node retrieves file from peer replica node when local copy is absent.")

    # 3. Test missing replica error handling (HTTP 404 with explicit systems message)
    missing_id = "file-deadbeef"
    res_missing = client.get(f"/files/{missing_id}")
    assert res_missing.status_code == 404, f"Expected 404 for missing file, got {res_missing.status_code}"
    detail = res_missing.json().get("detail", "")
    assert "File replica unavailable" in detail, f"Expected explicit replica error detail, got: {detail}"
    print(f"  ✓ PASS: Missing file returns explicit 404 detail: '{detail}'")

    # Cleanup test files
    if os.path.exists(local_path):
        os.remove(local_path)
    if os.path.exists(peer_path):
        os.remove(peer_path)

    print("\n=== All Backend File Download Tests Passed Successfully (3/3)! ===\n")

if __name__ == "__main__":
    test_download_flow()
