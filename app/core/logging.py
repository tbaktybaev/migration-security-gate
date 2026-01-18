from __future__ import annotations

import json
from typing import Any, Iterable

from app.core.utils import utc_timestamp


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
    request_id: str | None,
    scenario: str,
    endpoint: str,
    client: str | None,
    decision: str,
    reason_codes: Iterable[str],
    artifact_refs: Iterable[str],
    log_type: str,
    level: str,
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
        }
    )
