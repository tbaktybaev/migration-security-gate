# Migration Security Gate

Control-plane service that validates migration artifacts and returns ALLOW/BLOCK decisions
before deployment or replication. This system protects the migration phase, not runtime.

## Quick Start (Local)

1. Create a virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the service:

```
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

## Docker Compose

```
docker compose up --build
```

## Environment Variables

- `API_TOKEN` (default: `dev-token`)
- `AUDIT_LOG_PATH` (default: `data/audit.log`)
- `MINIO_ENDPOINT` (default: `http://minio:9000`)
- `MINIO_ACCESS_KEY` (default: `minioadmin`)
- `MINIO_SECRET_KEY` (default: `minioadmin`)
- `MINIO_BUCKET` (default: `mig-artifacts`)
- `MINIO_SECURE` (default: `false`)

## API Examples (T1/T2)

### T1 Good (ALLOW)

```
curl -s -X POST http://localhost:8000/api/v1/validate/migration \
  -H "Authorization: Bearer dev-token" \
  -F "migration_manifest=@examples/t1_good/migration_manifest.json" \
  -F "app_config=@examples/t1_good/app-config.yaml"
```

### T1 Bad (BLOCK)

```
curl -s -X POST http://localhost:8000/api/v1/validate/migration \
  -H "Authorization: Bearer dev-token" \
  -F "migration_manifest=@examples/t1_bad/migration_manifest.json" \
  -F "app_config=@examples/t1_bad/app-config.yaml"
```

### T2 Good (ALLOW)

```
curl -s -X POST http://localhost:8000/api/v1/validate/replication \
  -H "Authorization: Bearer dev-token" \
  -F "replication_manifest=@examples/t2_good/replication_manifest.yaml" \
  -F "snapshot=@examples/t2_good/snapshot.tar.gz"
```

### T2 Bad (BLOCK)

```
curl -s -X POST http://localhost:8000/api/v1/validate/replication \
  -H "Authorization: Bearer dev-token" \
  -F "replication_manifest=@examples/t2_bad/replication_manifest.yaml" \
  -F "snapshot=@examples/t2_bad/snapshot.tar.gz"
```

### T2 Reference Mode (ALLOW)

Upload artifacts to MinIO:

```
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb --ignore-existing local/mig-artifacts
mc cp examples/t2_ref_good/snapshot_ref_good.tar.gz local/mig-artifacts/ref/snapshot_ref_good.tar.gz
```

Validate via reference endpoint:

```
curl -s -X POST http://localhost:8000/api/v1/validate/replication/ref \
  -H "Authorization: Bearer dev-token" \
  --data-binary @examples/t2_ref_good/replication_manifest_ref.yaml
```

## UI

Open in browser:

- `http://localhost:8000/` (menu)
- `http://localhost:8000/ui/migration`
- `http://localhost:8000/ui/replication`
- `http://localhost:8000/ui/audit`
- `http://localhost:8000/ui/alerts`

## Audit Logs

Audit log file is stored at `AUDIT_LOG_PATH` (default: `/tmp/audit.log`).

## Logging (Log Service, Variant A)

Structured logs are emitted to stdout for every validation request.
Each log entry includes: `timestamp`, `level`, `service`, `request_id`,
`scenario`, `endpoint`, `decision`, `reason_codes`, `artifact_refs`, and `duration_ms`.

Logical log streams are represented by `log_type`:
- `audit` — decision summary
- `integrity` — hash mismatch / artifact fetch failures
- `policy` — auth/policy/manifest violations

Filtering examples:

```
# by request_id
grep "<request_id>" /tmp/audit.log

# decision=BLOCK (stdout)
kubectl logs deploy/security-gate -n <ns> | grep '"decision":"BLOCK"'

# log_type=integrity (stdout)
kubectl logs deploy/security-gate -n <ns> | grep '"log_type":"integrity"'
```

## Tests

```
pytest -q
```

## Integration Tests (MinIO)

```
make integration-test
```
