from __future__ import annotations
import uuid
import secrets
import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portal import (
    PortalAccount, PortalUser, PortalActivityLog, PortalClaim,
    PortalDraftOrder, PortalDraftOrderLine, PortalAIRecommendation,
    PortalAccountStatus, PortalUserRole, PortalActivityType,
    PortalClaimStatus, PortalDraftOrderStatus,
    PortalAIAgentType, PortalAIRecStatus,
)
from app.schemas.portal import (
    PortalAccountCreate, PortalAccountUpdate,
    PortalUserInvite,
    PortalClaimCreate, PortalClaimReview,
    PortalDraftOrderCreate, PortalDraftOrderReview,
    PortalAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed


async def _next_account_code(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count(PortalAccount.id)))).scalar() or 0
    return f"PA-{n + 1:05d}"


async def _next_claim_no(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count(PortalClaim.id)))).scalar() or 0
    return f"CLM-{n + 1:05d}"


async def _next_draft_no(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count(PortalDraftOrder.id)))).scalar() or 0
    return f"DRF-{n + 1:05d}"


async def _log_activity(
    db: AsyncSession,
    user_id: str,
    account_id: Optional[str],
    activity_type: PortalActivityType,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
):
    log = PortalActivityLog(
        portal_user_id=uuid.UUID(user_id),
        portal_account_id=uuid.UUID(account_id) if account_id else None,
        activity_type=activity_type,
        reference_type=reference_type,
        reference_id=reference_id,
        activity_datetime=datetime.utcnow(),
        notes=notes,
    )
    db.add(log)
    await db.flush()


# ── Portal Accounts ───────────────────────────────────────────────────────────

async def get_accounts(db: AsyncSession, status: Optional[str] = None, skip: int = 0, limit: int = 100):
    q = select(PortalAccount)
    if status:
        q = q.where(PortalAccount.portal_status == status)
    q = q.order_by(PortalAccount.created_at.desc()).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()


async def get_account(db: AsyncSession, account_id: str) -> Optional[PortalAccount]:
    return await db.get(PortalAccount, uuid.UUID(account_id))


async def create_account(db: AsyncSession, data: PortalAccountCreate) -> PortalAccount:
    account = PortalAccount(
        account_code=await _next_account_code(db),
        **data.model_dump(),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def update_account(db: AsyncSession, account_id: str, data: PortalAccountUpdate) -> Optional[PortalAccount]:
    account = await get_account(db, account_id)
    if not account:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(account, k, v)
    await db.commit()
    await db.refresh(account)
    return account


async def activate_account(db: AsyncSession, account_id: str) -> Optional[PortalAccount]:
    account = await get_account(db, account_id)
    if not account:
        return None
    account.portal_status = PortalAccountStatus.ACTIVE
    await db.commit()
    await db.refresh(account)
    return account


async def suspend_account(db: AsyncSession, account_id: str) -> Optional[PortalAccount]:
    account = await get_account(db, account_id)
    if not account:
        return None
    account.portal_status = PortalAccountStatus.SUSPENDED
    await db.commit()
    await db.refresh(account)
    return account


# ── Portal Users ──────────────────────────────────────────────────────────────

async def get_users(db: AsyncSession, account_id: str):
    result = await db.execute(
        select(PortalUser).where(PortalUser.portal_account_id == uuid.UUID(account_id))
    )
    return result.scalars().all()


async def invite_user(db: AsyncSession, account_id: str, data: PortalUserInvite) -> PortalUser:
    token = secrets.token_urlsafe(32)
    user = PortalUser(
        portal_account_id=uuid.UUID(account_id),
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        login_identifier=data.email,
        role_type=data.role_type,
        invited_by=data.invited_by,
        invitation_token=token,
        token_expires_at=datetime.utcnow() + timedelta(days=7),
        is_active=False,
        password_hash=_hash_password(secrets.token_urlsafe(16)),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def activate_user_with_password(db: AsyncSession, token: str, new_password: str) -> Optional[PortalUser]:
    result = await db.execute(
        select(PortalUser).where(PortalUser.invitation_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.token_expires_at and user.token_expires_at < datetime.utcnow():
        return None
    user.password_hash = _hash_password(new_password)
    user.is_active = True
    user.invitation_token = None
    user.token_expires_at = None
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: str) -> Optional[PortalUser]:
    user = await db.get(PortalUser, uuid.UUID(user_id))
    if not user:
        return None
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


# ── Authentication ────────────────────────────────────────────────────────────

async def login(db: AsyncSession, email: str, password: str) -> Optional[dict]:
    result = await db.execute(
        select(PortalUser)
        .options(selectinload(PortalUser.account))
        .where(PortalUser.email == email, PortalUser.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    if user.account.portal_status != PortalAccountStatus.ACTIVE:
        return None
    user.last_login_at = datetime.utcnow()
    await db.flush()
    await _log_activity(db, str(user.id), str(user.portal_account_id), PortalActivityType.LOGIN)
    await db.commit()
    # Build a simple JWT-like token (placeholder — use real JWT in production)
    token = secrets.token_urlsafe(48)
    return {
        "token": token,
        "portal_user_id": str(user.id),
        "portal_account_id": str(user.portal_account_id),
        "full_name": user.full_name,
        "role_type": str(user.role_type),
        "account_type": str(user.account.account_type),
        "account_code": user.account.account_code,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_portal_dashboard(db: AsyncSession, account: PortalAccount) -> dict:
    from app.models.sales import Invoice, InvoiceStatus, SalesOrder, SOStatus, Payment

    # Pull linked IDs
    customer_id_str = account.linked_customer_id
    dist_id_str = account.linked_distributor_id

    # Outstanding balance from invoices
    inv_q = select(Invoice).where(
        Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])
    )
    if customer_id_str:
        try:
            inv_q = inv_q.where(Invoice.customer_id == uuid.UUID(customer_id_str))
        except Exception:
            pass

    invoices = (await db.execute(inv_q.limit(200))).scalars().all()

    today = date.today()
    outstanding = Decimal("0")
    overdue = Decimal("0")
    current_due = Decimal("0")
    aging_0_30 = Decimal("0")
    aging_31_60 = Decimal("0")
    aging_61_90 = Decimal("0")
    aging_90_plus = Decimal("0")

    recent_invoices = []
    for inv in sorted(invoices, key=lambda x: x.invoice_date, reverse=True)[:5]:
        remaining = (inv.total_amount or Decimal("0")) - (inv.paid_amount or Decimal("0"))
        outstanding += remaining
        if inv.due_date and inv.due_date < today:
            days_past = (today - inv.due_date).days
            overdue += remaining
            if days_past <= 30:
                aging_0_30 += remaining
            elif days_past <= 60:
                aging_31_60 += remaining
            elif days_past <= 90:
                aging_61_90 += remaining
            else:
                aging_90_plus += remaining
        else:
            current_due += remaining
        recent_invoices.append({
            "id": str(inv.id),
            "invoice_no": inv.invoice_no,
            "invoice_date": str(inv.invoice_date),
            "due_date": str(inv.due_date),
            "total_amount": float(inv.total_amount or 0),
            "paid_amount": float(inv.paid_amount or 0),
            "outstanding": float(remaining),
            "status": str(inv.status),
            "currency": inv.currency,
        })

    # Open orders
    so_q = select(func.count(SalesOrder.id)).where(
        SalesOrder.status.notin_(["CANCELLED", "INVOICED"])
    )
    if customer_id_str:
        try:
            so_q = so_q.where(SalesOrder.customer_id == uuid.UUID(customer_id_str))
        except Exception:
            pass
    open_orders = (await db.execute(so_q)).scalar() or 0

    # Recent orders
    ro_q = select(SalesOrder).order_by(SalesOrder.order_date.desc()).limit(5)
    if customer_id_str:
        try:
            ro_q = ro_q.where(SalesOrder.customer_id == uuid.UUID(customer_id_str))
        except Exception:
            pass
    recent_orders_rows = (await db.execute(ro_q)).scalars().all()
    recent_orders = [
        {
            "id": str(o.id),
            "order_no": o.order_no,
            "order_date": str(o.order_date),
            "status": str(o.status),
            "currency": o.currency,
        }
        for o in recent_orders_rows
    ]

    # Recent payments
    pay_q = select(Payment).order_by(Payment.payment_date.desc()).limit(5)
    recent_payments_rows = (await db.execute(pay_q)).scalars().all()
    recent_payments = [
        {"id": str(p.id), "payment_date": str(p.payment_date), "amount": float(p.amount or 0), "method": p.method}
        for p in recent_payments_rows
    ]

    # Open claims
    open_claims = (await db.execute(
        select(func.count(PortalClaim.id)).where(
            and_(
                PortalClaim.portal_account_id == account.id,
                PortalClaim.status.in_([PortalClaimStatus.SUBMITTED, PortalClaimStatus.UNDER_REVIEW]),
            )
        )
    )).scalar() or 0

    return {
        "account_code": account.account_code,
        "account_type": str(account.account_type),
        "outstanding_balance": float(outstanding),
        "overdue_balance": float(overdue),
        "current_due": float(current_due),
        "aging_0_30": float(aging_0_30),
        "aging_31_60": float(aging_31_60),
        "aging_61_90": float(aging_61_90),
        "aging_90_plus": float(aging_90_plus),
        "open_orders": open_orders,
        "recent_orders": recent_orders,
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "open_claims": open_claims,
        "credit_limit": None,
    }


# ── Scoped Order Queries ──────────────────────────────────────────────────────

async def get_portal_orders(db: AsyncSession, account: PortalAccount, status: Optional[str] = None, skip: int = 0, limit: int = 50):
    from app.models.sales import SalesOrder, SOLine
    from sqlalchemy.orm import selectinload as sl

    q = select(SalesOrder).options(sl(SalesOrder.lines))
    if account.linked_customer_id:
        try:
            q = q.where(SalesOrder.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return []
    elif account.linked_distributor_id:
        try:
            q = q.where(SalesOrder.distributor_id == uuid.UUID(account.linked_distributor_id))
        except Exception:
            return []
    else:
        return []
    if status:
        q = q.where(SalesOrder.status == status)
    q = q.order_by(SalesOrder.order_date.desc()).offset(skip).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [_serialize_order(o) for o in rows]


def _serialize_order(o):
    return {
        "id": str(o.id),
        "order_no": o.order_no,
        "order_date": str(o.order_date),
        "requested_delivery_date": str(o.requested_delivery_date),
        "status": str(o.status),
        "currency": o.currency,
        "payment_method": str(o.payment_method),
        "payment_status": str(o.payment_status),
        "line_count": len(o.lines or []),
    }


async def get_portal_order_detail(db: AsyncSession, account: PortalAccount, order_id: str):
    from app.models.sales import SalesOrder, SOLine
    from sqlalchemy.orm import selectinload as sl

    q = (
        select(SalesOrder)
        .options(sl(SalesOrder.lines), sl(SalesOrder.shipments), sl(SalesOrder.invoices))
        .where(SalesOrder.id == uuid.UUID(order_id))
    )
    if account.linked_customer_id:
        try:
            q = q.where(SalesOrder.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return None
    elif account.linked_distributor_id:
        try:
            q = q.where(SalesOrder.distributor_id == uuid.UUID(account.linked_distributor_id))
        except Exception:
            return None
    o = (await db.execute(q)).scalar_one_or_none()
    if not o:
        return None
    d = _serialize_order(o)
    d["lines"] = [
        {
            "id": str(l.id),
            "line_no": l.line_no,
            "product_id": str(l.product_id),
            "ordered_quantity": float(l.ordered_quantity),
            "shipped_quantity": float(l.shipped_quantity),
            "unit": l.unit,
            "unit_price": float(l.unit_price),
            "discount_pct": float(l.discount_pct),
        }
        for l in (o.lines or [])
    ]
    d["shipments"] = [
        {"id": str(s.id), "shipment_no": s.shipment_no, "status": str(s.status), "scheduled_date": str(s.scheduled_date)}
        for s in (o.shipments or [])
    ]
    d["invoices"] = [
        {"id": str(i.id), "invoice_no": i.invoice_no, "status": str(i.status), "total_amount": float(i.total_amount or 0)}
        for i in (o.invoices or [])
    ]
    return d


async def get_portal_shipments(db: AsyncSession, account: PortalAccount, skip: int = 0, limit: int = 50):
    from app.models.sales import Shipment, SalesOrder
    q = (
        select(Shipment)
        .join(SalesOrder, SalesOrder.id == Shipment.so_id)
        .options(selectinload(Shipment.lines))
        .order_by(Shipment.scheduled_date.desc())
        .offset(skip).limit(limit)
    )
    if account.linked_customer_id:
        try:
            q = q.where(SalesOrder.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return []
    elif account.linked_distributor_id:
        try:
            q = q.where(SalesOrder.distributor_id == uuid.UUID(account.linked_distributor_id))
        except Exception:
            return []
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(s.id),
            "shipment_no": s.shipment_no,
            "so_id": str(s.so_id),
            "status": str(s.status),
            "scheduled_date": str(s.scheduled_date),
            "dispatched_date": str(s.dispatched_date) if s.dispatched_date else None,
            "carrier": s.carrier,
            "tracking_number": s.tracking_number,
            "line_count": len(s.lines or []),
        }
        for s in rows
    ]


async def get_portal_invoices(db: AsyncSession, account: PortalAccount, status: Optional[str] = None, skip: int = 0, limit: int = 50):
    from app.models.sales import Invoice

    q = select(Invoice)
    if account.linked_customer_id:
        try:
            q = q.where(Invoice.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return []
    else:
        return []
    if status:
        q = q.where(Invoice.status == status)
    q = q.order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(i.id),
            "invoice_no": i.invoice_no,
            "invoice_date": str(i.invoice_date),
            "due_date": str(i.due_date),
            "status": str(i.status),
            "currency": i.currency,
            "subtotal": float(i.subtotal or 0),
            "tax_amount": float(i.tax_amount or 0),
            "total_amount": float(i.total_amount or 0),
            "paid_amount": float(i.paid_amount or 0),
            "outstanding": float((i.total_amount or 0) - (i.paid_amount or 0)),
        }
        for i in rows
    ]


async def get_portal_payments(db: AsyncSession, account: PortalAccount, skip: int = 0, limit: int = 50):
    from app.models.sales import Payment, Invoice

    q = (
        select(Payment)
        .join(Invoice, Invoice.id == Payment.invoice_id)
    )
    if account.linked_customer_id:
        try:
            q = q.where(Invoice.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return []
    else:
        return []
    q = q.order_by(Payment.payment_date.desc()).offset(skip).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(p.id),
            "invoice_id": str(p.invoice_id),
            "payment_date": str(p.payment_date),
            "amount": float(p.amount or 0),
            "method": p.method,
            "reference": p.reference,
        }
        for p in rows
    ]


async def get_portal_statement(db: AsyncSession, account: PortalAccount, from_date: Optional[date] = None, to_date: Optional[date] = None):
    invoices = await get_portal_invoices(db, account, limit=200)
    payments = await get_portal_payments(db, account, limit=200)
    if from_date:
        invoices = [i for i in invoices if i["invoice_date"] >= str(from_date)]
        payments = [p for p in payments if p["payment_date"] >= str(from_date)]
    if to_date:
        invoices = [i for i in invoices if i["invoice_date"] <= str(to_date)]
        payments = [p for p in payments if p["payment_date"] <= str(to_date)]
    total_invoiced = sum(i["total_amount"] for i in invoices)
    total_paid = sum(p["amount"] for p in payments)
    return {
        "account_code": account.account_code,
        "from_date": str(from_date) if from_date else None,
        "to_date": str(to_date) if to_date else None,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "outstanding_balance": total_invoiced - total_paid,
        "invoices": invoices,
        "payments": payments,
    }


# ── Claims ─────────────────────────────────────────────────────────────────────

async def get_claims(db: AsyncSession, account_id: str, status: Optional[str] = None):
    q = select(PortalClaim).where(PortalClaim.portal_account_id == uuid.UUID(account_id))
    if status:
        q = q.where(PortalClaim.status == status)
    q = q.order_by(PortalClaim.created_at.desc())
    return (await db.execute(q)).scalars().all()


async def create_claim(db: AsyncSession, account_id: str, user_id: str, data: PortalClaimCreate) -> PortalClaim:
    claim = PortalClaim(
        claim_no=await _next_claim_no(db),
        portal_account_id=uuid.UUID(account_id),
        submitted_by=user_id,
        **data.model_dump(),
    )
    db.add(claim)
    await _log_activity(db, user_id, account_id, PortalActivityType.SUBMIT_CLAIM, "claim")
    await db.commit()
    await db.refresh(claim)
    return claim


async def review_claim(db: AsyncSession, claim_id: str, data: PortalClaimReview) -> Optional[PortalClaim]:
    claim = await db.get(PortalClaim, uuid.UUID(claim_id))
    if not claim:
        return None
    claim.status = data.status
    if data.resolution_notes:
        claim.resolution_notes = data.resolution_notes
    if data.resolved_by:
        claim.resolved_by = data.resolved_by
        claim.resolved_date = date.today()
    await db.commit()
    await db.refresh(claim)
    return claim


# ── Draft Orders ──────────────────────────────────────────────────────────────

async def get_draft_orders(db: AsyncSession, account_id: str, status: Optional[str] = None):
    q = (
        select(PortalDraftOrder)
        .options(selectinload(PortalDraftOrder.lines))
        .where(PortalDraftOrder.portal_account_id == uuid.UUID(account_id))
    )
    if status:
        q = q.where(PortalDraftOrder.status == status)
    q = q.order_by(PortalDraftOrder.created_at.desc())
    return (await db.execute(q)).scalars().all()


async def create_draft_order(db: AsyncSession, account_id: str, user_id: str, data: PortalDraftOrderCreate) -> PortalDraftOrder:
    draft = PortalDraftOrder(
        draft_no=await _next_draft_no(db),
        portal_account_id=uuid.UUID(account_id),
        submitted_by=user_id,
        source_order_id=data.source_order_id,
        requested_delivery_date=data.requested_delivery_date,
        delivery_address=data.delivery_address,
        order_comments=data.order_comments,
        currency=data.currency,
        status=PortalDraftOrderStatus.DRAFT,
    )
    db.add(draft)
    await db.flush()
    total = Decimal("0")
    for ld in data.lines:
        unit_price = ld.unit_price or Decimal("0")
        line_total = ld.quantity * unit_price
        total += line_total
        db.add(PortalDraftOrderLine(
            draft_order_id=draft.id,
            product_id=ld.product_id,
            product_name=ld.product_name,
            product_sku=ld.product_sku,
            quantity=ld.quantity,
            unit=ld.unit,
            unit_price=unit_price,
            line_total=line_total,
            notes=ld.notes,
        ))
    draft.total_amount = total
    await _log_activity(db, user_id, account_id, PortalActivityType.SUBMIT_ORDER, "draft_order", str(draft.id))
    await db.commit()
    await db.refresh(draft)
    return draft


async def submit_draft_order(db: AsyncSession, draft_id: str) -> Optional[PortalDraftOrder]:
    result = await db.execute(
        select(PortalDraftOrder).options(selectinload(PortalDraftOrder.lines))
        .where(PortalDraftOrder.id == uuid.UUID(draft_id))
    )
    draft = result.scalar_one_or_none()
    if not draft:
        return None
    draft.status = PortalDraftOrderStatus.SUBMITTED
    await db.commit()
    await db.refresh(draft)
    return draft


async def review_draft_order(db: AsyncSession, draft_id: str, data: PortalDraftOrderReview) -> Optional[PortalDraftOrder]:
    result = await db.execute(
        select(PortalDraftOrder).options(selectinload(PortalDraftOrder.lines))
        .where(PortalDraftOrder.id == uuid.UUID(draft_id))
    )
    draft = result.scalar_one_or_none()
    if not draft:
        return None
    draft.status = data.status
    if data.review_notes:
        draft.review_notes = data.review_notes
    if data.reviewed_by:
        draft.reviewed_by = data.reviewed_by
    if data.converted_order_id:
        draft.converted_order_id = data.converted_order_id
    await db.commit()
    await db.refresh(draft)
    return draft


async def reorder_from_order(db: AsyncSession, account: PortalAccount, user_id: str, source_order_id: str) -> Optional[PortalDraftOrder]:
    from app.models.sales import SalesOrder
    from sqlalchemy.orm import selectinload as sl
    q = select(SalesOrder).options(sl(SalesOrder.lines)).where(SalesOrder.id == uuid.UUID(source_order_id))
    if account.linked_customer_id:
        try:
            q = q.where(SalesOrder.customer_id == uuid.UUID(account.linked_customer_id))
        except Exception:
            return None
    source = (await db.execute(q)).scalar_one_or_none()
    if not source:
        return None
    from app.schemas.portal import PortalDraftOrderCreate, PortalDraftOrderLineCreate
    lines = [
        PortalDraftOrderLineCreate(
            product_id=str(l.product_id),
            quantity=l.ordered_quantity,
            unit=l.unit,
            unit_price=l.unit_price,
        )
        for l in (source.lines or [])
    ]
    data = PortalDraftOrderCreate(
        source_order_id=source_order_id,
        currency=source.currency,
        lines=lines,
    )
    return await create_draft_order(db, str(account.id), user_id, data)


# ── Activity Logs ─────────────────────────────────────────────────────────────

async def get_activity_logs(db: AsyncSession, account_id: Optional[str] = None, user_id: Optional[str] = None, limit: int = 100):
    q = select(PortalActivityLog).order_by(PortalActivityLog.activity_datetime.desc()).limit(limit)
    if account_id:
        q = q.where(PortalActivityLog.portal_account_id == uuid.UUID(account_id))
    if user_id:
        q = q.where(PortalActivityLog.portal_user_id == uuid.UUID(user_id))
    return (await db.execute(q)).scalars().all()


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_support_assistant(db: AsyncSession) -> List[PortalAIRecommendation]:
    recs = []
    # Accounts with open claims > 3
    claim_counts = (await db.execute(
        select(PortalClaim.portal_account_id, func.count(PortalClaim.id))
        .where(PortalClaim.status.in_([PortalClaimStatus.SUBMITTED, PortalClaimStatus.UNDER_REVIEW]))
        .group_by(PortalClaim.portal_account_id)
        .having(func.count(PortalClaim.id) >= 3)
    )).all()
    for row in claim_counts:
        rec = PortalAIRecommendation(
            agent_type=PortalAIAgentType.SUPPORT_ASSISTANT,
            portal_account_id=row[0],
            title="Multiple Open Claims Detected",
            body=f"Portal account has {row[1]} open claims. Proactively contact this customer to resolve issues and prevent escalation.",
            priority="HIGH",
            action_label="Contact Customer",
            status=PortalAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)
    await db.commit()
    return recs


async def run_friction_monitor(db: AsyncSession) -> List[PortalAIRecommendation]:
    recs = []
    # Accounts with many logins but no orders in last 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    login_counts = (await db.execute(
        select(PortalActivityLog.portal_account_id, func.count(PortalActivityLog.id))
        .where(
            and_(
                PortalActivityLog.activity_type == PortalActivityType.LOGIN,
                PortalActivityLog.activity_datetime >= cutoff,
            )
        )
        .group_by(PortalActivityLog.portal_account_id)
        .having(func.count(PortalActivityLog.id) >= 5)
    )).all()
    order_accounts = {
        str(row[0])
        for row in (await db.execute(
            select(PortalActivityLog.portal_account_id)
            .where(
                and_(
                    PortalActivityLog.activity_type == PortalActivityType.SUBMIT_ORDER,
                    PortalActivityLog.activity_datetime >= cutoff,
                )
            )
            .distinct()
        )).all()
    }
    for row in login_counts:
        if str(row[0]) not in order_accounts:
            rec = PortalAIRecommendation(
                agent_type=PortalAIAgentType.FRICTION_MONITOR,
                portal_account_id=row[0],
                title="Portal Browsing Without Ordering",
                body=f"This portal account logged in {row[1]} times in 30 days but placed no orders. Possible friction in the order flow or pricing concern. Follow up.",
                priority="MEDIUM",
                action_label="Investigate Friction",
                status=PortalAIRecStatus.PENDING,
            )
            db.add(rec)
            recs.append(rec)
    await db.commit()
    return recs


async def run_commercial_opportunity(db: AsyncSession) -> List[PortalAIRecommendation]:
    recs = []
    # Accounts that last ordered > 45 days ago — nudge reorder
    cutoff = datetime.utcnow() - timedelta(days=45)
    last_order_by_account = (await db.execute(
        select(PortalActivityLog.portal_account_id, func.max(PortalActivityLog.activity_datetime))
        .where(PortalActivityLog.activity_type == PortalActivityType.SUBMIT_ORDER)
        .group_by(PortalActivityLog.portal_account_id)
        .having(func.max(PortalActivityLog.activity_datetime) < cutoff)
        .limit(20)
    )).all()
    for row in last_order_by_account:
        rec = PortalAIRecommendation(
            agent_type=PortalAIAgentType.COMMERCIAL_OPPORTUNITY,
            portal_account_id=row[0],
            title="Reorder Opportunity",
            body=f"This portal account has not placed an order in 45+ days. Last order was on {row[1].date() if row[1] else 'N/A'}. Consider a reorder nudge or promotional offer.",
            priority="MEDIUM",
            action_label="Send Reorder Nudge",
            status=PortalAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)
    await db.commit()
    return recs


async def get_ai_recommendations(db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None):
    q = select(PortalAIRecommendation).order_by(PortalAIRecommendation.created_at.desc())
    if agent_type:
        q = q.where(PortalAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(PortalAIRecommendation.status == status)
    return (await db.execute(q)).scalars().all()


async def ack_ai_recommendation(db: AsyncSession, rec_id: str, data: PortalAIRecAck) -> Optional[PortalAIRecommendation]:
    rec = await db.get(PortalAIRecommendation, uuid.UUID(rec_id))
    if not rec:
        return None
    rec.status = data.status
    if data.acknowledged_by:
        rec.acknowledged_by = data.acknowledged_by
    if data.notes:
        rec.notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Reports ───────────────────────────────────────────────────────────────────

async def portal_adoption_report(db: AsyncSession) -> dict:
    total_accounts = (await db.execute(select(func.count(PortalAccount.id)))).scalar() or 0
    active_accounts = (await db.execute(
        select(func.count(PortalAccount.id)).where(PortalAccount.portal_status == PortalAccountStatus.ACTIVE)
    )).scalar() or 0
    total_users = (await db.execute(select(func.count(PortalUser.id)))).scalar() or 0
    active_users = (await db.execute(
        select(func.count(PortalUser.id)).where(PortalUser.is_active.is_(True))
    )).scalar() or 0
    cutoff = datetime.utcnow() - timedelta(days=30)
    logins_30d = (await db.execute(
        select(func.count(PortalActivityLog.id))
        .where(and_(
            PortalActivityLog.activity_type == PortalActivityType.LOGIN,
            PortalActivityLog.activity_datetime >= cutoff,
        ))
    )).scalar() or 0
    orders_30d = (await db.execute(
        select(func.count(PortalActivityLog.id))
        .where(and_(
            PortalActivityLog.activity_type == PortalActivityType.SUBMIT_ORDER,
            PortalActivityLog.activity_datetime >= cutoff,
        ))
    )).scalar() or 0
    claims_30d = (await db.execute(
        select(func.count(PortalClaim.id)).where(PortalClaim.created_at >= cutoff)
    )).scalar() or 0
    return {
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "activation_rate_pct": round(active_accounts / max(total_accounts, 1) * 100, 1),
        "total_users": total_users,
        "active_users": active_users,
        "logins_last_30_days": logins_30d,
        "orders_submitted_last_30_days": orders_30d,
        "claims_submitted_last_30_days": claims_30d,
    }
