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

## Secrets Management & Security (Section 34)

DFSS enforces strict environment-driven configuration and zero-hardcoded secrets across the entire codebase.

### 1. Environment Configuration

All sensitive configuration parameters must be supplied via environment variables or a local `.env` file (copied from `.env.example`). The server performs startup validation (`validate_auth_config()`) and will **fail loudly with a `RuntimeError`** if required secrets are absent.

| Variable | Description | Required / Default |
| :--- | :--- | :--- |
| `JWT_SECRET` | High-entropy signing key (minimum 32 bytes / 256 bits) for HMAC SHA-256 tokens. | **Required** (Fails startup if missing) |
| `JWT_EXPIRY_MINUTES` | Access token lifespan in minutes. | Optional (Default: `60`) |
| `JWT_REFRESH_EXPIRY_DAYS` | Refresh token lifespan in days. | Optional (Default: `7`) |
| `ADMIN_BOOTSTRAP_PASSWORD` | Bootstrap password for initial cluster admin account provisioning. | Optional |
| `NODE_NAME` | Human-readable node identifier (e.g. `Node A`). | Required per node |
| `CURRENT_NODE_URL` | Local network bind URL (e.g. `http://localhost:8000`). | Required per node |
| `STORAGE_DIR` | Local path for physical file replicas and SQLite metadata. | Required per node |

### 2. .gitignore & Secret Protection

- `.env` and `.env.*` files are explicitly excluded in `.gitignore` to prevent committing real credentials to version control.
- Only `.env.example` containing non-sensitive placeholder templates is tracked in Git.

---

## Brute-Force Protection & Rate Limiting (Section 33)

DFSS enforces thread-safe rate limiting on the `/auth/login` authentication route to safeguard cluster nodes against brute-force password guessing and denial-of-service attacks.

### Mechanism & Policies
- **Sliding Window Tracking**: Failed login attempts are recorded per client IP / source origin over a configurable sliding time window (`AUTH_RATE_LIMIT_WINDOW_SECONDS`, default: 60s).
- **Temporary Lockout**: If consecutive failed attempts reach the configured threshold (`AUTH_RATE_LIMIT_MAX_ATTEMPTS`, default: 5 attempts), the source origin is temporarily locked out.
- **HTTP 429 Too Many Requests**: Requests during lockout are rejected with `HTTP 429` and include a `Retry-After: <seconds>` header indicating the remaining cooldown duration.
- **Automatic Cooldown & Recovery**: After the cooldown period (`AUTH_RATE_LIMIT_COOLDOWN_SECONDS`, default: 60s) elapses, legitimate authentication requests immediately succeed without manual intervention.
- **Immediate Reset on Success**: A single successful login immediately resets the failure counter for that source.
- **Source Isolation**: Rate limiting is tracked per origin IP/host, ensuring legitimate users on separate addresses are never locked out by attacks on other IPs.

| Configuration Variable | Description | Default |
| :--- | :--- | :--- |
| `AUTH_RATE_LIMIT_MAX_ATTEMPTS` | Maximum failed attempts allowed before triggering lockout. | `5` |
| `AUTH_RATE_LIMIT_COOLDOWN_SECONDS` | Lockout duration in seconds. | `60` |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | Sliding window duration in seconds. | `60` |

---

## JWT_SECRET Rotation Procedure

To maintain security compliance or respond to credential exposure incidents, follow this standardized procedure for rotating `JWT_SECRET`:

### Step 1: Generate a New High-Entropy Secret Key

Generate a cryptographically secure random 32-byte (256-bit) hex or base64 key:

```bash
# Using OpenSSL
openssl rand -hex 32

# Or using Python secrets module
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 2: Update Configuration on All Cluster Nodes

Update the `JWT_SECRET` environment variable or `.env` file across all participating nodes (`Node A`, `Node B`, `Node C`, or deployment container environments):

```bash
JWT_SECRET="<your-newly-generated-32-byte-hex-key>"
```

> **Important**: Ensure all cluster nodes share the **identical** new `JWT_SECRET` so that inter-node RPC and distributed replication requests continue to authenticate seamlessly.

### Step 3: Perform a Rolling Restart of Distributed Nodes

Restart the cluster node processes sequentially (or restart container pods):

```bash
# Terminal 1 - Node A
python nodes/nodeA.py

# Terminal 2 - Node B
python nodes/nodeB.py

# Terminal 3 - Node C
python nodes/nodeC.py
```

### Step 4: Session Invalidation & Re-Authentication

- **User Access & Refresh Tokens**: Any tokens signed with the old secret are immediately invalidated. Subsequent requests bearing old tokens will receive `401 Unauthorized` (`"Token signature is invalid or has been tampered with"`).
- **Client Re-login**: Active users and administrators must re-authenticate via `POST /auth/login` to obtain fresh JWT tokens signed with the new secret.
- **Inter-Node System Tokens**: Each node automatically provisions new `SYSTEM` role tokens signed with the updated key upon restart.

### Step 5: Post-Rotation Health & Sanity Verification

1. **Verify Startup Logs**: Confirm all nodes start cleanly and log:
   ```
   INFO: Authentication & Secrets Configuration Validated.
   ```
2. **Check Node Health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```
3. **Verify Authentication & Operations**:
   - Authenticate via `POST /auth/login` with admin credentials.
   - Perform a test file upload/metadata query to confirm cluster-wide consensus and replication.

---

## Notes

* The system simulates a **distributed file storage system** using multiple nodes running on different ports.
* Each node represents a server in the distributed environment with local storage replication.
* All protected endpoints enforce standard error schemas (`{"detail": ...}`) and distinguish between unauthenticated (`401`) and unauthorized (`403`) access.

