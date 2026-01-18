from __future__ import annotations

import os
from hashlib import sha256

import pytest


RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"

if not RUN_INTEGRATION:
    pytest.skip("integration tests disabled", allow_module_level=True)

import requests
from minio import Minio


@pytest.mark.skipif(not RUN_INTEGRATION, reason="integration tests disabled")
def test_reference_mode_allows_good_snapshot() -> None:
    gate_url = os.getenv("GATE_URL", "http://localhost:8000")
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    bucket = os.getenv("MINIO_BUCKET", "mig-artifacts")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    client = _minio_client(minio_endpoint, access_key, secret_key)
    _ensure_bucket(client, bucket)
    _wait_for_gate(gate_url)

    snapshot_bytes = b"ref-good-snapshot"
    snapshot_hash = sha256(snapshot_bytes).hexdigest()
    key = "ref/snapshot_good.tar.gz"
    _upload_bytes(client, bucket, key, snapshot_bytes)

    manifest = (
        "app_id: billing\n"
        "env: prod\n"
        "snapshot:\n"
        f"  uri: s3://{bucket}/{key}\n"
        f"  sha256: {snapshot_hash}\n"
        "sync_mode: sync\n"
    )

    response = requests.post(
        f"{gate_url}/api/v1/validate/replication/ref",
        headers={"Authorization": "Bearer dev-token"},
        data=manifest.encode("utf-8"),
        timeout=10,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "ALLOW"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="integration tests disabled")
def test_reference_mode_blocks_bad_hash() -> None:
    gate_url = os.getenv("GATE_URL", "http://localhost:8000")
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    bucket = os.getenv("MINIO_BUCKET", "mig-artifacts")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    client = _minio_client(minio_endpoint, access_key, secret_key)
    _ensure_bucket(client, bucket)
    _wait_for_gate(gate_url)

    snapshot_bytes = b"ref-bad-snapshot"
    key = "ref/snapshot_bad.tar.gz"
    _upload_bytes(client, bucket, key, snapshot_bytes)

    manifest = (
        "app_id: billing\n"
        "env: prod\n"
        "snapshot:\n"
        f"  uri: s3://{bucket}/{key}\n"
        "  sha256: deadbeef\n"
        "sync_mode: sync\n"
    )

    response = requests.post(
        f"{gate_url}/api/v1/validate/replication/ref",
        headers={"Authorization": "Bearer dev-token"},
        data=manifest.encode("utf-8"),
        timeout=10,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "BLOCK"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="integration tests disabled")
def test_reference_mode_blocks_missing_field() -> None:
    gate_url = os.getenv("GATE_URL", "http://localhost:8000")
    _wait_for_gate(gate_url)
    manifest = "env: prod\nsync_mode: sync\n"
    response = requests.post(
        f"{gate_url}/api/v1/validate/replication/ref",
        headers={"Authorization": "Bearer dev-token"},
        data=manifest.encode("utf-8"),
        timeout=10,
    )
    assert response.status_code in {200, 400}
    payload = response.json()
    assert payload["decision"] == "BLOCK"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="integration tests disabled")
def test_reference_mode_blocks_missing_artifact() -> None:
    gate_url = os.getenv("GATE_URL", "http://localhost:8000")
    bucket = os.getenv("MINIO_BUCKET", "mig-artifacts")
    _wait_for_gate(gate_url)
    manifest = (
        "app_id: billing\n"
        "env: prod\n"
        "snapshot:\n"
        f"  uri: s3://{bucket}/ref/does-not-exist.tar.gz\n"
        "  sha256: deadbeef\n"
        "sync_mode: sync\n"
    )
    response = requests.post(
        f"{gate_url}/api/v1/validate/replication/ref",
        headers={"Authorization": "Bearer dev-token"},
        data=manifest.encode("utf-8"),
        timeout=10,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "BLOCK"


def _minio_client(endpoint: str, access_key: str, secret_key: str) -> Minio:
    secure = endpoint.startswith("https://")
    endpoint = endpoint.replace("http://", "").replace("https://", "")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def _upload_bytes(client: Minio, bucket: str, key: str, payload: bytes) -> None:
    client.put_object(bucket, key, data=_to_stream(payload), length=len(payload))


def _to_stream(payload: bytes):
    import io

    return io.BytesIO(payload)


def _wait_for_gate(base_url: str) -> None:
    import time

    deadline = time.time() + 20
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/v1/audit/logs", timeout=2)
            if response.status_code in {200, 401}:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    if last_error:
        raise last_error
