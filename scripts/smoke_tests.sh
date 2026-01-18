#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
TOKEN=${API_TOKEN:-dev-token}
MINIO_ENDPOINT=${MINIO_ENDPOINT:-http://localhost:9000}
MINIO_BUCKET=${MINIO_BUCKET:-mig-artifacts}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minioadmin}

PORT_FORWARD_PID=""

cleanup() {
  if [ -n "${PORT_FORWARD_PID}" ]; then
    kill "${PORT_FORWARD_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

kubectl -n migsec port-forward svc/minio 9000:9000 >/dev/null 2>&1 &
PORT_FORWARD_PID=$!
sleep 2

python - <<'PY'
import os
from minio import Minio

endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
bucket = os.getenv("MINIO_BUCKET", "mig-artifacts")
secure = endpoint.startswith("https://")
endpoint = endpoint.replace("http://", "").replace("https://", "")

client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
if not client.bucket_exists(bucket):
    client.make_bucket(bucket)

client.fput_object(bucket, "ref/snapshot_ref_good.tar.gz", "examples/t2_ref_good/snapshot_ref_good.tar.gz")
client.fput_object(bucket, "ref/snapshot_ref_bad.tar.gz", "examples/t2_ref_bad/snapshot_ref_bad.tar.gz")
PY

python - <<'PY'
import json
import os
import subprocess
import sys

base = os.getenv("BASE_URL", "http://localhost:8000")
token = os.getenv("API_TOKEN", "dev-token")


def run_curl(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def assert_decision(name, payload, expected):
    decision = payload.get("decision")
    if decision != expected:
        print(f"{name}: FAIL expected {expected}, got {decision}")
        sys.exit(1)
    print(f"{name}: PASS ({decision})")


payload = run_curl([
    "curl", "-s", "-X", "POST", f"{base}/api/v1/validate/migration",
    "-H", f"Authorization: Bearer {token}",
    "-F", "migration_manifest=@examples/t1_good/migration_manifest.json",
    "-F", "app_config=@examples/t1_good/app-config.yaml",
])
assert_decision("T1 good", payload, "ALLOW")

payload = run_curl([
    "curl", "-s", "-X", "POST", f"{base}/api/v1/validate/migration",
    "-H", f"Authorization: Bearer {token}",
    "-F", "migration_manifest=@examples/t1_bad/migration_manifest.json",
    "-F", "app_config=@examples/t1_bad/app-config.yaml",
])
assert_decision("T1 bad", payload, "BLOCK")

payload = run_curl([
    "curl", "-s", "-X", "POST", f"{base}/api/v1/validate/replication/ref",
    "-H", f"Authorization: Bearer {token}",
    "--data-binary", "@examples/t2_ref_good/replication_manifest_ref.yaml",
])
assert_decision("T2 ref good", payload, "ALLOW")

payload = run_curl([
    "curl", "-s", "-X", "POST", f"{base}/api/v1/validate/replication/ref",
    "-H", f"Authorization: Bearer {token}",
    "--data-binary", "@examples/t2_ref_bad/replication_manifest_ref.yaml",
])
assert_decision("T2 ref bad", payload, "BLOCK")

print("SMOKE TESTS PASS")
PY
