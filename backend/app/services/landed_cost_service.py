"""
Landed Cost Allocation Service
Handles: document creation, GRN linking, allocation engine,
         inventory valuation update, posting, 3 AI agents.
"""
from __future__ import annotations

import re
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.landed_cost import (
    LandedCostHeader, LandedCostLine, LandedCostGRNLink,
    LandedCostAllocationLine, LCInventoryAdjustment, LCAIRecommendation,
    LCAllocationMethod,
)
from app.models.procurement import GoodsReceipt, GRNLine
from app.models.master import Material
from app.schemas.landed_cost import (
    LandedCostHeaderCreate, LandedCostHeaderUpdate,
    LandedCostLineCreate, LandedCostGRNLinkCreate,
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


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_header(db: AsyncSession, payload: LandedCostHeaderCreate) -> LandedCostHeader:
    lc_no = await _next_lc_no(db)
    total_fc = sum(_D(l.amount_fc) for l in payload.cost_lines)
    total_base = sum(_D(l.amount_fc) * _D(l.exchange_rate) for l in payload.cost_lines)

    hdr = LandedCostHeader(
        lc_no=lc_no,
        reference_type=payload.reference_type,
        shipment_id=payload.shipment_id,
        po_id=payload.po_id,
        vendor_name=payload.vendor_name,
        bill_no=payload.bill_no,
        bill_date=payload.bill_date,
        currency_code=payload.currency_code,
        exchange_rate=payload.exchange_rate,
        total_lc_amount_fc=_R(total_fc),
        total_lc_amount_base=_R(total_base),
        allocation_method=payload.allocation_method,
        notes=payload.notes,
        status="DRAFT",
    )
    db.add(hdr)
    await db.flush()

    for cl in payload.cost_lines:
        line = LandedCostLine(
            header_id=hdr.id,
            cost_type=cl.cost_type,
            description=cl.description,
            vendor_name=cl.vendor_name,
            amount_fc=_R(cl.amount_fc),
            currency_code=cl.currency_code,
            exchange_rate=_R(cl.exchange_rate, 6),
            amount_base=_R(_D(cl.amount_fc) * _D(cl.exchange_rate)),
            allocation_method=cl.allocation_method,
            is_included_in_valuation=cl.is_included_in_valuation,
            account_code=cl.account_code,
            remarks=cl.remarks,
        )
        db.add(line)

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
            selectinload(LandedCostHeader.cost_lines),
            selectinload(LandedCostHeader.grn_links),
            selectinload(LandedCostHeader.allocation_lines),
            selectinload(LandedCostHeader.ai_recs),
        )
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
    hdr = await get_header(db, header_id)
    if not hdr:
        return None
    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(hdr, k, v)
    await db.commit()
    return await get_header(db, header_id)


async def add_cost_line(db: AsyncSession, header_id: UUID, payload: LandedCostLineCreate) -> LandedCostHeader:
    line = LandedCostLine(
        header_id=header_id,
        cost_type=payload.cost_type,
        description=payload.description,
        vendor_name=payload.vendor_name,
        amount_fc=_R(payload.amount_fc),
        currency_code=payload.currency_code,
        exchange_rate=_R(payload.exchange_rate, 6),
        amount_base=_R(_D(payload.amount_fc) * _D(payload.exchange_rate)),
        allocation_method=payload.allocation_method,
        is_included_in_valuation=payload.is_included_in_valuation,
        account_code=payload.account_code,
        remarks=payload.remarks,
    )
    db.add(line)
    # recalculate header totals
    hdr_q = await db.execute(select(LandedCostHeader).where(LandedCostHeader.id == header_id))
    hdr = hdr_q.scalar_one()
    lines_q = await db.execute(select(LandedCostLine).where(LandedCostLine.header_id == header_id))
    existing = list(lines_q.scalars().all())
    total_base = sum(_D(l.amount_base) for l in existing) + _R(_D(payload.amount_fc) * _D(payload.exchange_rate))
    hdr.total_lc_amount_base = total_base
    await db.commit()
    return await get_header(db, header_id)


async def add_grn_link(db: AsyncSession, header_id: UUID, payload: LandedCostGRNLinkCreate) -> LandedCostHeader:
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
    hdr = await get_header(db, header_id)
    if not hdr:
        raise ValueError("Landed cost document not found")
    if hdr.status not in ("DRAFT", "VALIDATED"):
        raise ValueError(f"Cannot allocate in status {hdr.status}")

    # Clear existing allocation lines
    await db.execute(
        LandedCostAllocationLine.__table__.delete().where(
            LandedCostAllocationLine.header_id == header_id
        )
    )

    # Collect GRN lines for all linked GRNs
    grn_ids = [gl.grn_id for gl in hdr.grn_links]
    if not grn_ids:
        await db.commit()
        return await get_header(db, header_id)

    grn_lines_q = await db.execute(
        select(GRNLine).where(GRNLine.grn_id.in_(grn_ids))
    )
    grn_lines: List[GRNLine] = list(grn_lines_q.scalars().all())

    # Build allocation basis per GRN line for each cost line
    cost_lines = [cl for cl in hdr.cost_lines if cl.is_included_in_valuation]

    for cl in cost_lines:
        method = cl.allocation_method or hdr.allocation_method
        basis_map = _compute_basis(method, grn_lines)
        total_basis = sum(basis_map.values())
        if total_basis == Decimal("0"):
            # fallback to equal split
            total_basis = Decimal(len(grn_lines))
            basis_map = {gl.id: Decimal("1") for gl in grn_lines}

        total_allocated = Decimal("0")
        alloc_rows = []
        for gl in grn_lines:
            basis = basis_map.get(gl.id, Decimal("0"))
            share = basis / total_basis if total_basis else Decimal("0")
            allocated = _R(_D(cl.amount_base) * share)
            per_unit = _R(allocated / _D(gl.received_qty), 6) if _D(gl.received_qty) > 0 else None
            total_allocated += allocated
            alloc_rows.append(LandedCostAllocationLine(
                header_id=header_id,
                lc_line_id=cl.id,
                grn_id=gl.grn_id,
                grn_line_id=gl.id,
                material_id=gl.material_id,
                material_name=gl.material_name,
                lot_no=getattr(gl, "lot_no", None),
                received_qty=gl.received_qty,
                purchase_value=_D(gl.unit_cost) * _D(gl.received_qty) if gl.unit_cost else None,
                allocation_basis=basis,
                allocation_share=_R(share * 100, 4),
                allocated_amount=allocated,
                per_unit_lc_cost=per_unit,
                is_posted=False,
            ))

        # Rounding correction on last row
        if alloc_rows:
            diff = _R(_D(cl.amount_base)) - total_allocated
            alloc_rows[-1].allocated_amount = _R(alloc_rows[-1].allocated_amount + diff)

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
            basis[gl.id] = _D(gl.received_qty)
        elif method == LCAllocationMethod.BY_WEIGHT:
            basis[gl.id] = _D(getattr(gl, "gross_weight", None))
        elif method == LCAllocationMethod.BY_VOLUME:
            basis[gl.id] = _D(getattr(gl, "volume", None))
        elif method == LCAllocationMethod.BY_VALUE:
            val = _D(gl.unit_cost) * _D(gl.received_qty) if gl.unit_cost else Decimal("0")
            basis[gl.id] = val
        else:  # EQUAL_SPLIT / CUSTOM
            basis[gl.id] = Decimal("1")
    return basis


# ── Post ──────────────────────────────────────────────────────────────────────

async def post_landed_cost(db: AsyncSession, header_id: UUID, posted_by: str = "system") -> LandedCostHeader:
    """
    Post: create inventory adjustment records for all allocation lines,
    update average costs, mark document as POSTED.
    """
    hdr = await get_header(db, header_id)
    if not hdr:
        raise ValueError("Document not found")
    if hdr.status != "VALIDATED":
        raise ValueError(f"Can only post VALIDATED documents (current: {hdr.status})")

    for al in hdr.allocation_lines:
        if al.is_posted:
            continue
        # Create inventory adjustment
        adj = LCInventoryAdjustment(
            header_id=header_id,
            grn_line_id=al.grn_line_id,
            material_id=al.material_id,
            lot_no=al.lot_no,
            adjustment_amount=al.allocated_amount,
            per_unit_amount=al.per_unit_lc_cost,
            posted_at=datetime.utcnow(),
        )
        db.add(adj)
        await db.flush()
        al.is_posted = True
        al.inventory_adj_id = adj.id

    # Mark header as POSTED
    hdr_row_q = await db.execute(select(LandedCostHeader).where(LandedCostHeader.id == header_id))
    hdr_row = hdr_row_q.scalar_one()
    hdr_row.status = "POSTED"
    hdr_row.posted_at = datetime.utcnow()
    hdr_row.posted_by = posted_by
    await db.commit()
    return await get_header(db, header_id)


async def cancel_landed_cost(db: AsyncSession, header_id: UUID) -> LandedCostHeader:
    hdr_q = await db.execute(select(LandedCostHeader).where(LandedCostHeader.id == header_id))
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
