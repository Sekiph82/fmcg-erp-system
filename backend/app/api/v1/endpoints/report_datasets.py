"""M47.S01.T011 report-builder datasets (upload CSV, blend with a catalog source). Prefix /api/v1/report-datasets.
Reading needs reports.view; creating/changing needs reports.create or reports.admin."""
from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m47_datasets import ReportDataset
from app.services import report_dataset_service as rds

router = APIRouter(dependencies=[Depends(require_any_permission(("reports.view",)))])
WRITE = ("reports.create", "reports.admin")


def _out(d: ReportDataset) -> dict:
    return {"id": str(d.id), "key": d.key, "name": d.name, "columns": d.columns, "row_count": d.row_count,
            "join": {"source": d.join_source, "local": d.join_local, "remote": d.join_remote} if d.join_source else None,
            "created_by": d.created_by, "source_key": f"ds:{d.key}"}


class DatasetIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    csv: str = Field(max_length=5_000_000)
    join_source: Optional[str] = None
    join_local: Optional[str] = None
    join_remote: Optional[str] = None


class JoinIn(BaseModel):
    join_source: Optional[str] = None
    join_local: Optional[str] = None
    join_remote: Optional[str] = None


@router.get("")
async def datasets(db: AsyncSession = Depends(get_db)):
    return [_out(d) for d in (await db.execute(select(ReportDataset).order_by(ReportDataset.name))).scalars()]


@router.post("", status_code=201)
async def create(b: DatasetIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, WRITE)):
        raise HTTPException(403, "Creating datasets needs report create rights.")
    try:
        cols, rows = rds.parse_csv(b.csv)
        key = re.sub(r"[^a-z0-9_]", "_", b.name.lower()).strip("_")[:30] or "dataset"
        if (await db.execute(select(ReportDataset.id).where(ReportDataset.key == key))).first():
            key = f"{key[:30]}_{uuid.uuid4().hex[:6]}"
        d = ReportDataset(key=key, name=b.name.strip(), columns=cols, rows=rows, row_count=len(rows), created_by=user.username)
        rds.validate_join(d, b.join_source, b.join_local, b.join_remote)
    except rds.DatasetError as e:
        raise HTTPException(422, str(e))
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return _out(d)


@router.patch("/{did}/join")
async def set_join(did: uuid.UUID, b: JoinIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, WRITE)):
        raise HTTPException(403, "Changing datasets needs report create rights.")
    d = await db.get(ReportDataset, did)
    if d is None:
        raise HTTPException(404, "Not found")
    try:
        rds.validate_join(d, b.join_source, b.join_local, b.join_remote)
    except rds.DatasetError as e:
        raise HTTPException(422, str(e))
    await db.commit()
    await db.refresh(d)
    return _out(d)


@router.get("/{did}/preview")
async def preview(did: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    d = await db.get(ReportDataset, did)
    if d is None:
        raise HTTPException(404, "Not found")
    return await rds.report_rows(db, d.key, user, [], [], 50, 0)


@router.delete("/{did}")
async def delete(did: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not (user.is_superuser or has_any_permission(user, WRITE)):
        raise HTTPException(403, "Deleting datasets needs report create rights.")
    d = await db.get(ReportDataset, did)
    if d is None:
        raise HTTPException(404, "Not found")
    await db.delete(d)
    await db.commit()
    return {"ok": True}
