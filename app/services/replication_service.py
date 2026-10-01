import threading
from typing import Any, Dict, Optional
import requests
from app.models.config import NODES, CURRENT_NODE
from app.services.jwt_service import get_system_auth_headers

# Replication tunables
_replication_lock = threading.Lock()
REPLICATION_FACTOR: int = 3
AUTO_REBALANCE: bool = True
REPLICATION_TIMEOUT: float = 5.0


def get_cluster_size() -> int:
    """
    Returns the current total number of nodes in the cluster topology.
    """
    try:
        from app.services import health_service
        nodes = health_service.get_all_nodes()
        if nodes:
            return len(nodes)
    except Exception:
        pass
    return len(NODES)


def get_replication_config() -> Dict[str, Any]:
    """
    Returns the active replication settings and current cluster constraints.
    """
    with _replication_lock:
        size = get_cluster_size()
        return {
            "replication_factor": min(REPLICATION_FACTOR, size) if size > 0 else REPLICATION_FACTOR,
            "cluster_size": size,
            "max_possible_replication_factor": size,
            "auto_rebalance": AUTO_REBALANCE,
            "replication_timeout": REPLICATION_TIMEOUT,
        }


def update_replication_config(
    replication_factor: Optional[int] = None,
    auto_rebalance: Optional[bool] = None,
    replication_timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Updates replication settings with validation against cluster size.
    Per Section 13 & 26 DoD:
    Changing replication factor is validated against cluster size before being accepted.
    """
    global REPLICATION_FACTOR, AUTO_REBALANCE, REPLICATION_TIMEOUT

    with _replication_lock:
        cluster_size = get_cluster_size()

        if replication_factor is not None:
            if replication_factor < 1:
                raise ValueError("Replication factor must be at least 1")
            if replication_factor > cluster_size:
                raise ValueError(
                    f"Replication factor ({replication_factor}) cannot exceed "
                    f"current cluster size ({cluster_size} nodes)"
                )
            REPLICATION_FACTOR = int(replication_factor)

        if auto_rebalance is not None:
            AUTO_REBALANCE = bool(auto_rebalance)

        if replication_timeout is not None:
            if replication_timeout <= 0:
                raise ValueError("Replication timeout must be greater than 0")
            REPLICATION_TIMEOUT = float(replication_timeout)

        return {
            "replication_factor": REPLICATION_FACTOR,
            "cluster_size": cluster_size,
            "max_possible_replication_factor": cluster_size,
            "auto_rebalance": AUTO_REBALANCE,
            "replication_timeout": REPLICATION_TIMEOUT,
        }


def is_node_alive(node):
    """Check if a node is alive by hitting its /health endpoint."""
    try:
        res = requests.get(f"{node}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


def replicate_file(file_path, filename):
    """Replicate a file to all alive peer nodes with SYSTEM role authentication."""
    for node in NODES:
        if node == CURRENT_NODE:
            continue

        # Skip dead nodes
        if not is_node_alive(node):
            print(f"[REPLICATION] {node} is DOWN - skipping")
            continue

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                headers = get_system_auth_headers()
                response = requests.post(f"{node}/replicate", files=files, headers=headers, timeout=REPLICATION_TIMEOUT)

            print(f"[REPLICATION] Sent to {node} - Status: {response.status_code}")

        except Exception as e:
            print(f"[REPLICATION] Failed to send to {node}: {e}")