"""
test_authorization_errors.py
=============================
Automated test suite verifying authorization and authentication error handling:
1. Error Shape Invariant: Every protected route returns a uniform JSON error payload `{"detail": ...}`.
2. 401 vs 403 Non-Conflation:
   - Unauthenticated requests (missing, invalid, or expired tokens) strictly return HTTP 401 Unauthorized.
   - Authenticated callers with insufficient role privileges strictly return HTTP 403 Forbidden.
   - 401 and 403 are never conflated across any endpoint category.
3. Zero User Enumeration on /auth/login:
   - Non-existent usernames and incorrect passwords return identical HTTP 401 status codes and response bodies.
   - Error messages never reveal account existence.
"""

import io
import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-auth-error-handling-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import create_access_token, create_system_token
from app.services.user_storage import create_user, delete_user, init_db


class TestAuthorizationErrorHandling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # Seed test user accounts
        delete_user("auth_err_test_user")
        cls.user_record = create_user(
            User(
                username="auth_err_test_user",
                hashed_password=hash_password("ValidPassword123!"),
                role=Role.USER,
                is_active=True,
            )
        )
        cls.user_token = create_access_token(
            user_id=cls.user_record["id"],
            role=Role.USER,
            username="auth_err_test_user"
        )

        delete_user("auth_err_test_admin")
        cls.admin_record = create_user(
            User(
                username="auth_err_test_admin",
                hashed_password=hash_password("AdminPassword123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )
        cls.admin_token = create_access_token(
            user_id=cls.admin_record["id"],
            role=Role.ADMIN,
            username="auth_err_test_admin"
        )

        cls.system_token = create_system_token(node_id="Node A")

        cls.expired_token = create_access_token(
            user_id="any-id",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}
        cls.expired_headers = {"Authorization": f"Bearer {cls.expired_token}"}
        cls.invalid_headers = {"Authorization": "Bearer bad.token.signature"}

    @classmethod
    def tearDownClass(cls):
        delete_user("auth_err_test_user")
        delete_user("auth_err_test_admin")

    # =========================================================================
    # 1. Consistent Error Shape Across All Protected Route Categories
    # =========================================================================
    def test_uniform_error_shape_on_unauthenticated_requests(self):
        """DoD: Every protected route returns the same consistent error shape ({"detail": ...})."""
        protected_routes = [
            ("GET", "/health"),
            ("GET", "/cluster/status"),
            ("GET", "/nodes"),
            ("POST", "/nodes/update?node_name=nodeA&status=ALIVE"),
            ("GET", "/files/file-12345"),
            ("POST", "/files/upload"),
            ("DELETE", "/files/file-12345"),
            ("GET", "/auth/me"),
            ("POST", "/auth/users"),
            ("POST", "/raft/request-vote"),
            ("POST", "/raft/append-entries"),
            ("POST", "/replicate"),
            ("POST", "/sync-time?target_time=100.0"),
            ("POST", "/fail-leader"),
        ]

        for method, path in protected_routes:
            if method == "GET":
                res = self.client.get(path)
            elif method == "POST":
                if "upload" in path or "replicate" in path:
                    files = {"file": ("test.txt", io.BytesIO(b"data"), "text/plain")}
                    res = self.client.post(path, files=files)
                elif "raft" in path:
                    res = self.client.post(path, json={"term": 1})
                else:
                    res = self.client.post(path)
            elif method == "DELETE":
                res = self.client.delete(path)

            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"
            )
            body = res.json()
            self.assertIn("detail", body, f"Route {path} did not return 'detail' key in error body")
            self.assertIsInstance(body["detail"], str)
            self.assertIn("X-Error-Code", res.headers)

    # =========================================================================
    # 2. Strict 401 vs 403 Non-Conflation
    # =========================================================================
    def test_401_vs_403_never_conflated_on_admin_routes(self):
        """Admin routes return 401 when unauthenticated and 403 when authenticated as non-admin."""
        delete_user("new_user_err_test")
        admin_routes = [
            ("POST", "/auth/users", {"username": "new_user_err_test", "password": "Password123!"}),
            ("POST", "/nodes/update?node_name=nodeA&status=ALIVE", None),
            ("POST", "/fail-leader", None),
        ]

        for method, path, payload in admin_routes:
            # 1. Unauthenticated -> strictly 401
            res_unauth = self.client.post(path, json=payload) if payload else self.client.post(path)
            self.assertEqual(
                res_unauth.status_code, 401,
                f"Expected 401 on unauthenticated call to {path}, got {res_unauth.status_code}"
            )
            self.assertEqual(res_unauth.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

            # 2. Authenticated as USER (insufficient role) -> strictly 403 (NOT 401)
            res_user = (
                self.client.post(path, json=payload, headers=self.user_headers)
                if payload else self.client.post(path, headers=self.user_headers)
            )
            self.assertEqual(
                res_user.status_code, 403,
                f"Expected 403 on USER role call to admin route {path}, got {res_user.status_code}"
            )
            self.assertIn("detail", res_user.json())

            # 3. Authenticated as ADMIN -> 200/201 (success)
            res_admin = (
                self.client.post(path, json=payload, headers=self.admin_headers)
                if payload else self.client.post(path, headers=self.admin_headers)
            )
            self.assertIn(res_admin.status_code, [200, 201])

        delete_user("new_user_err_test")


    def test_401_vs_403_never_conflated_on_system_routes(self):
        """System RPC routes return 401 when unauthenticated and 403 when called with human user JWT."""
        vote_payload = {
            "term": 1,
            "candidate_id": "Node B",
            "last_log_index": 0,
            "last_log_term": 0,
        }

        # /raft/request-vote
        res_unauth = self.client.post("/raft/request-vote", json=vote_payload)
        self.assertEqual(res_unauth.status_code, 401)

        res_user = self.client.post("/raft/request-vote", json=vote_payload, headers=self.user_headers)
        self.assertEqual(res_user.status_code, 403)
        self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN_SYSTEM_REQUIRED")

        res_admin = self.client.post("/raft/request-vote", json=vote_payload, headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 403)

        res_sys = self.client.post("/raft/request-vote", json=vote_payload, headers=self.system_headers)
        self.assertEqual(res_sys.status_code, 200)


    def test_expired_token_distinguishable_from_role_rejection(self):
        """Expired tokens yield 401 TOKEN_EXPIRED, never conflated with 403 Forbidden."""
        res = self.client.get("/auth/me", headers=self.expired_headers)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "TOKEN_EXPIRED")
        self.assertEqual(res.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

    # =========================================================================
    # 3. Zero Username Enumeration on /auth/login
    # =========================================================================
    def test_zero_username_enumeration_identical_response(self):
        """DoD: Authentication errors never leak whether a username exists."""
        # 1. Non-existent username
        res_nonexistent = self.client.post(
            "/auth/login",
            json={"username": "totally_nonexistent_user_99999", "password": "WrongPassword123!"}
        )

        # 2. Existing username with wrong password
        res_badpassword = self.client.post(
            "/auth/login",
            json={"username": "auth_err_test_user", "password": "WrongPassword123!"}
        )

        # Invariant 1: Both must return identical HTTP 401 status
        self.assertEqual(res_nonexistent.status_code, 401)
        self.assertEqual(res_badpassword.status_code, 401)

        # Invariant 2: Both must return exact same JSON error payload
        self.assertEqual(res_nonexistent.json(), res_badpassword.json())
        self.assertEqual(res_nonexistent.json()["detail"], "Invalid username or password")

        # Invariant 3: Both must return identical header indicators
        self.assertEqual(
            res_nonexistent.headers.get("X-Error-Code"),
            res_badpassword.headers.get("X-Error-Code")
        )
        self.assertEqual(res_nonexistent.headers.get("X-Error-Code"), "INVALID_CREDENTIALS")


if __name__ == "__main__":
    unittest.main()
