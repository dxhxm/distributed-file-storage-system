"""
test_admin_node_management.py
=============================
Automated test suite verifying Admin Node Management Endpoints per Section 26:
- Cordon node (POST /nodes/cordon, POST /nodes/{node_id}/cordon)
- Uncordon node (POST /nodes/uncordon, POST /nodes/{node_id}/uncordon)
- Remove node (POST /nodes/remove, POST /nodes/{node_id}/remove, DELETE /nodes/{node_id})
- Add node (POST /nodes/add)
- Update node (POST /nodes/update)

DoD Invariants:
1. Only ADMIN role can reach and execute these routes.
2. Authenticated non-admin callers (USER, SYSTEM) strictly get HTTP 403 Forbidden.
3. Non-admin requests NEVER receive HTTP 404 on admin endpoints (preventing route or resource enumeration leakage).
4. Unauthenticated requests strictly receive HTTP 401 Unauthorized.
5. Missing node requests by authenticated ADMIN receive HTTP 404 Not Found.
"""

import os
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-admin-node-management-tests-2026-64-bytes-secure")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token
from app.services import health_service


class TestAdminNodeManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        cls.admin_token = create_access_token(
            user_id="admin-node-mgr-001",
            role=Role.ADMIN,
            username="super_cluster_admin"
        )
        cls.user_token = create_access_token(
            user_id="user-node-reader-001",
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
        # Reset health_service state before each test
        health_service.nodes_status["nodeA"] = "ALIVE"
        health_service.nodes_status["nodeB"] = "ALIVE"
        health_service.nodes_status["nodeC"] = "ALIVE"
        health_service.NODE_URLS["nodeA"] = "http://127.0.0.1:8000"
        health_service.NODE_URLS["nodeB"] = "http://127.0.0.1:8001"
        health_service.NODE_URLS["nodeC"] = "http://127.0.0.1:8002"
        health_service.NODE_DISPLAY_NAMES["nodeA"] = "Node A"
        health_service.NODE_DISPLAY_NAMES["nodeB"] = "Node B"
        health_service.NODE_DISPLAY_NAMES["nodeC"] = "Node C"

    # =========================================================================
    # 1. Non-Admin Authenticated Users Receive 403 (No 404 Route Leakage)
    # =========================================================================
    def test_non_admin_gets_403_not_404_on_node_management_routes(self):
        """
        DoD: Only ADMIN can reach these routes.
        A non-admin authenticated user gets 403, NOT a 404 that leaks route existence.
        Tested against both existing and non-existing node endpoints.
        """
        endpoints_to_test = [
            ("POST", "/nodes/cordon?node_name=nodeB"),
            ("POST", "/nodes/nodeB/cordon"),
            ("POST", "/nodes/non_existent_node_xyz/cordon"),
            ("POST", "/nodes/uncordon?node_name=nodeB"),
            ("POST", "/nodes/nodeB/uncordon"),
            ("POST", "/nodes/non_existent_node_xyz/uncordon"),
            ("POST", "/nodes/remove?node_name=nodeB"),
            ("POST", "/nodes/nodeB/remove"),
            ("DELETE", "/nodes/nodeB"),
            ("DELETE", "/nodes/non_existent_node_xyz"),
            ("POST", "/nodes/add?node_name=nodeD&url=http://127.0.0.1:8003"),
            ("POST", "/nodes/update?node_name=nodeB&status=DEAD"),
        ]

        for method, path in endpoints_to_test:
            # 1. USER role gets 403 Forbidden (Never 404)
            if method == "POST":
                res_user = self.client.post(path, headers=self.user_headers)
            elif method == "DELETE":
                res_user = self.client.delete(path, headers=self.user_headers)
            else:
                self.fail(f"Unsupported method: {method}")

            self.assertEqual(
                res_user.status_code, 403,
                f"Expected 403 Forbidden for USER on {method} {path}, got {res_user.status_code} with body {res_user.text}"
            )
            self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN")
            self.assertEqual(res_user.json()["detail"], "Admin privileges required")

            # 2. SYSTEM role gets 403 Forbidden (Never 404)
            if method == "POST":
                res_sys = self.client.post(path, headers=self.system_headers)
            elif method == "DELETE":
                res_sys = self.client.delete(path, headers=self.system_headers)
            else:
                self.fail(f"Unsupported method: {method}")

            self.assertEqual(
                res_sys.status_code, 403,
                f"Expected 403 Forbidden for SYSTEM on {method} {path}, got {res_sys.status_code}"
            )

    def test_unauthenticated_requests_get_401(self):
        """DoD: Unauthenticated requests to node management routes return 401."""
        endpoints = [
            ("POST", "/nodes/cordon?node_name=nodeB"),
            ("POST", "/nodes/nodeB/cordon"),
            ("POST", "/nodes/uncordon?node_name=nodeB"),
            ("POST", "/nodes/remove?node_name=nodeB"),
            ("DELETE", "/nodes/nodeB"),
            ("POST", "/nodes/add?node_name=nodeD&url=http://127.0.0.1:8003"),
            ("POST", "/nodes/update?node_name=nodeB&status=DEAD"),
        ]
        for method, path in endpoints:
            if method == "POST":
                res = self.client.post(path)
            elif method == "DELETE":
                res = self.client.delete(path)
            else:
                self.fail(f"Unsupported method: {method}")

            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"
            )
            self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

    # =========================================================================
    # 2. Authenticated ADMIN Cordon & Uncordon Lifecycle
    # =========================================================================
    def test_admin_cordon_and_uncordon_lifecycle(self):
        """DoD: Authenticated ADMIN can cordon and uncordon cluster nodes."""
        # 1. Cordon via query parameter
        res_cordon = self.client.post("/nodes/cordon?node_name=nodeB", headers=self.admin_headers)
        self.assertEqual(res_cordon.status_code, 200)
        self.assertEqual(res_cordon.json()["status"], "CORDONED")
        self.assertEqual(health_service.nodes_status["nodeB"], "CORDONED")

        # Verify get_nodes reflects CORDONED
        res_nodes = self.client.get("/nodes", headers=self.admin_headers)
        self.assertEqual(res_nodes.status_code, 200)
        nodes_list = res_nodes.json()["nodes"]
        node_b_info = next((n for n in nodes_list if n["id"] in ("nodeB", "Node B")), None)
        self.assertIsNotNone(node_b_info)
        self.assertEqual(node_b_info["status"], "CORDONED")

        # 2. Uncordon via path parameter
        res_uncordon = self.client.post("/nodes/nodeB/uncordon", headers=self.admin_headers)
        self.assertEqual(res_uncordon.status_code, 200)
        self.assertEqual(res_uncordon.json()["status"], "ALIVE")
        self.assertEqual(health_service.nodes_status["nodeB"], "ALIVE")

        # 3. Cordon via JSON payload
        res_cordon_json = self.client.post(
            "/nodes/cordon",
            json={"node_name": "nodeC"},
            headers=self.admin_headers
        )
        self.assertEqual(res_cordon_json.status_code, 200)
        self.assertEqual(health_service.nodes_status["nodeC"], "CORDONED")

        # 4. Uncordon via JSON payload
        res_uncordon_json = self.client.post(
            "/nodes/uncordon",
            json={"node_name": "nodeC"},
            headers=self.admin_headers
        )
        self.assertEqual(res_uncordon_json.status_code, 200)
        self.assertEqual(health_service.nodes_status["nodeC"], "ALIVE")

    # =========================================================================
    # 3. Authenticated ADMIN Remove and Add Lifecycle
    # =========================================================================
    def test_admin_remove_and_add_node_lifecycle(self):
        """DoD: Authenticated ADMIN can remove and add nodes."""
        # 1. Remove nodeB via POST /nodes/remove
        res_rem = self.client.post("/nodes/remove?node_name=nodeB", headers=self.admin_headers)
        self.assertEqual(res_rem.status_code, 200)
        self.assertEqual(res_rem.json()["status"], "REMOVED")
        self.assertNotIn("nodeB", health_service.nodes_status)

        # 2. Remove nodeC via DELETE /nodes/{node_id}
        res_del = self.client.delete("/nodes/nodeC", headers=self.admin_headers)
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(res_del.json()["status"], "REMOVED")
        self.assertNotIn("nodeC", health_service.nodes_status)

        # 3. Add nodeD via POST /nodes/add
        res_add = self.client.post(
            "/nodes/add",
            json={"node_name": "nodeD", "url": "http://127.0.0.1:8003", "display_name": "Node D"},
            headers=self.admin_headers
        )
        self.assertEqual(res_add.status_code, 200)
        self.assertIn("nodeD", health_service.nodes_status)
        self.assertEqual(health_service.nodes_status["nodeD"], "ALIVE")

    # =========================================================================
    # 4. ADMIN Handling of Missing Nodes (Returns 404)
    # =========================================================================
    def test_admin_non_existent_node_returns_404(self):
        """DoD: Authenticated ADMIN receives 404 on operations against non-existent nodes."""
        res_cordon = self.client.post("/nodes/unknown_node/cordon", headers=self.admin_headers)
        self.assertEqual(res_cordon.status_code, 404)

        res_uncordon = self.client.post("/nodes/unknown_node/uncordon", headers=self.admin_headers)
        self.assertEqual(res_uncordon.status_code, 404)

        res_remove = self.client.delete("/nodes/unknown_node", headers=self.admin_headers)
        self.assertEqual(res_remove.status_code, 404)


if __name__ == "__main__":
    unittest.main()
