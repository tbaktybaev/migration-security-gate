# T1 Bad Example

Expected: BLOCK

Expected reason codes (one or more):
- CONFIG_HASH_MISMATCH
- TLS_DISABLED_PROD
- PUBLIC_PORT_EXPOSED
- SECRETS_REF_MISSING

How to reproduce (API):

curl -s -X POST http://localhost:8000/api/v1/validate/migration \
  -H "Authorization: Bearer dev-token" \
  -F "migration_manifest=@migration_manifest.json" \
  -F "app_config=@app-config.yaml"

How to reproduce (UI):
- Open http://localhost:8000/ui/migration
- Upload the two files from this folder
