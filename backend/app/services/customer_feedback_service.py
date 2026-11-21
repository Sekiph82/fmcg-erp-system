"""Customer feedback and loyalty for the customer's own channels (M40.S01.T001).

- NPS from the partner portal: active customer surveys the customer has not answered recently, and delivery
  surveys for each order delivered in the last 30 days.
- One-time public survey links (token stored as SHA-256, expires, single answer) for customers without a portal login.
- Loyalty: balance, tier and history for the portal; points are earned automatically when an invoice is fully
  paid (once per invoice), for customers enrolled in the programme.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loyalty import CustomerLoyaltyAccount, LoyaltyTier, LoyaltyTransaction
from app.models.nps import NPSResponse, NPSSurvey, NPSSurveyLink

REANSWER_DAYS = 90        # a general survey is offered again after this
DELIVERY_WINDOW_DAYS = 30  # delivery surveys for orders delivered within this window
LINK_DAYS = 30


class FeedbackError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _naive_utc() -> datetime:
    return datetime.utcnow()


async def open_surveys(db: AsyncSession, customer_id: uuid.UUID) -> list[dict]:
    from app.models.sales import SalesOrder, Shipment, ShipmentStatus
    surveys = (await db.execute(select(NPSSurvey).where(NPSSurvey.is_active.is_(True),
                                                        NPSSurvey.target_type == "CUSTOMER"))).scalars().all()
    answered = (await db.execute(select(NPSResponse.survey_id, NPSResponse.so_id, NPSResponse.responded_at)
                                 .where(NPSResponse.customer_id == customer_id))).all()
    recent_general = {s for s, so, at in answered if so is None and at >= _naive_utc() - timedelta(days=REANSWER_DAYS)}
    answered_orders = {(s, so) for s, so, _ in answered if so is not None}
    out = []
    delivered = None
    for sv in surveys:
        if sv.trigger == "DELIVERY":
            if delivered is None:
                since = datetime.now(timezone.utc) - timedelta(days=DELIVERY_WINDOW_DAYS)
                delivered = (await db.execute(
                    select(SalesOrder.id, SalesOrder.order_no).join(Shipment, Shipment.so_id == SalesOrder.id)
                    .where(SalesOrder.customer_id == customer_id, Shipment.status == ShipmentStatus.DELIVERED,
                           Shipment.updated_at >= since).distinct())).all()
            for so_id, so_no in delivered:
                if (sv.id, so_id) not in answered_orders:
                    out.append({"survey_id": str(sv.id), "so_id": str(so_id), "order_no": so_no,
                                "question": sv.question_text, "follow_up": sv.follow_up_text})
        elif sv.id not in recent_general:
            out.append({"survey_id": str(sv.id), "so_id": None, "order_no": None,
                        "question": sv.question_text, "follow_up": sv.follow_up_text})
    return out


async def answer(db: AsyncSession, customer_id: uuid.UUID, survey_id: uuid.UUID, so_id: Optional[uuid.UUID],
                 score: int, comment: Optional[str], channel: str) -> NPSResponse:
    if not 0 <= score <= 10:
        raise FeedbackError(422, "Score must be between 0 and 10.")
    from app.models.sales import Customer
    # one answer at a time per customer: a double click or retry cannot record the same survey twice
    await db.execute(select(Customer.id).where(Customer.id == customer_id).with_for_update())
    offered = {(o["survey_id"], o["so_id"]) for o in await open_surveys(db, customer_id)}
    if (str(survey_id), str(so_id) if so_id else None) not in offered:
        raise FeedbackError(409, "This survey is not open for you (already answered or not available).")
    resp = NPSResponse(survey_id=survey_id, customer_id=customer_id, so_id=so_id, score=score,
                       comment=(comment or None) and comment[:2000], channel=channel, responded_at=_naive_utc())
    db.add(resp)
    await db.flush()
    return resp


async def create_link(db: AsyncSession, survey_id: uuid.UUID, customer_id: uuid.UUID, so_id: Optional[uuid.UUID],
                      user_id) -> str:
    from app.models.sales import Customer, SalesOrder
    sv = await db.get(NPSSurvey, survey_id)
    if sv is None or not sv.is_active:
        raise FeedbackError(404, "Survey not found or not active.")
    if await db.get(Customer, customer_id) is None:
        raise FeedbackError(422, "Unknown customer.")
    if so_id:
        so = await db.get(SalesOrder, so_id)
        if so is None or so.customer_id != customer_id:
            raise FeedbackError(422, "The order does not belong to this customer.")
    token = secrets.token_urlsafe(24)
    db.add(NPSSurveyLink(token_hash=_hash(token), survey_id=survey_id, customer_id=customer_id, so_id=so_id,
                         expires_at=datetime.now(timezone.utc) + timedelta(days=LINK_DAYS), created_by_id=user_id))
    await db.flush()
    return token


async def _link(db: AsyncSession, token: str, lock: bool = False) -> NPSSurveyLink:
    q = select(NPSSurveyLink).where(NPSSurveyLink.token_hash == _hash(token))
    link = (await db.execute(q.with_for_update() if lock else q)).scalar_one_or_none()
    if link is None or link.expires_at < datetime.now(timezone.utc):
        raise FeedbackError(404, "This survey link is not valid or has expired.")
    return link


async def public_survey(db: AsyncSession, token: str) -> dict:
    from app.models.sales import SalesOrder
    link = await _link(db, token)
    sv = await db.get(NPSSurvey, link.survey_id)
    so = await db.get(SalesOrder, link.so_id) if link.so_id else None
    return {"question": sv.question_text, "follow_up": sv.follow_up_text, "order_no": so.order_no if so else None,
            "answered": link.used_at is not None}


async def public_answer(db: AsyncSession, token: str, score: int, comment: Optional[str]) -> None:
    if not 0 <= score <= 10:
        raise FeedbackError(422, "Score must be between 0 and 10.")
    link = await _link(db, token, lock=True)
    if link.used_at is not None:
        raise FeedbackError(409, "Thank you — this survey has already been answered.")
    db.add(NPSResponse(survey_id=link.survey_id, customer_id=link.customer_id, so_id=link.so_id, score=score,
                       comment=(comment or None) and comment[:2000], channel="link", responded_at=_naive_utc()))
    link.used_at = datetime.now(timezone.utc)
    await db.flush()


# ── loyalty ─────────────────────────────────────────────────────────────────

async def loyalty_summary(db: AsyncSession, customer_id: uuid.UUID) -> dict:
    acc = (await db.execute(select(CustomerLoyaltyAccount).where(CustomerLoyaltyAccount.customer_id == customer_id))).scalar_one_or_none()
    if acc is None:
        return {"enrolled": False}
    tier = await db.get(LoyaltyTier, acc.tier_id) if acc.tier_id else None
    nxt = (await db.execute(select(LoyaltyTier).where(LoyaltyTier.is_active.is_(True),
                                                      LoyaltyTier.min_lifetime_points > acc.lifetime_points)
                            .order_by(LoyaltyTier.min_lifetime_points).limit(1))).scalar_one_or_none()
    rows = (await db.execute(select(LoyaltyTransaction).where(LoyaltyTransaction.account_id == acc.id)
                             .order_by(LoyaltyTransaction.created_at.desc()).limit(50))).scalars().all()
    return {"enrolled": True, "balance": acc.total_points, "lifetime": acc.lifetime_points,
            "tier": tier.tier_name if tier else None,
            "next_tier": {"name": nxt.tier_name, "points_needed": nxt.min_lifetime_points - acc.lifetime_points} if nxt else None,
            "history": [{"at": t.created_at.isoformat() if t.created_at else None, "type": t.transaction_type,
                         "points": t.points_delta, "balance_after": t.balance_after, "description": t.description}
                        for t in rows]}


async def award_invoice_points(db: AsyncSession, invoice) -> int:
    """Points for a fully paid invoice, once per invoice, for enrolled customers. Returns points awarded."""
    acc = (await db.execute(select(CustomerLoyaltyAccount).where(CustomerLoyaltyAccount.customer_id == invoice.customer_id)
                            .with_for_update())).scalar_one_or_none()
    if acc is None:
        return 0
    ref = str(invoice.id)
    seen = (await db.execute(select(LoyaltyTransaction.id).where(LoyaltyTransaction.account_id == acc.id,
                                                                 LoyaltyTransaction.reference_type == "INVOICE",
                                                                 LoyaltyTransaction.reference_id == ref))).first()
    if seen:
        return 0
    tier = await db.get(LoyaltyTier, acc.tier_id) if acc.tier_id else None
    rate = Decimal(str(tier.points_per_100_spend)) if tier else Decimal("1")
    points = int(Decimal(str(invoice.total_amount)) / 100 * rate)
    if points <= 0:
        return 0
    acc.total_points += points
    acc.lifetime_points += points
    acc.last_activity_at = _naive_utc()
    db.add(LoyaltyTransaction(account_id=acc.id, transaction_type="EARN", points_delta=points,
                              reference_type="INVOICE", reference_id=ref,
                              description=f"Invoice {invoice.invoice_no} paid", balance_after=acc.total_points))
    best = (await db.execute(select(LoyaltyTier).where(LoyaltyTier.is_active.is_(True),
                                                       LoyaltyTier.min_lifetime_points <= acc.lifetime_points)
                             .order_by(LoyaltyTier.min_lifetime_points.desc()).limit(1))).scalar_one_or_none()
    if best is not None:
        acc.tier_id = best.id
    await db.flush()
    return points
