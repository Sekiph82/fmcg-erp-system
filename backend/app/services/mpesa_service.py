"""
M-Pesa (Safaricom Daraja) payment service — sales module.

Delegates STK Push to mpesa_daraja_service, which handles OAuth2 token fetch,
real Daraja API calls, and simulation fallback when credentials are not configured.

When MPESA_CONFIGURED is False, mpesa_daraja_service returns a simulation response
(ws_CO_SIM_* prefix). When credentials are set, real Daraja calls are made.
No changes to this file or calling code are needed when credentials are added.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.services import mpesa_daraja_service as _daraja

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import (
    SalesOrder, MpesaTransaction, MpesaTxStatus, SOPaymentStatus, PaymentMethod,
)

logger = logging.getLogger(__name__)


# ── Daraja delegation ─────────────────────────────────────────────────────────

async def _stk_push_request(phone: str, amount: Decimal, reference: str) -> str:
    """
    Delegates to mpesa_daraja_service._stk_push_request.
    Returns the CheckoutRequestID (simulation ID when credentials absent, real ID otherwise).
    """
    checkout_id, _merchant_id, _resp = await _daraja._stk_push_request(
        phone=phone,
        amount=int(amount),
        reference=reference,
    )
    return checkout_id


# ── Public API ────────────────────────────────────────────────────────────────

async def initiate_payment(
    db: AsyncSession,
    so: SalesOrder,
    phone_number: str,
    amount: Decimal,
    user_id: uuid.UUID,
) -> MpesaTransaction:
    """
    Create a pending MpesaTransaction and fire an STK Push to the customer's phone.
    Multiple attempts are allowed on the same SO (e.g. wrong number, timeout).
    """
    if so.payment_method != PaymentMethod.MPESA:
        raise HTTPException(
            422,
            "Sales order payment method is not M-Pesa. "
            "Update payment_method to 'mpesa' before initiating.",
        )
    if so.payment_status == SOPaymentStatus.PAID:
        raise HTTPException(422, "Sales order is already fully paid.")

    checkout_request_id = await _stk_push_request(
        phone=phone_number,
        amount=amount,
        reference=so.order_no,
    )

    tx = MpesaTransaction(
        so_id=so.id,
        phone_number=phone_number,
        amount=amount,
        mpesa_request_id=checkout_request_id,
        status=MpesaTxStatus.PENDING,
        initiated_by_id=user_id,
    )
    db.add(tx)

    # Track latest request on the SO for quick lookup
    so.mpesa_request_id = checkout_request_id
    await db.flush()
    await db.refresh(tx)
    return tx


async def handle_callback(
    db: AsyncSession,
    checkout_request_id: str,
    result_code: int,
    result_description: str,
    mpesa_receipt_number: Optional[str] = None,
    amount: Optional[Decimal] = None,
) -> MpesaTransaction:
    """
    Process a Daraja STK Push callback.
    Updates the transaction and recalculates SO payment_status.
    """
    result = await db.execute(
        select(MpesaTransaction)
        .where(MpesaTransaction.mpesa_request_id == checkout_request_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, f"No pending transaction for CheckoutRequestID {checkout_request_id}")

    tx.result_code = result_code
    tx.result_description = result_description

    if result_code == 0:
        tx.status = MpesaTxStatus.COMPLETED
        tx.mpesa_reference = mpesa_receipt_number
        # Update SO
        so_result = await db.execute(
            select(SalesOrder).where(SalesOrder.id == tx.so_id).with_for_update()
        )
        so = so_result.scalar_one()
        so.mpesa_reference = mpesa_receipt_number

        # Recalculate total paid across completed transactions
        paid_result = await db.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.so_id == so.id,
                MpesaTransaction.status == MpesaTxStatus.COMPLETED,
            )
        )
        completed = list(paid_result.scalars().all())
        total_paid = sum(t.amount for t in completed)

        # We need the SO total to determine fully vs partially paid.
        # The SO total is derived from lines; use a simple threshold.
        # If we don't have lines loaded we treat any payment as partially paid
        # until the caller (endpoint) confirms the full amount.
        so.payment_status = SOPaymentStatus.PARTIALLY_PAID if total_paid > 0 else SOPaymentStatus.PENDING
        # Caller may upgrade to PAID via _maybe_mark_paid after checking SO total.
    else:
        tx.status = MpesaTxStatus.FAILED
        # If there's no completed transaction on this SO, mark payment as failed
        paid_result = await db.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.so_id == tx.so_id,
                MpesaTransaction.status == MpesaTxStatus.COMPLETED,
            )
        )
        any_paid = paid_result.scalar_one_or_none()
        if not any_paid:
            so_result = await db.execute(
                select(SalesOrder).where(SalesOrder.id == tx.so_id).with_for_update()
            )
            so = so_result.scalar_one()
            so.payment_status = SOPaymentStatus.FAILED

    await db.flush()
    await db.refresh(tx)
    return tx


async def recalculate_payment_status(db: AsyncSession, so: SalesOrder, so_total: Decimal) -> None:
    """
    Re-examine completed transactions for `so` and set payment_status accordingly.
    Call this after handle_callback when you have access to the SO total.
    """
    paid_result = await db.execute(
        select(MpesaTransaction).where(
            MpesaTransaction.so_id == so.id,
            MpesaTransaction.status == MpesaTxStatus.COMPLETED,
        )
    )
    completed = list(paid_result.scalars().all())
    total_paid = sum(t.amount for t in completed)

    if total_paid >= so_total - Decimal("0.005"):
        so.payment_status = SOPaymentStatus.PAID
    elif total_paid > 0:
        so.payment_status = SOPaymentStatus.PARTIALLY_PAID
    await db.flush()


# ── Dispatch guard ────────────────────────────────────────────────────────────

def assert_payment_cleared_for_dispatch(so: SalesOrder, customer_is_prepaid: bool) -> None:
    """
    Raises HTTPException if dispatch is blocked by unpaid prepaid requirement.
    Call this before dispatching a shipment.
    """
    if not customer_is_prepaid:
        return  # postpaid / credit customers ship first, pay later
    if so.payment_status != SOPaymentStatus.PAID:
        raise HTTPException(
            422,
            detail={
                "error": "PAYMENT_REQUIRED",
                "message": (
                    "This customer requires prepayment. "
                    f"Current payment status: {so.payment_status.value}. "
                    "Complete M-Pesa payment before dispatching."
                ),
                "payment_status": so.payment_status.value,
            },
        )
