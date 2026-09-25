"""
test_file_auth_rbac.py
======================
Automated test suite verifying authentication and role authorization across all cluster file operations:
1. Gating verification on all 3 file routes (Upload, Download, Delete):
   - Reject unauthenticated requests with HTTP 401 Unauthorized (NOT_AUTHENTICATED).
   - Reject expired tokens with HTTP 401 Unauthorized (TOKEN_EXPIRED).
   - Reject malformed / tampered tokens with HTTP 401 Unauthorized (INVALID_TOKEN).
2. Authenticated USER role:
   - Successfully uploads files via POST /files/upload and POST /upload.
   - Successfully downloads files via GET /files/{file_id}.
   - Successfully deletes files via DELETE /files/{file_id}.
3. Authenticated ADMIN role:
   - Full upload, download, and deletion capability.
4. End-to-end flow verification:
   - User authentication -> JWT token -> Upload -> List -> Download -> Delete.
"""

import io
import os
import unittest
import hashlib
from datetime import timedelta
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-file-auth-rbac-unit-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token


class TestFileOperationsAuthRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Storage directory setup
        os.makedirs("Storage", exist_ok=True)

        # Pre-generate test tokens
        cls.user_token = create_access_token(
            user_id="user-file-op-101",
            role=Role.USER,
            username="alice_storage_user"
        )
        cls.admin_token = create_access_token(
            user_id="admin-file-op-202",
            role=Role.ADMIN,
            username="bob_storage_admin"
        )
        cls.expired_token = create_access_token(
            user_id="user-file-op-101",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.expired_headers = {"Authorization": f"Bearer {cls.expired_token}"}
        cls.invalid_headers = {"Authorization": "Bearer invalid.malformed.token"}

    # =========================================================================
    # 1. Unauthenticated Rejections on All File Routes (DoD: HTTP 401)
    # =========================================================================
    def test_unauthenticated_upload_rejected_with_401(self):
        """Unauthenticated POST /files/upload and POST /upload return 401 Unauthorized."""
        file_payload = {"file": ("unauth_test.txt", io.BytesIO(b"unauth content"), "text/plain")}

        # 1. /files/upload
        res1 = self.client.post("/files/upload", files=file_payload)
        self.assertEqual(res1.status_code, 401)
        self.assertEqual(res1.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

        # 2. /upload alias
        file_payload2 = {"file": ("unauth_test2.txt", io.BytesIO(b"unauth content 2"), "text/plain")}
        res2 = self.client.post("/upload", files=file_payload2)
        self.assertEqual(res2.status_code, 401)
        self.assertEqual(res2.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    def test_unauthenticated_download_rejected_with_401(self):
        """Unauthenticated GET /files/{file_id} returns 401 Unauthorized."""
        res = self.client.get("/files/file-someid123")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    def test_unauthenticated_delete_rejected_with_401(self):
        """Unauthenticated DELETE /files/{file_id} returns 401 Unauthorized."""
        res = self.client.delete("/files/file-someid123")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    # =========================================================================
    # 2. Expired & Invalid Token Rejections (HTTP 401)
    # =========================================================================
    def test_expired_token_rejected_on_all_file_routes(self):
        """Expired JWT tokens return 401 with TOKEN_EXPIRED code on all file routes."""
        # Upload
        files = {"file": ("exp_file.txt", io.BytesIO(b"data"), "text/plain")}
        res_up = self.client.post("/files/upload", files=files, headers=self.expired_headers)
        self.assertEqual(res_up.status_code, 401)
        self.assertEqual(res_up.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

        # Download
        res_dl = self.client.get("/files/file-test", headers=self.expired_headers)
        self.assertEqual(res_dl.status_code, 401)
        self.assertEqual(res_dl.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

        # Delete
        res_del = self.client.delete("/files/file-test", headers=self.expired_headers)
        self.assertEqual(res_del.status_code, 401)
        self.assertEqual(res_del.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

    def test_invalid_token_rejected_on_all_file_routes(self):
        """Malformed or tampered JWT tokens return 401 with INVALID_TOKEN code."""
        # Upload
        files = {"file": ("inv_file.txt", io.BytesIO(b"data"), "text/plain")}
        res_up = self.client.post("/files/upload", files=files, headers=self.invalid_headers)
        self.assertEqual(res_up.status_code, 401)
        self.assertEqual(res_up.headers.get("X-Error-Code"), "INVALID_TOKEN")

        # Download
        res_dl = self.client.get("/files/file-test", headers=self.invalid_headers)
        self.assertEqual(res_dl.status_code, 401)
        self.assertEqual(res_dl.headers.get("X-Error-Code"), "INVALID_TOKEN")

        # Delete
        res_del = self.client.delete("/files/file-test", headers=self.invalid_headers)
        self.assertEqual(res_del.status_code, 401)
        self.assertEqual(res_del.headers.get("X-Error-Code"), "INVALID_TOKEN")

    # =========================================================================
    # 3. Authenticated USER Full End-to-End File Operations Lifecycle
    # =========================================================================
    def test_authenticated_user_file_lifecycle(self):
        """DoD: Authenticated USER can upload, download, and delete files end to end."""
        filename = "user_lifecycle_doc.txt"
        file_content = b"User file operations lifecycle test payload 2026"
        file_id = f"file-{hashlib.md5(filename.encode()).hexdigest()[:8]}"

        # 1. USER Uploads file via /files/upload
        files = {"file": (filename, io.BytesIO(file_content), "text/plain")}
        res_upload = self.client.post("/files/upload", files=files, headers=self.user_headers)
        self.assertEqual(res_upload.status_code, 200)
        self.assertIn("File uploaded", res_upload.json().get("message", ""))
        self.assertEqual(res_upload.json().get("filename"), filename)

        # Verify file is listed
        res_list = self.client.get("/files")
        self.assertEqual(res_list.status_code, 200)
        listed_files = res_list.json().get("files", [])
        self.assertTrue(any(f.get("name") == filename for f in listed_files))

        # 2. USER Downloads file via /files/{file_id}
        res_download = self.client.get(f"/files/{file_id}", headers=self.user_headers)
        self.assertEqual(res_download.status_code, 200)
        self.assertEqual(res_download.content, file_content)
        self.assertIn("attachment", res_download.headers.get("content-disposition", "").lower())

        # Also verify download by filename
        res_dl_name = self.client.get(f"/files/{filename}", headers=self.user_headers)
        self.assertEqual(res_dl_name.status_code, 200)
        self.assertEqual(res_dl_name.content, file_content)

        # 3. USER Deletes file via /files/{file_id}
        res_delete = self.client.delete(f"/files/{file_id}", headers=self.user_headers)
        self.assertEqual(res_delete.status_code, 200)
        self.assertEqual(res_delete.json().get("message"), "File deleted successfully")

        # Verify file is removed from disk and listing
        local_path = os.path.join("Storage", filename)
        self.assertFalse(os.path.exists(local_path))

    # =========================================================================
    # 4. Authenticated ADMIN Full End-to-End File Operations Lifecycle
    # =========================================================================
    def test_authenticated_admin_file_lifecycle(self):
        """Authenticated ADMIN can upload, download, and delete files."""
        filename = "admin_managed_file.dat"
        file_content = b"Admin managed system data binary payload"
        file_id = f"file-{hashlib.md5(filename.encode()).hexdigest()[:8]}"

        # 1. ADMIN Uploads file via /upload alias
        files = {"file": (filename, io.BytesIO(file_content), "application/octet-stream")}
        res_upload = self.client.post("/upload", files=files, headers=self.admin_headers)
        self.assertEqual(res_upload.status_code, 200)

        # 2. ADMIN Downloads file
        res_download = self.client.get(f"/files/{file_id}", headers=self.admin_headers)
        self.assertEqual(res_download.status_code, 200)
        self.assertEqual(res_download.content, file_content)

        # 3. ADMIN Deletes file
        res_delete = self.client.delete(f"/files/{file_id}", headers=self.admin_headers)
        self.assertEqual(res_delete.status_code, 200)


if __name__ == "__main__":
    unittest.main()
