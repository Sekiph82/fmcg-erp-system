"""
3-Way Invoice Matching Service
PO ↔ GRN ↔ Supplier Invoice comparison engine with:
  - tolerance rules, duplicate detection, approval workflow,
  - payment hold integration, cumulative billing guard, 3 AI agents
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice_match import (
    InvoiceMatchHeader, InvoiceMatchLine, InvoiceMatchGRNLink,
    InvoiceMatchTolerance, DuplicateInvoiceLog, InvoiceMatchReview,
    IMAIRecommendation,
    MatchLineStatus, MatchOverallStatus, DuplicateRisk,
)
from app.models.finance import PurchaseInvoice, PurchaseInvoiceLine
from app.models.procurement import PurchaseOrder, POLine, GoodsReceipt, GRNLine, GRNStatus, POStatus
from app.models.master import Material
from app.schemas.invoice_match import (
    ToleranceRuleCreate, ToleranceRuleUpdate, ReviewCreate, RunMatchRequest,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Any, dp: int = 4) -> Decimal:
    return _D(v).quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


def _pct(part: Decimal, base: Decimal) -> Optional[Decimal]:
    if base == 0:
        return None
    return _R(part / base * 100, 3)


async def _next_match_no(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(InvoiceMatchHeader))
    n = (result.scalar() or 0) + 1
    return f"3WM-{n:06d}"


async def _lock_match_source_rows(
    db: AsyncSession,
    invoice_id: UUID,
) -> tuple[PurchaseInvoice, Optional[PurchaseOrder]]:
    """Serialize matching/review operations using one stable invoice→PO lock order."""
    invoice_q = await db.execute(
        select(PurchaseInvoice)
        .options(selectinload(PurchaseInvoice.lines))
        .where(PurchaseInvoice.id == invoice_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    invoice = invoice_q.scalar_one_or_none()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    po: Optional[PurchaseOrder] = None
    if invoice.po_id:
        po_q = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == invoice.po_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        po = po_q.scalar_one_or_none()
    return invoice, po


# ── Tolerance Rule CRUD ───────────────────────────────────────────────────────

async def create_tolerance_rule(db: AsyncSession, payload: ToleranceRuleCreate) -> InvoiceMatchTolerance:
    rule = InvoiceMatchTolerance(**payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def list_tolerance_rules(db: AsyncSession, active_only: bool = False) -> List[InvoiceMatchTolerance]:
    q = select(InvoiceMatchTolerance).order_by(InvoiceMatchTolerance.priority)
    if active_only:
        q = q.where(InvoiceMatchTolerance.is_active == True)
    result = await db.execute(q)
    return list(result.scalars().all())


async def update_tolerance_rule(db: AsyncSession, rule_id: UUID, payload: ToleranceRuleUpdate) -> Optional[InvoiceMatchTolerance]:
    q = await db.execute(
        select(InvoiceMatchTolerance)
        .where(InvoiceMatchTolerance.id == rule_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    rule = q.scalar_one_or_none()
    if not rule:
        return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return rule


async def _find_tolerance(
    db: AsyncSession, supplier_id: Optional[UUID], item_category: Optional[str]
) -> Optional[InvoiceMatchTolerance]:
    """Find the most specific applicable tolerance rule."""
    rules_q = await db.execute(
        select(InvoiceMatchTolerance)
        .where(InvoiceMatchTolerance.is_active == True)
        .order_by(InvoiceMatchTolerance.priority)
    )
    rules = list(rules_q.scalars().all())
    # Prefer supplier+category > supplier only > category only > global
    for rule in rules:
        if rule.supplier_id == supplier_id and rule.item_category == item_category:
            return rule
    for rule in rules:
        if rule.supplier_id == supplier_id and rule.item_category is None:
            return rule
    for rule in rules:
        if rule.supplier_id is None and rule.item_category == item_category:
            return rule
    for rule in rules:
        if rule.supplier_id is None and rule.item_category is None:
            return rule
    return None


# ── Core Matching Engine ──────────────────────────────────────────────────────

async def run_match(db: AsyncSession, invoice_id: UUID, force_rerun: bool = False) -> InvoiceMatchHeader:
    """
    Main 3-way matching engine.
    1. Load invoice + lines
    2. For each invoice line: find PO line, collect GRN lines
    3. Compute variances, apply tolerances, set statuses
    4. Detect duplicates
    5. Determine overall status + payment hold
    """
    # Lock the invoice first so repeated runs for one invoice serialize. Once its
    # PO is known, lock that PO as well so different invoices cannot concurrently
    # consume the same remaining accepted quantity.
    invoice, po = await _lock_match_source_rows(db, invoice_id)
    if po is not None and po.status == POStatus.CANCELLED:
        raise ValueError("Cannot match an invoice to a cancelled purchase order")

    # Validate supplier identity before creating or replacing a match header so
    # an invalid cross-supplier reference has no partial database side effect.
    if po is not None and po.supplier_id != invoice.supplier_id:
        raise ValueError("Invoice supplier does not match linked purchase order supplier")

    # Re-read only after acquiring the locks: another request may have created
    # the match while this request waited for the invoice row.
    existing_q = await db.execute(
        select(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.invoice_id == invoice_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    existing = existing_q.scalar_one_or_none()
    if existing and not force_rerun:
        return await get_header(db, existing.id)
    if existing and force_rerun and (existing.reviewed_at or existing.approved_at):
        raise ValueError("A reviewed or approved match cannot be rerun")

    # Duplicate detection
    dup_flag = await _detect_duplicate(db, invoice)

    # Create or reset header
    if existing:
        # Bulk deletes do not apply ORM relationship cascades. Remove the
        # concrete GRN link children first or a valid force-rerun fails its FK.
        old_line_ids = select(InvoiceMatchLine.id).where(
            InvoiceMatchLine.header_id == existing.id,
        )
        await db.execute(
            InvoiceMatchGRNLink.__table__.delete().where(
                InvoiceMatchGRNLink.match_line_id.in_(old_line_ids),
            )
        )
        await db.execute(InvoiceMatchLine.__table__.delete().where(InvoiceMatchLine.header_id == existing.id))
        hdr = existing
    else:
        match_no = await _next_match_no(db)
        hdr = InvoiceMatchHeader(
            match_no=match_no,
            invoice_id=invoice_id,
            po_id=invoice.po_id,
            supplier_id=invoice.supplier_id,
            invoice_no=invoice.invoice_no,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency,
            invoice_total=_D(invoice.total_amount),
            overall_status=MatchOverallStatus.PENDING_REVIEW,
            run_at=datetime.utcnow(),
        )
        db.add(hdr)
        await db.flush()

    hdr.duplicate_flag = dup_flag
    hdr.run_at = datetime.utcnow()

    # Load PO lines while the parent PO row remains locked for the duration of
    # this transaction.
    po_lines_map: dict[UUID, POLine] = {}
    if invoice.po_id:
        po_lines_q = await db.execute(
            select(POLine).where(POLine.po_id == invoice.po_id)
        )
        for pl in po_lines_q.scalars().all():
            po_lines_map[pl.id] = pl

    # Load previously invoiced quantities per PO line (cumulative billing guard)
    prev_invoiced = await _prev_invoiced_qtys(db, invoice.po_id, exclude_invoice_id=invoice_id)

    # Load GRN lines for this PO
    grn_line_map: dict[Optional[UUID], List[GRNLine]] = {}  # po_line_id → list of GRN lines
    if invoice.po_id:
        grn_q = await db.execute(
            select(GRNLine)
            .join(GoodsReceipt, GRNLine.grn_id == GoodsReceipt.id)
            .where(
                GoodsReceipt.po_id == invoice.po_id,
                GoodsReceipt.status == GRNStatus.POSTED,
            )
        )
        for gl in grn_q.scalars().all():
            grn_line_map.setdefault(gl.po_line_id, []).append(gl)

    # Load material names
    mat_ids = [il.material_id for il in invoice.lines if il.material_id]
    mat_names: dict[UUID, str] = {}
    if mat_ids:
        mats_q = await db.execute(select(Material).where(Material.id.in_(mat_ids)))
        for m in mats_q.scalars().all():
            mat_names[m.id] = m.name

    # Process each invoice line
    line_statuses = []
    action_required_line_policies: list[tuple[str, Optional[InvoiceMatchTolerance]]] = []
    manual_tolerance_approval_required = False
    for inv_line in invoice.lines:
        # Match only when the product identity points to one PO line. Choosing
        # the first duplicate material/product line could compare against the
        # wrong price, tax, or unit and falsely release an invoice for payment.
        candidates = [
            pl for pl in po_lines_map.values()
            if (inv_line.material_id and pl.material_id == inv_line.material_id)
            or (inv_line.product_id and pl.product_id == inv_line.product_id)
        ]
        po_line: Optional[POLine] = candidates[0] if len(candidates) == 1 else None
        block_reason: Optional[str] = None
        if len(candidates) > 1:
            block_reason = "Invoice item matches multiple PO lines; select an exact PO line before payment review."
        elif po is not None and invoice.currency.strip().upper() != str(po.currency or "").strip().upper():
            block_reason = "Invoice currency does not match the linked PO currency."
        elif po_line is not None and _uom_code(inv_line.unit) != _uom_code(po_line.unit):
            block_reason = "Invoice unit does not match the linked PO line unit; no implicit conversion is applied."

        # Collect GRN lines
        grn_lines_for_line: List[GRNLine] = []
        if po_line:
            grn_lines_for_line = grn_line_map.get(po_line.id, [])

        if po_line and any(_uom_code(gl.unit) != _uom_code(po_line.unit) for gl in grn_lines_for_line):
            block_reason = "Posted receipt unit does not match the PO line unit; no implicit conversion is applied."

        # Cumulative received/accepted
        total_received = sum(_D(gl.received_quantity) for gl in grn_lines_for_line)
        total_accepted = sum(_D(gl.accepted_quantity) for gl in grn_lines_for_line)
        prev_inv = prev_invoiced.get(po_line.id if po_line else None, Decimal("0"))
        billable = max(total_accepted - prev_inv, Decimal("0"))

        invoiced_qty = _D(inv_line.quantity)
        invoiced_price = _D(inv_line.unit_price)
        invoiced_tax = _D(inv_line.tax_rate)
        ordered_qty = _D(po_line.ordered_quantity) if po_line else None
        ordered_price = _D(po_line.unit_price) if po_line else None
        ordered_tax = _D(po_line.tax_rate) if po_line else None

        # Quantity variance is scoped to this invoice's remaining accepted amount.
        # Using cumulative accepted quantity here misclassifies subsequent invoices
        # after earlier matched invoices have already consumed part of the receipt.
        qty_var = invoiced_qty - billable if total_accepted else None
        price_var = (invoiced_price - ordered_price) if ordered_price is not None else None
        tax_var = (invoiced_tax - ordered_tax) if ordered_tax is not None else None
        qty_var_pct = _pct(_D(qty_var), billable) if qty_var is not None and billable else None
        price_var_pct = _pct(_D(price_var), ordered_price) if price_var is not None and ordered_price else None

        # Find tolerance rule
        rule = await _find_tolerance(db, invoice.supplier_id, None)

        # Determine line status
        if invoiced_qty <= 0:
            block_reason = "Invoice quantity must be greater than zero to pass three-way matching."
        status = (
            MatchLineStatus.BLOCKED
            if block_reason
            else _evaluate_line_status(
                po_line=po_line,
                grn_lines=grn_lines_for_line,
                invoiced_qty=invoiced_qty,
                billable_qty=billable,
                qty_var_pct=qty_var_pct,
                price_var_pct=price_var_pct,
                tax_var=tax_var,
                rule=rule,
                qty_var_abs=qty_var,
                price_var_abs=price_var,
            )
        )
        line_statuses.append(status)
        manual_tolerance_review = (
            status == MatchLineStatus.MATCHED_WITHIN_TOLERANCE
            and rule is not None
            and not rule.auto_approve_within_tolerance
        )
        action_required = status not in (
            MatchLineStatus.FULLY_MATCHED,
            MatchLineStatus.MATCHED_WITHIN_TOLERANCE,
        ) or manual_tolerance_review
        if action_required:
            action_required_line_policies.append((status, rule))
        manual_tolerance_approval_required = manual_tolerance_approval_required or manual_tolerance_review

        mat_name = mat_names.get(inv_line.material_id) if inv_line.material_id else None

        ml = InvoiceMatchLine(
            header_id=hdr.id,
            invoice_line_id=inv_line.id,
            po_line_id=po_line.id if po_line else None,
            material_id=inv_line.material_id,
            material_name=mat_name or inv_line.description,
            description=inv_line.description,
            ordered_qty=ordered_qty,
            ordered_unit_price=ordered_price,
            ordered_tax_rate=ordered_tax,
            total_received_qty=total_received,
            total_accepted_qty=total_accepted,
            prev_invoiced_qty=prev_inv,
            billable_qty=billable,
            invoiced_qty=invoiced_qty,
            invoiced_unit_price=invoiced_price,
            invoiced_tax_rate=invoiced_tax,
            invoiced_line_total=_D(inv_line.line_total),
            qty_variance=qty_var,
            price_variance=price_var,
            tax_variance=tax_var,
            qty_variance_pct=qty_var_pct,
            price_variance_pct=price_var_pct,
            match_status=status,
            tolerance_rule_id=rule.id if rule else None,
            action_required=action_required,
            notes=block_reason,
        )
        db.add(ml)
        await db.flush()

        # GRN links
        for gl in grn_lines_for_line:
            grn_hdr_q = await db.execute(select(GoodsReceipt).where(GoodsReceipt.id == gl.grn_id))
            grn_hdr = grn_hdr_q.scalar_one_or_none()
            db.add(InvoiceMatchGRNLink(
                match_line_id=ml.id,
                grn_id=gl.grn_id,
                grn_line_id=gl.id,
                grn_no=grn_hdr.grn_no if grn_hdr else None,
                received_qty=gl.received_quantity,
                accepted_qty=gl.accepted_quantity,
                rejected_qty=gl.rejected_quantity,
                received_date=grn_hdr.received_date if grn_hdr else None,
            ))

    # Overall status
    overall = _derive_overall_status(line_statuses, dup_flag)
    hdr.overall_status = overall
    hdr.review_required = overall not in (
        MatchOverallStatus.FULLY_MATCHED,
        MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
    ) or manual_tolerance_approval_required

    # Payment hold
    payable, hold_reason = _compute_payment_hold(overall, dup_flag)
    if manual_tolerance_approval_required:
        payable = False
        hold_reason = "Configured tolerance requires finance approval before payment"
    else:
        variance_statuses = {
            MatchLineStatus.PARTIAL_MATCH,
            MatchLineStatus.QUANTITY_MISMATCH,
            MatchLineStatus.PRICE_MISMATCH,
            MatchLineStatus.TAX_MISMATCH,
        }
        may_pay_beyond_tolerance = (
            not dup_flag
            and bool(action_required_line_policies)
            and all(
                status in variance_statuses
                and rule is not None
                and not rule.block_payment_beyond_tolerance
                for status, rule in action_required_line_policies
            )
        )
        if may_pay_beyond_tolerance:
            payable = True
            hold_reason = None
    hdr.is_payable = payable
    hdr.payment_hold_reason = hold_reason

    await db.commit()
    return await get_header(db, hdr.id)


def _evaluate_line_status(
    po_line: Optional[POLine],
    grn_lines: List[GRNLine],
    invoiced_qty: Decimal,
    billable_qty: Decimal,
    qty_var_pct: Optional[Decimal],
    price_var_pct: Optional[Decimal],
    tax_var: Optional[Decimal],
    rule: Optional[InvoiceMatchTolerance],
    qty_var_abs: Optional[Decimal] = None,
    price_var_abs: Optional[Decimal] = None,
) -> str:
    if not po_line:
        return MatchLineStatus.MISSING_PO
    if not grn_lines:
        return MatchLineStatus.MISSING_GRN

    q_tol = _D(rule.quantity_tolerance_pct) if rule else Decimal("1")
    p_tol = _D(rule.price_tolerance_pct) if rule else Decimal("2")
    t_tol = _D(rule.tax_tolerance_pct) if rule else Decimal("0")

    qty_ok = (qty_var_pct is None) or (abs(qty_var_pct) <= q_tol)
    price_ok = (price_var_pct is None) or (abs(price_var_pct) <= p_tol)
    tax_ok = (tax_var is None) or (abs(tax_var) <= t_tol / 100)
    if rule and rule.quantity_tolerance_abs is not None and qty_var_abs is not None:
        qty_ok = qty_ok and abs(qty_var_abs) <= _D(rule.quantity_tolerance_abs)
    if rule and rule.price_tolerance_abs is not None and price_var_abs is not None:
        price_ok = price_ok and abs(price_var_abs) <= _D(rule.price_tolerance_abs)

    # Overbilling check
    if invoiced_qty > billable_qty * (1 + q_tol / 100):
        return MatchLineStatus.OVERBILLED

    has_variance = not (qty_ok and price_ok and tax_ok)

    if not has_variance:
        # Check if exact or within tolerance
        exact_qty = (qty_var_pct is None) or (abs(qty_var_pct) == 0)
        exact_price = (price_var_pct is None) or (abs(price_var_pct) == 0)
        exact_tax = (tax_var is None) or (abs(tax_var) == 0)
        if exact_qty and exact_price and exact_tax:
            return MatchLineStatus.FULLY_MATCHED
        return MatchLineStatus.MATCHED_WITHIN_TOLERANCE

    if not qty_ok:
        return MatchLineStatus.QUANTITY_MISMATCH
    if not price_ok:
        return MatchLineStatus.PRICE_MISMATCH
    if not tax_ok:
        return MatchLineStatus.TAX_MISMATCH
    return MatchLineStatus.PARTIAL_MATCH


def _uom_code(value: Any) -> str:
    """Normalize a unit code without inventing a conversion factor."""
    return str(value or "").strip().upper()


def _derive_overall_status(line_statuses: List[str], dup_flag: bool) -> str:
    if dup_flag:
        return MatchOverallStatus.DUPLICATE_SUSPECTED
    if not line_statuses:
        return MatchOverallStatus.PENDING_REVIEW

    status_set = set(line_statuses)
    bad = {
        MatchLineStatus.MISSING_PO, MatchLineStatus.MISSING_GRN,
        MatchLineStatus.BLOCKED, MatchLineStatus.OVERBILLED,
    }
    if status_set & bad:
        return MatchOverallStatus.BLOCKED
    if MatchLineStatus.PRICE_MISMATCH in status_set:
        return MatchOverallStatus.PRICE_MISMATCH
    if MatchLineStatus.QUANTITY_MISMATCH in status_set:
        return MatchOverallStatus.QUANTITY_MISMATCH
    if MatchLineStatus.TAX_MISMATCH in status_set:
        return MatchOverallStatus.PRICE_MISMATCH
    if all(s == MatchLineStatus.FULLY_MATCHED for s in line_statuses):
        return MatchOverallStatus.FULLY_MATCHED
    if all(s in (MatchLineStatus.FULLY_MATCHED, MatchLineStatus.MATCHED_WITHIN_TOLERANCE) for s in line_statuses):
        return MatchOverallStatus.MATCHED_WITHIN_TOLERANCE
    if MatchLineStatus.PARTIAL_MATCH in status_set:
        return MatchOverallStatus.PARTIAL_MATCH
    return MatchOverallStatus.PENDING_REVIEW


def _compute_payment_hold(overall: str, dup_flag: bool) -> tuple[bool, Optional[str]]:
    if dup_flag:
        return False, "Duplicate invoice suspected — hold pending review"
    payable_statuses = {
        MatchOverallStatus.FULLY_MATCHED,
        MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
        MatchOverallStatus.APPROVED_EXCEPTION,
    }
    if overall in payable_statuses:
        return True, None
    reasons = {
        MatchOverallStatus.BLOCKED: "Invoice blocked due to missing PO/GRN or overbilling",
        MatchOverallStatus.PRICE_MISMATCH: "Price mismatch exceeds tolerance — review required",
        MatchOverallStatus.QUANTITY_MISMATCH: "Quantity mismatch exceeds tolerance — review required",
        MatchOverallStatus.MISSING_PO: "No matching Purchase Order found",
        MatchOverallStatus.MISSING_GRN: "No Goods Receipt recorded for this invoice",
        MatchOverallStatus.PARTIAL_MATCH: "Partial match — outstanding items unresolved",
        MatchOverallStatus.PENDING_REVIEW: "Pending review by procurement/finance",
        MatchOverallStatus.DUPLICATE_SUSPECTED: "Duplicate invoice — payment on hold",
        MatchOverallStatus.REJECTED: "Invoice rejected",
    }
    return False, reasons.get(overall, "Payment on hold")


async def _prev_invoiced_qtys(
    db: AsyncSession, po_id: Optional[UUID], exclude_invoice_id: Optional[UUID]
) -> dict[Optional[UUID], Decimal]:
    """Returns {po_line_id: total_invoiced_qty} from all OTHER posted match lines on this PO."""
    if not po_id:
        return {}
    q = (
        select(InvoiceMatchLine.po_line_id, func.sum(InvoiceMatchLine.invoiced_qty).label("total"))
        .join(InvoiceMatchHeader, InvoiceMatchLine.header_id == InvoiceMatchHeader.id)
        .where(
            and_(
                InvoiceMatchHeader.po_id == po_id,
                InvoiceMatchHeader.invoice_id != exclude_invoice_id,
                InvoiceMatchHeader.overall_status.in_([
                    MatchOverallStatus.FULLY_MATCHED,
                    MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
                    MatchOverallStatus.APPROVED_EXCEPTION,
                ]),
            )
        )
        .group_by(InvoiceMatchLine.po_line_id)
    )
    result = await db.execute(q)
    return {r[0]: _D(r[1]) for r in result.all()}


# ── Duplicate Detection ───────────────────────────────────────────────────────

async def _detect_duplicate(db: AsyncSession, invoice: PurchaseInvoice) -> bool:
    """Check for exact/near-duplicate invoices from the same supplier."""
    q = await db.execute(
        select(PurchaseInvoice).where(
            and_(
                PurchaseInvoice.supplier_id == invoice.supplier_id,
                PurchaseInvoice.id != invoice.id,
                or_(
                    PurchaseInvoice.invoice_no == invoice.invoice_no,
                    and_(
                        PurchaseInvoice.invoice_date == invoice.invoice_date,
                        PurchaseInvoice.total_amount == invoice.total_amount,
                    ),
                ),
            )
        )
    )
    matches = q.scalars().all()
    if not matches:
        return False

    for match in matches:
        risk = DuplicateRisk.EXACT if match.invoice_no == invoice.invoice_no else DuplicateRisk.SUSPECTED
        reasons = []
        if match.invoice_no == invoice.invoice_no:
            reasons.append("same_invoice_no")
        if match.invoice_date == invoice.invoice_date:
            reasons.append("same_invoice_date")
        if _D(match.total_amount) == _D(invoice.total_amount):
            reasons.append("same_total_amount")

        # Avoid duplicate log entries
        existing_dup_q = await db.execute(
            select(DuplicateInvoiceLog).where(
                and_(
                    DuplicateInvoiceLog.invoice_id == invoice.id,
                    DuplicateInvoiceLog.matched_invoice_id == match.id,
                )
            )
        )
        if not existing_dup_q.scalar_one_or_none():
            db.add(DuplicateInvoiceLog(
                invoice_id=invoice.id,
                matched_invoice_id=match.id,
                supplier_id=invoice.supplier_id,
                invoice_no=invoice.invoice_no,
                matched_invoice_no=match.invoice_no,
                duplicate_risk=risk,
                match_reasons=reasons,
                similarity_score=Decimal("1.00") if risk == DuplicateRisk.EXACT else Decimal("0.75"),
            ))
    return True


# ── Review / Approval Workflow ────────────────────────────────────────────────

class InvoiceMatchApprovalRoleError(ValueError):
    """Raised when an exception approver lacks a tolerance rule's required role."""


def _validate_exception_approval(
    *,
    duplicate_flag: bool,
    review_required: bool,
    line_statuses: list[str],
    required_roles: set[str],
    actor_role_names: set[str],
    justification: Optional[str],
) -> None:
    if duplicate_flag:
        raise ValueError("Duplicate-suspected invoices must be resolved before exception approval")
    if not review_required:
        raise ValueError("Only matches requiring review can be approved as exceptions")
    if not justification or not justification.strip():
        raise ValueError("A justification is required to approve a match exception")

    statuses = {getattr(status, "value", status) for status in line_statuses}
    non_overridable = {
        MatchLineStatus.MISSING_PO,
        MatchLineStatus.MISSING_GRN,
        MatchLineStatus.BLOCKED,
        MatchLineStatus.OVERBILLED,
    }
    if statuses & non_overridable:
        raise ValueError("Missing-source, blocked, and overbilled lines cannot be exception-approved")

    exception_statuses = {
        MatchLineStatus.MATCHED_WITHIN_TOLERANCE,
        MatchLineStatus.PARTIAL_MATCH,
        MatchLineStatus.QUANTITY_MISMATCH,
        MatchLineStatus.PRICE_MISMATCH,
        MatchLineStatus.TAX_MISMATCH,
    }
    if not statuses & exception_statuses:
        raise ValueError("The match has no tolerance exception eligible for approval")

    normalized_actor_roles = {role.casefold() for role in actor_role_names}
    if "*" in normalized_actor_roles:
        return
    missing_roles = sorted(
        role for role in {role.strip() for role in required_roles if role.strip()}
        if role.casefold() not in normalized_actor_roles
    )
    if missing_roles:
        raise InvoiceMatchApprovalRoleError(
            f"Tolerance rule requires approver role: {', '.join(missing_roles)}"
        )


async def submit_review(
    db: AsyncSession,
    header_id: UUID,
    payload: ReviewCreate,
    *,
    actor_role_names: Optional[set[str]] = None,
) -> InvoiceMatchHeader:
    snapshot_q = await db.execute(
        select(InvoiceMatchHeader.invoice_id, InvoiceMatchHeader.run_at)
        .where(InvoiceMatchHeader.id == header_id)
    )
    snapshot = snapshot_q.one_or_none()
    if not snapshot:
        raise ValueError("Match record not found")

    # Match runs and approvals take source-row locks in the same order. If a
    # rerun won the race, reject this approval against the stale result the
    # reviewer originally loaded and require a refreshed decision.
    await _lock_match_source_rows(db, snapshot.invoice_id)
    hdr_q = await db.execute(
        select(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.id == header_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    hdr = hdr_q.scalar_one_or_none()
    if not hdr:
        raise ValueError("Match record not found")
    if hdr.run_at != snapshot.run_at:
        raise ValueError("Match was rerun during review; refresh the current result before reviewing")
    if hdr.run_at != payload.expected_run_at:
        raise ValueError("Match result changed; refresh the current result before reviewing")

    if payload.action == "APPROVED_EXCEPTION":
        lines_q = await db.execute(
            select(InvoiceMatchLine.id, InvoiceMatchLine.match_status, InvoiceMatchLine.tolerance_rule_id)
            .where(
                InvoiceMatchLine.header_id == header_id,
                InvoiceMatchLine.action_required.is_(True),
            )
            .order_by(InvoiceMatchLine.id)
            .with_for_update()
        )
        action_lines = lines_q.all()
        tolerance_ids = {row.tolerance_rule_id for row in action_lines if row.tolerance_rule_id}
        required_roles: set[str] = set()
        if tolerance_ids:
            rules_q = await db.execute(
                select(InvoiceMatchTolerance)
                .where(InvoiceMatchTolerance.id.in_(tolerance_ids))
                .order_by(InvoiceMatchTolerance.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            required_roles = {
                rule.approval_role_required
                for rule in rules_q.scalars().all()
                if rule.approval_role_required
            }
        _validate_exception_approval(
            duplicate_flag=hdr.duplicate_flag,
            review_required=hdr.review_required,
            line_statuses=[row.match_status for row in action_lines],
            required_roles=required_roles,
            actor_role_names=actor_role_names or set(),
            justification=payload.justification,
        )

    prev_status = hdr.overall_status

    review = InvoiceMatchReview(
        header_id=header_id,
        action=payload.action,
        reviewer_name=payload.reviewer_name,
        reviewer_role=payload.reviewer_role,
        previous_status=prev_status,
        justification=payload.justification,
        line_ids=payload.line_ids,
    )

    if payload.action == "APPROVED_EXCEPTION":
        hdr.overall_status = MatchOverallStatus.APPROVED_EXCEPTION
        hdr.is_payable = True
        hdr.payment_hold_reason = None
        hdr.approved_by = payload.reviewer_name
        hdr.approved_at = datetime.utcnow()
        # Update affected lines
        lines_q = await db.execute(
            select(InvoiceMatchLine).where(InvoiceMatchLine.header_id == header_id)
        )
        for ml in lines_q.scalars().all():
            if ml.action_required:
                ml.match_status = MatchLineStatus.APPROVED_EXCEPTION
                ml.action_required = False

    elif payload.action == "REJECTED":
        hdr.overall_status = MatchOverallStatus.REJECTED
        hdr.is_payable = False
        hdr.payment_hold_reason = f"Rejected by {payload.reviewer_name}: {payload.justification or 'No reason given'}"

    elif payload.action == "ESCALATED":
        hdr.review_required = True

    review.new_status = hdr.overall_status
    hdr.reviewed_by = payload.reviewer_name
    hdr.reviewed_at = datetime.utcnow()

    db.add(review)
    await db.commit()
    return await get_header(db, header_id)


# ── Getters ───────────────────────────────────────────────────────────────────

async def get_header(db: AsyncSession, header_id: UUID) -> Optional[InvoiceMatchHeader]:
    result = await db.execute(
        select(InvoiceMatchHeader)
        .options(
            selectinload(InvoiceMatchHeader.match_lines).selectinload(InvoiceMatchLine.grn_links),
            selectinload(InvoiceMatchHeader.match_lines).selectinload(InvoiceMatchLine.tolerance_rule),
            selectinload(InvoiceMatchHeader.reviews),
            selectinload(InvoiceMatchHeader.ai_recs),
        )
        .where(InvoiceMatchHeader.id == header_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def list_headers(
    db: AsyncSession,
    status: Optional[str] = None,
    review_required: Optional[bool] = None,
    duplicate_flag: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[InvoiceMatchHeader]:
    q = select(InvoiceMatchHeader).order_by(InvoiceMatchHeader.created_at.desc())
    if status:
        q = q.where(InvoiceMatchHeader.overall_status == status)
    if review_required is not None:
        q = q.where(InvoiceMatchHeader.review_required == review_required)
    if duplicate_flag is not None:
        q = q.where(InvoiceMatchHeader.duplicate_flag == duplicate_flag)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_blocked_invoices(db: AsyncSession) -> List[InvoiceMatchHeader]:
    result = await db.execute(
        select(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.is_payable == False)
        .order_by(InvoiceMatchHeader.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


async def get_duplicate_suspicions(db: AsyncSession) -> List[DuplicateInvoiceLog]:
    result = await db.execute(
        select(DuplicateInvoiceLog)
        .where(DuplicateInvoiceLog.is_resolved == False)
        .order_by(DuplicateInvoiceLog.created_at.desc())
    )
    return list(result.scalars().all())


async def resolve_duplicate(
    db: AsyncSession, dup_id: UUID, resolved_by: str, resolution_notes: str
) -> Optional[DuplicateInvoiceLog]:
    q = await db.execute(select(DuplicateInvoiceLog).where(DuplicateInvoiceLog.id == dup_id))
    dup = q.scalar_one_or_none()
    if not dup:
        return None
    dup.is_resolved = True
    dup.resolved_by = resolved_by
    dup.resolved_at = datetime.utcnow()
    dup.resolution_notes = resolution_notes
    await db.commit()
    await db.refresh(dup)
    return dup


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    total_q = await db.execute(select(func.count()).select_from(InvoiceMatchHeader))
    total = total_q.scalar() or 0

    by_status_q = await db.execute(
        select(InvoiceMatchHeader.overall_status, func.count())
        .group_by(InvoiceMatchHeader.overall_status)
    )
    by_status = {r[0]: r[1] for r in by_status_q.all()}

    payable_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.is_payable == True)
    )
    on_hold_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.is_payable == False)
    )
    dup_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.duplicate_flag == True)
    )
    pending_review_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.review_required == True)
    )
    ai_q = await db.execute(
        select(func.count()).select_from(IMAIRecommendation)
        .where(IMAIRecommendation.status == "PENDING")
    )

    recent_q = await db.execute(
        select(InvoiceMatchHeader)
        .order_by(InvoiceMatchHeader.created_at.desc())
        .limit(10)
    )
    recent = list(recent_q.scalars().all())

    mismatch_types = [
        {"type": k, "count": v}
        for k, v in by_status.items()
        if k not in (MatchOverallStatus.FULLY_MATCHED, MatchOverallStatus.MATCHED_WITHIN_TOLERANCE)
    ]

    return {
        "total_matches": total,
        "fully_matched": by_status.get(MatchOverallStatus.FULLY_MATCHED, 0),
        "within_tolerance": by_status.get(MatchOverallStatus.MATCHED_WITHIN_TOLERANCE, 0),
        "mismatched": sum(v for k, v in by_status.items()
                         if k not in (MatchOverallStatus.FULLY_MATCHED, MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
                                      MatchOverallStatus.APPROVED_EXCEPTION)),
        "blocked": by_status.get(MatchOverallStatus.BLOCKED, 0),
        "pending_review": pending_review_q.scalar() or 0,
        "duplicate_suspected": dup_q.scalar() or 0,
        "payable_count": payable_q.scalar() or 0,
        "on_hold_count": on_hold_q.scalar() or 0,
        "pending_ai_recs": ai_q.scalar() or 0,
        "mismatch_by_type": mismatch_types,
        "recent_matches": recent,
    }


# ── Reports ────────────────────────────────────────────────────────────────────

async def report_mismatch_summary(db: AsyncSession) -> list:
    q = await db.execute(
        select(InvoiceMatchLine.match_status, func.count().label("count"))
        .group_by(InvoiceMatchLine.match_status)
        .order_by(func.count().desc())
    )
    return [{"match_status": r[0], "count": r[1]} for r in q.all()]


async def report_supplier_accuracy(db: AsyncSession) -> list:
    q = await db.execute(
        select(
            InvoiceMatchHeader.supplier_id,
            func.count().label("total"),
            func.sum(
                func.cast(InvoiceMatchHeader.overall_status.in_([
                    MatchOverallStatus.FULLY_MATCHED,
                    MatchOverallStatus.MATCHED_WITHIN_TOLERANCE,
                ]), Integer if False else func.cast(1, type_=func.count().type))
            ),
        )
        .group_by(InvoiceMatchHeader.supplier_id)
    )
    # Simple approach
    all_q = await db.execute(
        select(
            InvoiceMatchHeader.supplier_id,
            InvoiceMatchHeader.overall_status,
            func.count().label("cnt"),
        )
        .group_by(InvoiceMatchHeader.supplier_id, InvoiceMatchHeader.overall_status)
    )
    rows = all_q.all()
    supplier_data: dict = {}
    for r in rows:
        sid = str(r[0]) if r[0] else "unknown"
        if sid not in supplier_data:
            supplier_data[sid] = {"supplier_id": r[0], "total": 0, "matched": 0, "mismatched": 0}
        supplier_data[sid]["total"] += r[2]
        if r[1] in (MatchOverallStatus.FULLY_MATCHED, MatchOverallStatus.MATCHED_WITHIN_TOLERANCE, MatchOverallStatus.APPROVED_EXCEPTION):
            supplier_data[sid]["matched"] += r[2]
        else:
            supplier_data[sid]["mismatched"] += r[2]
    result = []
    for d in supplier_data.values():
        acc = _R(Decimal(d["matched"]) / Decimal(max(d["total"], 1)) * 100, 1)
        result.append({**d, "accuracy_pct": acc})
    return sorted(result, key=lambda x: x["accuracy_pct"])


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession, header_id: Optional[UUID] = None) -> int:
    created = 0
    if header_id:
        hdr = await get_header(db, header_id)
        headers = [hdr] if hdr else []
    else:
        q = await db.execute(
            select(InvoiceMatchHeader)
            .options(selectinload(InvoiceMatchHeader.match_lines))
            .where(InvoiceMatchHeader.review_required == True)
            .order_by(InvoiceMatchHeader.created_at.desc())
            .limit(30)
        )
        headers = list(q.scalars().all())

    for hdr in headers:
        created += await _agent_anomaly_detector(db, hdr)
        created += await _agent_exception_prioritizer(db, hdr)

    created += await _agent_tolerance_tuner(db)

    await db.commit()
    return created


async def _agent_anomaly_detector(db: AsyncSession, hdr: InvoiceMatchHeader) -> int:
    if not hdr.match_lines:
        return 0
    # Flag price variances > 10%
    severe_lines = [
        ml for ml in hdr.match_lines
        if ml.price_variance_pct and abs(_D(ml.price_variance_pct)) > 10
    ]
    if not severe_lines:
        return 0
    items = ", ".join(ml.material_name or str(ml.id)[:8] for ml in severe_lines[:3])
    rec = IMAIRecommendation(
        header_id=hdr.id,
        agent_type="ANOMALY_DETECTOR",
        status="PENDING",
        priority="HIGH",
        title=f"Severe price deviation detected on {hdr.match_no}",
        explanation=(
            f"Invoice {hdr.invoice_no} has {len(severe_lines)} line(s) with price deviations >10% "
            f"vs PO agreed prices. Items: {items}."
        ),
        impact_summary=f"{len(severe_lines)} line(s) affected. Review before payment release.",
        suggested_action="Contact supplier to clarify pricing. Compare against current market rates. Reject if not justified.",
        confidence_score=Decimal("0.90"),
    )
    db.add(rec)
    return 1


async def _agent_exception_prioritizer(db: AsyncSession, hdr: InvoiceMatchHeader) -> int:
    if hdr.overall_status not in (
        MatchOverallStatus.BLOCKED, MatchOverallStatus.PRICE_MISMATCH,
        MatchOverallStatus.QUANTITY_MISMATCH, MatchOverallStatus.MISSING_PO,
        MatchOverallStatus.MISSING_GRN,
    ):
        return 0
    # Check if this supplier has had repeated mismatches
    count_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(
            and_(
                InvoiceMatchHeader.supplier_id == hdr.supplier_id,
                InvoiceMatchHeader.overall_status.in_([
                    MatchOverallStatus.PRICE_MISMATCH,
                    MatchOverallStatus.QUANTITY_MISMATCH,
                    MatchOverallStatus.BLOCKED,
                ]),
                InvoiceMatchHeader.id != hdr.id,
            )
        )
    )
    repeat_count = count_q.scalar() or 0
    if repeat_count < 2:
        return 0
    rec = IMAIRecommendation(
        header_id=hdr.id,
        agent_type="EXCEPTION_PRIORITIZER",
        status="PENDING",
        priority="CRITICAL" if repeat_count >= 5 else "HIGH",
        title=f"Repeated mismatch pattern — supplier has {repeat_count} prior mismatch(es)",
        explanation=(
            f"This supplier has had {repeat_count} previous invoice mismatch(es). "
            f"Current invoice {hdr.invoice_no} shows {hdr.overall_status}. "
            f"Escalate to procurement head for supplier review."
        ),
        impact_summary=f"Pattern of {repeat_count} mismatches suggests systemic billing issue.",
        suggested_action="Escalate to procurement head. Consider formal supplier corrective action request.",
        confidence_score=Decimal("0.82"),
    )
    db.add(rec)
    return 1


async def _agent_tolerance_tuner(db: AsyncSession) -> int:
    """Suggest tolerance adjustments based on mismatch frequency."""
    # Find rules that generate excessive manual work (many MATCHED_WITHIN_TOLERANCE still requiring review)
    count_q = await db.execute(
        select(func.count()).select_from(InvoiceMatchHeader)
        .where(InvoiceMatchHeader.review_required == True)
    )
    review_count = count_q.scalar() or 0
    if review_count < 5:
        return 0
    # Check if a recommendation already exists (don't spam)
    existing_q = await db.execute(
        select(func.count()).select_from(IMAIRecommendation)
        .where(
            and_(
                IMAIRecommendation.agent_type == "TOLERANCE_TUNER",
                IMAIRecommendation.status == "PENDING",
            )
        )
    )
    if (existing_q.scalar() or 0) > 0:
        return 0
    rec = IMAIRecommendation(
        header_id=None,
        agent_type="TOLERANCE_TUNER",
        status="PENDING",
        priority="MEDIUM",
        title=f"High manual review volume: {review_count} invoices pending review",
        explanation=(
            f"There are {review_count} invoices requiring manual review. "
            f"Consider widening quantity or price tolerance thresholds for trusted suppliers "
            f"to reduce review burden without increasing financial risk."
        ),
        impact_summary=f"{review_count} invoices in review queue.",
        suggested_action=(
            "Review tolerance rules. For suppliers with >95% historical accuracy, "
            "consider increasing price tolerance from 2% to 3% and quantity tolerance to 1.5%."
        ),
        confidence_score=Decimal("0.72"),
    )
    db.add(rec)
    return 1


async def list_ai_recs(
    db: AsyncSession,
    header_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> List[IMAIRecommendation]:
    q = select(IMAIRecommendation).order_by(IMAIRecommendation.created_at.desc())
    if header_id:
        q = q.where(IMAIRecommendation.header_id == header_id)
    if status:
        q = q.where(IMAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def action_ai_rec(db: AsyncSession, rec_id: UUID, status: str, actioned_by: str = "user") -> Optional[IMAIRecommendation]:
    q = await db.execute(select(IMAIRecommendation).where(IMAIRecommendation.id == rec_id))
    rec = q.scalar_one_or_none()
    if not rec:
        return None
    rec.status = status
    rec.actioned_at = datetime.utcnow()
    rec.actioned_by = actioned_by
    await db.commit()
    await db.refresh(rec)
    return rec
