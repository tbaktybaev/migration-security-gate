from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.audit.logger import append_audit_record, ensure_audit_log_ready, read_audit_logs
from app.core.exceptions import ApiError, AuditUnavailableError, InternalError, MalformedInputError
from app.core.logging import log_request_summary
from app.core.models import Artifacts, AuditRecord, Reason, ValidationOutcome, ValidationResult
from app.core.security import verify_bearer_token
from app.core.utils import utc_timestamp
from app.validators.migration import validate_migration
from app.validators.replication import validate_replication
from app.validators.replication_ref import validate_replication_reference


app = FastAPI(title="Migration Security Gate", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
templates = Jinja2Templates(directory="app/ui/templates")


@app.middleware("http")
async def request_summary_logger(request: Request, call_next):
    start = request.scope.get("_start_time")
    if start is None:
        import time

        start = time.time()
        request.scope["_start_time"] = start
    response = await call_next(request)
    try:
        import time

        duration_ms = int((time.time() - start) * 1000)
        decision = getattr(request.state, "decision", None)
        if decision:
            log_request_summary(
                request_id=getattr(request.state, "request_id", "unknown"),
                scenario=getattr(request.state, "scenario", "T1"),
                endpoint=str(request.url.path),
                client=request.headers.get("user-agent"),
                decision=decision,
                reason_codes=getattr(request.state, "reason_codes", []),
                artifact_refs=getattr(request.state, "artifact_refs", []),
                duration_ms=duration_ms,
                log_type=getattr(request.state, "log_type", "audit"),
                level=getattr(request.state, "level", "INFO"),
            )
    except Exception:
        pass
    return response


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    scenario = getattr(request.state, "scenario", "T1")
    result = _build_result(
        decision="BLOCK",
        scenario=scenario,
        reasons=[Reason(code=exc.code, message=exc.message)],
        artifacts=None,
    )
    _attach_request_state(request, result, endpoint=request.url.path, artifact_refs=[])
    _log_result(result)
    return JSONResponse(status_code=exc.http_status, content=_serialize_result(result))


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    scenario = getattr(request.state, "scenario", "T1")
    result = _build_result(
        decision="BLOCK",
        scenario=scenario,
        reasons=[Reason(code="INTERNAL_ERROR", message="Internal server error")],
        artifacts=None,
    )
    _attach_request_state(request, result, endpoint=request.url.path, artifact_refs=[])
    _log_result(result)
    return JSONResponse(status_code=500, content=_serialize_result(result))


@app.post("/api/v1/validate/migration")
async def validate_migration_endpoint(
    request: Request,
    authorization: str | None = Header(default=None),
    migration_manifest: UploadFile = File(...),
    app_config: UploadFile = File(...),
) -> ValidationResult:
    request.state.scenario = "T1"
    _require_audit_ready()
    verify_bearer_token(authorization)
    manifest_bytes = await migration_manifest.read()
    config_bytes = await app_config.read()
    outcome = validate_migration(manifest_bytes, config_bytes)
    result = _result_from_outcome(outcome, scenario="T1")
    _attach_request_state(
        request,
        result,
        endpoint=str(request.url.path),
        artifact_refs=[migration_manifest.filename or "migration_manifest", app_config.filename or "app_config"],
    )
    _log_result(result)
    return result


@app.post("/api/v1/validate/replication")
async def validate_replication_endpoint(
    request: Request,
    authorization: str | None = Header(default=None),
    replication_manifest: UploadFile = File(...),
    snapshot: UploadFile = File(...),
    wal_files: List[UploadFile] | None = File(default=None),
) -> ValidationResult:
    request.state.scenario = "T2"
    _require_audit_ready()
    verify_bearer_token(authorization)
    manifest_bytes = await replication_manifest.read()
    snapshot_bytes = await snapshot.read()
    outcome = validate_replication(manifest_bytes, snapshot_bytes)
    result = _result_from_outcome(outcome, scenario="T2")
    _attach_request_state(
        request,
        result,
        endpoint=str(request.url.path),
        artifact_refs=[replication_manifest.filename or "replication_manifest", snapshot.filename or "snapshot"],
    )
    _log_result(result)
    return result


@app.post("/api/v1/validate/replication/ref")
async def validate_replication_reference_endpoint(
    request: Request,
    authorization: str | None = Header(default=None),
) -> ValidationResult:
    request.state.scenario = "T2"
    _require_audit_ready()
    verify_bearer_token(authorization)
    manifest_bytes = await request.body()
    outcome = validate_replication_reference(manifest_bytes)
    result = _result_from_outcome(outcome, scenario="T2")
    _attach_request_state(
        request,
        result,
        endpoint=str(request.url.path),
        artifact_refs=_extract_ref_artifacts(manifest_bytes),
    )
    _log_result(result)
    return result


@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    limit: Optional[int] = None,
    decision: Optional[str] = None,
    scenario: Optional[str] = None,
) -> List[AuditRecord]:
    return read_audit_logs(limit=limit, decision=decision, scenario=scenario)


@app.get("/")
async def ui_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/ui/migration")
async def ui_migration(request: Request):
    return templates.TemplateResponse("validate_migration.html", {"request": request, "result": None})


@app.post("/ui/migration")
async def ui_migration_submit(
    request: Request,
    migration_manifest: UploadFile = File(...),
    app_config: UploadFile = File(...),
):
    try:
        _require_audit_ready()
        manifest_bytes = await migration_manifest.read()
        config_bytes = await app_config.read()
        outcome = validate_migration(manifest_bytes, config_bytes)
        result = _result_from_outcome(outcome, scenario="T1")
        _attach_request_state(
            request,
            result,
            endpoint=str(request.url.path),
            artifact_refs=[migration_manifest.filename or "migration_manifest", app_config.filename or "app_config"],
        )
        _log_result(result)
    except ApiError as exc:
        result = _build_result(
            decision="BLOCK",
            scenario="T1",
            reasons=[Reason(code=exc.code, message=exc.message)],
            artifacts=None,
        )
        _attach_request_state(request, result, endpoint=str(request.url.path), artifact_refs=[])
        _log_result(result)
    return templates.TemplateResponse("validate_migration.html", {"request": request, "result": result})


@app.get("/ui/replication")
async def ui_replication(request: Request):
    return templates.TemplateResponse("validate_replication.html", {"request": request, "result": None})


@app.post("/ui/replication")
async def ui_replication_submit(
    request: Request,
    replication_manifest: UploadFile | None = File(default=None),
    snapshot: UploadFile | None = File(default=None),
    wal_files: List[UploadFile] | None = File(default=None),
    mode: str = Form("upload"),
    reference_manifest: str | None = Form(default=None),
    reference_manifest_file: UploadFile | None = File(default=None),
):
    try:
        _require_audit_ready()
        if mode != "reference":
            if reference_manifest_file is not None:
                mode = "reference"
            elif reference_manifest and reference_manifest.strip():
                mode = "reference"
        if mode == "reference":
            if reference_manifest_file is not None:
                manifest_bytes = await reference_manifest_file.read()
            else:
                manifest_bytes = (reference_manifest or "").encode("utf-8")
            outcome = validate_replication_reference(manifest_bytes)
        else:
            if replication_manifest is None or snapshot is None:
                raise MalformedInputError("replication manifest and snapshot are required", "INVALID_MANIFEST")
            manifest_bytes = await replication_manifest.read()
            snapshot_bytes = await snapshot.read()
            outcome = validate_replication(manifest_bytes, snapshot_bytes)
        result = _result_from_outcome(outcome, scenario="T2")
        _attach_request_state(
            request,
            result,
            endpoint=str(request.url.path),
            artifact_refs=_ui_artifact_refs(mode, replication_manifest, snapshot, reference_manifest_file),
        )
        _log_result(result)
    except ApiError as exc:
        result = _build_result(
            decision="BLOCK",
            scenario="T2",
            reasons=[Reason(code=exc.code, message=exc.message)],
            artifacts=None,
        )
        _attach_request_state(request, result, endpoint=str(request.url.path), artifact_refs=[])
        _log_result(result)
    return templates.TemplateResponse("validate_replication.html", {"request": request, "result": result})


@app.get("/ui/audit")
async def ui_audit_logs(request: Request):
    logs = list(reversed(read_audit_logs()))
    return templates.TemplateResponse("audit_logs.html", {"request": request, "logs": logs})


@app.get("/ui/alerts")
async def ui_alerts(request: Request):
    logs = list(reversed(read_audit_logs(decision="BLOCK")))
    return templates.TemplateResponse("alerts.html", {"request": request, "logs": logs})


def _result_from_outcome(outcome: ValidationOutcome, scenario: str) -> ValidationResult:
    return _build_result(
        decision=outcome.decision,
        scenario=scenario,
        reasons=outcome.reasons,
        artifacts=outcome.artifacts,
    )


def _build_result(
    decision: str,
    scenario: str,
    reasons: List[Reason],
    artifacts: Optional[object],
) -> ValidationResult:
    return ValidationResult(
        request_id=str(uuid4()),
        decision=decision,
        scenario=scenario,
        reasons=reasons,
        artifacts=artifacts or Artifacts(),
        timestamp=utc_timestamp(),
    )


def _serialize_result(result: ValidationResult) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result.dict()


def _log_result(result: ValidationResult) -> None:
    record = AuditRecord(
        request_id=result.request_id,
        scenario=result.scenario,
        decision=result.decision,
        reasons=[reason.code for reason in result.reasons],
        timestamp=result.timestamp,
    )
    append_audit_record(record)


def _require_audit_ready() -> None:
    try:
        ensure_audit_log_ready()
    except Exception as exc:
        raise AuditUnavailableError() from exc


def _attach_request_state(
    request: Request,
    result: ValidationResult,
    *,
    endpoint: str,
    artifact_refs: list[str],
) -> None:
    request.state.request_id = result.request_id
    request.state.scenario = result.scenario
    request.state.decision = result.decision
    request.state.reason_codes = [reason.code for reason in result.reasons]
    request.state.endpoint = endpoint
    request.state.artifact_refs = artifact_refs
    request.state.log_type = _log_type_for_reasons(result.reasons)
    request.state.level = "WARN" if result.decision == "BLOCK" else "INFO"


def _log_type_for_reasons(reasons: list[Reason]) -> str:
    integrity_codes = {"CONFIG_HASH_MISMATCH", "SNAPSHOT_HASH_MISMATCH", "WAL_HASH_MISMATCH", "ARTIFACT_FETCH_FAILED"}
    policy_codes = {"TLS_DISABLED_PROD", "PUBLIC_PORT_EXPOSED", "SECRETS_REF_MISSING", "SECRETS_INLINE", "AUTH_FAILED", "INVALID_MANIFEST", "AUDIT_UNAVAILABLE"}
    if any(reason.code in integrity_codes for reason in reasons):
        return "integrity"
    if any(reason.code in policy_codes for reason in reasons):
        return "policy"
    return "audit"


def _extract_ref_artifacts(manifest_bytes: bytes) -> list[str]:
    try:
        import yaml

        parsed = yaml.safe_load(manifest_bytes.decode("utf-8"))
        if isinstance(parsed, dict):
            snapshot = parsed.get("snapshot", {}) or {}
            wal = parsed.get("wal", {}) or {}
            refs = []
            if isinstance(snapshot, dict) and isinstance(snapshot.get("uri"), str):
                refs.append(snapshot.get("uri"))
            if isinstance(wal, dict) and isinstance(wal.get("uri"), str):
                refs.append(wal.get("uri"))
            return refs
    except Exception:
        pass
    return []


def _ui_artifact_refs(
    mode: str,
    replication_manifest: UploadFile | None,
    snapshot: UploadFile | None,
    reference_manifest_file: UploadFile | None,
) -> list[str]:
    if mode == "reference":
        return [reference_manifest_file.filename] if reference_manifest_file else ["reference_manifest"]
    refs = []
    if replication_manifest:
        refs.append(replication_manifest.filename or "replication_manifest")
    if snapshot:
        refs.append(snapshot.filename or "snapshot")
    return refs
