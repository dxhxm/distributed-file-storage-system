"""
test_replication_config.py
==========================
Automated test suite verifying Admin-Only Replication Configuration Endpoints
per Section 13 (Replication) and Section 26 (Admin Operations & Privileged Endpoints):
- GET /replication/config: View active replication settings and cluster size constraints.
- POST /replication/config, PUT /replication/config: Adjust replication factor and settings.

DoD Invariants:
1. Only ADMIN can reach this route.
2. Changing replication factor is validated against cluster size before being accepted.
3. Authenticated non-admin callers (USER, SYSTEM) strictly receive HTTP 403 Forbidden (never 404).
4. Unauthenticated requests strictly receive HTTP 401 Unauthorized.
5. Invalid values (negative factor, factor > cluster_size, zero/negative timeout) are rejected with clear errors.
"""

import os
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-replication-config-tests-2026-64-bytes")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token
from app.services import replication_service, log_service, health_service


class TestReplicationConfigEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        cls.admin_token = create_access_token(
            user_id="admin-repl-mgr-01",
            role=Role.ADMIN,
            username="rachel_repl_admin"
        )
        cls.user_token = create_access_token(
            user_id="user-non-admin-02",
            role=Role.USER,
            username="mark_regular_user"
        )
        cls.system_token = create_system_token(
            node_id="Node A"
        )

        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}

    def setUp(self):
        # Reset default replication settings before each test
        replication_service.REPLICATION_FACTOR = 3
        replication_service.AUTO_REBALANCE = True
        replication_service.REPLICATION_TIMEOUT = 5.0
        health_service.nodes_status["nodeA"] = "ALIVE"
        health_service.nodes_status["nodeB"] = "ALIVE"
        health_service.nodes_status["nodeC"] = "ALIVE"

    # =========================================================================
    # 1. ADMIN Happy Paths: View and Update Replication Settings
    # =========================================================================
    def test_admin_can_view_replication_config(self):
        """DoD: Authenticated ADMIN can view active replication configuration."""
        res = self.client.get("/replication/config", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("replication_factor", data)
        self.assertIn("cluster_size", data)
        self.assertIn("max_possible_replication_factor", data)
        self.assertIn("auto_rebalance", data)
        self.assertIn("replication_timeout", data)
        self.assertEqual(data["replication_factor"], 3)
        self.assertGreaterEqual(data["cluster_size"], 3)
        self.assertEqual(data["max_possible_replication_factor"], data["cluster_size"])

    def test_admin_can_update_replication_factor_json_post(self):
        """DoD: Authenticated ADMIN can adjust replication factor within cluster size bounds."""
        payload = {
            "replication_factor": 2,
            "auto_rebalance": False,
            "replication_timeout": 8.0,
        }
        res = self.client.post("/replication/config", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["replication_factor"], 2)
        self.assertEqual(data["auto_rebalance"], False)
        self.assertEqual(data["replication_timeout"], 8.0)
        self.assertIn("message", data)

        # Verify service state updated
        self.assertEqual(replication_service.REPLICATION_FACTOR, 2)
        self.assertEqual(replication_service.AUTO_REBALANCE, False)
        self.assertEqual(replication_service.REPLICATION_TIMEOUT, 8.0)

    def test_admin_can_update_replication_config_put(self):
        """DoD: Authenticated ADMIN can update replication settings via PUT method."""
        payload = {
            "replication_factor": 3,
            "auto_rebalance": True,
        }
        res = self.client.put("/replication/config", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["replication_factor"], 3)
        self.assertEqual(data["auto_rebalance"], True)

    def test_admin_can_update_replication_config_query_params(self):
        """DoD: Authenticated ADMIN can update replication settings via Query Params."""
        res = self.client.post(
            "/replication/config?replication_factor=2&replication_timeout=6.5",
            headers=self.admin_headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["replication_factor"], 2)
        self.assertEqual(data["replication_timeout"], 6.5)

    # =========================================================================
    # 2. Validation Against Cluster Size (DoD Invariant)
    # =========================================================================
    def test_reject_replication_factor_exceeding_cluster_size(self):
        """
        DoD Invariant: Changing replication factor is validated against cluster size.
        Rejects replication_factor > cluster_size.
        """
        cluster_size = replication_service.get_cluster_size()
        exceeding_factor = cluster_size + 1

        payload = {"replication_factor": exceeding_factor}
        res = self.client.post("/replication/config", json=payload, headers=self.admin_headers)

        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.json())
        self.assertIn("cannot exceed current cluster size", res.json()["detail"])
        self.assertIn(str(cluster_size), res.json()["detail"])

    def test_reject_replication_factor_less_than_one(self):
        """DoD: Rejects replication factor < 1 (zero or negative)."""
        # Zero factor
        res_zero = self.client.post(
            "/replication/config",
            json={"replication_factor": 0},
            headers=self.admin_headers
        )
        self.assertIn(res_zero.status_code, (400, 422))

        # Negative factor via query param
        res_neg = self.client.post(
            "/replication/config?replication_factor=-2",
            headers=self.admin_headers
        )
        self.assertIn(res_neg.status_code, (400, 422))

    def test_reject_invalid_replication_timeout(self):
        """DoD: Rejects negative or zero replication timeout."""
        res = self.client.post(
            "/replication/config",
            json={"replication_timeout": -1.0},
            headers=self.admin_headers
        )
        self.assertIn(res.status_code, (400, 422))

    # =========================================================================
    # 3. RBAC Enforcement: Strict ADMIN-Only (403 for USER/SYSTEM, never 404)
    # =========================================================================
    def test_non_admin_roles_forbidden_on_replication_config(self):
        """
        DoD: Only ADMIN can reach this route.
        Non-admin authenticated callers (USER, SYSTEM) get 403 Forbidden.
        """
        # 1. USER role GET -> 403
        res_user_get = self.client.get("/replication/config", headers=self.user_headers)
        self.assertEqual(res_user_get.status_code, 403)
        self.assertEqual(res_user_get.json()["detail"], "Admin privileges required")
        self.assertEqual(res_user_get.headers.get("X-Error-Code"), "FORBIDDEN")

        # 2. USER role POST -> 403
        res_user_post = self.client.post(
            "/replication/config",
            json={"replication_factor": 2},
            headers=self.user_headers
        )
        self.assertEqual(res_user_post.status_code, 403)
        self.assertEqual(res_user_post.json()["detail"], "Admin privileges required")

        # 3. SYSTEM role GET -> 403
        res_sys_get = self.client.get("/replication/config", headers=self.system_headers)
        self.assertEqual(res_sys_get.status_code, 403)
        self.assertEqual(res_sys_get.json()["detail"], "Admin privileges required")

        # 4. SYSTEM role POST -> 403
        res_sys_post = self.client.post(
            "/replication/config",
            json={"replication_factor": 2},
            headers=self.system_headers
        )
        self.assertEqual(res_sys_post.status_code, 403)

    def test_unauthenticated_requests_receive_401(self):
        """DoD: Unauthenticated requests to /replication/config return 401."""
        res_get = self.client.get("/replication/config")
        self.assertEqual(res_get.status_code, 401)
        self.assertEqual(res_get.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

        res_post = self.client.post("/replication/config", json={"replication_factor": 2})
        self.assertEqual(res_post.status_code, 401)
        self.assertEqual(res_post.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
