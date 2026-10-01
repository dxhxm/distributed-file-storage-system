"""
replication_model.py
====================
Pydantic data models and schemas for cluster replication configuration (Section 13)
and Admin-only replication settings per Section 26.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ReplicationConfig(BaseModel):
    """
    Active replication settings for the cluster.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    replication_factor: int = Field(
        default=3,
        ge=1,
        description="Target number of replica copies stored across cluster nodes (must be >= 1)"
    )
    cluster_size: int = Field(
        default=3,
        ge=1,
        description="Current total number of nodes in the cluster topology"
    )
    auto_rebalance: bool = Field(
        default=True,
        description="Whether to automatically rebalance/re-replicate on node failure"
    )
    replication_timeout: float = Field(
        default=5.0,
        gt=0,
        description="Network timeout in seconds for inter-node replication RPC"
    )


class UpdateReplicationConfigRequest(BaseModel):
    """
    Payload for updating cluster replication configuration.
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    replication_factor: Optional[int] = Field(
        default=None,
        ge=1,
        description="New target replication factor (must be >= 1 and <= cluster_size)"
    )
    auto_rebalance: Optional[bool] = Field(
        default=None,
        description="Toggle automatic rebalance on cluster mutations"
    )
    replication_timeout: Optional[float] = Field(
        default=None,
        gt=0,
        description="Network timeout in seconds for inter-node replication RPC"
    )


class ReplicationConfigResponse(BaseModel):
    """
    Public response schema for replication configuration.
    """
    model_config = ConfigDict(populate_by_name=True)

    replication_factor: int = Field(..., description="Target number of replica copies")
    cluster_size: int = Field(..., description="Current total node count in cluster")
    max_possible_replication_factor: int = Field(..., description="Maximum allowed replication factor")
    auto_rebalance: bool = Field(..., description="Auto-rebalance enabled status")
    replication_timeout: float = Field(..., description="Replication timeout in seconds")
    message: Optional[str] = Field(default=None, description="Status or confirmation message")
