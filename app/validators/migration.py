from __future__ import annotations

import json
from typing import Any

import yaml
from pydantic import ValidationError

from app.core.exceptions import MalformedInputError
from app.core.logging import log_event
from app.core.models import Artifacts, MigrationManifest, Reason, ValidationOutcome
from app.integrity.hashing import hash_bytes, hashes_match
from app.policies.policy_engine import evaluate_migration_policies


def validate_migration(manifest_bytes: bytes, config_bytes: bytes) -> ValidationOutcome:
    manifest = _parse_manifest(manifest_bytes)
    config = _parse_config(config_bytes)

    computed_hash = hash_bytes(config_bytes)
    artifacts = Artifacts()
    artifacts.computed_hashes.config = computed_hash

    if not hashes_match(manifest.config_sha256, computed_hash):
        log_event(
            request_id=None,
            scenario="T1",
            endpoint="/api/v1/validate/migration",
            client=None,
            decision="BLOCK",
            reason_codes=["CONFIG_HASH_MISMATCH"],
            artifact_refs=[],
            log_type="integrity",
            level="WARN",
        )
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[
                Reason(
                    code="CONFIG_HASH_MISMATCH",
                    message="Computed config hash does not match manifest",
                )
            ],
            artifacts=artifacts,
        )

    if manifest.env not in {"prod", "staging"}:
        log_event(
            request_id=None,
            scenario="T1",
            endpoint="/api/v1/validate/migration",
            client=None,
            decision="BLOCK",
            reason_codes=["UNKNOWN_ENV"],
            artifact_refs=[],
            log_type="policy",
            level="WARN",
        )
        return ValidationOutcome(
            decision="BLOCK",
            reasons=[
                Reason(
                    code="UNKNOWN_ENV",
                    message="Environment must be prod or staging",
                )
            ],
            artifacts=artifacts,
        )

    policy_reasons = evaluate_migration_policies(manifest.env, config)
    if policy_reasons:
        log_event(
            request_id=None,
            scenario="T1",
            endpoint="/api/v1/validate/migration",
            client=None,
            decision="BLOCK",
            reason_codes=[reason.code for reason in policy_reasons],
            artifact_refs=[],
            log_type="policy",
            level="WARN",
        )
        return ValidationOutcome(
            decision="BLOCK",
            reasons=policy_reasons,
            artifacts=artifacts,
        )

    return ValidationOutcome(decision="ALLOW", reasons=[], artifacts=artifacts)


def _parse_manifest(raw: bytes) -> MigrationManifest:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MalformedInputError("Failed to parse migration_manifest JSON", "PARSE_ERROR") from exc
    try:
        return MigrationManifest(**data)
    except ValidationError as exc:
        raise MalformedInputError("migration_manifest schema invalid", "SCHEMA_INVALID") from exc


def _parse_config(raw: bytes) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise MalformedInputError("Failed to parse app_config YAML", "PARSE_ERROR") from exc
    if not isinstance(parsed, dict):
        raise MalformedInputError("app_config must be a YAML object", "SCHEMA_INVALID")
    if "tls" not in parsed or "ports" not in parsed or "secrets_ref" not in parsed:
        raise MalformedInputError("app_config missing required fields", "SCHEMA_INVALID")
    return parsed
