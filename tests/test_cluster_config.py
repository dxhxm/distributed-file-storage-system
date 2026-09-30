"""
test_cluster_config.py
======================
Automated test suite verifying Admin-Only Cluster Configuration Endpoints
per Sections 11, 12, and 26:
- GET /cluster/config: View active election timeouts, heartbeat intervals, health check intervals.
- POST /cluster/config, PUT /cluster/config: Mutate cluster configuration tunables.

DoD Invariants:
1. Only ADMIN role can view and change cluster configuration.
2. Authenticated non-admin callers (USER, SYSTEM) strictly receive HTTP 403 Forbidden (never 404).
3. Unauthenticated requests strictly receive HTTP 401 Unauthorized.
4. Invalid values (negative values, zero intervals, max < min, heartbeat >= election_timeout_min) are rejected with clear error messages.
"""

import os
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-cluster-config-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token
from app.api.consensus import consensus_service


class TestClusterConfigEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        cls.admin_token = create_access_token(
            user_id="admin-cfg-mgr-01",
            role=Role.ADMIN,
            username="cluster_cfg_admin"
        )
        cls.user_token = create_access_token(
            user_id="user-cfg-reader-01",
            role=Role.USER,
            username="regular_cluster_user"
        )
        cls.system_token = create_system_token(
            node_id="Node A"
        )

        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}

    def setUp(self):
        # Reset default configuration tunables before each test
        consensus_service.election_timeout_range = (2.0, 4.0)
        consensus_service.heartbeat_interval = 0.5

    # =========================================================================
    # 1. ADMIN Happy Paths: View and Update Cluster Configuration
    # =========================================================================
    def test_admin_can_view_cluster_config(self):
        """DoD: Authenticated ADMIN can view active cluster configuration."""
        res = self.client.get("/cluster/config", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("election_timeout_min", data)
        self.assertIn("election_timeout_max", data)
        self.assertIn("heartbeat_interval", data)
        self.assertIn("health_check_interval", data)
        self.assertEqual(data["election_timeout_min"], 2.0)
        self.assertEqual(data["election_timeout_max"], 4.0)
        self.assertEqual(data["heartbeat_interval"], 0.5)

    def test_admin_can_update_cluster_config_json_post(self):
        """DoD: Authenticated ADMIN can update tunables via JSON POST."""
        payload = {
            "election_timeout_min": 3.0,
            "election_timeout_max": 6.0,
            "heartbeat_interval": 1.0,
            "health_check_interval": 8.0,
        }
        res = self.client.post("/cluster/config", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["election_timeout_min"], 3.0)
        self.assertEqual(data["election_timeout_max"], 6.0)
        self.assertEqual(data["heartbeat_interval"], 1.0)
        self.assertEqual(data["health_check_interval"], 8.0)
        self.assertIn("message", data)

        # Verify consensus service state changed
        self.assertEqual(consensus_service.election_timeout_range, (3.0, 6.0))
        self.assertEqual(consensus_service.heartbeat_interval, 1.0)

    def test_admin_can_update_cluster_config_put(self):
        """DoD: Authenticated ADMIN can update tunables via PUT method."""
        payload = {
            "election_timeout_min": 2.5,
            "election_timeout_max": 5.0,
            "heartbeat_interval": 0.8,
        }
        res = self.client.put("/cluster/config", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["election_timeout_min"], 2.5)
        self.assertEqual(data["election_timeout_max"], 5.0)
        self.assertEqual(data["heartbeat_interval"], 0.8)

    def test_admin_can_update_cluster_config_query_params(self):
        """DoD: Authenticated ADMIN can update tunables via Query Parameters."""
        res = self.client.post(
            "/cluster/config?election_timeout_min=3.5&election_timeout_max=7.0&heartbeat_interval=1.2",
            headers=self.admin_headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["election_timeout_min"], 3.5)
        self.assertEqual(data["election_timeout_max"], 7.0)
        self.assertEqual(data["heartbeat_interval"], 1.2)

    # =========================================================================
    # 2. Validation: Rejection of Invalid / Negative / Zero Values
    # =========================================================================
    def test_reject_negative_or_zero_intervals(self):
        """DoD: Negative or zero values are rejected with clear error."""
        # 1. Negative heartbeat interval via JSON
        res_neg_hb = self.client.post(
            "/cluster/config",
            json={"heartbeat_interval": -1.0},
            headers=self.admin_headers
        )
        self.assertIn(res_neg_hb.status_code, (400, 422))

        # 2. Zero election timeout via JSON
        res_zero = self.client.post(
            "/cluster/config",
            json={"election_timeout_min": 0},
            headers=self.admin_headers
        )
        self.assertIn(res_zero.status_code, (400, 422))

        # 3. Negative interval via Query Param
        res_neg_query = self.client.post(
            "/cluster/config?heartbeat_interval=-0.5",
            headers=self.admin_headers
        )
        self.assertEqual(res_neg_query.status_code, 400)
        self.assertIn("detail", res_neg_query.json())
        self.assertIn("Must be greater than 0", res_neg_query.json()["detail"])

    def test_reject_election_max_less_than_min(self):
        """DoD: Rejects election_timeout_max < election_timeout_min."""
        payload = {
            "election_timeout_min": 5.0,
            "election_timeout_max": 2.0,
        }
        res = self.client.post("/cluster/config", json=payload, headers=self.admin_headers)
        self.assertIn(res.status_code, (400, 422))
        self.assertIn("detail", res.json())

    def test_reject_heartbeat_interval_greater_than_or_equal_to_election_timeout(self):
        """DoD: Rejects heartbeat_interval >= election_timeout_min."""
        payload = {
            "election_timeout_min": 2.0,
            "election_timeout_max": 4.0,
            "heartbeat_interval": 3.0,
        }
        res = self.client.post("/cluster/config", json=payload, headers=self.admin_headers)
        self.assertIn(res.status_code, (400, 422))
        self.assertIn("detail", res.json())

    # =========================================================================
    # 3. Role-Based Access Control (RBAC): Strict ADMIN-Only (403 for USER/SYSTEM)
    # =========================================================================
    def test_non_admin_roles_forbidden_on_view_and_change_config(self):
        """
        DoD: Only ADMIN can view/change cluster configuration.
        Non-admin authenticated users (USER, SYSTEM) receive 403 Forbidden.
        """
        # 1. USER role GET /cluster/config -> 403
        res_user_get = self.client.get("/cluster/config", headers=self.user_headers)
        self.assertEqual(res_user_get.status_code, 403)
        self.assertEqual(res_user_get.json()["detail"], "Admin privileges required")
        self.assertEqual(res_user_get.headers.get("X-Error-Code"), "FORBIDDEN")

        # 2. USER role POST /cluster/config -> 403
        res_user_post = self.client.post(
            "/cluster/config",
            json={"heartbeat_interval": 0.8},
            headers=self.user_headers
        )
        self.assertEqual(res_user_post.status_code, 403)
        self.assertEqual(res_user_post.json()["detail"], "Admin privileges required")

        # 3. SYSTEM role GET /cluster/config -> 403
        res_sys_get = self.client.get("/cluster/config", headers=self.system_headers)
        self.assertEqual(res_sys_get.status_code, 403)
        self.assertEqual(res_sys_get.json()["detail"], "Admin privileges required")

        # 4. SYSTEM role POST /cluster/config -> 403
        res_sys_post = self.client.post(
            "/cluster/config",
            json={"heartbeat_interval": 0.8},
            headers=self.system_headers
        )
        self.assertEqual(res_sys_post.status_code, 403)

    def test_unauthenticated_requests_receive_401(self):
        """DoD: Unauthenticated requests to /cluster/config return 401."""
        res_get = self.client.get("/cluster/config")
        self.assertEqual(res_get.status_code, 401)
        self.assertEqual(res_get.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

        res_post = self.client.post("/cluster/config", json={"heartbeat_interval": 0.8})
        self.assertEqual(res_post.status_code, 401)
        self.assertEqual(res_post.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
