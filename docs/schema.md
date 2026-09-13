# Distributed File Storage System (DFSS) Storage Schemas

This document defines the storage and data schemas utilized across DFSS nodes, encompassing distributed file metadata (Section 19) and user authentication & authorization storage (Section 26).

---

## 1. Authentication & Authorization Schema (Section 26)

The user storage table (`users`) persists user identity, role access levels, and cryptographic password hashes.

### 1.1 Database Engine
- **Engine**: SQLite 3 (`metadata.db` located under `$STORAGE_DIR` / node storage root).
- **Table Name**: `users`

### 1.2 Table Definition (`users`)

```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'USER',
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

### 1.3 Field Specifications

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique identifier (UUID4 format). |
| `username` | `TEXT` | `UNIQUE NOT NULL` | Unique account handle; case-sensitive identifier. |
| `hashed_password` | `TEXT` | `NOT NULL` | Cryptographic bcrypt hash (`$2b$12$...`). Plaintext is never stored. |
| `role` | `TEXT` | `NOT NULL DEFAULT 'USER'` | Authorization role: `'USER'`, `'ADMIN'`, or `'SYSTEM'`. |
| `created_at` | `TEXT` | `NOT NULL` | ISO 8601 UTC timestamp of creation (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`). |
| `is_active` | `INTEGER` | `NOT NULL DEFAULT 1` | Account status flag (`1` for active, `0` for deactivated/suspended). |

---

## 2. Distributed File Metadata Schema (Section 19)

File metadata tracks physical file chunks, replica placement across cluster nodes, and synchronization health.

### 2.1 Schema Overview

| Field | Type | Description |
| :--- | :--- | :--- |
| `file_id` | `TEXT` | Unique deterministic file hash identifier (e.g. `file-5a543a70`). |
| `name` | `TEXT` | Original filename as uploaded. |
| `size` | `INTEGER` | File size in bytes. |
| `replicas` | `JSON / ARRAY` | List of cluster nodes holding verified physical replicas (e.g. `["Node A", "Node B"]`). |
| `status` | `TEXT` | Replication state: `'REPLICATED'` (≥ 2 replicas) or `'SYNCING'` (< 2 replicas). |
| `updated_at` | `TEXT` | ISO 8601 UTC timestamp of last replication or mutation. |

---

## 3. Schema Invariants & Security Principles
1. **Never Store Plaintext Credentials**: Only cryptographically salted hashes produced via `hash_password()` are accepted and written to `users.hashed_password`.
2. **Unique Username Enforcement**: Database-level unique constraint (`idx_users_username`) guarantees no duplicate account creation across nodes.
3. **No Circular Schema Dependencies**: Database access and Pydantic validation are decoupled into separate modular layers (`app.models.user_model` and `app.services.user_storage`).
