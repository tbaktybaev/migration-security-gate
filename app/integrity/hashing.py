from app.core.utils import compute_sha256, normalize_hex


def hash_bytes(data: bytes) -> str:
    return compute_sha256(data)


def hashes_match(expected: str, actual: str) -> bool:
    return normalize_hex(expected) == normalize_hex(actual)
