"""
cluster_config_model.py
======================
Pydantic data models and validation rules for cluster configuration tunables
(e.g., election timeouts, heartbeat intervals) per Sections 11, 12, and 26.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClusterConfig(BaseModel):
    """
    Cluster configuration tunables schema.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    election_timeout_min: float = Field(
        default=2.0,
        gt=0,
        description="Minimum randomized election timeout in seconds (must be > 0)"
    )
    election_timeout_max: float = Field(
        default=4.0,
        gt=0,
        description="Maximum randomized election timeout in seconds (must be >= election_timeout_min)"
    )
    heartbeat_interval: float = Field(
        default=0.5,
        gt=0,
        description="Raft leader heartbeat broadcast interval in seconds (must be > 0)"
    )
    health_check_interval: float = Field(
        default=5.0,
        gt=0,
        description="Background node health check probing interval in seconds (must be > 0)"
    )

    @model_validator(mode="after")
    def validate_timer_relationships(self) -> "ClusterConfig":
        if self.election_timeout_max < self.election_timeout_min:
            raise ValueError(
                f"election_timeout_max ({self.election_timeout_max}s) cannot be less than "
                f"election_timeout_min ({self.election_timeout_min}s)"
            )
        if self.heartbeat_interval >= self.election_timeout_min:
            raise ValueError(
                f"heartbeat_interval ({self.heartbeat_interval}s) must be smaller than "
                f"election_timeout_min ({self.election_timeout_min}s) to prevent false election timeouts"
            )
        return self


class UpdateClusterConfigRequest(BaseModel):
    """
    Payload for updating cluster configuration tunables.
    Allows partial or complete updates with strict non-negative validation.
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    election_timeout_min: Optional[float] = Field(
        default=None,
        gt=0,
        description="Minimum randomized election timeout in seconds (must be > 0)"
    )
    election_timeout_max: Optional[float] = Field(
        default=None,
        gt=0,
        description="Maximum randomized election timeout in seconds (must be >= election_timeout_min)"
    )
    heartbeat_interval: Optional[float] = Field(
        default=None,
        gt=0,
        description="Raft leader heartbeat broadcast interval in seconds (must be > 0)"
    )
    health_check_interval: Optional[float] = Field(
        default=None,
        gt=0,
        description="Background node health check probing interval in seconds (must be > 0)"
    )


class ClusterConfigResponse(BaseModel):
    """
    Public response schema representing the active cluster configuration.
    """
    model_config = ConfigDict(populate_by_name=True)

    election_timeout_min: float = Field(..., description="Minimum election timeout (seconds)")
    election_timeout_max: float = Field(..., description="Maximum election timeout (seconds)")
    heartbeat_interval: float = Field(..., description="Heartbeat broadcast interval (seconds)")
    health_check_interval: float = Field(..., description="Health check interval (seconds)")
    message: Optional[str] = Field(default=None, description="Optional status message on update")
