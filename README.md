# Distributed Fault-Tolerant File Storage System (DFSS)

A lightweight, fault-tolerant distributed file storage and replication system built with **FastAPI**, **Raft Consensus**, **Berkeley Time Synchronization**, and **Role-Based Access Control (RBAC)**.

---

## Overview

DFSS coordinates a cluster of independent server nodes to provide fault-tolerant, replicated file storage with high availability and strong data consistency. If any node in the cluster fails or goes offline, the remaining nodes automatically elect a new leader and continue serving read/write traffic without data loss.

### Key Capabilities
* **Raft Consensus Engine**: Automatic leader election, heartbeat health monitoring, and cluster state agreement.
* **Fault-Tolerant Replication**: Consistent multi-node file chunk distribution and replica synchronization.
* **Berkeley Time Synchronization**: Internal logical clock alignment and drift compensation across cluster nodes.
* **Role-Based Access Control (RBAC)**: Secure JWT access and refresh token sessions with `USER`, `ADMIN`, and `SYSTEM` roles.
* **Zero-Trust Security Layer**: OWASP defense-in-depth headers, TLS/HTTPS enforcement, and brute-force rate limiting.

---

## System Architecture

```
                       +-------------------------------+
                       |    Client / Web Application   |
                       +---------------+---------------+
                                       |
                     HTTP / REST API   |   (Bearer JWT / RBAC)
                                       v
        +-------------------------------------------------------------+
        |                 DFSS Distributed Cluster                    |
        |                                                             |
        |   +------------------+             +------------------+     |
        |   |   Node A:8000    |<----------->|   Node B:8001    |     |
        |   | (Current Leader) |  Heartbeats |    (Follower)    |     |
        |   +--------+---------+  Consensus  +--------+---------+     |
        |            |        \             /         |               |
        |            |         \           /          |               |
        |            |          v         v           |               |
        |            |     +------------------+       |               |
        |            |     |   Node C:8002    |       |               |
        |            |     |    (Follower)    |       |               |
        |            |     +--------+---------+       |               |
        |            v              v                 v               |
        |     [Storage Node1] [Storage Node3]  [Storage Node2]        |
        |     (Files + SQLite)(Files + SQLite) (Files + SQLite)       |
        +-------------------------------------------------------------+
```

---

## How It Works

1. **Cluster Consensus & Leader Election**
   * Each node starts in a `FOLLOWER` state with a randomized election timeout.
   * If a follower misses heartbeats from the active leader, it transitions to `CANDIDATE` and requests cluster votes.
   * Once a candidate achieves a quorum majority, it becomes the `LEADER` and dispatches periodic heartbeats to followers.

2. **File Replication Workflow**
   * Write operations (file upload, metadata update, deletion) are routed to the cluster Leader.
   * The Leader commits the entry to its local storage database and broadcasts replication requests to alive follower nodes.
   * Follower nodes pull replica payloads, verify SHA-256 content hashes, and persist them locally.

3. **Time Synchronization**
   * Nodes execute a distributed Berkeley time synchronization algorithm at regular intervals to sample peer clock offsets, calculate average drift, and apply gradual clock slew correction.

4. **Authentication & RBAC**
   * Users authenticate via `/auth/login` to obtain short-lived JWT access tokens and long-lived refresh tokens.
   * Role permissions (`USER`, `ADMIN`, `SYSTEM`) are strictly enforced per endpoint.

---

## Getting Started

### Prerequisites
* **Python 3.10+**
* Virtual environment (`venv`)

### 1. Installation

```bash
# Clone the repository
git clone <github-repository-link>
cd distributed-file-storage-system

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the sample environment template:

```bash
cp .env.example .env
```

### 3. Start Distributed Cluster Nodes

Run each node in a dedicated terminal window:

```bash
# Terminal 1 — Node A (Port 8000)
python nodes/nodeA.py

# Terminal 2 — Node B (Port 8001)
python nodes/nodeB.py

# Terminal 3 — Node C (Port 8002)
python nodes/nodeC.py
```

### 4. Access API Documentation

Interactive OpenAPI / Swagger documentation is available on each running node:

* **Node A**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Node B**: [http://localhost:8001/docs](http://localhost:8001/docs)
* **Node C**: [http://localhost:8002/docs](http://localhost:8002/docs)

---

## API Endpoints Overview

| Category | Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/auth/login` | User login (returns access & refresh tokens) | Public |
| **Auth** | `POST` | `/auth/refresh` | Exchange refresh token for new access token | Public |
| **Auth** | `GET` | `/auth/me` | Retrieve authenticated user profile | `USER` / `ADMIN` |
| **Files** | `POST` | `/replicate/upload` | Upload and replicate a file across cluster | `USER` / `ADMIN` |
| **Files** | `GET` | `/replicate/download/{filename}` | Download file from node replica | `USER` / `ADMIN` |
| **Files** | `GET` | `/replicate/files` | List all replicated files in storage | `USER` / `ADMIN` |
| **Files** | `DELETE` | `/replicate/delete/{filename}` | Delete file from cluster replicas | `ADMIN` |
| **Consensus** | `GET` | `/consensus/status` | Cluster election state and active leader | Authenticated |
| **Consensus** | `POST` | `/consensus/propose` | Propose state transition to leader | Authenticated |
| **Health** | `GET` | `/health` | Node health check and peer status | Authenticated |
| **Admin** | `GET` | `/admin/logs` | Query cluster audit and security logs | `ADMIN` |
| **Admin** | `POST` | `/auth/users` | Provision new user account | `ADMIN` |

---

## Security & Secrets Management (Section 34 & Section 33)

DFSS is engineered with zero hardcoded credentials and a defense-in-depth security layer.

### Key Environment Variables

| Variable | Description | Default / Requirement |
| :--- | :--- | :--- |
| `JWT_SECRET` | 32-byte secret key for HMAC SHA-256 JWT tokens. | **Required** (`validate_auth_config()` aborts on boot if missing) |
| `JWT_EXPIRY_MINUTES` | Access token lifespan in minutes. | `60` |
| `JWT_REFRESH_EXPIRY_DAYS` | Refresh token lifespan in days. | `7` |
| `AUTH_RATE_LIMIT_MAX_ATTEMPTS` | Failed login attempts allowed before lockout. | `5` |
| `AUTH_RATE_LIMIT_COOLDOWN_SECONDS` | Lockout cooldown duration in seconds. | `60` |
| `ENFORCE_HTTPS` | Redirect plain HTTP traffic to HTTPS (`HTTP 307`). | `false` (dev) / `true` (prod) |

### JWT_SECRET Rotation Procedure

To rotate cluster signing secrets per Section 34 security policies:

1. **Generate Secret**: Generate a cryptographically secure 32-byte key:
   ```bash
   openssl rand -hex 32
   ```
2. **Update Environment**: Update `JWT_SECRET` in `.env` (or container environment) across all nodes.
3. **Restart Nodes**: Perform a rolling restart of Node A, Node B, and Node C.
4. **Re-Authentication**: Active user sessions are invalidated and clients re-authenticate via `/auth/login`. Inter-node system tokens regenerate automatically.

---

## Running Automated Tests

Run the complete test suite:

```bash
# Run all unit and integration tests
python -m unittest discover -s tests

# Run specific security test suites
python -m unittest tests/test_security_headers.py
python -m unittest tests/test_rate_limiter.py
python -m unittest tests/test_secrets_audit.py
```

---

## License

MIT License
