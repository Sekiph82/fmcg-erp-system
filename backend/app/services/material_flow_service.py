from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.material_flow import (
    MaterialFlowTransaction, MaterialFlowLine, MaterialReservation,
    MaterialReservationLine, ProductionConsumption, PreparedLot,
    TankOccupancy, BatchReconciliation, BatchReconciliationLine,
    FlowStage, MFAIRecommendation,
    FlowStatus, FlowType, QualityStatus, ReservationStatus,
    TankStatus, ReconciliationStatus, MFAIAgentType, MFAIRecStatus,
)
from app.models.inventory import Stock
from app.schemas.material_flow import (
    FlowTransactionCreate, FlowStageCreate, ReservationCreate,
    ConsumptionCreate, PreparedLotCreate, PreparedLotWeigh,
    TankCreate, TankUpdate, ReconciliationApprove, MFAIRecAction,
    FlowHistoryFilter, MFDashboard,
)

_D = Decimal


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _flow_no() -> str:
    return f"MF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


def _res_no() -> str:
    return f"RES-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


def _recon_no() -> str:
    return f"REC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


def _prep_lot_no() -> str:
    return f"PL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"


# ── Stage CRUD ────────────────────────────────────────────────────────────────

async def create_stage(db: AsyncSession, data: FlowStageCreate) -> FlowStage:
    stage = FlowStage(**data.model_dump())
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage


async def list_stages(db: AsyncSession, active_only: bool = True) -> List[FlowStage]:
    q = select(FlowStage)
    if active_only:
        q = q.where(FlowStage.active_flag == True)
    q = q.order_by(FlowStage.sequence_no)
    result = await db.execute(q)
    return result.scalars().all()


async def get_stage(db: AsyncSession, stage_id: UUID) -> Optional[FlowStage]:
    result = await db.execute(select(FlowStage).where(FlowStage.id == stage_id))
    return result.scalar_one_or_none()


# ── Flow Transaction ──────────────────────────────────────────────────────────

async def create_flow_transaction(
    db: AsyncSession, data: FlowTransactionCreate, created_by: Optional[UUID] = None
) -> MaterialFlowTransaction:
    tx = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=data.flow_type,
        flow_mode=data.flow_mode,
        status=FlowStatus.DRAFT,
        production_order_id=data.production_order_id,
        work_order_id=data.work_order_id,
        source_document_type=data.source_document_type,
        source_document_id=data.source_document_id,
        transaction_datetime=data.transaction_datetime or _now(),
        plant_id=data.plant_id,
        created_by=created_by,
        notes=data.notes,
    )
    db.add(tx)
    await db.flush()
    for ln in data.lines:
        line = MaterialFlowLine(transaction_id=tx.id, **ln.model_dump())
        db.add(line)
    await db.commit()
    await db.refresh(tx)
    return tx


async def get_flow_transaction(db: AsyncSession, flow_id: UUID) -> Optional[MaterialFlowTransaction]:
    result = await db.execute(
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .where(MaterialFlowTransaction.id == flow_id)
    )
    return result.scalar_one_or_none()


async def list_flow_transactions(
    db: AsyncSession,
    production_order_id: Optional[UUID] = None,
    flow_type: Optional[FlowType] = None,
    status: Optional[FlowStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[MaterialFlowTransaction]:
    q = (
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .order_by(MaterialFlowTransaction.transaction_datetime.desc())
    )
    if production_order_id:
        q = q.where(MaterialFlowTransaction.production_order_id == production_order_id)
    if flow_type:
        q = q.where(MaterialFlowTransaction.flow_type == flow_type)
    if status:
        q = q.where(MaterialFlowTransaction.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


async def confirm_flow_transaction(
    db: AsyncSession, flow_id: UUID, approved_by: Optional[UUID] = None
) -> MaterialFlowTransaction:
    tx = await get_flow_transaction(db, flow_id)
    if not tx:
        raise ValueError("Flow transaction not found")
    if tx.status not in (FlowStatus.DRAFT, FlowStatus.PENDING):
        raise ValueError(f"Cannot confirm transaction in status {tx.status}")
    tx.status = FlowStatus.POSTED
    tx.approved_by = approved_by
    await db.commit()
    await db.refresh(tx)
    return tx


async def reverse_flow_transaction(
    db: AsyncSession, flow_id: UUID, created_by: Optional[UUID] = None
) -> MaterialFlowTransaction:
    original = await get_flow_transaction(db, flow_id)
    if not original:
        raise ValueError("Flow transaction not found")
    if original.status != FlowStatus.POSTED:
        raise ValueError("Only POSTED transactions can be reversed")

    reversal = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=original.flow_type,
        flow_mode=original.flow_mode,
        status=FlowStatus.POSTED,
        production_order_id=original.production_order_id,
        source_document_type="REVERSAL",
        source_document_id=original.id,
        transaction_datetime=_now(),
        plant_id=original.plant_id,
        created_by=created_by,
        notes=f"Reversal of {original.flow_no}",
    )
    db.add(reversal)
    await db.flush()

    for ln in original.lines:
        rev_line = MaterialFlowLine(
            transaction_id=reversal.id,
            line_no=ln.line_no,
            item_type=ln.item_type,
            material_id=ln.material_id,
            product_id=ln.product_id,
            lot_id=ln.lot_id,
            batch_id=ln.batch_id,
            quantity=ln.quantity,
            uom=ln.uom,
            source_warehouse_id=ln.destination_warehouse_id,
            source_location_id=ln.destination_location_id,
            source_stage_id=ln.destination_stage_id,
            destination_warehouse_id=ln.source_warehouse_id,
            destination_location_id=ln.source_location_id,
            destination_stage_id=ln.source_stage_id,
            quality_status=ln.quality_status,
            movement_reason=ln.movement_reason,
            return_flag=True,
            reference_line_id=ln.id,
        )
        db.add(rev_line)

    original.status = FlowStatus.REVERSED
    await db.commit()
    await db.refresh(reversal)
    return reversal


# ── Reservation ───────────────────────────────────────────────────────────────

async def create_reservation(
    db: AsyncSession, data: ReservationCreate, created_by: Optional[UUID] = None
) -> MaterialReservation:
    res = MaterialReservation(
        reservation_no=_res_no(),
        production_order_id=data.production_order_id,
        work_order_id=data.work_order_id,
        status=ReservationStatus.ACTIVE,
        expiry_datetime=data.expiry_datetime,
        created_by=created_by,
        notes=data.notes,
    )
    db.add(res)
    await db.flush()
    for ln in data.lines:
        line = MaterialReservationLine(reservation_id=res.id, **ln.model_dump())
        db.add(line)
    await db.commit()
    await db.refresh(res)
    return res


async def get_reservation(db: AsyncSession, res_id: UUID) -> Optional[MaterialReservation]:
    result = await db.execute(
        select(MaterialReservation)
        .options(selectinload(MaterialReservation.lines))
        .where(MaterialReservation.id == res_id)
    )
    return result.scalar_one_or_none()


async def list_reservations(
    db: AsyncSession,
    production_order_id: Optional[UUID] = None,
    status: Optional[ReservationStatus] = None,
    limit: int = 50,
) -> List[MaterialReservation]:
    q = (
        select(MaterialReservation)
        .options(selectinload(MaterialReservation.lines))
        .order_by(MaterialReservation.created_at.desc())
    )
    if production_order_id:
        q = q.where(MaterialReservation.production_order_id == production_order_id)
    if status:
        q = q.where(MaterialReservation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def cancel_reservation(db: AsyncSession, res_id: UUID) -> MaterialReservation:
    res = await get_reservation(db, res_id)
    if not res:
        raise ValueError("Reservation not found")
    res.status = ReservationStatus.CANCELLED
    await db.commit()
    await db.refresh(res)
    return res


# ── Consumption ───────────────────────────────────────────────────────────────

async def record_consumption(
    db: AsyncSession, data: ConsumptionCreate, operator_id: Optional[UUID] = None
) -> ProductionConsumption:
    issued = await _get_total_issued(db, data.production_order_id, data.material_id, data.product_id)
    consumed_so_far = await _get_total_consumed(db, data.production_order_id, data.material_id, data.product_id)
    variance = issued - consumed_so_far - data.quantity_consumed - data.quantity_returned - data.quantity_scrapped

    consumption = ProductionConsumption(
        production_order_id=data.production_order_id,
        work_order_id=data.work_order_id,
        item_type=data.item_type,
        material_id=data.material_id,
        product_id=data.product_id,
        lot_id=data.lot_id,
        quantity_issued=issued,
        quantity_consumed=data.quantity_consumed,
        quantity_returned=data.quantity_returned,
        quantity_scrapped=data.quantity_scrapped,
        quantity_variance=variance,
        uom=data.uom,
        stage_id=data.stage_id,
        consumed_at=_now(),
        operator_id=operator_id,
        notes=data.notes,
    )
    db.add(consumption)
    await db.commit()
    await db.refresh(consumption)
    return consumption


async def _get_total_issued(
    db: AsyncSession, order_id: UUID,
    material_id: Optional[UUID], product_id: Optional[UUID]
) -> Decimal:
    q = (
        select(func.coalesce(func.sum(MaterialFlowLine.quantity), 0))
        .join(MaterialFlowTransaction, MaterialFlowLine.transaction_id == MaterialFlowTransaction.id)
        .where(
            MaterialFlowTransaction.production_order_id == order_id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
            MaterialFlowLine.issue_flag == True,
        )
    )
    if material_id:
        q = q.where(MaterialFlowLine.material_id == material_id)
    if product_id:
        q = q.where(MaterialFlowLine.product_id == product_id)
    result = await db.execute(q)
    return _D(str(result.scalar() or 0))


async def _get_total_consumed(
    db: AsyncSession, order_id: UUID,
    material_id: Optional[UUID], product_id: Optional[UUID]
) -> Decimal:
    q = select(func.coalesce(func.sum(ProductionConsumption.quantity_consumed), 0)).where(
        ProductionConsumption.production_order_id == order_id
    )
    if material_id:
        q = q.where(ProductionConsumption.material_id == material_id)
    if product_id:
        q = q.where(ProductionConsumption.product_id == product_id)
    result = await db.execute(q)
    return _D(str(result.scalar() or 0))


async def list_consumptions(
    db: AsyncSession, production_order_id: UUID
) -> List[ProductionConsumption]:
    result = await db.execute(
        select(ProductionConsumption)
        .where(ProductionConsumption.production_order_id == production_order_id)
        .order_by(ProductionConsumption.consumed_at.desc())
    )
    return result.scalars().all()


# ── Prepared Lots ─────────────────────────────────────────────────────────────

async def create_prepared_lot(db: AsyncSession, data: PreparedLotCreate) -> PreparedLot:
    pl = PreparedLot(
        prepared_lot_no=_prep_lot_no(),
        **data.model_dump(),
    )
    db.add(pl)
    await db.commit()
    await db.refresh(pl)
    return pl


async def record_weigh(
    db: AsyncSession, lot_id: UUID, data: PreparedLotWeigh
) -> PreparedLot:
    result = await db.execute(select(PreparedLot).where(PreparedLot.id == lot_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise ValueError("Prepared lot not found")
    pl.actual_quantity = data.actual_quantity
    pl.weighed_at = _now()
    if data.operator_id:
        pl.operator_id = data.operator_id
    if pl.tolerance_pct and pl.target_quantity:
        tol = pl.target_quantity * pl.tolerance_pct / _D("100")
        pl.over_weigh = data.actual_quantity > pl.target_quantity + tol
        pl.under_weigh = data.actual_quantity < pl.target_quantity - tol
    if data.notes:
        pl.notes = data.notes
    await db.commit()
    await db.refresh(pl)
    return pl


async def list_prepared_lots(
    db: AsyncSession,
    production_order_id: Optional[UUID] = None,
    consumed: Optional[bool] = None,
) -> List[PreparedLot]:
    q = select(PreparedLot).order_by(PreparedLot.created_at.desc())
    if production_order_id:
        q = q.where(PreparedLot.production_order_id == production_order_id)
    if consumed is not None:
        q = q.where(PreparedLot.consumed == consumed)
    result = await db.execute(q)
    return result.scalars().all()


# ── Tank Occupancy ────────────────────────────────────────────────────────────

async def create_tank(db: AsyncSession, data: TankCreate) -> TankOccupancy:
    tank = TankOccupancy(**data.model_dump())
    db.add(tank)
    await db.commit()
    await db.refresh(tank)
    return tank


async def get_tank(db: AsyncSession, tank_id: UUID) -> Optional[TankOccupancy]:
    result = await db.execute(select(TankOccupancy).where(TankOccupancy.id == tank_id))
    return result.scalar_one_or_none()


async def list_tanks(
    db: AsyncSession,
    stage_id: Optional[UUID] = None,
    status: Optional[TankStatus] = None,
) -> List[TankOccupancy]:
    q = select(TankOccupancy).order_by(TankOccupancy.tank_code)
    if stage_id:
        q = q.where(TankOccupancy.stage_id == stage_id)
    if status:
        q = q.where(TankOccupancy.tank_status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def update_tank(
    db: AsyncSession, tank_id: UUID, data: TankUpdate
) -> TankOccupancy:
    tank = await get_tank(db, tank_id)
    if not tank:
        raise ValueError("Tank not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(tank, k, v)
    if data.quantity_current is not None and tank.quantity_current > 0:
        tank.tank_status = TankStatus.IN_USE
    elif data.quantity_current == _D("0"):
        tank.tank_status = TankStatus.EMPTY
    await db.commit()
    await db.refresh(tank)
    return tank


# ── Batch Reconciliation ──────────────────────────────────────────────────────

async def compute_reconciliation(
    db: AsyncSession, production_order_id: UUID
) -> BatchReconciliation:
    existing = await db.execute(
        select(BatchReconciliation).where(
            BatchReconciliation.production_order_id == production_order_id,
            BatchReconciliation.status.notin_([ReconciliationStatus.CLOSED]),
        )
    )
    rec = existing.scalar_one_or_none()
    if not rec:
        rec = BatchReconciliation(
            reconciliation_no=_recon_no(),
            production_order_id=production_order_id,
            status=ReconciliationStatus.OPEN,
        )
        db.add(rec)
        await db.flush()

    consumptions = await list_consumptions(db, production_order_id)

    total_issued = sum(_D(str(c.quantity_issued)) for c in consumptions)
    total_consumed = sum(_D(str(c.quantity_consumed)) for c in consumptions)
    total_returned = sum(_D(str(c.quantity_returned)) for c in consumptions)
    total_scrapped = sum(_D(str(c.quantity_scrapped)) for c in consumptions)
    total_variance = total_issued - total_consumed - total_returned - total_scrapped

    rec.total_issued = total_issued
    rec.total_consumed = total_consumed
    rec.total_returned = total_returned
    rec.total_scrapped = total_scrapped
    rec.total_variance = total_variance
    rec.variance_pct = (
        (total_variance / total_issued * _D("100")).quantize(_D("0.001"))
        if total_issued > 0 else None
    )

    await db.commit()
    await db.refresh(rec)
    return rec


async def get_reconciliation(
    db: AsyncSession, production_order_id: UUID
) -> Optional[BatchReconciliation]:
    result = await db.execute(
        select(BatchReconciliation)
        .options(selectinload(BatchReconciliation.lines))
        .where(BatchReconciliation.production_order_id == production_order_id)
        .order_by(BatchReconciliation.created_at.desc())
    )
    return result.scalars().first()


async def close_reconciliation(
    db: AsyncSession, production_order_id: UUID, data: ReconciliationApprove,
    approved_by: Optional[UUID] = None,
) -> BatchReconciliation:
    rec = await get_reconciliation(db, production_order_id)
    if not rec:
        rec = await compute_reconciliation(db, production_order_id)
    if rec.status == ReconciliationStatus.CLOSED:
        raise ValueError("Reconciliation already closed")
    rec.status = ReconciliationStatus.CLOSED
    rec.variance_reason = data.variance_reason
    rec.approved_by = approved_by
    rec.approved_at = _now()
    rec.closed_at = _now()
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Flow History ──────────────────────────────────────────────────────────────

async def get_flow_history(
    db: AsyncSession, f: FlowHistoryFilter, limit: int = 100, offset: int = 0
) -> List[MaterialFlowTransaction]:
    q = (
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .order_by(MaterialFlowTransaction.transaction_datetime.desc())
    )
    if f.production_order_id:
        q = q.where(MaterialFlowTransaction.production_order_id == f.production_order_id)
    if f.flow_type:
        q = q.where(MaterialFlowTransaction.flow_type == f.flow_type)
    if f.date_from:
        q = q.where(MaterialFlowTransaction.transaction_datetime >= f.date_from)
    if f.date_to:
        q = q.where(MaterialFlowTransaction.transaction_datetime <= f.date_to)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    flows_today = await db.execute(
        select(func.count(MaterialFlowTransaction.id)).where(
            MaterialFlowTransaction.transaction_datetime >= today
        )
    )
    issued_today = await db.execute(
        select(func.coalesce(func.sum(MaterialFlowLine.quantity), 0))
        .join(MaterialFlowTransaction, MaterialFlowLine.transaction_id == MaterialFlowTransaction.id)
        .where(
            MaterialFlowTransaction.transaction_datetime >= today,
            MaterialFlowLine.issue_flag == True,
        )
    )
    active_res = await db.execute(
        select(func.count(MaterialReservation.id)).where(
            MaterialReservation.status == ReservationStatus.ACTIVE
        )
    )
    open_recon = await db.execute(
        select(func.count(BatchReconciliation.id)).where(
            BatchReconciliation.status.notin_([ReconciliationStatus.CLOSED])
        )
    )
    tanks_in_use = await db.execute(
        select(func.count(TankOccupancy.id)).where(
            TankOccupancy.tank_status == TankStatus.IN_USE
        )
    )
    tanks_qc = await db.execute(
        select(func.count(TankOccupancy.id)).where(
            TankOccupancy.tank_status == TankStatus.QC_HOLD
        )
    )
    pending_ai = await db.execute(
        select(func.count(MFAIRecommendation.id)).where(
            MFAIRecommendation.status == MFAIRecStatus.PENDING
        )
    )

    recent_flows_result = await db.execute(
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .order_by(MaterialFlowTransaction.transaction_datetime.desc())
        .limit(10)
    )
    ai_recs_result = await db.execute(
        select(MFAIRecommendation)
        .where(MFAIRecommendation.status == MFAIRecStatus.PENDING)
        .order_by(MFAIRecommendation.created_at.desc())
        .limit(5)
    )

    return {
        "total_flows_today": flows_today.scalar() or 0,
        "total_issued_today": _D(str(issued_today.scalar() or 0)),
        "active_reservations": active_res.scalar() or 0,
        "open_reconciliations": open_recon.scalar() or 0,
        "tanks_in_use": tanks_in_use.scalar() or 0,
        "tanks_qc_hold": tanks_qc.scalar() or 0,
        "pending_ai_recs": pending_ai.scalar() or 0,
        "total_wip_quantity": _D("0"),
        "recent_flows": recent_flows_result.scalars().all(),
        "ai_recommendations": ai_recs_result.scalars().all(),
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(
    db: AsyncSession, production_order_id: Optional[UUID] = None
) -> List[MFAIRecommendation]:
    recs: List[MFAIRecommendation] = []

    # Agent 1: Variance Analyzer
    consumptions = []
    if production_order_id:
        consumptions = await list_consumptions(db, production_order_id)

    high_variance = [c for c in consumptions if c.quantity_variance and abs(c.quantity_variance) > 0]
    if high_variance:
        for c in high_variance[:3]:
            r = MFAIRecommendation(
                agent_type=MFAIAgentType.VARIANCE_ANALYZER,
                status=MFAIRecStatus.PENDING,
                production_order_id=production_order_id,
                title="Abnormal material variance detected",
                description=(
                    f"Material variance of {c.quantity_variance} {c.uom} detected. "
                    f"Issued: {c.quantity_issued}, Consumed: {c.quantity_consumed}. "
                    "Investigate potential measurement or process loss."
                ),
                severity="high",
                confidence_score=_D("82"),
                estimated_impact="Material cost overrun or unreported loss",
            )
            db.add(r)
            recs.append(r)

    # Agent 2: Flow Optimizer
    tanks = await list_tanks(db)
    over_reserved = [t for t in tanks if t.quantity_reserved > t.quantity_current * _D("0.9")]
    if over_reserved:
        r = MFAIRecommendation(
            agent_type=MFAIAgentType.FLOW_OPTIMIZER,
            status=MFAIRecStatus.PENDING,
            production_order_id=production_order_id,
            title="Over-reserved tank capacity detected",
            description=(
                f"{len(over_reserved)} tank(s) have reservations exceeding 90% of current stock. "
                "Consider releasing unused reservations or reallocating buffer."
            ),
            severity="medium",
            confidence_score=_D("74"),
            estimated_impact="Reduced tank availability for incoming bulk",
        )
        db.add(r)
        recs.append(r)

    # Agent 3: Risk Monitor
    qc_hold_tanks = [t for t in tanks if t.tank_status == TankStatus.QC_HOLD]
    if qc_hold_tanks:
        r = MFAIRecommendation(
            agent_type=MFAIAgentType.RISK_MONITOR,
            status=MFAIRecStatus.PENDING,
            production_order_id=None,
            title=f"{len(qc_hold_tanks)} tank(s) on QC hold",
            description=(
                f"Tanks on QC hold: {', '.join(t.tank_code for t in qc_hold_tanks[:5])}. "
                "Blocked bulk may delay downstream filling operations."
            ),
            severity="high",
            confidence_score=_D("91"),
            estimated_impact="Filling line stoppage or schedule delay",
        )
        db.add(r)
        recs.append(r)

    if recs:
        await db.commit()
    return recs


async def action_ai_rec(
    db: AsyncSession, rec_id: UUID, data: MFAIRecAction, actioned_by: Optional[UUID] = None
) -> MFAIRecommendation:
    result = await db.execute(select(MFAIRecommendation).where(MFAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError("AI recommendation not found")
    rec.status = data.status
    rec.actioned_by = actioned_by
    rec.actioned_at = _now()
    rec.action_notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_ai_recs(
    db: AsyncSession,
    agent_type: Optional[MFAIAgentType] = None,
    status: Optional[MFAIRecStatus] = None,
    limit: int = 50,
) -> List[MFAIRecommendation]:
    q = select(MFAIRecommendation).order_by(MFAIRecommendation.created_at.desc())
    if agent_type:
        q = q.where(MFAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(MFAIRecommendation.status == status)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
