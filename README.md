# Distributed Fault-Tolerant File Storage System

## Instructions to Run the Prototype

### 1. Clone the Repository

```bash
git clone <github-repository-link>
cd distributed-file-storage-system
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment.

Mac / Linux

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Start the Distributed Nodes

Run each node in a separate terminal.

Start Node A

```bash
python nodes/nodeA.py
```

Start Node B

```bash
python nodes/nodeB.py
```

Start Node C

```bash
python nodes/nodeC.py
```

---

### 5. Access the API

After starting the servers, open the FastAPI documentation:

```
http://localhost:8000/docs
```

This interface can be used to test the available API endpoints such as uploading and retrieving files.

---

## File Access & Authorization Policy

DFSS operates on a **Shared Collaborative Cluster Storage Model**:

### 1. Storage & Namespace Access Model
* **Shared Cluster File Pool**: Stored files belong to a shared cluster namespace and are accessible across all authenticated users (`USER` and `ADMIN`).
* **Collaborative File Operations**: Any authenticated user can upload new files, view the cluster-wide file ledger (`GET /files`), download any stored file or replica (`GET /files/{file_id}`), and delete files (`DELETE /files/{file_id}`).
* **Strict Authentication Invariant**: Unauthenticated requests to any file route are rejected immediately with `HTTP 401 Unauthorized`.
* **Internal Node Replication**: Inter-node file replication (`POST /replicate`) is restricted to internal `SYSTEM` service tokens.

### 2. Role-Based Access Control (RBAC) Matrix

| Endpoint Route | Method | Permitted Roles | Description | Unauth / Forbidden Status |
| :--- | :--- | :--- | :--- | :--- |
| `/auth/login` | `POST` | Public | Authenticate user & issue JWT token | `401 Unauthorized` on bad credentials |
| `/auth/register` | `POST` | Public | Register new user account | `400 Bad Request` on duplicate |
| `/auth/me` | `GET` | `USER`, `ADMIN`, `SYSTEM` | Current user profile | `401 Unauthorized` |
| `/auth/users` | `GET` | `ADMIN` | List all registered user accounts | `401` / `403 Forbidden` |
| `/files` | `GET` | `USER`, `ADMIN`, `SYSTEM` | List all files in the cluster | `401 Unauthorized` |
| `/files/{file_id}` | `GET` | `USER`, `ADMIN`, `SYSTEM` | Download file / fetch replica | `401 Unauthorized` |
| `/files/upload`, `/upload` | `POST` | `USER`, `ADMIN`, `SYSTEM` | Upload and replicate file | `401 Unauthorized` |
| `/files/{file_id}` | `DELETE` | `USER`, `ADMIN`, `SYSTEM` | Delete file & purge replicas | `401 Unauthorized` |
| `/replicate` | `POST` | `SYSTEM` | Inter-node file replication | `401` / `403 Forbidden` |
| `/health` | `GET` | `USER`, `ADMIN`, `SYSTEM` | Node health status | `401 Unauthorized` |
| `/cluster/status` | `GET` | `USER`, `ADMIN`, `SYSTEM` | Cluster topology & node states | `401 Unauthorized` |
| `/nodes` | `GET` | `USER`, `ADMIN`, `SYSTEM` | Node inventory | `401 Unauthorized` |
| `/nodes/update` | `POST` | `ADMIN` | Mutate cluster node configuration | `401` / `403 Forbidden` |
| `/nodes/remove` | `POST` | `ADMIN` | Remove node from cluster | `401` / `403 Forbidden` |
| `/nodes/add` | `POST` | `ADMIN` | Add node to cluster | `401` / `403 Forbidden` |
| `/raft/*`, `/sync-time` | `GET`/`POST` | `SYSTEM` | Inter-node consensus & synchronization | `401` / `403 Forbidden` |

---

## Notes

* The system simulates a **distributed file storage system** using multiple nodes running on different ports.
* Each node represents a server in the distributed environment with local storage replication.
* All protected endpoints enforce standard error schemas (`{"detail": ...}`) and distinguish between unauthenticated (`401`) and unauthorized (`403`) access.

