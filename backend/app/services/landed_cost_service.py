"""
Landed Cost Allocation Service
Handles: document creation, GRN linking, allocation engine,
         inventory valuation update, posting, 3 AI agents.
"""
from __future__ import annotations

import re
from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, func, and_, extract, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.finance import (
    AccountType,
    AccountingPeriod,
    ChartOfAccount,
    ExchangeRate,
    JournalEntry,
    JournalLine,
    JournalStatus,
    OperationalPostingStatus,
)
from app.models.inventory import CostLayer
from app.models.landed_cost import (
    LandedCostHeader, LandedCostLine, LandedCostGRNLink,
    LandedCostLineActual, LandedCostAllocationLine, LCInventoryAdjustment, LCAIRecommendation,
    LCAllocationMethod,
)
from app.models.procurement import GoodsReceipt, GRNLine, GRNStatus, POLine
from app.models.master import Material
from app.schemas.landed_cost import (
    LandedCostHeaderCreate, LandedCostHeaderUpdate,
    LandedCostLineCreate, LandedCostLineActualCreate, LandedCostGRNLinkCreate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Any, dp: int = 4) -> Decimal:
    return _D(v).quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


async def _next_lc_no(db: AsyncSession) -> str:
    result = await db.execute(
        select(func.count()).select_from(LandedCostHeader)
    )
    n = (result.scalar() or 0) + 1
    return f"LC-{n:06d}"


async def _resolve_rate_snapshot(
    db: AsyncSession,
    currency: str,
    as_of_date: Optional[date],
) -> tuple[Decimal, Optional[UUID], Optional[date], str]:
    """Resolve a dated Finance rate and return its immutable document snapshot."""
    code = currency.strip().upper()
    effective_date = as_of_date or date.today()
    if code == "KES":
        return Decimal("1"), None, effective_date, "BASE_CURRENCY"
    query = select(ExchangeRate).where(
        ExchangeRate.currency == code,
        ExchangeRate.rate_date <= effective_date,
    )
    rate_row = (await db.execute(query.order_by(ExchangeRate.rate_date.desc()).limit(1))).scalar_one_or_none()
    if rate_row is None:
        raise ValueError(f"No Finance exchange rate exists for {code} on or before {effective_date}")
    rate = _D(rate_row.rate_to_kes)
    if not rate.is_finite() or rate <= 0:
        raise ValueError(f"Finance exchange rate for {code} on {rate_row.rate_date} must be positive")
    source = rate_row.source.value if hasattr(rate_row.source, "value") else str(rate_row.source)
    return rate, rate_row.id, rate_row.rate_date, source


def _header_totals(lines: list[LandedCostLine], header_rate: Decimal) -> tuple[Decimal, Decimal]:
    if not header_rate.is_finite() or header_rate <= 0:
        raise ValueError("Document currency exchange rate must be positive")
    total_base = sum((_D(line.amount_base) for line in lines), Decimal("0"))
    total_fc = total_base / header_rate
    return _R(total_fc), _R(total_base)


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_header(db: AsyncSession, payload: LandedCostHeaderCreate) -> LandedCostHeader:
    lc_no = await _next_lc_no(db)
    header_rate, header_rate_id, header_rate_date, header_rate_source = await _resolve_rate_snapshot(
        db, payload.currency_code, payload.bill_date,
    )

    hdr = LandedCostHeader(
        lc_no=lc_no,
        reference_type=payload.reference_type,
        shipment_id=payload.shipment_id,
        po_id=payload.po_id,
        vendor_name=payload.vendor_name,
        bill_no=payload.bill_no,
        bill_date=payload.bill_date,
        currency_code=payload.currency_code,
        exchange_rate=header_rate,
        exchange_rate_id=header_rate_id,
        exchange_rate_date=header_rate_date,
        exchange_rate_source=header_rate_source,
        total_lc_amount_fc=Decimal("0"),
        total_lc_amount_base=Decimal("0"),
        allocation_method=payload.allocation_method,
        notes=payload.notes,
        status="DRAFT",
    )
    db.add(hdr)
    await db.flush()

    created_lines = []
    for cl in payload.cost_lines:
        estimate = cl.estimated_amount_fc if cl.estimated_amount_fc is not None else cl.amount_fc
        line_rate, line_rate_id, line_rate_date, line_rate_source = await _resolve_rate_snapshot(
            db, cl.currency_code, payload.bill_date,
        )
        line = LandedCostLine(
            header_id=hdr.id,
            cost_type=cl.cost_type,
            description=cl.description,
            vendor_name=cl.vendor_name,
            amount_fc=_R(estimate),
            estimated_amount_fc=_R(estimate),
            currency_code=cl.currency_code,
            exchange_rate=line_rate,
            exchange_rate_id=line_rate_id,
            exchange_rate_date=line_rate_date,
            exchange_rate_source=line_rate_source,
            amount_base=_R(_D(estimate) * line_rate),
            allocation_method=cl.allocation_method,
            is_included_in_valuation=cl.is_included_in_valuation,
            account_code=cl.account_code,
            remarks=cl.remarks,
        )
        db.add(line)
        created_lines.append(line)

    total_fc, total_base = _header_totals(created_lines, header_rate)
    hdr.total_lc_amount_fc = total_fc
    hdr.total_lc_amount_base = total_base

    for gl in payload.grn_links:
        link = LandedCostGRNLink(
            header_id=hdr.id,
            grn_id=gl.grn_id,
            grn_no=gl.grn_no,
            po_no=gl.po_no,
        )
        db.add(link)

    await db.commit()
    return await get_header(db, hdr.id)


async def get_header(db: AsyncSession, header_id: UUID) -> Optional[LandedCostHeader]:
    result = await db.execute(
        select(LandedCostHeader)
        .options(
            selectinload(LandedCostHeader.cost_lines).selectinload(LandedCostLine.actual_record),
            selectinload(LandedCostHeader.grn_links),
            selectinload(LandedCostHeader.allocation_lines),
            selectinload(LandedCostHeader.ai_recs),
        )
        .execution_options(populate_existing=True)
        .where(LandedCostHeader.id == header_id)
    )
    return result.scalar_one_or_none()


async def list_headers(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[LandedCostHeader]:
    q = select(LandedCostHeader).order_by(LandedCostHeader.created_at.desc())
    if status:
        q = q.where(LandedCostHeader.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return list(result.scalars().all())


async def update_header(db: AsyncSession, header_id: UUID, payload: LandedCostHeaderUpdate) -> Optional[LandedCostHeader]:
    hdr_q = await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )
    hdr = hdr_q.scalar_one_or_none()
    if not hdr:
        return None
    if hdr.status != "DRAFT":
        raise ValueError(f"Cannot update a landed cost document in status {hdr.status}")
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(hdr, k, v)
    rate_context_changed = "currency_code" in data or "bill_date" in data
    lines = (await db.execute(
        select(LandedCostLine).where(LandedCostLine.header_id == header_id).with_for_update()
    )).scalars().all()
    if rate_context_changed:
        header_rate, header_rate_id, header_rate_date, header_rate_source = await _resolve_rate_snapshot(
            db, hdr.currency_code, hdr.bill_date,
        )
        hdr.exchange_rate = header_rate
        hdr.exchange_rate_id = header_rate_id
        hdr.exchange_rate_date = header_rate_date
        hdr.exchange_rate_source = header_rate_source
        for line in lines:
            line_rate, line_rate_id, line_rate_date, line_rate_source = await _resolve_rate_snapshot(
                db, line.currency_code, hdr.bill_date,
            )
            line.exchange_rate = line_rate
            line.exchange_rate_id = line_rate_id
            line.exchange_rate_date = line_rate_date
            line.exchange_rate_source = line_rate_source
            line.amount_base = _R(_D(line.amount_fc) * line_rate)
        hdr.total_lc_amount_fc, hdr.total_lc_amount_base = _header_totals(lines, header_rate)
    await db.commit()
    return await get_header(db, header_id)


async def add_cost_line(db: AsyncSession, header_id: UUID, payload: LandedCostLineCreate) -> LandedCostHeader:
    hdr_q = await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )
    hdr = hdr_q.scalar_one_or_none()
    if not hdr:
        raise ValueError("Landed cost document not found")
    if hdr.status != "DRAFT":
        raise ValueError(f"Cannot add a cost line in status {hdr.status}")

    estimate = payload.estimated_amount_fc if payload.estimated_amount_fc is not None else payload.amount_fc
    line_rate, line_rate_id, line_rate_date, line_rate_source = await _resolve_rate_snapshot(
        db, payload.currency_code, hdr.bill_date,
    )
    line = LandedCostLine(
        header_id=header_id,
        cost_type=payload.cost_type.value,
        description=payload.description,
        vendor_name=payload.vendor_name,
        amount_fc=_R(estimate),
        estimated_amount_fc=_R(estimate),
        currency_code=payload.currency_code,
        exchange_rate=line_rate,
        exchange_rate_id=line_rate_id,
        exchange_rate_date=line_rate_date,
        exchange_rate_source=line_rate_source,
        amount_base=_R(_D(estimate) * line_rate),
        allocation_method=payload.allocation_method,
        is_included_in_valuation=payload.is_included_in_valuation,
        account_code=payload.account_code,
        remarks=payload.remarks,
    )
    db.add(line)
    await db.flush()
    lines = (await db.execute(select(LandedCostLine).where(LandedCostLine.header_id == header_id))).scalars().all()
    hdr.total_lc_amount_fc, hdr.total_lc_amount_base = _header_totals(lines, _D(hdr.exchange_rate))
    await db.commit()
    return await get_header(db, header_id)


async def record_actual_cost(
    db: AsyncSession,
    header_id: UUID,
    line_id: UUID,
    payload: LandedCostLineActualCreate,
    recorded_by_id: UUID,
) -> LandedCostHeader:
    """Append an actual source amount; preserve any already-posted estimate."""
    header = (await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )).scalar_one_or_none()
    if not header:
        raise ValueError("Landed cost document not found")
    if header.status not in {"DRAFT", "VALIDATED", "POSTED"}:
        raise ValueError(f"Cannot record actual cost in status {header.status}")

    line = (await db.execute(
        select(LandedCostLine)
        .where(LandedCostLine.id == line_id, LandedCostLine.header_id == header_id)
        .with_for_update()
    )).scalar_one_or_none()
    if not line:
        raise ValueError("Landed cost line not found")

    existing = (await db.execute(
        select(LandedCostLineActual.id).where(LandedCostLineActual.lc_line_id == line_id)
    )).scalar_one_or_none()
    if existing:
        raise ValueError("An actual cost is already recorded for this line; corrections require a separate adjustment")

    if header.status != "POSTED":
        posted_allocation = (await db.execute(
            select(LandedCostAllocationLine.id).where(
                LandedCostAllocationLine.header_id == header_id,
                LandedCostAllocationLine.is_posted.is_(True),
            ).limit(1)
        )).scalar_one_or_none()
        if posted_allocation:
            raise ValueError("Posted allocations are immutable; reconcile actual cost through a separate adjustment")

    db.add(LandedCostLineActual(
        lc_line_id=line_id,
        amount_fc=_R(payload.amount_fc),
        source_reference=payload.source_reference,
        recorded_by_id=recorded_by_id,
    ))

    if header.status != "POSTED":
        line.amount_fc = _R(payload.amount_fc)
        line.amount_base = _R(_D(payload.amount_fc) * _D(line.exchange_rate))
        await db.execute(delete(LandedCostAllocationLine).where(
            LandedCostAllocationLine.header_id == header_id,
            LandedCostAllocationLine.is_posted.is_(False),
        ))
        if header.status == "VALIDATED":
            header.status = "DRAFT"

        await db.flush()
        lines = (await db.execute(
            select(LandedCostLine).where(LandedCostLine.header_id == header_id)
        )).scalars().all()
        header.total_lc_amount_fc, header.total_lc_amount_base = _header_totals(
            lines, _D(header.exchange_rate),
        )

    await db.commit()
    return await get_header(db, header_id)


async def add_grn_link(db: AsyncSession, header_id: UUID, payload: LandedCostGRNLinkCreate) -> LandedCostHeader:
    hdr_q = await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )
    hdr = hdr_q.scalar_one_or_none()
    if not hdr:
        raise ValueError("Landed cost document not found")
    if hdr.status != "DRAFT":
        raise ValueError(f"Cannot add a GRN link in status {hdr.status}")
    link = LandedCostGRNLink(
        header_id=header_id,
        grn_id=payload.grn_id,
        grn_no=payload.grn_no,
        po_no=payload.po_no,
    )
    db.add(link)
    await db.commit()
    return await get_header(db, header_id)


# ── Allocation Engine ──────────────────────────────────────────────────────────

async def run_allocation(db: AsyncSession, header_id: UUID) -> LandedCostHeader:
    """
    Allocate each cost line across GRN lines using the configured method.
    Clears previous allocation lines before re-running.
    """
    hdr_q = await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )
    locked_hdr = hdr_q.scalar_one_or_none()
    if not locked_hdr:
        raise ValueError("Landed cost document not found")
    if locked_hdr.status not in ("DRAFT", "VALIDATED"):
        raise ValueError(f"Cannot allocate in status {locked_hdr.status}")
    hdr = await get_header(db, header_id)
    if not hdr.cost_lines:
        raise ValueError("Landed cost must contain at least one cost line before allocation")
    if any(_D(line.amount_fc) < 0 or _D(line.amount_base) < 0 for line in hdr.cost_lines):
        raise ValueError(
            "Negative landed-cost lines require a separately configured credit or reversal flow and cannot be allocated"
        )

    # Clear existing allocation lines
    await db.execute(
        LandedCostAllocationLine.__table__.delete().where(
            LandedCostAllocationLine.header_id == header_id
        )
    )

    # Allocation is based only on posted receipts and quantities accepted into stock.
    grn_ids = [gl.grn_id for gl in hdr.grn_links]
    if not grn_ids:
        raise ValueError("Landed cost must be linked to at least one goods receipt before allocation")

    grn_lines_q = await db.execute(
        select(GRNLine)
        .join(GoodsReceipt, GoodsReceipt.id == GRNLine.grn_id)
        .options(
            selectinload(GRNLine.material),
            selectinload(GRNLine.product),
            selectinload(GRNLine.po_line).selectinload(POLine.po),
        )
        .where(
            GRNLine.grn_id.in_(grn_ids),
            GoodsReceipt.status == GRNStatus.POSTED,
            GRNLine.accepted_quantity > 0,
        )
        .order_by(GRNLine.id)
    )
    grn_lines: List[GRNLine] = list(grn_lines_q.scalars().all())
    if not grn_lines:
        raise ValueError("Linked goods receipts must be posted and contain accepted quantities")

    # Build allocation basis per GRN line for each cost line
    cost_lines = list(hdr.cost_lines)

    for cl in cost_lines:
        method = cl.allocation_method or hdr.allocation_method
        basis_map = _compute_basis(method, grn_lines)
        allocation_amounts = _allocate_amounts(_D(cl.amount_base), basis_map, method)
        alloc_rows = []
        for gl in grn_lines:
            basis = basis_map.get(gl.id, Decimal("0"))
            allocated = allocation_amounts.get(gl.id, Decimal("0"))
            if allocated <= 0:
                continue
            share = allocated / _D(cl.amount_base) if _D(cl.amount_base) > 0 else Decimal("0")
            accepted_qty = _D(gl.accepted_quantity)
            per_unit = _R(allocated / accepted_qty, 6) if accepted_qty > 0 else None
            alloc_rows.append(LandedCostAllocationLine(
                header_id=header_id,
                lc_line_id=cl.id,
                grn_id=gl.grn_id,
                grn_line_id=gl.id,
                material_id=gl.material_id,
                material_name=(gl.material.name if gl.material else gl.product.name if gl.product else None),
                lot_no=gl.lot_number,
                received_qty=accepted_qty,
                received_weight=(basis if method == LCAllocationMethod.BY_WEIGHT else None),
                received_volume=(basis if method == LCAllocationMethod.BY_VOLUME else None),
                purchase_value=_base_unit_cost(gl) * accepted_qty,
                allocation_basis=basis,
                allocation_share=_R(share * 100, 4),
                allocated_amount=allocated,
                per_unit_lc_cost=per_unit,
                is_posted=False,
            ))

        for row in alloc_rows:
            db.add(row)

    # Mark as VALIDATED
    hdr_row_q = await db.execute(select(LandedCostHeader).where(LandedCostHeader.id == header_id))
    hdr_row = hdr_row_q.scalar_one()
    hdr_row.status = "VALIDATED"
    await db.commit()
    return await get_header(db, header_id)


def _compute_basis(method: str, grn_lines: List[GRNLine]) -> dict:
    basis = {}
    for gl in grn_lines:
        if method == LCAllocationMethod.BY_QUANTITY:
            value = _D(gl.accepted_quantity)
        elif method == LCAllocationMethod.BY_WEIGHT:
            item = gl.material or gl.product
            weight = _D(item.weight_kg) if item and item.weight_kg is not None else Decimal("0")
            if weight <= 0:
                raise ValueError(f"GRN line {gl.id} has no positive item weight in kg for BY_WEIGHT allocation")
            value = _D(gl.accepted_quantity) * weight
        elif method == LCAllocationMethod.BY_VOLUME:
            volume = _D(gl.accepted_volume_m3)
            if volume <= 0:
                raise ValueError(
                    f"GRN line {gl.id} has no accepted volume in m³ for BY_VOLUME allocation"
                )
            value = volume
        elif method == LCAllocationMethod.BY_VALUE:
            value = _base_unit_cost(gl) * _D(gl.accepted_quantity)
            if value <= 0:
                raise ValueError(
                    f"GRN line {gl.id} has no positive PO-backed base purchase value for BY_VALUE allocation"
                )
        elif method == LCAllocationMethod.EQUAL_SPLIT:
            value = Decimal("1")
        else:
            raise ValueError(f"Unsupported landed-cost allocation method: {method}")
        if value < 0:
            raise ValueError(f"GRN line {gl.id} has a negative {method} allocation basis")
        basis[gl.id] = value
    return basis


def _allocate_amounts(amount: Decimal, basis_map: dict, method: str) -> dict:
    """Return four-decimal allocations that reconcile exactly to the source amount."""
    amount = _R(amount)
    if any(_D(value) < 0 for value in basis_map.values()):
        raise ValueError(f"Cannot allocate landed-cost line: the configured {method} basis contains a negative value")
    positive_basis = {key: _D(value) for key, value in basis_map.items() if _D(value) > 0}
    total_basis = sum(positive_basis.values(), Decimal("0"))
    if total_basis <= 0:
        raise ValueError(f"Cannot allocate landed-cost line: the configured {method} basis is unavailable")
    if amount < 0:
        raise ValueError("Negative landed-cost amounts cannot be allocated")

    allocated = {
        key: _R(amount * basis / total_basis)
        for key, basis in positive_basis.items()
    }
    rounding_difference = amount - sum(allocated.values(), Decimal("0"))
    correction_key = max(positive_basis, key=lambda key: (allocated[key], str(key)))
    allocated[correction_key] = _R(allocated[correction_key] + rounding_difference)
    if allocated[correction_key] < 0:
        raise ValueError("Landed-cost rounding correction would create a negative allocation")
    return allocated


def _base_unit_cost(grn_line: GRNLine) -> Decimal:
    po_line = grn_line.po_line
    purchase_order = po_line.po if po_line else None
    if not po_line or not purchase_order:
        return Decimal("0")
    return _D(po_line.unit_price) * _D(purchase_order.exchange_rate)


# ── Post ──────────────────────────────────────────────────────────────────────

async def post_landed_cost(
    db: AsyncSession,
    header_id: UUID,
    posted_by: str = "system",
    posted_by_id: Optional[UUID] = None,
) -> LandedCostHeader:
    """
    Post landed-cost allocations to their source FIFO layers and the GL.

    All changes are committed together. Missing source, account, valuation,
    company, or open-period configuration fails closed before the document is
    marked posted.
    """
    from app.services.finance_service import (
        assert_journal_lines_postable,
        find_inventory_account_mapping,
        get_or_create_operational_posting_event,
        mark_journal_posted,
        mark_operational_posting_posted,
    )

    try:
        if not posted_by_id:
            raise ValueError("An authenticated finance posting actor is required")
        hdr = (await db.execute(
            select(LandedCostHeader)
            .options(
                selectinload(LandedCostHeader.cost_lines),
                selectinload(LandedCostHeader.grn_links),
                selectinload(LandedCostHeader.allocation_lines),
            )
            .where(LandedCostHeader.id == header_id)
            .with_for_update()
        )).scalar_one_or_none()
        if not hdr:
            raise ValueError("Document not found")
        if hdr.status != "VALIDATED":
            raise ValueError(f"Can only post VALIDATED documents (current: {hdr.status})")
        if not hdr.bill_date:
            raise ValueError("A bill date is required for period-aware landed-cost posting")
        if not hdr.allocation_lines:
            raise ValueError("Landed cost must be allocated to GRN lines before posting")

        period = (await db.execute(
            select(AccountingPeriod)
            .where(
                AccountingPeriod.period_start <= hdr.bill_date,
                AccountingPeriod.period_end >= hdr.bill_date,
            )
            .with_for_update()
        )).scalar_one_or_none()
        if not period:
            raise ValueError(f"No accounting period exists for landed-cost bill date {hdr.bill_date.isoformat()}")
        if period.status.value in {"CLOSED", "LOCKED"}:
            raise ValueError(f"Accounting period {period.period_ym} is {period.status.value}")

        cost_lines = {line.id: line for line in hdr.cost_lines}
        for allocation in sorted(hdr.allocation_lines, key=lambda line: str(line.id)):
            if allocation.is_posted:
                if (
                    allocation.accounting_status == OperationalPostingStatus.POSTED
                    and allocation.journal_entry_id
                    and allocation.posting_batch_id
                    and allocation.inventory_adj_id
                ):
                    continue
                raise ValueError(f"Allocation {allocation.id} has an incomplete prior posting; manual reconciliation is required")

            amount = _R(allocation.allocated_amount)
            received_qty = _D(allocation.received_qty)
            if amount <= 0 or received_qty <= 0 or not allocation.material_id:
                raise ValueError(f"Allocation {allocation.id} is missing a positive amount, quantity, or material")
            cost_line = cost_lines.get(allocation.lc_line_id)
            if not cost_line:
                raise ValueError(f"Allocation {allocation.id} does not resolve to a landed-cost line")
            if not allocation.grn_line_id:
                raise ValueError(f"Allocation {allocation.id} has no source GRN line")

            grn_line = await db.get(GRNLine, allocation.grn_line_id)
            if not grn_line or grn_line.grn_id != allocation.grn_id or not grn_line.stock_movement_id:
                raise ValueError(f"Allocation {allocation.id} has no matching source GRN stock movement")
            receipt = await db.get(GoodsReceipt, grn_line.grn_id)
            if not receipt or not receipt.company_id:
                raise ValueError(f"Source GRN line {grn_line.id} has no company for base-currency accounting")
            company = await db.get(Company, receipt.company_id)
            if not company or not company.base_currency:
                raise ValueError(f"Source GRN line {grn_line.id} has no configured company base currency")

            mapping = await find_inventory_account_mapping(
                db,
                stock_type="MATERIAL",
                material_id=allocation.material_id,
            )
            if (
                not mapping
                or not mapping.landed_cost_clearing_account_id
            ):
                raise ValueError(f"Material {allocation.material_id} needs an active landed-cost clearing account mapping")

            layer = None
            inventory_delta = Decimal("0")
            consumed_cost = Decimal("0")
            old_unit_cost = Decimal("0")
            new_unit_cost = Decimal("0")
            new_total_value = Decimal("0")
            on_hand = Decimal("0")
            per_unit_cost = Decimal("0")
            expense_account = None
            if cost_line.is_included_in_valuation:
                if not mapping.inventory_account_id or not mapping.valuation_method:
                    raise ValueError(f"Material {allocation.material_id} needs an inventory account and valuation method mapping")
                if mapping.valuation_method.strip().upper() != "FIFO":
                    raise ValueError(f"Landed-cost capitalization currently requires FIFO valuation; found {mapping.valuation_method}")

                layer = (await db.execute(
                    select(CostLayer)
                    .where(CostLayer.movement_id == grn_line.stock_movement_id)
                    .with_for_update()
                )).scalar_one_or_none()
                if not layer or layer.material_id != allocation.material_id:
                    raise ValueError(f"Source GRN line {grn_line.id} has no matching FIFO cost layer")
                if _D(layer.qty_received) != received_qty:
                    raise ValueError(f"Source FIFO layer quantity does not match allocation {allocation.id}")

                on_hand = _D(layer.qty_remaining)
                old_unit_cost = _D(layer.unit_cost).quantize(Decimal("0.000001"))
                old_total_value = _D(layer.total_value).quantize(Decimal("0.0001"))
                if on_hand < 0 or on_hand > received_qty:
                    raise ValueError(f"Source FIFO layer {layer.id} has an invalid remaining quantity")
                expected_value = _R(on_hand * old_unit_cost)
                if expected_value != old_total_value:
                    raise ValueError(f"Source FIFO layer {layer.id} has inconsistent quantity and value")

                per_unit_cost = _R(amount / received_qty, 6)
                new_unit_cost = (old_unit_cost + per_unit_cost).quantize(Decimal("0.000001"))
                new_total_value = _R(on_hand * new_unit_cost)
                inventory_delta = new_total_value - old_total_value
                consumed_cost = amount - inventory_delta
                if inventory_delta < 0 or consumed_cost < 0:
                    raise ValueError(f"Allocation {allocation.id} cannot be represented safely at configured precision")
                if consumed_cost and not mapping.cogs_account_id:
                    raise ValueError(f"Material {allocation.material_id} needs a COGS account for consumed receipt quantity")
            else:
                if not cost_line.account_code:
                    raise ValueError(f"Non-capitalizable landed-cost line {cost_line.id} needs an explicit expense account code")
                expense_account = (await db.execute(
                    select(ChartOfAccount).where(ChartOfAccount.code == cost_line.account_code)
                )).scalar_one_or_none()
                if not expense_account or expense_account.account_type != AccountType.EXPENSE:
                    raise ValueError(f"Landed-cost expense account {cost_line.account_code} must resolve to a configured expense account")

            event, batch, created = await get_or_create_operational_posting_event(
                db,
                source_module="landed_cost",
                source_event="LANDED_COST_POST",
                source_id=header_id,
                source_line_id=allocation.id,
                source_ref=hdr.lc_no,
                stock_movement_id=grn_line.stock_movement_id,
                event_date=hdr.bill_date,
                amount=amount,
                currency=company.base_currency,
                created_by_id=posted_by_id,
                require_period=True,
            )
            if not created:
                raise ValueError(f"A prior landed-cost posting event exists for allocation {allocation.id}; manual reconciliation is required")

            entry_no = f"LCPOST-{str(allocation.id).replace('-', '')}"
            entry = JournalEntry(
                entry_no=entry_no,
                entry_date=hdr.bill_date,
                description=f"Landed cost allocation {hdr.lc_no}",
                source_module="landed_cost",
                source_event="LANDED_COST_POST",
                source_id=allocation.id,
                source_ref=hdr.lc_no,
                company_id=receipt.company_id,
                status=JournalStatus.DRAFT,
                posting_batch_id=batch.id,
                created_by_id=posted_by_id,
            )
            if cost_line.is_included_in_valuation:
                if inventory_delta:
                    entry.lines.append(JournalLine(
                        account_id=mapping.inventory_account_id,
                        description=f"Inventory landed-cost adjustment {allocation.id}",
                        debit=inventory_delta,
                        credit=Decimal("0"),
                        currency=company.base_currency,
                    ))
                if consumed_cost:
                    entry.lines.append(JournalLine(
                        account_id=mapping.cogs_account_id,
                        description=f"Consumed landed-cost allocation {allocation.id}",
                        debit=consumed_cost,
                        credit=Decimal("0"),
                        currency=company.base_currency,
                    ))
            else:
                entry.lines.append(JournalLine(
                    account_id=expense_account.id,
                    description=f"Landed-cost expense allocation {allocation.id}",
                    debit=amount,
                    credit=Decimal("0"),
                    currency=company.base_currency,
                ))
            entry.lines.append(JournalLine(
                account_id=mapping.landed_cost_clearing_account_id,
                description=f"Landed-cost clearing {allocation.id}",
                debit=Decimal("0"),
                credit=amount,
                currency=company.base_currency,
            ))
            db.add(entry)
            await db.flush()
            await assert_journal_lines_postable(db, entry.lines)
            await mark_journal_posted(db, entry, posted_by_id, require_period=True)
            await mark_operational_posting_posted(
                db,
                event,
                batch,
                journal_entry_id=entry.id,
                posted_by_id=posted_by_id,
            )

            if layer:
                layer.unit_cost = new_unit_cost
                layer.total_value = new_total_value
                adjustment = LCInventoryAdjustment(
                    header_id=header_id,
                    grn_line_id=allocation.grn_line_id,
                    material_id=allocation.material_id,
                    lot_no=allocation.lot_no,
                    adjustment_amount=amount,
                    per_unit_amount=per_unit_cost,
                    qty_on_hand=on_hand,
                    old_avg_cost=old_unit_cost,
                    new_avg_cost=new_unit_cost,
                    journal_ref=entry.entry_no,
                    posting_batch_id=batch.id,
                    journal_entry_id=entry.id,
                    accounting_status=OperationalPostingStatus.POSTED,
                    posted_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                db.add(adjustment)
                await db.flush()
                allocation.inventory_adj_id = adjustment.id
            allocation.is_posted = True
            allocation.posting_batch_id = batch.id
            allocation.journal_entry_id = entry.id
            allocation.accounting_status = OperationalPostingStatus.POSTED
            allocation.posting_error = None
            if event.status != OperationalPostingStatus.POSTED:
                raise ValueError(f"Posting event for allocation {allocation.id} did not reach POSTED")

        hdr.status = "POSTED"
        hdr.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        hdr.posted_by = posted_by
        await db.commit()
        return await get_header(db, header_id)
    except Exception:
        await db.rollback()
        raise


async def cancel_landed_cost(db: AsyncSession, header_id: UUID) -> LandedCostHeader:
    hdr_q = await db.execute(
        select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
    )
    hdr = hdr_q.scalar_one_or_none()
    if not hdr:
        raise ValueError("Document not found")
    if hdr.status == "POSTED":
        raise ValueError("Cannot cancel a posted document")
    hdr.status = "CANCELLED"
    await db.commit()
    return await get_header(db, header_id)


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    now = datetime.utcnow()

    total_q = await db.execute(select(func.count()).select_from(LandedCostHeader))
    total = total_q.scalar() or 0

    by_status_q = await db.execute(
        select(LandedCostHeader.status, func.count())
        .group_by(LandedCostHeader.status)
    )
    by_status = {r[0]: r[1] for r in by_status_q.all()}

    # MTD cost
    mtd_q = await db.execute(
        select(func.coalesce(func.sum(LandedCostHeader.total_lc_amount_base), 0))
        .where(
            and_(
                LandedCostHeader.status == "POSTED",
                extract("year", LandedCostHeader.posted_at) == now.year,
                extract("month", LandedCostHeader.posted_at) == now.month,
            )
        )
    )
    mtd = _D(mtd_q.scalar())

    # YTD cost
    ytd_q = await db.execute(
        select(func.coalesce(func.sum(LandedCostHeader.total_lc_amount_base), 0))
        .where(
            and_(
                LandedCostHeader.status == "POSTED",
                extract("year", LandedCostHeader.posted_at) == now.year,
            )
        )
    )
    ytd = _D(ytd_q.scalar())

    # Pending AI recs
    ai_q = await db.execute(
        select(func.count()).select_from(LCAIRecommendation)
        .where(LCAIRecommendation.status == "PENDING")
    )
    pending_ai = ai_q.scalar() or 0

    # Top cost types
    top_q = await db.execute(
        select(LandedCostLine.cost_type, func.sum(LandedCostLine.amount_base).label("total"))
        .join(LandedCostHeader, LandedCostLine.header_id == LandedCostHeader.id)
        .where(LandedCostHeader.status == "POSTED")
        .group_by(LandedCostLine.cost_type)
        .order_by(func.sum(LandedCostLine.amount_base).desc())
        .limit(5)
    )
    top_cost_types = [{"cost_type": r[0], "total": float(r[1] or 0)} for r in top_q.all()]

    # Recent docs
    recent_q = await db.execute(
        select(LandedCostHeader)
        .order_by(LandedCostHeader.created_at.desc())
        .limit(10)
    )
    recent = list(recent_q.scalars().all())

    return {
        "total_documents": total,
        "draft_count": by_status.get("DRAFT", 0),
        "validated_count": by_status.get("VALIDATED", 0),
        "posted_count": by_status.get("POSTED", 0),
        "cancelled_count": by_status.get("CANCELLED", 0),
        "total_lc_cost_mtd": mtd,
        "total_lc_cost_ytd": ytd,
        "pending_ai_recs": pending_ai,
        "top_cost_types": top_cost_types,
        "recent_documents": recent,
    }


# ── Reports ────────────────────────────────────────────────────────────────────

async def report_cost_by_type(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list:
    q = (
        select(
            LandedCostLine.cost_type,
            func.sum(LandedCostLine.amount_base).label("total_amount"),
            func.count(LandedCostLine.id).label("doc_count"),
        )
        .join(LandedCostHeader, LandedCostLine.header_id == LandedCostHeader.id)
        .where(LandedCostHeader.status == "POSTED")
        .group_by(LandedCostLine.cost_type)
        .order_by(func.sum(LandedCostLine.amount_base).desc())
    )
    if date_from:
        q = q.where(LandedCostHeader.bill_date >= date_from)
    if date_to:
        q = q.where(LandedCostHeader.bill_date <= date_to)

    result = await db.execute(q)
    rows = result.all()

    grand_total = sum(_D(r[1]) for r in rows)
    out = []
    for r in rows:
        total = _D(r[1])
        pct = _R(total / grand_total * 100, 2) if grand_total else Decimal("0")
        out.append({
            "cost_type": r[0],
            "total_amount": total,
            "doc_count": r[2],
            "pct_of_total": pct,
        })
    return out


async def report_allocation_by_material(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list:
    q = (
        select(
            LandedCostAllocationLine.material_name,
            func.sum(LandedCostAllocationLine.allocated_amount).label("total_allocated"),
            func.count(LandedCostAllocationLine.id).label("doc_count"),
            func.avg(LandedCostAllocationLine.per_unit_lc_cost).label("avg_per_unit"),
        )
        .join(LandedCostHeader, LandedCostAllocationLine.header_id == LandedCostHeader.id)
        .where(LandedCostHeader.status == "POSTED")
        .group_by(LandedCostAllocationLine.material_name)
        .order_by(func.sum(LandedCostAllocationLine.allocated_amount).desc())
    )
    if date_from:
        q = q.where(LandedCostHeader.bill_date >= date_from)
    if date_to:
        q = q.where(LandedCostHeader.bill_date <= date_to)

    result = await db.execute(q)
    return [
        {
            "material_name": r[0],
            "total_allocated": _D(r[1]),
            "doc_count": r[2],
            "avg_per_unit": _D(r[3]) if r[3] else None,
        }
        for r in result.all()
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession, header_id: Optional[UUID] = None) -> int:
    """Run 3 AI agents. Returns number of recommendations created."""
    created = 0

    if header_id:
        hdr = await get_header(db, header_id)
        headers = [hdr] if hdr else []
    else:
        q = await db.execute(
            select(LandedCostHeader)
            .options(
                selectinload(LandedCostHeader.cost_lines),
                selectinload(LandedCostHeader.allocation_lines),
            )
            .where(LandedCostHeader.status.in_(["VALIDATED", "POSTED"]))
            .order_by(LandedCostHeader.created_at.desc())
            .limit(20)
        )
        headers = list(q.scalars().all())

    for hdr in headers:
        created += await _agent_cost_analyzer(db, hdr)
        created += await _agent_route_optimizer(db, hdr)
        created += await _agent_variance_detector(db, hdr)

    await db.commit()
    return created


async def _agent_cost_analyzer(db: AsyncSession, hdr: LandedCostHeader) -> int:
    """Flag high-cost components (>30% of total)."""
    if not hdr.cost_lines:
        return 0
    total = _D(hdr.total_lc_amount_base)
    if total == 0:
        return 0
    flagged = []
    for cl in hdr.cost_lines:
        pct = _D(cl.amount_base) / total * 100
        if pct >= 30:
            flagged.append(f"{cl.cost_type} ({_R(pct, 1)}%)")
    if not flagged:
        return 0
    rec = LCAIRecommendation(
        header_id=hdr.id,
        agent_type="COST_ANALYZER",
        status="PENDING",
        title=f"High-cost components detected: {', '.join(flagged)}",
        explanation=(
            f"Document {hdr.lc_no} has cost components exceeding 30% of total landed cost. "
            f"Review vendor pricing and consider renegotiating rates."
        ),
        impact_summary=f"Components at issue: {', '.join(flagged)}. Total LC: {float(total):,.2f}",
        suggested_action="Review pricing with vendors; explore consolidation opportunities.",
        confidence_score=Decimal("0.85"),
    )
    db.add(rec)
    return 1


async def _agent_route_optimizer(db: AsyncSession, hdr: LandedCostHeader) -> int:
    """Suggest cheaper routing if freight > 50% of total."""
    if not hdr.cost_lines:
        return 0
    total = _D(hdr.total_lc_amount_base)
    if total == 0:
        return 0
    freight_types = {"FREIGHT_SEA", "FREIGHT_AIR", "FREIGHT_LAND"}
    freight_total = sum(
        _D(cl.amount_base) for cl in hdr.cost_lines
        if cl.cost_type in freight_types
    )
    pct = freight_total / total * 100
    if pct < 50:
        return 0
    rec = LCAIRecommendation(
        header_id=hdr.id,
        agent_type="ROUTE_OPTIMIZER",
        status="PENDING",
        title=f"Freight cost is {_R(pct, 1)}% of total — consider alternative routing",
        explanation=(
            f"Freight charges account for {_R(pct, 1)}% of the total landed cost on {hdr.lc_no}. "
            f"Sea freight is typically 60–80% cheaper than air."
        ),
        impact_summary=f"Freight: {float(freight_total):,.2f} of {float(total):,.2f} total",
        suggested_action="Evaluate sea freight options or consolidate shipments to reduce per-unit freight cost.",
        confidence_score=Decimal("0.78"),
    )
    db.add(rec)
    return 1


async def _agent_variance_detector(db: AsyncSession, hdr: LandedCostHeader) -> int:
    """Compare LC cost to purchase value and flag if LC > 20% of PO value."""
    if not hdr.allocation_lines:
        return 0
    total_pv = sum(_D(al.purchase_value) for al in hdr.allocation_lines if al.purchase_value)
    if total_pv == 0:
        return 0
    total_lc = _D(hdr.total_lc_amount_base)
    ratio = total_lc / total_pv * 100
    if ratio < 20:
        return 0
    rec = LCAIRecommendation(
        header_id=hdr.id,
        agent_type="VARIANCE_DETECTOR",
        status="PENDING",
        title=f"Landed costs are {_R(ratio, 1)}% of purchase value — unusually high",
        explanation=(
            f"For {hdr.lc_no}, total landed costs ({float(total_lc):,.2f}) represent "
            f"{_R(ratio, 1)}% of the underlying purchase value ({float(total_pv):,.2f}). "
            f"Industry benchmarks suggest 5–15% as normal range."
        ),
        impact_summary=f"LC/PV ratio: {_R(ratio, 1)}%. Target: <15%",
        suggested_action="Audit each cost component; verify demurrage, detention, or storage charges are not inflated.",
        confidence_score=Decimal("0.80"),
    )
    db.add(rec)
    return 1


async def list_ai_recs(
    db: AsyncSession,
    header_id: Optional[UUID] = None,
    status: Optional[str] = None,
) -> List[LCAIRecommendation]:
    q = select(LCAIRecommendation).order_by(LCAIRecommendation.created_at.desc())
    if header_id:
        q = q.where(LCAIRecommendation.header_id == header_id)
    if status:
        q = q.where(LCAIRecommendation.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def action_ai_rec(db: AsyncSession, rec_id: UUID, status: str, actioned_by: str = "user") -> Optional[LCAIRecommendation]:
    q = await db.execute(select(LCAIRecommendation).where(LCAIRecommendation.id == rec_id))
    rec = q.scalar_one_or_none()
    if not rec:
        return None
    rec.status = status
    rec.actioned_at = datetime.utcnow()
    rec.actioned_by = actioned_by
    await db.commit()
    await db.refresh(rec)
    return rec
