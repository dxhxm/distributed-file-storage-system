"""
log_model.py
============
Pydantic data models for system logs, audit trails, and detailed health metrics
per Section 26 (Admin Operations & Privileged Endpoints).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class LogEntry(BaseModel):
    """
    Structured log entry model.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Monotonically increasing sequence identifier")
    timestamp: float = Field(..., description="Epoch timestamp of the log event")
    timestamp_iso: str = Field(..., description="ISO 8601 formatted timestamp string")
    level: str = Field(..., description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, AUDIT)")
    component: str = Field(..., description="Source logger name or system component")
    message: str = Field(..., description="Log message text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual event metadata")


class LogsResponse(BaseModel):
    """
    Response schema for retrieving system log entries.
    """
    model_config = ConfigDict(populate_by_name=True)

    logs: List[LogEntry] = Field(default_factory=list, description="List of structured log entries")
    total_retrieved: int = Field(..., description="Number of logs returned in current query")
    total_buffered: int = Field(..., description="Total count of logs currently in memory buffer")
    limit: int = Field(..., description="Applied query limit")
    level_filter: Optional[str] = Field(default=None, description="Applied log level filter")
    component_filter: Optional[str] = Field(default=None, description="Applied component filter")
    search_query: Optional[str] = Field(default=None, description="Applied keyword search query")


class DetailedHealthResponse(BaseModel):
    """
    Detailed system health status and operational telemetry (Admin only).
    """
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(..., description="Overall system health status (HEALTHY, DEGRADED, UNHEALTHY)")
    timestamp: float = Field(..., description="Current server epoch timestamp")
    uptime_seconds: float = Field(..., description="Node uptime duration in seconds")
    cluster: Dict[str, Any] = Field(default_factory=dict, description="Cluster topology and quorum state")
    consensus: Dict[str, Any] = Field(default_factory=dict, description="Raft consensus and leader election telemetry")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Individual node statuses and heartbeat metrics")
    storage: Dict[str, Any] = Field(default_factory=dict, description="Storage engine metrics and file ledger summary")
    time_sync: Dict[str, Any] = Field(default_factory=dict, description="Clock synchronization and skew metrics")
    system_runtime: Dict[str, Any] = Field(default_factory=dict, description="Python runtime and OS process environment")
