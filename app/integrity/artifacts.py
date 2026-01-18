from __future__ import annotations

from dataclasses import dataclass

from minio import Minio
from minio.error import S3Error

from app.core.config import (
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)


@dataclass(frozen=True)
class S3Location:
    bucket: str
    key: str


def fetch_s3_object(uri: str) -> bytes:
    location = parse_s3_uri(uri)
    client = _minio_client()
    try:
        response = client.get_object(location.bucket, location.key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as exc:
        raise RuntimeError("Failed to fetch artifact from MinIO") from exc


def parse_s3_uri(uri: str) -> S3Location:
    if not isinstance(uri, str) or not uri.startswith("s3://"):
        raise ValueError("URI must start with s3://")
    path = uri[len("s3://") :]
    if "/" not in path:
        raise ValueError("URI must include bucket and key")
    bucket, key = path.split("/", 1)
    if not bucket or not key:
        raise ValueError("URI must include bucket and key")
    return S3Location(bucket=bucket, key=key)


def _minio_client() -> Minio:
    endpoint = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
    return Minio(endpoint, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
