"""
test_auth_login.py
==================
Automated test suite verifying POST /auth/login endpoint:
1. Correct credentials return HTTP 200, valid JWT, and correct user role.
2. Incorrect credentials return HTTP 401 with zero user-enumeration hint.
3. Inactive users are rejected.
4. Input validation (HTTP 422 on missing/empty fields).
5. Token verification against jwt_service.
"""

import os
import unittest
from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set for the test runner process
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-running-automated-test-suite-2026-64-byte-secure-key")

from app.main import app
from app.models import Role, User
from app.services import (
    create_user,
    decode_access_token,
    delete_user,
    get_user_by_username,
    hash_password,
    init_db,
)


class TestAuthLoginEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        init_db()

        # Seed test users
        cls.user_password = "UserPassword123!"
        cls.admin_password = "AdminPassword456!"
        cls.inactive_password = "InactivePassword789!"

        # 1. Standard active user
        delete_user("test_user_std")
        cls.std_user = User(
            username="test_user_std",
            hashed_password=hash_password(cls.user_password),
            role=Role.USER,
            is_active=True
        )
        cls.std_record = create_user(cls.std_user)

        # 2. Admin active user
        delete_user("test_admin_usr")
        cls.admin_user = User(
            username="test_admin_usr",
            hashed_password=hash_password(cls.admin_password),
            role=Role.ADMIN,
            is_active=True
        )
        cls.admin_record = create_user(cls.admin_user)

        # 3. Inactive user
        delete_user("test_inactive_usr")
        cls.inactive_user = User(
            username="test_inactive_usr",
            hashed_password=hash_password(cls.inactive_password),
            role=Role.USER,
            is_active=False
        )
        cls.inactive_record = create_user(cls.inactive_user)

    @classmethod
    def tearDownClass(cls):
        delete_user("test_user_std")
        delete_user("test_admin_usr")
        delete_user("test_inactive_usr")

    def test_login_success_user_role(self):
        """DoD: Correct credentials return a valid JWT and role (USER)."""
        response = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["username"], "test_user_std")
        self.assertEqual(data["user_id"], self.std_record["id"])
        self.assertGreater(data["expires_in_minutes"], 0)

        # Validate token payload losslessly
        payload = decode_access_token(data["access_token"])
        self.assertEqual(payload["sub"], self.std_record["id"])
        self.assertEqual(payload["role"], "USER")
        self.assertEqual(payload["username"], "test_user_std")

    def test_login_success_admin_role(self):
        """DoD: Correct credentials return a valid JWT and role (ADMIN)."""
        response = self.client.post(
            "/auth/login",
            json={"username": "test_admin_usr", "password": self.admin_password}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["role"], "ADMIN")

        payload = decode_access_token(data["access_token"])
        self.assertEqual(payload["role"], "ADMIN")

    def test_login_incorrect_password_no_enumeration_hint(self):
        """DoD: Incorrect credentials return 401 with no user-enumeration hint."""
        response = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": "WrongPasswordHere#999"}
        )

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data.get("detail"), "Invalid username or password")
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Bearer")

    def test_login_nonexistent_user_no_enumeration_hint(self):
        """DoD: Non-existent user returns 401 with identical error to wrong password (no enumeration hint)."""
        # Response for non-existent user
        resp_nonexistent = self.client.post(
            "/auth/login",
            json={"username": "completely_unknown_user_999", "password": "AnyPassword123"}
        )

        # Response for wrong password on existing user
        resp_wrong_pw = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": "WrongPasswordHere#999"}
        )

        # Both must return HTTP 401 with the exact same detail string
        self.assertEqual(resp_nonexistent.status_code, 401)
        self.assertEqual(resp_wrong_pw.status_code, 401)
        self.assertEqual(resp_nonexistent.json()["detail"], resp_wrong_pw.json()["detail"])
        self.assertEqual(resp_nonexistent.json()["detail"], "Invalid username or password")

    def test_inactive_user_is_rejected(self):
        """DoD: Inactive user is rejected."""
        response = self.client.post(
            "/auth/login",
            json={"username": "test_inactive_usr", "password": self.inactive_password}
        )

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("inactive", data.get("detail", "").lower())

    def test_login_validation_errors(self):
        """Test missing fields and empty payloads return HTTP 422."""
        # Missing password
        r1 = self.client.post("/auth/login", json={"username": "test_user_std"})
        self.assertEqual(r1.status_code, 422)

        # Missing username
        r2 = self.client.post("/auth/login", json={"password": self.user_password})
        self.assertEqual(r2.status_code, 422)

        # Empty strings
        r3 = self.client.post("/auth/login", json={"username": "", "password": "valid_password"})
        self.assertEqual(r3.status_code, 422)

        r4 = self.client.post("/auth/login", json={"username": "valid_user", "password": ""})
        self.assertEqual(r4.status_code, 422)

    def setUp(self):
        # Reset rate limiter before each test case
        from app.services.rate_limiter import auth_rate_limiter
        auth_rate_limiter.reset()

    def test_login_alias_route(self):
        """Verify alias /login works identically to /auth/login."""
        response = self.client.post(
            "/login",
            json={"username": "test_user_std", "password": self.user_password}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_brute_force_failed_logins_throttled_with_429(self):
        """DoD: Repeated failed logins from one source are throttled/locked temporarily (Section 33)."""
        client_ip = "192.168.50.10"
        headers = {"X-Forwarded-For": client_ip}

        # First 5 failed login attempts return 401 Unauthorized
        for i in range(5):
            resp = self.client.post(
                "/auth/login",
                json={"username": "test_user_std", "password": "WrongPassword#999"},
                headers=headers,
            )
            self.assertEqual(resp.status_code, 401, f"Attempt {i+1} should return 401")

        # 6th attempt is throttled and returns 429 Too Many Requests
        throttled_resp = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": "WrongPassword#999"},
            headers=headers,
        )
        self.assertEqual(throttled_resp.status_code, 429)
        self.assertIn("Too many failed login attempts", throttled_resp.json().get("detail", ""))
        self.assertIn("Retry-After", throttled_resp.headers)
        self.assertGreater(int(throttled_resp.headers["Retry-After"]), 0)
        self.assertEqual(throttled_resp.headers.get("X-Error-Code"), "RATE_LIMITED")

    def test_rate_limit_cooldown_permits_legitimate_login(self):
        """DoD: Legitimate retries after cooldown succeed (Section 33)."""
        from app.services.rate_limiter import auth_rate_limiter
        import time

        client_ip = "192.168.50.20"
        headers = {"X-Forwarded-For": client_ip}

        # Lock out the client with 5 failed attempts
        for _ in range(5):
            self.client.post(
                "/auth/login",
                json={"username": "test_user_std", "password": "BadPassword123"},
                headers=headers,
            )

        # Confirm locked out
        locked_resp = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password},
            headers=headers,
        )
        self.assertEqual(locked_resp.status_code, 429)

        # Simulate cooldown expiration by fast-forwarding the lockout expiry in rate limiter
        with auth_rate_limiter._lock:
            if client_ip in auth_rate_limiter._lockouts:
                # Set lockout to past timestamp
                auth_rate_limiter._lockouts[client_ip] = time.time() - 1

        # Now legitimate login succeeds
        success_resp = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password},
            headers=headers,
        )
        self.assertEqual(success_resp.status_code, 200)
        self.assertIn("access_token", success_resp.json())

    def test_successful_login_resets_rate_limiter_counter(self):
        """Successful login resets failure counter so next failures start from 0."""
        client_ip = "192.168.50.30"
        headers = {"X-Forwarded-For": client_ip}

        # 4 failed attempts (1 below threshold 5)
        for _ in range(4):
            r = self.client.post(
                "/auth/login",
                json={"username": "test_user_std", "password": "WrongPassword"},
                headers=headers,
            )
            self.assertEqual(r.status_code, 401)

        # Successful login resets the counter
        success = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password},
            headers=headers,
        )
        self.assertEqual(success.status_code, 200)

        # Another 4 failed attempts should still be 401 (not 429), since counter was reset
        for _ in range(4):
            r = self.client.post(
                "/auth/login",
                json={"username": "test_user_std", "password": "WrongPassword"},
                headers=headers,
            )
            self.assertEqual(r.status_code, 401)

    def test_rate_limiting_isolated_by_client_source(self):
        """Attacker IP getting locked out does not affect distinct legitimate user IP."""
        attacker_ip = "10.200.1.1"
        user_ip = "10.200.1.2"

        # Lock out attacker IP
        for _ in range(5):
            self.client.post(
                "/auth/login",
                json={"username": "test_user_std", "password": "BruteForceAttempt"},
                headers={"X-Forwarded-For": attacker_ip},
            )

        attacker_resp = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password},
            headers={"X-Forwarded-For": attacker_ip},
        )
        self.assertEqual(attacker_resp.status_code, 429)

        # Legitimate user from distinct IP can log in without issue
        user_resp = self.client.post(
            "/auth/login",
            json={"username": "test_user_std", "password": self.user_password},
            headers={"X-Forwarded-For": user_ip},
        )
        self.assertEqual(user_resp.status_code, 200)
        self.assertIn("access_token", user_resp.json())


if __name__ == "__main__":
    print("\n=== Running DFSS POST /auth/login Route Tests ===\n")
    unittest.main(verbosity=2)
