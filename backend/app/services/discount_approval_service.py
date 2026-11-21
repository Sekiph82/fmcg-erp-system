"""Discount approval for quotations and sales orders (M41.S01.T001).

A document whose discount is above the company limit (SystemConfig ``sales.discount_approval_limit_pct``, default
10 %) waits for approval: approval_status = PENDING_DISCOUNT. It cannot be sent (quote), accepted (quote) or confirmed
(sales order) until someone with the sales approve right for that record, other than its creator, approves it.
Any later change to lines or discount re-checks the limit and drops an earlier approval.

Units differ on purpose: quotation discount_pct is a percentage (10 = 10 %), sales-order line discount_pct is a
fraction (0.10 = 10 %). The check is "any single line above the limit, or the whole-document discount above it".
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select

LIMIT_KEY = "sales.discount_approval_limit_pct"
DEFAULT_LIMIT = Decimal("10")
PENDING, APPROVED, REJECTED = "PENDING_DISCOUNT", "DISCOUNT_APPROVED", "DISCOUNT_REJECTED"


async def limit_pct(db) -> Decimal:
    from app.models.utilities import SystemConfig

    value = (await db.execute(select(SystemConfig.value).where(SystemConfig.key == LIMIT_KEY))).scalar_one_or_none()
    try:
        return Decimal(str(value).strip()) if value not in (None, "") else DEFAULT_LIMIT
    except ArithmeticError:
        return DEFAULT_LIMIT


def discount_pct(lines, header_pct=Decimal("0"), fraction: bool = False) -> Decimal:
    """Highest of: any line discount, the whole-document discount (line + header), in percent."""
    scale = Decimal("100") if fraction else Decimal("1")
    pcts = [Decimal(str(getattr(l, "discount_pct", 0) or 0)) * scale for l in lines]
    gross = sum((Decimal(str(_qty(l))) * Decimal(str(l.unit_price or 0)) for l in lines), Decimal("0"))
    net = sum((Decimal(str(_qty(l))) * Decimal(str(l.unit_price or 0)) * (1 - p / 100) for l, p in zip(lines, pcts)),
              Decimal("0")) * (1 - Decimal(str(header_pct or 0)) / 100)
    whole = (1 - net / gross) * 100 if gross > 0 else Decimal("0")
    return max([whole, *pcts], default=Decimal("0"))


def _qty(line):
    return getattr(line, "qty", None) if getattr(line, "qty", None) is not None else getattr(line, "ordered_quantity", 0)


async def refresh(db, doc, lines, header_pct=Decimal("0"), fraction: bool = False, editor_id=None) -> None:
    """Re-check after a create or change: above the limit -> waiting for approval (earlier approval dropped).
    The person who set these numbers (editor_id) may not approve them, like the creator."""
    required = discount_pct(lines, header_pct, fraction) > await limit_pct(db)
    doc.discount_approval_required = required
    doc.discount_approved_by_id = None
    doc.discount_approved_at = None
    doc.approval_status = PENDING if required else None
    doc.discount_changed_by_id = editor_id if required else None


def is_approved(doc) -> bool:
    return not doc.discount_approval_required or (doc.approval_status == APPROVED and doc.discount_approved_at is not None)


def ensure_approved(doc, action: str) -> None:
    if not is_approved(doc):
        state = "was rejected — change the discount" if doc.approval_status == REJECTED else "is waiting for approval"
        raise HTTPException(409, f"The discount on this document is above the approval limit and {state} before you can {action}.")


def can_decide(user, doc) -> bool:
    from app.core.access_control import can_modify_record

    if doc.approval_status != PENDING or _own(user, doc):
        return False
    return can_modify_record(user, "sales", "approve", doc)


def _own(user, doc) -> bool:
    """Creator or last editor of the discount: never decides it (superusers included)."""
    uid = getattr(user, "id", None)
    return uid is not None and uid in (doc.created_by_id, getattr(doc, "discount_changed_by_id", None))


async def decide(db, doc, user, approve: bool, reason: str | None, link: str) -> None:
    from app.core.access_control import can_modify_record

    if doc.approval_status != PENDING:
        raise HTTPException(409, "This discount is not waiting for a decision.")
    if _own(user, doc):
        raise HTTPException(403, "You cannot decide a discount you created or changed yourself.")
    if not (can_modify_record(user, "sales", "approve", doc)):
        raise HTTPException(403, "You may not approve discounts on this document.")
    if not approve and not (reason or "").strip():
        raise HTTPException(422, "Give a reason for the rejection.")
    now = datetime.now(timezone.utc)
    if approve:
        doc.approval_status, doc.discount_approved_by_id, doc.discount_approved_at = APPROVED, user.id, now
    else:
        doc.approval_status, doc.discount_approved_by_id, doc.discount_approved_at = REJECTED, None, None
    if doc.created_by_id:
        await _tell_creator(db, doc, approve, reason, link)


async def _tell_creator(db, doc, approve: bool, reason: str | None, link: str) -> None:
    from app.models.notifications import Notification, NotificationChannel, NotificationPriority, NotificationStatus, NotificationType

    ref = getattr(doc, "quote_no", None) or getattr(doc, "order_no", None) or str(doc.id)[:8]
    text = f"Discount on {ref} approved." if approve else f"Discount on {ref} rejected: {(reason or '').strip()[:300]}"
    db.add(Notification(user_id=str(doc.created_by_id), title=text[:300], message=f"{text} Open {link}",
                        notification_type=NotificationType.INFO, channel=NotificationChannel.IN_APP,
                        priority=NotificationPriority.NORMAL, status=NotificationStatus.SENT,
                        sent_at=datetime.utcnow(), reference_type="discount_decision", reference_id=str(doc.id),
                        module="sales"))
