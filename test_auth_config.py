"""
test_auth_config.py
===================
Automated test suite verifying Environment & Secrets setup for Authentication:
1. .env.example documents every new auth variable (JWT_SECRET, JWT_EXPIRY_MINUTES, ADMIN_BOOTSTRAP_PASSWORD).
2. .gitignore ensures no secret files (.env, .env.*) can be committed.
3. Missing or blank JWT_SECRET fails startup loudly with RuntimeError.
4. Valid JWT_SECRET and JWT_EXPIRY_MINUTES integrate with token lifecycle.
5. ADMIN_BOOTSTRAP_PASSWORD parsing.
"""

import os
import unittest
from unittest.mock import patch

from app.models.config import (
    get_admin_bootstrap_password,
    get_jwt_expiry_minutes,
    get_jwt_secret,
    validate_auth_config,
)
from app.models.user_model import Role
from app.services import create_access_token, decode_access_token


class TestAuthConfig(unittest.TestCase):

    def test_env_example_documents_all_auth_variables(self):
        """DoD: .env.example documents every new auth variable per Section 34."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        env_example_path = os.path.join(project_root, ".env.example")

        self.assertTrue(os.path.exists(env_example_path), ".env.example must exist in project root")

        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check required auth variables documented
        self.assertIn("JWT_SECRET", content, ".env.example must document JWT_SECRET")
        self.assertIn("JWT_EXPIRY_MINUTES", content, ".env.example must document JWT_EXPIRY_MINUTES")
        self.assertIn("ADMIN_BOOTSTRAP_PASSWORD", content, ".env.example must document ADMIN_BOOTSTRAP_PASSWORD")
        self.assertIn("Section 34", content, ".env.example must reference Section 34")

        # Verify placeholders only (no real private keys)
        self.assertNotIn("real-secret", content.lower())

    def test_gitignore_protects_env_files(self):
        """DoD: No secret value committed to Git; .gitignore blocks .env files."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        gitignore_path = os.path.join(project_root, ".gitignore")

        self.assertTrue(os.path.exists(gitignore_path), ".gitignore must exist")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        self.assertIn(".env", lines, ".gitignore must ignore .env")
        self.assertIn(".env.*", lines, ".gitignore must ignore .env.*")
        self.assertIn("!.env.example", lines, ".gitignore must allow tracking .env.example")

    def test_missing_jwt_secret_fails_loudly(self):
        """DoD: Missing JWT_SECRET fails startup loudly, not silently (RuntimeError)."""
        # Test case: Unset environment variable
        with patch.dict(os.environ, {}, clear=True):
            # Ensure both keys are absent
            os.environ.pop("JWT_SECRET", None)
            os.environ.pop("JWT_SECRET_KEY", None)

            with self.assertRaises(RuntimeError) as ctx:
                get_jwt_secret()
            self.assertIn("Missing required environment variable 'JWT_SECRET'", str(ctx.exception))

            with self.assertRaises(RuntimeError) as ctx_val:
                validate_auth_config()
            self.assertIn("Missing required environment variable 'JWT_SECRET'", str(ctx_val.exception))

        # Test case: Empty string
        with patch.dict(os.environ, {"JWT_SECRET": ""}):
            with self.assertRaises(RuntimeError):
                get_jwt_secret()

        # Test case: Whitespace only
        with patch.dict(os.environ, {"JWT_SECRET": "    "}):
            with self.assertRaises(RuntimeError):
                get_jwt_secret()

    def test_valid_jwt_secret_and_expiry_resolution(self):
        """Test valid configuration resolution and token integration."""
        custom_secret = "my-custom-super-secure-jwt-signing-secret-key-2026-xyz"
        with patch.dict(os.environ, {
            "JWT_SECRET": custom_secret,
            "JWT_EXPIRY_MINUTES": "180",
            "ADMIN_BOOTSTRAP_PASSWORD": "BootstrapSecretPassword#99"
        }):
            # 1. Validation succeeds
            validate_auth_config()
            self.assertEqual(get_jwt_secret(), custom_secret)
            self.assertEqual(get_jwt_expiry_minutes(), 180)
            self.assertEqual(get_admin_bootstrap_password(), "BootstrapSecretPassword#99")

            # 2. JWT token generation uses resolved env secret and expiry
            token = create_access_token(user_id="user-cfg-01", role=Role.ADMIN)
            payload = decode_access_token(token)
            self.assertEqual(payload["sub"], "user-cfg-01")
            self.assertEqual(payload["role"], "ADMIN")

            # Expiration should be roughly 180 minutes in future
            duration_seconds = payload["exp"] - payload["iat"]
            self.assertEqual(duration_seconds, 180 * 60)

    def test_default_jwt_expiry_and_empty_admin_password(self):
        """Test fallback defaults for expiry and bootstrap password."""
        with patch.dict(os.environ, {"JWT_SECRET": "a" * 32}, clear=True):
            self.assertEqual(get_jwt_expiry_minutes(), 60)
            self.assertIsNone(get_admin_bootstrap_password())


if __name__ == "__main__":
    print("\n=== Running DFSS Auth Environment & Secrets Tests ===\n")
    unittest.main(verbosity=2)
