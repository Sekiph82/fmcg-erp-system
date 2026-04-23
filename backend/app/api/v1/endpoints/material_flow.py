from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.material_flow import (
    FlowType, FlowStatus, ReservationStatus, TankStatus,
    MFAIAgentType, MFAIRecStatus,
)
from app.schemas.material_flow import (
    FlowStageCreate, FlowStageOut,
    FlowTransactionCreate, FlowTransactionOut, FlowTransactionApprove,
    ReservationCreate, ReservationOut,
    ConsumptionCreate, ConsumptionOut,
    PreparedLotCreate, PreparedLotOut, PreparedLotWeigh,
    TankCreate, TankOut, TankUpdate,
    ReconciliationOut, ReconciliationApprove,
    MFAIRecOut, MFAIRecAction,
    MFDashboard, FlowHistoryFilter,
)
from app.services import material_flow_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=MFDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    data = await svc.get_dashboard(db)
    return MFDashboard(**data)


# ── Stages ────────────────────────────────────────────────────────────────────

@router.post("/stages", response_model=FlowStageOut, status_code=201)
async def create_stage(data: FlowStageCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_stage(db, data)


@router.get("/stages", response_model=List[FlowStageOut])
async def list_stages(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_stages(db, active_only)


@router.get("/stages/{stage_id}", response_model=FlowStageOut)
async def get_stage(stage_id: UUID, db: AsyncSession = Depends(get_db)):
    stage = await svc.get_stage(db, stage_id)
    if not stage:
        raise HTTPException(404, "Stage not found")
    return stage


# ── Flow Transactions ─────────────────────────────────────────────────────────

@router.post("/transactions", response_model=FlowTransactionOut, status_code=201)
async def create_transaction(
    data: FlowTransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_flow_transaction(db, data)


@router.get("/transactions", response_model=List[FlowTransactionOut])
async def list_transactions(
    production_order_id: Optional[UUID] = None,
    flow_type: Optional[FlowType] = None,
    status: Optional[FlowStatus] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_flow_transactions(db, production_order_id, flow_type, status, limit, offset)


@router.get("/transactions/{flow_id}", response_model=FlowTransactionOut)
async def get_transaction(flow_id: UUID, db: AsyncSession = Depends(get_db)):
    tx = await svc.get_flow_transaction(db, flow_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.post("/transactions/{flow_id}/confirm", response_model=FlowTransactionOut)
async def confirm_transaction(
    flow_id: UUID,
    body: FlowTransactionApprove = FlowTransactionApprove(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.confirm_flow_transaction(db, flow_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/transactions/{flow_id}/reverse", response_model=FlowTransactionOut)
async def reverse_transaction(flow_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.reverse_flow_transaction(db, flow_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Reservations ──────────────────────────────────────────────────────────────

@router.post("/reservations", response_model=ReservationOut, status_code=201)
async def create_reservation(data: ReservationCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_reservation(db, data)


@router.get("/reservations", response_model=List[ReservationOut])
async def list_reservations(
    production_order_id: Optional[UUID] = None,
    status: Optional[ReservationStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_reservations(db, production_order_id, status, limit)


@router.get("/reservations/{res_id}", response_model=ReservationOut)
async def get_reservation(res_id: UUID, db: AsyncSession = Depends(get_db)):
    res = await svc.get_reservation(db, res_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    return res


@router.post("/reservations/{res_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(res_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.cancel_reservation(db, res_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Issues (shortcut: POST a RAW_ISSUE / PKG_ISSUE transaction) ───────────────

@router.post("/issues", response_model=FlowTransactionOut, status_code=201)
async def issue_materials(data: FlowTransactionCreate, db: AsyncSession = Depends(get_db)):
    if data.flow_type not in (
        FlowType.RAW_ISSUE, FlowType.PKG_ISSUE, FlowType.CONSUMABLE_ISSUE
    ):
        raise HTTPException(400, "Only issue flow types allowed on this endpoint")
    return await svc.create_flow_transaction(db, data)


# ── Consumptions ──────────────────────────────────────────────────────────────

@router.post("/consumptions", response_model=ConsumptionOut, status_code=201)
async def record_consumption(data: ConsumptionCreate, db: AsyncSession = Depends(get_db)):
    return await svc.record_consumption(db, data)


@router.get("/consumptions/{order_id}", response_model=List[ConsumptionOut])
async def list_consumptions(order_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_consumptions(db, order_id)


# ── Returns ───────────────────────────────────────────────────────────────────

@router.post("/returns", response_model=FlowTransactionOut, status_code=201)
async def return_materials(data: FlowTransactionCreate, db: AsyncSession = Depends(get_db)):
    if data.flow_type not in (FlowType.RETURN, FlowType.REVERSAL):
        raise HTTPException(400, "Only RETURN or REVERSAL flow types allowed on this endpoint")
    return await svc.create_flow_transaction(db, data)


# ── Transfers ─────────────────────────────────────────────────────────────────

@router.post("/transfers", response_model=FlowTransactionOut, status_code=201)
async def transfer_materials(data: FlowTransactionCreate, db: AsyncSession = Depends(get_db)):
    if data.flow_type not in (
        FlowType.STAGE_TRANSFER, FlowType.BULK_TRANSFER, FlowType.TANK_TRANSFER,
        FlowType.LINE_TRANSFER, FlowType.WEIGHING_TRANSFER, FlowType.INTERMEDIATE_CREATE,
    ):
        raise HTTPException(400, "Only transfer flow types allowed on this endpoint")
    return await svc.create_flow_transaction(db, data)


# ── FG Receipts ───────────────────────────────────────────────────────────────

@router.post("/fg-receipts", response_model=FlowTransactionOut, status_code=201)
async def fg_receipt(data: FlowTransactionCreate, db: AsyncSession = Depends(get_db)):
    if data.flow_type != FlowType.FG_RECEIPT:
        raise HTTPException(400, "Only FG_RECEIPT flow type allowed on this endpoint")
    return await svc.create_flow_transaction(db, data)


# ── Prepared Lots ─────────────────────────────────────────────────────────────

@router.post("/prepared-lots", response_model=PreparedLotOut, status_code=201)
async def create_prepared_lot(data: PreparedLotCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_prepared_lot(db, data)


@router.get("/prepared-lots", response_model=List[PreparedLotOut])
async def list_prepared_lots(
    production_order_id: Optional[UUID] = None,
    consumed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_prepared_lots(db, production_order_id, consumed)


@router.post("/prepared-lots/{lot_id}/weigh", response_model=PreparedLotOut)
async def record_weigh(lot_id: UUID, data: PreparedLotWeigh, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.record_weigh(db, lot_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Tank Occupancy ────────────────────────────────────────────────────────────

@router.post("/tanks", response_model=TankOut, status_code=201)
async def create_tank(data: TankCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_tank(db, data)


@router.get("/tanks", response_model=List[TankOut])
async def list_tanks(
    stage_id: Optional[UUID] = None,
    status: Optional[TankStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    tanks = await svc.list_tanks(db, stage_id, status)
    result = []
    for t in tanks:
        d = TankOut.model_validate(t)
        if t.capacity_max and t.capacity_max > 0:
            d.fill_pct = (t.quantity_current / t.capacity_max * 100).quantize(__import__("decimal").Decimal("0.1"))
        if t.product:
            d.product_name = t.product.name if hasattr(t.product, "name") else None
        if t.material:
            d.material_name = t.material.name if hasattr(t.material, "name") else None
        result.append(d)
    return result


@router.get("/tanks/{tank_id}", response_model=TankOut)
async def get_tank(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    tank = await svc.get_tank(db, tank_id)
    if not tank:
        raise HTTPException(404, "Tank not found")
    return tank


@router.patch("/tanks/{tank_id}", response_model=TankOut)
async def update_tank(tank_id: UUID, data: TankUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_tank(db, tank_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Reconciliation ────────────────────────────────────────────────────────────

@router.get("/reconciliation/{order_id}", response_model=ReconciliationOut)
async def get_reconciliation(order_id: UUID, db: AsyncSession = Depends(get_db)):
    rec = await svc.compute_reconciliation(db, order_id)
    return rec


@router.post("/reconciliation/{order_id}/close", response_model=ReconciliationOut)
async def close_reconciliation(
    order_id: UUID,
    data: ReconciliationApprove = ReconciliationApprove(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.close_reconciliation(db, order_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Flow History ──────────────────────────────────────────────────────────────

@router.get("/history", response_model=List[FlowTransactionOut])
async def get_history(
    production_order_id: Optional[UUID] = None,
    flow_type: Optional[FlowType] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    f = FlowHistoryFilter(
        production_order_id=production_order_id,
        flow_type=flow_type,
    )
    return await svc.get_flow_history(db, f, limit, offset)


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[MFAIRecOut])
async def run_ai(
    production_order_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.run_ai_agents(db, production_order_id)


@router.get("/ai/recommendations", response_model=List[MFAIRecOut])
async def list_ai_recs(
    agent_type: Optional[MFAIAgentType] = None,
    status: Optional[MFAIRecStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type, status, limit)


@router.post("/ai/recommendations/{rec_id}/action", response_model=MFAIRecOut)
async def action_ai_rec(rec_id: UUID, data: MFAIRecAction, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.action_ai_rec(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
