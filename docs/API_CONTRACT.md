## 8. API Contract (Frozen)

### 8.1 Contract Status

| Attribute | Value |

|-----------|-------|

| **Status** | Frozen for implementation |

| **Audience** | Platform engineers, CI/CD integrators, security reviewers |

| **Out of scope** | Cloud provider actions, deployment execution, secret management |

This API is a **decision service**. It validates artifacts and returns **ALLOW/BLOCK** with reasons.

### 8.2 Global API Principles

1. **Fail-Closed:** Any error → BLOCK
2. **Deterministic:** Same input → same decision
3. **Auditable:** Every request produces an audit record
4. **Synchronous:** Client must wait for a decision
5. **Idempotent by content:** Same artifacts produce the same result

### 8.3 Authentication and Transport (MVP)

| Aspect | Implementation |

|--------|----------------|

| Transport | HTTPS |

| Auth (MVP) | Static API token in header |

| Header format | `Authorization: Bearer <token>` |

| Missing/invalid auth | HTTP 401 + BLOCK decision |

(No mTLS implementation required for MVP; may be simulated later.)

### 8.4 Common Response Model

#### Decision Enum

- `ALLOW`
- `BLOCK`

#### ValidationResult (Canonical Schema)

```json
{
  "request_id": "uuid",
  "decision": "ALLOW | BLOCK",
  "scenario": "T1 | T2",
  "reasons": [
    {
      "code": "STRING_CODE",
      "message": "Human-readable explanation"
    }
  ],
  "artifacts": {
    "computed_hashes": {
      "config": "sha256",
      "snapshot": "sha256"
    }
  },
  "timestamp": "RFC3339"
}
```

**Invariants:**

- `reasons` MUST be non-empty for `BLOCK`
- `reasons` MAY be empty for `ALLOW`

---

### 8.5 Endpoint: Validate Migration (T1)

```
POST /api/v1/validate/migration
Content-Type: multipart/form-data
```

#### Request Parts

| Part name | Type | Required | Description |

|-----------|------|----------|-------------|

| `migration_manifest` | JSON file | YES | Declares intended migration |

| `app_config` | YAML file | YES | Application configuration |

#### migration_manifest.json Schema

```json
{
  "app_id": "string",
  "env": "prod | staging",
  "version": "string",
  "config_sha256": "hex-string"
}
```

**Validation rules:**

- Missing fields → BLOCK
- Unknown `env` → BLOCK

#### app-config.yaml Required Fields

```yaml
tls:
  enabled: true
ports:
  - 443
secrets_ref: "vault://path"
```

**Policy rules (environment-aware):**

- `env=prod` requires `tls.enabled == true`
- No public ports (0.0.0.0) in prod
- `secrets_ref` must exist (string, non-empty)

#### Response Examples

**ALLOW (HTTP 200):**

```json
{
  "decision": "ALLOW",
  "scenario": "T1",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-18T10:30:00Z"
}
```

**BLOCK (HTTP 200):**

```json
{
  "decision": "BLOCK",
  "scenario": "T1",
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "reasons": [
    {
      "code": "CONFIG_HASH_MISMATCH",
      "message": "Computed config hash does not match manifest"
    }
  ],
  "timestamp": "2026-01-18T10:31:00Z"
}
```

---

### 8.6 Endpoint: Validate Replication (T2)

```
POST /api/v1/validate/replication
Content-Type: multipart/form-data
```

#### Request Parts

| Part name | Type | Required | Description |

|-----------|------|----------|-------------|

| `replication_manifest` | YAML file | YES | Replication parameters |

| `snapshot` | tar.gz | YES | Database snapshot |

| `wal_files` | files[] | NO | Fake WAL/binlog files |

#### replication_manifest.yaml Schema

```yaml
source_db: "string"
target_db: "string"
expected_snapshot_hash: "hex-string"
sync_mode: "sync | async"
```

**Validation rules:**

- Snapshot hash mismatch → BLOCK
- Unsupported sync_mode → BLOCK

#### Response Example (BLOCK - Integrity Failure)

```json
{
  "decision": "BLOCK",
  "scenario": "T2",
  "request_id": "550e8400-e29b-41d4-a716-446655440002",
  "reasons": [
    {
      "code": "SNAPSHOT_HASH_MISMATCH",
      "message": "Snapshot integrity verification failed"
    }
  ],
  "timestamp": "2026-01-18T10:32:00Z"
}
```

---

### 8.6.1 Endpoint: Validate Replication (T2) — Reference Mode

```
POST /api/v1/validate/replication/ref
Content-Type: application/json | application/yaml
```

#### Request Body (Reference Manifest)

```yaml
app_id: "billing"
env: "prod"
snapshot:
  uri: "s3://mig-artifacts/billing/snapshot_20260118.tar.gz"
  sha256: "<hex>"
wal:
  uri: "s3://mig-artifacts/billing/wal_20260118.tar.gz"
  sha256: "<hex>"
sync_mode: "async"
policy_version: "2026.01"
change_id: "CHG-12345"
```

**Required fields:** `app_id`, `env`, `snapshot.uri`, `snapshot.sha256`, `sync_mode`

**Rules:**
- Any fetch error → `BLOCK`
- Hash mismatch → `BLOCK`
- Unsupported env/sync_mode → `BLOCK`

Response follows the canonical `ValidationResult`.

### 8.7 Endpoint: Audit Logs

```
GET /api/v1/audit/logs
```

#### Query Parameters

| Param | Description |

|-------|-------------|

| `limit` | Max records to return |

| `decision` | Filter by ALLOW / BLOCK |

| `scenario` | Filter by T1 / T2 |

#### Log Record Model

```json
{
  "request_id": "uuid",
  "scenario": "T1 | T2",
  "decision": "ALLOW | BLOCK",
  "reasons": ["codes"],
  "timestamp": "RFC3339"
}
```

**Invariant:** Audit logs are append-only.

---

### 8.8 Error Semantics

| Condition | HTTP Status | Decision |

|-----------|-------------|----------|

| Invalid auth | 401 | BLOCK |

| Malformed input | 400 | BLOCK |

| Validation failure | 200 | BLOCK |

| Internal error | 500 | BLOCK |

**CRITICAL:** HTTP success does NOT imply ALLOW. The `decision` field is authoritative.

### 8.9 Idempotency and Correlation

- `request_id` generated per request (UUID v4)
- Same artifacts → same decision (deterministic)
- `request_id` must appear in all audit logs

### 8.10 Reason Codes (Enumeration)

| Code | Scenario | Meaning |

|------|----------|---------|

| `SCHEMA_INVALID` | T1/T2 | Required fields missing or malformed |

| `CONFIG_HASH_MISMATCH` | T1 | Computed hash != manifest claim |

| `TLS_DISABLED_PROD` | T1 | TLS disabled in production environment |

| `PUBLIC_PORT_EXPOSED` | T1 | 0.0.0.0 binding detected in prod |

| `SECRETS_REF_MISSING` | T1 | No secrets_ref defined |

| `UNKNOWN_ENV` | T1 | Environment not in allowed list |

| `SNAPSHOT_HASH_MISMATCH` | T2 | Snapshot integrity failed |

| `UNSUPPORTED_SYNC_MODE` | T2 | sync_mode not recognized |

| `PARSE_ERROR` | T1/T2 | Unable to parse artifact |

| `AUTH_FAILED` | T1/T2 | Authentication failed |

| `INTERNAL_ERROR` | T1/T2 | Unhandled internal failure |

| `SECRETS_INLINE` | T1 | Inline secrets detected in config |

| `INVALID_MANIFEST` | T2 | Reference manifest missing/invalid |

| `ARTIFACT_FETCH_FAILED` | T2 | Unable to fetch artifact from store |

| `WAL_HASH_MISMATCH` | T2 | WAL integrity verification failed |

---

## 9. Implementation Readiness Checklist

Before implementation begins, verify:

- [ ] Pydantic schemas match this contract exactly
- [ ] Hashing utilities implemented (SHA-256)
- [ ] Policy engine enforces environment-aware rules
- [ ] All failure paths return BLOCK decision
- [ ] Audit logging is mandatory for every request
- [ ] Reason codes enumerated and documented
- [ ] Error responses conform to contract

---

## 10. Contract Freeze Statement

This API contract is **final** for implementation.

All code must conform to it without reinterpretation.

Any deviation requires explicit approval and contract amendment.

---

## 11. Implementation Todos

- **schemas**: Define Pydantic schemas for manifests, configs, and responses to match the frozen contract
- **hashing**: Implement SHA-256 hashing utilities and snapshot integrity helpers
- **policy-engine**: Enforce environment-aware policy rules (prod vs staging) with reason codes
- **validators**: Build validation pipelines for migration (T1) and replication (T2)
- **audit-logging**: Implement append-only audit logging and retrieval filters
- **api-layer**: Wire API endpoints, auth checks, and error semantics to return ALLOW/BLOCK