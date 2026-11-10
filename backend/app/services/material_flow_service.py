from __future__ import annotations
import hashlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_CEILING
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func, case
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import selectinload

from app.models.material_flow import (
    MaterialFlowTransaction, MaterialFlowLine, MaterialReservation,
    MaterialReservationLine, ProductionConsumption, PreparedLot,
    TankOccupancy, BatchReconciliation,
    FlowStage, MFAIRecommendation,
    FlowMode, FlowStatus, FlowType, QualityStatus, ReservationStatus,
    MovementReason, StageType,
    TankStatus, ReconciliationStatus, MFAIAgentType, MFAIRecStatus,
)
from app.models.inventory import MovementType, Stock, StockMovement, StockType
from app.models.master import Material, MaterialType, Warehouse
from app.models.production import ProductionOrder, ProductionOrderStatus
from app.models.production_advanced import WorkOrder, WorkOrderStatus
from app.models.quality import LotQualityStatus, ReleaseStatus
from app.models.wms import StorageLocation, WarehouseZone, ZoneType
from app.schemas.material_flow import (
    FlowTransactionCreate, FlowStageCreate, ReservationCreate,
    MaterialIssueCreate, MaterialReturnCreate, MaterialScrapCreate,
    WIPOutputCreate, WIPTransferCreate, WIPBulkTransferCreate, WIPBulkTransferLineCreate, WIPBalanceOut,
    MaterialPickListLineOut, MaterialPickListOut,
    ConsumptionCreate, PreparedLotCreate, PreparedLotWeigh,
    TankCreate, TankUpdate, ReconciliationApprove, MFAIRecAction,
    FlowHistoryFilter,
)
from app.services.utilities_service import convert_uom
from app.services.inventory_locking import lock_inventory_identity

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


def _fefo_stock_sort_key(stock: Stock) -> tuple[bool, date, bool, date, str, str]:
    lot = stock.lot
    return (
        lot is None or lot.expiry_date is None,
        lot.expiry_date if lot and lot.expiry_date else date.max,
        lot is None,
        lot.manufacture_date if lot and lot.manufacture_date else date.max,
        lot.lot_number.casefold() if lot else "",
        str(stock.id),
    )


async def _resolve_staging_location(
    db: AsyncSession,
    warehouse_id: UUID,
    requested_location_id: Optional[UUID],
) -> Optional[StorageLocation]:
    query = (
        select(StorageLocation)
        .join(WarehouseZone, StorageLocation.zone_id == WarehouseZone.id)
        .options(selectinload(StorageLocation.zone))
        .where(
            WarehouseZone.warehouse_id == warehouse_id,
            WarehouseZone.zone_type == ZoneType.STAGING,
            WarehouseZone.is_active.is_(True),
            StorageLocation.is_active.is_(True),
            StorageLocation.is_blocked.is_(False),
        )
        .order_by(StorageLocation.id)
        .with_for_update()
    )
    if requested_location_id is not None:
        query = query.where(StorageLocation.id == requested_location_id)
    result = await db.execute(query)
    candidates = list(result.scalars().all())
    if requested_location_id is not None:
        if not candidates:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "RESERVATION_STAGING_LOCATION_INVALID",
                    "message": "Staging location must be active, unblocked, and in a staging zone in the source warehouse.",
                    "staging_location_id": str(requested_location_id),
                    "warehouse_id": str(warehouse_id),
                },
            )
        return candidates[0]
    if len(candidates) > 1:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "RESERVATION_STAGING_LOCATION_REQUIRED",
                "message": "Select a staging location because this warehouse has multiple active staging locations.",
                "warehouse_id": str(warehouse_id),
                "available_locations": [
                    {"id": str(location.id), "code": location.code}
                    for location in candidates
                ],
            },
        )
    return candidates[0] if candidates else None


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
        q = q.where(FlowStage.active_flag.is_(True))
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
    if data.flow_type == FlowType.REVERSAL:
        raise ValueError(
            "Generic REVERSAL transactions are disabled; use a linked inventory-aware correction workflow."
        )
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


async def _find_issue_by_idempotency_key(
    db: AsyncSession, idempotency_key: str
) -> Optional[MaterialFlowTransaction]:
    result = await db.execute(
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .where(MaterialFlowTransaction.idempotency_key == idempotency_key)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


def _return_idempotent_issue(
    existing: MaterialFlowTransaction,
    reservation_id: UUID,
    requested: dict[UUID, Decimal],
    created_by: UUID,
    flow_type: FlowType,
) -> MaterialFlowTransaction:
    existing_lines = {
        line.reservation_line_id: Decimal(line.quantity)
        for line in existing.lines
        if line.reservation_line_id is not None
    }
    if (
        existing.created_by != created_by
        or existing.flow_type != flow_type
        or existing.source_document_type != "MATERIAL_RESERVATION"
        or existing.source_document_id != reservation_id
        or existing_lines != requested
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_ISSUE_IDEMPOTENCY_KEY_REUSED",
                "message": "This idempotency key already belongs to a different material issue request.",
            },
        )
    if existing.status != FlowStatus.POSTED:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_ISSUE_IDEMPOTENT_RESULT_NOT_POSTED",
                "message": "The original material issue is no longer posted; no replacement issue was created.",
                "flow_id": str(existing.id),
                "status": existing.status.value,
            },
        )
    return existing


async def issue_reserved_materials(
    db: AsyncSession,
    reservation_id: UUID,
    data: MaterialIssueCreate,
    created_by: UUID,
    flow_type: FlowType = FlowType.RAW_ISSUE,
) -> MaterialFlowTransaction:
    if flow_type not in {FlowType.RAW_ISSUE, FlowType.PKG_ISSUE}:
        raise HTTPException(status_code=422, detail="Reserved material issue type is not supported.")
    idempotency_key = data.idempotency_key.strip()
    if len(idempotency_key) < 16:
        raise HTTPException(
            status_code=422,
            detail="Idempotency key must contain at least 16 non-whitespace characters.",
        )
    requested: dict[UUID, Decimal] = {}
    for line in data.lines:
        quantity = Decimal(line.quantity)
        if not quantity.is_finite() or quantity <= 0:
            raise HTTPException(status_code=422, detail="Issued quantity must be finite and greater than zero.")
        if quantity != quantity.quantize(Decimal("0.001")):
            raise HTTPException(
                status_code=422,
                detail="Issued quantity may not exceed the inventory precision of 0.001.",
            )
        if line.reservation_line_id in requested:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_ISSUE_DUPLICATE_RESERVATION_LINE",
                    "message": "A reservation line may appear only once in an issue request.",
                    "reservation_line_id": str(line.reservation_line_id),
                },
            )
        requested[line.reservation_line_id] = quantity

    await lock_inventory_identity(db, f"material-issue-idempotency:{idempotency_key}")
    existing = await _find_issue_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        return _return_idempotent_issue(existing, reservation_id, requested, created_by, flow_type)

    order_id_result = await db.execute(
        select(MaterialReservation.production_order_id).where(
            MaterialReservation.id == reservation_id
        )
    )
    order_id = order_id_result.scalar_one_or_none()
    if order_id is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=409, detail="Reservation production order is unavailable")
    if order.status not in {
        ProductionOrderStatus.RELEASED,
        ProductionOrderStatus.IN_PROGRESS,
    }:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_ISSUE_ORDER_NOT_ACTIVE",
                "message": "Materials can be issued only while the production order is released or in progress.",
                "production_order_id": str(order.id),
                "status": order.status.value,
            },
        )

    reservation_result = await db.execute(
        select(MaterialReservation)
        .options(selectinload(MaterialReservation.lines))
        .where(MaterialReservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    reservation = reservation_result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status not in {
        ReservationStatus.ACTIVE,
        ReservationStatus.PARTIALLY_ISSUED,
    }:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_ISSUE_RESERVATION_NOT_ACTIVE",
                "message": "Only active or partially issued reservations can be issued.",
                "status": reservation.status.value,
            },
        )
    if reservation.expiry_datetime is not None:
        expiry = reservation.expiry_datetime
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= _now():
            raise HTTPException(status_code=409, detail="The material reservation has expired")

    existing = await _find_issue_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        return _return_idempotent_issue(existing, reservation_id, requested, created_by, flow_type)

    reservation_lines = {line.id: line for line in reservation.lines}
    requested_material_ids = {
        reservation_lines[line_id].material_id
        for line_id in requested
        if line_id in reservation_lines and reservation_lines[line_id].material_id is not None
    }
    material_types_result = await db.execute(
        select(Material.id, Material.material_type).where(Material.id.in_(requested_material_ids))
    )
    material_types = {material_id: material_type for material_id, material_type in material_types_result.all()}
    stock_ids: set[UUID] = set()
    for reservation_line_id, quantity in requested.items():
        line = reservation_lines.get(reservation_line_id)
        if line is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_ISSUE_RESERVATION_LINE_MISMATCH",
                    "message": "Every issue line must belong to the selected reservation.",
                    "reservation_line_id": str(reservation_line_id),
                },
            )
        if (
            line.item_type.strip().lower() != "material"
            or line.material_id is None
            or line.warehouse_id != order.source_warehouse_id
            or line.material_id not in material_types
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_ISSUE_RESERVATION_LINE_INVALID",
                    "message": "The reservation line is not a material line in the production source warehouse.",
                    "reservation_line_id": str(line.id),
                },
            )
        is_packaging = material_types[line.material_id] == MaterialType.PACKAGING
        if (flow_type == FlowType.PKG_ISSUE) != is_packaging:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Packaging materials must use the dedicated packaging issue workflow."
                    if is_packaging
                    else "The packaging issue workflow accepts packaging materials only."
                ),
            )
        if line.source_stock_id is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_ISSUE_SOURCE_STOCK_UNRESOLVED",
                    "message": "This legacy reservation has no exact source-stock link and cannot be issued safely.",
                    "reservation_line_id": str(line.id),
                },
            )
        outstanding = Decimal(line.quantity_reserved or 0) - Decimal(line.quantity_issued or 0)
        if outstanding <= 0 or quantity > outstanding:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_ISSUE_EXCEEDS_RESERVED_QUANTITY",
                    "message": "Issued quantity must not exceed this reservation line's outstanding quantity.",
                    "reservation_line_id": str(line.id),
                    "outstanding_quantity": str(max(outstanding, Decimal(0))),
                    "requested_quantity": str(quantity),
                },
            )
        stock_ids.add(line.source_stock_id)

    stock_result = await db.execute(
        select(Stock)
        .options(selectinload(Stock.lot))
        .where(Stock.id.in_(stock_ids))
        .order_by(Stock.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    stocks = {stock.id: stock for stock in stock_result.scalars().all()}
    if set(stocks) != stock_ids:
        raise HTTPException(
            status_code=409,
            detail="A reservation source-stock row no longer exists; issue was not posted.",
        )

    lot_ids: set[UUID] = set()
    for reservation_line_id in requested:
        line = reservation_lines[reservation_line_id]
        stock = stocks[line.source_stock_id]
        if (
            stock.stock_type != StockType.MATERIAL
            or stock.material_id != line.material_id
            or stock.warehouse_id != line.warehouse_id
            or stock.lot_id != line.lot_id
            or stock.location_id != line.source_location_id
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_ISSUE_SOURCE_STOCK_MISMATCH",
                    "message": "The source-stock row no longer matches the reservation's warehouse, material, lot, and location.",
                    "reservation_line_id": str(line.id),
                    "stock_id": str(stock.id),
                },
            )
        if line.lot_id is not None:
            lot_ids.add(line.lot_id)

    quality_statuses: dict[UUID, LotQualityStatus] = {}
    if lot_ids:
        quality_result = await db.execute(
            select(LotQualityStatus)
            .where(LotQualityStatus.lot_id.in_(lot_ids))
            .order_by(LotQualityStatus.lot_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        quality_statuses = {
            status.lot_id: status for status in quality_result.scalars().all()
        }

    source_location_ids = {
        reservation_lines[reservation_line_id].source_location_id
        for reservation_line_id in requested
        if reservation_lines[reservation_line_id].source_location_id is not None
    }
    source_locations: dict[UUID, StorageLocation] = {}
    if source_location_ids:
        location_result = await db.execute(
            select(StorageLocation)
            .options(selectinload(StorageLocation.zone))
            .where(StorageLocation.id.in_(source_location_ids))
            .order_by(StorageLocation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        source_locations = {
            location.id: location for location in location_result.scalars().all()
        }

    issue_quantity_by_stock: dict[UUID, Decimal] = {}
    # Lot eligibility is evaluated at server posting time. A client-supplied
    # historical event timestamp must not make an expired lot issuable today.
    issue_date = _now().date()
    for reservation_line_id, quantity in requested.items():
        line = reservation_lines[reservation_line_id]
        stock = stocks[line.source_stock_id]
        on_hand = Decimal(stock.quantity_on_hand or 0)
        reserved = Decimal(stock.quantity_reserved or 0)
        available = Decimal(stock.quantity_available or 0)
        if on_hand < 0 or reserved < 0 or available < 0 or on_hand != reserved + available:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "STOCK_BALANCE_MISMATCH",
                    "message": "Stock on-hand, reserved, and available quantities are inconsistent.",
                    "stock_id": str(stock.id),
                },
            )
        if stock.is_blocked or reserved < quantity or on_hand < quantity:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_ISSUE_RESERVED_STOCK_UNAVAILABLE",
                    "message": "The reserved source stock is blocked or no longer contains the requested reserved quantity.",
                    "reservation_line_id": str(line.id),
                    "stock_id": str(stock.id),
                },
            )
        if line.lot_id is not None:
            lot = stock.lot
            quality = quality_statuses.get(line.lot_id)
            if (
                lot is None
                or lot.material_id != line.material_id
                or lot.is_quarantine
                or (lot.expiry_date is not None and lot.expiry_date < issue_date)
                or quality is None
                or quality.release_status != ReleaseStatus.RELEASED
                or quality.hold_flag
                or quality.quarantine_flag
                or not quality.fefo_eligible
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "MATERIAL_ISSUE_LOT_NOT_ELIGIBLE",
                        "message": "The reserved lot is expired, held, quarantined, unreleased, or no longer FEFO eligible.",
                        "reservation_line_id": str(line.id),
                        "lot_id": str(line.lot_id),
                    },
                )
        if line.source_location_id is not None:
            location = source_locations.get(line.source_location_id)
            zone = location.zone if location is not None else None
            if (
                location is None
                or not location.is_active
                or location.is_blocked
                or zone is None
                or not zone.is_active
                or zone.warehouse_id != line.warehouse_id
                or zone.zone_type not in {ZoneType.RAW_MATERIAL, ZoneType.STAGING}
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "MATERIAL_ISSUE_SOURCE_LOCATION_UNAVAILABLE",
                        "message": "The reservation source location is no longer usable.",
                        "reservation_line_id": str(line.id),
                        "location_id": str(line.source_location_id),
                    },
                )
        issue_quantity_by_stock[stock.id] = (
            issue_quantity_by_stock.get(stock.id, Decimal(0)) + quantity
        )
    for stock_id, quantity in issue_quantity_by_stock.items():
        if Decimal(stocks[stock_id].quantity_reserved or 0) < quantity:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_ISSUE_RESERVED_STOCK_UNAVAILABLE",
                    "message": "The stock row does not contain the combined reserved quantity for these issue lines.",
                    "stock_id": str(stock_id),
                    "requested_quantity": str(quantity),
                },
            )

    transaction_datetime = data.transaction_datetime or _now()
    if transaction_datetime.tzinfo is None:
        transaction_datetime = transaction_datetime.replace(tzinfo=timezone.utc)
    transaction = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=flow_type,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        work_order_id=reservation.work_order_id,
        source_document_type="MATERIAL_RESERVATION",
        source_document_id=reservation.id,
        idempotency_key=idempotency_key,
        transaction_datetime=transaction_datetime,
        created_by=created_by,
        notes=data.notes,
    )
    db.add(transaction)
    await db.flush()

    for line_no, (reservation_line_id, quantity) in enumerate(requested.items(), start=1):
        line = reservation_lines[reservation_line_id]
        stock = stocks[line.source_stock_id]
        flow_line = MaterialFlowLine(
            transaction_id=transaction.id,
            line_no=line_no,
            item_type="material",
            material_id=line.material_id,
            lot_id=line.lot_id,
            quantity=quantity,
            uom=line.uom,
            source_warehouse_id=line.warehouse_id,
            source_location_id=line.source_location_id,
            quality_status=line.quality_status_required,
            movement_reason=MovementReason.PRODUCTION_ISSUE,
            reservation_flag=True,
            issue_flag=True,
            reservation_line_id=line.id,
            notes=data.notes,
        )
        db.add(flow_line)
        line.quantity_issued = Decimal(line.quantity_issued or 0) + quantity
        stock.quantity_on_hand = Decimal(stock.quantity_on_hand or 0) - quantity
        stock.quantity_reserved = Decimal(stock.quantity_reserved or 0) - quantity
        stock.quantity_available = (
            Decimal(stock.quantity_on_hand or 0) - Decimal(stock.quantity_reserved or 0)
        )
        if stock.quantity_on_hand < 0 or stock.quantity_reserved < 0 or stock.quantity_available < 0:
            raise HTTPException(
                status_code=409,
                detail="Reserved stock changed while the issue was being applied.",
            )
        db.add(
            StockMovement(
                reference_number=transaction.flow_no,
                movement_type=MovementType.ISSUE,
                stock_type=StockType.MATERIAL,
                movement_date=transaction_datetime.date(),
                material_id=line.material_id,
                lot_id=line.lot_id,
                source_warehouse_id=line.warehouse_id,
                source_location_id=line.source_location_id,
                quantity=quantity,
                notes=f"Material issue for reservation {reservation.reservation_no}; flow line {line_no}.",
                created_by_id=created_by,
            )
        )

    outstanding_remains = any(
        Decimal(line.quantity_issued or 0) < Decimal(line.quantity_reserved or 0)
        for line in reservation.lines
    )
    any_issued = any(Decimal(line.quantity_issued or 0) > 0 for line in reservation.lines)
    reservation.status = (
        ReservationStatus.PARTIALLY_ISSUED
        if outstanding_remains
        else ReservationStatus.FULLY_ISSUED
    ) if any_issued else ReservationStatus.ACTIVE
    await db.flush()
    return await get_flow_transaction(db, transaction.id) or transaction


async def get_material_issue_order_id(db: AsyncSession, issue_line_id: UUID) -> Optional[UUID]:
    result = await db.execute(
        select(MaterialFlowTransaction.production_order_id)
        .join(MaterialFlowLine, MaterialFlowLine.transaction_id == MaterialFlowTransaction.id)
        .where(
            MaterialFlowLine.id == issue_line_id,
            MaterialFlowLine.issue_flag.is_(True),
            MaterialFlowTransaction.flow_type.in_((FlowType.RAW_ISSUE, FlowType.PKG_ISSUE)),
        )
    )
    return result.scalar_one_or_none()


async def return_excess_material(
    db: AsyncSession,
    issue_line_id: UUID,
    data: MaterialReturnCreate,
    created_by: UUID,
) -> MaterialFlowTransaction:
    idempotency_key = data.idempotency_key.strip()
    quantity = Decimal(data.quantity)
    if created_by is None:
        raise HTTPException(status_code=401, detail="An authenticated operator is required.")
    if len(idempotency_key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    if not quantity.is_finite() or quantity <= 0:
        raise HTTPException(status_code=422, detail="Return quantity must be finite and greater than zero.")
    if quantity != quantity.quantize(Decimal("0.001")):
        raise HTTPException(status_code=422, detail="Return quantity may not exceed inventory precision of 0.001.")

    await lock_inventory_identity(db, f"material-return-idempotency:{idempotency_key}")
    existing = await _find_issue_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        existing_quantity = (
            Decimal(existing.lines[0].quantity)
            if len(existing.lines) == 1
            else None
        )
        if (
            existing.created_by != created_by
            or existing.flow_type != FlowType.RETURN
            or existing.source_document_type != "MATERIAL_ISSUE_LINE"
            or existing.source_document_id != issue_line_id
            or existing_quantity != quantity
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_RETURN_IDEMPOTENCY_KEY_REUSED",
                    "message": "This idempotency key already belongs to a different material return request.",
                },
            )
        if existing.status != FlowStatus.POSTED:
            raise HTTPException(
                status_code=409,
                detail="The original material return is no longer posted; no replacement return was created.",
            )
        return existing

    order_id = await get_material_issue_order_id(db, issue_line_id)
    if order_id is None:
        raise HTTPException(status_code=404, detail="Posted material issue line not found")
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status not in {ProductionOrderStatus.IN_PROGRESS, ProductionOrderStatus.COMPLETED}:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_ORDER_STATE_INVALID",
                "message": "Unused material can be returned only while its production order is in progress or completed.",
                "status": order.status.value,
            },
        )

    flow_result = await db.execute(
        select(MaterialFlowLine, MaterialFlowTransaction)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(MaterialFlowLine.id == issue_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    flow_pair = flow_result.one_or_none()
    if flow_pair is None:
        raise HTTPException(status_code=404, detail="Posted material issue line not found")
    issue_line, issue_transaction = flow_pair
    if (
        issue_transaction.production_order_id != order.id
        or issue_transaction.flow_type not in {FlowType.RAW_ISSUE, FlowType.PKG_ISSUE}
        or issue_transaction.status != FlowStatus.POSTED
        or issue_line.issue_flag is not True
        or issue_line.item_type.strip().lower() != "material"
        or issue_line.material_id is None
        or issue_line.reservation_line_id is None
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_ISSUE_LINE_INVALID",
                "message": "A material return must reference a posted reservation-based material issue line.",
                "issue_flow_line_id": str(issue_line.id),
            },
        )
    if order.source_warehouse_id is None or issue_line.source_warehouse_id != order.source_warehouse_id:
        raise HTTPException(status_code=409, detail="The material issue line is outside the production source warehouse.")

    reservation_line_result = await db.execute(
        select(MaterialReservationLine)
        .where(MaterialReservationLine.id == issue_line.reservation_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    reservation_line = reservation_line_result.scalar_one_or_none()
    if (
        reservation_line is None
        or reservation_line.source_stock_id is None
        or reservation_line.material_id != issue_line.material_id
        or reservation_line.lot_id != issue_line.lot_id
        or reservation_line.warehouse_id != issue_line.source_warehouse_id
        or reservation_line.source_location_id != issue_line.source_location_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_SOURCE_IDENTITY_UNRESOLVED",
                "message": "The exact original source-stock identity is missing or no longer matches this issue line.",
                "issue_flow_line_id": str(issue_line.id),
            },
        )
    source_stock_result = await db.execute(
        select(Stock)
        .where(Stock.id == reservation_line.source_stock_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    source_stock = source_stock_result.scalar_one_or_none()
    if (
        source_stock is None
        or source_stock.stock_type != StockType.MATERIAL
        or source_stock.material_id != issue_line.material_id
        or source_stock.lot_id != issue_line.lot_id
        or source_stock.warehouse_id != issue_line.source_warehouse_id
        or source_stock.location_id != issue_line.source_location_id
    ):
        raise HTTPException(status_code=409, detail="The original source-stock row no longer matches the issue line.")

    if issue_line.source_location_id is not None:
        location_result = await db.execute(
            select(StorageLocation)
            .options(selectinload(StorageLocation.zone))
            .where(StorageLocation.id == issue_line.source_location_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        location = location_result.scalar_one_or_none()
        zone = location.zone if location is not None else None
        if (
            location is None
            or not location.is_active
            or location.is_blocked
            or zone is None
            or not zone.is_active
            or zone.warehouse_id != order.source_warehouse_id
            or zone.zone_type not in {ZoneType.RAW_MATERIAL, ZoneType.STAGING}
        ):
            raise HTTPException(status_code=409, detail="The original material location is no longer eligible for return receipt.")

    legacy_result = await db.execute(
        select(func.count(ProductionConsumption.id)).where(
            ProductionConsumption.production_order_id == order.id,
            ProductionConsumption.flow_line_id.is_(None),
            ProductionConsumption.material_id == issue_line.material_id,
            (
                ProductionConsumption.quantity_consumed
                + ProductionConsumption.quantity_returned
                + ProductionConsumption.quantity_scrapped
            )
            > 0,
        )
    )
    if legacy_result.scalar_one() > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_RETURN_LEGACY_ISSUE_UNLINKED",
                "message": "Existing unlinked consumption prevents safe calculation of unused issued quantity.",
                "production_order_id": str(order.id),
                "material_id": str(issue_line.material_id),
            },
        )
    prior_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    ProductionConsumption.quantity_consumed
                    + ProductionConsumption.quantity_returned
                    + ProductionConsumption.quantity_scrapped
                ),
                0,
            )
        ).where(ProductionConsumption.flow_line_id == issue_line.id)
    )
    settled_quantity = Decimal(str(prior_result.scalar() or 0))
    outstanding = Decimal(issue_line.quantity) - settled_quantity
    if outstanding <= 0 or quantity > outstanding:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "MATERIAL_RETURN_EXCEEDS_UNUSED_ISSUE",
                "message": "Returned quantity must not exceed the issue line's unused, unreturned, unscrapped quantity.",
                "issue_flow_line_id": str(issue_line.id),
                "outstanding_quantity": str(max(outstanding, Decimal(0))),
                "requested_quantity": str(quantity),
            },
        )

    transaction_datetime = _now()
    transaction = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.RETURN,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        work_order_id=issue_transaction.work_order_id,
        source_document_type="MATERIAL_ISSUE_LINE",
        source_document_id=issue_line.id,
        idempotency_key=idempotency_key,
        transaction_datetime=transaction_datetime,
        created_by=created_by,
        notes=data.notes,
    )
    db.add(transaction)
    await db.flush()
    return_flow_line_id = uuid.uuid4()
    return_line = MaterialFlowLine(
        id=return_flow_line_id,
        transaction_id=transaction.id,
        line_no=1,
        item_type="material",
        material_id=issue_line.material_id,
        lot_id=issue_line.lot_id,
        quantity=quantity,
        uom=issue_line.uom,
        destination_warehouse_id=order.source_warehouse_id,
        destination_location_id=issue_line.source_location_id,
        quality_status=QualityStatus.QUARANTINE,
        movement_reason=MovementReason.RETURN_UNUSED,
        return_flag=True,
        reference_line_id=issue_line.id,
        notes=data.notes,
    )
    db.add(return_line)
    returned_stock = Stock(
        stock_type=StockType.MATERIAL,
        warehouse_id=order.source_warehouse_id,
        material_id=issue_line.material_id,
        lot_id=issue_line.lot_id,
        quantity_on_hand=quantity,
        quantity_reserved=Decimal("0"),
        quantity_available=quantity,
        is_blocked=True,
        location_id=issue_line.source_location_id,
    )
    db.add(returned_stock)
    db.add(
        StockMovement(
            reference_number=transaction.flow_no,
            movement_type=MovementType.RETURN,
            stock_type=StockType.MATERIAL,
            movement_date=transaction_datetime.date(),
            material_id=issue_line.material_id,
            lot_id=issue_line.lot_id,
            destination_warehouse_id=order.source_warehouse_id,
            destination_location_id=issue_line.source_location_id,
            quantity=quantity,
            notes=f"Unused material returned from issue line {issue_line.id}; blocked pending review.",
            created_by_id=created_by,
        )
    )
    db.add(
        ProductionConsumption(
            production_order_id=order.id,
            work_order_id=issue_transaction.work_order_id,
            flow_line_id=issue_line.id,
            return_flow_line_id=return_flow_line_id,
            idempotency_key=idempotency_key,
            item_type="material",
            material_id=issue_line.material_id,
            lot_id=issue_line.lot_id,
            quantity_issued=Decimal(issue_line.quantity),
            quantity_consumed=Decimal("0"),
            quantity_returned=quantity,
            quantity_scrapped=Decimal("0"),
            quantity_variance=outstanding - quantity,
            uom=issue_line.uom,
            consumed_at=transaction_datetime,
            operator_id=created_by,
            notes=data.notes,
        )
    )
    await db.flush()
    return await get_flow_transaction(db, transaction.id) or transaction


async def scrap_issued_material(
    db: AsyncSession,
    issue_line_id: UUID,
    data: MaterialScrapCreate,
    created_by: UUID,
) -> MaterialFlowTransaction:
    idempotency_key = data.idempotency_key.strip()
    quantity = Decimal(data.quantity)
    if created_by is None:
        raise HTTPException(status_code=401, detail="An authenticated operator is required.")
    if len(idempotency_key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    if not quantity.is_finite() or quantity <= 0:
        raise HTTPException(status_code=422, detail="Scrap quantity must be finite and greater than zero.")
    if quantity != quantity.quantize(Decimal("0.001")):
        raise HTTPException(status_code=422, detail="Scrap quantity may not exceed inventory precision of 0.001.")
    reason_code = data.reason_code.value
    notes = data.notes.strip()
    if not notes:
        raise HTTPException(status_code=422, detail="A scrap/spillage explanation is required.")

    await lock_inventory_identity(db, f"material-scrap-idempotency:{idempotency_key}")
    existing = await _find_issue_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        existing_quantity = Decimal(existing.lines[0].quantity) if len(existing.lines) == 1 else None
        if (
            existing.created_by != created_by
            or existing.flow_type != FlowType.SCRAP
            or existing.source_document_type != "MATERIAL_ISSUE_LINE"
            or existing.source_document_id != issue_line_id
            or existing_quantity != quantity
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_SCRAP_IDEMPOTENCY_KEY_REUSED",
                    "message": "This idempotency key already belongs to a different scrap request.",
                },
            )
        if existing.status != FlowStatus.POSTED:
            raise HTTPException(status_code=409, detail="The original scrap event is no longer posted.")
        return existing

    order_id = await get_material_issue_order_id(db, issue_line_id)
    if order_id is None:
        raise HTTPException(status_code=404, detail="Posted material issue line not found")
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_SCRAP_ORDER_NOT_IN_PROGRESS",
                "message": "Production scrap/spillage can be recorded only while the order is in progress.",
                "status": order.status.value,
            },
        )

    flow_result = await db.execute(
        select(MaterialFlowLine, MaterialFlowTransaction)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(MaterialFlowLine.id == issue_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    flow_pair = flow_result.one_or_none()
    if flow_pair is None:
        raise HTTPException(status_code=404, detail="Posted material issue line not found")
    issue_line, issue_transaction = flow_pair
    if (
        issue_transaction.production_order_id != order.id
        or issue_transaction.flow_type not in {FlowType.RAW_ISSUE, FlowType.PKG_ISSUE}
        or issue_transaction.status != FlowStatus.POSTED
        or issue_line.issue_flag is not True
        or issue_line.item_type.strip().lower() != "material"
        or issue_line.material_id is None
        or issue_line.reservation_line_id is None
        or order.source_warehouse_id is None
        or issue_line.source_warehouse_id != order.source_warehouse_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_SCRAP_ISSUE_LINE_INVALID",
                "message": "Scrap must reference a posted reservation-based material issue line in the production source warehouse.",
                "issue_flow_line_id": str(issue_line.id),
            },
        )

    reservation_line_result = await db.execute(
        select(MaterialReservationLine)
        .where(MaterialReservationLine.id == issue_line.reservation_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    reservation_line = reservation_line_result.scalar_one_or_none()
    if (
        reservation_line is None
        or reservation_line.source_stock_id is None
        or reservation_line.material_id != issue_line.material_id
        or reservation_line.lot_id != issue_line.lot_id
        or reservation_line.warehouse_id != issue_line.source_warehouse_id
        or reservation_line.source_location_id != issue_line.source_location_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_SCRAP_SOURCE_IDENTITY_UNRESOLVED",
                "message": "The exact original reservation source cannot be verified for this scrap event.",
                "issue_flow_line_id": str(issue_line.id),
            },
        )

    legacy_result = await db.execute(
        select(func.count(ProductionConsumption.id)).where(
            ProductionConsumption.production_order_id == order.id,
            ProductionConsumption.flow_line_id.is_(None),
            ProductionConsumption.material_id == issue_line.material_id,
            (
                ProductionConsumption.quantity_consumed
                + ProductionConsumption.quantity_returned
                + ProductionConsumption.quantity_scrapped
            )
            > 0,
        )
    )
    if legacy_result.scalar_one() > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_SCRAP_LEGACY_ISSUE_UNLINKED",
                "message": "Existing unlinked consumption prevents safe calculation of remaining issued material.",
                "production_order_id": str(order.id),
                "material_id": str(issue_line.material_id),
            },
        )
    prior_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    ProductionConsumption.quantity_consumed
                    + ProductionConsumption.quantity_returned
                    + ProductionConsumption.quantity_scrapped
                ),
                0,
            )
        ).where(ProductionConsumption.flow_line_id == issue_line.id)
    )
    settled_quantity = Decimal(str(prior_result.scalar() or 0))
    outstanding = Decimal(issue_line.quantity) - settled_quantity
    if outstanding <= 0 or quantity > outstanding:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "MATERIAL_SCRAP_EXCEEDS_OUTSTANDING_ISSUE",
                "message": "Scrap quantity must not exceed the issued line's remaining unconsumed, unreturned, unscrapped quantity.",
                "issue_flow_line_id": str(issue_line.id),
                "outstanding_quantity": str(max(outstanding, Decimal(0))),
                "requested_quantity": str(quantity),
            },
        )

    transaction_datetime = _now()
    transaction = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.SCRAP,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        work_order_id=issue_transaction.work_order_id,
        source_document_type="MATERIAL_ISSUE_LINE",
        source_document_id=issue_line.id,
        idempotency_key=idempotency_key,
        transaction_datetime=transaction_datetime,
        created_by=created_by,
        notes=f"{reason_code}: {notes}",
    )
    db.add(transaction)
    await db.flush()
    scrap_flow_line_id = uuid.uuid4()
    scrap_line = MaterialFlowLine(
        id=scrap_flow_line_id,
        transaction_id=transaction.id,
        line_no=1,
        item_type="material",
        material_id=issue_line.material_id,
        lot_id=issue_line.lot_id,
        quantity=quantity,
        uom=issue_line.uom,
        source_warehouse_id=order.source_warehouse_id,
        source_location_id=issue_line.source_location_id,
        quality_status=QualityStatus.REJECTED,
        movement_reason=MovementReason.SCRAP,
        scrap_flag=True,
        reference_line_id=issue_line.id,
        notes=f"{reason_code}: {notes}",
    )
    db.add(scrap_line)
    db.add(
        ProductionConsumption(
            production_order_id=order.id,
            work_order_id=issue_transaction.work_order_id,
            flow_line_id=issue_line.id,
            scrap_flow_line_id=scrap_flow_line_id,
            idempotency_key=idempotency_key,
            scrap_reason_code=reason_code,
            item_type="material",
            material_id=issue_line.material_id,
            lot_id=issue_line.lot_id,
            quantity_issued=Decimal(issue_line.quantity),
            quantity_consumed=Decimal("0"),
            quantity_returned=Decimal("0"),
            quantity_scrapped=quantity,
            quantity_variance=outstanding - quantity,
            uom=issue_line.uom,
            consumed_at=transaction_datetime,
            operator_id=created_by,
            notes=notes,
        )
    )
    await db.flush()
    return await get_flow_transaction(db, transaction.id) or transaction


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


_WIP_STAGE_TYPES = {
    StageType.MIXING,
    StageType.PREMIX,
    StageType.INTERMEDIATE_HOLD,
    StageType.BULK_TANK,
    StageType.QC_HOLD_TANK,
    StageType.RELEASED_BULK,
    StageType.FILLING_STAGING,
}


def _validate_wip_quantity(quantity: Decimal) -> Decimal:
    value = Decimal(quantity)
    if not value.is_finite() or value <= 0 or value != value.quantize(Decimal("0.001")):
        raise HTTPException(status_code=422, detail="WIP quantity must be positive and use 0.001 precision.")
    return value


async def _lock_wip_order(
    db: AsyncSession, order_id: UUID, *, require_in_progress: bool = True
) -> ProductionOrder:
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if require_in_progress and order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="WIP can only be recorded or transferred for an in-progress production order.")
    if order.source_warehouse_id is None:
        raise HTTPException(status_code=409, detail="Production order source warehouse is required for WIP location control.")
    return order


async def _validate_wip_location(
    db: AsyncSession,
    order: ProductionOrder,
    stage_id: UUID,
    location_id: UUID,
) -> tuple[FlowStage, StorageLocation]:
    stage = await db.get(FlowStage, stage_id, with_for_update=True)
    if (
        stage is None
        or not stage.active_flag
        or stage.stage_type not in _WIP_STAGE_TYPES
        or stage.warehouse_id != order.source_warehouse_id
    ):
        raise HTTPException(status_code=422, detail="WIP stage must be active, production-capable, and in the order source warehouse.")
    result = await db.execute(
        select(StorageLocation)
        .options(selectinload(StorageLocation.zone))
        .where(StorageLocation.id == location_id)
        .with_for_update()
    )
    location = result.scalar_one_or_none()
    if (
        location is None
        or not location.is_active
        or location.is_blocked
        or location.zone is None
        or not location.zone.is_active
        or location.zone.warehouse_id != order.source_warehouse_id
        or (stage.location_id is not None and stage.location_id != location.id)
    ):
        raise HTTPException(status_code=422, detail="WIP location must be active, unblocked, and match the stage warehouse/location.")
    return stage, location


async def _find_wip_transaction(db: AsyncSession, key: str) -> Optional[MaterialFlowTransaction]:
    result = await db.execute(
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .where(MaterialFlowTransaction.idempotency_key == key)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _lock_wip_idempotency_key(db: AsyncSession, key: str) -> None:
    # The DB uniqueness constraint is global, so serialize same-key calls even
    # when they target different production orders.
    lock_id = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big", signed=True)
    await db.execute(select(func.pg_advisory_xact_lock(lock_id)))


def _require_idempotent_wip_match(
    existing: MaterialFlowTransaction,
    *,
    created_by: UUID,
    flow_type: FlowType,
    order_id: UUID,
    source_document_type: str,
    source_document_id: UUID,
    expected: Callable[[MaterialFlowLine], bool],
) -> MaterialFlowTransaction:
    if (
        existing.created_by != created_by
        or existing.flow_type != flow_type
        or existing.production_order_id != order_id
        or existing.source_document_type != source_document_type
        or existing.source_document_id != source_document_id
        or len(existing.lines) != 1
        or expected(existing.lines[0]) is False
    ):
        raise HTTPException(status_code=409, detail="WIP idempotency key was already used for a different request.")
    if existing.status != FlowStatus.POSTED:
        raise HTTPException(status_code=409, detail="Original WIP request is no longer posted; no replacement was created.")
    return existing


async def record_wip_output(
    db: AsyncSession, data: WIPOutputCreate, created_by: UUID
) -> MaterialFlowTransaction:
    quantity = _validate_wip_quantity(Decimal(data.quantity))
    key = data.idempotency_key.strip()
    if len(key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    await _lock_wip_idempotency_key(db, key)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        order = await db.get(ProductionOrder, data.production_order_id)
        if order is None:
            raise HTTPException(status_code=409, detail="Original WIP output order is no longer available.")
        return _require_idempotent_wip_match(
            existing,
            created_by=created_by,
            flow_type=FlowType.INTERMEDIATE_CREATE,
            order_id=order.id,
            source_document_type="M24_WIP_OUTPUT",
            source_document_id=order.id,
            expected=lambda line: all((
                line.item_type == "product",
                line.product_id == order.product_id,
                Decimal(line.quantity) == quantity,
                line.uom.strip().upper() == order.uom.strip().upper() == data.uom.strip().upper(),
                line.destination_stage_id == data.destination_stage_id,
                line.destination_location_id == data.destination_location_id,
                line.batch_id == (order.batch_no or order.order_no),
            )),
        )
    order = await _lock_wip_order(db, data.production_order_id, require_in_progress=False)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        return _require_idempotent_wip_match(
            existing,
            created_by=created_by,
            flow_type=FlowType.INTERMEDIATE_CREATE,
            order_id=order.id,
            source_document_type="M24_WIP_OUTPUT",
            source_document_id=order.id,
            expected=lambda line: all((
                line.item_type == "product",
                line.product_id == order.product_id,
                Decimal(line.quantity) == quantity,
                line.uom.strip().upper() == order.uom.strip().upper() == data.uom.strip().upper(),
                line.destination_stage_id == data.destination_stage_id,
                line.destination_location_id == data.destination_location_id,
                line.batch_id == (order.batch_no or order.order_no),
            )),
        )
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="WIP can only be recorded or transferred for an in-progress production order.")
    stage, location = await _validate_wip_location(
        db, order, data.destination_stage_id, data.destination_location_id
    )
    if data.uom.strip().upper() != order.uom.strip().upper():
        raise HTTPException(status_code=422, detail="WIP output UOM must match the production-order product UOM.")
    result = await db.execute(
        select(func.coalesce(func.sum(MaterialFlowLine.quantity), 0))
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(
            MaterialFlowTransaction.production_order_id == order.id,
            MaterialFlowTransaction.flow_type == FlowType.INTERMEDIATE_CREATE,
            MaterialFlowTransaction.source_document_type == "M24_WIP_OUTPUT",
            MaterialFlowTransaction.source_document_id == order.id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
        )
    )
    already_recorded = Decimal(result.scalar_one() or 0)
    if already_recorded + quantity > Decimal(order.planned_quantity):
        raise HTTPException(status_code=409, detail="Recorded WIP output cannot exceed the production order planned quantity.")

    tx = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.INTERMEDIATE_CREATE,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        source_document_type="M24_WIP_OUTPUT",
        source_document_id=order.id,
        idempotency_key=key,
        transaction_datetime=_now(),
        created_by=created_by,
        notes=data.notes,
    )
    db.add(tx)
    await db.flush()
    db.add(MaterialFlowLine(
        transaction_id=tx.id,
        line_no=1,
        item_type="product",
        product_id=order.product_id,
        batch_id=order.batch_no or order.order_no,
        quantity=quantity,
        uom=order.uom,
        source_warehouse_id=order.source_warehouse_id,
        destination_warehouse_id=order.source_warehouse_id,
        destination_stage_id=stage.id,
        destination_location_id=location.id,
        quality_status=stage.quality_default_status,
        movement_reason=MovementReason.INTERMEDIATE_TRANSFER,
        notes=data.notes,
    ))
    await db.commit()
    return await get_flow_transaction(db, tx.id)


async def _wip_origin_balances(
    db: AsyncSession,
    order: ProductionOrder,
    origin_line_id: UUID,
) -> tuple[MaterialFlowLine, dict[tuple[UUID, UUID], Decimal]]:
    origin_result = await db.execute(
        select(MaterialFlowLine)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(
            MaterialFlowLine.id == origin_line_id,
            MaterialFlowLine.item_type == "product",
            MaterialFlowLine.product_id == order.product_id,
            MaterialFlowTransaction.production_order_id == order.id,
            MaterialFlowTransaction.flow_type == FlowType.INTERMEDIATE_CREATE,
            MaterialFlowTransaction.source_document_type == "M24_WIP_OUTPUT",
            MaterialFlowTransaction.source_document_id == order.id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
        )
        .with_for_update()
    )
    origin = origin_result.scalar_one_or_none()
    if (
        origin is None
        or origin.destination_stage_id is None
        or origin.destination_location_id is None
        or origin.source_stage_id is not None
        or origin.source_location_id is not None
        or origin.source_warehouse_id != order.source_warehouse_id
        or origin.destination_warehouse_id != order.source_warehouse_id
        or origin.batch_id != (order.batch_no or order.order_no)
    ):
        raise HTTPException(status_code=404, detail="Posted WIP output was not found for this production order.")
    balances = {(origin.destination_stage_id, origin.destination_location_id): Decimal(origin.quantity)}
    transfer_result = await db.execute(
        select(MaterialFlowLine, MaterialFlowTransaction.source_document_type)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(
            MaterialFlowLine.reference_line_id == origin.id,
            MaterialFlowTransaction.production_order_id == order.id,
            or_(
                and_(
                    MaterialFlowTransaction.flow_type == FlowType.STAGE_TRANSFER,
                    MaterialFlowTransaction.source_document_type == "M24_WIP_TRANSFER",
                    MaterialFlowTransaction.source_document_id == origin.id,
                ),
                and_(
                    MaterialFlowTransaction.flow_type == FlowType.BULK_TRANSFER,
                    MaterialFlowTransaction.source_document_type == "M24_WIP_BULK_TRANSFER",
                    MaterialFlowTransaction.source_document_id == order.id,
                ),
                and_(
                    MaterialFlowTransaction.flow_type == FlowType.FG_RECEIPT,
                    MaterialFlowTransaction.source_document_type == "M24_WIP_FG_RECEIPT",
                    MaterialFlowTransaction.source_document_id == order.id,
                ),
            ),
            MaterialFlowTransaction.status == FlowStatus.POSTED,
        )
        .order_by(
            case(
                (MaterialFlowTransaction.source_document_type == "M24_WIP_FG_RECEIPT", 1),
                else_=0,
            ),
            MaterialFlowTransaction.transaction_datetime,
            MaterialFlowTransaction.id,
            MaterialFlowLine.line_no,
        )
    )
    for movement, source_document_type in transfer_result.all():
        source_key = (movement.source_stage_id, movement.source_location_id)
        destination_key = (movement.destination_stage_id, movement.destination_location_id)
        moved_quantity = Decimal(movement.quantity)
        source_balance = balances.get(source_key, Decimal("0"))
        if (
            movement.source_stage_id is None
            or movement.source_location_id is None
            or moved_quantity <= 0
            or moved_quantity > source_balance
            or movement.item_type != origin.item_type
            or movement.product_id != origin.product_id
            or movement.material_id != origin.material_id
            or movement.lot_id != origin.lot_id
            or movement.batch_id != origin.batch_id
            or movement.uom != origin.uom
            or movement.source_warehouse_id != order.source_warehouse_id
        ):
            raise HTTPException(status_code=409, detail="WIP transfer history exceeds its recorded output quantity.")
        balances[source_key] = source_balance - moved_quantity
        if source_document_type == "M24_WIP_FG_RECEIPT":
            if (
                movement.destination_stage_id is not None
                or movement.destination_location_id is not None
                or movement.destination_warehouse_id != order.target_warehouse_id
            ):
                raise HTTPException(status_code=409, detail="Finished-goods receipt history has an invalid WIP destination.")
        else:
            if (
                movement.destination_stage_id is None
                or movement.destination_location_id is None
                or movement.destination_warehouse_id != order.source_warehouse_id
            ):
                raise HTTPException(status_code=409, detail="WIP transfer history has no destination stage or location.")
            destination_key = (movement.destination_stage_id, movement.destination_location_id)
            balances[destination_key] = balances.get(destination_key, Decimal("0")) + moved_quantity
    return origin, balances


async def list_wip_balances(db: AsyncSession, production_order_id: UUID) -> list[WIPBalanceOut]:
    result = await db.execute(
        select(MaterialFlowTransaction)
        .options(selectinload(MaterialFlowTransaction.lines))
        .where(
            MaterialFlowTransaction.production_order_id == production_order_id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
            MaterialFlowTransaction.flow_type.in_(
                (FlowType.INTERMEDIATE_CREATE, FlowType.STAGE_TRANSFER, FlowType.BULK_TRANSFER, FlowType.FG_RECEIPT)
            ),
            MaterialFlowTransaction.source_document_type.in_(
                ("M24_WIP_OUTPUT", "M24_WIP_TRANSFER", "M24_WIP_BULK_TRANSFER", "M24_WIP_FG_RECEIPT")
            ),
        )
    )
    order = await db.get(ProductionOrder, production_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    origins = [
        line
        for tx in result.scalars().all()
        if (
            tx.flow_type == FlowType.INTERMEDIATE_CREATE
            and tx.source_document_type == "M24_WIP_OUTPUT"
            and tx.source_document_id == order.id
        )
        for line in tx.lines
    ]
    balances: list[WIPBalanceOut] = []
    for origin in origins:
        _, origin_balances = await _wip_origin_balances(db, order, origin.id)
        for (stage_id, location_id), quantity in origin_balances.items():
            if quantity <= 0:
                continue
            stage = await db.get(FlowStage, stage_id)
            location = await db.get(StorageLocation, location_id)
            if stage is None or location is None:
                continue
            balances.append(WIPBalanceOut(
                origin_line_id=origin.id,
                production_order_id=order.id,
                production_order_no=order.order_no,
                product_id=order.product_id,
                batch_id=origin.batch_id or order.batch_no or order.order_no,
                lot_id=origin.lot_id,
                quantity=quantity,
                uom=origin.uom,
                stage_id=stage.id,
                stage_name=stage.stage_name,
                location_id=location.id,
                location_code=location.code,
                quality_status=origin.quality_status,
            ))
    return balances


async def receive_wip_finished_goods(
    db: AsyncSession,
    order_id: UUID,
    *,
    quantity: Decimal,
    destination_warehouse_id: UUID,
    created_by: UUID,
) -> Optional[MaterialFlowTransaction]:
    """Consume all recorded WIP origins when the production order posts its FG receipt.

    Legacy production orders without an M24 WIP output ledger keep the established
    completion behavior. Once WIP is recorded, its full available quantity must
    match the canonical finished-goods receipt before the order can close.
    """
    value = _validate_wip_quantity(Decimal(quantity))
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="WIP finished goods can only be received while the order is in progress.")

    output_result = await db.execute(
        select(func.count(MaterialFlowLine.id))
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(
            MaterialFlowTransaction.production_order_id == order.id,
            MaterialFlowTransaction.flow_type == FlowType.INTERMEDIATE_CREATE,
            MaterialFlowTransaction.source_document_type == "M24_WIP_OUTPUT",
            MaterialFlowTransaction.source_document_id == order.id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
            MaterialFlowLine.item_type == "product",
            MaterialFlowLine.product_id == order.product_id,
        )
    )
    if output_result.scalar_one() == 0:
        invalid_output_count = await db.scalar(
            select(func.count(MaterialFlowLine.id))
            .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
            .where(
                MaterialFlowTransaction.production_order_id == order.id,
                MaterialFlowTransaction.flow_type == FlowType.INTERMEDIATE_CREATE,
                MaterialFlowTransaction.source_document_type == "M24_WIP_OUTPUT",
                MaterialFlowTransaction.source_document_id.is_distinct_from(order.id),
                MaterialFlowTransaction.status == FlowStatus.POSTED,
                MaterialFlowLine.item_type == "product",
                MaterialFlowLine.product_id == order.product_id,
            )
        )
        if invalid_output_count:
            raise HTTPException(status_code=409, detail="WIP output source document does not match the production order.")
        return None

    if destination_warehouse_id != order.target_warehouse_id:
        raise HTTPException(status_code=409, detail="Finished goods must use the production order target warehouse.")
    if order.source_warehouse_id is None:
        raise HTTPException(status_code=409, detail="Production order source warehouse is required for WIP receipt lineage.")

    idempotency_key = f"M24-WIP-FG-RECEIPT:{order.id}"
    await _lock_wip_idempotency_key(db, idempotency_key)
    existing = await _find_wip_transaction(db, idempotency_key)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Finished goods for this production order already consumed its WIP ledger.")

    balances = await list_wip_balances(db, order.id)
    available_quantity = sum((Decimal(balance.quantity) for balance in balances), Decimal("0"))
    if available_quantity != value:
        raise HTTPException(
            status_code=409,
            detail=(
                "Finished-goods quantity must equal all available WIP for this order "
                f"({available_quantity} {order.uom})."
            ),
        )

    transaction = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.FG_RECEIPT,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        source_document_type="M24_WIP_FG_RECEIPT",
        source_document_id=order.id,
        idempotency_key=idempotency_key,
        created_by=created_by,
        notes=f"Finished-goods receipt for {order.order_no}; source WIP fully consumed.",
        lines=[],
    )
    db.add(transaction)
    await db.flush()
    for line_no, balance in enumerate(balances, start=1):
        transaction.lines.append(MaterialFlowLine(
            line_no=line_no,
            item_type="product",
            product_id=order.product_id,
            lot_id=balance.lot_id,
            batch_id=balance.batch_id,
            quantity=balance.quantity,
            uom=balance.uom,
            source_warehouse_id=order.source_warehouse_id,
            source_location_id=balance.location_id,
            source_stage_id=balance.stage_id,
            destination_warehouse_id=order.target_warehouse_id,
            destination_location_id=None,
            destination_stage_id=None,
            quality_status=balance.quality_status,
            movement_reason=MovementReason.FG_RECEIPT,
            reference_line_id=balance.origin_line_id,
            notes="WIP origin consumed by the atomic production-order finished-goods receipt.",
        ))
    await db.flush()
    return transaction


async def transfer_wip(
    db: AsyncSession,
    order_id: UUID,
    origin_line_id: UUID,
    data: WIPTransferCreate,
    created_by: UUID,
) -> MaterialFlowTransaction:
    quantity = _validate_wip_quantity(Decimal(data.quantity))
    key = data.idempotency_key.strip()
    if len(key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    await _lock_wip_idempotency_key(db, key)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        return _require_idempotent_wip_match(
            existing,
            created_by=created_by,
            flow_type=FlowType.STAGE_TRANSFER,
            order_id=order_id,
            source_document_type="M24_WIP_TRANSFER",
            source_document_id=origin_line_id,
            expected=lambda line: all((
                line.reference_line_id == origin_line_id,
                Decimal(line.quantity) == quantity,
                line.source_stage_id == data.source_stage_id,
                line.source_location_id == data.source_location_id,
                line.destination_stage_id == data.destination_stage_id,
                line.destination_location_id == data.destination_location_id,
            )),
        )
    order = await _lock_wip_order(db, order_id, require_in_progress=False)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        return _require_idempotent_wip_match(
            existing,
            created_by=created_by,
            flow_type=FlowType.STAGE_TRANSFER,
            order_id=order.id,
            source_document_type="M24_WIP_TRANSFER",
            source_document_id=origin_line_id,
            expected=lambda line: all((
                line.reference_line_id == origin_line_id,
                Decimal(line.quantity) == quantity,
                line.source_stage_id == data.source_stage_id,
                line.source_location_id == data.source_location_id,
                line.destination_stage_id == data.destination_stage_id,
                line.destination_location_id == data.destination_location_id,
            )),
        )
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="WIP can only be recorded or transferred for an in-progress production order.")
    source_stage, source_location = await _validate_wip_location(
        db, order, data.source_stage_id, data.source_location_id
    )
    destination_stage, destination_location = await _validate_wip_location(
        db, order, data.destination_stage_id, data.destination_location_id
    )
    if source_stage.id == destination_stage.id and source_location.id == destination_location.id:
        raise HTTPException(status_code=422, detail="WIP destination must differ from the source stage or location.")
    origin, balances = await _wip_origin_balances(
        db, order, origin_line_id
    )
    available = balances.get((source_stage.id, source_location.id), Decimal("0"))
    if quantity > available:
        raise HTTPException(status_code=409, detail="WIP transfer quantity exceeds the available balance at the source location.")
    tx = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.STAGE_TRANSFER,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        source_document_type="M24_WIP_TRANSFER",
        source_document_id=origin.id,
        idempotency_key=key,
        transaction_datetime=_now(),
        created_by=created_by,
        notes=data.notes,
    )
    db.add(tx)
    await db.flush()
    db.add(MaterialFlowLine(
        transaction_id=tx.id,
        line_no=1,
        item_type="product",
        product_id=origin.product_id,
        lot_id=origin.lot_id,
        batch_id=origin.batch_id,
        quantity=quantity,
        uom=origin.uom,
        source_warehouse_id=order.source_warehouse_id,
        source_location_id=source_location.id,
        source_stage_id=source_stage.id,
        destination_warehouse_id=order.source_warehouse_id,
        destination_location_id=destination_location.id,
        destination_stage_id=destination_stage.id,
        quality_status=origin.quality_status,
        movement_reason=MovementReason.INTERMEDIATE_TRANSFER,
        reference_line_id=origin.id,
        notes=data.notes,
    ))
    await db.commit()
    return await get_flow_transaction(db, tx.id)


def _normalize_wip_bulk_request(
    lines: list[WIPBulkTransferLineCreate],
) -> list[tuple[UUID, Decimal, UUID, UUID, UUID, UUID]]:
    normalized = [
        (
            line.origin_line_id,
            _validate_wip_quantity(Decimal(line.quantity)),
            line.source_stage_id,
            line.source_location_id,
            line.destination_stage_id,
            line.destination_location_id,
        )
        for line in lines
    ]
    identity_keys = [
        (item[0], item[2], item[3], item[4], item[5])
        for item in normalized
    ]
    if len(identity_keys) != len(set(identity_keys)):
        raise HTTPException(status_code=422, detail="A WIP origin/source/destination may appear only once in a bulk transfer.")
    return sorted(normalized, key=lambda item: tuple(str(value) for value in item))


def _existing_wip_bulk_signature(
    transaction: MaterialFlowTransaction,
) -> list[tuple[UUID, Decimal, UUID, UUID, UUID, UUID]]:
    items = [
        (
            line.reference_line_id,
            Decimal(line.quantity),
            line.source_stage_id,
            line.source_location_id,
            line.destination_stage_id,
            line.destination_location_id,
        )
        for line in transaction.lines
        if line.reference_line_id is not None
        and line.source_stage_id is not None
        and line.source_location_id is not None
        and line.destination_stage_id is not None
        and line.destination_location_id is not None
    ]
    return sorted(items, key=lambda item: tuple(str(value) for value in item))


def _return_wip_bulk_retry(
    existing: MaterialFlowTransaction,
    *,
    order_id: UUID,
    created_by: UUID,
    expected_lines: list[tuple[UUID, Decimal, UUID, UUID, UUID, UUID]],
) -> MaterialFlowTransaction:
    if (
        existing.created_by != created_by
        or existing.flow_type != FlowType.BULK_TRANSFER
        or existing.production_order_id != order_id
        or existing.source_document_type != "M24_WIP_BULK_TRANSFER"
        or existing.source_document_id != order_id
        or existing.status != FlowStatus.POSTED
        or len(existing.lines) != len(expected_lines)
        or any(line.item_type != "product" for line in existing.lines)
        or _existing_wip_bulk_signature(existing) != expected_lines
    ):
        raise HTTPException(status_code=409, detail="WIP bulk-transfer idempotency key belongs to a different or non-posted request.")
    return existing


async def transfer_wip_bulk(
    db: AsyncSession,
    order_id: UUID,
    data: WIPBulkTransferCreate,
    created_by: UUID,
) -> MaterialFlowTransaction:
    key = data.idempotency_key.strip()
    if len(key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    requested_lines = _normalize_wip_bulk_request(data.lines)
    await _lock_wip_idempotency_key(db, key)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        return _return_wip_bulk_retry(
            existing,
            order_id=order_id,
            created_by=created_by,
            expected_lines=requested_lines,
        )

    order = await _lock_wip_order(db, order_id, require_in_progress=False)
    existing = await _find_wip_transaction(db, key)
    if existing is not None:
        return _return_wip_bulk_retry(
            existing,
            order_id=order_id,
            created_by=created_by,
            expected_lines=requested_lines,
        )
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="WIP can only be transferred for an in-progress production order.")

    source_keys = {(item[0], item[2], item[3]) for item in requested_lines}
    if any((item[0], item[4], item[5]) in source_keys for item in requested_lines):
        raise HTTPException(status_code=422, detail="A bulk request cannot transfer WIP through another line in the same batch.")

    origins: dict[UUID, MaterialFlowLine] = {}
    balances_by_origin: dict[UUID, dict[tuple[UUID, UUID], Decimal]] = {}
    source_totals: dict[tuple[UUID, UUID, UUID], Decimal] = {}
    for origin_id, quantity, source_stage_id, source_location_id, destination_stage_id, destination_location_id in requested_lines:
        source_stage, source_location = await _validate_wip_location(
            db, order, source_stage_id, source_location_id
        )
        destination_stage, destination_location = await _validate_wip_location(
            db, order, destination_stage_id, destination_location_id
        )
        if source_stage.id == destination_stage.id and source_location.id == destination_location.id:
            raise HTTPException(status_code=422, detail="WIP destination must differ from the source stage or location.")
        if origin_id not in balances_by_origin:
            origin, balances = await _wip_origin_balances(db, order, origin_id)
            origins[origin_id] = origin
            balances_by_origin[origin_id] = balances
        source_key = (origin_id, source_stage.id, source_location.id)
        source_totals[source_key] = source_totals.get(source_key, Decimal("0")) + quantity

    for (origin_id, stage_id, location_id), requested_quantity in source_totals.items():
        available = balances_by_origin[origin_id].get((stage_id, location_id), Decimal("0"))
        if requested_quantity > available:
            raise HTTPException(status_code=409, detail="Bulk WIP transfer exceeds a source location's available balance.")

    tx = MaterialFlowTransaction(
        flow_no=_flow_no(),
        flow_type=FlowType.BULK_TRANSFER,
        flow_mode=FlowMode.ONE_STEP,
        status=FlowStatus.POSTED,
        production_order_id=order.id,
        source_document_type="M24_WIP_BULK_TRANSFER",
        source_document_id=order.id,
        idempotency_key=key,
        transaction_datetime=_now(),
        created_by=created_by,
        notes=data.notes,
    )
    db.add(tx)
    await db.flush()
    for line_no, (origin_id, quantity, source_stage_id, source_location_id, destination_stage_id, destination_location_id) in enumerate(requested_lines, start=1):
        origin = origins[origin_id]
        db.add(MaterialFlowLine(
            transaction_id=tx.id,
            line_no=line_no,
            item_type="product",
            product_id=origin.product_id,
            lot_id=origin.lot_id,
            batch_id=origin.batch_id,
            quantity=quantity,
            uom=origin.uom,
            source_warehouse_id=order.source_warehouse_id,
            source_location_id=source_location_id,
            source_stage_id=source_stage_id,
            destination_warehouse_id=order.source_warehouse_id,
            destination_location_id=destination_location_id,
            destination_stage_id=destination_stage_id,
            quality_status=origin.quality_status,
            movement_reason=MovementReason.BULK_TRANSFER,
            reference_line_id=origin.id,
            notes=data.notes,
        ))
    await db.commit()
    return await get_flow_transaction(db, tx.id)


async def confirm_flow_transaction(
    db: AsyncSession, flow_id: UUID, approved_by: Optional[UUID] = None
) -> MaterialFlowTransaction:
    tx = await get_flow_transaction(db, flow_id)
    if not tx:
        raise ValueError("Flow transaction not found")
    if tx.flow_type == FlowType.REVERSAL:
        raise ValueError(
            "Generic REVERSAL transactions cannot be posted without inventory-aware correction events."
        )
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
    raise ValueError(
        "Generic reversal is unavailable because it does not post matching stock, reservation, WIP, genealogy, and accounting events. "
        "Use the linked issue-line return or scrap workflow where supported; other corrections remain blocked until their atomic workflow is available."
    )


# ── Reservation ───────────────────────────────────────────────────────────────

async def create_reservation(
    db: AsyncSession, data: ReservationCreate, created_by: Optional[UUID] = None
) -> MaterialReservation:
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == data.production_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status not in {
        ProductionOrderStatus.RELEASED,
        ProductionOrderStatus.IN_PROGRESS,
    }:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PRODUCTION_ORDER_NOT_RELEASED",
                "message": "Materials can only be reserved for a released or in-progress production order.",
                "production_order_id": str(order.id),
                "status": order.status.value,
            },
        )
    if order.source_warehouse_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PRODUCTION_SOURCE_WAREHOUSE_REQUIRED",
                "message": "A production source warehouse is required to reserve materials.",
                "production_order_id": str(order.id),
            },
        )
    source_warehouse = await db.get(Warehouse, order.source_warehouse_id)
    if source_warehouse is None or not source_warehouse.is_active:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PRODUCTION_SOURCE_WAREHOUSE_UNAVAILABLE",
                "message": "The production source warehouse is missing or inactive.",
                "production_order_id": str(order.id),
            },
        )
    if data.work_order_id is not None:
        work_order_result = await db.execute(
            select(WorkOrder).where(WorkOrder.id == data.work_order_id)
        )
        work_order = work_order_result.scalar_one_or_none()
        if work_order is None or work_order.production_order_id != order.id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "RESERVATION_WORK_ORDER_MISMATCH",
                    "message": "The selected work order must belong to the production order.",
                    "production_order_id": str(order.id),
                    "work_order_id": str(data.work_order_id),
                },
            )
    if not data.lines:
        raise HTTPException(status_code=422, detail="At least one material line is required")

    requested: list[tuple[object, Material, Decimal, Optional[StorageLocation]]] = []
    stocks_by_material: dict[UUID, list[Stock]] = {}
    staging_locations: dict[Optional[UUID], Optional[StorageLocation]] = {}
    use_date = order.scheduled_start.date() if order.scheduled_start else date.today()
    for input_line in data.lines:
        if (
            input_line.item_type.strip().lower() != "material"
            or input_line.material_id is None
            or input_line.product_id is not None
        ):
            raise HTTPException(
                status_code=422,
                detail="Production reservations must reference exactly one material per line.",
            )
        if input_line.warehouse_id != order.source_warehouse_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "RESERVATION_SOURCE_WAREHOUSE_MISMATCH",
                    "message": "A production reservation must use the order's source warehouse.",
                    "production_order_id": str(order.id),
                    "source_warehouse_id": str(order.source_warehouse_id),
                },
            )
        quantity = Decimal(input_line.quantity_required)
        if not quantity.is_finite() or quantity <= 0:
            raise HTTPException(status_code=422, detail="Reservation quantity must be greater than zero")
        if input_line.quality_status_required != QualityStatus.RELEASED:
            raise HTTPException(
                status_code=422,
                detail="Production reservations require released-quality material.",
            )

        material_result = await db.execute(
            select(Material).where(Material.id == input_line.material_id)
        )
        material = material_result.scalar_one_or_none()
        if material is None or not material.is_active:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "RESERVATION_MATERIAL_UNAVAILABLE",
                    "message": "The requested material is missing or inactive.",
                    "material_id": str(input_line.material_id),
                },
            )
        from_uom = str(getattr(input_line.uom, "value", input_line.uom) or "").strip().upper()
        to_uom = str(getattr(material.uom, "value", material.uom) or "").strip().upper()
        try:
            material_quantity = await convert_uom(db, quantity, from_uom, to_uom)
        except (HTTPException, MultipleResultsFound) as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "RESERVATION_MATERIAL_UOM_UNRESOLVED",
                    "message": f"No unique unit conversion is available for material '{material.name}'.",
                    "material_id": str(material.id),
                    "from_uom": from_uom,
                    "to_uom": to_uom,
                },
            ) from exc
        required = Decimal(material_quantity).quantize(
            Decimal("0.001"), rounding=ROUND_CEILING
        )
        staging_id = input_line.staging_location_id
        if staging_id not in staging_locations:
            staging_locations[staging_id] = await _resolve_staging_location(
                db, order.source_warehouse_id, staging_id
            )
        requested.append((input_line, material, required, staging_locations[staging_id]))

    material_ids = sorted({material.id for _, material, _, _ in requested}, key=str)
    stocks_by_material = {material_id: [] for material_id in material_ids}
    stock_result = await db.execute(
        select(Stock)
        .options(selectinload(Stock.lot))
        .where(
            Stock.stock_type == StockType.MATERIAL,
            Stock.warehouse_id == order.source_warehouse_id,
            Stock.material_id.in_(material_ids),
            Stock.is_blocked.is_(False),
        )
        .order_by(Stock.material_id, Stock.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    for stock in stock_result.scalars().all():
        stocks_by_material[stock.material_id].append(stock)

    all_stocks = [stock for stocks in stocks_by_material.values() for stock in stocks]
    lot_ids = sorted({stock.lot_id for stock in all_stocks if stock.lot_id is not None})
    source_location_ids = sorted(
        {stock.location_id for stock in all_stocks if stock.location_id is not None}, key=str
    )
    source_locations: dict[UUID, StorageLocation] = {}
    if source_location_ids:
        location_result = await db.execute(
            select(StorageLocation)
            .options(selectinload(StorageLocation.zone))
            .where(StorageLocation.id.in_(source_location_ids))
            .order_by(StorageLocation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        source_locations = {
            location.id: location for location in location_result.scalars().all()
        }
    quality_statuses: dict[UUID, LotQualityStatus] = {}
    if lot_ids:
        quality_result = await db.execute(
            select(LotQualityStatus)
            .where(LotQualityStatus.lot_id.in_(lot_ids))
            .order_by(LotQualityStatus.lot_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        quality_statuses = {
            status.lot_id: status for status in quality_result.scalars().all()
        }

    remaining_by_stock: dict[UUID, Decimal] = {}
    eligible_by_material: dict[UUID, list[Stock]] = {}
    for material_id, stocks in stocks_by_material.items():
        eligible = []
        for stock in stocks:
            if stock.location_id is not None:
                location = source_locations.get(stock.location_id)
                zone = location.zone if location is not None else None
                if (
                    location is None
                    or not location.is_active
                    or location.is_blocked
                    or zone is None
                    or not zone.is_active
                    or zone.warehouse_id != order.source_warehouse_id
                    or zone.zone_type not in {ZoneType.RAW_MATERIAL, ZoneType.STAGING}
                ):
                    continue
            if stock.lot_id is not None:
                lot = stock.lot
                quality_status = quality_statuses.get(stock.lot_id)
                if (
                    lot is None
                    or lot.material_id != material_id
                    or lot.is_quarantine
                    or (lot.expiry_date is not None and lot.expiry_date < use_date)
                    or quality_status is None
                    or quality_status.hold_flag
                    or quality_status.quarantine_flag
                    or quality_status.release_status != ReleaseStatus.RELEASED
                    or not quality_status.fefo_eligible
                ):
                    continue
            on_hand = Decimal(stock.quantity_on_hand or 0)
            reserved = Decimal(stock.quantity_reserved or 0)
            available = Decimal(stock.quantity_available or 0)
            if on_hand < 0 or reserved < 0 or available < 0 or on_hand != reserved + available:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "STOCK_BALANCE_MISMATCH",
                        "message": "Stock on-hand, reserved, and available quantities are inconsistent.",
                        "stock_id": str(stock.id),
                    },
                )
            eligible.append(stock)
            remaining_by_stock[stock.id] = available
        eligible.sort(key=_fefo_stock_sort_key)
        eligible_by_material[material_id] = eligible

    allocations: list[
        tuple[object, Material, Stock, Decimal, Optional[StorageLocation], Optional[str]]
    ] = []
    for input_line, material, required, staging_location in requested:
        remaining = required
        candidates = eligible_by_material[material.id]
        available_candidates = [
            stock
            for stock in candidates
            if remaining_by_stock.get(stock.id, Decimal(0)) > 0
        ]
        recommended_stock = available_candidates[0] if available_candidates else None
        recommended_lot_number = (
            recommended_stock.lot.lot_number
            if recommended_stock is not None and recommended_stock.lot is not None
            else None
        )
        if input_line.lot_id is not None and not any(
            stock.lot_id == input_line.lot_id for stock in candidates
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_RESERVATION_LOT_UNAVAILABLE",
                    "message": "The requested lot is not an eligible lot with available stock for this material and warehouse.",
                    "material_id": str(material.id),
                    "lot_id": str(input_line.lot_id),
                },
            )
        if input_line.lot_fixed and input_line.lot_id is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_RESERVATION_FIXED_LOT_REQUIRED",
                    "message": "A fixed lot selection requires a lot ID.",
                    "material_id": str(material.id),
                },
            )
        if input_line.lot_fixed:
            fixed_candidates = [
                stock for stock in candidates if stock.lot_id == input_line.lot_id
            ]
            if not fixed_candidates or sum(
                (remaining_by_stock.get(stock.id, Decimal(0)) for stock in fixed_candidates),
                Decimal(0),
            ) < required:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "MATERIAL_RESERVATION_FIXED_LOT_UNAVAILABLE",
                        "message": "The selected fixed lot is not eligible or does not have enough available quantity.",
                        "material_id": str(material.id),
                        "lot_id": str(input_line.lot_id),
                    },
                )
            if recommended_stock is None or recommended_stock.lot_id != input_line.lot_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "MATERIAL_RESERVATION_NON_FEFO_LOT",
                        "message": "The selected lot is not the earliest-expiry eligible lot. Use the FEFO recommendation or remove the fixed-lot selection.",
                        "material_id": str(material.id),
                        "selected_lot_id": str(input_line.lot_id),
                        "recommended_lot_id": str(recommended_stock.lot_id)
                        if recommended_stock and recommended_stock.lot_id
                        else None,
                        "recommended_lot_number": recommended_lot_number,
                        "recommended_expiry_date": recommended_stock.lot.expiry_date.isoformat()
                        if recommended_stock and recommended_stock.lot and recommended_stock.lot.expiry_date
                        else None,
                    },
                )
            candidates = fixed_candidates
        for stock in candidates:
            available = remaining_by_stock.get(stock.id, Decimal(0))
            allocation = min(available, remaining)
            if allocation <= 0:
                continue
            allocations.append(
                (
                    input_line,
                    material,
                    stock,
                    allocation,
                    staging_location,
                    recommended_lot_number,
                )
            )
            remaining_by_stock[stock.id] = available - allocation
            remaining -= allocation
            if remaining == 0:
                break
        if remaining > 0:
            available = required - remaining
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "MATERIAL_RESERVATION_SHORTAGE",
                    "message": f"Insufficient released stock for material '{material.name}'.",
                    "production_order_id": str(order.id),
                    "material_id": str(material.id),
                    "required_quantity": str(required),
                    "available_quantity": str(available),
                },
            )

    res = MaterialReservation(
        reservation_no=_res_no(),
        production_order_id=data.production_order_id,
        work_order_id=data.work_order_id,
        status=ReservationStatus.ACTIVE,
        expiry_datetime=data.expiry_datetime,
        created_by=created_by,
        notes=data.notes,
        lines=[],
    )
    db.add(res)
    await db.flush()
    for line_no, (
        input_line,
        material,
        stock,
        quantity,
        staging_location,
        fefo_lot_candidate,
    ) in enumerate(allocations, start=1):
        stock.quantity_reserved = Decimal(stock.quantity_reserved or 0) + quantity
        stock.quantity_available = Decimal(stock.quantity_on_hand or 0) - stock.quantity_reserved
        if stock.quantity_available < 0:
            raise HTTPException(
                status_code=409,
                detail="Inventory availability changed while the reservation was being applied.",
            )
        line = MaterialReservationLine(
            reservation_id=res.id,
            line_no=line_no,
            item_type="material",
            material_id=material.id,
            product_id=None,
            lot_id=stock.lot_id,
            warehouse_id=stock.warehouse_id,
            quantity_required=quantity,
            quantity_reserved=quantity,
            quantity_issued=Decimal(0),
            uom=str(getattr(material.uom, "value", material.uom)),
            quality_status_required=QualityStatus.RELEASED,
            source_stock_id=stock.id,
            source_location_id=stock.location_id,
            staging_location_id=staging_location.id if staging_location else None,
            fefo_lot_candidate=fefo_lot_candidate,
            lot_fixed=input_line.lot_fixed,
            notes=input_line.notes,
        )
        res.lines.append(line)
    await db.flush()
    loaded = await get_reservation(db, res.id)
    return loaded or res


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


async def generate_material_pick_list(
    db: AsyncSession, reservation_id: UUID
) -> Optional[MaterialPickListOut]:
    result = await db.execute(
        select(MaterialReservation)
        .options(
            selectinload(MaterialReservation.lines).selectinload(MaterialReservationLine.material),
            selectinload(MaterialReservation.lines).selectinload(MaterialReservationLine.lot),
            selectinload(MaterialReservation.lines).selectinload(MaterialReservationLine.source_location),
            selectinload(MaterialReservation.lines).selectinload(MaterialReservationLine.staging_location),
            selectinload(MaterialReservation.production_order).selectinload(
                ProductionOrder.source_warehouse
            ),
        )
        .where(MaterialReservation.id == reservation_id)
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        return None
    order = reservation.production_order
    if order is None:
        raise HTTPException(status_code=409, detail="Reservation has no production-order record")
    if order.status not in {
        ProductionOrderStatus.RELEASED,
        ProductionOrderStatus.IN_PROGRESS,
    }:
        raise HTTPException(
            status_code=409,
            detail="A pick list is available only while its production order is released or in progress.",
        )
    if reservation.status not in {
        ReservationStatus.ACTIVE,
        ReservationStatus.PARTIALLY_ISSUED,
    }:
        raise HTTPException(
            status_code=409,
            detail="A pick list is available only for an active reservation.",
        )
    warehouse = order.source_warehouse
    if warehouse is None or not warehouse.is_active:
        raise HTTPException(status_code=409, detail="The reservation source warehouse is unavailable")

    grouped: dict[tuple[UUID, UUID | None, UUID, UUID | None, UUID | None, str], dict] = {}
    for line in reservation.lines:
        if line.warehouse_id != order.source_warehouse_id:
            raise HTTPException(
                status_code=409,
                detail="Reservation contains a line outside the production order source warehouse.",
            )
        if line.material_id is None or line.material is None:
            raise HTTPException(status_code=409, detail="Reservation line has no material identity")
        if line.lot_id is not None and line.lot is None:
            raise HTTPException(status_code=409, detail="Reservation line references a missing lot")
        outstanding = Decimal(line.quantity_reserved or 0) - Decimal(line.quantity_issued or 0)
        if outstanding < 0:
            raise HTTPException(status_code=409, detail="Issued quantity exceeds the reserved quantity")
        if outstanding == 0:
            continue
        source_location = line.source_location
        staging_location = line.staging_location
        key = (
            line.material_id,
            line.lot_id,
            line.warehouse_id,
            line.source_location_id,
            line.staging_location_id,
            line.uom,
        )
        item = grouped.setdefault(
            key,
            {
                "reservation_line_ids": [],
                "line_no": line.line_no,
                "material": line.material,
                "lot": line.lot,
                "source_location": source_location,
                "staging_location": staging_location,
                "warehouse_id": line.warehouse_id,
                "quantity_to_pick": Decimal(0),
                "uom": line.uom,
            },
        )
        item["reservation_line_ids"].append(line.id)
        item["line_no"] = min(item["line_no"], line.line_no)
        item["quantity_to_pick"] += outstanding

    if not grouped:
        raise HTTPException(status_code=409, detail="Reservation has no outstanding quantity to pick")

    lines = []
    for item in sorted(grouped.values(), key=lambda value: value["line_no"]):
        material = item["material"]
        lot = item["lot"]
        lines.append(
            MaterialPickListLineOut(
                reservation_line_ids=item["reservation_line_ids"],
                line_no=item["line_no"],
                material_id=material.id,
                material_code=material.code,
                material_name=material.name,
                lot_id=lot.id if lot else None,
                lot_number=lot.lot_number if lot else None,
                expiry_date=lot.expiry_date if lot else None,
                warehouse_id=item["warehouse_id"],
                source_location_id=item["source_location"].id if item["source_location"] else None,
                source_location_code=item["source_location"].code if item["source_location"] else None,
                staging_location_id=item["staging_location"].id if item["staging_location"] else None,
                staging_location_code=item["staging_location"].code if item["staging_location"] else None,
                quantity_to_pick=item["quantity_to_pick"],
                uom=item["uom"],
            )
        )
    return MaterialPickListOut(
        reservation_id=reservation.id,
        reservation_no=reservation.reservation_no,
        reservation_status=reservation.status,
        production_order_id=order.id,
        production_order_no=order.order_no,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        generated_at=_now(),
        lines=lines,
    )


async def _release_reservation_balance(
    db: AsyncSession, reservation: MaterialReservation
) -> None:
    if reservation.status not in {
        ReservationStatus.ACTIVE,
        ReservationStatus.PARTIALLY_ISSUED,
    }:
        raise HTTPException(
            status_code=422,
            detail=f"A {reservation.status.value.lower()} reservation cannot be cancelled.",
        )

    release_by_stock_id: dict[UUID, Decimal] = {}
    legacy_by_identity: dict[tuple[UUID, UUID, UUID | None, UUID | None], Decimal] = {}
    for line in reservation.lines:
        outstanding = Decimal(line.quantity_reserved or 0) - Decimal(line.quantity_issued or 0)
        if outstanding < 0:
            raise HTTPException(
                status_code=409,
                detail="Reservation issued quantity exceeds its reserved quantity.",
            )
        if outstanding == 0:
            continue
        if line.material_id is None:
            raise HTTPException(
                status_code=409,
                detail="Reservation line has no material identity and cannot release stock safely.",
            )
        if line.source_stock_id is not None:
            release_by_stock_id[line.source_stock_id] = (
                release_by_stock_id.get(line.source_stock_id, Decimal(0)) + outstanding
            )
        else:
            key = (line.material_id, line.warehouse_id, line.lot_id, line.source_location_id)
            legacy_by_identity[key] = legacy_by_identity.get(key, Decimal(0)) + outstanding

    for (material_id, warehouse_id, lot_id, source_location_id), quantity_to_release in sorted(
        legacy_by_identity.items(),
        key=lambda item: tuple(str(value or "") for value in item[0]),
    ):
        lot_clause = Stock.lot_id.is_(None) if lot_id is None else Stock.lot_id == lot_id
        stock_result = await db.execute(
            select(Stock)
            .where(
                Stock.stock_type == StockType.MATERIAL,
                Stock.material_id == material_id,
                Stock.warehouse_id == warehouse_id,
                lot_clause,
                Stock.location_id.is_(None)
                if source_location_id is None
                else Stock.location_id == source_location_id,
            )
            .order_by(Stock.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        stocks = list(stock_result.scalars().all())
        if len(stocks) != 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "RESERVATION_SOURCE_STOCK_UNRESOLVED",
                    "message": "A legacy reservation without an exact stock link can be released only when its source identity matches exactly one stock row.",
                    "material_id": str(material_id),
                    "warehouse_id": str(warehouse_id),
                    "lot_id": str(lot_id) if lot_id else None,
                    "source_location_id": str(source_location_id) if source_location_id else None,
                    "matching_stock_rows": len(stocks),
                },
            )
        stock_id = stocks[0].id
        release_by_stock_id[stock_id] = release_by_stock_id.get(stock_id, Decimal(0)) + quantity_to_release

    stock_ids = set(release_by_stock_id)
    stock_result = await db.execute(
        select(Stock)
        .where(Stock.id.in_(stock_ids))
        .order_by(Stock.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    stocks_by_id = {stock.id: stock for stock in stock_result.scalars().all()}
    if set(stocks_by_id) != stock_ids:
        raise HTTPException(
            status_code=409,
            detail="A reservation source-stock row no longer exists; its balance cannot be released safely.",
        )
    stock_release_plan: list[tuple[Stock, Decimal]] = []
    for stock_id, release in release_by_stock_id.items():
        stock = stocks_by_id[stock_id]
        on_hand = Decimal(stock.quantity_on_hand or 0)
        reserved = Decimal(stock.quantity_reserved or 0)
        available = Decimal(stock.quantity_available or 0)
        if on_hand < 0 or reserved < release or available < 0 or on_hand != reserved + available:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "RESERVATION_STOCK_BALANCE_MISMATCH",
                    "message": "The stock row does not contain a consistent outstanding reservation balance.",
                    "stock_id": str(stock.id),
                    "release_quantity": str(release),
                },
            )
        stock_release_plan.append((stock, release))
    for stock, released in stock_release_plan:
        stock.quantity_reserved = Decimal(stock.quantity_reserved or 0) - released
        stock.quantity_available = Decimal(stock.quantity_on_hand or 0) - stock.quantity_reserved
    reservation.status = ReservationStatus.CANCELLED


async def cancel_reservation(db: AsyncSession, res_id: UUID) -> MaterialReservation:
    order_id_result = await db.execute(
        select(MaterialReservation.production_order_id).where(MaterialReservation.id == res_id)
    )
    order_id = order_id_result.scalar_one_or_none()
    if order_id is None:
        raise ValueError("Reservation not found")
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=409, detail="Reservation production order is unavailable")
    result = await db.execute(
        select(MaterialReservation)
        .options(selectinload(MaterialReservation.lines))
        .where(MaterialReservation.id == res_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    res = result.scalar_one_or_none()
    if not res:
        raise ValueError("Reservation not found")
    await _release_reservation_balance(db, res)
    await db.flush()
    return res


async def cancel_reservations_for_order(db: AsyncSession, production_order_id: UUID) -> None:
    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == production_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order_result.scalar_one_or_none() is None:
        return
    result = await db.execute(
        select(MaterialReservation)
        .options(selectinload(MaterialReservation.lines))
        .where(
            MaterialReservation.production_order_id == production_order_id,
            MaterialReservation.status.in_(
                {ReservationStatus.ACTIVE, ReservationStatus.PARTIALLY_ISSUED}
            ),
        )
        .order_by(MaterialReservation.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    for reservation in result.scalars().all():
        await _release_reservation_balance(db, reservation)
    await db.flush()


# ── Consumption ───────────────────────────────────────────────────────────────

async def record_consumption(
    db: AsyncSession, data: ConsumptionCreate, operator_id: UUID
) -> ProductionConsumption:
    idempotency_key = data.idempotency_key.strip()
    quantity = Decimal(data.quantity_consumed)
    if operator_id is None:
        raise HTTPException(status_code=401, detail="An authenticated operator is required.")
    if len(idempotency_key) < 16:
        raise HTTPException(status_code=422, detail="Idempotency key must contain at least 16 non-whitespace characters.")
    if not quantity.is_finite() or quantity <= 0:
        raise HTTPException(status_code=422, detail="Consumed quantity must be finite and greater than zero.")
    if quantity != quantity.quantize(Decimal("0.001")):
        raise HTTPException(status_code=422, detail="Consumed quantity may not exceed inventory precision of 0.001.")

    await lock_inventory_identity(db, f"material-consumption-idempotency:{idempotency_key}")
    existing_result = await db.execute(
        select(ProductionConsumption)
        .where(ProductionConsumption.idempotency_key == idempotency_key)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        if (
            existing.operator_id != operator_id
            or existing.production_order_id != data.production_order_id
            or existing.flow_line_id != data.flow_line_id
            or Decimal(existing.quantity_consumed) != quantity
            or existing.work_order_id != data.work_order_id
            or existing.stage_id != data.stage_id
            or existing.notes != data.notes
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "MATERIAL_CONSUMPTION_IDEMPOTENCY_KEY_REUSED",
                    "message": "This idempotency key already belongs to a different consumption request.",
                },
            )
        return existing

    order_result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.id == data.production_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Production order not found")
    if order.status != ProductionOrderStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_CONSUMPTION_ORDER_NOT_IN_PROGRESS",
                "message": "Actual material consumption can be recorded only for an in-progress production order.",
                "status": order.status.value,
            },
        )

    if data.work_order_id is not None:
        work_order_result = await db.execute(
            select(WorkOrder)
            .where(WorkOrder.id == data.work_order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        work_order = work_order_result.scalar_one_or_none()
        if work_order is None or work_order.production_order_id != order.id:
            raise HTTPException(status_code=422, detail="Work order does not belong to the production order.")
        if work_order.status != WorkOrderStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail="Consumption requires an in-progress work order.")

    flow_result = await db.execute(
        select(MaterialFlowLine, MaterialFlowTransaction)
        .join(MaterialFlowTransaction, MaterialFlowTransaction.id == MaterialFlowLine.transaction_id)
        .where(MaterialFlowLine.id == data.flow_line_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    flow_pair = flow_result.one_or_none()
    if flow_pair is None:
        raise HTTPException(status_code=404, detail="Issued material line not found")
    issue_line, issue_transaction = flow_pair
    if (
        issue_transaction.production_order_id != order.id
        or issue_transaction.flow_type not in {FlowType.RAW_ISSUE, FlowType.PKG_ISSUE}
        or issue_transaction.status != FlowStatus.POSTED
        or issue_line.issue_flag is not True
        or issue_line.item_type.strip().lower() != "material"
        or issue_line.material_id is None
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "MATERIAL_CONSUMPTION_ISSUE_LINE_INVALID",
                "message": "Consumption must reference a posted material issue line for the same production order.",
                "flow_line_id": str(issue_line.id),
            },
        )
    material_type_result = await db.execute(
        select(Material.material_type).where(Material.id == issue_line.material_id)
    )
    material_type = material_type_result.scalar_one_or_none()
    if material_type is None or (issue_transaction.flow_type == FlowType.PKG_ISSUE) != (material_type == MaterialType.PACKAGING):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "MATERIAL_CONSUMPTION_ISSUE_TYPE_MISMATCH",
                "message": "Packaging consumption must reference a packaging issue line, and packaging cannot be consumed as raw material.",
                "flow_line_id": str(issue_line.id),
            },
        )
    if order.source_warehouse_id is None or issue_line.source_warehouse_id != order.source_warehouse_id:
        raise HTTPException(status_code=409, detail="Issued line is outside the production source warehouse.")
    if issue_transaction.work_order_id is not None and data.work_order_id != issue_transaction.work_order_id:
        raise HTTPException(
            status_code=422,
            detail="Consumption work order must match the work order recorded by the material issue.",
        )

    legacy_result = await db.execute(
        select(func.count(ProductionConsumption.id)).where(
            ProductionConsumption.production_order_id == order.id,
            ProductionConsumption.flow_line_id.is_(None),
            ProductionConsumption.material_id == issue_line.material_id,
            (
                ProductionConsumption.quantity_consumed
                + ProductionConsumption.quantity_returned
                + ProductionConsumption.quantity_scrapped
            )
            > 0,
        )
    )
    if legacy_result.scalar_one() > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "MATERIAL_CONSUMPTION_LEGACY_ISSUE_UNLINKED",
                "message": "Existing consumption for this material is not linked to an exact issue line, so remaining issued quantity cannot be established safely.",
                "production_order_id": str(order.id),
                "material_id": str(issue_line.material_id),
            },
        )

    issued_quantity = Decimal(issue_line.quantity)
    prior_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    ProductionConsumption.quantity_consumed
                    + ProductionConsumption.quantity_returned
                    + ProductionConsumption.quantity_scrapped
                ),
                0,
            )
        ).where(ProductionConsumption.flow_line_id == issue_line.id)
    )
    already_settled = Decimal(str(prior_result.scalar() or 0))
    outstanding = issued_quantity - already_settled
    if outstanding <= 0 or quantity > outstanding:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "MATERIAL_CONSUMPTION_EXCEEDS_ISSUED_QUANTITY",
                "message": "Consumed quantity must not exceed the issued line's remaining unconsumed quantity.",
                "flow_line_id": str(issue_line.id),
                "outstanding_quantity": str(max(outstanding, Decimal(0))),
                "requested_quantity": str(quantity),
            },
        )

    consumption = ProductionConsumption(
        production_order_id=order.id,
        flow_line_id=issue_line.id,
        idempotency_key=idempotency_key,
        work_order_id=data.work_order_id,
        item_type=issue_line.item_type,
        material_id=issue_line.material_id,
        product_id=issue_line.product_id,
        lot_id=issue_line.lot_id,
        quantity_issued=issued_quantity,
        quantity_consumed=quantity,
        quantity_returned=Decimal("0"),
        quantity_scrapped=Decimal("0"),
        quantity_variance=outstanding - quantity,
        uom=issue_line.uom,
        stage_id=data.stage_id,
        consumed_at=_now(),
        operator_id=operator_id,
        notes=data.notes,
    )
    db.add(consumption)
    await db.flush()
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
            MaterialFlowLine.issue_flag.is_(True),
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
    issued_result = await db.execute(
        select(func.coalesce(func.sum(MaterialFlowLine.quantity), 0))
        .join(
            MaterialFlowTransaction,
            MaterialFlowTransaction.id == MaterialFlowLine.transaction_id,
        )
        .where(
            MaterialFlowTransaction.production_order_id == production_order_id,
            MaterialFlowTransaction.status == FlowStatus.POSTED,
            MaterialFlowTransaction.flow_type.in_((FlowType.RAW_ISSUE, FlowType.PKG_ISSUE)),
            MaterialFlowLine.issue_flag.is_(True),
        )
    )
    total_issued = _D(str(issued_result.scalar() or 0))
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
            MaterialFlowLine.issue_flag.is_(True),
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
