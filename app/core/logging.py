from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any, Iterable

from app.core.utils import utc_timestamp

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_scenario_var: ContextVar[str | None] = ContextVar("scenario", default=None)
_endpoint_var: ContextVar[str | None] = ContextVar("endpoint", default=None)
_client_var: ContextVar[str | None] = ContextVar("client", default=None)
_artifact_refs_var: ContextVar[list[str]] = ContextVar("artifact_refs", default=[])
_policy_version_var: ContextVar[str | None] = ContextVar("policy_version", default=None)


def set_request_context(
    *,
    request_id: str,
    scenario: str | None = None,
    endpoint: str | None = None,
    client: str | None = None,
) -> None:
    _request_id_var.set(request_id)
    if scenario is not None:
        _scenario_var.set(scenario)
    if endpoint is not None:
        _endpoint_var.set(endpoint)
    if client is not None:
        _client_var.set(client)


def update_request_context(
    *,
    scenario: str | None = None,
    endpoint: str | None = None,
    client: str | None = None,
    artifact_refs: list[str] | None = None,
    policy_version: str | None = None,
) -> None:
    if scenario is not None:
        _scenario_var.set(scenario)
    if endpoint is not None:
        _endpoint_var.set(endpoint)
    if client is not None:
        _client_var.set(client)
    if artifact_refs is not None:
        _artifact_refs_var.set(artifact_refs)
    if policy_version is not None:
        _policy_version_var.set(policy_version)


def log_stdout(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True))


def log_request_summary(
    *,
    request_id: str,
    scenario: str,
    endpoint: str,
    client: str | None,
    decision: str,
    reason_codes: Iterable[str],
    artifact_refs: Iterable[str],
    duration_ms: int,
    log_type: str = "audit",
    level: str = "INFO",
) -> None:
    log_stdout(
        {
            "timestamp": utc_timestamp(),
            "level": level,
            "service": "security-gate",
            "log_type": log_type,
            "request_id": request_id,
            "scenario": scenario,
            "endpoint": endpoint,
            "client": client,
            "decision": decision,
            "reason_codes": list(reason_codes),
            "artifact_refs": list(artifact_refs),
            "duration_ms": duration_ms,
        }
    )


def log_event(
    *,
    decision: str,
    reason_codes: Iterable[str],
    artifact_refs: Iterable[str] | None,
    log_type: str,
    level: str,
    endpoint: str | None = None,
    scenario: str | None = None,
    client: str | None = None,
) -> None:
    log_stdout(
        {
            "timestamp": utc_timestamp(),
            "level": level,
            "service": "security-gate",
            "log_type": log_type,
            "request_id": _request_id_var.get(),
            "scenario": scenario or _scenario_var.get(),
            "endpoint": endpoint or _endpoint_var.get(),
            "client": client or _client_var.get(),
            "decision": decision,
            "reason_codes": list(reason_codes),
            "artifact_refs": list(artifact_refs if artifact_refs is not None else _artifact_refs_var.get()),
        }
    )


def get_policy_version() -> str | None:
    return _policy_version_var.get()
