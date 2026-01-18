# T2 Good Example

Expected: ALLOW

How to reproduce (API):

curl -s -X POST http://localhost:8000/api/v1/validate/replication \
  -H "Authorization: Bearer dev-token" \
  -F "replication_manifest=@replication_manifest.yaml" \
  -F "snapshot=@snapshot.tar.gz"

How to reproduce (UI):
- Open http://localhost:8000/ui/replication
- Upload the files from this folder
