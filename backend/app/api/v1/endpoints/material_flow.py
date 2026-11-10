from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import can_modify_scope, can_view_scope, forbidden_detail
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.material_flow import (
    FlowType, FlowStatus, ReservationStatus, TankStatus,
    MFAIAgentType, MFAIRecStatus,
)
from app.models.production import ProductionOrder
from app.schemas.material_flow import (
    FlowStageCreate, FlowStageOut,
    FlowTransactionCreate, FlowTransactionOut, FlowTransactionApprove,
    MaterialIssueCreate, MaterialReturnCreate, MaterialScrapCreate,
    WIPOutputCreate, WIPTransferCreate, WIPBulkTransferCreate, WIPBalanceOut,
    ReservationCreate, ReservationOut, MaterialPickListOut,
    ConsumptionCreate, ConsumptionOut,
    PreparedLotCreate, PreparedLotOut, PreparedLotWeigh,
    TankCreate, TankOut, TankUpdate,
    ReconciliationOut, ReconciliationApprove,
    MFAIRecOut, MFAIRecAction,
    MFDashboard, FlowHistoryFilter,
)
from app.services import material_flow_service as svc

router = APIRouter()


def _require_reservation_scope(user, order: ProductionOrder, action: str) -> None:
    warehouse_id = order.source_warehouse_id
    if warehouse_id is None or not can_modify_scope(
        user, "inventory", action, "warehouse", warehouse_id
    ):
        raise HTTPException(
            status_code=403,
            detail=forbidden_detail(
                "Material reservations require inventory access to the production source warehouse."
            ),
        )


def _can_view_reservation(user, order: ProductionOrder | None) -> bool:
    return bool(
        order
        and order.source_warehouse_id
        and can_view_scope(user, "inventory", "warehouse", order.source_warehouse_id)
    )


def _transaction_warehouse_ids(transaction) -> set[UUID]:
    warehouse_ids = {
        warehouse_id
        for line in transaction.lines
        for warehouse_id in (
            line.source_warehouse_id,
            line.destination_warehouse_id,
        )
        if warehouse_id is not None
    }
    return warehouse_ids


def _require_transaction_scope(user, warehouse_ids: set[UUID], action: str) -> None:
    if not warehouse_ids or any(
        not can_modify_scope(user, "inventory", action, "warehouse", warehouse_id)
        for warehouse_id in warehouse_ids
    ):
        raise HTTPException(
            status_code=403,
            detail=forbidden_detail("Material-flow transactions require access to every affected warehouse."),
        )


def _can_view_transaction(user, warehouse_ids: set[UUID]) -> bool:
    return bool(warehouse_ids) and all(
        can_view_scope(user, "inventory", "warehouse", warehouse_id)
        for warehouse_id in warehouse_ids
    )


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
    current_user=Depends(get_current_user),
):
    if data.flow_type in {
        FlowType.STAGE_TRANSFER,
        FlowType.INTERMEDIATE_CREATE,
        FlowType.BULK_TRANSFER,
        FlowType.TANK_TRANSFER,
        FlowType.LINE_TRANSFER,
        FlowType.WEIGHING_TRANSFER,
    }:
        raise HTTPException(
            status_code=409,
            detail="Transfer flows must use the authenticated transfer or WIP workflow.",
        )
    if data.flow_type == FlowType.FG_RECEIPT:
        raise HTTPException(
            status_code=409,
            detail="Finished goods must be received by completing the authenticated production order so WIP, stock, lot, and genealogy post atomically.",
        )
    if data.flow_type == FlowType.REVERSAL:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "INVENTORY_AWARE_REVERSAL_REQUIRED",
                "message": "Generic reversal drafts cannot be posted. Use an available linked correction workflow; unsupported stock, WIP, and finished-goods corrections remain blocked.",
            },
        )
    if data.flow_type == FlowType.RAW_ISSUE:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "RAW_ISSUE_REQUIRES_RESERVATION",
                "message": "Production material must be issued through POST /reservations/{reservation_id}/issue so stock, reservation, and movement records remain atomic.",
            },
        )
    if data.flow_type == FlowType.PKG_ISSUE:
        raise HTTPException(
            status_code=409,
            detail="Packaging must be issued from an exact production reservation through the packaging-issue workflow.",
        )
    if data.flow_type == FlowType.RETURN and any(
        line.item_type.strip().lower() == "material" for line in data.lines
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_REQUIRES_ISSUE_LINE",
                "message": "Unused production material must be returned through POST /issue-lines/{issue_line_id}/returns so stock, consumption, and movement history remain atomic.",
            },
        )
    if data.flow_type == FlowType.SCRAP and any(
        line.item_type.strip().lower() == "material" for line in data.lines
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_SCRAP_REQUIRES_ISSUE_LINE",
                "message": "Production material scrap must be posted through POST /issue-lines/{issue_line_id}/scrap so outstanding quantity and event history remain atomic.",
            },
        )
    warehouse_ids = {
        warehouse_id
        for line in data.lines
        for warehouse_id in (line.source_warehouse_id, line.destination_warehouse_id)
        if warehouse_id is not None
    }
    if data.production_order_id is not None:
        order = await db.get(ProductionOrder, data.production_order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Production order not found")
        if order.source_warehouse_id is not None:
            warehouse_ids.add(order.source_warehouse_id)
    _require_transaction_scope(current_user, warehouse_ids, "edit")
    return await svc.create_flow_transaction(db, data, current_user.id)


@router.get("/transactions", response_model=List[FlowTransactionOut])
async def list_transactions(
    production_order_id: Optional[UUID] = None,
    flow_type: Optional[FlowType] = None,
    status: Optional[FlowStatus] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    transactions = await svc.list_flow_transactions(
        db, production_order_id, flow_type, status, limit, offset
    )
    visible = []
    for transaction in transactions:
        warehouse_ids = _transaction_warehouse_ids(transaction)
        if transaction.production_order_id is not None:
            order = await db.get(ProductionOrder, transaction.production_order_id)
            if order is not None and order.source_warehouse_id is not None:
                warehouse_ids.add(order.source_warehouse_id)
        if _can_view_transaction(current_user, warehouse_ids):
            visible.append(transaction)
    return visible


@router.get("/transactions/{flow_id}", response_model=FlowTransactionOut)
async def get_transaction(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tx = await svc.get_flow_transaction(db, flow_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    warehouse_ids = _transaction_warehouse_ids(tx)
    if tx.production_order_id is not None:
        order = await db.get(ProductionOrder, tx.production_order_id)
        if order is not None and order.source_warehouse_id is not None:
            warehouse_ids.add(order.source_warehouse_id)
    if not _can_view_transaction(current_user, warehouse_ids):
        raise HTTPException(404, "Transaction not found")
    return tx


@router.post("/transactions/{flow_id}/confirm", response_model=FlowTransactionOut)
async def confirm_transaction(
    flow_id: UUID,
    body: FlowTransactionApprove = FlowTransactionApprove(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        transaction = await svc.get_flow_transaction(db, flow_id)
        if transaction is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        if transaction.flow_type == FlowType.FG_RECEIPT:
            if transaction.production_order_id is None:
                raise HTTPException(status_code=404, detail="Transaction not found")
            order = await db.get(ProductionOrder, transaction.production_order_id)
            if order is None:
                raise HTTPException(status_code=404, detail="Transaction not found")
            _require_reservation_scope(current_user, order, "edit")
            raise HTTPException(
                status_code=409,
                detail="Finished-goods receipts can only be posted by completing their production order.",
            )
        if transaction.flow_type in {
            FlowType.RAW_ISSUE,
            FlowType.PKG_ISSUE,
            FlowType.CONSUMABLE_ISSUE,
        }:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "ISSUE_TRANSACTION_REQUIRES_RESERVATION",
                    "message": "Issue transactions must be posted through the reservation issue workflow; a draft issue cannot be confirmed without applying inventory movements.",
                },
            )
        if transaction.flow_type in {FlowType.STAGE_TRANSFER, FlowType.INTERMEDIATE_CREATE} or (
            transaction.flow_type == FlowType.BULK_TRANSFER
            and any(line.item_type.strip().lower() == "product" for line in transaction.lines)
        ):
            raise HTTPException(
                status_code=409,
                detail="WIP output and stage movement cannot be confirmed through the generic transaction route.",
            )
        if transaction.flow_type == FlowType.RETURN and any(
            line.item_type.strip().lower() == "material" for line in transaction.lines
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_RETURN_REQUIRES_ISSUE_LINE",
                    "message": "Material return drafts must be posted through the issue-line return workflow.",
                },
            )
        if transaction.flow_type == FlowType.SCRAP and any(
            line.item_type.strip().lower() == "material" for line in transaction.lines
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_SCRAP_REQUIRES_ISSUE_LINE",
                    "message": "Material scrap drafts must be posted through the issue-line scrap workflow.",
                },
            )
        if transaction.production_order_id is None:
            raise HTTPException(status_code=409, detail="Transaction has no production-order scope")
        order = await db.get(ProductionOrder, transaction.production_order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        _require_reservation_scope(current_user, order, "edit")
        if transaction.flow_type == FlowType.REVERSAL:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "INVENTORY_AWARE_REVERSAL_REQUIRED",
                    "message": "A generic reversal cannot post the matching inventory and lineage correction events.",
                },
            )
        return await svc.confirm_flow_transaction(db, flow_id, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/transactions/{flow_id}/reverse", response_model=FlowTransactionOut)
async def reverse_transaction(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        transaction = await svc.get_flow_transaction(db, flow_id)
        if transaction is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        warehouse_ids = _transaction_warehouse_ids(transaction)
        if transaction.production_order_id is not None:
            order = await db.get(ProductionOrder, transaction.production_order_id)
            if order is not None and order.source_warehouse_id is not None:
                warehouse_ids.add(order.source_warehouse_id)
        _require_transaction_scope(current_user, warehouse_ids, "edit")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "INVENTORY_AWARE_REVERSAL_REQUIRED",
                "message": "Generic reversal does not post matching stock, reservation, WIP, genealogy, and accounting events. Use an available linked correction workflow; unsupported corrections remain blocked.",
            },
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Reservations ──────────────────────────────────────────────────────────────

@router.post("/reservations", response_model=ReservationOut, status_code=201)
async def create_reservation(
    data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, data.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "create")
    reservation = await svc.create_reservation(db, data, current_user.id)
    await db.commit()
    return reservation


@router.get("/reservations", response_model=List[ReservationOut])
async def list_reservations(
    production_order_id: Optional[UUID] = None,
    status: Optional[ReservationStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reservations = await svc.list_reservations(db, production_order_id, status, limit)
    visible = []
    for reservation in reservations:
        order = await db.get(ProductionOrder, reservation.production_order_id)
        if _can_view_reservation(current_user, order):
            visible.append(reservation)
    return visible


@router.get(
    "/reservations/{res_id}/pick-list",
    response_model=MaterialPickListOut,
)
async def generate_reservation_pick_list(
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pick_list = await svc.generate_material_pick_list(db, res_id)
    if pick_list is None:
        raise HTTPException(404, "Reservation not found")
    order = await db.get(ProductionOrder, pick_list.production_order_id)
    if not _can_view_reservation(current_user, order):
        raise HTTPException(404, "Reservation not found")
    return pick_list


@router.get("/reservations/{res_id}", response_model=ReservationOut)
async def get_reservation(
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await svc.get_reservation(db, res_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    order = await db.get(ProductionOrder, res.production_order_id)
    if not _can_view_reservation(current_user, order):
        raise HTTPException(404, "Reservation not found")
    return res


@router.post("/reservations/{res_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = await svc.get_reservation(db, res_id)
    if existing is None:
        raise HTTPException(404, "Reservation not found")
    order = await db.get(ProductionOrder, existing.production_order_id)
    if order is None:
        raise HTTPException(404, "Reservation not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        reservation = await svc.cancel_reservation(db, res_id)
        await db.commit()
        return reservation
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Issues (shortcut: POST a RAW_ISSUE / PKG_ISSUE transaction) ───────────────

@router.post("/issues", response_model=FlowTransactionOut, status_code=201)
async def issue_materials(
    data: FlowTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.flow_type not in (
        FlowType.RAW_ISSUE, FlowType.PKG_ISSUE, FlowType.CONSUMABLE_ISSUE
    ):
        raise HTTPException(400, "Only issue flow types allowed on this endpoint")
    if data.flow_type == FlowType.RAW_ISSUE:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "RAW_ISSUE_REQUIRES_RESERVATION",
                "message": "Production material must be issued through POST /reservations/{reservation_id}/issue so stock, reservation, and movement records remain atomic.",
            },
        )
    if data.flow_type == FlowType.PKG_ISSUE:
        raise HTTPException(
            status_code=409,
            detail="Packaging must be issued from an exact production reservation through the packaging-issue workflow.",
        )
    if data.production_order_id is None:
        raise HTTPException(status_code=422, detail="An issue transaction requires its production order.")
    order = await db.get(ProductionOrder, data.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "edit")
    if any(line.source_warehouse_id != order.source_warehouse_id for line in data.lines):
        raise HTTPException(status_code=422, detail="Issue lines must use the production order source warehouse.")
    return await svc.create_flow_transaction(db, data, current_user.id)


@router.post(
    "/reservations/{res_id}/issue",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def issue_reserved_materials(
    res_id: UUID,
    data: MaterialIssueCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reservation = await svc.get_reservation(db, res_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    order = await db.get(ProductionOrder, reservation.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        transaction = await svc.issue_reserved_materials(
            db, res_id, data, current_user.id
        )
        await db.commit()
        return transaction
    except Exception:
        await db.rollback()
        raise


@router.post(
    "/reservations/{res_id}/packaging-issue",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def issue_reserved_packaging(
    res_id: UUID,
    data: MaterialIssueCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reservation = await svc.get_reservation(db, res_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    order = await db.get(ProductionOrder, reservation.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        transaction = await svc.issue_reserved_materials(
            db, res_id, data, current_user.id, flow_type=FlowType.PKG_ISSUE
        )
        await db.commit()
        return transaction
    except Exception:
        await db.rollback()
        raise


@router.post(
    "/issue-lines/{issue_line_id}/returns",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def return_excess_material(
    issue_line_id: UUID,
    data: MaterialReturnCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order_id = await svc.get_material_issue_order_id(db, issue_line_id)
    if order_id is None:
        raise HTTPException(status_code=404, detail="Material issue line not found")
    order = await db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Material issue line not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        transaction = await svc.return_excess_material(
            db, issue_line_id, data, current_user.id
        )
        await db.commit()
        return transaction
    except Exception:
        await db.rollback()
        raise


@router.post(
    "/issue-lines/{issue_line_id}/scrap",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def scrap_issued_material(
    issue_line_id: UUID,
    data: MaterialScrapCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order_id = await svc.get_material_issue_order_id(db, issue_line_id)
    if order_id is None:
        raise HTTPException(status_code=404, detail="Material issue line not found")
    order = await db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Material issue line not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        transaction = await svc.scrap_issued_material(
            db, issue_line_id, data, current_user.id
        )
        await db.commit()
        return transaction
    except Exception:
        await db.rollback()
        raise


# ── Consumptions ──────────────────────────────────────────────────────────────

@router.post("/consumptions", response_model=ConsumptionOut, status_code=201)
async def record_consumption(
    data: ConsumptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, data.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "edit")
    try:
        consumption = await svc.record_consumption(db, data, current_user.id)
        await db.commit()
        return consumption
    except Exception:
        await db.rollback()
        raise


@router.get("/consumptions/{order_id}", response_model=List[ConsumptionOut])
async def list_consumptions(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, order_id)
    if order is None or not _can_view_reservation(current_user, order):
        raise HTTPException(status_code=404, detail="Production order not found")
    return await svc.list_consumptions(db, order_id)


# ── Returns ───────────────────────────────────────────────────────────────────

@router.post("/returns", response_model=FlowTransactionOut, status_code=201)
async def return_materials(
    data: FlowTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.flow_type not in (FlowType.RETURN, FlowType.REVERSAL):
        raise HTTPException(400, "Only RETURN or REVERSAL flow types allowed on this endpoint")
    if data.flow_type == FlowType.REVERSAL:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "INVENTORY_AWARE_REVERSAL_REQUIRED",
                "message": "Generic REVERSAL drafts cannot be created through the returns endpoint.",
            },
        )
    if data.flow_type == FlowType.RETURN and any(
        line.item_type.strip().lower() == "material" for line in data.lines
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_REQUIRES_ISSUE_LINE",
                "message": "Unused production material must be returned through POST /issue-lines/{issue_line_id}/returns.",
            },
        )
    warehouse_ids = {
        warehouse_id
        for line in data.lines
        for warehouse_id in (line.source_warehouse_id, line.destination_warehouse_id)
        if warehouse_id is not None
    }
    _require_transaction_scope(current_user, warehouse_ids, "edit")
    return await svc.create_flow_transaction(db, data, current_user.id)


# ── Transfers ─────────────────────────────────────────────────────────────────

@router.post("/transfers", response_model=FlowTransactionOut, status_code=201)
async def transfer_materials(
    data: FlowTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if data.flow_type not in (
        FlowType.STAGE_TRANSFER, FlowType.BULK_TRANSFER, FlowType.TANK_TRANSFER,
        FlowType.LINE_TRANSFER, FlowType.WEIGHING_TRANSFER, FlowType.INTERMEDIATE_CREATE,
    ):
        raise HTTPException(400, "Only transfer flow types allowed on this endpoint")
    if data.flow_type in {FlowType.STAGE_TRANSFER, FlowType.INTERMEDIATE_CREATE} or any(
        line.item_type.strip().lower() == "product" for line in data.lines
    ):
        raise HTTPException(
            status_code=409,
            detail="Production WIP must use the authenticated WIP output or stage-transfer workflow.",
        )
    warehouse_ids = {
        warehouse_id
        for line in data.lines
        for warehouse_id in (line.source_warehouse_id, line.destination_warehouse_id)
        if warehouse_id is not None
    }
    if data.production_order_id is not None:
        order = await db.get(ProductionOrder, data.production_order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Production order not found")
        if order.source_warehouse_id is not None:
            warehouse_ids.add(order.source_warehouse_id)
    _require_transaction_scope(current_user, warehouse_ids, "edit")
    return await svc.create_flow_transaction(db, data, current_user.id)


@router.post("/wip/outputs", response_model=FlowTransactionOut, status_code=201)
async def record_wip_output(
    data: WIPOutputCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, data.production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "edit")
    return await svc.record_wip_output(db, data, current_user.id)


@router.get("/wip/balances", response_model=List[WIPBalanceOut])
async def list_wip_balances(
    production_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, production_order_id)
    if order is None or not _can_view_reservation(current_user, order):
        raise HTTPException(status_code=404, detail="Production order not found")
    return await svc.list_wip_balances(db, production_order_id)


@router.post(
    "/wip/orders/{order_id}/outputs/{origin_line_id}/transfers",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def transfer_wip(
    order_id: UUID,
    origin_line_id: UUID,
    data: WIPTransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "edit")
    return await svc.transfer_wip(db, order_id, origin_line_id, data, current_user.id)


@router.post(
    "/wip/orders/{order_id}/bulk-transfers",
    response_model=FlowTransactionOut,
    status_code=201,
)
async def transfer_wip_bulk(
    order_id: UUID,
    data: WIPBulkTransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    order = await db.get(ProductionOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    _require_reservation_scope(current_user, order, "edit")
    return await svc.transfer_wip_bulk(db, order_id, data, current_user.id)


# ── FG Receipts ───────────────────────────────────────────────────────────────

@router.post("/fg-receipts", response_model=FlowTransactionOut, status_code=201)
async def fg_receipt(
    data: FlowTransactionCreate,
    current_user=Depends(get_current_user),
):
    if data.flow_type != FlowType.FG_RECEIPT:
        raise HTTPException(400, "Only FG_RECEIPT flow type allowed on this endpoint")
    raise HTTPException(
        status_code=409,
        detail="Finished goods must be received by completing the authenticated production order so WIP, stock, lot, and genealogy post atomically.",
    )


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
    current_user=Depends(get_current_user),
):
    f = FlowHistoryFilter(
        production_order_id=production_order_id,
        flow_type=flow_type,
    )
    transactions = await svc.get_flow_history(db, f, limit, offset)
    visible = []
    for transaction in transactions:
        warehouse_ids = _transaction_warehouse_ids(transaction)
        if transaction.production_order_id is not None:
            order = await db.get(ProductionOrder, transaction.production_order_id)
            if order is not None and order.source_warehouse_id is not None:
                warehouse_ids.add(order.source_warehouse_id)
        if _can_view_transaction(current_user, warehouse_ids):
            visible.append(transaction)
    return visible


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
