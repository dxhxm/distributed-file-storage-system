"""
test_file_delete.py
===================
Automated test suite for DELETE /files/{file_id} endpoint:
1. Tests deleting a local file by file_id.
2. Tests deleting a replicated file across local and peer storage nodes.
3. Tests 404 response when attempting to delete a non-existent file.
4. Verifies file is no longer returned in GET /files.
"""

import os
import hashlib
from fastapi.testclient import TestClient

# Ensure test storage directories exist
os.makedirs("Storage", exist_ok=True)
os.makedirs(os.path.join("nodes", "Node1", "Storage"), exist_ok=True)
os.makedirs(os.path.join("nodes", "Node2", "Storage"), exist_ok=True)
os.makedirs(os.path.join("nodes", "Node3", "Storage"), exist_ok=True)

from app.main import app

client = TestClient(app)

def test_delete_flow():
    print("\n=== Running DFSS File Delete Backend Tests ===\n")

    # 1. Test local file deletion by file_id
    filename1 = "test_delete_local.txt"
    content = b"Data to be deleted by test_file_delete"
    local_path = os.path.join("Storage", filename1)
    with open(local_path, "wb") as f:
        f.write(content)

    file_id1 = f"file-{hashlib.md5(filename1.encode()).hexdigest()[:8]}"

    # Verify file is present first
    assert os.path.exists(local_path), "File must exist before deletion"

    # Delete by file_id
    res_del = client.delete(f"/files/{file_id1}")
    assert res_del.status_code == 200, f"Expected 200, got {res_del.status_code}: {res_del.text}"
    del_json = res_del.json()
    assert del_json.get("message") == "File deleted successfully"
    assert del_json.get("filename") == filename1
    assert not os.path.exists(local_path), "File must be removed from local storage"
    print("  ✓ PASS: Direct local file deletion by file_id removes file from storage.")

    # 2. Test multi-node replica deletion
    filename2 = "test_delete_replicated.dat"
    content2 = b"Replicated binary payload"
    path_local = os.path.join("Storage", filename2)
    path_node2 = os.path.join("nodes", "Node2", "Storage", filename2)
    path_node3 = os.path.join("nodes", "Node3", "Storage", filename2)

    with open(path_local, "wb") as f:
        f.write(content2)
    with open(path_node2, "wb") as f:
        f.write(content2)
    with open(path_node3, "wb") as f:
        f.write(content2)

    file_id2 = f"file-{hashlib.md5(filename2.encode()).hexdigest()[:8]}"

    res_del_rep = client.delete(f"/files/{file_id2}")
    assert res_del_rep.status_code == 200, f"Expected 200, got {res_del_rep.status_code}"
    assert not os.path.exists(path_local), "Local copy must be deleted"
    assert not os.path.exists(path_node2), "Node2 replica must be deleted"
    assert not os.path.exists(path_node3), "Node3 replica must be deleted"
    print("  ✓ PASS: Replicated file deletion removes all copies across cluster nodes.")

    # 3. Test deleting non-existent file returns explicit 404
    missing_id = "file-nonexistent999"
    res_missing = client.delete(f"/files/{missing_id}")
    assert res_missing.status_code == 404, f"Expected 404 for missing file, got {res_missing.status_code}"
    detail = res_missing.json().get("detail", "")
    assert "File not found" in detail, f"Expected 'File not found' in detail, got: {detail}"
    print(f"  ✓ PASS: Deleting non-existent file returns 404 with detail: '{detail}'")

    # 4. Verify file is no longer in GET /files
    res_list = client.get("/files")
    assert res_list.status_code == 200
    files = res_list.json().get("files", [])
    assert not any(f.get("file_id") == file_id1 for f in files), f"{file_id1} should not appear in /files"
    assert not any(f.get("file_id") == file_id2 for f in files), f"{file_id2} should not appear in /files"
    print("  ✓ PASS: Deleted files no longer appear in GET /files ledger.")

    print("\n=== All Backend File Delete Tests Passed Successfully (4/4)! ===\n")

if __name__ == "__main__":
    test_delete_flow()
