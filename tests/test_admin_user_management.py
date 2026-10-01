"""
test_admin_user_management.py
=============================
Automated test suite verifying Admin-Only User and Role Management endpoints
per Section 26:
- GET /auth/users: List all users in cluster (never leaks password hashes).
- PUT/POST /auth/users/{identifier}/role: Update a user's role (USER, ADMIN, SYSTEM).
- POST /auth/users/{identifier}/deactivate & PUT /auth/users/{identifier}/status: Deactivate/activate user.

DoD Invariants:
1. Only ADMIN can list, deactivate, or change user roles.
2. An admin cannot demote the last remaining ADMIN account (avoiding lockout).
3. An admin cannot deactivate the last remaining active ADMIN account (avoiding lockout).
4. Non-admin callers (USER, SYSTEM) strictly receive HTTP 403 Forbidden (never 404).
5. Unauthenticated callers strictly receive HTTP 401 Unauthorized.
6. Deactivated users cannot log in or refresh tokens.
7. Role and status changes are recorded in the audit log.
"""

import os
import tempfile
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-admin-user-mgmt-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import create_access_token, create_system_token
from app.services.user_storage import (
    create_user,
    delete_user,
    get_user_by_username,
    init_db,
    list_users,
)


class TestAdminUserRoleManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls._orig_storage_dir = os.environ.get("STORAGE_DIR")
        os.environ["STORAGE_DIR"] = cls.temp_dir.name

        init_db()
        cls.client = TestClient(app)

        # Seed Primary Admin (only admin at start)
        cls.primary_admin = create_user(
            User(
                username="admin_primary_alpha",
                hashed_password=hash_password("AdminAlphaPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )
        cls.primary_admin_token = create_access_token(
            user_id=cls.primary_admin["id"],
            role=Role.ADMIN,
            username="admin_primary_alpha"
        )
        cls.admin_headers = {"Authorization": f"Bearer {cls.primary_admin_token}"}

        # Seed Standard User
        cls.standard_user = create_user(
            User(
                username="user_bob_standard",
                hashed_password=hash_password("BobStandardPass123!"),
                role=Role.USER,
                is_active=True,
            )
        )
        cls.user_token = create_access_token(
            user_id=cls.standard_user["id"],
            role=Role.USER,
            username="user_bob_standard"
        )
        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}

        # Seed System Token
        cls.system_token = create_system_token(node_id="Node A")
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}

    def setUp(self):
        from app.services.user_storage import get_connection
        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    "DELETE FROM users WHERE username NOT IN (?, ?)",
                    ("admin_primary_alpha", "user_bob_standard")
                )
                conn.execute(
                    "UPDATE users SET role = 'ADMIN', is_active = 1 WHERE username = 'admin_primary_alpha'"
                )
                conn.execute(
                    "UPDATE users SET role = 'USER', is_active = 1 WHERE username = 'user_bob_standard'"
                )
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()
        if cls._orig_storage_dir is not None:
            os.environ["STORAGE_DIR"] = cls._orig_storage_dir
        elif "STORAGE_DIR" in os.environ:
            del os.environ["STORAGE_DIR"]

    @classmethod
    def _cleanup_test_users(cls):
        test_usernames = [
            "admin_primary_alpha",
            "admin_secondary_beta",
            "user_bob_standard",
            "user_carol_dev",
            "user_deact_target",
        ]
        for name in test_usernames:
            delete_user(name)

    # =========================================================================
    # 1. User Listing: GET /auth/users
    # =========================================================================
    def test_admin_can_list_users(self):
        """DoD: Only ADMIN can list users. Returns public UserResponse without credentials."""
        res = self.client.get("/auth/users", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        users = res.json()
        self.assertIsInstance(users, list)
        self.assertGreaterEqual(len(users), 2)

        # Verify schema invariants
        for u in users:
            self.assertIn("id", u)
            self.assertIn("username", u)
            self.assertIn("role", u)
            self.assertIn("created_at", u)
            self.assertIn("is_active", u)
            # Security invariant: NEVER expose hashed_password or password
            self.assertNotIn("hashed_password", u)
            self.assertNotIn("password", u)

        # Test route alias /users
        res_alias = self.client.get("/users", headers=self.admin_headers)
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(len(res_alias.json()), len(users))

    # =========================================================================
    # 2. Change Role: Promotion, Multi-Admin Demotion, and Lockout Prevention
    # =========================================================================
    def test_admin_can_promote_user_to_admin(self):
        """Admin can promote a standard USER to ADMIN by username or user ID."""
        # Create user to promote
        dev_user = create_user(
            User(
                username="user_carol_dev",
                hashed_password=hash_password("DevPassword123!"),
                role=Role.USER,
                is_active=True,
            )
        )

        # Promote via username in path
        res = self.client.put(
            f"/auth/users/{dev_user['username']}/role",
            json={"role": "ADMIN"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["username"], "user_carol_dev")
        self.assertEqual(data["role"], "ADMIN")

        # Verify in DB
        db_user = get_user_by_username("user_carol_dev")
        self.assertIsNotNone(db_user)
        assert db_user is not None
        self.assertEqual(db_user["role"], "ADMIN")

    def test_demote_admin_when_multiple_admins_exist_succeeds(self):
        """Demoting an ADMIN when another active ADMIN exists succeeds."""
        # 1. Seed second admin
        admin_beta = create_user(
            User(
                username="admin_secondary_beta",
                hashed_password=hash_password("BetaAdminPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )

        # 2. Demote admin_secondary_beta by UUID
        res = self.client.put(
            f"/auth/users/{admin_beta['id']}/role",
            json={"role": "USER"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "USER")

        # Verify DB
        db_beta = get_user_by_username("admin_secondary_beta")
        self.assertIsNotNone(db_beta)
        assert db_beta is not None
        self.assertEqual(db_beta["role"], "USER")

    def test_prevent_demoting_last_remaining_admin_lockout_dod(self):
        """
        DoD Invariant:
        An admin cannot demote the last remaining ADMIN account, avoiding a lockout.
        """
        # Ensure only 1 active admin exists (primary_admin)
        delete_user("admin_secondary_beta")
        delete_user("user_carol_dev")

        # Attempt to demote primary_admin to USER
        res_demote_user = self.client.put(
            f"/auth/users/{self.primary_admin['id']}/role",
            json={"role": "USER"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_demote_user.status_code, 400)
        self.assertIn("Cannot demote the last remaining active ADMIN account", res_demote_user.json()["detail"])

        # Attempt to demote primary_admin to SYSTEM
        res_demote_sys = self.client.put(
            f"/auth/users/{self.primary_admin['username']}/role",
            json={"role": "SYSTEM"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_demote_sys.status_code, 400)
        self.assertIn("lockout", res_demote_sys.json()["detail"])

        # Verify primary_admin is still ADMIN
        admin_rec = get_user_by_username("admin_primary_alpha")
        self.assertIsNotNone(admin_rec)
        assert admin_rec is not None
        self.assertEqual(admin_rec["role"], "ADMIN")

    def test_change_role_nonexistent_user_returns_404(self):
        """Updating role for non-existent user identifier returns 404."""
        res = self.client.put(
            "/auth/users/non_existent_uuid_9999/role",
            json={"role": "ADMIN"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"])

    # =========================================================================
    # 3. User Deactivation, Login Rejection, and Last Admin Lockout
    # =========================================================================
    def test_admin_can_deactivate_and_reactivate_user(self):
        """Admin can deactivate user; deactivated user cannot log in; reactivation restores access."""
        deact_user = create_user(
            User(
                username="user_deact_target",
                hashed_password=hash_password("TargetPass123!"),
                role=Role.USER,
                is_active=True,
            )
        )

        # 1. Login before deactivation -> succeeds (200)
        res_login_before = self.client.post(
            "/auth/login",
            json={"username": "user_deact_target", "password": "TargetPass123!"}
        )
        self.assertEqual(res_login_before.status_code, 200)
        refresh_token = res_login_before.json()["refresh_token"]

        # 2. Deactivate user via POST /auth/users/{identifier}/deactivate
        res_deact = self.client.post(
            f"/auth/users/{deact_user['username']}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(res_deact.status_code, 200)
        self.assertFalse(res_deact.json()["is_active"])

        # 3. Login after deactivation -> rejected with 401 ACCOUNT_DISABLED
        res_login_after = self.client.post(
            "/auth/login",
            json={"username": "user_deact_target", "password": "TargetPass123!"}
        )
        self.assertEqual(res_login_after.status_code, 401)
        self.assertEqual(res_login_after.headers.get("X-Error-Code"), "ACCOUNT_DISABLED")

        # 4. Refresh token for deactivated user -> rejected with 401
        res_refresh = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        self.assertEqual(res_refresh.status_code, 401)

        # 5. Reactivate user via PUT /auth/users/{identifier}/status
        res_react = self.client.put(
            f"/auth/users/{deact_user['id']}/status",
            json={"is_active": True},
            headers=self.admin_headers,
        )
        self.assertEqual(res_react.status_code, 200)
        self.assertTrue(res_react.json()["is_active"])

        # 6. Login after reactivation -> succeeds
        res_login_react = self.client.post(
            "/auth/login",
            json={"username": "user_deact_target", "password": "TargetPass123!"}
        )
        self.assertEqual(res_login_react.status_code, 200)

    def test_prevent_deactivating_last_remaining_admin_lockout(self):
        """
        DoD Invariant:
        An admin cannot deactivate the last remaining active ADMIN account, avoiding lockout.
        """
        # Ensure only primary_admin is active admin
        delete_user("admin_secondary_beta")

        # 1. Attempt deactivation via /deactivate route
        res_deact = self.client.post(
            f"/auth/users/{self.primary_admin['id']}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(res_deact.status_code, 400)
        self.assertIn("Cannot deactivate the last remaining active ADMIN account", res_deact.json()["detail"])

        # 2. Attempt deactivation via /status route
        res_status = self.client.put(
            f"/auth/users/{self.primary_admin['username']}/status",
            json={"is_active": False},
            headers=self.admin_headers,
        )
        self.assertEqual(res_status.status_code, 400)
        self.assertIn("lockout", res_status.json()["detail"])

        # Verify admin is still active
        admin_rec = get_user_by_username("admin_primary_alpha")
        self.assertIsNotNone(admin_rec)
        assert admin_rec is not None
        self.assertTrue(admin_rec["is_active"])

    def test_deactivate_nonexistent_user_returns_404(self):
        """Deactivating non-existent user returns 404."""
        res = self.client.post(
            "/auth/users/non_existent_uuid_8888/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 404)

    # =========================================================================
    # 4. RBAC: Strict ADMIN-Only Enforcement (403 for USER/SYSTEM, 401 for Unauth)
    # =========================================================================
    def test_non_admin_roles_forbidden_on_all_admin_user_routes(self):
        """
        DoD: Only ADMIN can list/deactivate/change roles.
        Non-admin authenticated callers (USER, SYSTEM) strictly receive 403 Forbidden.
        """
        endpoints = [
            ("GET", "/auth/users", None),
            ("GET", "/users", None),
            ("PUT", f"/auth/users/{self.standard_user['id']}/role", {"role": "ADMIN"}),
            ("POST", f"/auth/users/{self.standard_user['id']}/deactivate", None),
            ("PUT", f"/auth/users/{self.standard_user['id']}/status", {"is_active": False}),
        ]

        for method, path, payload in endpoints:
            # 1. USER role -> 403
            if method == "GET":
                res_user = self.client.get(path, headers=self.user_headers)
            elif method == "POST":
                res_user = self.client.post(path, json=payload, headers=self.user_headers) if payload else self.client.post(path, headers=self.user_headers)
            else:
                res_user = self.client.put(path, json=payload, headers=self.user_headers)

            self.assertEqual(
                res_user.status_code, 403,
                f"Expected 403 for USER role on {method} {path}, got {res_user.status_code}"
            )
            self.assertEqual(res_user.json()["detail"], "Admin privileges required")
            self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN")

            # 2. SYSTEM role -> 403
            if method == "GET":
                res_sys = self.client.get(path, headers=self.system_headers)
            elif method == "POST":
                res_sys = self.client.post(path, json=payload, headers=self.system_headers) if payload else self.client.post(path, headers=self.system_headers)
            else:
                res_sys = self.client.put(path, json=payload, headers=self.system_headers)

            self.assertEqual(
                res_sys.status_code, 403,
                f"Expected 403 for SYSTEM role on {method} {path}, got {res_sys.status_code}"
            )
            self.assertEqual(res_sys.json()["detail"], "Admin privileges required")

    def test_unauthenticated_requests_return_401(self):
        """Unauthenticated requests strictly return 401 Unauthorized."""
        endpoints = [
            ("GET", "/auth/users"),
            ("PUT", f"/auth/users/{self.standard_user['id']}/role", {"role": "ADMIN"}),
            ("POST", f"/auth/users/{self.standard_user['id']}/deactivate"),
            ("PUT", f"/auth/users/{self.standard_user['id']}/status", {"is_active": False}),
        ]

        for item in endpoints:
            method = item[0]
            path = item[1]
            payload = item[2] if len(item) > 2 else None

            if method == "GET":
                res = self.client.get(path)
            elif method == "POST":
                res = self.client.post(path, json=payload) if payload else self.client.post(path)
            else:
                res = self.client.put(path, json=payload)

            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 for unauthenticated request on {method} {path}, got {res.status_code}"
            )
            self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
