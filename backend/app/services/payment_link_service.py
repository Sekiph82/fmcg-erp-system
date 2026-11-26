"""M45.S01.T021 customer payment links for an invoice balance.

- The link carries a 256-bit random token (only its SHA-256 is stored); unknown tokens are 404, expired/revoked 410.
- The customer page shows invoice number, customer and the open balance; payment by M-Pesa STK push through the
  existing Daraja service; card payment through the Pesapal hosted checkout (card_payment_service, M48.S01.T010).
- Settlement happens only from the provider callback, once per transaction (unique attempt per M-Pesa transaction):
  a real payment becomes a PENDING cash collection (MPESA, receipt as code), which finance confirms into the ledger
  through the existing collections flow. Without Daraja credentials the push is simulated: the attempt and link are
  marked TEST_SETTLED / TEST_PAID and nothing reaches collections or the ledger (never "paid" without a provider).
- Partial payments are allowed unless the link forbids them; the link is PAID once the invoice is fully covered.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payments_hub import PaymentLink, PaymentLinkAttempt


PENDING_TTL = timedelta(minutes=15)    # an STK push not answered by then no longer reserves the balance (M46.S01.T008)


class LinkError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def open_balance(db: AsyncSession, inv) -> Decimal:
    """Invoice balance minus collections awaiting confirmation and payments still pending on its links."""
    from app.api.v1.endpoints.field_app import open_to_collect
    pending = (await db.execute(select(func.coalesce(func.sum(PaymentLinkAttempt.amount), 0))
                                .join(PaymentLink, PaymentLink.id == PaymentLinkAttempt.link_id)
                                .where(PaymentLink.invoice_id == inv.id, PaymentLinkAttempt.status == "PENDING",
                                       PaymentLinkAttempt.created_at >= _now() - PENDING_TTL))).scalar_one()
    from app.services.card_payment_service import pending_reserved
    pending = Decimal(pending) + await pending_reserved(db, inv.id)    # unpaid hosted card checkouts reserve too
    return max(Decimal("0"), Decimal(await open_to_collect(db, inv)) - pending).quantize(Decimal("0.01"))


async def create(db: AsyncSession, invoice_id, user_id, days: int, allow_partial: bool) -> tuple[PaymentLink, str]:
    from app.models.sales import Invoice
    inv = await db.get(Invoice, invoice_id)
    if inv is None:
        raise LinkError(404, "Invoice not found")
    if inv.status.value not in ("ISSUED", "PARTIALLY_PAID", "OVERDUE"):
        raise LinkError(409, "Only open invoices can be paid by link.")
    if await open_balance(db, inv) <= 0:
        raise LinkError(409, "Nothing left to pay on this invoice.")
    token = secrets.token_urlsafe(32)
    link = PaymentLink(token_hash=digest(token), invoice_id=inv.id, currency=inv.currency, allow_partial=allow_partial,
                       expires_at=_now() + timedelta(days=max(1, min(days, 60))), created_by_id=user_id)
    db.add(link)
    await db.flush()
    return link, token


async def resolve(db: AsyncSession, token: str, lock: bool = False) -> PaymentLink:
    q = select(PaymentLink).where(PaymentLink.token_hash == digest(token or ""))
    link = (await db.execute(q.with_for_update() if lock else q)).scalar_one_or_none()
    if link is None:
        raise LinkError(404, "This payment link does not exist.")
    if link.revoked_at is not None or link.status == "REVOKED":
        raise LinkError(410, "This payment link was cancelled.")
    if link.expires_at <= _now() and link.status == "ACTIVE":
        raise LinkError(410, "This payment link has expired.")
    return link


async def public_view(db: AsyncSession, link: PaymentLink) -> dict:
    from app.core.config import settings
    from app.models.sales import Customer, Invoice
    from app.services import card_payment_service as cards
    inv = await db.get(Invoice, link.invoice_id)
    cust = await db.get(Customer, inv.customer_id)
    receipts = list((await db.execute(select(PaymentLinkAttempt.receipt, PaymentLinkAttempt.amount, PaymentLinkAttempt.status)
                                      .where(PaymentLinkAttempt.link_id == link.id,
                                             PaymentLinkAttempt.status.in_(("SETTLED", "TEST_SETTLED"))))).all())
    return {"invoice_no": inv.invoice_no, "customer": cust.name if cust else None, "currency": link.currency,
            "amount_due": str(await open_balance(db, inv)), "status": link.status, "allow_partial": link.allow_partial,
            "expires_at": link.expires_at.isoformat(),
            "providers": {"mpesa": "LIVE" if settings.MPESA_CONFIGURED else "SIMULATED (no real money)", "card": cards.mode(await cards.config(db))},
            "receipts": [{"receipt": r, "amount": str(a), "test": s == "TEST_SETTLED"} for r, a, s in receipts]}


async def pay_mpesa(db: AsyncSession, token: str, phone: str, amount: Optional[Decimal]) -> PaymentLinkAttempt:
    from app.models.sales import Invoice
    from app.services import mpesa_daraja_service as daraja
    link = await resolve(db, token, lock=True)
    if link.status != "ACTIVE":
        raise LinkError(409, "This invoice is already paid.")
    recent = (await db.execute(select(func.count()).select_from(PaymentLinkAttempt).where(
        PaymentLinkAttempt.link_id == link.id, PaymentLinkAttempt.created_at >= _now() - timedelta(hours=1)))).scalar_one()
    if recent >= 5:
        raise LinkError(429, "Too many payment attempts on this link; try again in an hour.")
    inv = await db.get(Invoice, link.invoice_id, with_for_update=True, populate_existing=True)
    due = await open_balance(db, inv)
    amount = due if amount is None else Decimal(amount)
    if amount != amount.quantize(Decimal("1")):
        raise LinkError(422, "M-Pesa takes whole shillings; enter a whole amount.")
    if amount <= 0 or amount > due:
        raise LinkError(422, f"Enter an amount between 1 and {due}.")
    if amount < due and not link.allow_partial:
        raise LinkError(422, "This link only accepts the full amount.")
    if link.currency != "KES":
        raise LinkError(422, "M-Pesa takes KES only.")
    attempt_ref = f"PL-{inv.invoice_no}-{secrets.token_hex(3).upper()}"[:40]
    tx = await daraja.initiate_payment(db, phone, amount, attempt_ref, related_entity_type="payment_link",
                                       related_entity_id=str(link.id))
    simulated = bool(json.loads(tx.response_payload or "{}").get("_simulated"))
    a = PaymentLinkAttempt(link_id=link.id, mpesa_tx_id=tx.id, amount=amount, simulated=simulated)
    db.add(a)
    await db.flush()
    return a


async def on_mpesa_callback(db: AsyncSession, tx) -> Optional[PaymentLinkAttempt]:
    """Called after the Daraja callback updated `tx`; settles the matching attempt exactly once."""
    from app.models.field_ops import CashCollection
    from app.models.integrations import MpesaTxStatus
    from app.models.sales import Invoice
    if tx is None or tx.related_entity_type != "payment_link":
        return None
    # M48.S01.T010 race audit: concurrent/duplicate callbacks serialise on the attempt row; populate_existing makes the
    # second one see the first one's SETTLED status (never a stale identity-map copy), so it books nothing.
    a = (await db.execute(select(PaymentLinkAttempt).where(PaymentLinkAttempt.mpesa_tx_id == tx.id).with_for_update()
                          .execution_options(populate_existing=True))).scalar_one_or_none()
    if a is None or a.status not in ("PENDING", "EXPIRED"):
        return a                                   # unknown or already settled: replays change nothing
                                                   # (a late success after expiry still settles: the money moved)
    link = await db.get(PaymentLink, a.link_id, with_for_update=True, populate_existing=True)
    if tx.status != MpesaTxStatus.SUCCESS:
        a.status = "FAILED"
        return a
    a.receipt, a.settled_at = tx.mpesa_receipt_number or None, _now()
    inv = await db.get(Invoice, link.invoice_id)
    if a.simulated:
        a.status = "TEST_SETTLED"                  # simulator money: never a collection, never paid
        link.settled_amount = Decimal(link.settled_amount) + a.amount
        if link.settled_amount >= Decimal(inv.total_amount) - Decimal(inv.paid_amount):
            link.status = "TEST_PAID"
        return a
    c = CashCollection(collection_no=f"COL-PL-{secrets.token_hex(5).upper()}", customer_id=inv.customer_id, invoice_id=inv.id,
                       sales_order_id=inv.so_id, collection_date=date.today(), method="MPESA", amount=a.amount,
                       currency=inv.currency, reference=f"Payment link {link.id}", mpesa_code=a.receipt,
                       mpesa_phone=tx.phone_number, status="PENDING", client_ref=f"paylink:{tx.id}"[:64],
                       notes="Paid by the customer through a payment link (STK push). Finance confirms to post.")
    db.add(c)
    await db.flush()
    a.status, a.collection_id = "SETTLED", c.id
    link.settled_amount = Decimal(link.settled_amount) + a.amount
    from app.api.v1.endpoints.field_app import open_to_collect
    if await open_to_collect(db, inv) <= 0:
        link.status = "PAID"
    return a


async def expire_stale(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Mark pushes with no callback after PENDING_TTL as EXPIRED, releasing the balance they reserved."""
    from sqlalchemy import update
    now = now or _now()
    from app.services import card_payment_service as cards
    res = await db.execute(update(PaymentLinkAttempt).where(PaymentLinkAttempt.status == "PENDING",
                                                            PaymentLinkAttempt.created_at < now - PENDING_TTL)
                           .values(status="EXPIRED"))
    return (res.rowcount or 0) + await cards.expire_stale(db, now)
