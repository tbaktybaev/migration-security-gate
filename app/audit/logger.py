from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.config import AUDIT_LOG_PATH
from app.core.models import AuditRecord


def append_audit_record(record: AuditRecord) -> None:
    path = Path(AUDIT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_serialize_record(record) + "\n")


def read_audit_logs(
    limit: Optional[int] = None,
    decision: Optional[str] = None,
    scenario: Optional[str] = None,
) -> List[AuditRecord]:
    path = Path(AUDIT_LOG_PATH)
    if not path.exists():
        return []
    records: List[AuditRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                record = AuditRecord(**payload)
            except json.JSONDecodeError:
                continue
            if decision and record.decision != decision:
                continue
            if scenario and record.scenario != scenario:
                continue
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records


def ensure_audit_log_ready() -> None:
    path = Path(AUDIT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8"):
        return


def _serialize_record(record: AuditRecord) -> str:
    if hasattr(record, "model_dump_json"):
        return record.model_dump_json()
    return record.json()
