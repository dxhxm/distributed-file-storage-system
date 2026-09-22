"""
test_rbac_dependency.py
========================
Automated test suite verifying the Role-Based Access Control (RBAC) Dependency (`require_role`):
1. Dependency composes cleanly with JWT validation (get_current_user).
2. USER role gating: Allowed for USER; returns 403 for insufficient roles; 401 for unauthenticated.
3. ADMIN role gating: Allowed for ADMIN; returns 403 for insufficient roles; 401 for unauthenticated.
4. SYSTEM role gating: Allowed for SYSTEM; returns 403 for insufficient roles; 401 for unauthenticated.
5. Multi-role gating: Allowed for specified subsets of roles; 403 for others.
6. Error code distinction: Insufficient role returns 403 (not 401). Unauthenticated returns 401.
7. Parameter validation: Calling require_role with no arguments raises ValueError.
8. Case-insensitivity and string/enum normalization.
"""

import asyncio
import os
import unittest
from datetime import timedelta
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-rbac-dependency-unit-tests-2026-64-byte-secure-key")
os.environ.setdefault("JWT_EXPIRY_MINUTES", "60")

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_admin,
    require_role,
    require_system,
    require_user,
)
from app.models.user_model import Role
from app.services.jwt_service import create_access_token, create_system_token


class TestRBACDependency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Create a dedicated FastAPI app with test routes for each role
        cls.test_app = FastAPI()
        test_router = APIRouter()

        @test_router.get("/test/user-only")
        async def user_only_route(user: AuthenticatedUser = Depends(require_role(Role.USER))):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/admin-only")
        async def admin_only_route(user: AuthenticatedUser = Depends(require_role(Role.ADMIN))):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/system-only")
        async def system_only_route(user: AuthenticatedUser = Depends(require_role(Role.SYSTEM))):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/user-or-admin")
        async def user_or_admin_route(user: AuthenticatedUser = Depends(require_role(Role.USER, Role.ADMIN))):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/admin-or-system")
        async def admin_or_system_route(user: AuthenticatedUser = Depends(require_role("admin", "SYSTEM"))):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/shortcut-user")
        async def shortcut_user_route(user: AuthenticatedUser = Depends(require_user)):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/shortcut-admin")
        async def shortcut_admin_route(user: AuthenticatedUser = Depends(require_admin)):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        @test_router.get("/test/shortcut-system")
        async def shortcut_system_route(user: AuthenticatedUser = Depends(require_system)):
            return {"status": "ok", "role": user.role, "user_id": user.user_id}

        cls.test_app.include_router(test_router)
        cls.client = TestClient(cls.test_app)

        # 2. Pre-generate test tokens for USER, ADMIN, and SYSTEM
        cls.user_token = create_access_token(
            user_id="user-uid-001",
            role=Role.USER,
            username="regular_alice"
        )
        cls.admin_token = create_access_token(
            user_id="admin-uid-002",
            role=Role.ADMIN,
            username="admin_bob"
        )
        cls.system_token = create_system_token(
            node_id="Node A"
        )
        cls.expired_user_token = create_access_token(
            user_id="user-uid-001",
            role=Role.USER,
            expires_delta=timedelta(seconds=-10)
        )

        cls.user_headers = {"Authorization": f"Bearer {cls.user_token}"}
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.system_headers = {"Authorization": f"Bearer {cls.system_token}"}

    # =========================================================================
    # 1. USER Role Unit Tests
    # =========================================================================
    def test_user_role_allowed_on_user_route(self):
        """USER role token succeeds on require_role(Role.USER) route."""
        res = self.client.get("/test/user-only", headers=self.user_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "USER")
        self.assertEqual(res.json()["user_id"], "user-uid-001")

    def test_admin_and_system_roles_forbidden_on_user_only_route(self):
        """DoD: Insufficient role returns 403 Forbidden (not 401)."""
        # ADMIN calling user-only route
        res_admin = self.client.get("/test/user-only", headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 403)
        self.assertEqual(res_admin.headers.get("X-Error-Code"), "FORBIDDEN_USER_REQUIRED")

        # SYSTEM calling user-only route
        res_system = self.client.get("/test/user-only", headers=self.system_headers)
        self.assertEqual(res_system.status_code, 403)
        self.assertEqual(res_system.headers.get("X-Error-Code"), "FORBIDDEN_USER_REQUIRED")

    def test_unauthenticated_on_user_route_returns_401(self):
        """Unauthenticated caller on require_role route returns 401 Unauthorized."""
        res_missing = self.client.get("/test/user-only")
        self.assertEqual(res_missing.status_code, 401)
        self.assertEqual(res_missing.headers.get("X-Error-Code"), "NOT_AUTHENTICATED")

        res_expired = self.client.get("/test/user-only", headers={"Authorization": f"Bearer {self.expired_user_token}"})
        self.assertEqual(res_expired.status_code, 401)
        self.assertEqual(res_expired.headers.get("X-Error-Code"), "TOKEN_EXPIRED")

    # =========================================================================
    # 2. ADMIN Role Unit Tests
    # =========================================================================
    def test_admin_role_allowed_on_admin_route(self):
        """ADMIN role token succeeds on require_role(Role.ADMIN) route."""
        res = self.client.get("/test/admin-only", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "ADMIN")
        self.assertEqual(res.json()["user_id"], "admin-uid-002")

    def test_user_and_system_roles_forbidden_on_admin_only_route(self):
        """DoD: Insufficient role on admin route returns 403 Forbidden."""
        # USER calling admin-only route
        res_user = self.client.get("/test/admin-only", headers=self.user_headers)
        self.assertEqual(res_user.status_code, 403)
        self.assertEqual(res_user.json()["detail"], "Admin privileges required")
        self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN")

        # SYSTEM calling admin-only route
        res_system = self.client.get("/test/admin-only", headers=self.system_headers)
        self.assertEqual(res_system.status_code, 403)
        self.assertEqual(res_system.headers.get("X-Error-Code"), "FORBIDDEN")

    def test_unauthenticated_on_admin_route_returns_401(self):
        """Unauthenticated caller on admin route returns 401 Unauthorized."""
        res = self.client.get("/test/admin-only")
        self.assertEqual(res.status_code, 401)

    # =========================================================================
    # 3. SYSTEM Role Unit Tests
    # =========================================================================
    def test_system_role_allowed_on_system_route(self):
        """SYSTEM role token succeeds on require_role(Role.SYSTEM) route."""
        res = self.client.get("/test/system-only", headers=self.system_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["role"], "SYSTEM")
        self.assertEqual(res.json()["user_id"], "Node A")

    def test_user_and_admin_roles_forbidden_on_system_only_route(self):
        """DoD: Insufficient role on system route returns 403 Forbidden."""
        # USER calling system-only route
        res_user = self.client.get("/test/system-only", headers=self.user_headers)
        self.assertEqual(res_user.status_code, 403)
        self.assertIn("System credential required", res_user.json()["detail"])
        self.assertEqual(res_user.headers.get("X-Error-Code"), "FORBIDDEN_SYSTEM_REQUIRED")

        # ADMIN calling system-only route
        res_admin = self.client.get("/test/system-only", headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 403)
        self.assertEqual(res_admin.headers.get("X-Error-Code"), "FORBIDDEN_SYSTEM_REQUIRED")

    def test_unauthenticated_on_system_route_returns_401(self):
        """Unauthenticated caller on system route returns 401 Unauthorized."""
        res = self.client.get("/test/system-only")
        self.assertEqual(res.status_code, 401)

    # =========================================================================
    # 4. Multi-Role Gate Tests
    # =========================================================================
    def test_multi_role_user_or_admin(self):
        """require_role(Role.USER, Role.ADMIN) allows USER and ADMIN, rejects SYSTEM."""
        res_user = self.client.get("/test/user-or-admin", headers=self.user_headers)
        self.assertEqual(res_user.status_code, 200)

        res_admin = self.client.get("/test/user-or-admin", headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 200)

        res_system = self.client.get("/test/user-or-admin", headers=self.system_headers)
        self.assertEqual(res_system.status_code, 403)
        self.assertEqual(res_system.headers.get("X-Error-Code"), "FORBIDDEN")

    def test_multi_role_admin_or_system_with_case_normalization(self):
        """require_role('admin', 'SYSTEM') normalizes strings and allows ADMIN and SYSTEM, rejects USER."""
        res_admin = self.client.get("/test/admin-or-system", headers=self.admin_headers)
        self.assertEqual(res_admin.status_code, 200)

        res_system = self.client.get("/test/admin-or-system", headers=self.system_headers)
        self.assertEqual(res_system.status_code, 200)

        res_user = self.client.get("/test/admin-or-system", headers=self.user_headers)
        self.assertEqual(res_user.status_code, 403)

    # =========================================================================
    # 5. Pre-configured Shortcut Dependencies Tests
    # =========================================================================
    def test_shortcut_dependencies(self):
        """Verifies require_user, require_admin, require_system shortcuts."""
        # require_user
        self.assertEqual(self.client.get("/test/shortcut-user", headers=self.user_headers).status_code, 200)
        self.assertEqual(self.client.get("/test/shortcut-user", headers=self.admin_headers).status_code, 403)

        # require_admin
        self.assertEqual(self.client.get("/test/shortcut-admin", headers=self.admin_headers).status_code, 200)
        self.assertEqual(self.client.get("/test/shortcut-admin", headers=self.user_headers).status_code, 403)

        # require_system
        self.assertEqual(self.client.get("/test/shortcut-system", headers=self.system_headers).status_code, 200)
        self.assertEqual(self.client.get("/test/shortcut-system", headers=self.user_headers).status_code, 403)

    # =========================================================================
    # 6. Direct Async Dependency Invocation & Edge Cases
    # =========================================================================
    def test_require_role_empty_args_raises_value_error(self):
        """Calling require_role with no arguments raises ValueError."""
        with self.assertRaises(ValueError):
            require_role()

    def test_direct_async_dependency_invocation(self):
        """Tests invoking the generated dependency directly as an async callable."""
        admin_auth = AuthenticatedUser(user_id="adm-1", role="ADMIN", username="admin")
        user_auth = AuthenticatedUser(user_id="usr-1", role="USER", username="user")

        checker = require_role(Role.ADMIN)

        # Authorized call returns the user model
        result = asyncio.run(checker(admin_auth))
        self.assertEqual(result, admin_auth)

        # Unauthorized call raises HTTPException 403
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user_auth))
        self.assertEqual(ctx.exception.status_code, 403)
        headers = ctx.exception.headers or {}
        self.assertEqual(headers.get("X-Error-Code"), "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
