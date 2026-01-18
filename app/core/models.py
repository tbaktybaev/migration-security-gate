from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field


class MigrationManifest(BaseModel):
    app_id: str
    env: str
    version: str
    config_sha256: str


class ReplicationManifest(BaseModel):
    source_db: str
    target_db: str
    expected_snapshot_hash: str
    sync_mode: str


class ReferenceArtifact(BaseModel):
    uri: str
    sha256: str
    signature: Optional[str] = None


class ReplicationReferenceManifest(BaseModel):
    app_id: str
    env: str
    snapshot: ReferenceArtifact
    wal: Optional[ReferenceArtifact] = None
    sync_mode: str
    policy_version: Optional[str] = None
    change_id: Optional[str] = None


class Reason(BaseModel):
    code: str
    message: str


class ComputedHashes(BaseModel):
    config: Optional[str] = None
    snapshot: Optional[str] = None


class Artifacts(BaseModel):
    computed_hashes: ComputedHashes = Field(default_factory=ComputedHashes)


class ValidationResult(BaseModel):
    request_id: str
    decision: str
    scenario: str
    reasons: List[Reason] = Field(default_factory=list)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    timestamp: str


class AuditRecord(BaseModel):
    request_id: str
    scenario: str
    decision: str
    reasons: List[str]
    timestamp: str


@dataclass(frozen=True)
class ValidationOutcome:
    decision: str
    reasons: List[Reason]
    artifacts: Artifacts
