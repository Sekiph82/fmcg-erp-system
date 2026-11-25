"""Sales quotas and forecast management (M43.S01.T007).

A quota is one target for one scope (REP = user id, TEAM = sales_team_id, TERRITORY = sales_region_id,
COMPANY = company id), one period and ONE currency. Totals are only ever summed in the quota's currency; orders and
deals in other currencies are counted separately as excluded, never converted silently.

- Actual: confirmed sales orders (CONFIRMED … INVOICED) dated in the period, net of line discounts, excluding tax.
  REP = orders created by the user; TEAM / TERRITORY / COMPANY by the order's sales_team_id / sales_region_id /
  company_id.
- Forecast: open CRM deals expected to close in the period, by forecast category (stored override, else derived
  from probability: ≥ 90 % COMMIT, ≥ 50 % BEST_CASE, otherwise PIPELINE; OMITTED excluded) plus the probability-
  weighted amount. Projection = actual + commit × w_commit + best case × w_best + pipeline × w_pipeline with
  adjustable assumptions (defaults 1 / 0.5 / 0.1) that are stored with every snapshot.
- Snapshots record the numbers over time (weekly job and on demand) so forecast accuracy can be reviewed later.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMRecord, CRMStatus, SalesQuota, SalesQuotaSnapshot
from app.models.sales import SalesOrder, SOLine, SOStatus

log = logging.getLogger(__name__)
CONFIRMED = (SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING, SOStatus.SHIPPED, SOStatus.INVOICED)
DEFAULT_ASSUMPTIONS = {"commit": 1.0, "best_case": 0.5, "pipeline": 0.1}
CATEGORIES = ("PIPELINE", "BEST_CASE", "COMMIT", "OMITTED")


def category(rec: CRMRecord) -> str:
    if rec.forecast_category:
        return rec.forecast_category
    p = Decimal(str(rec.probability_pct or 0))
    return "COMMIT" if p >= 90 else "BEST_CASE" if p >= 50 else "PIPELINE"


def _order_scope(q: SalesQuota):
    return {"REP": cast(SalesOrder.created_by_id, String) == q.scope_ref,
            "TEAM": SalesOrder.sales_team_id == q.scope_ref, "TERRITORY": SalesOrder.sales_region_id == q.scope_ref,
            "COMPANY": cast(SalesOrder.company_id, String) == q.scope_ref}[q.scope_type]


def _deal_scope(q: SalesQuota):
    return {"REP": CRMRecord.assigned_rep_id == str(q.scope_ref), "TEAM": CRMRecord.sales_team_id == q.scope_ref,
            "TERRITORY": CRMRecord.sales_region_id == q.scope_ref,
            "COMPANY": cast(CRMRecord.company_id, String) == q.scope_ref}[q.scope_type]


async def attainment(db: AsyncSession, q: SalesQuota, assumptions: Optional[dict] = None) -> dict:
    a = {**DEFAULT_ASSUMPTIONS, **{k: float(v) for k, v in (assumptions or {}).items() if k in DEFAULT_ASSUMPTIONS}}
    net = SOLine.ordered_quantity * SOLine.unit_price * (1 - SOLine.discount_pct)
    base = and_(_order_scope(q), SalesOrder.status.in_(CONFIRMED),
                SalesOrder.order_date >= q.period_start, SalesOrder.order_date <= q.period_end)
    rows = dict((await db.execute(select(SalesOrder.currency, func.coalesce(func.sum(net), 0))
                                  .join(SOLine, SOLine.so_id == SalesOrder.id).where(base)
                                  .group_by(SalesOrder.currency))).all())
    actual = Decimal(str(rows.pop(q.currency, 0) or 0))
    excluded_orders = {cur: float(v) for cur, v in rows.items()}
    deals = (await db.execute(select(CRMRecord).where(
        _deal_scope(q), CRMRecord.status == CRMStatus.OPEN, CRMRecord.expected_close_date >= q.period_start,
        CRMRecord.expected_close_date <= q.period_end))).scalars().all()
    cats = {c: Decimal("0") for c in CATEGORIES}
    weighted, excluded_deals = Decimal("0"), 0
    for d in deals:
        if (d.currency or "KES") != q.currency:
            excluded_deals += 1
            continue
        amt = Decimal(str(d.expected_revenue or 0))
        c = category(d)
        cats[c] += amt
        if c != "OMITTED":
            weighted += amt * Decimal(str(d.probability_pct or 0)) / 100
    projected = actual + cats["COMMIT"] * Decimal(str(a["commit"])) + cats["BEST_CASE"] * Decimal(str(a["best_case"])) \
        + cats["PIPELINE"] * Decimal(str(a["pipeline"]))
    target = Decimal(str(q.target_amount))
    return {"quota_id": str(q.id), "currency": q.currency, "target": float(target), "actual": float(actual),
            "commit": float(cats["COMMIT"]), "best_case": float(cats["BEST_CASE"]), "pipeline": float(cats["PIPELINE"]),
            "omitted": float(cats["OMITTED"]), "weighted": float(weighted), "projected": float(projected),
            "attainment_pct": float(actual / target * 100) if target else None,
            "projected_pct": float(projected / target * 100) if target else None,
            "gap": float(target - projected), "assumptions": a,
            "excluded_other_currency": {"orders": excluded_orders, "deals": excluded_deals}}


async def snapshot(db: AsyncSession, q: SalesQuota, assumptions: Optional[dict] = None) -> SalesQuotaSnapshot:
    r = await attainment(db, q, assumptions)
    s = SalesQuotaSnapshot(quota_id=q.id, taken_at=datetime.now(timezone.utc), actual_amount=r["actual"],
                           commit_amount=r["commit"], best_case_amount=r["best_case"], pipeline_amount=r["pipeline"],
                           projected_amount=r["projected"], assumptions=r["assumptions"])
    db.add(s)
    await db.flush()
    return s


async def snapshot_open_quotas(db: AsyncSession) -> int:
    today = date.today()
    quotas = (await db.execute(select(SalesQuota).where(SalesQuota.period_start <= today,
                                                        SalesQuota.period_end >= today - timedelta(days=7)))).scalars().all()
    for q in quotas:
        last = (await db.execute(select(func.max(SalesQuotaSnapshot.taken_at)).where(
            SalesQuotaSnapshot.quota_id == q.id))).scalar_one()
        if last is None or last < datetime.now(timezone.utc) - timedelta(days=7):
            await snapshot(db, q)
    return len(quotas)


async def run_weekly_snapshots(interval: float = 6 * 3600.0) -> None:
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await snapshot_open_quotas(db)
                await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("quota snapshot tick failed")
        await asyncio.sleep(interval)
