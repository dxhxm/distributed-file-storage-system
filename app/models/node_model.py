"""
node_model.py
=============
Pydantic data models for cluster node management operations in DFSS per Section 26.
Defines schemas for:
- NodeActionRequest: Generic node action payload (cordon, uncordon, remove).
- AddNodeRequest: Node registration payload.
- UpdateNodeRequest: Node status update payload.
- NodeInfoResponse: Public node metadata representation.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NodeActionRequest(BaseModel):
    """
    Schema for node management actions (e.g. cordon, uncordon, remove).
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    node_name: Optional[str] = Field(default=None, description="Identifier or display name of the target node")
    node_id: Optional[str] = Field(default=None, description="Alias for node identifier")


class AddNodeRequest(BaseModel):
    """
    Schema for adding/registering a new cluster node.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    node_name: str = Field(..., min_length=1, description="Unique node key/identifier (e.g. 'nodeD')")
    url: str = Field(..., min_length=1, description="Base URL of the cluster node (e.g. 'http://127.0.0.1:8003')")
    display_name: Optional[str] = Field(default=None, description="Human-readable node label (e.g. 'Node D')")


class UpdateNodeRequest(BaseModel):
    """
    Schema for updating node configuration or state.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    node_name: str = Field(..., min_length=1, description="Identifier of the target node")
    status: str = Field(..., min_length=1, description="Target status ('ALIVE', 'DEAD', 'CORDONED', etc.)")
