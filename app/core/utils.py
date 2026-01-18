from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_hex(value: str) -> str:
    return value.strip().lower()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
