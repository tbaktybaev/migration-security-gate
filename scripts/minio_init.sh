#!/usr/bin/env bash
set -euo pipefail

MINIO_ENDPOINT=${MINIO_ENDPOINT:-http://localhost:9000}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}
BUCKET=${MINIO_BUCKET:-mig-artifacts}

mc alias set local "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc mb --ignore-existing local/"$BUCKET"
