# T1 Good Example

Expected: ALLOW

How to reproduce (API):

curl -s -X POST http://localhost:8000/api/v1/validate/migration \
  -H "Authorization: Bearer dev-token" \
  -F "migration_manifest=@migration_manifest.json" \
  -F "app_config=@app-config.yaml"

How to reproduce (UI):
- Open http://localhost:8000/ui/migration
- Upload the two files from this folder
