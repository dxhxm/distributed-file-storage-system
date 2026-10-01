"""
log_service.py
==============
In-memory structured logging, audit trail, and operational telemetry service
per Section 26.
Features:
- Thread-safe circular ring buffer for real-time application logs.
- Custom logging.Handler to capture log events across all system components.
- Dedicated audit logging to record who viewed what and when.
- In-depth telemetry aggregation for detailed health diagnostics.
"""

import collections
import datetime
import logging
import os
import platform
import sys
import threading
import time
from typing import Any, Dict, List, Optional

START_TIME = time.time()
MAX_LOG_BUFFER_SIZE = 10000

_log_lock = threading.Lock()
_log_buffer = collections.deque(maxlen=MAX_LOG_BUFFER_SIZE)
_log_seq_counter = 0


class RingBufferLogHandler(logging.Handler):
    """
    Logging handler that intercepts Python logging records and appends them
    to the centralized in-memory structured log ring buffer.
    """
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            add_log_entry(
                level=record.levelname,
                component=record.name,
                message=msg,
                timestamp=record.created,
                metadata={
                    "filename": record.filename,
                    "lineno": record.lineno,
                    "funcName": record.funcName,
                }
            )
        except Exception:
            self.handleError(record)


def add_log_entry(
    level: str,
    component: str,
    message: str,
    timestamp: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Thread-safely adds a structured log entry to the circular buffer.
    """
    global _log_seq_counter
    ts = timestamp if timestamp is not None else time.time()
    ts_iso = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat()

    with _log_lock:
        _log_seq_counter += 1
        entry = {
            "id": _log_seq_counter,
            "timestamp": ts,
            "timestamp_iso": ts_iso,
            "level": str(level).upper(),
            "component": str(component),
            "message": str(message),
            "metadata": metadata or {},
        }
        _log_buffer.append(entry)
        return entry


def record_audit(
    actor_id: str,
    actor_username: str,
    action: str,
    target: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Records a high-integrity audit trail entry documenting admin/system actions.
    Per Section 26 DoD: Log access is itself logged (who viewed what, when).
    """
    audit_msg = (
        f"[AUDIT] Actor '{actor_username}' (id: '{actor_id}') executed '{action}' "
        f"on target '{target}'."
    )
    audit_meta = {
        "actor_id": actor_id,
        "actor_username": actor_username,
        "action": action,
        "target": target,
        "details": details or {},
    }
    logger = logging.getLogger("audit")
    logger.info(audit_msg)
    return add_log_entry(
        level="AUDIT",
        component="audit",
        message=audit_msg,
        metadata=audit_meta,
    )


def get_logs(
    limit: int = 100,
    level: Optional[str] = None,
    component: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves filtered logs from the ring buffer in reverse chronological order (newest first).
    """
    with _log_lock:
        entries = list(_log_buffer)

    # Reverse chronological (newest first)
    entries.reverse()

    norm_level = level.strip().upper() if level and level.strip() else None
    norm_comp = component.strip().lower() if component and component.strip() else None
    norm_search = search.strip().lower() if search and search.strip() else None

    filtered = []
    for item in entries:
        if norm_level and item["level"] != norm_level:
            continue
        if norm_comp and norm_comp not in item["component"].lower():
            continue
        if norm_search:
            msg_match = norm_search in item["message"].lower()
            comp_match = norm_search in item["component"].lower()
            if not (msg_match or comp_match):
                continue

        filtered.append(item)
        if len(filtered) >= limit:
            break

    return {
        "logs": filtered,
        "total_retrieved": len(filtered),
        "total_buffered": len(entries),
        "limit": limit,
        "level_filter": level,
        "component_filter": component,
        "search_query": search,
    }


def clear_logs() -> None:
    """Clears the in-memory log buffer (useful for test isolation)."""
    with _log_lock:
        _log_buffer.clear()


def get_detailed_health() -> Dict[str, Any]:
    """
    Aggregates comprehensive health, telemetry, and diagnostics across all system sub-components.
    """
    now = time.time()
    uptime = now - START_TIME

    # 1. Consensus telemetry
    consensus_info = {}
    try:
        from app.api.consensus import consensus_service
        if consensus_service:
            with consensus_service.lock:
                consensus_info = {
                    "current_node": getattr(consensus_service, "current_node", "Node A"),
                    "state": getattr(consensus_service, "state", "FOLLOWER"),
                    "term": getattr(consensus_service, "current_term", 0),
                    "leader_id": getattr(consensus_service, "leader_id", None),
                    "commit_index": getattr(consensus_service, "commit_index", -1),
                    "last_applied": getattr(consensus_service, "last_applied", -1),
                    "log_entries_count": len(getattr(consensus_service, "log", [])),
                    "state_machine_blocks": len(getattr(consensus_service, "state_machine", [])),
                    "peers": getattr(consensus_service, "peers", []),
                    "running": getattr(consensus_service, "running", True),
                    "election_timeout_range": getattr(consensus_service, "election_timeout_range", (2.0, 4.0)),
                    "heartbeat_interval": getattr(consensus_service, "heartbeat_interval", 0.5),
                }
    except Exception as exc:
        consensus_info = {"error": f"Failed to inspect consensus service: {str(exc)}"}

    # 2. Node connectivity and cluster topology
    cluster_status = {}
    nodes_info = []
    try:
        from app.services import health_service
        cluster_status = health_service.get_cluster_status()
        nodes_info = health_service.get_nodes_info().get("nodes", [])
    except Exception as exc:
        cluster_status = {"error": f"Failed to inspect cluster status: {str(exc)}"}

    # 3. Storage engine metrics
    storage_info = {}
    try:
        from app.services import user_storage
        # Get count of files from DB if possible
        import sqlite3
        db_path = getattr(user_storage, "DB_PATH", "users.db")
        if os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
                user_count = 0
                if "users" in tables:
                    cursor.execute("SELECT COUNT(*) FROM users;")
                    user_count = cursor.fetchone()[0]

            storage_info = {
                "db_path": os.path.abspath(db_path),
                "db_size_bytes": os.path.getsize(db_path),
                "registered_users_count": user_count,
                "tables": tables,
                "status": "ONLINE",
            }
        else:
            storage_info = {
                "db_path": os.path.abspath(db_path),
                "status": "UNINITIALIZED",
            }
    except Exception as exc:
        storage_info = {"error": f"Failed to inspect storage: {str(exc)}"}

    # 4. Time synchronization metrics
    time_sync_info = {}
    try:
        from app.services import time_sync
        time_sync_info = {
            "drift_offset": getattr(time_sync, "drift_offset", 0.0),
            "target_offset": getattr(time_sync, "target_offset", 0.0),
            "last_returned_time": getattr(time_sync, "last_returned_time", 0.0),
            "slew_rate": getattr(time_sync, "SLEW_RATE", 0.001),
            "slew_interval": getattr(time_sync, "SLEW_INTERVAL", 0.1),
            "max_skew_threshold": getattr(time_sync, "max_skew_threshold", 60.0),
        }
    except Exception as exc:
        time_sync_info = {"error": f"Failed to inspect time sync: {str(exc)}"}

    # 5. System runtime and environment
    system_runtime = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "start_time_iso": datetime.datetime.fromtimestamp(START_TIME, tz=datetime.timezone.utc).isoformat(),
        "uptime_formatted": f"{uptime:.2f}s",
        "buffered_logs_count": len(_log_buffer),
    }

    # Determine overall status
    cluster_state = cluster_status.get("cluster_state", "UNKNOWN")
    if cluster_state in ("HEALTHY", "OPERATIONAL"):
        status = "HEALTHY"
    elif cluster_state == "NO MAJORITY":
        status = "DEGRADED"
    else:
        status = "OPERATIONAL"

    return {
        "status": status,
        "timestamp": now,
        "uptime_seconds": uptime,
        "cluster": cluster_status,
        "consensus": consensus_info,
        "nodes": nodes_info,
        "storage": storage_info,
        "time_sync": time_sync_info,
        "system_runtime": system_runtime,
    }


# Automatically attach RingBufferLogHandler to root logger and standard loggers
_root_logger = logging.getLogger()
_handler = RingBufferLogHandler()
_handler.setLevel(logging.DEBUG)
_root_logger.addHandler(_handler)

# Pre-populate startup log entry
add_log_entry("INFO", "system", "DFSS System Logging & Telemetry Engine initialized.")
