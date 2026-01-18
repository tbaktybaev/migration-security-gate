from __future__ import annotations

import yaml
from pydantic import ValidationError

from app.core.exceptions import MalformedInputError
from app.core.logging import log_event
from app.core.models import Artifacts, Reason, ReplicationManifest, ValidationOutcome
from app.integrity.hashing import hash_bytes, hashes_match


def validate_replication(manifest_bytes: bytes, snapshot_bytes: bytes) -> ValidationOutcome:
    manifest = _parse_manifest(manifest_bytes)

    computed_hash = hash_bytes(snapshot_bytes)
    artifacts = Artifacts()
    artifacts.computed_hashes.snapshot = computed_hash

    if not hashes_match(manifest.expected_snapshot_hash, computed_hash):
        log_event(
            decision="BLOCK",
            reason_codes=["SNAPSHOT_HASH_MISMATCH"],
            artifact_refs=None,
            log_type="integrity",
            level="WARN",
        )
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[
                Reason(
                    code="SNAPSHOT_HASH_MISMATCH",
                    message="Snapshot integrity verification failed",
                )
            ],
            artifacts=artifacts,
        )

    if manifest.sync_mode not in {"sync", "async"}:
        log_event(
            decision="BLOCK",
            reason_codes=["UNSUPPORTED_SYNC_MODE"],
            artifact_refs=None,
            log_type="policy",
            level="WARN",
        )
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[
                Reason(
                    code="UNSUPPORTED_SYNC_MODE",
                    message="sync_mode must be sync or async",
                )
            ],
            artifacts=artifacts,
        )

    return ValidationOutcome(decision="ALLOW", reasons=[], artifacts=artifacts)


def _parse_manifest(raw: bytes) -> ReplicationManifest:
    try:
        parsed = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MalformedInputError("Failed to parse replication_manifest YAML", "PARSE_ERROR") from exc
    if not isinstance(parsed, dict):
        raise MalformedInputError("replication_manifest must be a YAML object", "SCHEMA_INVALID")
    try:
        return ReplicationManifest(**parsed)
    except ValidationError as exc:
        raise MalformedInputError("replication_manifest schema invalid", "SCHEMA_INVALID") from exc
