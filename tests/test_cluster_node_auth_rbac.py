"""
test_cluster_node_auth_rbac.py
==============================
Automated test suite verifying Role-Based Access Control (RBAC) on Cluster and Node endpoints:
1. Read endpoints (GET /health, /cluster/status, /nodes, /nodes/{node_id}, /nodes/status, /nodes/check):
   - Open to all authenticated roles (USER, ADMIN, SYSTEM).
   - Reject unauthenticated requests with HTTP 401 Unauthorized (NOT_AUTHENTICATED).
   - Reject expired / invalid tokens with HTTP 401 Unauthorized.
2. Mutating endpoints (POST /nodes/update, POST /fail-leader):
   - Restricted strictly to ADMIN role.
   - Reject USER and SYSTEM roles with HTTP 403 Forbidden.
   - Reject unauthenticated requests with HTTP 401 Unauthorized.
"""

import os
import unittest
from datetime import timedelta
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-cluster-node-auth-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token


class TestClusterNodeAuthRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Pre-generate tokens for each role
        cls.user_token = create_access_token(
            user_id="user-node-reader-01",
            role=Role.USER,
            username="alice_reader"
        )
        cls.admin_token = create_access_token(
            user_id="admin-node-mgr-02",
            role=Role.ADMIN,
            username="bob_cluster_admin"
        )
        cls.system_token = create_system_token(
            node_id="Node A"
        )
        cls.expired_token = create_access_token(
            user_id="user-node-reader-01",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}
        cls.expired_headers = {"Authorization": f"Bearer {cls.expired_token}"}
        cls.invalid_headers = {"Authorization": "Bearer malformed.invalid.token"}

    # =========================================================================
    # 1. Unauthenticated Rejections on Read & Mutating Endpoints (HTTP 401)
    # =========================================================================
    def test_unauthenticated_read_endpoints_rejected_with_401(self):
        """DoD: Unauthenticated calls on cluster/node read endpoints return 401."""
        endpoints = [
            "/health",
            "/cluster/status",
            "/nodes",
            "/nodes/nodeA",
            "/nodes/status",
            "/nodes/check",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 on unauthenticated GET {ep}, got {res.status_code}"
            )
            self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    def test_unauthenticated_mutating_endpoints_rejected_with_401(self):
        """DoD: Unauthenticated calls on node-mutating endpoints return 401."""
        # 1. /nodes/update
        res_update = self.client.post("/nodes/update?node_name=nodeB&status=ALIVE")
        self.assertEqual(res_update.status_code, 401)
        self.assertEqual(res_update.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

        # 2. /fail-leader
        res_fail = self.client.post("/fail-leader")
        self.assertEqual(res_fail.status_code, 401)
        self.assertEqual(res_fail.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    def test_expired_and_invalid_tokens_rejected_on_cluster_endpoints(self):
        """Expired and invalid tokens return 401 on cluster endpoints."""
        res_exp = self.client.get("/health", headers=self.expired_headers)
        self.assertEqual(res_exp.status_code, 401)
        self.assertEqual(res_exp.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

        res_inv = self.client.get("/cluster/status", headers=self.invalid_headers)
        self.assertEqual(res_inv.status_code, 401)
        self.assertEqual(res_inv.headers.get("X-Error-Code"), "INVALID_TOKEN")

    # =========================================================================
    # 2. Read Endpoints Accessible by Any Authenticated Role (USER, ADMIN, SYSTEM)
    # =========================================================================
    def test_user_role_can_read_cluster_and_nodes(self):
        """DoD: Authenticated USER can read cluster and node status."""
        # GET /health
        res_health = self.client.get("/health", headers=self.user_headers)
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        # GET /cluster/status
        res_status = self.client.get("/cluster/status", headers=self.user_headers)
        self.assertEqual(res_status.status_code, 200)
        self.assertIn("cluster_state", res_status.json())

        # GET /nodes
        res_nodes = self.client.get("/nodes", headers=self.user_headers)
        self.assertEqual(res_nodes.status_code, 200)
        self.assertIn("nodes", res_nodes.json())

    def test_admin_role_can_read_cluster_and_nodes(self):
        """DoD: Authenticated ADMIN can read cluster and node status."""
        res_health = self.client.get("/health", headers=self.admin_headers)
        self.assertEqual(res_health.status_code, 200)

        res_status = self.client.get("/cluster/status", headers=self.admin_headers)
        self.assertEqual(res_status.status_code, 200)

        res_nodes = self.client.get("/nodes", headers=self.admin_headers)
        self.assertEqual(res_nodes.status_code, 200)

    def test_system_role_can_read_cluster_and_nodes(self):
        """DoD: Authenticated SYSTEM role can read cluster and node status for RPC."""
        res_health = self.client.get("/health", headers=self.system_headers)
        self.assertEqual(res_health.status_code, 200)

        res_status = self.client.get("/cluster/status", headers=self.system_headers)
        self.assertEqual(res_status.status_code, 200)

        res_nodes = self.client.get("/nodes", headers=self.system_headers)
        self.assertEqual(res_nodes.status_code, 200)

    # =========================================================================
    # 3. Mutating Endpoints Restricted Strictly to ADMIN (HTTP 403 for USER/SYSTEM)
    # =========================================================================
    def test_admin_can_reach_mutating_node_routes(self):
        """DoD: ADMIN can execute mutating actions (POST /nodes/update, POST /fail-leader)."""
        # 1. Update node status
        res_update = self.client.post(
            "/nodes/update?node_name=nodeA&status=ALIVE",
            headers=self.admin_headers
        )
        self.assertEqual(res_update.status_code, 200)
        self.assertIn("message", res_update.json())

        # 2. Simulate fail leader
        res_fail = self.client.post("/fail-leader", headers=self.admin_headers)
        self.assertEqual(res_fail.status_code, 200)
        self.assertIn("message", res_fail.json())

    def test_user_role_forbidden_on_mutating_routes(self):
        """DoD: USER role receives HTTP 403 Forbidden on mutating routes."""
        res_update = self.client.post(
            "/nodes/update?node_name=nodeA&status=ALIVE",
            headers=self.user_headers
        )
        self.assertEqual(res_update.status_code, 403)
        self.assertEqual(res_update.json()["detail"], "Admin privileges required")
        self.assertEqual(res_update.headers.get("X-Error-Code"), "FORBIDDEN")

        res_fail = self.client.post("/fail-leader", headers=self.user_headers)
        self.assertEqual(res_fail.status_code, 403)
        self.assertEqual(res_fail.json()["detail"], "Admin privileges required")
        self.assertEqual(res_fail.headers.get("X-Error-Code"), "FORBIDDEN")

    def test_system_role_forbidden_on_mutating_routes(self):
        """DoD: SYSTEM role receives HTTP 403 Forbidden on mutating admin routes."""
        res_update = self.client.post(
            "/nodes/update?node_name=nodeA&status=ALIVE",
            headers=self.system_headers
        )
        self.assertEqual(res_update.status_code, 403)
        self.assertEqual(res_update.json()["detail"], "Admin privileges required")

        res_fail = self.client.post("/fail-leader", headers=self.system_headers)
        self.assertEqual(res_fail.status_code, 403)
        self.assertEqual(res_fail.json()["detail"], "Admin privileges required")


if __name__ == "__main__":
    unittest.main()
