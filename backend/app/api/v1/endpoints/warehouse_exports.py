"""Data warehouse export (M45.S01.T020). Prefix /api/v1/warehouse-exports. Superusers or reports.admin."""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
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
            "kinds": {"LOCAL_DIR": "available", "S3": "available", "POSTGRES": "available", **{k: "NOT_CONFIGURED" for k in wes.UNCONFIGURED}},
            "targets": [{"id": str(t.id), "name": t.name, "kind": t.kind, "config": {k: v for k, v in t.config.items() if k != "access_key"},
                         "active": t.active} for t in targets],
            "jobs": [{"id": str(j.id), "target_id": str(j.target_id), "dataset": j.dataset, "format": j.file_format,
                      "every_minutes": j.every_minutes, "watermark": j.watermark.isoformat() if j.watermark else None,
                      "next_run_at": j.next_run_at.isoformat() if j.next_run_at else None} for j in jobs],
            "runs": [{"id": str(r.id), "job_id": str(r.job_id), "status": r.status, "rows": r.rows, "deleted": r.deleted,
                      "files": r.files[-3:], "schema_change": r.schema_change, "error": r.error,
                      "started_at": r.started_at.isoformat()} for r in runs]}


class TargetIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["LOCAL_DIR", "S3", "POSTGRES", "SNOWFLAKE", "BIGQUERY"]
    config: dict = Field(default_factory=dict)
    secret: Optional[str] = Field(None, max_length=1000)


@router.post("/targets", status_code=201)
async def add_target(body: TargetIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    need = {"LOCAL_DIR": ["dir"], "S3": ["endpoint_url", "bucket", "access_key"], "POSTGRES": []}.get(body.kind, [])
    if any(not body.config.get(k) for k in need) or (body.kind in ("S3", "POSTGRES") and not body.secret):
        raise HTTPException(422, f"{body.kind} needs {', '.join(need + (['secret'] if body.kind in ('S3', 'POSTGRES') else []))}.")
    t = ExportTarget(name=body.name, kind=body.kind, config=body.config, secret=wes.encrypt(body.secret), created_by=current_user.username)
    db.add(t)
    pats.audit(db, current_user, "DW_TARGET_ADDED", "dw_target", body.name, {"kind": body.kind})
    await db.commit()
    return {"id": str(t.id)}


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
    await db.commit()
    return {"id": str(j.id)}


@router.post("/jobs/{jid}/run")
async def run(jid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _admin(current_user)
    j = await db.get(ExportJob, jid)
    if j is None:
        raise HTTPException(404, "Job not found")
    r = await wes.run_job(db, j)
    return {"status": r.status, "rows": r.rows, "deleted": r.deleted, "error": r.error, "schema_change": r.schema_change}
