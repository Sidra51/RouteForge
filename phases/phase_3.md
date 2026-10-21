# LLM Gateway Platform - Phase 3 Complete Overview

This document provides a comprehensive technical overview of the **LLM Gateway Platform** built during Phase 3. It details the database modifications, API updates, key rotation and deactivation policies, frontend integrations, and validation methods.

---

## 1. System Architecture & Lifecycle Flow

Below is the execution flow demonstrating the lifecycle of API keys, from generation, rename, active state toggling, credential rotation, through soft-deletion.

```mermaid
graph TD
    A[Create Key POST] -->|Generates raw key & hashes it| B[Active API Key]
    B -->|PATCH /activate /deactivate| C[Toggle Status is_active]
    B -->|PATCH /api-keys/{id}| D[Rename key name]
    B -->|POST /rotate| E[Rotate Key]
    E -->|Deactivates & Soft-deletes old key| F[Soft-Deleted Old Key]
    E -->|Creates new key inheriting name & expires_at| G[Active New Key]
    B -->|DELETE /api-keys/{id}| H[Soft-Deleted Key is_active=False, deleted_at=now]
    
    style F fill:#f9d5d5,stroke:#e06666
    style H fill:#f9d5d5,stroke:#e06666
    style G fill:#d5f9d5,stroke:#66d166
```

---

## 2. Directory Structure of Phase 3 Changes

```text
llm-gateway/
│
├── alembic/
│   └── versions/
│       └── ba1f1c43291d_add_deleted_at_to_api_keys.py   # [NEW] Alembic DB schema migration
│
├── app/
│   ├── api/
│   │   ├── api_keys.py           # Updated endpoints for rename, deactivate, rotate, delete
│   │   └── ...
│   │
│   ├── models/
│   │   ├── api_key.py            # Added deleted_at (TIMESTAMP NULL) support for soft delete
│   │   └── ...
│   │
│   ├── schemas/
│   │   ├── api_key.py            # [NEW] APIKeyUpdate & APIKeyUsageSummary (nested metrics)
│   │   └── ...
│   │
│   ├── services/
│   │   ├── api_key_service.py    # Rewrote list, toggle, rename, rotate, and soft-delete logic
│   │   └── ...
│   │
│   └── static/
│       ├── index.html            # Added Rename modal dialog and table columns (Calls, Spend)
│       └── app.js                # Integrated toggles, edit handlers, rotate, and delete UX
│
└── test_key_lifecycle.py         # [NEW] Automated lifecycle integration test script
```

---

## 3. Core SaaS Features Built in Phase 3

### A. Soft-Deletion Policy
Rather than running SQL `DELETE` which wipes telemetry metadata and compromises audits, deleting a key now updates:
* `is_active = False`
* `deleted_at = now()`

Gateway authorize routines (`validate_key()`) ensure keys where `deleted_at` is populated are strictly rejected.

### B. Nested Usage Aggregation (`APIKeyUsageSummary`)
Instead of mixing usage stats directly into the parent model, key responses now embed a nested object:
```json
{
  "id": "uuid-here",
  "name": "Production Key",
  "key_prefix": "gw_live_...",
  "usage": {
    "total_requests": 105,
    "total_tokens": 82000,
    "total_cost": 0.0042
  }
}
```
Aggregations are resolved efficiently inside the service layer using a single `group_by` SQL query.

### C. Rotation with Expiration Carryover
When rotating a key:
1. The old key is soft-deleted (`deleted_at = now()`, `is_active = False`).
2. A new active API key is generated with a fresh raw value.
3. The new key retains the exact custom `name` and original `expires_at` date of the old key.

### D. Active Status Toggles & Renaming
Users can temporarily deactivate keys to pause traffic without losing data, and rename labels instantly to reflect shifts in environment usage.

---

## 4. Verification Suite

The `test_key_lifecycle.py` script automatically verifies the full lifecycle through HTTP API endpoints:
1. Registers a test user.
2. Generates a key with 30-day expiration.
3. Renames the key and lists it to check the nested `usage` schema structure.
4. Deactivates the key and asserts that gateway requests are rejected.
5. Reactivates the key and sends a query to confirm cost/token telemetry updates.
6. Rotates the key and validates expiration and name carryover.
7. Soft-deletes the key and confirms it is hidden from client listings and blocked by the gateway.
