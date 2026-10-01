"""
logs.py
=======
API routes for Admin-only access to system logs, audit trails, and logging queries
per Section 26 (Admin Operations & Privileged Endpoints).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import AuthenticatedUser, require_admin
from app.models.log_model import LogsResponse
from app.services import log_service

router = APIRouter()


@router.get("/logs", response_model=LogsResponse, tags=["Admin Logging & Audit"])
@router.get("/admin/logs", response_model=LogsResponse, include_in_schema=False)
@router.get("/system/logs", response_model=LogsResponse, include_in_schema=False)
def get_system_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of log records to return"),
    level: Optional[str] = Query(default=None, description="Filter logs by level (INFO, WARNING, ERROR, AUDIT, DEBUG)"),
    component: Optional[str] = Query(default=None, description="Filter logs by component/logger name"),
    search: Optional[str] = Query(default=None, description="Search query string matching log message or component"),
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Retrieve structured system logs and audit trail.
    Restricted to ADMIN role.

    DoD Invariant:
    Log access is itself logged (who viewed what, when).
    """
    # 1. Audit the access event (who viewed what, when)
    log_service.record_audit(
        actor_id=current_user.user_id,
        actor_username=current_user.username or current_user.user_id,
        action="VIEW_SYSTEM_LOGS",
        target="/logs",
        details={
            "limit": limit,
            "level": level,
            "component": component,
            "search": search,
        }
    )

    # 2. Retrieve filtered log entries
    result = log_service.get_logs(
        limit=limit,
        level=level,
        component=component,
        search=search,
    )

    return LogsResponse(**result)
