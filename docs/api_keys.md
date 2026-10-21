# LLM Gateway - API Key Lifecycle Management

This document details how developer API keys are securely generated, validated, renamed, rotated, and soft-deleted.

---

## 1. Key Creation & Formatting
* **Format**: Issued credentials start with the public identifier prefix `gw_live_` followed by 48 hexadecimal characters (24 bytes of entropy).
* **Validation**: Valid keys are looked up in the database using their SHA-256 hash value to prevent database exposure.
* **Expiration**: Keys can optionally be given an expiration limit in days. Once expired, the key is set to inactive.

---

## 2. Status Toggles & Renaming
* **Deactivation**: Developers can deactivate keys via `PATCH /api-keys/{id}/deactivate` to temporarily pause traffic. Active status can be restored at any time.
* **Renaming**: Custom labels can be updated via `PATCH /api-keys/{id}` to distinguish where keys are deployed (e.g. "Staging Server" vs. "Production Frontend").

---

## 3. Rotation Policy
To recover from compromised credentials:
1. The old key is immediately disabled and soft-deleted.
2. A new active API key is generated.
3. The new key carries over the exact **custom name** and **original expiration limit** of the old key to prevent configuration resets.

---

## 4. Soft-Deletion Policy
* **Behavior**: Deleting a key sets `is_active = False` and `deleted_at = now()`.
* **Telemetry Protection**: The row is kept in the database so that historical usage logs (`usage_logs`) remain linked to the key for correct dashboard spend totals and auditing.
* **Filter**: Soft-deleted keys are filtered out of all query list endpoints and authorization checks.

---

## 5. Nested Usage Structure
Each key returned in the list schema embeds its consumption stats under a `usage` sub-object:
```json
{
  "id": "uuid-here",
  "name": "Production Frontend Key",
  "key_prefix": "gw_live_abcd",
  "is_active": true,
  "usage": {
    "total_requests": 150,
    "total_tokens": 42000,
    "total_cost": 0.00125
  }
}
```
Aggregations are computed using SQL `group_by` aggregates for high-performance updates.
