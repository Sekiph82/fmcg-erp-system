"""
Business logic guards — enforce financial and operational rules
that protect against fraud, manipulation, and policy violations.

These are HELPER functions called from service/endpoint layers.
They raise HTTPException when a guard fails.

Guards implemented:
  - margin_floor_check()         — pricing below minimum margin
  - duplicate_payment_check()    — same payment within time window
  - stock_adjustment_requires_reason() — negative adjustments need reason
  - expense_policy_check()       — expense over threshold needs approval
  - payroll_statutory_completeness() — payroll requires all statutory IDs
"""
from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


# ── Pricing margin guard ──────────────────────────────────────────────────────

DEFAULT_MINIMUM_MARGIN_PCT = Decimal("5.0")   # 5% minimum gross margin

async def margin_floor_check(
    selling_price: Decimal,
    cost_price: Decimal,
    minimum_margin_pct: Decimal = DEFAULT_MINIMUM_MARGIN_PCT,
    approver_override: bool = False,
) -> None:
    """
    Block pricing that violates minimum margin policy.
    Pass approver_override=True if the user holds sales.approve permission.
    """
    if cost_price <= 0:
        return
    margin = ((selling_price - cost_price) / cost_price) * 100
    if margin < minimum_margin_pct:
        if not approver_override:
            log.warning(
                "Margin floor violated: selling=%s cost=%s margin=%.2f%% min=%.2f%%",
                selling_price, cost_price, margin, minimum_margin_pct,
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "margin_floor_violation",
                    "detail": f"Selling price yields {float(margin):.1f}% margin, below minimum {float(minimum_margin_pct):.1f}%.",
                    "requires": "sales.approve permission to override",
                },
            )
        log.info(
            "Margin floor override by approver: margin=%.2f%%",
            margin,
        )


# ── Duplicate payment guard ───────────────────────────────────────────────────

DUPLICATE_WINDOW_MINUTES = 5

async def duplicate_payment_check(
    db: AsyncSession,
    customer_id: str,
    amount: Decimal,
    payment_method: str,
) -> None:
    """
    Detect potential duplicate payments: same customer, same amount, same method
    within DUPLICATE_WINDOW_MINUTES.
    """
    try:
        from app.models.sales import Payment
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=DUPLICATE_WINDOW_MINUTES)
        existing = (await db.execute(
            select(Payment)
            .where(Payment.customer_id == customer_id)  # type: ignore[attr-defined]
            .where(Payment.amount == amount)
            .where(Payment.created_at >= cutoff)
        )).scalar_one_or_none()

        if existing:
            log.warning(
                "Duplicate payment guard: customer=%s amount=%s method=%s found_id=%s",
                customer_id, amount, payment_method, existing.id,
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "potential_duplicate_payment",
                    "detail": f"A payment of the same amount was received in the last {DUPLICATE_WINDOW_MINUTES} minutes.",
                    "existing_payment_id": str(existing.id),
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        log.debug("Duplicate payment check skipped: %s", e)


# ── Stock adjustment guard ────────────────────────────────────────────────────

def stock_adjustment_requires_reason(
    quantity_delta: Decimal,
    reason: Optional[str],
    allow_negative_without_reason: bool = False,
) -> None:
    """
    Require a reason for any negative stock adjustment.
    """
    if quantity_delta < 0 and not reason:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "reason_required",
                "detail": "A reason is required for negative stock adjustments.",
            },
        )


# ── Expense policy guard ──────────────────────────────────────────────────────

DEFAULT_EXPENSE_APPROVAL_THRESHOLD = Decimal("10000")  # KES 10,000

def expense_approval_required(
    amount: Decimal,
    threshold: Decimal = DEFAULT_EXPENSE_APPROVAL_THRESHOLD,
    already_approved: bool = False,
) -> bool:
    """
    Returns True if the expense requires manager approval.
    Raises if amount exceeds threshold AND not already approved.
    """
    if amount > threshold and not already_approved:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "approval_required",
                "detail": f"Expenses over KES {float(threshold):,.0f} require manager approval before submission.",
                "threshold_kes": float(threshold),
            },
        )
    return amount > threshold


# ── Payroll statutory completeness guard ─────────────────────────────────────

def payroll_statutory_completeness(
    kra_pin: Optional[str],
    nhif_no: Optional[str],
    nssf_no: Optional[str],
    employee_name: str = "employee",
) -> None:
    """
    Block payroll run if employee is missing required statutory identifiers.
    """
    missing = []
    if not kra_pin:
        missing.append("KRA PIN")
    if not nhif_no:
        missing.append("NHIF number")
    if not nssf_no:
        missing.append("NSSF number")
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "missing_statutory_data",
                "detail": f"Cannot process payroll for {employee_name}. Missing: {', '.join(missing)}.",
                "missing_fields": missing,
            },
        )


# ── Invoice match policy guard ────────────────────────────────────────────────

def invoice_match_payment_block(
    invoice_id: str,
    match_status: str,
    policy_blocks_payment: bool = True,
) -> None:
    """
    Block payment release if invoice is not matched and policy requires matching.
    """
    BLOCKED_STATUSES = {"UNMATCHED", "DISPUTED", "ON_HOLD"}
    if policy_blocks_payment and match_status in BLOCKED_STATUSES:
        log.warning(
            "Payment blocked: invoice=%s match_status=%s",
            invoice_id, match_status,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "payment_blocked_by_match_policy",
                "detail": f"Invoice {invoice_id} has match status '{match_status}'. Resolve the match before releasing payment.",
                "match_status": match_status,
            },
        )
