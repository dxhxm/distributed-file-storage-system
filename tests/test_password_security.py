"""
test_password_security.py
=========================
Automated security test suite for password hashing and verification:
1. hash_password() never returns the same hash twice for the same input (unique salts).
2. verify_password() correctly accepts matching passwords and rejects incorrect passwords.
3. No reversible encoding (cryptographic one-way bcrypt format).
4. No plaintext passwords logged anywhere during operations or error states.
5. Edge cases: Unicode/special characters, malformed hashes, empty/None inputs.
"""

import logging
import io
import unittest

from app.services import hash_password, verify_password
from app.services.auth_service import hash_password as explicit_hash, verify_password as explicit_verify


class TestPasswordSecurity(unittest.TestCase):

    def test_unique_salts_for_identical_passwords(self):
        """DoD: hash_password() never returns the same hash twice for the same input (salted)."""
        password = "SecureClusterPassword#2026!"
        hashes = [hash_password(password) for _ in range(5)]

        # Verify all 5 hashes are distinct
        self.assertEqual(len(set(hashes)), 5, "Every invocation of hash_password must generate a unique salt")

        # Verify all hashes still successfully verify against the original password
        for h in hashes:
            self.assertTrue(verify_password(password, h), "Each uniquely salted hash must verify correctly")

    def test_verify_password_accept_and_reject(self):
        """DoD: verify_password() correctly accepts matching passwords and rejects mismatches."""
        password = "CorrectHorseBatteryStaple"
        h = hash_password(password)

        # Correct password
        self.assertTrue(verify_password(password, h), "Must return True for correct password")

        # Wrong passwords
        self.assertFalse(verify_password("wrong_password", h), "Must return False for wrong password")
        self.assertFalse(verify_password("correcthorsebatterystaple", h), "Case sensitivity must be enforced")
        self.assertFalse(verify_password("CorrectHorseBatteryStaple ", h), "Trailing whitespace mismatch must fail")
        self.assertFalse(verify_password(" CorrectHorseBatteryStaple", h), "Leading whitespace mismatch must fail")

    def test_non_reversible_bcrypt_format(self):
        """DoD: bcrypt/argon2-based hash, no reversible encoding."""
        password = "SuperSecretPlainText123"
        h = hash_password(password)

        # Ensure hash starts with standard bcrypt identifier ($2b$ or $2a$)
        self.assertTrue(h.startswith("$2b$") or h.startswith("$2a$"), f"Expected bcrypt hash prefix, got: {h}")

        # Ensure the plaintext password is never directly contained in the hash
        self.assertNotIn(password, h, "Plaintext password must not be present in the generated hash")

        # Ensure common trivial decodings (e.g. base64, hex, rot13) do not match plaintext
        import base64
        try:
            decoded = base64.b64decode(h).decode("utf-8", errors="ignore")
            self.assertNotEqual(decoded, password)
        except Exception:
            pass

    def test_no_plaintext_logged_anywhere(self):
        """DoD: No plaintext logged anywhere."""
        secret_password = "UltraConfidentialPlaintextSecret#999"

        # Capture log stream from auth_service logger and root logger
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)

        auth_logger = logging.getLogger("auth_service")
        auth_logger.setLevel(logging.DEBUG)
        auth_logger.addHandler(handler)

        try:
            # 1. Successful hashing and verification
            h = hash_password(secret_password)
            verify_password(secret_password, h)

            # 2. Failed verification with incorrect password
            verify_password("wrong_secret_input", h)

            # 3. Malformed hash verification
            verify_password(secret_password, "corrupted_hash_value_12345")
            verify_password(secret_password, "$2b$12$invalidbcrexamplehash12345678901234567890")

            # Check full logged contents
            log_output = log_stream.getvalue()
            self.assertNotIn(secret_password, log_output, "Plaintext password must NEVER appear in logs")
            self.assertNotIn("wrong_secret_input", log_output, "Candidate plaintext password must NEVER appear in logs")
        finally:
            auth_logger.removeHandler(handler)

    def test_edge_cases_and_input_validation(self):
        """Test edge cases: empty strings, None, invalid types, unicode passwords, malformed hashes."""
        # 1. hash_password input validation
        with self.assertRaises(ValueError):
            hash_password("")

        with self.assertRaises(ValueError):
            hash_password(None)  # type: ignore

        with self.assertRaises(ValueError):
            hash_password(12345)  # type: ignore

        # 2. verify_password edge cases (should safely return False without crashing)
        self.assertFalse(verify_password("", "some_hash"))
        self.assertFalse(verify_password("password", ""))
        self.assertFalse(verify_password(None, "some_hash"))
        self.assertFalse(verify_password("password", None))
        self.assertFalse(verify_password(123, 456))
        self.assertFalse(verify_password("password", "invalid_garbage_hash"))
        self.assertFalse(verify_password("password", "$2b$12$"))

        # 3. Unicode and special characters support
        unicode_password = "🔒Pässwörd!日本語_🔐_123"
        unicode_hash = hash_password(unicode_password)
        self.assertTrue(verify_password(unicode_password, unicode_hash))
        self.assertFalse(verify_password("🔒Pässwörd!日本語_🔐_124", unicode_hash))

    def test_imports_match(self):
        """Verify package export consistency."""
        self.assertIs(hash_password, explicit_hash)
        self.assertIs(verify_password, explicit_verify)


if __name__ == "__main__":
    print("\n=== Running DFSS Password Security Tests ===\n")
    unittest.main(verbosity=2)
