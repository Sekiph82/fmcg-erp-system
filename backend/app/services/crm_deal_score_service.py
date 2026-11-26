"""Explainable deal score and buying-group coverage (M43.S01.T012).

Score 0–100 = weighted sum of factors, each 0–1 with a plain-language reason. Factors with no data are listed as
"missing" and their weight is left out (renormalised), so a deal is never punished or rewarded for unknown data.
Weights are configurable (SystemConfig "crm.deal_score_weights"); defaults below. This is a transparent rule-based
score, not a trained model: no accuracy is claimed. History rows (at most one per record per day) give the trend.

Native ERP signals beyond a CRM: the linked customer's overdue invoices and past confirmed orders.
Trained deal-win model (M47.S01.T009): a logistic regression on closed (won/lost) deals, trained only when there are at
least MIN_PER_CLASS deals of each outcome; version, holdout AUC/accuracy and sample sizes are stored and shown with the
probability. With too few closed deals the rule score stands alone, labelled "not enough data". Before go-live the data
is synthetic, so the metrics say nothing about real deals.

Buying group: contacts associated with the deal (crm_contact_associations, object_type crm_record) with role labels;
coverage counts decision maker, buyer/finance and champion, and warns about missing roles and known blockers.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import (CRMActivity, CRMContactAssociation, CRMDealScoreHistory, CRMEmailEvent, CRMOutboundMessage,
                            CRMPipelineStage, CRMRecord, CRMStageHistory, CRMStatus, CRMWinLoss)

DEFAULT_WEIGHTS = {"stage": 25, "activity": 20, "engagement": 10, "buying_group": 20, "quote": 10, "stage_age": 10,
                   "customer": 5}
KEY_ROLES = (("decision_maker",), ("buyer", "finance"), ("champion",))


async def weights(db: AsyncSession) -> dict:
    from app.models.utilities import SystemConfig
    row = (await db.execute(select(SystemConfig).where(SystemConfig.key == "crm.deal_score_weights"))).scalar_one_or_none()
    try:
        custom = json.loads(row.value) if row and row.value else {}
    except ValueError:
        custom = {}
    return {k: float(custom.get(k, v)) for k, v in DEFAULT_WEIGHTS.items()}


async def buying_group(db: AsyncSession, rec: CRMRecord) -> dict:
    labels = [l for (l,) in (await db.execute(select(CRMContactAssociation.label).where(
        CRMContactAssociation.object_type == "crm_record", CRMContactAssociation.object_id == rec.id))).all()]
    covered = [any(r in labels for r in group) for group in KEY_ROLES]
    missing = ["/".join(g).replace("_", " ") for g, ok in zip(KEY_ROLES, covered) if not ok]
    return {"roles": sorted(set(labels)), "coverage": round(sum(covered) / len(KEY_ROLES), 2), "missing": missing,
            "blockers": labels.count("blocker")}


async def score(db: AsyncSession, rec: CRMRecord, today: Optional[date] = None) -> dict:
    from app.models.sales import Invoice, InvoiceStatus, SalesOrder, SOStatus
    today = today or date.today()
    w = await weights(db)
    factors, missing = [], []

    def add(key, value, reason):
        factors.append({"factor": key, "value": round(max(0.0, min(1.0, value)), 3), "weight": w[key], "reason": reason})

    st = await db.get(CRMPipelineStage, rec.stage_id) if rec.stage_id else None
    if st is not None:
        add("stage", float(st.default_probability or 0) / 100, f"Stage '{st.stage_name}' ({st.default_probability or 0}% typical)")
    else:
        missing.append("stage")
    last = (await db.execute(select(func.max(func.coalesce(CRMActivity.completed_datetime, CRMActivity.activity_datetime)))
                             .where(CRMActivity.crm_record_id == rec.id))).scalar_one()
    if last:
        days = (datetime.utcnow() - last).days
        add("activity", 1.0 if days <= 7 else 0.5 if days <= 30 else 0.0, f"Last activity {days} day(s) ago")
    else:
        missing.append("activity")
    since = datetime.now(timezone.utc) - timedelta(days=30)
    tracked = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
        CRMOutboundMessage.crm_record_id == rec.id, CRMOutboundMessage.track_engagement.is_(True),
        CRMOutboundMessage.sent_at >= since))).scalar_one()
    if tracked:
        human = (await db.execute(select(func.count(func.distinct(CRMEmailEvent.message_id))).join(
            CRMOutboundMessage, CRMOutboundMessage.id == CRMEmailEvent.message_id).where(
            CRMOutboundMessage.crm_record_id == rec.id, CRMEmailEvent.is_machine.is_(False),
            CRMEmailEvent.occurred_at >= since))).scalar_one()
        add("engagement", human / tracked, f"{human} of {tracked} tracked e-mail(s) opened or clicked by a person (30 days)")
    else:
        missing.append("engagement")
    bg = await buying_group(db, rec)
    if bg["roles"]:
        add("buying_group", bg["coverage"] - 0.25 * bg["blockers"],
            "Buying group covers " + (", ".join(bg["roles"])) + (f"; missing {', '.join(bg['missing'])}" if bg["missing"] else ""))
    else:
        missing.append("buying_group")
    if rec.linked_quotation_id:
        add("quote", 1.0, "A quotation is linked")
    else:
        add("quote", 0.0, "No quotation yet")
    entered = (await db.execute(select(func.max(CRMStageHistory.changed_at)).where(
        CRMStageHistory.crm_record_id == rec.id, CRMStageHistory.to_stage_id == rec.stage_id))).scalar_one()
    if entered:
        age = (datetime.now(timezone.utc) - entered).days
        add("stage_age", 1.0 if age <= 14 else 0.5 if age <= 45 else 0.0, f"{age} day(s) in the current stage")
    else:
        missing.append("stage_age")
    if rec.assigned_customer_id:
        overdue = (await db.execute(select(func.count()).select_from(Invoice).where(
            Invoice.customer_id == rec.assigned_customer_id, Invoice.status == InvoiceStatus.OVERDUE))).scalar_one()
        orders = (await db.execute(select(func.count()).select_from(SalesOrder).where(
            SalesOrder.customer_id == rec.assigned_customer_id,
            SalesOrder.status.in_((SOStatus.CONFIRMED, SOStatus.SHIPPED, SOStatus.INVOICED))))).scalar_one()
        add("customer", (0.5 if orders else 0.3) + (0.5 if not overdue else 0.0) - (0.3 if overdue > 2 else 0.0),
            f"{orders} past order(s), {overdue} overdue invoice(s) in the ERP")
    else:
        missing.append("customer")
    total_w = sum(f["weight"] for f in factors) or 1.0
    value = round(sum(f["value"] * f["weight"] for f in factors) / total_w * 100)
    return {"record_id": str(rec.id), "score": value, "factors": factors, "missing": missing, "buying_group": bg,
            "method": "Transparent weighted rules; not a trained prediction.", "trained": await win_probability(db, rec)}


async def score_with_trend(db: AsyncSession, rec: CRMRecord) -> dict:
    result = await score(db, rec)
    last = (await db.execute(select(CRMDealScoreHistory).where(CRMDealScoreHistory.crm_record_id == rec.id)
                             .order_by(CRMDealScoreHistory.computed_at.desc()).limit(1))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if last is None or now - last.computed_at > timedelta(hours=24):
        db.add(CRMDealScoreHistory(crm_record_id=rec.id, score=result["score"], factors=result["factors"], computed_at=now))
        await db.flush()
    hist = (await db.execute(select(CRMDealScoreHistory.computed_at, CRMDealScoreHistory.score).where(
        CRMDealScoreHistory.crm_record_id == rec.id).order_by(CRMDealScoreHistory.computed_at).limit(90))).all()
    result["trend"] = [{"at": at.isoformat(), "score": s} for at, s in hist]
    return result


# ── M47.S01.T009 trained deal-win model ───────────────────────────────────────

MIN_PER_CLASS = 10
WIN_FEATURES = ["log_amount", "days_open", "stage_changes", "activities", "completed_activities", "prior_orders"]


def _aware(v: datetime) -> datetime:
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


async def _features(db: AsyncSession, recs: list, as_of: Optional[dict] = None) -> list[list[float]]:
    """One vector per record. as_of: record id -> end time (close time for closed deals; now for open ones)."""
    import math

    from app.models.crm import CRMActivityResult
    from app.models.sales import SalesOrder
    from app.services.customer_intel_service import LIVE_ORDERS
    ids = [r.id for r in recs]
    acts = {rid: (n, done) for rid, n, done in (await db.execute(select(
        CRMActivity.crm_record_id, func.count(), func.count().filter(CRMActivity.result_status == CRMActivityResult.COMPLETED))
        .where(CRMActivity.crm_record_id.in_(ids)).group_by(CRMActivity.crm_record_id))).all()}
    stages = dict((await db.execute(select(CRMStageHistory.crm_record_id, func.count()).where(
        CRMStageHistory.crm_record_id.in_(ids), CRMStageHistory.to_stage_id.is_not(None))
        .group_by(CRMStageHistory.crm_record_id))).all())
    custs = {r.assigned_customer_id for r in recs if r.assigned_customer_id}
    orders: dict = {}
    if custs:
        for cid, d in (await db.execute(select(SalesOrder.customer_id, SalesOrder.order_date).where(
                SalesOrder.customer_id.in_(custs), SalesOrder.status.in_(LIVE_ORDERS)))).all():
            orders.setdefault(cid, []).append(d)
    now = datetime.now(timezone.utc)
    out = []
    for r in recs:
        start = _aware(r.created_at)
        end = (as_of or {}).get(r.id) or now
        n, done = acts.get(r.id, (0, 0))
        prior = sum(1 for d in orders.get(r.assigned_customer_id, []) if d < start.date())
        out.append([math.log1p(float(r.expected_revenue or 0)), max(0.0, (end - start).total_seconds() / 86400),
                    float(stages.get(r.id, 0)), float(n), float(done), float(prior)])
    return out


async def _closed(db: AsyncSession) -> list[tuple]:
    """(record, label 1=won 0=lost, close time) for closed deals, oldest close first."""
    rows = (await db.execute(select(CRMRecord, CRMWinLoss.close_date).outerjoin(CRMWinLoss, CRMWinLoss.crm_record_id == CRMRecord.id)
                             .where(CRMRecord.status.in_((CRMStatus.WON, CRMStatus.LOST))).limit(20000))).all()
    out = [(rec, 1.0 if rec.status == CRMStatus.WON else 0.0,
            datetime.combine(close, datetime.min.time(), timezone.utc) if close else _aware(rec.updated_at)) for rec, close in rows]
    return sorted(out, key=lambda t: (t[2], str(t[0].id)))


async def train_win_model(db: AsyncSession, user: str) -> dict:
    import numpy as np

    from app.models.customer_intel import CIModel
    from app.services.customer_intel_service import auc, fit_logistic, predict
    rows = await _closed(db)
    won, lost = sum(1 for r in rows if r[1] == 1), sum(1 for r in rows if r[1] == 0)
    if won < MIN_PER_CLASS or lost < MIN_PER_CLASS:
        return {"trained": False, "status": "NOT_ENOUGH_DATA", "won": won, "lost": lost, "min_per_class": MIN_PER_CLASS,
                "reason": f"Need at least {MIN_PER_CLASS} won and {MIN_PER_CLASS} lost deals; have {won} won and {lost} lost."}
    X = np.array(await _features(db, [r[0] for r in rows], {r[0].id: r[2] for r in rows}))
    y = np.array([r[1] for r in rows])
    cut = int(len(rows) * 0.75)                                 # newest quarter of closes is the holdout (time-aware)
    if len(set(y[:cut].tolist())) < 2:
        return {"trained": False, "status": "NOT_ENOUGH_DATA", "won": won, "lost": lost,
                "reason": "The training period has only one outcome."}
    params = fit_logistic(X[:cut], y[:cut])
    p = predict(params, X[cut:])
    yv = y[cut:]
    metrics = {"n_train": cut, "n_holdout": int(len(yv)), "won": won, "lost": lost, "auc": auc(yv, p),
               "accuracy": round(float(np.mean((p >= 0.5) == (yv == 1))), 3), "holdout_win_rate": round(float(yv.mean()), 3),
               "note": "Measured on a time-ordered holdout of the deals in this database. Before go-live that is synthetic "
                       "data, so these numbers say nothing about real deals."}
    version = (await db.execute(select(func.count()).select_from(CIModel).where(CIModel.kind == "DEAL_WIN"))).scalar_one() + 1
    for old in (await db.execute(select(CIModel).where(CIModel.kind == "DEAL_WIN", CIModel.status == "ACTIVE"))).scalars():
        old.status = "RETIRED"
    m = CIModel(kind="DEAL_WIN", params={**params, "features": WIN_FEATURES, "version": version}, metrics=metrics, trained_by=user)
    db.add(m)
    await db.flush()
    return {"trained": True, "model_id": str(m.id), "version": version, "metrics": metrics}


async def active_win_model(db: AsyncSession):
    from app.models.customer_intel import CIModel
    return (await db.execute(select(CIModel).where(CIModel.kind == "DEAL_WIN", CIModel.status == "ACTIVE")
                             .order_by(CIModel.trained_at.desc()).limit(1))).scalar_one_or_none()


async def win_probability(db: AsyncSession, rec: CRMRecord) -> dict:
    import numpy as np

    from app.services.customer_intel_service import predict
    m = await active_win_model(db)
    if m is None:
        return {"status": "NOT_ENOUGH_DATA", "probability": None,
                "label": f"Not enough data: a model needs {MIN_PER_CLASS} won and {MIN_PER_CLASS} lost deals; rule score only."}
    x = np.array(await _features(db, [rec]))
    return {"status": "TRAINED", "probability": round(float(predict(m.params, x)[0]), 3), "model_version": m.params.get("version"),
            "trained_at": m.trained_at.isoformat() if m.trained_at else None, "metrics": m.metrics}
