"""
test_auth_provisioning.py
=========================
Automated test suite verifying the Admin-Only User Provisioning endpoint (POST /auth/users):
1. Only an authenticated ADMIN can create a user (returns HTTP 201).
2. Non-admin caller gets HTTP 403 Forbidden.
3. Unauthenticated / invalid token callers get HTTP 401 Unauthorized.
4. Duplicate username is rejected cleanly with HTTP 409 Conflict.
5. Password / hashed_password is never exposed in the response.
6. Input validation (HTTP 422).
"""

import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set for the test runner process
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-running-automated-test-suite-2026-64-byte-secure-key")

from app.main import app
from app.models import Role, User
from app.services import (
    create_access_token,
    delete_user,
    get_user_by_username,
    hash_password,
    init_db,
)


class TestAuthProvisioningEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        init_db()

        # Seed admin and standard user tokens
        cls.admin_token = create_access_token(
            user_id="admin-prov-uuid-001",
            role=Role.ADMIN,
            username="cluster_master_admin"
        )
        cls.user_token = create_access_token(
            user_id="user-prov-uuid-002",
            role=Role.USER,
            username="standard_operator"
        )
        cls.expired_admin_token = create_access_token(
            user_id="admin-prov-uuid-001",
            role=Role.ADMIN,
            expires_delta=timedelta(seconds=-10)
        )

    def tearDown(self):
        # Clean up any created test users
        for username in ["prov_alice", "prov_bob_admin", "prov_sys_agent", "prov_dup_user"]:
            delete_user(username)

    def test_admin_creates_user_success(self):
        """DoD: Only an authenticated ADMIN can create a user (returns 201 & UserResponse)."""
        payload = {
            "username": "prov_alice",
            "password": "AliceSecurePassword#2026",
            "role": "USER",
            "is_active": True,
        }

        response = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=payload,
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()

        # Verify response structure and data
        self.assertIn("id", data)
        self.assertEqual(data["username"], "prov_alice")
        self.assertEqual(data["role"], "USER")
        self.assertTrue(data["is_active"])
        self.assertIn("created_at", data)

        # Security check: Password must NEVER be exposed
        self.assertNotIn("password", data)
        self.assertNotIn("hashed_password", data)

        # Verify user is persisted and can authenticate via /auth/login
        login_resp = self.client.post(
            "/auth/login",
            json={"username": "prov_alice", "password": "AliceSecurePassword#2026"}
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

    def test_admin_creates_admin_and_system_users(self):
        """Test admin can provision ADMIN and SYSTEM role accounts."""
        # 1. Provision ADMIN
        r_admin = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"username": "prov_bob_admin", "password": "BobAdminPass#2026", "role": "ADMIN"}
        )
        self.assertEqual(r_admin.status_code, 201)
        self.assertEqual(r_admin.json()["role"], "ADMIN")

        # 2. Provision SYSTEM
        r_sys = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"username": "prov_sys_agent", "password": "SystemPass#2026", "role": "SYSTEM"}
        )
        self.assertEqual(r_sys.status_code, 201)
        self.assertEqual(r_sys.json()["role"], "SYSTEM")

    def test_non_admin_caller_gets_403(self):
        """DoD: Non-admin caller gets 403 Forbidden."""
        payload = {
            "username": "prov_alice",
            "password": "AliceSecurePassword#2026",
            "role": "USER",
        }

        response = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.user_token}"},
            json=payload,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin privileges required")

        # Verify user was NOT created
        self.assertIsNone(get_user_by_username("prov_alice"))

    def test_unauthenticated_caller_gets_401(self):
        """Test unauthenticated, invalid, and expired tokens receive HTTP 401."""
        payload = {"username": "prov_alice", "password": "Password123!"}

        # 1. No Authorization header
        r_no_auth = self.client.post("/auth/users", json=payload)
        self.assertEqual(r_no_auth.status_code, 401)
        self.assertEqual(r_no_auth.json()["detail"], "Not authenticated")

        # 2. Invalid / garbage token
        r_bad_token = self.client.post(
            "/auth/users",
            headers={"Authorization": "Bearer invalid.garbage.token"},
            json=payload
        )
        self.assertEqual(r_bad_token.status_code, 401)

        # 3. Expired token
        r_expired = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.expired_admin_token}"},
            json=payload
        )
        self.assertEqual(r_expired.status_code, 401)
        self.assertEqual(r_expired.json()["detail"], "Token has expired")

    def test_duplicate_username_rejected_cleanly(self):
        """DoD: Duplicate username is rejected cleanly with HTTP 409."""
        payload = {
            "username": "prov_dup_user",
            "password": "FirstPassword#2026",
            "role": "USER",
        }

        # First creation succeeds
        r1 = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=payload,
        )
        self.assertEqual(r1.status_code, 201)

        # Second creation with identical username fails with 409
        r2 = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "username": "prov_dup_user",
                "password": "DifferentPassword#2026",
                "role": "ADMIN",
            },
        )
        self.assertEqual(r2.status_code, 409)
        self.assertIn("already exists", r2.json()["detail"])

    def test_invalid_payload_validation(self):
        """Test missing fields and invalid role values return HTTP 422."""
        # Missing password
        r1 = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"username": "prov_bad"}
        )
        self.assertEqual(r1.status_code, 422)

        # Missing username
        r2 = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"password": "Password#1"}
        )
        self.assertEqual(r2.status_code, 422)

        # Invalid role
        r3 = self.client.post(
            "/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"username": "prov_bad", "password": "pwd", "role": "SUPERUSER"}
        )
        self.assertEqual(r3.status_code, 422)

    def test_alias_route_users(self):
        """Verify alias /users endpoint functions identically to /auth/users."""
        response = self.client.post(
            "/users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"username": "prov_alice", "password": "Password123!"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "prov_alice")


if __name__ == "__main__":
    print("\n=== Running DFSS Admin User Provisioning Tests ===\n")
    unittest.main(verbosity=2)
