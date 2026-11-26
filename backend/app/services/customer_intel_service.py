"""M45.S01.T004–T006 customer intelligence from first-party ERP/CRM data.

Intent (T004): weighted, exponentially decayed first-party signals: consented website visits/forms, e-mail clicks,
quote views and new orders. Every point is explained; no third-party intent data exists until an external feed is
activated (NOT_CONFIGURED).

Churn (T005): a customer with at least `min_orders` past orders has churned when it places no order in the next
`horizon_days`. Features are computed only from data before the cut-off date (no leakage). A logistic regression is
trained locally on time-ordered snapshots (older cut-offs train, newest validate) and reports AUC, Brier score and
calibration next to a recency rule baseline. Too little history → no score ("insufficient history"). Metrics describe
the data it was trained on (synthetic before go-live); they are not a claim about real-world accuracy.

Health (T006): configurable weighted average of components (ordering, overdue invoices, tickets, NPS, e-mail
engagement, repeat purchase). A component without data is left out and named; if less than half the weight has data
the score is "not enough data" instead of a number.

Product usage (M47.S01.T008): portal/shop sign-ins, catalogue views (portal activity "catalog_view" and consented,
identified website page views on catalogue paths) and self-service orders (portal orders and submitted portal
reorder drafts) over 30/90 days. It is a health component only for customers with a portal/shop account; without one
it is reported as missing, never as zero. Churn uses the 90-day count as a feature (older models keep their features).
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, Optional

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_intel import CIAlert, CIHealthSnapshot, CIModel, CISetting
from app.models.sales import Customer, Invoice, InvoiceStatus, SalesOrder, SOStatus

DEFAULTS = {
    "intent": {"half_life_days": 7, "window_days": 30, "threshold": 15, "cooldown_days": 7,
               "weights": {"PAGE": 1, "PRICING_PAGE": 3, "FORM": 5, "CTA": 2, "EMAIL_CLICK": 3, "QUOTE_VIEW": 6, "ORDER": 8},
               "pricing_paths": ["/pricing", "/products", "/catalogue", "/order"]},
    "health": {"threshold": 50, "cooldown_days": 14,
               "weights": {"ordering": 30, "overdue": 25, "tickets": 15, "nps": 10, "engagement": 10, "repeat": 10,
                           "usage": 10},
               "playbook": ["Call the customer within 2 working days", "Review overdue invoices with finance",
                            "Check open tickets and agree a fix date"]},
    "churn": {"horizon_days": 90, "min_orders": 3, "alert_probability": 0.6},
}
CATALOG_PATHS = ("/catalog", "/catalogue", "/products", "/shop")   # website paths counted as catalogue views
LIVE_ORDERS = [s for s in SOStatus if s not in (SOStatus.DRAFT, SOStatus.CANCELLED)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def settings_for(db: AsyncSession, key: str) -> dict:
    row = await db.get(CISetting, key)
    out = {**DEFAULTS[key]}
    if row:
        out.update({k: v for k, v in row.value.items() if k in DEFAULTS[key]})
    return out


async def save_settings(db: AsyncSession, key: str, value: dict, user: str) -> dict:
    clean = {k: v for k, v in value.items() if k in DEFAULTS[key]}
    if "weights" in clean:
        w = clean["weights"]
        if not isinstance(w, dict) or set(w) - set(DEFAULTS[key]["weights"]) or any(
                not isinstance(x, (int, float)) or x < 0 or x > 100 for x in w.values()):
            raise ValueError("Weights must be numbers 0–100 for the known signals only.")
    row = await db.get(CISetting, key)
    if row is None:
        db.add(CISetting(key=key, value=clean, updated_by=user))
    else:
        row.value, row.updated_by, row.updated_at = {**row.value, **clean}, user, _now()
    return await settings_for(db, key) if row else {**DEFAULTS[key], **clean}


# ── shared data access ───────────────────────────────────────────────────────

async def customer_emails(db: AsyncSession, customer_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    from app.models.crm import CRMAccountContact, CRMContact, CRMContactAssociation
    ids = list(customer_ids)
    out: dict = defaultdict(set)
    for cid, e in (await db.execute(select(Customer.id, Customer.email).where(Customer.id.in_(ids)))).all():
        if e:
            out[cid].add(e.strip().lower())
    for cid, e in (await db.execute(select(CRMAccountContact.customer_id, CRMAccountContact.email)
                                    .where(CRMAccountContact.customer_id.in_(ids)))).all():
        if e:
            out[cid].add(e.strip().lower())
    for oid, e in (await db.execute(select(CRMContactAssociation.object_id, CRMContact.email)
                                    .join(CRMContact, CRMContact.id == CRMContactAssociation.contact_id)
                                    .where(CRMContactAssociation.object_type == "customer",
                                           CRMContactAssociation.object_id.in_(ids)))).all():
        if e:
            out[oid].add(e.strip().lower())
    return out


async def owners(db: AsyncSession, customer_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Optional[uuid.UUID]]:
    """Customer owner = the rep assigned on the newest CRM record for that customer."""
    from app.models.crm import CRMRecord
    out: dict = {}
    rows = (await db.execute(select(CRMRecord.assigned_customer_id, CRMRecord.assigned_rep_id).where(
        CRMRecord.assigned_customer_id.in_(list(customer_ids)), CRMRecord.assigned_rep_id.is_not(None))
        .order_by(CRMRecord.created_at))).all()
    for cid, rep in rows:
        try:
            out[cid] = uuid.UUID(str(rep))
        except ValueError:
            pass
    return out


async def visible_customer_ids(db: AsyncSession, user) -> Optional[set[uuid.UUID]]:
    """None = all customers (CRM-wide right); otherwise the customers this user owns."""
    from app.core.access_control import has_any_permission
    from app.models.crm import CRMRecord
    if user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all")):
        return None
    return set((await db.execute(select(CRMRecord.assigned_customer_id).where(
        CRMRecord.assigned_rep_id == str(user.id), CRMRecord.assigned_customer_id.is_not(None)))).scalars())


# ── T004 buyer intent ────────────────────────────────────────────────────────

@dataclass
class Signal:
    kind: str
    at: datetime
    detail: str
    points: float = 0.0


async def signals(db: AsyncSession, customer_id: uuid.UUID, since: datetime, cfg: dict,
                  emails: Optional[set[str]] = None) -> list[Signal]:
    from app.models.crm import (CRMDocumentLink, CRMDocumentView, CRMEmailEvent, CRMOutboundMessage, WebEvent,
                                WebIdentity)
    from app.models.quotation import Quotation
    out: list[Signal] = []
    if emails is None:
        emails = (await customer_emails(db, [customer_id])).get(customer_id, set())
    if emails:   # website: only visitors linked with marketing consent (web_identities)
        vhs = list((await db.execute(select(WebIdentity.visitor_hash).where(WebIdentity.email.in_(emails)))).scalars())
        if vhs:
            for e in (await db.execute(select(WebEvent).where(WebEvent.visitor_hash.in_(vhs), WebEvent.occurred_at >= since)
                                       .order_by(WebEvent.occurred_at).limit(2000))).scalars():
                kind = e.kind
                if kind == "PAGE" and any(e.path.startswith(p) for p in cfg["pricing_paths"]):
                    kind = "PRICING_PAGE"
                out.append(Signal(kind, e.occurred_at, f"{e.kind}{':' + e.name if e.name else ''} {e.path}"))
    for at, url in (await db.execute(select(CRMEmailEvent.occurred_at, CRMEmailEvent.url)
                                     .join(CRMOutboundMessage, CRMOutboundMessage.id == CRMEmailEvent.message_id)
                                     .where(CRMOutboundMessage.customer_id == customer_id, CRMEmailEvent.kind == "CLICK",
                                            CRMEmailEvent.is_machine.is_(False), CRMEmailEvent.occurred_at >= since))).all():
        out.append(Signal("EMAIL_CLICK", at, f"clicked {url or 'a link'}"))
    for at, qno in (await db.execute(select(CRMDocumentView.viewed_at, Quotation.quote_no)
                                     .join(CRMDocumentLink, CRMDocumentLink.id == CRMDocumentView.link_id)
                                     .join(Quotation, Quotation.id == CRMDocumentLink.quotation_id)
                                     .where(Quotation.customer_id == customer_id, CRMDocumentView.viewed_at >= since))).all():
        out.append(Signal("QUOTE_VIEW", at, f"opened quote {qno}"))
    for d, no in (await db.execute(select(SalesOrder.order_date, SalesOrder.order_no).where(
            SalesOrder.customer_id == customer_id, SalesOrder.status != SOStatus.CANCELLED,
            SalesOrder.order_date >= since.date()))).all():
        out.append(Signal("ORDER", datetime(d.year, d.month, d.day, tzinfo=timezone.utc), f"order {no}"))
    return out


def score_signals(sigs: list[Signal], cfg: dict, now: datetime) -> tuple[float, list[Signal]]:
    hl = float(cfg["half_life_days"])
    for s in sigs:
        age = max(0.0, (now - s.at).total_seconds() / 86400)
        s.points = round(float(cfg["weights"].get(s.kind, 0)) * 0.5 ** (age / hl), 2)
    ranked = sorted((s for s in sigs if s.points > 0), key=lambda s: -s.points)
    return round(sum(s.points for s in ranked), 1), ranked


async def intent(db: AsyncSession, customer_id: uuid.UUID, now: Optional[datetime] = None) -> dict:
    cfg = await settings_for(db, "intent")
    now = now or _now()
    total, ranked = score_signals(await signals(db, customer_id, now - timedelta(days=cfg["window_days"]), cfg), cfg, now)
    return {"customer_id": str(customer_id), "score": total, "threshold": cfg["threshold"], "hot": total >= cfg["threshold"],
            "explanation": [{"kind": s.kind, "at": s.at.isoformat(), "detail": s.detail, "points": s.points} for s in ranked[:20]],
            "external_feed": "NOT_CONFIGURED"}


# ── features (shared by churn and health) ────────────────────────────────────

@dataclass
class Features:
    orders_total: int = 0
    last_order: Optional[date] = None
    orders_90: int = 0
    orders_prev_90: int = 0
    revenue_90: float = 0.0
    revenue_prev_90: float = 0.0
    overdue_amount: float = 0.0
    typical_gap: Optional[float] = None
    open_tickets: int = 0
    tickets_90: int = 0
    nps_last: Optional[int] = None
    emails_sent_90: int = 0
    emails_engaged_90: int = 0
    has_portal: bool = False                        # M47.S01.T008 product usage (portal / shop)
    usage: dict = field(default_factory=lambda: {k: 0 for k in USAGE_KEYS})
    extra: dict = field(default_factory=dict)

    def vector(self, as_of: date) -> list[float]:
        days = (as_of - self.last_order).days if self.last_order else 365.0
        gap = self.typical_gap or 30.0
        return [min(days, 365.0) / 30.0, min(days / gap, 12.0), float(self.orders_90), float(self.orders_prev_90),
                math.log1p(self.revenue_90), math.log1p(self.revenue_prev_90),
                float(self.orders_90 - self.orders_prev_90), math.log1p(self.overdue_amount), float(self.open_tickets),
                math.log1p(self.usage["logins_90d"] + self.usage["catalog_views_90d"] + self.usage["self_service_orders_90d"])]


USAGE_KEYS = ("logins_30d", "logins_90d", "catalog_views_30d", "catalog_views_90d", "self_service_orders_30d",
              "self_service_orders_90d")
FEATURES = ["months_since_last_order", "gap_ratio", "orders_90d", "orders_prev_90d", "log_revenue_90d",
            "log_revenue_prev_90d", "order_trend", "log_overdue", "open_tickets", "log_usage_90d"]


async def features(db: AsyncSession, customer_ids: list[uuid.UUID], as_of: date) -> dict[uuid.UUID, Features]:
    """Everything strictly before `as_of` (orders/invoices dated on or after the cut-off are ignored: no leakage)."""
    from app.models.crm import CRMEmailEvent, CRMOutboundMessage
    from app.models.helpdesk import HelpdeskTicket
    from app.models.nps import NPSResponse
    out = {c: Features() for c in customer_ids}
    d90, d180 = as_of - timedelta(days=90), as_of - timedelta(days=180)
    dates: dict = defaultdict(list)
    for cid, d in (await db.execute(select(SalesOrder.customer_id, SalesOrder.order_date).where(
            SalesOrder.customer_id.in_(customer_ids), SalesOrder.status.in_(LIVE_ORDERS), SalesOrder.order_date < as_of)
            .order_by(SalesOrder.order_date))).all():
        dates[cid].append(d)
    for cid, ds in dates.items():
        f = out[cid]
        f.orders_total, f.last_order = len(ds), ds[-1]
        f.orders_90 = sum(1 for d in ds if d >= d90)
        f.orders_prev_90 = sum(1 for d in ds if d180 <= d < d90)
        if len(ds) >= 2:
            gaps = sorted((b - a).days for a, b in zip(ds, ds[1:]))
            f.typical_gap = float(max(1, gaps[len(gaps) // 2]))
    for cid, d, total, paid, due, st in (await db.execute(select(
            Invoice.customer_id, Invoice.invoice_date, Invoice.total_amount, Invoice.paid_amount, Invoice.due_date,
            Invoice.status).where(Invoice.customer_id.in_(customer_ids), Invoice.invoice_date < as_of,
                                  Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])))).all():
        f = out[cid]
        if d >= d90:
            f.revenue_90 += float(total or 0)
        elif d >= d180:
            f.revenue_prev_90 += float(total or 0)
        if st != InvoiceStatus.PAID and due < as_of:
            f.overdue_amount += max(0.0, float((total or 0) - (paid or 0)))
    since = datetime(d90.year, d90.month, d90.day, tzinfo=timezone.utc)
    cut = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)
    for cid, st, created in (await db.execute(select(HelpdeskTicket.customer_id, HelpdeskTicket.status,
                                                     HelpdeskTicket.created_at).where(
            HelpdeskTicket.customer_id.in_(customer_ids), HelpdeskTicket.created_at < cut))).all():
        f = out[cid]
        if str(getattr(st, "value", st)) in ("OPEN", "IN_PROGRESS", "ESCALATED", "PENDING", "WAITING"):
            f.open_tickets += 1
        if created and created >= since:
            f.tickets_90 += 1
    for cid, score, at in (await db.execute(select(NPSResponse.customer_id, NPSResponse.score, NPSResponse.responded_at)
                                            .where(NPSResponse.customer_id.in_(customer_ids),
                                                   NPSResponse.responded_at < cut.replace(tzinfo=None))
                                            .order_by(NPSResponse.responded_at))).all():
        out[cid].nps_last = int(score)
    for cid, mid, eng in (await db.execute(select(CRMOutboundMessage.customer_id, CRMOutboundMessage.id,
                                                  func.count(CRMEmailEvent.id)).outerjoin(
            CRMEmailEvent, (CRMEmailEvent.message_id == CRMOutboundMessage.id) & CRMEmailEvent.is_machine.is_(False))
            .where(CRMOutboundMessage.customer_id.in_(customer_ids), CRMOutboundMessage.status == "SENT",
                   CRMOutboundMessage.sent_at >= since, CRMOutboundMessage.sent_at < cut)
            .group_by(CRMOutboundMessage.customer_id, CRMOutboundMessage.id))).all():
        out[cid].emails_sent_90 += 1
        out[cid].emails_engaged_90 += 1 if eng else 0
    await _usage(db, out, as_of)
    return out


async def _usage(db: AsyncSession, out: dict, as_of: date) -> None:
    """Portal / shop usage in the 90 days before `as_of` (nothing on or after the cut-off: no leakage)."""
    from app.models.crm import WebEvent, WebIdentity
    from app.models.portal import PortalAccount, PortalActivityLog, PortalActivityType, PortalDraftOrder, PortalDraftOrderStatus
    cut = datetime(as_of.year, as_of.month, as_of.day)                      # naive UTC, like the portal logs
    d30, d90 = cut - timedelta(days=30), cut - timedelta(days=90)
    by_str = {str(c): c for c in out}
    accounts = {a: by_str[c] for a, c in (await db.execute(select(PortalAccount.id, PortalAccount.linked_customer_id).where(
        PortalAccount.linked_customer_id.in_(list(by_str))))).all()}

    def add(cid, kind: str, at: datetime) -> None:
        at = at if at.tzinfo is None else at.astimezone(timezone.utc).replace(tzinfo=None)
        if d90 <= at < cut:
            out[cid].usage[f"{kind}_90d"] += 1
            if at >= d30:
                out[cid].usage[f"{kind}_30d"] += 1
    for cid in set(accounts.values()):
        out[cid].has_portal = True
    if accounts:
        for acc, kind, ref, at in (await db.execute(select(PortalActivityLog.portal_account_id, PortalActivityLog.activity_type,
                                                           PortalActivityLog.reference_type, PortalActivityLog.activity_datetime)
                                                    .where(PortalActivityLog.portal_account_id.in_(list(accounts)),
                                                           PortalActivityLog.activity_datetime >= d90,
                                                           PortalActivityLog.activity_datetime < cut))).all():
            if kind == PortalActivityType.LOGIN:
                add(accounts[acc], "logins", at)
            elif ref == "catalog_view":
                add(accounts[acc], "catalog_views", at)
        for acc, at in (await db.execute(select(PortalDraftOrder.portal_account_id, PortalDraftOrder.created_at).where(
                PortalDraftOrder.portal_account_id.in_(list(accounts)), PortalDraftOrder.source_order_id.is_not(None),
                PortalDraftOrder.status != PortalDraftOrderStatus.DRAFT))).all():
            add(accounts[acc], "self_service_orders", at)                   # submitted reorder drafts
    for cid, at in (await db.execute(select(SalesOrder.customer_id, SalesOrder.created_at).where(
            SalesOrder.customer_id.in_(list(out)), SalesOrder.offline_id.like("portal:%"),
            SalesOrder.status != SOStatus.CANCELLED))).all():
        out[cid].has_portal = True
        add(cid, "self_service_orders", at)                                 # orders placed in the portal / shop
    paths = CATALOG_PATHS
    emails = await customer_emails(db, [c for c in out if out[c].has_portal])
    vh_by_email: dict = {}
    for vh, e in (await db.execute(select(WebIdentity.visitor_hash, WebIdentity.email).where(
            WebIdentity.email.in_({e for es in emails.values() for e in es})))).all():
        vh_by_email.setdefault(e, []).append(vh)
    for cid, es in emails.items():
        vhs = [v for e in es for v in vh_by_email.get(e, ())]
        if vhs:   # website catalogue page views of the customer's identified (consented) visitors
            for path, at in (await db.execute(select(WebEvent.path, WebEvent.occurred_at).where(
                    WebEvent.visitor_hash.in_(vhs), WebEvent.kind == "PAGE",
                    WebEvent.occurred_at >= d90.replace(tzinfo=timezone.utc)))).all():
                if any(path.startswith(p) for p in paths):
                    add(cid, "catalog_views", at)


# ── T005 churn ───────────────────────────────────────────────────────────────

def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 0.1, iters: int = 2000, lr: float = 0.1):
    """Plain gradient-descent logistic regression on standardized features (no external ML dependency)."""
    mean, std = X.mean(axis=0), X.std(axis=0)
    std[std == 0] = 1.0
    Z = (X - mean) / std
    w, b = np.zeros(Z.shape[1]), 0.0
    for _ in range(iters):
        p = _sigmoid(Z @ w + b)
        w -= lr * ((Z.T @ (p - y)) / len(y) + l2 * w / len(y))
        b -= lr * float(np.mean(p - y))
    return {"mean": mean.tolist(), "std": std.tolist(), "coef": w.tolist(), "intercept": b}


def predict(params: dict, X: np.ndarray) -> np.ndarray:
    Z = (X - np.array(params["mean"])) / np.array(params["std"])
    return _sigmoid(Z @ np.array(params["coef"]) + params["intercept"])


def auc(y: np.ndarray, p: np.ndarray) -> Optional[float]:
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return None
    wins = sum(float(np.sum(pp > neg)) + 0.5 * float(np.sum(pp == neg)) for pp in pos)
    return round(wins / (len(pos) * len(neg)), 3)


def calibration(y: np.ndarray, p: np.ndarray, bins: int = 5) -> list[dict]:
    out = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        m = (p >= lo) & ((p < hi) if i < bins - 1 else (p <= hi))
        if m.any():
            out.append({"bin": f"{lo:.1f}–{hi:.1f}", "n": int(m.sum()), "predicted": round(float(p[m].mean()), 3),
                        "observed": round(float(y[m].mean()), 3)})
    return out


def rule_risk(f: Features, as_of: date) -> float:
    """Baseline / cold model: overdue relative to the customer's own ordering rhythm."""
    if not f.last_order:
        return 1.0
    ratio = (as_of - f.last_order).days / (f.typical_gap or 30.0)
    return round(min(1.0, max(0.0, (ratio - 1.0) / 3.0)), 3)


async def _snapshots(db: AsyncSession, cut_offs: list[date], horizon: int, min_orders: int):
    """(cut_off, customer, features, label) for every cut-off whose horizon has fully passed."""
    rows = []
    ids = list((await db.execute(select(Customer.id))).scalars())
    for cut in cut_offs:
        fs = await features(db, ids, cut)
        future = set((await db.execute(select(SalesOrder.customer_id).where(
            SalesOrder.customer_id.in_(ids), SalesOrder.status.in_(LIVE_ORDERS), SalesOrder.order_date >= cut,
            SalesOrder.order_date < cut + timedelta(days=horizon)))).scalars())
        for cid, f in fs.items():
            if f.orders_total >= min_orders:
                rows.append((cut, cid, f, 0 if cid in future else 1))
    return rows


async def train_churn(db: AsyncSession, user: str, today: Optional[date] = None, months: int = 12) -> dict:
    cfg = await settings_for(db, "churn")
    today = today or date.today()
    horizon = int(cfg["horizon_days"])
    last_cut = today - timedelta(days=horizon)
    cut_offs = sorted({last_cut - timedelta(days=30 * i) for i in range(months)})
    rows = await _snapshots(db, cut_offs, horizon, int(cfg["min_orders"]))
    if len(rows) < 20 or len({r[3] for r in rows}) < 2:
        return {"trained": False, "reason": "Not enough labeled history (need 20+ snapshots with both outcomes).",
                "snapshots": len(rows)}
    split = cut_offs[-max(1, len(cut_offs) // 4)]          # newest quarter of cut-offs validates (time-aware split)
    train = [r for r in rows if r[0] < split]
    valid = [r for r in rows if r[0] >= split]
    if len({r[3] for r in train}) < 2 or not valid:
        return {"trained": False, "reason": "The training period has only one outcome.", "snapshots": len(rows)}
    Xt = np.array([r[2].vector(r[0]) for r in train]); yt = np.array([r[3] for r in train], dtype=float)
    Xv = np.array([r[2].vector(r[0]) for r in valid]); yv = np.array([r[3] for r in valid], dtype=float)
    params = fit_logistic(Xt, yt)
    pv = predict(params, Xv)
    base = np.array([rule_risk(r[2], r[0]) for r in valid])
    metrics = {"n_train": len(train), "n_valid": len(valid), "split_date": split.isoformat(),
               "train_until": max(r[0] for r in train).isoformat(), "horizon_days": horizon,
               "churn_rate_valid": round(float(yv.mean()), 3), "auc": auc(yv, pv),
               "brier": round(float(np.mean((pv - yv) ** 2)), 4), "calibration": calibration(yv, pv),
               "baseline_rule": {"auc": auc(yv, base), "brier": round(float(np.mean((base - yv) ** 2)), 4)},
               "note": "Measured on the data in this database. Before go-live that is synthetic data, "
                       "so these numbers say nothing about real customers."}
    for old in (await db.execute(select(CIModel).where(CIModel.kind == "CHURN", CIModel.status == "ACTIVE"))).scalars():
        old.status = "RETIRED"
    m = CIModel(kind="CHURN", params={**params, "features": FEATURES}, metrics=metrics, trained_by=user)
    db.add(m)
    await db.flush()
    return {"trained": True, "model_id": str(m.id), "metrics": metrics}


async def churn(db: AsyncSession, customer_ids: list[uuid.UUID], as_of: Optional[date] = None) -> dict[uuid.UUID, dict]:
    cfg = await settings_for(db, "churn")
    as_of = as_of or date.today()
    model = (await db.execute(select(CIModel).where(CIModel.kind == "CHURN", CIModel.status == "ACTIVE")
                              .order_by(CIModel.trained_at.desc()))).scalars().first()
    fs = await features(db, customer_ids, as_of)
    out = {}
    for cid, f in fs.items():
        if f.orders_total < int(cfg["min_orders"]):
            out[cid] = {"probability": None, "method": "none",
                        "reason": f"Insufficient history ({f.orders_total} orders; {cfg['min_orders']} needed)."}
            continue
        if model:   # a model keeps the feature list it was trained with (models from before M47 have 9 features)
            named = dict(zip(FEATURES, f.vector(as_of)))
            used = model.params.get("features") or FEATURES[:9]
            x = np.array([[named[k] for k in used]])
            p = float(predict(model.params, x)[0])
            z = (x[0] - np.array(model.params["mean"])) / np.array(model.params["std"])
            contrib = sorted(zip(used, (z * np.array(model.params["coef"])).tolist()), key=lambda t: -abs(t[1]))[:3]
            out[cid] = {"probability": round(p, 3), "method": "model", "model_id": str(model.id),
                        "factors": [{"feature": k, "effect": "raises risk" if v > 0 else "lowers risk", "weight": round(v, 2)}
                                    for k, v in contrib],
                        "confidence": "low" if f.orders_total < 2 * int(cfg["min_orders"]) else "normal"}
        else:
            out[cid] = {"probability": rule_risk(f, as_of), "method": "rule",
                        "factors": [{"feature": "gap_ratio", "effect": "days since last order vs usual gap",
                                     "weight": round((as_of - f.last_order).days / (f.typical_gap or 30.0), 2)}],
                        "confidence": "low"}
    return out


# ── T006 health ──────────────────────────────────────────────────────────────

def health_components(f: Features, as_of: date) -> dict[str, Optional[float]]:
    c: dict[str, Optional[float]] = {}
    if f.last_order:
        ratio = (as_of - f.last_order).days / (f.typical_gap or 30.0)
        c["ordering"] = round(max(0.0, min(100.0, 100.0 - max(0.0, ratio - 1.0) * 40.0)), 1)
        c["repeat"] = 100.0 if f.orders_90 >= 2 else 60.0 if f.orders_90 == 1 else 0.0
    else:
        c["ordering"] = c["repeat"] = None
    if f.revenue_90 or f.revenue_prev_90 or f.overdue_amount:
        base = max(f.revenue_90 + f.revenue_prev_90, 1.0)
        c["overdue"] = round(max(0.0, 100.0 - 100.0 * min(1.0, f.overdue_amount / base) * 2), 1)
    else:
        c["overdue"] = None
    c["tickets"] = round(max(0.0, 100.0 - 25.0 * f.open_tickets - 5.0 * f.tickets_90), 1)
    c["nps"] = float(f.nps_last * 10) if f.nps_last is not None else None
    c["engagement"] = round(100.0 * f.emails_engaged_90 / f.emails_sent_90, 1) if f.emails_sent_90 >= 3 else None
    if f.has_portal:   # no portal/shop account: usage is unknown and named as missing by health(), never scored 0
        u = f.usage
        c["usage"] = (100.0 if u["self_service_orders_90d"] >= 2 else 80.0 if u["self_service_orders_90d"] == 1
                      else 50.0 if u["logins_30d"] + u["catalog_views_30d"] else 25.0 if u["logins_90d"] + u["catalog_views_90d"]
                      else 0.0)
    return c


def combine(components: dict[str, Optional[float]], weights: dict) -> tuple[Optional[int], list[str]]:
    total = sum(float(w) for w in weights.values()) or 1.0
    have = {k: v for k, v in components.items() if v is not None and weights.get(k)}
    missing = [k for k, v in components.items() if v is None]
    covered = sum(float(weights[k]) for k in have)
    if covered < total / 2:
        return None, missing
    return round(sum(v * float(weights[k]) for k, v in have.items()) / covered), missing


async def health(db: AsyncSession, customer_ids: list[uuid.UUID], as_of: Optional[date] = None) -> dict[uuid.UUID, dict]:
    cfg = await settings_for(db, "health")
    as_of = as_of or date.today()
    fs = await features(db, customer_ids, as_of)
    trend: dict = defaultdict(list)
    for cid, day, score in (await db.execute(select(CIHealthSnapshot.customer_id, CIHealthSnapshot.day, CIHealthSnapshot.score)
                                             .where(CIHealthSnapshot.customer_id.in_(customer_ids))
                                             .order_by(CIHealthSnapshot.day.desc()))).all():
        if len(trend[cid]) < 8:
            trend[cid].append({"day": day.isoformat(), "score": score})
    out = {}
    for cid, f in fs.items():
        comp = health_components(f, as_of)
        score, missing = combine(comp, cfg["weights"])
        if not f.has_portal:
            missing = [*missing, "usage"]
        out[cid] = {"score": score, "label": "not enough data" if score is None else
                    ("healthy" if score >= 70 else "watch" if score >= cfg["threshold"] else "at risk"),
                    "components": comp, "missing": missing, "trend": list(reversed(trend[cid])),
                    "signals": {"orders_90d": f.orders_90, "overdue_amount": round(f.overdue_amount, 2),
                                "open_tickets": f.open_tickets, "nps_last": f.nps_last},
                    "usage": ({**f.usage, "note": "portal/shop sign-ins, catalogue views and self-service orders"}
                              if f.has_portal else {"note": "no portal or shop account: usage unknown"})}
    return out


# ── alerts and daily snapshot (tick) ─────────────────────────────────────────

async def _alert(db: AsyncSession, kind: str, cid: uuid.UUID, score: float, reasons: list, owner, cooldown: int,
                 now: datetime) -> bool:
    recent = (await db.execute(select(func.count()).select_from(CIAlert).where(
        CIAlert.kind == kind, CIAlert.customer_id == cid, CIAlert.created_at >= now - timedelta(days=cooldown)))).scalar_one()
    if recent:
        return False
    db.add(CIAlert(kind=kind, customer_id=cid, score=score, reasons=reasons, owner_user_id=owner, created_at=now))
    if owner:
        from app.models.notifications import (Notification, NotificationChannel, NotificationPriority,
                                              NotificationStatus, NotificationType)
        name = (await db.get(Customer, cid)).name
        title = {"INTENT": f"Buying signals: {name}", "HEALTH": f"Customer health low: {name}",
                 "CHURN": f"Churn risk: {name}"}[kind]
        db.add(Notification(user_id=str(owner), title=title[:255], message="; ".join(str(r) for r in reasons)[:2000],
                            notification_type=NotificationType.WARNING, priority=NotificationPriority.NORMAL,
                            channel=NotificationChannel.IN_APP, reference_type="customer", reference_id=str(cid),
                            module="crm", status=NotificationStatus.SENT, sent_at=now.replace(tzinfo=None)))
    return True


async def run_daily(db: AsyncSession, now: Optional[datetime] = None, limit: int = 2000) -> dict:
    """Snapshot health for active customers and raise intent/health/churn alerts (idempotent per day)."""
    now = now or _now()
    today = now.date()
    ids = list((await db.execute(select(Customer.id).where(Customer.is_active.is_(True)).limit(limit))).scalars())
    if not ids:
        return {"customers": 0, "alerts": 0}
    hcfg, icfg, ccfg = await settings_for(db, "health"), await settings_for(db, "intent"), await settings_for(db, "churn")
    hs, cs, own = await health(db, ids, today), await churn(db, ids, today), await owners(db, ids)
    emails = await customer_emails(db, ids)
    alerts = 0
    for cid in ids:
        h = hs[cid]
        exists = (await db.execute(select(CIHealthSnapshot.id).where(CIHealthSnapshot.customer_id == cid,
                                                                     CIHealthSnapshot.day == today))).scalar_one_or_none()
        if exists is None:
            db.add(CIHealthSnapshot(customer_id=cid, day=today, score=h["score"], components=h["components"]))
        if h["score"] is not None and h["score"] < hcfg["threshold"]:
            alerts += await _alert(db, "HEALTH", cid, h["score"], [f"score {h['score']}"] + hcfg["playbook"],
                                   own.get(cid), hcfg["cooldown_days"], now)
        p = cs[cid].get("probability")
        if p is not None and p >= ccfg["alert_probability"]:
            alerts += await _alert(db, "CHURN", cid, p, [f"{f['feature']} {f['effect']}" for f in cs[cid].get("factors", [])],
                                   own.get(cid), 30, now)
        sigs = await signals(db, cid, now - timedelta(days=icfg["window_days"]), icfg, emails.get(cid, set()))
        total, ranked = score_signals(sigs, icfg, now)
        if total >= icfg["threshold"]:
            alerts += await _alert(db, "INTENT", cid, total, [f"{s.detail} (+{s.points})" for s in ranked[:5]],
                                   own.get(cid), icfg["cooldown_days"], now)
    await db.flush()
    return {"customers": len(ids), "alerts": alerts}
