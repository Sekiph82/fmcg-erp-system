"""
Procurement Suggestion Engine
─────────────────────────────
Converts MRP shortages + inventory state into intelligent purchasing decisions.
Handles: supplier selection, MOQ enforcement, lead-time planning, grouping,
urgency classification, risk flagging, and PR conversion.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Stock, StockType
from app.models.master import Material, Supplier
from app.models.mrp import MRPRun, MRPResult, MRPSuggestion, SuggestionType as MRPSuggestionType
from app.models.procurement import (
    POLine, POStatus, PurchaseOrder,
    PurchaseRequisition, PRLine, PRStatus,
)
from app.models.user import User
from app.models.procurement_suggestion import (
    PSAIAgentType, PSAIRecommendation,
    PSGroupStatus, PSRunStatus,
    PSSuggestionStatus, PSUrgencyLevel,
    SupplierItemPriority, SupplierItemPrice,
    ProcurementSuggestionRun, ProcurementSuggestionLine,
    ProcurementSuggestionGroup,
)
from app.schemas.procurement_suggestion import (
    ConvertGroupToPRRequest, PSDashboard,
    PSLineUpdate, PSRunCreate,
    ShortageReportRow, SupplierCompareResult, SupplierCompareRow,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    q = Decimal("0." + "0" * dp)
    return v.quantize(q, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _today() -> date:
    return date.today()


def _run_no() -> str:
    d = _today().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:6].upper()
    return f"PS-{d}-{short}"


def _group_no(supplier_code: str) -> str:
    d = _today().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:4].upper()
    return f"PG-{supplier_code[:6].upper()}-{d}-{short}"


# ── Round up to MOQ / pack_size ───────────────────────────────────────────────

def _apply_moq(qty: Decimal, moq: Decimal, pack_size: Optional[Decimal]) -> Decimal:
    """Round qty up to satisfy MOQ and pack_size."""
    result = max(qty, moq)
    if pack_size and pack_size > 0:
        import math
        multiples = math.ceil(float(result) / float(pack_size))
        result = Decimal(str(multiples)) * pack_size
    return _R(result)


# ── Supplier scoring ──────────────────────────────────────────────────────────

def _score_supplier(sip: SupplierItemPrice, supplier: Supplier) -> Decimal:
    """Composite score 0-100 (higher = better)."""
    score = Decimal("50")

    # Priority bonus
    priority_bonus = {
        SupplierItemPriority.PRIMARY:   Decimal("30"),
        SupplierItemPriority.SECONDARY: Decimal("15"),
        SupplierItemPriority.TERTIARY:  Decimal("5"),
        SupplierItemPriority.FALLBACK:  Decimal("0"),
    }
    score += priority_bonus.get(sip.priority, Decimal("0"))

    # Reliability score (0-100 → 0-10 contribution)
    if sip.reliability_score:
        score += _D(sip.reliability_score) / Decimal("10")

    # Supplier performance score (0-100 → 0-10 contribution)
    if supplier.performance_score:
        score += _D(supplier.performance_score) / Decimal("10")

    # Preferred supplier bonus
    if supplier.is_preferred:
        score += Decimal("5")

    return min(_R(score, 2), Decimal("100"))


# ── Urgency classification ─────────────────────────────────────────────────────

def _classify_urgency(
    shortage_qty: Decimal,
    available_qty: Decimal,
    required_date: Optional[date],
    lead_time_days: int,
) -> PSUrgencyLevel:
    if shortage_qty <= 0:
        return PSUrgencyLevel.LOW

    today = _today()
    days_to_required = (required_date - today).days if required_date else 999

    if available_qty <= 0 and days_to_required <= lead_time_days:
        return PSUrgencyLevel.CRITICAL
    if days_to_required <= lead_time_days + 3:
        return PSUrgencyLevel.HIGH
    if days_to_required <= lead_time_days + 14:
        return PSUrgencyLevel.MEDIUM
    return PSUrgencyLevel.LOW


# ── Risk detection ────────────────────────────────────────────────────────────

def _detect_risks(
    sip_list: List[SupplierItemPrice],
    lead_time_days: int,
    shortage_qty: Decimal,
) -> Tuple[bool, str]:
    notes: List[str] = []

    if len(sip_list) == 1:
        notes.append("Single-supplier dependency")
    if lead_time_days > 30:
        notes.append(f"Long lead time ({lead_time_days}d)")
    if shortage_qty > 0 and not sip_list:
        notes.append("No supplier mapped for this material")

    return bool(notes), "; ".join(notes)


# ── Stock aggregation ─────────────────────────────────────────────────────────

async def _get_material_stock(
    db: AsyncSession,
    material_id: UUID,
    warehouse_id: Optional[UUID],
) -> Tuple[Decimal, Decimal]:
    """Return (available_qty, on_hand_qty) excluding blocked/QC-hold stock."""
    q = (
        select(
            func.sum(Stock.quantity_available).label("avail"),
            func.sum(Stock.quantity_on_hand).label("on_hand"),
        )
        .where(
            Stock.material_id == material_id,
            Stock.stock_type == StockType.MATERIAL,
            Stock.is_blocked == False,
        )
    )
    if warehouse_id:
        q = q.where(Stock.warehouse_id == warehouse_id)

    row = (await db.execute(q)).one_or_none()
    avail   = _D(row.avail)   if row and row.avail   else Decimal("0")
    on_hand = _D(row.on_hand) if row and row.on_hand else Decimal("0")
    return avail, on_hand


async def _get_incoming_po_qty(
    db: AsyncSession,
    material_id: UUID,
) -> Decimal:
    """Sum open PO lines not yet received."""
    q = (
        select(func.sum(POLine.ordered_quantity - POLine.received_quantity))
        .join(PurchaseOrder, POLine.po_id == PurchaseOrder.id)
        .where(
            POLine.material_id == material_id,
            PurchaseOrder.status.in_([POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]),
        )
    )
    val = (await db.execute(q)).scalar()
    return max(_D(val), Decimal("0"))


# ── Select best supplier ───────────────────────────────────────────────────────

async def _select_supplier(
    db: AsyncSession,
    material_id: UUID,
    run_date: date,
) -> Tuple[Optional[SupplierItemPrice], List[SupplierItemPrice]]:
    """Return (best_sip, all_sips). Respects validity window."""
    q = (
        select(SupplierItemPrice)
        .options(selectinload(SupplierItemPrice.supplier))
        .where(
            SupplierItemPrice.material_id == material_id,
            SupplierItemPrice.is_active == True,
            or_(SupplierItemPrice.valid_from == None, SupplierItemPrice.valid_from <= run_date),
            or_(SupplierItemPrice.valid_to   == None, SupplierItemPrice.valid_to   >= run_date),
        )
    )
    result = await db.execute(q)
    sips: List[SupplierItemPrice] = list(result.scalars().all())

    if not sips:
        return None, []

    # Score each and pick best
    scored = [(sip, _score_supplier(sip, sip.supplier)) for sip in sips]
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[0][0], [s for s, _ in scored]


# ── Core engine ───────────────────────────────────────────────────────────────

async def create_run(db: AsyncSession, payload: PSRunCreate, user_id: UUID) -> ProcurementSuggestionRun:
    run = ProcurementSuggestionRun(
        run_no=_run_no(),
        suggestion_date=_today(),
        warehouse_id=payload.warehouse_id,
        mrp_run_id=payload.mrp_run_id,
        status=PSRunStatus.QUEUED,
        planning_horizon_days=payload.planning_horizon_days,
        include_safety_stock=payload.include_safety_stock,
        include_reorder_point=payload.include_reorder_point,
        currency=payload.currency,
        notes=payload.notes,
        created_by=user_id,
    )
    db.add(run)
    await db.flush()
    return run


async def execute_run(db: AsyncSession, run_id: UUID) -> ProcurementSuggestionRun:
    """Run the procurement suggestion engine for a given run record."""
    run = await db.get(ProcurementSuggestionRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")
    if run.status not in (PSRunStatus.QUEUED, PSRunStatus.FAILED):
        raise ValueError(f"Run already in status {run.status}")

    run.status     = PSRunStatus.RUNNING
    run.started_at = _now()
    await db.flush()

    try:
        await _engine_logic(db, run)
        run.status       = PSRunStatus.COMPLETED
        run.completed_at = _now()
    except Exception as exc:
        run.status        = PSRunStatus.FAILED
        run.error_message = str(exc)
        run.completed_at  = _now()
        raise

    await db.flush()
    return run


async def _engine_logic(db: AsyncSession, run: ProcurementSuggestionRun) -> None:
    today       = _today()
    horizon     = today + timedelta(days=run.planning_horizon_days)
    run_date    = today

    # ── 1. Collect materials that need procurement ────────────────────────────
    # Source A: MRP shortages (PROCUREMENT type) if mrp_run_id linked
    # Source B: Materials below safety stock / reorder point

    candidate_materials: Dict[UUID, dict] = {}

    if run.mrp_run_id:
        q = (
            select(MRPSuggestion)
            .options(selectinload(MRPSuggestion.material))
            .where(
                MRPSuggestion.run_id == run.mrp_run_id,
                MRPSuggestion.suggestion_type == MRPSuggestionType.PROCUREMENT,
                MRPSuggestion.material_id != None,
            )
        )
        rows = (await db.execute(q)).scalars().all()
        for s in rows:
            if s.material_id not in candidate_materials:
                candidate_materials[s.material_id] = {
                    "required_qty":   _D(s.suggested_qty),
                    "required_date":  s.required_date,
                    "mrp_suggestion_id": s.id,
                }
            else:
                # accumulate if multiple MRP lines for same material
                candidate_materials[s.material_id]["required_qty"] += _D(s.suggested_qty)

    # Source B: All active materials — check safety stock / reorder point
    if run.include_safety_stock or run.include_reorder_point:
        mats_q = select(Material).where(Material.is_active == True)
        mats   = (await db.execute(mats_q)).scalars().all()

        for mat in mats:
            mat_id = mat.id
            avail, _ = await _get_material_stock(db, mat_id, run.warehouse_id)

            trigger = False
            trigger_qty = Decimal("0")

            if run.include_reorder_point and mat.reorder_point:
                rp = _D(mat.reorder_point)
                if avail < rp:
                    trigger = True
                    trigger_qty = max(trigger_qty, rp - avail)

            if trigger and mat_id not in candidate_materials:
                candidate_materials[mat_id] = {
                    "required_qty":   _R(trigger_qty),
                    "required_date":  today + timedelta(days=30),
                    "mrp_suggestion_id": None,
                }

    # ── 2. Build suggestion lines ─────────────────────────────────────────────
    lines_created = 0
    total_cost    = Decimal("0")

    for mat_id, meta in candidate_materials.items():
        mat = await db.get(Material, mat_id)
        if not mat:
            continue

        avail, on_hand          = await _get_material_stock(db, mat_id, run.warehouse_id)
        incoming_po             = await _get_incoming_po_qty(db, mat_id)
        required_qty            = _D(meta["required_qty"])
        required_date: Optional[date] = meta.get("required_date")
        mrp_suggestion_id       = meta.get("mrp_suggestion_id")

        safety_stock  = Decimal("0")  # future: per-material safety stock table
        reorder_point = _D(mat.reorder_point)

        effective_supply = avail + incoming_po
        shortage_qty     = max(required_qty - effective_supply, Decimal("0"))

        if shortage_qty <= 0 and avail >= reorder_point:
            continue  # no need to order

        # Select best supplier
        best_sip, all_sips = await _select_supplier(db, mat_id, run_date)

        # MOQ / pack size enforcement
        order_qty    = max(shortage_qty, _D(best_sip.moq) if best_sip else Decimal("1"))
        if best_sip:
            order_qty = _apply_moq(order_qty, _D(best_sip.moq), _D(best_sip.pack_size) if best_sip.pack_size else None)

        # Lead time
        lead_time = (
            best_sip.lead_time_days + best_sip.buffer_days + best_sip.customs_days
            if best_sip
            else _D(mat.lead_time_days)
        )
        lead_time_days = int(lead_time) if not isinstance(lead_time, int) else lead_time

        # Suggested order date
        if required_date:
            sod = required_date - timedelta(days=lead_time_days)
        else:
            sod = today

        # Urgency
        urgency = _classify_urgency(shortage_qty, avail, required_date, lead_time_days)

        # Risk
        risk_flag, risk_notes = _detect_risks(all_sips, lead_time_days, shortage_qty)

        # Cost estimate
        supplier_price       = _D(best_sip.unit_price) if best_sip else Decimal("0")
        estimated_total_cost = _R(order_qty * supplier_price, 4)
        total_cost          += estimated_total_cost

        # Alt suppliers
        alt_ids = [str(s.supplier_id) for s in all_sips if best_sip and s.supplier_id != best_sip.supplier_id]

        # Recommendation score (simple heuristic)
        rec_score = Decimal("50")
        if urgency == PSUrgencyLevel.CRITICAL:
            rec_score = Decimal("95")
        elif urgency == PSUrgencyLevel.HIGH:
            rec_score = Decimal("80")
        elif urgency == PSUrgencyLevel.MEDIUM:
            rec_score = Decimal("65")
        if risk_flag:
            rec_score -= Decimal("10")

        line = ProcurementSuggestionLine(
            run_id=run.id,
            material_id=mat_id,
            uom=mat.uom.value if mat.uom else None,
            required_qty=_R(required_qty),
            available_qty=_R(avail),
            shortage_qty=_R(shortage_qty),
            safety_stock_qty=_R(safety_stock),
            reorder_point_qty=_R(reorder_point),
            incoming_po_qty=_R(incoming_po),
            supplier_id=best_sip.supplier_id if best_sip else None,
            alternative_supplier_ids=alt_ids or None,
            supplier_price=supplier_price if best_sip else None,
            currency=best_sip.currency if best_sip else run.currency,
            moq=_D(best_sip.moq) if best_sip else None,
            pack_size=_D(best_sip.pack_size) if best_sip and best_sip.pack_size else None,
            adjusted_order_qty=order_qty,
            estimated_total_cost=estimated_total_cost if best_sip else None,
            lead_time_days=best_sip.lead_time_days if best_sip else mat.lead_time_days,
            buffer_days=best_sip.buffer_days if best_sip else 0,
            required_date=required_date,
            suggested_order_date=sod,
            urgency_level=urgency,
            risk_flag=risk_flag,
            risk_notes=risk_notes or None,
            recommendation_score=min(rec_score, Decimal("100")),
            status=PSSuggestionStatus.DRAFT,
            mrp_suggestion_id=mrp_suggestion_id,
        )
        db.add(line)
        lines_created += 1

    await db.flush()

    # ── 3. Group by supplier ──────────────────────────────────────────────────
    await _build_groups(db, run)

    run.suggestion_count    = lines_created
    run.total_estimated_cost = _R(total_cost, 4)


async def _build_groups(db: AsyncSession, run: ProcurementSuggestionRun) -> None:
    """Group suggestion lines by supplier into consolidated orders."""
    # Delete existing groups
    existing_groups = (await db.execute(
        select(ProcurementSuggestionGroup).where(ProcurementSuggestionGroup.run_id == run.id)
    )).scalars().all()
    for g in existing_groups:
        await db.delete(g)
    await db.flush()

    # Fetch lines with supplier
    lines_q = (
        select(ProcurementSuggestionLine)
        .options(
            selectinload(ProcurementSuggestionLine.supplier),
            selectinload(ProcurementSuggestionLine.material),
        )
        .where(
            ProcurementSuggestionLine.run_id == run.id,
            ProcurementSuggestionLine.supplier_id != None,
        )
    )
    lines = (await db.execute(lines_q)).scalars().all()

    # Group by supplier_id
    from collections import defaultdict
    by_supplier: Dict[UUID, List[ProcurementSuggestionLine]] = defaultdict(list)
    for line in lines:
        by_supplier[line.supplier_id].append(line)

    for sup_id, sup_lines in by_supplier.items():
        total_cost  = sum(_D(l.estimated_total_cost) for l in sup_lines if l.estimated_total_cost)
        target_date = min((l.required_date for l in sup_lines if l.required_date), default=None)
        supplier    = sup_lines[0].supplier

        group = ProcurementSuggestionGroup(
            run_id=run.id,
            supplier_id=sup_id,
            group_no=_group_no(supplier.code if supplier else "UNK"),
            target_delivery_date=target_date,
            line_count=len(sup_lines),
            total_estimated_cost=_R(total_cost, 4),
            currency=sup_lines[0].currency,
            status=PSGroupStatus.DRAFT,
        )
        db.add(group)
        await db.flush()

        for line in sup_lines:
            line.group_id = group.id

    await db.flush()


# ── Get / list runs ───────────────────────────────────────────────────────────

async def list_runs(db: AsyncSession, skip: int = 0, limit: int = 50) -> List[ProcurementSuggestionRun]:
    q = (
        select(ProcurementSuggestionRun)
        .options(selectinload(ProcurementSuggestionRun.warehouse))
        .order_by(ProcurementSuggestionRun.created_at.desc())
        .offset(skip).limit(limit)
    )
    return list((await db.execute(q)).scalars().all())


async def get_run(db: AsyncSession, run_id: UUID) -> Optional[ProcurementSuggestionRun]:
    return await db.get(ProcurementSuggestionRun, run_id)


async def list_lines(
    db: AsyncSession,
    run_id: UUID,
    urgency: Optional[PSUrgencyLevel] = None,
    risk_only: bool = False,
    status: Optional[PSSuggestionStatus] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[ProcurementSuggestionLine]:
    q = (
        select(ProcurementSuggestionLine)
        .options(
            selectinload(ProcurementSuggestionLine.material),
            selectinload(ProcurementSuggestionLine.supplier),
        )
        .where(ProcurementSuggestionLine.run_id == run_id)
    )
    if urgency:
        q = q.where(ProcurementSuggestionLine.urgency_level == urgency)
    if risk_only:
        q = q.where(ProcurementSuggestionLine.risk_flag == True)
    if status:
        q = q.where(ProcurementSuggestionLine.status == status)
    q = q.order_by(ProcurementSuggestionLine.urgency_level.asc(), ProcurementSuggestionLine.recommendation_score.desc())
    q = q.offset(skip).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def update_line(db: AsyncSession, line_id: UUID, payload: PSLineUpdate) -> ProcurementSuggestionLine:
    line = await db.get(ProcurementSuggestionLine, line_id)
    if not line:
        raise ValueError(f"Line {line_id} not found")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(line, field, val)

    # Recalculate cost if qty or price changed
    if payload.adjusted_order_qty is not None and line.supplier_price:
        line.estimated_total_cost = _R(_D(line.adjusted_order_qty) * _D(line.supplier_price), 4)

    await db.flush()
    return line


async def approve_line(db: AsyncSession, line_id: UUID) -> ProcurementSuggestionLine:
    line = await db.get(ProcurementSuggestionLine, line_id)
    if not line:
        raise ValueError(f"Line {line_id} not found")
    line.status = PSSuggestionStatus.APPROVED
    await db.flush()
    return line


async def reject_line(db: AsyncSession, line_id: UUID, reason: Optional[str] = None) -> ProcurementSuggestionLine:
    line = await db.get(ProcurementSuggestionLine, line_id)
    if not line:
        raise ValueError(f"Line {line_id} not found")
    line.status = PSSuggestionStatus.REJECTED
    if reason:
        line.notes = reason
    await db.flush()
    return line


# ── Groups ────────────────────────────────────────────────────────────────────

async def list_groups(db: AsyncSession, run_id: UUID) -> List[ProcurementSuggestionGroup]:
    q = (
        select(ProcurementSuggestionGroup)
        .options(
            selectinload(ProcurementSuggestionGroup.supplier),
            selectinload(ProcurementSuggestionGroup.lines).selectinload(ProcurementSuggestionLine.material),
        )
        .where(ProcurementSuggestionGroup.run_id == run_id)
        .order_by(ProcurementSuggestionGroup.total_estimated_cost.desc())
    )
    return list((await db.execute(q)).scalars().all())


# ── Convert group → Purchase Requisition ─────────────────────────────────────

async def _resolve_user_id(db: AsyncSession, user_id: Optional[UUID]) -> UUID:
    """Return user_id if provided, else fetch the first existing user as fallback."""
    if user_id:
        return user_id
    first_user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    if not first_user:
        raise ValueError("No users exist in the database. Create a user account first.")
    return first_user.id


async def convert_group_to_pr(
    db: AsyncSession,
    payload: ConvertGroupToPRRequest,
    user_id: Optional[UUID],
) -> PurchaseRequisition:
    group_id = payload.group_id

    group_q = (
        select(ProcurementSuggestionGroup)
        .options(
            selectinload(ProcurementSuggestionGroup.supplier),
            selectinload(ProcurementSuggestionGroup.lines).selectinload(ProcurementSuggestionLine.material),
        )
        .where(ProcurementSuggestionGroup.id == group_id)
    )
    group = (await db.execute(group_q)).scalar_one_or_none()
    if not group:
        raise ValueError(f"Group {group_id} not found")
    if group.status == PSGroupStatus.CONVERTED:
        raise ValueError("Group already converted to PR")

    resolved_user = await _resolve_user_id(db, user_id)

    # Build PR number
    d = _today().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:6].upper()
    pr_no = f"PR-PS-{d}-{short}"

    pr = PurchaseRequisition(
        pr_no=pr_no,
        requester_id=resolved_user,
        department="Procurement",
        required_date=payload.required_date,
        status=PRStatus.DRAFT,
        notes=payload.notes or f"Auto-generated from Procurement Suggestion Group {group.group_no}",
    )
    db.add(pr)
    await db.flush()

    for idx, line in enumerate(group.lines, start=1):
        if line.status == PSSuggestionStatus.REJECTED:
            continue
        pr_line = PRLine(
            pr_id=pr.id,
            line_no=idx,
            material_id=line.material_id,
            description=line.material.name if line.material else None,
            quantity=line.adjusted_order_qty,
            unit=line.uom or "KG",
            estimated_unit_cost=line.supplier_price,
            preferred_supplier_id=line.supplier_id,
        )
        db.add(pr_line)
        line.status        = PSSuggestionStatus.CONVERTED
        line.converted_pr_id = pr.id

    group.status        = PSGroupStatus.CONVERTED
    group.converted_pr_id = pr.id
    await db.flush()

    return pr


# ── Supplier compare ──────────────────────────────────────────────────────────

async def compare_suppliers_for_material(
    db: AsyncSession,
    material_id: UUID,
) -> SupplierCompareResult:
    mat = await db.get(Material, material_id)
    if not mat:
        raise ValueError(f"Material {material_id} not found")

    q = (
        select(SupplierItemPrice)
        .options(selectinload(SupplierItemPrice.supplier))
        .where(
            SupplierItemPrice.material_id == material_id,
            SupplierItemPrice.is_active == True,
        )
    )
    sips = list((await db.execute(q)).scalars().all())

    rows: List[SupplierCompareRow] = []
    for sip in sips:
        sup = sip.supplier
        total_lead = sip.lead_time_days + sip.buffer_days + sip.customs_days
        score      = _score_supplier(sip, sup)
        rows.append(SupplierCompareRow(
            supplier_id=sip.supplier_id,
            supplier_name=sup.name,
            supplier_code=sup.code,
            priority=sip.priority.value,
            unit_price=_D(sip.unit_price),
            currency=sip.currency,
            moq=_D(sip.moq),
            lead_time_days=sip.lead_time_days,
            total_lead_days=total_lead,
            reliability_score=_D(sip.reliability_score) if sip.reliability_score else None,
            contract_no=sip.contract_no,
            performance_score=_D(sup.performance_score) if sup.performance_score else None,
            is_preferred=sup.is_preferred,
            score=score,
        ))

    rows.sort(key=lambda r: r.score, reverse=True)
    recommended = rows[0].supplier_id if rows else None

    return SupplierCompareResult(
        material_id=material_id,
        material_name=mat.name,
        material_code=mat.code,
        suppliers=rows,
        recommended_supplier_id=recommended,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> PSDashboard:
    total_runs = (await db.execute(select(func.count()).select_from(ProcurementSuggestionRun))).scalar() or 0

    latest_run_q = (
        select(ProcurementSuggestionRun)
        .order_by(ProcurementSuggestionRun.created_at.desc())
        .limit(1)
    )
    latest_run = (await db.execute(latest_run_q)).scalar_one_or_none()

    open_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.status.in_([PSSuggestionStatus.DRAFT, PSSuggestionStatus.REVIEWED])
    )
    open_suggestions = (await db.execute(open_q)).scalar() or 0

    critical_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.urgency_level == PSUrgencyLevel.CRITICAL
    )
    critical_suggestions = (await db.execute(critical_q)).scalar() or 0

    high_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.urgency_level == PSUrgencyLevel.HIGH
    )
    high_suggestions = (await db.execute(high_q)).scalar() or 0

    risk_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.risk_flag == True
    )
    risk_flagged = (await db.execute(risk_q)).scalar() or 0

    cost_q = select(func.sum(ProcurementSuggestionLine.estimated_total_cost)).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.status != PSSuggestionStatus.REJECTED
    )
    total_cost = _D((await db.execute(cost_q)).scalar())

    approved_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.status == PSSuggestionStatus.APPROVED
    )
    approved_count = (await db.execute(approved_q)).scalar() or 0

    converted_q = select(func.count()).select_from(ProcurementSuggestionLine).where(
        ProcurementSuggestionLine.status == PSSuggestionStatus.CONVERTED
    )
    converted_count = (await db.execute(converted_q)).scalar() or 0

    supplier_count = (await db.execute(select(func.count()).select_from(Supplier).where(Supplier.is_active == True))).scalar() or 0
    sip_count = (await db.execute(select(func.count()).select_from(SupplierItemPrice).where(SupplierItemPrice.is_active == True))).scalar() or 0

    ai_q = select(func.count()).select_from(PSAIRecommendation)
    ai_recs = (await db.execute(ai_q)).scalar() or 0

    return PSDashboard(
        total_runs=total_runs,
        latest_run_no=latest_run.run_no if latest_run else None,
        latest_run_status=latest_run.status.value if latest_run else None,
        open_suggestions=open_suggestions,
        critical_suggestions=critical_suggestions,
        high_suggestions=high_suggestions,
        risk_flagged=risk_flagged,
        total_estimated_cost=_R(total_cost, 2),
        approved_count=approved_count,
        converted_count=converted_count,
        supplier_count=supplier_count,
        supplier_items_count=sip_count,
        ai_recs_count=ai_recs,
    )


# ── Shortage report ───────────────────────────────────────────────────────────

async def get_shortage_report(db: AsyncSession, run_id: UUID) -> List[ShortageReportRow]:
    lines_q = (
        select(ProcurementSuggestionLine)
        .options(
            selectinload(ProcurementSuggestionLine.material),
            selectinload(ProcurementSuggestionLine.supplier),
        )
        .where(
            ProcurementSuggestionLine.run_id == run_id,
            ProcurementSuggestionLine.shortage_qty > 0,
        )
        .order_by(ProcurementSuggestionLine.urgency_level.asc())
    )
    lines = list((await db.execute(lines_q)).scalars().all())

    return [
        ShortageReportRow(
            material_id=l.material_id,
            material_code=l.material.code if l.material else str(l.material_id),
            material_name=l.material.name if l.material else "",
            uom=l.uom,
            available_qty=l.available_qty,
            required_qty=l.required_qty,
            shortage_qty=l.shortage_qty,
            safety_stock_qty=l.safety_stock_qty,
            reorder_point_qty=l.reorder_point_qty,
            urgency_level=l.urgency_level.value,
            risk_flag=l.risk_flag,
            suggested_order_date=l.suggested_order_date,
            required_date=l.required_date,
            supplier_name=l.supplier.name if l.supplier else None,
            estimated_cost=l.estimated_total_cost,
        )
        for l in lines
    ]


# ── SupplierItemPrice CRUD ────────────────────────────────────────────────────

async def list_supplier_prices(
    db: AsyncSession,
    material_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[SupplierItemPrice]:
    q = (
        select(SupplierItemPrice)
        .options(
            selectinload(SupplierItemPrice.supplier),
            selectinload(SupplierItemPrice.material),
        )
    )
    if material_id:
        q = q.where(SupplierItemPrice.material_id == material_id)
    if supplier_id:
        q = q.where(SupplierItemPrice.supplier_id == supplier_id)
    q = q.offset(skip).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def create_supplier_price(
    db: AsyncSession,
    payload,
) -> SupplierItemPrice:
    from app.schemas.procurement_suggestion import SupplierItemPriceCreate
    sip = SupplierItemPrice(**payload.model_dump())
    db.add(sip)
    await db.flush()
    return sip


async def update_supplier_price(
    db: AsyncSession,
    sip_id: UUID,
    payload,
) -> SupplierItemPrice:
    sip = await db.get(SupplierItemPrice, sip_id)
    if not sip:
        raise ValueError(f"SupplierItemPrice {sip_id} not found")
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(sip, field, val)
    await db.flush()
    return sip


async def delete_supplier_price(db: AsyncSession, sip_id: UUID) -> None:
    sip = await db.get(SupplierItemPrice, sip_id)
    if not sip:
        raise ValueError(f"SupplierItemPrice {sip_id} not found")
    await db.delete(sip)
    await db.flush()


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession, run_id: UUID) -> Dict[str, int]:
    """Run all 3 AI procurement agents and store recommendations."""
    run = await db.get(ProcurementSuggestionRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    counts = {
        "supplier_optimizer": await _run_supplier_optimizer(db, run),
        "demand_risk_predictor": await _run_demand_risk_predictor(db, run),
        "cost_optimizer": await _run_cost_optimizer(db, run),
    }
    await db.flush()
    return counts


async def _run_supplier_optimizer(db: AsyncSession, run: ProcurementSuggestionRun) -> int:
    """Identify items where alternative supplier offers better value."""
    lines_q = (
        select(ProcurementSuggestionLine)
        .options(
            selectinload(ProcurementSuggestionLine.material),
            selectinload(ProcurementSuggestionLine.supplier),
        )
        .where(
            ProcurementSuggestionLine.run_id == run.id,
            ProcurementSuggestionLine.alternative_supplier_ids != None,
        )
    )
    lines = list((await db.execute(lines_q)).scalars().all())
    count = 0

    for line in lines:
        alt_ids = line.alternative_supplier_ids or []
        if not alt_ids:
            continue

        # Find cheapest alternative
        alt_sips_q = (
            select(SupplierItemPrice)
            .options(selectinload(SupplierItemPrice.supplier))
            .where(
                SupplierItemPrice.material_id == line.material_id,
                SupplierItemPrice.is_active == True,
            )
        )
        all_sips = list((await db.execute(alt_sips_q)).scalars().all())
        if len(all_sips) < 2:
            continue

        cheapest = min(all_sips, key=lambda s: float(s.unit_price))
        current  = next((s for s in all_sips if s.supplier_id == line.supplier_id), None)

        if current and _D(cheapest.unit_price) < _D(current.unit_price) * Decimal("0.95"):
            saving = (_D(current.unit_price) - _D(cheapest.unit_price)) * _D(line.adjusted_order_qty)
            rec = PSAIRecommendation(
                run_id=run.id,
                agent_type=PSAIAgentType.SUPPLIER_OPTIMIZER,
                material_id=line.material_id,
                supplier_id=cheapest.supplier_id,
                title=f"Cheaper supplier available for {line.material.name if line.material else 'material'}",
                recommendation=(
                    f"Switch from {line.supplier.name if line.supplier else 'current supplier'} "
                    f"to {cheapest.supplier.name} for {line.material.name if line.material else ''}. "
                    f"Unit price: {cheapest.unit_price} {cheapest.currency} vs current {current.unit_price} {current.currency}."
                ),
                rationale="Price difference exceeds 5% threshold. Consider switching if lead time acceptable.",
                potential_saving=_R(saving, 4),
                priority=2 if saving > 10000 else 4,
            )
            db.add(rec)
            count += 1

    return count


async def _run_demand_risk_predictor(db: AsyncSession, run: ProcurementSuggestionRun) -> int:
    """Flag materials with critical urgency and no supplier."""
    lines_q = (
        select(ProcurementSuggestionLine)
        .options(selectinload(ProcurementSuggestionLine.material))
        .where(
            ProcurementSuggestionLine.run_id == run.id,
            ProcurementSuggestionLine.urgency_level == PSUrgencyLevel.CRITICAL,
        )
    )
    lines = list((await db.execute(lines_q)).scalars().all())
    count = 0

    for line in lines:
        rec = PSAIRecommendation(
            run_id=run.id,
            agent_type=PSAIAgentType.DEMAND_RISK_PREDICTOR,
            material_id=line.material_id,
            supplier_id=line.supplier_id,
            title=f"CRITICAL shortage risk: {line.material.name if line.material else 'material'}",
            recommendation=(
                f"Material {line.material.code if line.material else ''} has CRITICAL urgency. "
                f"Shortage: {line.shortage_qty} {line.uom}. "
                f"Required date: {line.required_date}. "
                f"Suggested order date: {line.suggested_order_date} — order IMMEDIATELY."
            ),
            rationale="Stock will run out before replenishment arrives given current lead time.",
            potential_saving=None,
            priority=1,
        )
        db.add(rec)
        count += 1

        if not line.supplier_id:
            rec2 = PSAIRecommendation(
                run_id=run.id,
                agent_type=PSAIAgentType.DEMAND_RISK_PREDICTOR,
                material_id=line.material_id,
                supplier_id=None,
                title=f"No supplier mapped for critical material: {line.material.name if line.material else 'material'}",
                recommendation=(
                    f"Material {line.material.code if line.material else ''} is in critical shortage "
                    f"but has no active supplier price mapping. "
                    f"Add a SupplierItemPrice record immediately to enable automated ordering."
                ),
                rationale="Missing supplier mapping blocks automated procurement and increases lead time risk.",
                potential_saving=None,
                priority=1,
            )
            db.add(rec2)
            count += 1

    return count


async def _run_cost_optimizer(db: AsyncSession, run: ProcurementSuggestionRun) -> int:
    """Identify bulk purchase opportunities."""
    lines_q = (
        select(ProcurementSuggestionLine)
        .options(
            selectinload(ProcurementSuggestionLine.material),
            selectinload(ProcurementSuggestionLine.supplier),
        )
        .where(
            ProcurementSuggestionLine.run_id == run.id,
            ProcurementSuggestionLine.status != PSSuggestionStatus.REJECTED,
        )
    )
    lines = list((await db.execute(lines_q)).scalars().all())
    count = 0

    # Flag lines where order qty is < 3× MOQ (might be worth buying more now)
    for line in lines:
        if not line.moq or not line.estimated_total_cost:
            continue
        if line.adjusted_order_qty < _D(line.moq) * Decimal("3"):
            continue  # too small to optimize
        if line.urgency_level in (PSUrgencyLevel.LOW, PSUrgencyLevel.MEDIUM) and line.estimated_total_cost > Decimal("50000"):
            rec = PSAIRecommendation(
                run_id=run.id,
                agent_type=PSAIAgentType.COST_OPTIMIZER,
                material_id=line.material_id,
                supplier_id=line.supplier_id,
                title=f"Bulk purchase opportunity: {line.material.name if line.material else 'material'}",
                recommendation=(
                    f"Consider ordering a larger quantity of {line.material.name if line.material else ''} "
                    f"to lock in current pricing ({line.supplier_price} {line.currency}) before potential price increases. "
                    f"Current order: {line.adjusted_order_qty} {line.uom}."
                ),
                rationale="Bulk purchase can reduce per-unit cost and freight overhead. Review storage capacity before committing.",
                potential_saving=_R(_D(line.estimated_total_cost) * Decimal("0.05"), 4),
                priority=5,
            )
            db.add(rec)
            count += 1

    return count


# ── AI recs ───────────────────────────────────────────────────────────────────

async def list_ai_recs(db: AsyncSession, run_id: UUID) -> List[PSAIRecommendation]:
    q = (
        select(PSAIRecommendation)
        .options(
            selectinload(PSAIRecommendation.material),
            selectinload(PSAIRecommendation.supplier),
        )
        .where(PSAIRecommendation.run_id == run_id)
        .order_by(PSAIRecommendation.priority.asc())
    )
    return list((await db.execute(q)).scalars().all())


async def action_ai_rec(db: AsyncSession, rec_id: UUID, notes: Optional[str] = None) -> PSAIRecommendation:
    rec = await db.get(PSAIRecommendation, rec_id)
    if not rec:
        raise ValueError(f"AI rec {rec_id} not found")
    rec.is_actioned  = True
    rec.action_notes = notes
    await db.flush()
    return rec
