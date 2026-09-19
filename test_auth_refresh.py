"""
test_auth_refresh.py
====================
Automated test suite for Token Refresh and Expiry Handling per Section 26.
Validates:
1. POST /auth/login returns both access_token and refresh_token.
2. POST /auth/refresh exchanges a valid refresh token for fresh access & refresh tokens.
3. Refresh route aliases (/auth/refresh and /refresh) behave identically.
4. Revoked / Inactive user cannot refresh tokens (DoD: Refresh does not extend revoked access).
5. Deleted / non-existent user cannot refresh tokens.
6. Expired refresh token is rejected with 401 and distinguishable error header.
7. Access token cannot be misused as a refresh token (token type isolation).
8. Malformed, empty, or tampered refresh tokens are rejected with 401.
9. Live role updates in the database are reflected in the refreshed access token.
10. Unit tests for create_refresh_token and decode_refresh_token in jwt_service.
"""

import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient

os.environ["JWT_SECRET"] = "super-secret-key-for-auth-refresh-test-32bytes"
os.environ["JWT_EXPIRY_MINUTES"] = "15"
os.environ["JWT_REFRESH_EXPIRY_DAYS"] = "7"

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.services.user_storage import (
    create_user,
    delete_user,
    get_connection,
    init_db,
)


class TestAuthRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.plain_pwd = "UserSecretPassword123!"

    def setUp(self):
        delete_user("operator_bob")
        delete_user("operator_revoked")
        self.user_record = create_user(
            User(
                username="operator_bob",
                hashed_password=hash_password(self.plain_pwd),
                role=Role.USER,
                is_active=True,
            )
        )
        self.user_id = self.user_record["id"]

    def tearDown(self):
        delete_user("operator_bob")
        delete_user("operator_revoked")

    def test_login_issues_both_access_and_refresh_tokens(self):
        """Validates that POST /auth/login returns both access_token and refresh_token."""
        response = self.client.post(
            "/auth/login",
            json={"username": "operator_bob", "password": self.plain_pwd},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["username"], "operator_bob")
        self.assertEqual(data["user_id"], self.user_id)

        # Verify access token payload
        access_claims = decode_access_token(data["access_token"])
        self.assertEqual(access_claims["sub"], self.user_id)
        self.assertEqual(access_claims["role"], "USER")
        self.assertEqual(access_claims["token_type"], "access")

        # Verify refresh token payload
        refresh_claims = decode_refresh_token(data["refresh_token"])
        self.assertEqual(refresh_claims["sub"], self.user_id)
        self.assertEqual(refresh_claims["role"], "USER")
        self.assertEqual(refresh_claims["token_type"], "refresh")

    def test_successful_refresh_token_exchange(self):
        """Validates exchanging a valid refresh token for newly issued tokens."""
        # 1. Login to obtain tokens
        login_res = self.client.post(
            "/auth/login",
            json={"username": "operator_bob", "password": self.plain_pwd},
        )
        refresh_token = login_res.json()["refresh_token"]

        # 2. Exchange refresh token
        refresh_res = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(refresh_res.status_code, 200)
        data = refresh_res.json()

        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["username"], "operator_bob")
        self.assertEqual(data["user_id"], self.user_id)

        # Verify refreshed access token is valid
        new_access_claims = decode_access_token(data["access_token"])
        self.assertEqual(new_access_claims["sub"], self.user_id)
        self.assertEqual(new_access_claims["role"], "USER")

    def test_refresh_route_alias_works(self):
        """Validates that /refresh alias route works identically to /auth/refresh."""
        refresh_token = create_refresh_token(
            user_id=self.user_id,
            role=Role.USER,
            username="operator_bob",
        )

        response = self.client.post(
            "/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())
        self.assertIn("refresh_token", response.json())

    def test_revoked_or_inactive_user_cannot_refresh(self):
        """DoD: Refresh does not silently extend a revoked/inactive user's access."""
        # 1. User logs in while active
        login_res = self.client.post(
            "/auth/login",
            json={"username": "operator_bob", "password": self.plain_pwd},
        )
        refresh_token = login_res.json()["refresh_token"]

        # 2. Admin revokes/deactivates the user account in the database
        conn = get_connection()
        with conn:
            conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (self.user_id,))
        conn.close()

        # 3. User attempts to refresh token -> Must be rejected with 401
        refresh_res = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(refresh_res.status_code, 401)
        self.assertIn("disabled, inactive, or revoked", refresh_res.json()["detail"])

    def test_deleted_user_cannot_refresh(self):
        """Validates that refresh fails with 401 if user account was deleted from DB."""
        refresh_token = create_refresh_token(
            user_id=self.user_id,
            role=Role.USER,
            username="operator_bob",
        )

        # Delete user record
        delete_user("operator_bob")

        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("no longer exists", response.json()["detail"])

    def test_expired_refresh_token_rejected_with_distinguishable_header(self):
        """DoD: Expired-but-refreshable token validation enforces expiration correctly."""
        expired_refresh_token = create_refresh_token(
            user_id=self.user_id,
            role=Role.USER,
            expires_delta=timedelta(seconds=-10),  # expired 10s ago
        )

        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": expired_refresh_token},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Refresh token has expired")
        self.assertIn("error=\"token_expired\"", response.headers.get("WWW-Authenticate", ""))

    def test_access_token_cannot_be_used_as_refresh_token(self):
        """Security: Access token cannot be passed to /auth/refresh endpoint."""
        access_token = create_access_token(
            user_id=self.user_id,
            role=Role.USER,
            username="operator_bob",
        )

        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("not a valid refresh token", response.json()["detail"])

    def test_malformed_or_tampered_refresh_token_rejected(self):
        """Validates that malformed or tampered refresh tokens return HTTP 401."""
        valid_token = create_refresh_token(self.user_id, Role.USER)
        tampered_token = valid_token[:-6] + "invalid"

        # 1. Tampered signature
        r_tampered = self.client.post("/auth/refresh", json={"refresh_token": tampered_token})
        self.assertEqual(r_tampered.status_code, 401)

        # 2. Garbage string
        r_garbage = self.client.post("/auth/refresh", json={"refresh_token": "not-a-token-at-all"})
        self.assertEqual(r_garbage.status_code, 401)

    def test_role_update_propagates_on_token_refresh(self):
        """Validates that database role changes are immediately synced to refreshed tokens."""
        # 1. User gets refresh token as USER
        refresh_token = create_refresh_token(
            user_id=self.user_id,
            role=Role.USER,
            username="operator_bob",
        )

        # 2. Promote user to ADMIN in database
        conn = get_connection()
        with conn:
            conn.execute("UPDATE users SET role = 'ADMIN' WHERE id = ?", (self.user_id,))
        conn.close()

        # 3. Refresh token -> New access token must carry ADMIN role
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["role"], "ADMIN")

        new_access_claims = decode_access_token(data["access_token"])
        self.assertEqual(new_access_claims["role"], "ADMIN")


class TestJwtServiceRefreshTokenUnit(unittest.TestCase):
    """Unit tests for create_refresh_token and decode_refresh_token helper functions."""

    def test_create_and_decode_refresh_token_roundtrip(self):
        token = create_refresh_token(
            user_id="usr-12345",
            role=Role.ADMIN,
            username="super_admin",
        )
        claims = decode_refresh_token(token)
        self.assertEqual(claims["sub"], "usr-12345")
        self.assertEqual(claims["role"], "ADMIN")
        self.assertEqual(claims["username"], "super_admin")
        self.assertEqual(claims["token_type"], "refresh")

    def test_create_refresh_token_validation_errors(self):
        with self.assertRaises(ValueError):
            create_refresh_token("", Role.USER)

        with self.assertRaises(ValueError):
            create_refresh_token("usr-1", "")

    def test_decode_refresh_token_validation_errors(self):
        with self.assertRaises(TokenInvalidError):
            decode_refresh_token("")

        with self.assertRaises(TokenInvalidError):
            decode_refresh_token("   ")

        # Wrong secret key (ensure 32+ bytes for HMAC-SHA256)
        token = create_refresh_token("usr-1", Role.USER, secret_key="key-one-32bytes-secret-length-hex!!")
        with self.assertRaises(TokenInvalidError):
            decode_refresh_token(token, secret_key="key-two-32bytes-secret-length-hex!!")


if __name__ == "__main__":
    unittest.main()
