# T2 Reference Bad Example

Expected: BLOCK

Expected reason codes:
- SNAPSHOT_HASH_MISMATCH

Upload artifact to MinIO (example using mc):

mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb --ignore-existing local/mig-artifacts
mc cp snapshot_ref_bad.tar.gz local/mig-artifacts/ref/snapshot_ref_bad.tar.gz

Validate via API:

curl -s -X POST http://localhost:8000/api/v1/validate/replication/ref \
  -H "Authorization: Bearer dev-token" \
  --data-binary @replication_manifest_ref.yaml

UI:
- Open http://localhost:8000/ui/replication
- Switch to Reference Mode and submit manifest
