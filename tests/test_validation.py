from __future__ import annotations

import json
from hashlib import sha256

from app.validators.migration import validate_migration
from app.validators.replication import validate_replication


def test_migration_allows_valid_config() -> None:
    config = b"""tls:\n  enabled: true\nports:\n  - 443\nsecrets_ref: \"vault://path\"\n"""
    manifest = {
        "app_id": "svc",
        "env": "prod",
        "version": "1",
        "config_sha256": sha256(config).hexdigest(),
    }
    outcome = validate_migration(json.dumps(manifest).encode("utf-8"), config)
    assert outcome.decision == "ALLOW"


def test_migration_blocks_tampered_config() -> None:
    config = b"""tls:\n  enabled: true\nports:\n  - 443\nsecrets_ref: \"vault://path\"\n"""
    manifest = {
        "app_id": "svc",
        "env": "prod",
        "version": "1",
        "config_sha256": "deadbeef",
    }
    outcome = validate_migration(json.dumps(manifest).encode("utf-8"), config)
    assert outcome.decision == "BLOCK"


def test_replication_allows_valid_snapshot() -> None:
    snapshot = b"snapshot-ok"
    manifest = (
        "source_db: src\n"
        "target_db: tgt\n"
        f"expected_snapshot_hash: {sha256(snapshot).hexdigest()}\n"
        "sync_mode: sync\n"
    ).encode("utf-8")
    outcome = validate_replication(manifest, snapshot)
    assert outcome.decision == "ALLOW"


def test_replication_blocks_bad_snapshot() -> None:
    snapshot = b"snapshot-bad"
    manifest = (
        "source_db: src\n"
        "target_db: tgt\n"
        "expected_snapshot_hash: deadbeef\n"
        "sync_mode: sync\n"
    ).encode("utf-8")
    outcome = validate_replication(manifest, snapshot)
    assert outcome.decision == "BLOCK"


def test_missing_required_field_blocks() -> None:
    config = b"""tls:\n  enabled: true\nports:\n  - 443\nsecrets_ref: \"vault://path\"\n"""
    manifest = {"app_id": "svc", "env": "prod", "version": "1"}
    try:
        validate_migration(json.dumps(manifest).encode("utf-8"), config)
    except Exception:
        assert True
    else:
        assert False


def test_invalid_format_blocks() -> None:
    config = b"::invalid-yaml::"
    manifest = (
        "source_db: src\n"
        "target_db: tgt\n"
        "expected_snapshot_hash: deadbeef\n"
        "sync_mode: sync\n"
    ).encode("utf-8")
    outcome = validate_replication(manifest, config)
    assert outcome.decision == "BLOCK"
