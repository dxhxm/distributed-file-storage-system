"""
test_system_auth.py
===================
Automated test suite for SYSTEM-Role Inter-Node Authentication per Section 26.
Validates:
1. Inter-node RPC routes (/raft/request-vote, /raft/append-entries, /replicate, /sync-time) succeed when called with a valid SYSTEM credential.
2. Unauthenticated calls to internal node routes return HTTP 401 Unauthorized.
3. Standard USER JWTs are rejected on internal node routes with HTTP 403 Forbidden.
4. ADMIN JWTs are rejected on internal node routes with HTTP 403 Forbidden.
5. SYSTEM tokens are rejected on human user routes (/auth/users, /auth/me) with HTTP 403 Forbidden.
6. Helper functions create_system_token, decode_system_token, and get_system_auth_headers operate reliably.
"""

import io
import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient

os.environ["JWT_SECRET"] = "super-secret-key-for-system-auth-test-32bytes"
os.environ["JWT_EXPIRY_MINUTES"] = "60"

from app.main import app
from app.models.user_model import Role, User
from app.services.auth_service import hash_password
from app.services.jwt_service import (
    TokenInvalidError,
    create_access_token,
    create_system_token,
    decode_system_token,
    get_system_auth_headers,
)
from app.services.user_storage import (
    create_user,
    delete_user,
    init_db,
)


class TestSystemRoleInterNodeAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        # 1. Seed user token (USER role)
        delete_user("regular_user_test")
        cls.user_record = create_user(
            User(
                username="regular_user_test",
                hashed_password=hash_password("Pass123!"),
                role=Role.USER,
                is_active=True,
            )
        )
        cls.user_token = create_access_token(
            user_id=cls.user_record["id"],
            role=Role.USER,
            username="regular_user_test",
        )

        # 2. Seed admin token (ADMIN role)
        delete_user("admin_user_test")
        cls.admin_record = create_user(
            User(
                username="admin_user_test",
                hashed_password=hash_password("AdminPass123!"),
                role=Role.ADMIN,
                is_active=True,
            )
        )
        cls.admin_token = create_access_token(
            user_id=cls.admin_record["id"],
            role=Role.ADMIN,
            username="admin_user_test",
        )

        # 3. Generate SYSTEM token (SYSTEM role)
        cls.system_token = create_system_token(node_id="Node A")
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}
        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}

    @classmethod
    def tearDownClass(cls):
        delete_user("regular_user_test")
        delete_user("admin_user_test")

    # -------------------------------------------------------------------------
    # 1. Internal RPC calls with valid SYSTEM token succeed
    # -------------------------------------------------------------------------
    def test_raft_request_vote_succeeds_with_system_token(self):
        """Validates that POST /raft/request-vote accepts valid SYSTEM credential."""
        payload = {
            "term": 1,
            "candidate_id": "Node B",
            "last_log_index": 0,
            "last_log_term": 0,
        }
        res = self.client.post("/raft/request-vote", json=payload, headers=self.system_headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("term", res.json())
        self.assertIn("vote_granted", res.json())

    def test_raft_append_entries_succeeds_with_system_token(self):
        """Validates that POST /raft/append-entries accepts valid SYSTEM credential."""
        payload = {
            "term": 1,
            "leader_id": "Node B",
            "prev_log_index": -1,
            "prev_log_term": 0,
            "entries": [],
            "leader_commit": 0,
        }
        res = self.client.post("/raft/append-entries", json=payload, headers=self.system_headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("success", res.json())

    def test_replicate_succeeds_with_system_token(self):
        """Validates that POST /replicate accepts valid SYSTEM credential."""
        file_content = b"Replication test data for SYSTEM role auth"
        files = {"file": ("test_replica_file.txt", io.BytesIO(file_content), "text/plain")}

        res = self.client.post("/replicate", files=files, headers=self.system_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["filename"], "test_replica_file.txt")

    def test_sync_time_succeeds_with_system_token(self):
        """Validates that POST /sync-time accepts valid SYSTEM credential."""
        res = self.client.post("/sync-time?target_time=1700000000.0", headers=self.system_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

    # -------------------------------------------------------------------------
    # 2. Unauthenticated calls to internal routes rejected (401)
    # -------------------------------------------------------------------------
    def test_internal_routes_unauthenticated_rejected(self):
        """DoD: Inter-node calls without authentication are rejected with HTTP 401."""
        # 1. /raft/request-vote
        r1 = self.client.post("/raft/request-vote", json={"term": 1})
        self.assertEqual(r1.status_code, 401)
        self.assertEqual(r1.json()["detail"], "NOT_AUTHENTICATED")

        # 2. /raft/append-entries
        r2 = self.client.post("/raft/append-entries", json={"term": 1})
        self.assertEqual(r2.status_code, 401)
        self.assertEqual(r2.json()["detail"], "NOT_AUTHENTICATED")

        # 3. /replicate
        files = {"file": ("test.txt", io.BytesIO(b"data"), "text/plain")}
        r3 = self.client.post("/replicate", files=files)
        self.assertEqual(r3.status_code, 401)
        self.assertEqual(r3.json()["detail"], "NOT_AUTHENTICATED")

        # 4. /sync-time
        r4 = self.client.post("/sync-time?target_time=100.0")
        self.assertEqual(r4.status_code, 401)
        self.assertEqual(r4.json()["detail"], "NOT_AUTHENTICATED")

    # -------------------------------------------------------------------------
    # 3. USER tokens rejected on internal node routes (403)
    # -------------------------------------------------------------------------
    def test_user_jwt_rejected_on_internal_node_routes(self):
        """DoD: A user JWT is rejected on internal-only node routes with HTTP 403."""
        # 1. /raft/request-vote
        r1 = self.client.post(
            "/raft/request-vote",
            json={"term": 1, "candidate_id": "Node B"},
            headers=self.user_headers,
        )
        self.assertEqual(r1.status_code, 403)
        self.assertIn("System credential required", r1.json()["detail"])

        # 2. /raft/append-entries
        r2 = self.client.post(
            "/raft/append-entries",
            json={"term": 1, "leader_id": "Node B"},
            headers=self.user_headers,
        )
        self.assertEqual(r2.status_code, 403)
        self.assertIn("System credential required", r2.json()["detail"])

        # 3. /replicate
        files = {"file": ("test_user.txt", io.BytesIO(b"user_data"), "text/plain")}
        r3 = self.client.post("/replicate", files=files, headers=self.user_headers)
        self.assertEqual(r3.status_code, 403)
        self.assertIn("System credential required", r3.json()["detail"])

        # 4. /sync-time
        r4 = self.client.post("/sync-time?target_time=100.0", headers=self.user_headers)
        self.assertEqual(r4.status_code, 403)
        self.assertIn("System credential required", r4.json()["detail"])

    # -------------------------------------------------------------------------
    # 4. ADMIN tokens rejected on internal node routes (403)
    # -------------------------------------------------------------------------
    def test_admin_jwt_rejected_on_internal_node_routes(self):
        """DoD: An admin JWT is also rejected on internal-only node routes (distinct from SYSTEM)."""
        r_vote = self.client.post(
            "/raft/request-vote",
            json={"term": 1, "candidate_id": "Node B"},
            headers=self.admin_headers,
        )
        self.assertEqual(r_vote.status_code, 403)

        r_replicate = self.client.post(
            "/replicate",
            files={"file": ("test_admin.txt", io.BytesIO(b"admin_data"), "text/plain")},
            headers=self.admin_headers,
        )
        self.assertEqual(r_replicate.status_code, 403)

    # -------------------------------------------------------------------------
    # 5. SYSTEM token rejected on human user routes (403)
    # -------------------------------------------------------------------------
    def test_system_token_rejected_on_user_routes(self):
        """DoD: SYSTEM credentials cannot impersonate human users on user-facing routes."""
        # 1. /auth/me profile endpoint
        r_me = self.client.get("/auth/me", headers=self.system_headers)
        self.assertEqual(r_me.status_code, 403)
        self.assertIn("SYSTEM credentials not permitted on user routes", r_me.json()["detail"])

        # 2. /auth/users admin provisioning endpoint
        r_users = self.client.post(
            "/auth/users",
            json={"username": "impersonated_user", "password": "Pass123Password!"},
            headers=self.system_headers,
        )
        self.assertEqual(r_users.status_code, 403)

    # -------------------------------------------------------------------------
    # 6. Helper functions unit tests
    # -------------------------------------------------------------------------
    def test_create_and_decode_system_token(self):
        """Validates create_system_token and decode_system_token helpers."""
        token = create_system_token(node_id="Node C", expires_delta=timedelta(hours=2))
        payload = decode_system_token(token)

        self.assertEqual(payload["sub"], "Node C")
        self.assertEqual(payload["role"], "SYSTEM")
        self.assertEqual(payload["token_type"], "system")

    def test_decode_system_token_rejects_non_system_role(self):
        """Validates that decode_system_token rejects tokens without SYSTEM role."""
        user_jwt = create_access_token(user_id="user-123", role=Role.USER)
        with self.assertRaises(TokenInvalidError):
            decode_system_token(user_jwt)

    def test_get_system_auth_headers_utility(self):
        """Validates get_system_auth_headers helper produces valid Bearer header."""
        headers = get_system_auth_headers(node_id="Node A")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

        raw_token = headers["Authorization"].split(" ")[1]
        claims = decode_system_token(raw_token)
        self.assertEqual(claims["sub"], "Node A")
        self.assertEqual(claims["role"], "SYSTEM")


if __name__ == "__main__":
    unittest.main()
