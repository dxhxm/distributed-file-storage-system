"""
test_admin_logs_health.py
=========================
Automated test suite verifying Admin-Only System Logs & Detailed Health Access
per Section 26:
- GET /logs, GET /admin/logs: Retrieve structured system logs.
- GET /health/detailed, GET /admin/health: In-depth operational telemetry.

DoD Invariants:
1. Only ADMIN can retrieve system logs and detailed health.
2. Log access is itself logged (who viewed what, when) in the audit trail.
3. Authenticated non-admin callers (USER, SYSTEM) strictly receive HTTP 403 Forbidden (never 404).
4. Unauthenticated requests strictly receive HTTP 401 Unauthorized.
5. Log filtering (level, component, search keyword, limit) works accurately.
"""

import os
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-admin-logs-health-tests-2026-64-bytes")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.main import app
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token
from app.services import log_service


class TestAdminLogsAndHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        cls.admin_token = create_access_token(
            user_id="admin-log-viewer-01",
            role=Role.ADMIN,
            username="diana_super_admin"
        )
        cls.user_token = create_access_token(
            user_id="user-non-admin-01",
            role=Role.USER,
            username="frank_regular_user"
        )
        cls.system_token = create_system_token(
            node_id="Node A"
        )

        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}

    def setUp(self):
        log_service.clear_logs()
        # Seed several logs across components
        log_service.add_log_entry("INFO", "raft", "Raft node transitioned to FOLLOWER")
        log_service.add_log_entry("WARNING", "health", "Node B heartbeat missed 1 interval")
        log_service.add_log_entry("ERROR", "storage", "Disk block allocation retry succeeded")
        log_service.add_log_entry("DEBUG", "time_sync", "Calculated clock skew: 0.002ms")

    # =========================================================================
    # 1. ADMIN System Logs Retrieval & Audit Logging Invariant
    # =========================================================================
    def test_admin_can_retrieve_logs_and_access_is_audited(self):
        """
        DoD: Only ADMIN can retrieve system logs.
        Log access is itself logged (who viewed what, when).
        """
        # 1. Admin retrieves logs
        res = self.client.get("/logs?limit=50", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("logs", data)
        self.assertGreaterEqual(data["total_retrieved"], 4)

        # 2. Verify that log access itself created an AUDIT record
        res_audit_check = self.client.get("/logs?level=AUDIT", headers=self.admin_headers)
        self.assertEqual(res_audit_check.status_code, 200)
        audit_data = res_audit_check.json()

        audit_logs = [log for log in audit_data["logs"] if log["level"] == "AUDIT"]
        self.assertTrue(len(audit_logs) >= 1, "Expected at least one AUDIT log recording admin log access")

        first_audit = audit_logs[0]
        self.assertEqual(first_audit["component"], "audit")
        self.assertIn("diana_super_admin", first_audit["message"])
        self.assertIn("VIEW_SYSTEM_LOGS", first_audit["message"])
        self.assertIn("/logs", first_audit["message"])
        self.assertIn("timestamp_iso", first_audit)

        # Verify metadata details
        meta = first_audit["metadata"]
        self.assertEqual(meta.get("actor_id"), "admin-log-viewer-01")
        self.assertEqual(meta.get("actor_username"), "diana_super_admin")
        self.assertEqual(meta.get("action"), "VIEW_SYSTEM_LOGS")

    def test_admin_log_filtering_by_level_component_and_search(self):
        """Admin can filter system logs by level, component, and keyword search."""
        # 1. Filter by Level
        res_err = self.client.get("/logs?level=ERROR", headers=self.admin_headers)
        self.assertEqual(res_err.status_code, 200)
        logs_err = res_err.json()["logs"]
        for item in logs_err:
            self.assertEqual(item["level"], "ERROR")

        # 2. Filter by Component
        res_raft = self.client.get("/logs?component=raft", headers=self.admin_headers)
        self.assertEqual(res_raft.status_code, 200)
        logs_raft = res_raft.json()["logs"]
        for item in logs_raft:
            self.assertEqual(item["component"], "raft")

        # 3. Filter by Search Query
        res_search = self.client.get("/logs?search=disk", headers=self.admin_headers)
        self.assertEqual(res_search.status_code, 200)
        logs_search = res_search.json()["logs"]
        self.assertTrue(any("disk" in item["message"].lower() for item in logs_search))

    # =========================================================================
    # 2. ADMIN Detailed Health & Telemetry Retrieval
    # =========================================================================
    def test_admin_can_retrieve_detailed_health(self):
        """DoD: Authenticated ADMIN can view in-depth operational health diagnostics."""
        res = self.client.get("/health/detailed", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("status", data)
        self.assertIn("uptime_seconds", data)
        self.assertIn("cluster", data)
        self.assertIn("consensus", data)
        self.assertIn("nodes", data)
        self.assertIn("storage", data)
        self.assertIn("time_sync", data)
        self.assertIn("system_runtime", data)

        # Verify consensus section
        self.assertIn("state", data["consensus"])
        self.assertIn("term", data["consensus"])

        # Verify system runtime
        self.assertIn("python_version", data["system_runtime"])
        self.assertIn("pid", data["system_runtime"])

    # =========================================================================
    # 3. RBAC Enforcement: Strict ADMIN-Only (403 for USER/SYSTEM, never 404)
    # =========================================================================
    def test_non_admin_users_receive_403_on_logs_and_health_detailed(self):
        """
        DoD: Only ADMIN can reach logs and detailed health.
        Non-admin authenticated callers (USER, SYSTEM) get 403 Forbidden.
        """
        endpoints = ["/logs", "/admin/logs", "/health/detailed", "/admin/health"]

        for ep in endpoints:
            # 1. USER role -> 403
            res_user = self.client.get(ep, headers=self.user_headers)
            self.assertEqual(
                res_user.status_code, 403,
                f"Expected 403 for USER on {ep}, got {res_user.status_code}"
            )
            self.assertEqual(res_user.json()["detail"], "Admin privileges required")
            self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN")

            # 2. SYSTEM role -> 403
            res_sys = self.client.get(ep, headers=self.system_headers)
            self.assertEqual(
                res_sys.status_code, 403,
                f"Expected 403 for SYSTEM on {ep}, got {res_sys.status_code}"
            )
            self.assertEqual(res_sys.json()["detail"], "Admin privileges required")

    def test_unauthenticated_requests_receive_401(self):
        """DoD: Unauthenticated requests to /logs and /health/detailed return 401."""
        endpoints = ["/logs", "/admin/logs", "/health/detailed", "/admin/health"]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(
                res.status_code, 401,
                f"Expected 401 for unauthenticated GET {ep}, got {res.status_code}"
            )
            self.assertEqual(res.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")


if __name__ == "__main__":
    unittest.main()
