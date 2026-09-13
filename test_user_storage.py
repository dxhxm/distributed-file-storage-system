"""
test_user_storage.py
====================
Automated test suite verifying the Auth Storage Schema and Repository Service:
1. Table 'users' created with exact columns (id, username, hashed_password, role, created_at, is_active).
2. Unique constraint on username enforced.
3. Backend reachability: CRUD operations (create, read by username/id, list, delete).
4. Direct SQLite DDL and column schema inspection.
5. Documentation verification: docs/schema.md exists and documents metadata/auth schemas.
"""

import os
import sqlite3
import tempfile
import unittest

from app.models import Role, User
from app.services import (
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    hash_password,
    init_db,
    list_users,
)


class TestAuthStorageSchema(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_metadata.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_table_creation_and_exact_columns(self):
        """DoD: Table created with exact columns: id, username, hashed_password, role, created_at, is_active."""
        init_db(self.db_path)

        # Inspect SQLite schema directly using PRAGMA table_info
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        conn.close()

        # columns format: (cid, name, type, notnull, dflt_value, pk)
        col_names = [col[1] for col in columns]
        expected_columns = ["id", "username", "hashed_password", "role", "created_at", "is_active"]

        self.assertEqual(col_names, expected_columns, f"Expected columns {expected_columns}, got {col_names}")

        # Check primary key on 'id'
        id_col = next(col for col in columns if col[1] == "id")
        self.assertEqual(id_col[5], 1, "Column 'id' must be the PRIMARY KEY")

        # Check NOT NULL on required columns
        for required_col in ["username", "hashed_password", "role", "created_at", "is_active"]:
            c = next(col for col in columns if col[1] == required_col)
            self.assertEqual(c[3], 1, f"Column '{required_col}' must be NOT NULL")

    def test_unique_constraint_on_username(self):
        """DoD: Unique constraint on username enforced."""
        init_db(self.db_path)

        # 1. Create first user
        u1 = User(
            username="unique_user_alice",
            hashed_password=hash_password("Password123!"),
            role=Role.USER
        )
        created = create_user(u1, db_path=self.db_path)
        self.assertIsNotNone(created["id"])
        self.assertEqual(created["username"], "unique_user_alice")

        # 2. Attempt to create second user with identical username
        u2 = User(
            username="unique_user_alice",
            hashed_password=hash_password("DifferentPassword456!"),
            role=Role.ADMIN
        )
        with self.assertRaises(ValueError) as ctx:
            create_user(u2, db_path=self.db_path)

        self.assertIn("already exists", str(ctx.exception))

        # 3. Verify direct SQL insert also fails unique constraint
        conn = sqlite3.connect(self.db_path)
        with self.assertRaises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    "INSERT INTO users (id, username, hashed_password, role, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                    ("dummy-id-999", "unique_user_alice", "hash", "USER", "2026-09-13T00:00:00", 1)
                )
        conn.close()

    def test_backend_reachability_and_crud(self):
        """DoD: Table created and reachable from backend service."""
        # 1. Insert multiple users with various roles
        user_admin = User(
            username="admin_root",
            hashed_password=hash_password("RootAdminPassword#1"),
            role=Role.ADMIN
        )
        user_system = User(
            username="system_node_b",
            hashed_password=hash_password("InterNodeSyncToken#2"),
            role=Role.SYSTEM
        )
        user_standard = User(
            username="charlie",
            hashed_password=hash_password("CharlieSecret#3"),
            role=Role.USER
        )

        rec_admin = create_user(user_admin, db_path=self.db_path)
        rec_sys = create_user(user_system, db_path=self.db_path)
        rec_std = create_user(user_standard, db_path=self.db_path)

        # 2. Retrieve by username
        fetched_admin = get_user_by_username("admin_root", db_path=self.db_path)
        self.assertIsNotNone(fetched_admin)
        self.assertEqual(fetched_admin["id"], rec_admin["id"])
        self.assertEqual(fetched_admin["role"], "ADMIN")
        self.assertTrue(fetched_admin["is_active"])

        # 3. Retrieve by ID
        fetched_sys = get_user_by_id(rec_sys["id"], db_path=self.db_path)
        self.assertIsNotNone(fetched_sys)
        self.assertEqual(fetched_sys["username"], "system_node_b")
        self.assertEqual(fetched_sys["role"], "SYSTEM")

        # 4. List all users
        all_users = list_users(db_path=self.db_path)
        self.assertEqual(len(all_users), 3)
        usernames = [u["username"] for u in all_users]
        self.assertIn("admin_root", usernames)
        self.assertIn("system_node_b", usernames)
        self.assertIn("charlie", usernames)

        # 5. Delete a user
        deleted = delete_user("charlie", db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(get_user_by_username("charlie", db_path=self.db_path))
        self.assertEqual(len(list_users(db_path=self.db_path)), 2)

        # Deleting non-existent user returns False
        self.assertFalse(delete_user("charlie", db_path=self.db_path))

    def test_schema_documentation_present(self):
        """DoD: Schema documented alongside existing metadata schema in docs/schema.md."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        schema_doc_path = os.path.join(project_root, "docs", "schema.md")

        self.assertTrue(os.path.exists(schema_doc_path), "docs/schema.md must exist")

        with open(schema_doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify Section 26 User Auth Schema documented
        self.assertIn("users", content)
        self.assertIn("id", content)
        self.assertIn("username", content)
        self.assertIn("hashed_password", content)
        self.assertIn("role", content)
        self.assertIn("created_at", content)
        self.assertIn("is_active", content)
        self.assertIn("UNIQUE", content)

        # Verify Section 19 File Metadata Schema documented
        self.assertIn("Section 19", content)
        self.assertIn("file_id", content)
        self.assertIn("replicas", content)


if __name__ == "__main__":
    print("\n=== Running DFSS Auth Storage Schema Tests ===\n")
    unittest.main(verbosity=2)
