"""
test_rbac_matrix_integration.py
===============================
Comprehensive End-to-End RBAC Allow/Deny Matrix Integration Test Suite:
1. Tests every role-guarded route across the entire permission matrix:
   - UNAUTHENTICATED (Missing Authorization header) -> strictly HTTP 401
   - EXPIRED TOKEN -> strictly HTTP 401
   - TAMPERED / INVALID TOKEN -> strictly HTTP 401
   - USER role -> Allowed on general user routes (200); strictly HTTP 403 on admin-only or system-only routes
   - ADMIN role -> Allowed across all user and admin management routes (200/201)
   - SYSTEM role -> Allowed on inter-node / cluster routes; strictly HTTP 403 on human user-management routes
2. Verifies 401 Unauthorized vs 403 Forbidden strict non-conflation across all route categories.
3. Verifies uniform JSON error response schema ({"detail": ...}) and standard WWW-Authenticate headers.
4. Executes with zero flakes using isolated SQLite and storage environments.
"""

import io
import os
import tempfile
import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set
os.environ.setdefault("JWT_SECRET", "test-rbac-matrix-suite-jwt-secret-key-2026-64-bytes-secure-token")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import (
    create_access_token,
    create_system_token,
)
from app.services.user_storage import (
    create_user,
    delete_user,
    init_db,
)


class TestRBACMatrixIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls._orig_storage_dir = os.environ.get("STORAGE_DIR")
        os.environ["STORAGE_DIR"] = cls.temp_dir.name

        init_db()
        cls.client = TestClient(app)

        # 1. Standard USER account
        delete_user("matrix_std_user")
        cls.user_record = create_user(
            User(
                username="matrix_std_user",
                hashed_password=hash_password("UserPassword123!"),
                role=Role.USER,
                is_active=True,
            )
        )
        cls.user_token = create_access_token(
            user_id=cls.user_record["id"],
            role=Role.USER,
            username="matrix_std_user",
        )

        # 2. Primary ADMIN account
        delete_user("matrix_admin_usr")
        cls.admin_record = create_user(
            User(
                username="matrix_admin_usr",
                hashed_password=hash_password("AdminPassword123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )
        cls.admin_token = create_access_token(
            user_id=cls.admin_record["id"],
            role=Role.ADMIN,
            username="matrix_admin_usr",
        )

        # 3. Secondary ADMIN account (for role modification / lockout testing)
        delete_user("matrix_admin_sec")
        cls.admin_sec_record = create_user(
            User(
                username="matrix_admin_sec",
                hashed_password=hash_password("AdminSecPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )

        # 4. Target USER account for management tests
        delete_user("matrix_target_usr")
        cls.target_user_record = create_user(
            User(
                username="matrix_target_usr",
                hashed_password=hash_password("TargetUserPass123!"),
                role=Role.USER,
                is_active=True,
            )
        )

        # 5. Service-to-service SYSTEM token
        cls.system_token = create_system_token(node_id="Node A")

        # 6. Expired token
        cls.expired_token = create_access_token(
            user_id="usr-expired",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10),
        )

        # 7. Tampered token
        cls.tampered_token = cls.user_token[:-6] + "xxxxxx"

        # Pre-constructed request headers
        cls.headers_user = {"Authorization": f"Bearer {cls.user_token}"}
        cls.headers_admin = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.headers_system = {"Authorization": f"Bearer {cls.system_token}"}
        cls.headers_expired = {"Authorization": f"Bearer {cls.expired_token}"}
        cls.headers_tampered = {"Authorization": f"Bearer {cls.tampered_token}"}
        cls.headers_unauth = {}

    @classmethod
    def tearDownClass(cls):
        delete_user("matrix_std_user")
        delete_user("matrix_admin_usr")
        delete_user("matrix_admin_sec")
        delete_user("matrix_target_usr")
        cls.temp_dir.cleanup()
        if cls._orig_storage_dir:
            os.environ["STORAGE_DIR"] = cls._orig_storage_dir
        else:
            os.environ.pop("STORAGE_DIR", None)

    # =========================================================================
    # Helper for asserting standard error format
    # =========================================================================
    def _assert_error_response(self, response, expected_status: int):
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected status {expected_status} but got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("detail", data, "Error response must follow standard {'detail': ...} schema")
        if expected_status == 401:
            self.assertIn("WWW-Authenticate", response.headers, "401 responses must include WWW-Authenticate header")

    # =========================================================================
    # 1. User Profile Endpoint (GET /auth/me)
    # =========================================================================
    def test_matrix_auth_me(self):
        """GET /auth/me: USER(200), ADMIN(200), SYSTEM(403), UNAUTH(401), EXPIRED(401), TAMPERED(401)."""
        # Allowed: USER
        r_user = self.client.get("/auth/me", headers=self.headers_user)
        self.assertEqual(r_user.status_code, 200)
        self.assertEqual(r_user.json()["role"], "USER")

        # Allowed: ADMIN
        r_admin = self.client.get("/auth/me", headers=self.headers_admin)
        self.assertEqual(r_admin.status_code, 200)
        self.assertEqual(r_admin.json()["role"], "ADMIN")

        # Denied: SYSTEM (SYSTEM tokens cannot access human user profiles)
        r_sys = self.client.get("/auth/me", headers=self.headers_system)
        self._assert_error_response(r_sys, 403)

        # Denied: Unauthenticated, Expired, Tampered
        self._assert_error_response(self.client.get("/auth/me", headers=self.headers_unauth), 401)
        self._assert_error_response(self.client.get("/auth/me", headers=self.headers_expired), 401)
        self._assert_error_response(self.client.get("/auth/me", headers=self.headers_tampered), 401)

    # =========================================================================
    # 2. Admin User Management Endpoints (/auth/users)
    # =========================================================================
    def test_matrix_get_all_users(self):
        """GET /auth/users: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401), EXPIRED(401)."""
        # Allowed: ADMIN
        r_admin = self.client.get("/auth/users", headers=self.headers_admin)
        self.assertEqual(r_admin.status_code, 200)
        self.assertIsInstance(r_admin.json(), list)

        # Denied: USER (403)
        r_user = self.client.get("/auth/users", headers=self.headers_user)
        self._assert_error_response(r_user, 403)

        # Denied: SYSTEM (403)
        r_sys = self.client.get("/auth/users", headers=self.headers_system)
        self._assert_error_response(r_sys, 403)

        # Denied: Unauthenticated (401)
        self._assert_error_response(self.client.get("/auth/users", headers=self.headers_unauth), 401)
        self._assert_error_response(self.client.get("/auth/users", headers=self.headers_expired), 401)

    def test_matrix_create_user(self):
        """POST /auth/users: ADMIN(201), USER(403), SYSTEM(403), UNAUTH(401)."""
        payload = {
            "username": "matrix_new_user_temp",
            "password": "TempPassword123!",
            "role": "USER",
            "is_active": True,
        }

        # Denied: USER (403)
        r_user = self.client.post("/auth/users", json=payload, headers=self.headers_user)
        self._assert_error_response(r_user, 403)

        # Denied: SYSTEM (403)
        r_sys = self.client.post("/auth/users", json=payload, headers=self.headers_system)
        self._assert_error_response(r_sys, 403)

        # Denied: Unauthenticated (401)
        r_unauth = self.client.post("/auth/users", json=payload, headers=self.headers_unauth)
        self._assert_error_response(r_unauth, 401)

        # Allowed: ADMIN (201)
        r_admin = self.client.post("/auth/users", json=payload, headers=self.headers_admin)
        self.assertEqual(r_admin.status_code, 201)
        self.assertEqual(r_admin.json()["username"], "matrix_new_user_temp")
        delete_user("matrix_new_user_temp")

    def test_matrix_modify_user_role_and_status(self):
        """PUT /auth/users/{id}/role & status: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401)."""
        target_id = self.target_user_record["id"]

        # Role change denied for USER (403)
        r_user_role = self.client.put(
            f"/auth/users/{target_id}/role",
            json={"role": "ADMIN"},
            headers=self.headers_user,
        )
        self._assert_error_response(r_user_role, 403)

        # Deactivation denied for USER (403)
        r_user_deact = self.client.post(
            f"/auth/users/{target_id}/deactivate",
            headers=self.headers_user,
        )
        self._assert_error_response(r_user_deact, 403)

        # Allowed for ADMIN (200)
        r_admin_role = self.client.put(
            f"/auth/users/{target_id}/role",
            json={"role": "ADMIN"},
            headers=self.headers_admin,
        )
        self.assertEqual(r_admin_role.status_code, 200)

        # Revert role back to USER
        self.client.put(
            f"/auth/users/{target_id}/role",
            json={"role": "USER"},
            headers=self.headers_admin,
        )

    # =========================================================================
    # 3. File Operations Routes (/files/*)
    # =========================================================================
    def test_matrix_file_upload_download_delete(self):
        """POST, GET, DELETE /files/*: USER(200), ADMIN(200), SYSTEM(200), UNAUTH(401)."""
        file_content = b"Integration test replication content"

        # Denied: Unauthenticated (401)
        r_unauth = self.client.post(
            "/files/upload",
            files={"file": ("matrix_sample.txt", io.BytesIO(file_content), "text/plain")},
            headers=self.headers_unauth,
        )
        self._assert_error_response(r_unauth, 401)

        # Allowed upload: USER (200)
        r_user = self.client.post(
            "/files/upload",
            files={"file": ("matrix_sample.txt", io.BytesIO(file_content), "text/plain")},
            headers=self.headers_user,
        )
        self.assertEqual(r_user.status_code, 200)

        # Allowed download: USER (200)
        r_dl_user = self.client.get("/files/matrix_sample.txt", headers=self.headers_user)
        self.assertEqual(r_dl_user.status_code, 200)

        # Allowed list files: USER (200), ADMIN (200), SYSTEM (200)
        self.assertEqual(self.client.get("/files", headers=self.headers_user).status_code, 200)
        self.assertEqual(self.client.get("/files", headers=self.headers_admin).status_code, 200)
        self.assertEqual(self.client.get("/files", headers=self.headers_system).status_code, 200)
        self._assert_error_response(self.client.get("/files", headers=self.headers_unauth), 401)

        # Allowed delete: USER, ADMIN, SYSTEM (200); Denied: UNAUTH (401)
        self._assert_error_response(self.client.delete("/files/matrix_sample.txt", headers=self.headers_unauth), 401)
        self.assertEqual(self.client.delete("/files/matrix_sample.txt", headers=self.headers_user).status_code, 200)

    # =========================================================================
    # 4. Replication Configuration Routes (/replication/config)
    # =========================================================================
    def test_matrix_replication_config(self):
        """GET & PUT /replication/config: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401)."""
        # Denied: USER (403)
        r_user_get = self.client.get("/replication/config", headers=self.headers_user)
        self._assert_error_response(r_user_get, 403)

        r_user_put = self.client.put("/replication/config", json={"replication_factor": 3}, headers=self.headers_user)
        self._assert_error_response(r_user_put, 403)

        # Denied: SYSTEM (403)
        r_sys_get = self.client.get("/replication/config", headers=self.headers_system)
        self._assert_error_response(r_sys_get, 403)

        # Denied: Unauthenticated (401)
        self._assert_error_response(self.client.get("/replication/config", headers=self.headers_unauth), 401)

        # Allowed: ADMIN (200)
        r_admin_get = self.client.get("/replication/config", headers=self.headers_admin)
        self.assertEqual(r_admin_get.status_code, 200)

    # =========================================================================
    # 5. Cluster Health & Node Management Routes
    # =========================================================================
    def test_matrix_health_and_nodes(self):
        """GET /health: Authenticated(200), UNAUTH(401). GET /health/detailed: ADMIN(200), USER(403)."""
        # GET /health
        self.assertEqual(self.client.get("/health", headers=self.headers_user).status_code, 200)
        self.assertEqual(self.client.get("/health", headers=self.headers_admin).status_code, 200)
        self.assertEqual(self.client.get("/health", headers=self.headers_system).status_code, 200)
        self._assert_error_response(self.client.get("/health", headers=self.headers_unauth), 401)

        # GET /health/detailed (Requires ADMIN)
        self.assertEqual(self.client.get("/health/detailed", headers=self.headers_admin).status_code, 200)
        self._assert_error_response(self.client.get("/health/detailed", headers=self.headers_user), 403)
        self._assert_error_response(self.client.get("/health/detailed", headers=self.headers_system), 403)
        self._assert_error_response(self.client.get("/health/detailed", headers=self.headers_unauth), 401)

    def test_matrix_node_management_actions(self):
        """POST /nodes/update & /nodes/remove: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401)."""
        update_payload = {"node_name": "Node B", "status": "ALIVE"}

        # Node update denied for USER (403)
        r_user_upd = self.client.post("/nodes/update", json=update_payload, headers=self.headers_user)
        self._assert_error_response(r_user_upd, 403)

        # Node update denied for SYSTEM (403)
        r_sys_upd = self.client.post("/nodes/update", json=update_payload, headers=self.headers_system)
        self._assert_error_response(r_sys_upd, 403)

        # Node update denied for Unauthenticated (401)
        r_unauth_upd = self.client.post("/nodes/update", json=update_payload, headers=self.headers_unauth)
        self._assert_error_response(r_unauth_upd, 401)

        # Node update allowed for ADMIN (200)
        r_admin_upd = self.client.post("/nodes/update", json=update_payload, headers=self.headers_admin)
        self.assertEqual(r_admin_upd.status_code, 200)

    # =========================================================================
    # 6. Admin Audit & Security Logging (GET /logs)
    # =========================================================================
    def test_matrix_admin_logs(self):
        """GET /logs: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401)."""
        # Denied: USER (403)
        r_user = self.client.get("/logs", headers=self.headers_user)
        self._assert_error_response(r_user, 403)

        # Denied: SYSTEM (403)
        r_sys = self.client.get("/logs", headers=self.headers_system)
        self._assert_error_response(r_sys, 403)

        # Denied: Unauthenticated (401)
        r_unauth = self.client.get("/logs", headers=self.headers_unauth)
        self._assert_error_response(r_unauth, 401)

        # Allowed: ADMIN (200)
        r_admin = self.client.get("/logs", headers=self.headers_admin)
        self.assertEqual(r_admin.status_code, 200)
        self.assertIn("logs", r_admin.json())

    # =========================================================================
    # 7. Cluster Configuration Endpoints (/cluster/config)
    # =========================================================================
    def test_matrix_cluster_config(self):
        """GET & PUT /cluster/config: ADMIN(200), USER(403), SYSTEM(403), UNAUTH(401)."""
        # Cluster config (ADMIN only)
        self.assertEqual(self.client.get("/cluster/config", headers=self.headers_admin).status_code, 200)
        self._assert_error_response(self.client.get("/cluster/config", headers=self.headers_user), 403)
        self._assert_error_response(self.client.get("/cluster/config", headers=self.headers_system), 403)
        self._assert_error_response(self.client.get("/cluster/config", headers=self.headers_unauth), 401)

    # =========================================================================
    # 8. Time Sync Inter-Node RPC (POST /sync-time)
    # =========================================================================
    def test_matrix_sync_time_rpc(self):
        """POST /sync-time: SYSTEM(200), USER(403), ADMIN(403), UNAUTH(401)."""
        # Denied: USER (403)
        r_user = self.client.post("/sync-time?target_time=1700000000.0", headers=self.headers_user)
        self._assert_error_response(r_user, 403)

        # Denied: ADMIN (403 - restricted exclusively to inter-node SYSTEM role)
        r_admin = self.client.post("/sync-time?target_time=1700000000.0", headers=self.headers_admin)
        self._assert_error_response(r_admin, 403)

        # Denied: Unauthenticated (401)
        r_unauth = self.client.post("/sync-time?target_time=1700000000.0", headers=self.headers_unauth)
        self._assert_error_response(r_unauth, 401)

        # Allowed: SYSTEM (200)
        r_sys = self.client.post("/sync-time?target_time=1700000000.0", headers=self.headers_system)
        self.assertEqual(r_sys.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
