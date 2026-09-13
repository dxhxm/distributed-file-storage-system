"""
test_user_model.py
==================
Automated test suite verifying the User and Role data models:
1. Role enum has exactly USER, ADMIN, and SYSTEM.
2. User model carries hashed_password only (no plaintext password field allowed).
3. Field validation, defaults, and type enforcement.
4. JSON serialization and deserialization.
5. Zero circular imports across all modules.
"""

import unittest
from datetime import datetime
from pydantic import ValidationError

from app.models import Role, User
from app.models.user_model import Role as ExplicitRole, User as ExplicitUser


class TestUserRoleDataModels(unittest.TestCase):

    def test_role_enum_exact_members(self):
        """DoD: Role enum has exactly USER, ADMIN, and SYSTEM."""
        expected_roles = {"USER", "ADMIN", "SYSTEM"}
        actual_roles = {role.value for role in Role}
        self.assertEqual(actual_roles, expected_roles, "Role enum must contain exactly USER, ADMIN, SYSTEM")
        self.assertEqual(len(Role), 3, "Role enum must have exactly 3 members")

        # Verify enum member attributes
        self.assertEqual(Role.USER.value, "USER")
        self.assertEqual(Role.ADMIN.value, "ADMIN")
        self.assertEqual(Role.SYSTEM.value, "SYSTEM")

        # Verify string comparison compatibility
        self.assertEqual(Role.USER, "USER")
        self.assertEqual(Role.ADMIN, "ADMIN")
        self.assertEqual(Role.SYSTEM, "SYSTEM")

    def test_user_model_has_hashed_password_and_no_plaintext_password(self):
        """DoD: User model never carries a plaintext password field, hashed_password only."""
        # 1. Inspect model schema / field definitions
        fields = User.model_fields
        self.assertIn("hashed_password", fields, "User model must define 'hashed_password'")
        self.assertNotIn("password", fields, "User model must NEVER define a plaintext 'password' field")
        self.assertNotIn("plaintext_password", fields, "User model must NEVER define a 'plaintext_password' field")

        # 2. Verify instantiation with hashed_password succeeds
        user = User(username="johndoe", hashed_password="argon2id$v=19$m=65536,t=3,p=4$fakehash")
        self.assertEqual(user.username, "johndoe")
        self.assertEqual(user.hashed_password, "argon2id$v=19$m=65536,t=3,p=4$fakehash")
        self.assertFalse(hasattr(user, "password"), "User instance must not have a 'password' attribute")

        # 3. Verify attempting to pass plaintext 'password' fails validation (extra='forbid')
        with self.assertRaises(ValidationError) as ctx:
            User(
                username="johndoe",
                password="plaintext_secret",  # type: ignore
                hashed_password="valid_hash"
            )
        self.assertIn("Extra inputs are not permitted", str(ctx.exception))

    def test_user_model_defaults(self):
        """Test default values for role, is_active, and created_at."""
        user = User(username="testuser", hashed_password="some_hash_123")
        self.assertEqual(user.role, Role.USER)
        self.assertTrue(user.is_active)
        self.assertIsInstance(user.created_at, datetime)

    def test_user_model_custom_roles(self):
        """Test user creation with explicit ADMIN and SYSTEM roles."""
        admin_user = User(username="admin_guy", hashed_password="admin_hash", role=Role.ADMIN)
        self.assertEqual(admin_user.role, Role.ADMIN)

        system_user = User(username="node_sync_agent", hashed_password="system_hash", role=Role.SYSTEM)
        self.assertEqual(system_user.role, Role.SYSTEM)

        # Invalid role should fail validation
        with self.assertRaises(ValidationError):
            User(username="invalid_role_guy", hashed_password="hash", role="SUPERUSER")  # type: ignore

    def test_user_model_required_fields(self):
        """Test validation error when required fields are missing."""
        # Missing hashed_password
        with self.assertRaises(ValidationError):
            User(username="missing_pwd")  # type: ignore

        # Missing username
        with self.assertRaises(ValidationError):
            User(hashed_password="some_hash")  # type: ignore

        # Empty strings for required fields
        with self.assertRaises(ValidationError):
            User(username="", hashed_password="valid_hash")

        with self.assertRaises(ValidationError):
            User(username="valid_user", hashed_password="")

    def test_serialization_and_deserialization(self):
        """Test model_dump, model_dump_json, and model_validate."""
        user = User(
            username="bob",
            hashed_password="hashed_bob_password",
            role=Role.ADMIN,
            is_active=False
        )
        data = user.model_dump()
        self.assertEqual(data["username"], "bob")
        self.assertEqual(data["hashed_password"], "hashed_bob_password")
        self.assertEqual(data["role"], "ADMIN")
        self.assertFalse(data["is_active"])
        self.assertNotIn("password", data)

        # JSON string roundtrip
        json_str = user.model_dump_json()
        self.assertIn('"username":"bob"', json_str)
        self.assertIn('"hashed_password":"hashed_bob_password"', json_str)
        self.assertNotIn('"password":', json_str)

        reloaded = User.model_validate_json(json_str)
        self.assertEqual(reloaded.username, user.username)
        self.assertEqual(reloaded.hashed_password, user.hashed_password)
        self.assertEqual(reloaded.role, Role.ADMIN)

    def test_imports_and_circular_dependency_check(self):
        """DoD: Models importable with no circular imports."""
        # Both top-level app.models and app.models.user_model export the same classes
        self.assertIs(Role, ExplicitRole)
        self.assertIs(User, ExplicitUser)

        # Verify importing across the entire application has no circular dependencies
        import importlib
        modules_to_test = [
            "app.main",
            "app.models",
            "app.models.user_model",
            "app.models.config",
            "app.api.health",
            "app.api.consensus",
            "app.api.time_sync",
            "app.api.replicate_routes",
            "app.services.health_service",
            "app.services.replication_service",
            "app.services.time_sync",
        ]
        for mod in modules_to_test:
            m = importlib.import_module(mod)
            self.assertIsNotNone(m, f"Module {mod} should import cleanly")


if __name__ == "__main__":
    print("\n=== Running DFSS User & Role Data Model Tests ===\n")
    unittest.main(verbosity=2)
