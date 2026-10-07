"""
test_security_review_pass.py
============================
Deliberate Attack-Style Security Review Test Suite:
1. Token Tampering:
   - Payload claim tampering (e.g. escalating role from USER to ADMIN).
   - User identity spoofing (altering 'sub' claim).
   - Signature stripping / algorithm manipulation ('none' algorithm).
   - Corrupted signature bytes / bit flips.
   - Forged signing keys (tokens signed with attacker secrets).
2. Token Lifecycle & Replay:
   - Expired token reuse across protected routes.
   - Cross-endpoint token misuse (refresh token on protected API, access token on /auth/refresh).
   - Revoked / deactivated user token replay on refresh endpoints.
3. Parameter Manipulation & Privilege Escalation:
   - Custom header injection (X-Role, X-Admin, X-User-Role) by non-admin users.
   - Query parameter spoofing (?role=ADMIN, ?is_admin=true).
   - Self-privilege escalation attempts via user management endpoints.
   - Admin account creation attempts by standard users.
   - Last-admin lockout protection attack prevention.
"""

import base64
import json
import os
import tempfile
import time
import unittest
from datetime import timedelta
import jwt

from fastapi.testclient import TestClient

# Ensure test JWT_SECRET is set
os.environ.setdefault("JWT_SECRET", "test-security-review-pass-jwt-secret-key-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import (
    create_access_token,
    create_refresh_token,
    create_system_token,
    get_jwt_secret,
)
from app.services.user_storage import (
    create_user,
    delete_user,
    init_db,
    update_user_status,
)


class TestSecurityReviewPass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls._orig_storage_dir = os.environ.get("STORAGE_DIR")
        os.environ["STORAGE_DIR"] = cls.temp_dir.name

        init_db()
        cls.client = TestClient(app)
        cls.server_secret = get_jwt_secret()

        # 1. Attacker (Standard USER)
        delete_user("attacker_usr")
        cls.attacker_record = create_user(
            User(
                username="attacker_usr",
                hashed_password=hash_password("AttackerPass123!"),
                role=Role.USER,
                is_active=True,
            )
        )
        cls.attacker_token = create_access_token(
            user_id=cls.attacker_record["id"],
            role=Role.USER,
            username="attacker_usr",
        )
        cls.attacker_refresh_token = create_refresh_token(
            user_id=cls.attacker_record["id"],
            role=Role.USER,
            username="attacker_usr",
        )

        # 2. Legitimate ADMIN
        delete_user("victim_admin")
        cls.admin_record = create_user(
            User(
                username="victim_admin",
                hashed_password=hash_password("AdminPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )
        cls.admin_token = create_access_token(
            user_id=cls.admin_record["id"],
            role=Role.ADMIN,
            username="victim_admin",
        )

        # 3. Secondary Admin (for lockout tests)
        delete_user("second_admin")
        cls.second_admin_record = create_user(
            User(
                username="second_admin",
                hashed_password=hash_password("SecondAdminPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )

    @classmethod
    def tearDownClass(cls):
        delete_user("attacker_usr")
        delete_user("victim_admin")
        delete_user("second_admin")
        cls.temp_dir.cleanup()
        if cls._orig_storage_dir:
            os.environ["STORAGE_DIR"] = cls._orig_storage_dir
        else:
            os.environ.pop("STORAGE_DIR", None)

    # =========================================================================
    # 1. Token Tampering Attack Vectors
    # =========================================================================
    def test_attack_tamper_payload_role_escalation(self):
        """DoD: Attacker tampering with token payload (USER -> ADMIN) is rejected with HTTP 401."""
        header_b64, payload_b64, sig_b64 = self.attacker_token.split(".")

        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_dict = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
        payload_dict["role"] = "ADMIN"  # Attempt privilege escalation

        tampered_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8").rstrip("=")

        tampered_jwt = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"

        # Test against admin-only route
        response = self.client.get("/auth/users", headers={"Authorization": f"Bearer {tampered_jwt}"})
        self.assertEqual(response.status_code, 401, "Tampered token must return 401 Unauthorized")
        self.assertEqual(response.json().get("detail"), "INVALID_TOKEN")

    def test_attack_tamper_payload_sub_spoofing(self):
        """DoD: Attacker altering 'sub' claim to impersonate admin is rejected with HTTP 401."""
        header_b64, payload_b64, sig_b64 = self.attacker_token.split(".")

        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_dict = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
        payload_dict["sub"] = self.admin_record["id"]  # Spoof admin user_id

        tampered_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8").rstrip("=")

        tampered_jwt = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"

        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_jwt}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("detail"), "INVALID_TOKEN")

    def test_attack_signature_stripping_none_algorithm(self):
        """DoD: Attacker stripping signature and setting alg='none' is rejected with HTTP 401."""
        unsigned_payload = {
            "sub": self.admin_record["id"],
            "role": "ADMIN",
            "username": "victim_admin",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "access",
        }
        none_token = jwt.encode(unsigned_payload, key="", algorithm="none")

        response = self.client.get("/auth/users", headers={"Authorization": f"Bearer {none_token}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("detail"), "INVALID_TOKEN")

    def test_attack_forged_secret_key(self):
        """DoD: Token signed with an unauthorized/attacker secret key is rejected with HTTP 401."""
        attacker_secret = "attacker-forged-secret-key-32bytes-long-attacker12345"
        forged_payload = {
            "sub": "attacker_usr",
            "role": "ADMIN",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "access",
        }
        forged_token = jwt.encode(forged_payload, attacker_secret, algorithm="HS256")

        response = self.client.get("/auth/users", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("detail"), "INVALID_TOKEN")

    def test_attack_corrupted_signature_bytes(self):
        """DoD: Corrupted or bit-flipped signature is rejected with HTTP 401."""
        parts = self.attacker_token.split(".")
        corrupted_token = f"{parts[0]}.{parts[1]}.{parts[2][:-3]}xyz"

        response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {corrupted_token}"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("detail"), "INVALID_TOKEN")

    # =========================================================================
    # 2. Token Lifecycle, Replay & Expiry Attacks
    # =========================================================================
    def test_attack_reused_expired_token_rejected(self):
        """DoD: Reused expired token is rejected across all route categories."""
        expired_token = create_access_token(
            user_id=self.attacker_record["id"],
            role=Role.USER,
            expires_delta=timedelta(seconds=-30),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        # Check across multiple endpoints
        endpoints = ["/auth/me", "/files", "/health", "/cluster/status"]
        for ep in endpoints:
            res = self.client.get(ep, headers=headers)
            self.assertEqual(res.status_code, 401, f"Expired token on {ep} must return 401")
            self.assertEqual(res.json().get("detail"), "TOKEN_EXPIRED")
            self.assertIn("error=\"invalid_token\"", res.headers.get("WWW-Authenticate", ""))

    def test_attack_access_token_misuse_on_refresh_route(self):
        """DoD: Using an access token as a refresh token on /auth/refresh is rejected."""
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": self.attacker_token},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("not a valid refresh token", response.json().get("detail", "").lower())

    def test_attack_deactivated_account_token_rejected_on_refresh(self):
        """DoD: Deactivated account cannot use unexpired refresh token to obtain fresh access tokens."""
        # Deactivate attacker
        update_user_status(self.attacker_record["id"], is_active=False)

        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": self.attacker_refresh_token},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("disabled", response.json().get("detail", "").lower())

        # Reactivate attacker for remaining tests
        update_user_status(self.attacker_record["id"], is_active=True)

    # =========================================================================
    # 3. Parameter Manipulation & Privilege Escalation Attacks
    # =========================================================================
    def test_attack_header_injection_role_escalation(self):
        """DoD: Standard USER attempting header spoofing (X-Role, X-Admin) is strictly rejected (403)."""
        spoofed_headers = {
            "Authorization": f"Bearer {self.attacker_token}",
            "X-Role": "ADMIN",
            "X-User-Role": "ADMIN",
            "X-Admin": "true",
            "X-Is-Admin": "1",
        }

        # Attempt to access admin routes with spoofed headers
        r1 = self.client.get("/auth/users", headers=spoofed_headers)
        self.assertEqual(r1.status_code, 403, "Header injection must not bypass role check")
        self.assertEqual(r1.headers.get("X-Error-Code"), "FORBIDDEN")

        r2 = self.client.get("/logs", headers=spoofed_headers)
        self.assertEqual(r2.status_code, 403)

        r3 = self.client.get("/replication/config", headers=spoofed_headers)
        self.assertEqual(r3.status_code, 403)

    def test_attack_query_parameter_spoofing(self):
        """DoD: Standard USER attempting query param manipulation (?role=ADMIN) is strictly rejected (403)."""
        headers = {"Authorization": f"Bearer {self.attacker_token}"}

        r1 = self.client.get("/auth/users?role=ADMIN&is_admin=true", headers=headers)
        self.assertEqual(r1.status_code, 403)

        r2 = self.client.get("/health/detailed?role=ADMIN", headers=headers)
        self.assertEqual(r2.status_code, 403)

    def test_attack_self_privilege_escalation_via_user_api(self):
        """DoD: Standard USER attempting to elevate own role via PUT /auth/users/{id}/role is rejected (403)."""
        attacker_id = self.attacker_record["id"]
        headers = {"Authorization": f"Bearer {self.attacker_token}"}

        response = self.client.put(
            f"/auth/users/{attacker_id}/role",
            json={"role": "ADMIN"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get("X-Error-Code"), "FORBIDDEN")

    def test_attack_user_create_admin_account(self):
        """DoD: Standard USER attempting to provision an admin account is rejected (403)."""
        headers = {"Authorization": f"Bearer {self.attacker_token}"}
        payload = {
            "username": "rogue_admin",
            "password": "RoguePassword123!",
            "role": "ADMIN",
            "is_active": True,
        }

        response = self.client.post("/auth/users", json=payload, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get("X-Error-Code"), "FORBIDDEN")

    def test_attack_admin_lockout_prevention(self):
        """DoD: System prevents demoting/deactivating the last remaining active ADMIN account."""
        # Deactivate second admin leaving only victim_admin as active
        update_user_status(self.second_admin_record["id"], is_active=False)

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        victim_id = self.admin_record["id"]

        # Attempt to demote the last remaining admin to USER
        demote_resp = self.client.put(
            f"/auth/users/{victim_id}/role",
            json={"role": "USER"},
            headers=admin_headers,
        )
        self.assertEqual(demote_resp.status_code, 400)
        self.assertIn("lockout", demote_resp.json().get("detail", "").lower())

        # Attempt to deactivate the last remaining admin
        deact_resp = self.client.post(
            f"/auth/users/{victim_id}/deactivate",
            headers=admin_headers,
        )
        self.assertEqual(deact_resp.status_code, 400)
        self.assertIn("lockout", deact_resp.json().get("detail", "").lower())

        # Clean up by reactivating second admin
        update_user_status(self.second_admin_record["id"], is_active=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
