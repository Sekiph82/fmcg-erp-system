"""Sales quotas and forecast (M43.S01.T007). Prefix /api/v1/sales-quotas.

Managers (crm.view_all / crm.edit_all) see every quota; others see their own REP quotas only. Writes need
crm.edit_all. A deal's forecast category may be set by a company-wide CRM editor or the deal's assigned rep.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.crm import CRMRecord, SalesQuota, SalesQuotaSnapshot
from app.models.user import User
from app.services import quota_service as quotas

router = APIRouter()
CURRENCIES = ("KES", "USD", "EUR", "GBP", "UGX", "TZS")


class QuotaIn(BaseModel):
    scope_type: Literal["REP", "TEAM", "TERRITORY", "COMPANY"]
    scope_ref: str = Field(min_length=1, max_length=100)
    scope_label: Optional[str] = Field(None, max_length=200)
    period_type: Literal["MONTH", "QUARTER", "YEAR", "CUSTOM"] = "MONTH"
    period_start: date
    period_end: date
    currency: str = Field("KES", min_length=3, max_length=3)
    target_amount: float = Field(gt=0, le=1e13)
    notes: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _check(self):
        self.currency = self.currency.upper()
        if self.currency not in CURRENCIES:
            raise ValueError(f"currency must be one of {', '.join(CURRENCIES)}")
        if self.period_end < self.period_start:
            raise ValueError("period_end must not be before period_start")
        return self


class Assumptions(BaseModel):
    commit: float = Field(1.0, ge=0, le=1)
    best_case: float = Field(0.5, ge=0, le=1)
    pipeline: float = Field(0.1, ge=0, le=1)


def _manager(u: User) -> bool:
    return u.is_superuser or has_permission(u, "crm.view_all") or has_permission(u, "crm.edit_all")


def _editor(u: User) -> bool:
    return u.is_superuser or has_permission(u, "crm.edit_all")


def _visible(q: SalesQuota, u: User) -> bool:
    return _manager(u) or (q.scope_type == "REP" and q.scope_ref == str(u.id))


def _out(q: SalesQuota) -> dict:
    return {"id": str(q.id), "scope_type": q.scope_type, "scope_ref": q.scope_ref, "scope_label": q.scope_label,
            "period_type": q.period_type, "period_start": q.period_start.isoformat(), "period_end": q.period_end.isoformat(),
            "currency": q.currency, "target_amount": float(q.target_amount), "notes": q.notes}


async def _get(db, quota_id, user) -> SalesQuota:
    q = await db.get(SalesQuota, quota_id)
    if q is None or not _visible(q, user):
        raise HTTPException(404, "Quota not found")
    return q


@router.get("")
async def list_quotas(active_on: Optional[date] = None, commit: float = Query(1.0, ge=0, le=1),
                      best_case: float = Query(0.5, ge=0, le=1), pipeline: float = Query(0.1, ge=0, le=1),
                      db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = select(SalesQuota).order_by(SalesQuota.period_start.desc(), SalesQuota.scope_type)
    if active_on:
        q = q.where(SalesQuota.period_start <= active_on, SalesQuota.period_end >= active_on)
    rows = [x for x in (await db.execute(q.limit(500))).scalars() if _visible(x, current_user)]
    a = {"commit": commit, "best_case": best_case, "pipeline": pipeline}
    return [{**_out(x), "attainment": await quotas.attainment(db, x, a)} for x in rows]


@router.post("", status_code=201)
async def create_quota(body: QuotaIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not _editor(current_user):
        raise HTTPException(403, "Only company-wide CRM editors can set quotas.")
    if (await db.execute(select(SalesQuota.id).where(
            SalesQuota.scope_type == body.scope_type, SalesQuota.scope_ref == body.scope_ref,
            SalesQuota.period_start == body.period_start, SalesQuota.period_end == body.period_end,
            SalesQuota.currency == body.currency))).first():
        raise HTTPException(409, "This scope already has a quota for that period and currency.")
    q = SalesQuota(**body.model_dump(), created_by_id=current_user.id)
    db.add(q)
    await db.flush()
    db.add(AuditLog(actor_id=current_user.id, event_type="SALES_QUOTA_CREATED", module="crm", target_type="sales_quota",
                    target_id=str(q.id), target_name=q.scope_label or q.scope_ref, details=_out(q)))
    await db.commit()
    return _out(q)


@router.put("/{quota_id}")
async def update_quota(quota_id: uuid.UUID, body: QuotaIn, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if not _editor(current_user):
        raise HTTPException(403, "Only company-wide CRM editors can change quotas.")
    q = await _get(db, quota_id, current_user)
    before = _out(q)
    for k, v in body.model_dump().items():
        setattr(q, k, v)
    db.add(AuditLog(actor_id=current_user.id, event_type="SALES_QUOTA_UPDATED", module="crm", target_type="sales_quota",
                    target_id=str(q.id), target_name=q.scope_label or q.scope_ref, before_value=before, after_value=_out(q)))
    await db.commit()
    return _out(q)


@router.delete("/{quota_id}", status_code=204)
async def delete_quota(quota_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if not _editor(current_user):
        raise HTTPException(403, "Only company-wide CRM editors can delete quotas.")
    q = await _get(db, quota_id, current_user)
    db.add(AuditLog(actor_id=current_user.id, event_type="SALES_QUOTA_DELETED", module="crm", target_type="sales_quota",
                    target_id=str(q.id), target_name=q.scope_label or q.scope_ref, before_value=_out(q)))
    await db.delete(q)
    await db.commit()


@router.post("/{quota_id}/snapshots", status_code=201)
async def take_snapshot(quota_id: uuid.UUID, body: Assumptions, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    q = await _get(db, quota_id, current_user)
    s = await quotas.snapshot(db, q, body.model_dump())
    await db.commit()
    return {"id": str(s.id), "taken_at": s.taken_at.isoformat()}


@router.get("/{quota_id}/snapshots")
async def snapshots(quota_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = await _get(db, quota_id, current_user)
    rows = (await db.execute(select(SalesQuotaSnapshot).where(SalesQuotaSnapshot.quota_id == q.id)
                             .order_by(SalesQuotaSnapshot.taken_at))).scalars()
    return [{"taken_at": s.taken_at.isoformat(), "actual": float(s.actual_amount), "commit": float(s.commit_amount),
             "best_case": float(s.best_case_amount), "pipeline": float(s.pipeline_amount),
             "projected": float(s.projected_amount), "assumptions": s.assumptions} for s in rows]


@router.get("/export.csv")
async def export_csv(active_on: Optional[date] = None, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    rows = await list_quotas(active_on, 1.0, 0.5, 0.1, db, current_user)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["scope_type", "scope", "period_start", "period_end", "currency", "target", "actual", "commit",
                "best_case", "pipeline", "projected", "attainment_pct"])
    for r in rows:
        a = r["attainment"]
        w.writerow([r["scope_type"], r["scope_label"] or r["scope_ref"], r["period_start"], r["period_end"], r["currency"],
                    r["target_amount"], a["actual"], a["commit"], a["best_case"], a["pipeline"], round(a["projected"], 2),
                    round(a["attainment_pct"], 1) if a["attainment_pct"] is not None else ""])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sales_quotas.csv"})


class CategoryIn(BaseModel):
    forecast_category: Optional[Literal["PIPELINE", "BEST_CASE", "COMMIT", "OMITTED"]] = None   # None = automatic


@router.put("/deals/{record_id}/forecast-category")
async def set_category(record_id: uuid.UUID, body: CategoryIn, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    rec = await db.get(CRMRecord, record_id)
    if rec is None:
        raise HTTPException(404, "Deal not found")
    if not (_editor(current_user) or rec.assigned_rep_id == str(current_user.id)):
        raise HTTPException(403, "Only the deal's rep or a company-wide CRM editor can change its forecast category.")
    before = rec.forecast_category
    rec.forecast_category = body.forecast_category
    db.add(AuditLog(actor_id=current_user.id, event_type="FORECAST_CATEGORY_SET", module="crm", target_type="crm_record",
                    target_id=str(rec.id), target_name=rec.company_name,
                    before_value={"forecast_category": before}, after_value={"forecast_category": body.forecast_category}))
    await db.commit()
    return {"id": str(rec.id), "forecast_category": quotas.category(rec), "override": rec.forecast_category}
