"""
test_secrets_audit.py
======================
Automated test suite for Secrets Management Audit per Section 34:
1. Scans repository source files to verify no hardcoded secrets or private keys are committed.
2. Asserts .env.example comprehensively documents all required configuration & secrets.
3. Validates JWT_SECRET key rotation mechanics (old secret invalidation and new secret issuance).
"""

import os
import re
import unittest
from unittest.mock import patch

from app.models.config import (
    get_jwt_secret,
    get_jwt_expiry_minutes,
    get_jwt_refresh_expiry_days,
    get_admin_bootstrap_password,
    validate_auth_config,
)
from app.models.user_model import Role
from app.services.jwt_service import (
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
    create_system_token,
    decode_system_token,
    TokenInvalidError,
)


class TestSecretsManagementAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.source_dirs = [
            os.path.join(cls.project_root, "app"),
            os.path.join(cls.project_root, "nodes"),
            os.path.join(cls.project_root, "client"),
            os.path.join(cls.project_root, "frontend", "src"),
        ]

    def test_no_hardcoded_private_keys_or_api_tokens_in_source(self):
        """DoD: grep-style scan of the repository finds no hardcoded private keys or live API credentials."""
        forbidden_patterns = [
            (re.compile(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH|PRIVATE)\s+KEY-----", re.IGNORECASE), "Private Key Block"),
            (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
            (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
            (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "Slack Token"),
        ]

        found_violations = []

        for base_dir in self.source_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                # Skip pycache, node_modules, and git directories
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git")]
                for file in files:
                    if file.endswith((".py", ".ts", ".tsx", ".js", ".json", ".html", ".css")):
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for pattern, desc in forbidden_patterns:
                                match = pattern.search(content)
                                if match:
                                    rel_path = os.path.relpath(file_path, self.project_root)
                                    found_violations.append(f"{rel_path}: Matched {desc} ('{match.group(0)}')")

        self.assertEqual(len(found_violations), 0, f"Found hardcoded secrets in source: {found_violations}")

    def test_env_example_lists_every_required_secret(self):
        """DoD: .env.example lists every required secret and cluster configuration per Section 34."""
        env_example_path = os.path.join(self.project_root, ".env.example")
        self.assertTrue(os.path.exists(env_example_path), ".env.example must exist at repository root")

        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_vars = [
            "JWT_SECRET",
            "JWT_EXPIRY_MINUTES",
            "JWT_REFRESH_EXPIRY_DAYS",
            "ADMIN_BOOTSTRAP_PASSWORD",
            "NODE_NAME",
            "CURRENT_NODE_URL",
            "STORAGE_DIR",
        ]

        for var in required_vars:
            self.assertIn(var, content, f".env.example must define and document '{var}'")

        # Verify Section 34 reference
        self.assertIn("Section 34", content, ".env.example must explicitly reference Section 34")

    def test_jwt_secret_rotation_lifecycle(self):
        """DoD & Functional: Validates JWT_SECRET key rotation behavior across token types."""
        secret_v1 = "initial-jwt-secret-key-version-1-secure-64-byte-entropy-token"
        secret_v2 = "rotated-jwt-secret-key-version-2-secure-64-byte-entropy-token"

        # Step 1: Issue tokens under Secret V1
        with patch.dict(os.environ, {"JWT_SECRET": secret_v1}):
            access_token_v1 = create_access_token(user_id="usr_audit_01", role=Role.USER, username="auditor")
            refresh_token_v1 = create_refresh_token(user_id="usr_audit_01", role=Role.USER, username="auditor")
            system_token_v1 = create_system_token(node_id="Node A")

            # Validate they decode successfully under Secret V1
            payload_acc = decode_access_token(access_token_v1)
            self.assertEqual(payload_acc["sub"], "usr_audit_01")
            payload_ref = decode_refresh_token(refresh_token_v1)
            self.assertEqual(payload_ref["sub"], "usr_audit_01")
            payload_sys = decode_system_token(system_token_v1)
            self.assertEqual(payload_sys["sub"], "Node A")

        # Step 2: Rotate secret to Secret V2
        with patch.dict(os.environ, {"JWT_SECRET": secret_v2}):
            # Tokens signed under Secret V1 must be rejected under Secret V2
            with self.assertRaises(TokenInvalidError):
                decode_access_token(access_token_v1)

            with self.assertRaises(TokenInvalidError):
                decode_refresh_token(refresh_token_v1)

            with self.assertRaises(TokenInvalidError):
                decode_system_token(system_token_v1)

            # Step 3: Issue new tokens under Secret V2
            access_token_v2 = create_access_token(user_id="usr_audit_01", role=Role.USER, username="auditor")
            refresh_token_v2 = create_refresh_token(user_id="usr_audit_01", role=Role.USER, username="auditor")
            system_token_v2 = create_system_token(node_id="Node A")

            # Verify new tokens decode successfully under Secret V2
            payload_acc_v2 = decode_access_token(access_token_v2)
            self.assertEqual(payload_acc_v2["sub"], "usr_audit_01")
            payload_ref_v2 = decode_refresh_token(refresh_token_v2)
            self.assertEqual(payload_ref_v2["sub"], "usr_audit_01")
            payload_sys_v2 = decode_system_token(system_token_v2)
            self.assertEqual(payload_sys_v2["sub"], "Node A")

    def test_jwt_secret_rotation_readme_documentation_exists(self):
        """DoD: Rotation steps documented in README per Section 34."""
        readme_path = os.path.join(self.project_root, "README.md")
        self.assertTrue(os.path.exists(readme_path), "README.md must exist at repository root")

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for rotation documentation keywords and steps
        self.assertIn("JWT_SECRET", content)
        self.assertIn("Rotation Procedure", content)
        self.assertIn("Section 34", content)
        self.assertIn("openssl rand -hex 32", content)
        self.assertIn("validate_auth_config()", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
