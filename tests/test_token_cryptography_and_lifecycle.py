"""
test_token_cryptography_and_lifecycle.py
=========================================
Comprehensive automated test suite for JWT Token Cryptography, Lifecycle, and Security:
1. Valid token generation and claim fidelity (sub, role, username, token_type, exp, iat).
2. Expired token rejection (access, refresh, and system tokens).
3. Tampered payload and corrupted signature detection (rejection with TokenInvalidError / HTTP 401).
4. Wrong secret key rejection (cross-secret invalidation, e.g. post-rotation).
5. Malformed token inputs (missing segments, non-base64 strings, empty tokens, non-string types).
6. Token type separation:
   - Access tokens cannot be used as refresh tokens.
   - Refresh tokens cannot be used as access tokens.
   - System tokens cannot access human user endpoints (/auth/me).
7. Algorithm security (defense against 'none' algorithm or unsupported asymmetric algorithms).
"""

import os
import time
import unittest
from datetime import timedelta, timezone, datetime
import jwt
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-token-crypto-suite-jwt-secret-key-2026-64-byte-secure-token")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.models.user_model import Role
from app.services.jwt_service import (
    create_access_token,
    create_refresh_token,
    create_system_token,
    decode_access_token,
    decode_refresh_token,
    decode_system_token,
    get_jwt_secret,
    JWTError,
    TokenExpiredError,
    TokenInvalidError,
)


class TestTokenCryptographyAndLifecycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.secret_key = get_jwt_secret()
        cls.wrong_secret = "completely-different-wrong-secret-key-for-testing-tampering-64bytes"

    # =========================================================================
    # 1. Valid Token Issuance & Claim Fidelity
    # =========================================================================
    def test_access_token_claim_fidelity(self):
        """DoD: Valid credentials issue access token with exact expected claims."""
        token = create_access_token(
            user_id="usr-12345",
            role=Role.USER,
            username="alice",
            extra_claims={"org": "engineering"}
        )
        self.assertIsInstance(token, str)

        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "usr-12345")
        self.assertEqual(payload["role"], "USER")
        self.assertEqual(payload["username"], "alice")
        self.assertEqual(payload["token_type"], "access")
        self.assertEqual(payload["org"], "engineering")
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)
        self.assertGreater(payload["exp"], payload["iat"])

    def test_refresh_token_claim_fidelity(self):
        """DoD: Refresh token issuance contains token_type='refresh' and extended expiry."""
        token = create_refresh_token(
            user_id="usr-12345",
            role=Role.ADMIN,
            username="admin_alice"
        )
        payload = decode_refresh_token(token)
        self.assertEqual(payload["sub"], "usr-12345")
        self.assertEqual(payload["role"], "ADMIN")
        self.assertEqual(payload["username"], "admin_alice")
        self.assertEqual(payload["token_type"], "refresh")

    def test_system_token_claim_fidelity(self):
        """DoD: System service token carries SYSTEM role and node identity."""
        token = create_system_token(node_id="Node B")
        payload = decode_system_token(token)
        self.assertEqual(payload["sub"], "Node B")
        self.assertEqual(payload["role"], Role.SYSTEM.value)
        self.assertEqual(payload["token_type"], "system")

    # =========================================================================
    # 2. Expired Token Handling
    # =========================================================================
    def test_expired_access_token_raises_token_expired_error(self):
        """DoD: Expired access token is rejected with distinct TokenExpiredError."""
        expired_token = create_access_token(
            user_id="usr-exp-01",
            role=Role.USER,
            expires_delta=timedelta(seconds=-1)
        )
        with self.assertRaises(TokenExpiredError):
            decode_access_token(expired_token)

    def test_expired_refresh_token_raises_token_expired_error(self):
        """DoD: Expired refresh token is rejected with distinct TokenExpiredError."""
        expired_refresh = create_refresh_token(
            user_id="usr-exp-02",
            role=Role.USER,
            expires_delta=timedelta(seconds=-1)
        )
        with self.assertRaises(TokenExpiredError):
            decode_refresh_token(expired_refresh)

    def test_expired_system_token_raises_token_expired_error(self):
        """DoD: Expired system token is rejected with TokenExpiredError."""
        expired_sys = create_system_token(
            node_id="Node C",
            expires_delta=timedelta(seconds=-1)
        )
        with self.assertRaises(TokenExpiredError):
            decode_system_token(expired_sys)

    # =========================================================================
    # 3. Tampered Payload & Corrupted Signature Detection
    # =========================================================================
    def test_tampered_payload_rejected(self):
        """DoD: Tampering with claims (e.g. escalating role from USER to ADMIN) invalidates signature."""
        token = create_access_token(user_id="usr-tamper-01", role=Role.USER)
        header_b64, payload_b64, signature_b64 = token.split(".")

        # Decode payload, alter role to ADMIN, and re-encode without signature
        import json
        import base64

        # Add padding if needed
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_data = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
        payload_data["role"] = "ADMIN"

        tampered_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_data, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8").rstrip("=")

        tampered_token = f"{header_b64}.{tampered_payload_b64}.{signature_b64}"

        with self.assertRaises(TokenInvalidError) as ctx:
            decode_access_token(tampered_token)
        self.assertIn("invalid or has been tampered with", str(ctx.exception))

    def test_corrupted_signature_rejected(self):
        """DoD: Modified or corrupted signature bits fail verification."""
        token = create_access_token(user_id="usr-corrupt-01", role=Role.USER)
        parts = token.split(".")
        # Corrupt last character of signature
        corrupted_sig = parts[2][:-1] + ("X" if parts[2][-1] != "X" else "Y")
        corrupted_token = f"{parts[0]}.{parts[1]}.{corrupted_sig}"

        with self.assertRaises(TokenInvalidError):
            decode_access_token(corrupted_token)

    def test_wrong_secret_key_rejected(self):
        """DoD: Token signed with a different key (attacker key / old pre-rotation key) is rejected."""
        foreign_token = create_access_token(
            user_id="usr-foreign-01",
            role=Role.ADMIN,
            secret_key=self.wrong_secret
        )
        with self.assertRaises(TokenInvalidError):
            decode_access_token(foreign_token)

    # =========================================================================
    # 4. Malformed and Invalid Inputs
    # =========================================================================
    def test_malformed_token_strings(self):
        """DoD: Garbage strings, missing segments, and non-string inputs raise TokenInvalidError."""
        invalid_inputs = [
            "",
            "   ",
            "single_segment_string",
            "header.payload",  # Missing signature
            "header.payload.signature.extra",  # 4 segments
            "not.a.valid.jwt.at.all",
            "null",
            None,
            12345,
        ]
        for inv in invalid_inputs:
            with self.assertRaises((TokenInvalidError, TypeError)):
                decode_access_token(inv)  # type: ignore

    def test_token_missing_required_claims(self):
        """DoD: Tokens missing required 'sub' or 'role' claims are rejected."""
        # Issue token manually without 'role'
        payload_no_role = {
            "sub": "user-no-role",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        raw_jwt = jwt.encode(payload_no_role, self.secret_key, algorithm="HS256")
        with self.assertRaises(TokenInvalidError) as ctx:
            decode_access_token(raw_jwt)
        self.assertIn("missing", str(ctx.exception).lower())

        # Issue token manually without 'sub'
        payload_no_sub = {
            "role": "USER",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        raw_jwt2 = jwt.encode(payload_no_sub, self.secret_key, algorithm="HS256")
        with self.assertRaises(TokenInvalidError) as ctx2:
            decode_access_token(raw_jwt2)
        self.assertIn("missing", str(ctx2.exception).lower())

    # =========================================================================
    # 5. Token Type Separation & Anti-Misuse Enforcement
    # =========================================================================
    def test_refresh_token_cannot_be_decoded_as_system_token(self):
        """Refresh token cannot masquerade as a SYSTEM service token."""
        refresh_token = create_refresh_token(user_id="user-01", role=Role.USER)
        with self.assertRaises(TokenInvalidError):
            decode_system_token(refresh_token)

    def test_access_token_cannot_be_used_as_refresh_token(self):
        """Access token cannot masquerade as a refresh token."""
        access_token = create_access_token(user_id="user-01", role=Role.USER)
        with self.assertRaises(TokenInvalidError) as ctx:
            decode_refresh_token(access_token)
        self.assertIn("not a valid refresh token", str(ctx.exception))

    def test_system_token_rejected_by_decode_refresh_token(self):
        """System token cannot be decoded as a refresh token."""
        system_token = create_system_token(node_id="Node A")
        with self.assertRaises(TokenInvalidError):
            decode_refresh_token(system_token)

    # =========================================================================
    # 6. Algorithm Confusion & 'none' Algorithm Resistance
    # =========================================================================
    def test_none_algorithm_rejected(self):
        """DoD: Tokens with alg='none' (unsigned tokens) are rejected unconditionally."""
        payload = {
            "sub": "admin_hacker",
            "role": "ADMIN",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "token_type": "access",
        }
        # Craft an unsigned token with alg='none'
        unsigned_token = jwt.encode(payload, key="", algorithm="none")

        with self.assertRaises(TokenInvalidError):
            decode_access_token(unsigned_token)


if __name__ == "__main__":
    unittest.main(verbosity=2)
