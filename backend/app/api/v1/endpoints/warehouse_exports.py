"""Data warehouse export (M45.S01.T020; Snowflake/BigQuery M48.S01.T007/T008). Prefix /api/v1/warehouse-exports.
Superusers or reports.admin. Secrets are write-only (encrypted at rest, never returned)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.warehouse_export import ExportJob, ExportRun, ExportTarget
from app.services import pat_service as pats
from app.services import warehouse_export_service as wes

router = APIRouter()


def _admin(u):
    if not (u.is_superuser or has_any_permission(u, ("reports.admin",))):
        raise HTTPException(403, "Only report administrators manage warehouse exports.")


@router.get("")
async def overview(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    targets = (await db.execute(select(ExportTarget).order_by(ExportTarget.name))).scalars().all()
    jobs = (await db.execute(select(ExportJob).order_by(ExportJob.dataset))).scalars().all()
    runs = (await db.execute(select(ExportRun).order_by(ExportRun.started_at.desc()).limit(50))).scalars().all()
    return {"datasets": list(wes.DATASETS), "formats": {"csv": "available", "jsonl": "available", "parquet": "NOT_AVAILABLE (pyarrow)"},
            "kinds": {k: "available" for k in ("LOCAL_DIR", "S3", "POSTGRES", "SNOWFLAKE", "BIGQUERY")},
            "targets": [{"id": str(t.id), "name": t.name, "kind": t.kind, "config": {k: v for k, v in t.config.items() if k != "access_key"},
                         "active": t.active, "configured": bool(t.secret), "created_by": t.created_by,
                         "status": (None if t.kind not in wes.CLOUD_KINDS else
                                    "NOT_CONFIGURED" if not t.secret else "APPROVED" if t.config.get("approved_by") else "CONFIGURED")}
                        for t in targets],
            "jobs": [{"id": str(j.id), "target_id": str(j.target_id), "dataset": j.dataset, "format": j.file_format,
                      "every_minutes": j.every_minutes, "watermark": j.watermark.isoformat() if j.watermark else None,
                      "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None} for j in jobs],
            "runs": [{"id": str(r.id), "job_id": str(r.job_id), "status": r.status, "rows": r.rows, "deleted": r.deleted,
                      "files": r.files[-3:], "schema_change": r.schema_change, "error": r.error, "mode": r.mode,
                      "started_at": r.started_at.isoformat()} for r in runs]}


class TargetIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["LOCAL_DIR", "S3", "POSTGRES", "SNOWFLAKE", "BIGQUERY"]
    config: dict = Field(default_factory=dict)
    secret: Optional[str] = Field(None, max_length=10000)
    passphrase: Optional[str] = Field(None, max_length=200)     # Snowflake: an encrypted PKCS#8 key's passphrase


def _seal(kind: str, secret: Optional[str], passphrase: Optional[str]) -> tuple[Optional[str], dict]:
    """Encrypt the credential; for cloud kinds check it parses first and return its public facts."""
    if not secret:
        return None, {}
    if kind == "SNOWFLAKE":
        from cryptography.hazmat.primitives import serialization
        from app.services.warehouse_cloud_writers import sf_fingerprint
        try:
            key = serialization.load_pem_private_key(secret.encode(), password=passphrase.encode() if passphrase else None)
        except Exception:
            raise HTTPException(422, "The Snowflake private key must be a PEM (PKCS#8) RSA key; check the passphrase.") from None
        return wes.encrypt(json.dumps({"private_key": secret, "passphrase": passphrase or None})), {"public_key_fp": sf_fingerprint(key)}
    if kind == "BIGQUERY":
        try:
            sa = json.loads(secret)
            ok = sa.get("type") == "service_account" and sa.get("client_email") and "PRIVATE KEY" in sa.get("private_key", "")
        except Exception:
            ok = False
        if not ok:
            raise HTTPException(422, "The BigQuery credential must be a service-account key JSON file.")
        return wes.encrypt(secret), {"client_email": sa["client_email"]}
    return wes.encrypt(secret), {}


def _check_cloud_config(kind: str, config: dict) -> None:
    from app.services import warehouse_cloud_writers as cw
    try:
        (cw.SnowflakeWriter if kind == "SNOWFLAKE" else cw.BigQueryWriter)(SimpleNamespace(config=config, secret=None))
    except wes.ExportError as e:
        raise HTTPException(422, str(e)) from None


@router.post("/targets", status_code=201)
async def add_target(body: TargetIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    need = {"LOCAL_DIR": ["dir"], "S3": ["endpoint_url", "bucket", "access_key"], "POSTGRES": []}.get(body.kind, [])
    if any(not body.config.get(k) for k in need) or (body.kind in ("S3", "POSTGRES") and not body.secret):
        raise HTTPException(422, f"{body.kind} needs {', '.join(need + (['secret'] if body.kind in ('S3', 'POSTGRES') else []))}.")
    config = {k: v for k, v in body.config.items() if k not in ("approved_by", "approved_at", "public_key_fp", "client_email")}
    if body.kind in wes.CLOUD_KINDS:
        _check_cloud_config(body.kind, config)
    sealed, facts = _seal(body.kind, body.secret, body.passphrase)
    t = ExportTarget(name=body.name, kind=body.kind, config={**config, **facts}, secret=sealed, created_by=current_user.username)
    db.add(t)
    pats.audit(db, current_user, "DW_TARGET_ADDED", "dw_target", body.name, {"kind": body.kind, "credential": bool(sealed)})
    await db.commit()
    return {"id": str(t.id), **facts}


class SecretIn(BaseModel):
    secret: str = Field(min_length=1, max_length=10000)
    passphrase: Optional[str] = Field(None, max_length=200)


async def _target(db, tid) -> ExportTarget:
    t = await db.get(ExportTarget, tid)
    if t is None:
        raise HTTPException(404, "Target not found")
    return t


@router.put("/targets/{tid}/secret")
async def set_secret(tid: uuid.UUID, body: SecretIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Write-only: replaces the stored credential; any earlier live approval is withdrawn."""
    _admin(current_user)
    t = await _target(db, tid)
    t.secret, facts = _seal(t.kind, body.secret, body.passphrase)
    t.config = {**{k: v for k, v in t.config.items() if k not in ("approved_by", "approved_at")}, **facts}
    pats.audit(db, current_user, "DW_TARGET_SECRET_SET", "dw_target", str(t.id), {"kind": t.kind})
    await db.commit()
    return {"configured": True, **facts}


@router.post("/targets/{tid}/approve")
async def approve_target(tid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Second administrator's approval, required before a LIVE (non-simulated) Snowflake/BigQuery sync."""
    _admin(current_user)
    t = await _target(db, tid)
    if t.kind not in wes.CLOUD_KINDS or not t.secret:
        raise HTTPException(422, "Only a configured Snowflake/BigQuery target needs approval.")
    if t.created_by == current_user.username:
        raise HTTPException(403, "A different administrator must approve a target they did not set up.")
    t.config = {**t.config, "approved_by": current_user.username, "approved_at": datetime.now(timezone.utc).isoformat()}
    pats.audit(db, current_user, "DW_TARGET_APPROVED", "dw_target", str(t.id), {"kind": t.kind})
    await db.commit()
    return {"status": "APPROVED"}


@router.post("/targets/{tid}/test")
async def test_target(tid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    t = await _target(db, tid)
    if t.kind not in wes.CLOUD_KINDS:
        raise HTTPException(422, "Connection tests are for Snowflake/BigQuery targets.")
    tid_s = str(t.id)
    try:
        w = wes.writer(t)
        out = {**await w.test_connection(), "mode": w.mode}
    except Exception as e:                      # ExportError / EgressBlocked: shown to the admin, never a 500
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}
    pats.audit(db, current_user, "DW_TARGET_TESTED", "dw_target", tid_s, {"ok": out["ok"]})
    await db.commit()
    return out


class JobIn(BaseModel):
    target_id: uuid.UUID
    dataset: str
    file_format: Literal["csv", "jsonl", "parquet"] = "csv"
    every_minutes: Optional[int] = Field(None, ge=15, le=10080)


@router.post("/jobs", status_code=201)
async def add_job(body: JobIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    if body.dataset not in wes.DATASETS:
        raise HTTPException(422, f"Dataset must be one of {', '.join(wes.DATASETS)}.")
    if body.file_format == "parquet":
        raise HTTPException(422, "Parquet is NOT_AVAILABLE: pyarrow is not installed; use csv or jsonl.")
    if await db.get(ExportTarget, body.target_id) is None:
        raise HTTPException(404, "Target not found")
    j = ExportJob(**body.model_dump(), known_ids=[], schema_cols=[])
    db.add(j)
    pats.audit(db, current_user, "DW_JOB_ADDED", "dw_job", body.dataset, {"target_id": str(body.target_id)})
    await db.commit()
    return {"id": str(j.id)}


@router.post("/jobs/{jid}/run")
async def run(jid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    j = await db.get(ExportJob, jid)
    if j is None:
        raise HTTPException(404, "Job not found")
    jid_s = str(j.id)
    r = await wes.run_job(db, j)
    out = {"status": r.status, "rows": r.rows, "deleted": r.deleted, "error": r.error, "schema_change": r.schema_change,
           "mode": r.mode}
    pats.audit(db, current_user, "DW_JOB_RUN", "dw_job", jid_s, {"status": r.status, "rows": r.rows})
    await db.commit()
    return out


@router.post("/jobs/{jid}/dry-run")
async def dry_run(jid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """The SQL / API requests the next sync would send, with the pending row count; nothing is sent, no data shown."""
    _admin(current_user)
    from app.services import warehouse_cloud_writers as cw
    j = await db.get(ExportJob, jid)
    if j is None:
        raise HTTPException(404, "Job not found")
    t = await _target(db, j.target_id)
    if t.kind not in wes.CLOUD_KINDS:
        raise HTTPException(422, "Dry run is for Snowflake/BigQuery targets.")
    spec = wes.DATASETS[j.dataset]
    params, where = {}, ""
    if j.watermark is not None:
        where = "WHERE (updated_at > :wm OR (updated_at = :wm AND id::text > :wid))"
        params = {"wm": j.watermark, "wid": j.watermark_id or ""}
    pending = (await db.execute(text(f'SELECT count(*) FROM "{spec["table"]}" {where}'), params)).scalar() or 0
    cols = list(spec["columns"])
    try:
        w = (cw.SnowflakeWriter if t.kind == "SNOWFLAKE" else cw.BigQueryWriter)(t)
        steps = await cw.plan(w, j.dataset, cols, min(pending, wes.BATCH))
    except wes.ExportError as e:
        raise HTTPException(422, str(e)) from None
    kinds = cw.erp_types(j.dataset, cols)
    types = {c: (cw.sf_type(kinds[c])[0] if t.kind == "SNOWFLAKE" else cw.bq_type(kinds[c])) for c in cols}
    return {"pending_rows": pending, "batch_rows": min(pending, wes.BATCH), "column_types": types, "plan": steps,
            "configured": bool(t.secret)}
