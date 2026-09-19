"""
test_jwt_service.py
===================
Automated test suite for JWT encoding, decoding, and validation:
1. Issue and verify JWTs carrying 'sub' (user id) and 'role' claim per Section 26.
2. Token round-trips losslessly (sub, role, iat, exp, username, custom claims).
3. Expired token raises a distinct, catchable TokenExpiredError.
4. Signature tampering and payload modification is rejected with TokenInvalidError.
5. Invalid secret key, malformed tokens, and missing claims handling.
"""

import os
import time
import unittest
from datetime import timedelta

from app.models import Role
from app.services import (
    JWTError,
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_access_token,
)
from app.services.jwt_service import (
    create_access_token as explicit_create,
    decode_access_token as explicit_decode,
)


class TestJWTService(unittest.TestCase):

    def setUp(self):
        self._orig_secret = os.environ.get("JWT_SECRET")
        os.environ["JWT_SECRET"] = "test-jwt-secret-key-for-running-automated-test-suite-2026-64-byte-secure-key"

    def tearDown(self):
        if self._orig_secret is not None:
            os.environ["JWT_SECRET"] = self._orig_secret
        else:
            os.environ.pop("JWT_SECRET", None)

    def test_token_lossless_roundtrip(self):
        """DoD: Token round-trips (encode then decode) losslessly carrying sub and role."""
        user_id = "user-uuid-12345-abcdef"
        username = "alice_wonderland"
        custom_extra = {"session_ip": "192.168.1.100", "node_origin": "Node A"}

        # Encode token
        token = create_access_token(
            user_id=user_id,
            role=Role.ADMIN,
            username=username,
            expires_delta=timedelta(minutes=30),
            extra_claims=custom_extra
        )

        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        self.assertEqual(token.count("."), 2, "JWT must contain 2 period delimiters")

        # Decode token
        payload = decode_access_token(token)

        # Assert lossless claim retention
        self.assertEqual(payload["sub"], user_id, "Subject (sub) claim must match user_id exactly")
        self.assertEqual(payload["role"], "ADMIN", "Role claim must match Role.ADMIN")
        self.assertEqual(payload["username"], username, "Username claim must match")
        self.assertEqual(payload["session_ip"], "192.168.1.100", "Custom claims must be preserved")
        self.assertEqual(payload["node_origin"], "Node A", "Custom claims must be preserved")
        self.assertIn("iat", payload, "Issued at (iat) timestamp must be present")
        self.assertIn("exp", payload, "Expiration (exp) timestamp must be present")
        self.assertGreater(payload["exp"], payload["iat"], "Expiration must be after issue time")

    def test_all_role_enum_variants(self):
        """Test token creation and decoding across all Section 26 role types."""
        roles_to_test = [Role.USER, Role.ADMIN, Role.SYSTEM, "USER", "ADMIN", "SYSTEM"]
        for role_val in roles_to_test:
            token = create_access_token(user_id="user-999", role=role_val)
            payload = decode_access_token(token)
            expected_str = role_val.value if hasattr(role_val, "value") else role_val
            self.assertEqual(payload["role"], expected_str)

    def test_expired_token_raises_distinct_error(self):
        """DoD: Expired token raises a distinct, catchable error (TokenExpiredError)."""
        # Create an expired token by setting negative expires_delta
        expired_token = create_access_token(
            user_id="user-expired-001",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

        # 1. Distinct catchable error
        with self.assertRaises(TokenExpiredError) as ctx:
            decode_access_token(expired_token)

        self.assertIn("expired", str(ctx.exception).lower())

        # 2. Inherits from JWTError
        try:
            decode_access_token(expired_token)
        except JWTError as e:
            self.assertIsInstance(e, TokenExpiredError)

    def test_signature_tampering_is_rejected(self):
        """DoD: Signature tampering is rejected with TokenInvalidError."""
        token = create_access_token(user_id="user-valid-007", role=Role.USER)
        header, payload_b64, signature = token.split(".")

        # Case 1: Tampered signature string
        tampered_sig_token = f"{header}.{payload_b64}.{signature[:-4]}xxxx"
        with self.assertRaises(TokenInvalidError) as ctx:
            decode_access_token(tampered_sig_token)
        self.assertTrue(issubclass(TokenInvalidError, JWTError))

        # Case 2: Tampered payload with valid original signature
        tampered_payload_token = f"{header}.eyJzdWIiOiAiaGFja2VyIiwgInJvbGUiOiAiQURNSU4ifQ.{signature}"
        with self.assertRaises(TokenInvalidError):
            decode_access_token(tampered_payload_token)

        # Case 3: Tampered header
        tampered_header_token = f"eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9x.{payload_b64}.{signature}"
        with self.assertRaises(TokenInvalidError):
            decode_access_token(tampered_header_token)

    def test_invalid_secret_key_rejection(self):
        """Test that tokens signed with a different secret key fail verification."""
        token = create_access_token(
            user_id="user-secret-test",
            role=Role.USER,
            secret_key="secret-key-alpha-12345-very-long-and-secure-32-byte-string"
        )

        with self.assertRaises(TokenInvalidError):
            decode_access_token(token, secret_key="different-secret-key-beta-67890-very-long-and-secure-32-byte-string")

    def test_malformed_and_edge_case_tokens(self):
        """Test handling of empty, None, and garbage token strings."""
        malformed_inputs = [
            "",
            "   ",
            "not_a_jwt",
            "header.payload",
            "header.payload.signature.extra",
            "invalid.base64!!.sig",
        ]
        for bad_token in malformed_inputs:
            with self.assertRaises(TokenInvalidError):
                decode_access_token(bad_token)  # type: ignore

        with self.assertRaises(TokenInvalidError):
            decode_access_token(None)  # type: ignore

    def test_input_validation_on_token_creation(self):
        """Test parameter validation in create_access_token."""
        # Empty user_id
        with self.assertRaises(ValueError):
            create_access_token(user_id="", role=Role.USER)

        with self.assertRaises(ValueError):
            create_access_token(user_id="   ", role=Role.USER)

        # Empty role
        with self.assertRaises(ValueError):
            create_access_token(user_id="user-1", role="")

    def test_imports_consistency(self):
        """Test re-export from app.services."""
        self.assertIs(create_access_token, explicit_create)
        self.assertIs(decode_access_token, explicit_decode)


if __name__ == "__main__":
    print("\n=== Running DFSS JWT Encoding/Decoding Security Tests ===\n")
    unittest.main(verbosity=2)
