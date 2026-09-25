"""
test_file_access_rules.py
=========================
Automated unit and integration test suite validating the Shared Collaborative
Cluster Storage Model and file access rule enforcement in DFSS.

Key Test Objectives:
1. Cross-User Shared Access:
   - User A (Alice) uploads a file.
   - User B (Bob) can list it via GET /files, download it via GET /files/{file_id}, and delete it via DELETE /files/{file_id}.
   - After deletion, the file is no longer accessible or listed for any user.
2. Admin Shared Access & Management:
   - User A uploads a file.
   - Admin user can list, download, and delete User A's file.
3. Unauthenticated Rejection Across All File Routes:
   - GET /files -> 401 Unauthorized
   - GET /files/{file_id} -> 401 Unauthorized
   - POST /files/upload -> 401 Unauthorized
   - POST /upload -> 401 Unauthorized
   - DELETE /files/{file_id} -> 401 Unauthorized
   - POST /replicate -> 401 Unauthorized
4. Token Expiration & Tampering on File Routes:
   - Expired JWT tokens return 401 Unauthorized with detail="TOKEN_EXPIRED".
   - Malformed/invalid JWT tokens return 401 Unauthorized with detail="INVALID_TOKEN".
5. Replication Role Boundary:
   - User/Admin token attempting POST /replicate receives 403 Forbidden.
   - SYSTEM service token successfully executes POST /replicate.
"""

import os
import sys
import io
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-standalone-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

# Configure test storage environment
STORAGE_DIR = os.path.join(tempfile.gettempdir(), "dfss_test_file_access_storage")
os.environ["STORAGE_DIR"] = STORAGE_DIR
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join("nodes", "Node1", "Storage"), exist_ok=True)
os.makedirs(os.path.join("nodes", "Node2", "Storage"), exist_ok=True)
os.makedirs(os.path.join("nodes", "Node3", "Storage"), exist_ok=True)

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, get_system_auth_headers


class TestFileAccessRules(unittest.TestCase):
    """Test suite validating DFSS shared file storage access rules and RBAC enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # 1. Create tokens for two distinct standard users
        cls.user_a_token = create_access_token(
            user_id="user-alice-uuid-001",
            role=Role.USER,
            username="alice"
        )
        cls.user_a_headers = {"Authorization": f"Bearer {cls.user_a_token}"}

        cls.user_b_token = create_access_token(
            user_id="user-bob-uuid-002",
            role=Role.USER,
            username="bob"
        )
        cls.user_b_headers = {"Authorization": f"Bearer {cls.user_b_token}"}

        # 2. Create token for admin user
        cls.admin_token = create_access_token(
            user_id="admin-carol-uuid-003",
            role=Role.ADMIN,
            username="carol_admin"
        )
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}

        # 3. Create expired and malformed tokens
        cls.expired_token = create_access_token(
            user_id="expired-user-uuid",
            role=Role.USER,
            username="expired_user",
            expires_delta=timedelta(seconds=-60)
        )
        cls.expired_headers = {"Authorization": f"Bearer {cls.expired_token}"}
        cls.invalid_headers = {"Authorization": "Bearer invalid.malformed.signature"}

        # 4. System headers
        cls.system_headers = get_system_auth_headers(node_id="Node A")

    def tearDown(self):
        """Clean up files created in test storage."""
        if os.path.exists(STORAGE_DIR):
            for fname in os.listdir(STORAGE_DIR):
                fpath = os.path.join(STORAGE_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass

    def test_01_cross_user_shared_access_flow(self):
        """Verify Alice uploads a file; Bob lists, downloads, and deletes it."""
        filename = "alice_shared_doc.txt"
        file_bytes = b"Hello from Alice! This document is shared across the cluster."
        file_id = f"file-{hashlib.md5(filename.encode()).hexdigest()[:8]}"

        # Step 1: Alice uploads the file
        upload_res = self.client.post(
            "/files/upload",
            files={"file": (filename, io.BytesIO(file_bytes), "text/plain")},
            headers=self.user_a_headers,
        )
        self.assertEqual(upload_res.status_code, 200)
        self.assertEqual(upload_res.json().get("filename"), filename)

        # Step 2: Bob lists files and verifies Alice's file is present
        list_res = self.client.get("/files", headers=self.user_b_headers)
        self.assertEqual(list_res.status_code, 200)
        files_data = list_res.json().get("files", [])
        found_file = next((f for f in files_data if f.get("name") == filename), None)
        self.assertIsNotNone(found_file, "Bob should see Alice's uploaded file in GET /files")
        self.assertEqual(found_file.get("file_id"), file_id)

        # Step 3: Bob downloads Alice's file by file_id
        dl_res = self.client.get(f"/files/{file_id}", headers=self.user_b_headers)
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.content, file_bytes)

        # Step 4: Bob downloads Alice's file by filename
        dl_name_res = self.client.get(f"/files/{filename}", headers=self.user_b_headers)
        self.assertEqual(dl_name_res.status_code, 200)
        self.assertEqual(dl_name_res.content, file_bytes)

        # Step 5: Bob deletes Alice's file
        del_res = self.client.delete(f"/files/{file_id}", headers=self.user_b_headers)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json().get("filename"), filename)

        # Step 6: Verify file is gone from Alice's and Bob's list view
        list_after_alice = self.client.get("/files", headers=self.user_a_headers)
        self.assertEqual(list_after_alice.status_code, 200)
        alice_files = list_after_alice.json().get("files", [])
        self.assertFalse(any(f.get("name") == filename for f in alice_files))

        list_after_bob = self.client.get("/files", headers=self.user_b_headers)
        self.assertEqual(list_after_bob.status_code, 200)
        bob_files = list_after_bob.json().get("files", [])
        self.assertFalse(any(f.get("name") == filename for f in bob_files))

    def test_02_admin_access_to_user_files(self):
        """Verify Admin user can list, download, and delete files uploaded by standard users."""
        filename = "alice_project_report.pdf"
        file_bytes = b"%PDF-1.4 Mock PDF Content Created by Alice"
        file_id = f"file-{hashlib.md5(filename.encode()).hexdigest()[:8]}"

        # Alice uploads
        res_up = self.client.post(
            "/files/upload",
            files={"file": (filename, io.BytesIO(file_bytes), "application/pdf")},
            headers=self.user_a_headers,
        )
        self.assertEqual(res_up.status_code, 200)

        # Admin lists
        res_list = self.client.get("/files", headers=self.admin_headers)
        self.assertEqual(res_list.status_code, 200)
        files = res_list.json().get("files", [])
        self.assertTrue(any(f.get("name") == filename for f in files))

        # Admin downloads
        res_dl = self.client.get(f"/files/{file_id}", headers=self.admin_headers)
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.content, file_bytes)

        # Admin deletes
        res_del = self.client.delete(f"/files/{file_id}", headers=self.admin_headers)
        self.assertEqual(res_del.status_code, 200)

        # Ensure deleted
        res_dl_after = self.client.get(f"/files/{file_id}", headers=self.admin_headers)
        self.assertEqual(res_dl_after.status_code, 404)

    def test_03_unauthenticated_calls_rejected_on_all_file_routes(self):
        """Verify unauthenticated requests are strictly rejected with 401 across all file endpoints."""
        file_payload = {"file": ("unauth.txt", io.BytesIO(b"unauthenticated"), "text/plain")}

        # 1. GET /files
        res_list = self.client.get("/files")
        self.assertEqual(res_list.status_code, 401)
        self.assertEqual(res_list.headers.get("x-error-code"), "NOT_AUTHENTICATED")

        # 2. GET /files/{file_id}
        res_dl = self.client.get("/files/file-test1234")
        self.assertEqual(res_dl.status_code, 401)
        self.assertEqual(res_dl.headers.get("x-error-code"), "NOT_AUTHENTICATED")

        # 3. POST /files/upload
        res_up1 = self.client.post("/files/upload", files=file_payload)
        self.assertEqual(res_up1.status_code, 401)
        self.assertEqual(res_up1.headers.get("x-error-code"), "NOT_AUTHENTICATED")

        # 4. POST /upload
        res_up2 = self.client.post("/upload", files=file_payload)
        self.assertEqual(res_up2.status_code, 401)
        self.assertEqual(res_up2.headers.get("x-error-code"), "NOT_AUTHENTICATED")

        # 5. DELETE /files/{file_id}
        res_del = self.client.delete("/files/file-test1234")
        self.assertEqual(res_del.status_code, 401)
        self.assertEqual(res_del.headers.get("x-error-code"), "NOT_AUTHENTICATED")

        # 6. POST /replicate
        res_rep = self.client.post("/replicate", files=file_payload)
        self.assertEqual(res_rep.status_code, 401)
        self.assertEqual(res_rep.headers.get("x-error-code"), "NOT_AUTHENTICATED")

    def test_04_expired_and_invalid_tokens_rejected_on_file_routes(self):
        """Verify expired and malformed tokens return 401 on file routes."""
        file_payload = {"file": ("test.txt", io.BytesIO(b"data"), "text/plain")}

        # Expired token on GET /files
        res_exp_list = self.client.get("/files", headers=self.expired_headers)
        self.assertEqual(res_exp_list.status_code, 401)
        self.assertEqual(res_exp_list.headers.get("x-error-code"), "TOKEN_EXPIRED")

        # Expired token on POST /files/upload
        res_exp_up = self.client.post("/files/upload", files=file_payload, headers=self.expired_headers)
        self.assertEqual(res_exp_up.status_code, 401)
        self.assertEqual(res_exp_up.headers.get("x-error-code"), "TOKEN_EXPIRED")

        # Invalid token on GET /files/{file_id}
        res_inv_dl = self.client.get("/files/file-123", headers=self.invalid_headers)
        self.assertEqual(res_inv_dl.status_code, 401)
        self.assertEqual(res_inv_dl.headers.get("x-error-code"), "INVALID_TOKEN")

        # Invalid token on DELETE /files/{file_id}
        res_inv_del = self.client.delete("/files/file-123", headers=self.invalid_headers)
        self.assertEqual(res_inv_del.status_code, 401)
        self.assertEqual(res_inv_del.headers.get("x-error-code"), "INVALID_TOKEN")

    def test_05_replication_role_isolation(self):
        """Verify POST /replicate is restricted to SYSTEM role and rejects USER/ADMIN with 403."""
        file_payload = {"file": ("replica.bin", io.BytesIO(b"replica chunk data"), "application/octet-stream")}

        # USER attempting POST /replicate -> 403 Forbidden
        res_user = self.client.post("/replicate", files=file_payload, headers=self.user_a_headers)
        self.assertEqual(res_user.status_code, 403)
        self.assertEqual(res_user.headers.get("x-error-code"), "FORBIDDEN_SYSTEM_REQUIRED")

        # ADMIN attempting POST /replicate -> 403 Forbidden
        res_admin = self.client.post("/replicate", files=file_payload, headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 403)
        self.assertEqual(res_admin.headers.get("x-error-code"), "FORBIDDEN_SYSTEM_REQUIRED")

        # SYSTEM token -> 200 OK
        res_sys = self.client.post("/replicate", files=file_payload, headers=self.system_headers)
        self.assertEqual(res_sys.status_code, 200)
        self.assertEqual(res_sys.json().get("filename"), "replica.bin")


if __name__ == "__main__":
    unittest.main()
