"""M36.S05.T001 customer journey attribution: source -> lead -> opportunity -> order -> repeat purchase.

Assumptions (stated in the report):
- Journey = a CRM record created in the period. Its touches, oldest first, are the website-form submissions
  linked to it (utm_source / utm_campaign, or 'website form'); without any, the record's own source
  (source_type + source_detail); without that, 'Manual'.
- Identity joins are explicit only: form submission -> CRM record -> its linked customer. No matching of
  people by e-mail or phone across records, so no consent question arises from the joins.
- Orders = the linked customer's confirmed sales orders (not draft, not cancelled; of the same company when a
  company is chosen) dated on or after the record's creation (Nairobi date) and up to the period end.
  A customer belongs to its OLDEST CRM record ever (not only this period's), so orders are never credited to
  two journeys across reports. Repeat purchase = 2 or more such orders. Revenue is net of tax:
  quantity x unit price x (1 - discount), discount stored as a fraction.
- Models: first touch, last touch, linear (equal split over distinct touches). Revenue is per currency and
  never summed across currencies. The report reconciles: credited revenue == revenue of the orders counted.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMLeadSubmission, CRMRecord, CRMRecordType, CRMStatus
from app.models.sales import SalesOrder, SOLine, SOStatus

NAIROBI = ZoneInfo("Africa/Nairobi")

MODELS = ("first", "last", "linear")
_EXCLUDED = (SOStatus.DRAFT, SOStatus.CANCELLED)


def _label_submission(s: CRMLeadSubmission) -> str:
    src = (s.utm_source or "").strip().lower()
    camp = (s.utm_campaign or "").strip()
    return f"{src or 'website form'}" + (f" / {camp}" if camp else "")


def _label_record(r: CRMRecord) -> str:
    st = getattr(r.source_type, "value", r.source_type)
    if not st or st == "MANUAL":
        return "Manual" + (f": {r.source_detail}" if r.source_detail else "")
    return st.replace("_", " ").title() + (f": {r.source_detail}" if r.source_detail else "")


def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def report(db: AsyncSession, date_from: date, date_to: date, model: str = "first",
                 company_id: Optional[str] = None) -> dict:
    if model not in MODELS:
        raise ValueError("model must be first, last or linear")
    start = datetime.combine(date_from, time.min, timezone.utc)
    end = datetime.combine(date_to, time.max, timezone.utc)
    in_period = [CRMRecord.created_at >= start, CRMRecord.created_at <= end]
    if company_id:
        in_period.append(CRMRecord.company_id == company_id)
    records = (await db.execute(select(CRMRecord).where(*in_period)
                                .order_by(CRMRecord.created_at, CRMRecord.id))).scalars().all()
    period_ids = select(CRMRecord.id).where(*in_period).scalar_subquery()  # no huge IN lists

    subs = defaultdict(list)
    for s in (await db.execute(select(CRMLeadSubmission).where(CRMLeadSubmission.crm_record_id.in_(period_ids))
                               .order_by(CRMLeadSubmission.received_at))).scalars():
        subs[s.crm_record_id].append(s)

    def touches(r: CRMRecord) -> list[str]:
        seen, out = set(), []
        for label in ([_label_submission(s) for s in subs[r.id]] or [_label_record(r)]):
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out

    # one journey per customer, ever: the customer's oldest CRM record (of this company, if one is chosen)
    period_customers = select(CRMRecord.assigned_customer_id).where(
        *in_period, CRMRecord.assigned_customer_id.is_not(None)).scalar_subquery()
    oldest = select(CRMRecord.assigned_customer_id, CRMRecord.id).where(
        CRMRecord.assigned_customer_id.in_(period_customers),
        *([CRMRecord.company_id == company_id] if company_id else [])
    ).order_by(CRMRecord.assigned_customer_id, CRMRecord.created_at, CRMRecord.id).distinct(CRMRecord.assigned_customer_id)
    owner_id = dict((await db.execute(oldest)).all())
    by_id = {r.id: r for r in records}
    owner_of = {cid: by_id[rid] for cid, rid in owner_id.items() if rid in by_id}  # owner must be in this period

    orders_by_customer = defaultdict(list)
    counted: list = []
    value = func.sum(SOLine.ordered_quantity * SOLine.unit_price * (1 - SOLine.discount_pct))
    oq = (select(SalesOrder.id, SalesOrder.customer_id, SalesOrder.order_date, SalesOrder.currency, value)
          .join(SOLine, SOLine.so_id == SalesOrder.id)
          .where(SalesOrder.customer_id.in_(period_customers), SalesOrder.status.not_in(_EXCLUDED),
                 SalesOrder.order_date <= date_to)
          .group_by(SalesOrder.id))
    if company_id:
        oq = oq.where(SalesOrder.company_id == company_id)
    for oid, cid, odate, ccy, val in (await db.execute(oq)).all():
        owner = owner_of.get(cid)
        if owner is not None and odate >= owner.created_at.astimezone(NAIROBI).date():
            orders_by_customer[cid].append((oid, ccy, Decimal(val or 0)))
            counted.append(oid)

    by_source: dict[str, dict] = {}
    total_revenue: dict[str, Decimal] = defaultdict(Decimal)

    def row(label: str) -> dict:
        z = Decimal(0)
        return by_source.setdefault(label, {"source": label, "journeys": z, "leads": z, "opportunities": z, "won": z,
                                            "customers_with_orders": z, "orders": z, "repeat_customers": z,
                                            "revenue": defaultdict(Decimal)})

    for r in records:
        t = touches(r)
        weights = ({t[0]: Decimal(1)} if model == "first" else {t[-1]: Decimal(1)} if model == "last"
                   else {x: Decimal(1) / Decimal(len(t)) for x in t})
        orders = orders_by_customer.get(r.assigned_customer_id, []) if owner_of.get(r.assigned_customer_id) is r else []
        is_opp = r.record_type == CRMRecordType.OPPORTUNITY or bool(r.opportunity_code)
        for label, w in weights.items():
            x = row(label)
            x["journeys"] += w
            x["leads"] += w if r.record_type == CRMRecordType.LEAD or r.lead_code else 0
            x["opportunities"] += w if is_opp else 0
            x["won"] += w if r.status == CRMStatus.WON else 0
            if orders:
                x["customers_with_orders"] += w
                x["orders"] += w * len(orders)
                x["repeat_customers"] += w if len(orders) >= 2 else 0
                for _, ccy, val in orders:
                    x["revenue"][ccy] += val * w
        for _, ccy, val in orders:
            total_revenue[ccy] += val

    out_rows = []
    for x in sorted(by_source.values(), key=lambda v: -v["journeys"]):
        out_rows.append({**{k: float(round(v, 2)) for k, v in x.items() if isinstance(v, (float, Decimal))}, "source": x["source"],
                         "revenue": {c: str(_q2(v)) for c, v in sorted(x["revenue"].items())}})
    credited = defaultdict(Decimal)
    for x in by_source.values():
        for c, v in x["revenue"].items():
            credited[c] += v
    # independent check: the counted orders re-valued straight from their lines in SQL
    independent: dict = defaultdict(Decimal)
    for i in range(0, len(counted), 5000):
        for ccy, val in (await db.execute(
                select(SalesOrder.currency, func.sum(SOLine.ordered_quantity * SOLine.unit_price * (1 - SOLine.discount_pct)))
                .join(SOLine, SOLine.so_id == SalesOrder.id).where(SalesOrder.id.in_(counted[i:i + 5000]))
                .group_by(SalesOrder.currency))).all():
            independent[ccy] += Decimal(val or 0)
    reconciled = all(abs(credited[c] - independent[c]) <= Decimal("0.01") and abs(total_revenue[c] - independent[c]) <= Decimal("0.01")
                     for c in set(credited) | set(total_revenue) | set(independent))
    return {"model": model, "date_from": date_from.isoformat(), "date_to": date_to.isoformat(), "rows": out_rows,
            "totals": {"journeys": len(records), "customers_with_orders": sum(1 for c, o in orders_by_customer.items() if o),
                       "orders": sum(len(o) for o in orders_by_customer.values()),
                       "revenue": {c: str(_q2(v)) for c, v in sorted(total_revenue.items())}},
            "reconciled": reconciled,
            "assumptions": [
                "Journey = CRM record created in the period; touches = its website-form submissions (UTM), else its source.",
                "Orders = confirmed orders of the record's linked customer from the record's creation to the period end.",
                "A customer belongs to its oldest CRM record ever; orders are credited only if that record is in this period.",
                "Revenue is net of tax (quantity x unit price x (1 - discount)); dates in Nairobi time.",
                "Linear splits credit equally over distinct touches; revenue is per currency, never summed across currencies.",
                "Joins are explicit links only (no matching people by e-mail or phone).",
            ]}
