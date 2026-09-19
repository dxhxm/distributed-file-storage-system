"""
test_jwt_dependency.py
======================
Automated test suite verifying the JWT Validation Dependency (get_current_user):
1. Missing/malformed token returns HTTP 401.
2. Expired token returns HTTP 401 with distinguishable error code ('TOKEN_EXPIRED').
3. Valid token attaches user + role to the request context (request.state.user / request.state.role).
4. Role-based access control guards (require_role / require_admin).
5. Protected route verification on GET /auth/me and GET /me.
"""

import os
import unittest
from datetime import timedelta
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set for the test runner process
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-running-automated-test-suite-2026-64-byte-secure-key")

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_admin,
    require_role,
)
from app.main import app
from app.models import Role
from app.services import create_access_token


class TestJWTValidationDependency(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Pre-generate test tokens
        cls.valid_user_token = create_access_token(
            user_id="user-dep-101",
            role=Role.USER,
            username="alice_user"
        )
        cls.valid_admin_token = create_access_token(
            user_id="admin-dep-202",
            role=Role.ADMIN,
            username="bob_admin"
        )
        cls.valid_system_token = create_access_token(
            user_id="sys-dep-303",
            role=Role.SYSTEM,
            username="cluster_sync_agent"
        )
        cls.expired_token = create_access_token(
            user_id="user-dep-101",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

    def test_missing_token_returns_401(self):
        """DoD: Missing token returns 401."""
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "NOT_AUTHENTICATED")
        self.assertEqual(response.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    def test_malformed_and_tampered_token_returns_401(self):
        """DoD: Malformed / tampered token returns 401."""
        # 1. Garbage string
        r_garbage = self.client.get("/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
        self.assertEqual(r_garbage.status_code, 401)
        self.assertEqual(r_garbage.json()["detail"], "INVALID_TOKEN")
        self.assertEqual(r_garbage.headers.get("X-Error-Code"), "INVALID_TOKEN")

        # 2. Tampered signature
        tampered_token = self.valid_user_token[:-5] + "xxxxx"
        r_tampered = self.client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(r_tampered.status_code, 401)
        self.assertEqual(r_tampered.json()["detail"], "INVALID_TOKEN")

        # 3. Non-bearer scheme / empty bearer
        r_empty = self.client.get("/auth/me", headers={"Authorization": "Bearer "})
        self.assertEqual(r_empty.status_code, 401)

    def test_expired_token_returns_401_with_distinguishable_code(self):
        """DoD: Expired token returns 401 with a distinguishable error code ('TOKEN_EXPIRED')."""
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.expired_token}"}
        )

        self.assertEqual(response.status_code, 401)
        data = response.json()

        # Distinguishable error code in both JSON detail and X-Error-Code header
        self.assertEqual(data["detail"], "TOKEN_EXPIRED")
        self.assertEqual(response.headers.get("X-Error-Code"), "TOKEN_EXPIRED")
        self.assertIn("error_description", response.headers.get("WWW-Authenticate", ""))

    def test_valid_token_attaches_user_and_role(self):
        """DoD: Valid token attaches user + role to the request."""
        # 1. Via HTTP integration
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {self.valid_user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["user_id"], "user-dep-101")
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["username"], "alice_user")
        self.assertIn("claims", data)
        self.assertEqual(data["claims"]["sub"], "user-dep-101")

        # 2. Direct unit test verifying request.state attachment
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.credentials = self.valid_admin_token

        auth_user = self.run_async(get_current_user(mock_request, mock_credentials))

        self.assertIsInstance(auth_user, AuthenticatedUser)
        self.assertEqual(auth_user.user_id, "admin-dep-202")
        self.assertEqual(auth_user.role, "ADMIN")
        self.assertEqual(mock_request.state.user, auth_user)
        self.assertEqual(mock_request.state.role, "ADMIN")

    def test_role_based_access_control_guards(self):
        """Test require_role and require_admin RBAC functions."""
        admin_user = AuthenticatedUser(user_id="a1", role="ADMIN", username="admin1")
        standard_user = AuthenticatedUser(user_id="u1", role="USER", username="user1")
        system_user = AuthenticatedUser(user_id="s1", role="SYSTEM", username="node1")

        # 1. require_admin check
        checker = require_role(Role.ADMIN)
        self.assertEqual(self.run_async(checker(admin_user)), admin_user)

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.run_async(checker(standard_user))
        self.assertEqual(ctx.exception.status_code, 403)

        # 2. Multi-role check
        multi_checker = require_role(Role.USER, Role.ADMIN)
        self.assertEqual(self.run_async(multi_checker(admin_user)), admin_user)
        self.assertEqual(self.run_async(multi_checker(standard_user)), standard_user)

        with self.assertRaises(HTTPException) as ctx2:
            self.run_async(multi_checker(system_user))
        self.assertEqual(ctx2.exception.status_code, 403)

    def test_alias_route_me(self):
        """Verify alias /me works identically to /auth/me."""
        response = self.client.get(
            "/me",
            headers={"Authorization": f"Bearer {self.valid_user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], "user-dep-101")

    def run_async(self, coroutine):
        """Helper to run async coroutines in test methods."""
        import asyncio
        return asyncio.run(coroutine)


if __name__ == "__main__":
    print("\n=== Running DFSS JWT Validation Dependency Tests ===\n")
    unittest.main(verbosity=2)
