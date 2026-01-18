from __future__ import annotations

from typing import Any, List

from app.core.models import Reason


def evaluate_migration_policies(env: str, config: dict[str, Any]) -> List[Reason]:
    reasons: List[Reason] = []
    if env == "prod":
        tls = config.get("tls", {})
        if tls.get("enabled") is not True:
            reasons.append(
                Reason(
                    code="TLS_DISABLED_PROD",
                    message="TLS must be enabled for production migrations",
                )
            )
        if _public_ports_exposed(config.get("ports", [])):
            reasons.append(
                Reason(
                    code="PUBLIC_PORT_EXPOSED",
                    message="Public ports (0.0.0.0) are not allowed in prod",
                )
            )
    secrets_ref = config.get("secrets_ref")
    if not isinstance(secrets_ref, str) or not secrets_ref.strip():
        reasons.append(
            Reason(
                code="SECRETS_REF_MISSING",
                message="secrets_ref must be a non-empty string",
            )
        )
    if _contains_inline_secrets(config):
        reasons.append(
            Reason(
                code="SECRETS_INLINE",
                message="Inline secrets are not allowed; use secrets_ref",
            )
        )
    return reasons


def _public_ports_exposed(ports: Any) -> bool:
    if not isinstance(ports, list):
        return False
    for entry in ports:
        if isinstance(entry, dict):
            bind = entry.get("bind") or entry.get("host") or entry.get("address")
            if isinstance(bind, str) and bind.strip() == "0.0.0.0":
                return True
        if isinstance(entry, str) and "0.0.0.0" in entry:
            return True
    return False


def _contains_inline_secrets(payload: Any) -> bool:
    secret_keys = {
        "secret",
        "secrets",
        "password",
        "token",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in secret_keys:
                if isinstance(value, str) and value.strip():
                    return True
            if _contains_inline_secrets(value):
                return True
    elif isinstance(payload, list):
        for item in payload:
            if _contains_inline_secrets(item):
                return True
    return False
