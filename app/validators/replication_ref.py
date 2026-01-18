from __future__ import annotations

import yaml
from pydantic import ValidationError

from app.core.exceptions import MalformedInputError
from app.core.models import Artifacts, Reason, ReplicationReferenceManifest, ValidationOutcome
from app.integrity.artifacts import fetch_s3_object, parse_s3_uri
from app.integrity.hashing import hash_bytes, hashes_match


def validate_replication_reference(manifest_bytes: bytes) -> ValidationOutcome:
    manifest = _parse_manifest(manifest_bytes)
    artifacts = Artifacts()

    if manifest.env not in {"prod", "staging"}:
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[Reason(code="INVALID_MANIFEST", message="env must be prod or staging")],
            artifacts=artifacts,
        )

    if manifest.sync_mode not in {"sync", "async"}:
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[Reason(code="INVALID_MANIFEST", message="sync_mode must be sync or async")],
            artifacts=artifacts,
        )

    try:
        parse_s3_uri(manifest.snapshot.uri)
    except ValueError as exc:
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[Reason(code="INVALID_MANIFEST", message=str(exc))],
            artifacts=artifacts,
        )

    try:
        snapshot_bytes = fetch_s3_object(manifest.snapshot.uri)
    except Exception:
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[Reason(code="ARTIFACT_FETCH_FAILED", message="Failed to fetch snapshot")],
            artifacts=artifacts,
        )

    snapshot_hash = hash_bytes(snapshot_bytes)
    artifacts.computed_hashes.snapshot = snapshot_hash
    if not hashes_match(manifest.snapshot.sha256, snapshot_hash):
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

    if manifest.wal is not None:
        try:
            parse_s3_uri(manifest.wal.uri)
        except ValueError as exc:
            return ValidationOutcome(
                decision="BLOCK",
                reasons=[Reason(code="INVALID_MANIFEST", message=str(exc))],
                artifacts=artifacts,
            )
        try:
            wal_bytes = fetch_s3_object(manifest.wal.uri)
        except Exception:
            return ValidationOutcome(
                decision="BLOCK",
                reasons=[Reason(code="ARTIFACT_FETCH_FAILED", message="Failed to fetch WAL")],
                artifacts=artifacts,
            )
        wal_hash = hash_bytes(wal_bytes)
        if not hashes_match(manifest.wal.sha256, wal_hash):
            return ValidationOutcome(
                decision="BLOCK",
                reasons=[Reason(code="WAL_HASH_MISMATCH", message="WAL integrity verification failed")],
                artifacts=artifacts,
            )

    return ValidationOutcome(decision="ALLOW", reasons=[], artifacts=artifacts)


def _parse_manifest(raw: bytes) -> ReplicationReferenceManifest:
    try:
        parsed = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MalformedInputError("Failed to parse replication manifest", "INVALID_MANIFEST") from exc
    if isinstance(parsed, str) and ":" in parsed:
        try:
            parsed = yaml.safe_load(parsed)
        except yaml.YAMLError:
            pass
    if not isinstance(parsed, dict):
        raise MalformedInputError("replication manifest must be an object", "INVALID_MANIFEST")
    try:
        return ReplicationReferenceManifest(**parsed)
    except ValidationError as exc:
        raise MalformedInputError("replication manifest schema invalid", "INVALID_MANIFEST") from exc
