from __future__ import annotations

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.models.inventory import SerialNumber, SerialMovement, SerialStatus
from app.schemas.serial_tracking import (
    SerialNumberCreate, SerialBulkCreate, SerialNumberRead,
    SerialTransferRequest, SerialMovementRead,
)

router = APIRouter()


def _build_serial_read(s: SerialNumber) -> SerialNumberRead:
    r = SerialNumberRead.model_validate(s)
    if s.product:
        r.product_name = getattr(s.product, "name", None)
    if s.lot:
        r.lot_number = getattr(s.lot, "lot_number", None)
    if s.warehouse:
        r.warehouse_name = getattr(s.warehouse, "name", None)
    return r


def _build_movement_read(m: SerialMovement) -> SerialMovementRead:
    r = SerialMovementRead.model_validate(m)
    if m.from_warehouse:
        r.from_warehouse_name = getattr(m.from_warehouse, "name", None)
    if m.to_warehouse:
        r.to_warehouse_name = getattr(m.to_warehouse, "name", None)
    if m.moved_by:
        r.moved_by_username = getattr(m.moved_by, "username", None) or getattr(m.moved_by, "email", None)
    return r


_LOAD_OPTS = [
    selectinload(SerialNumber.product),
    selectinload(SerialNumber.lot),
    selectinload(SerialNumber.warehouse),
]


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[SerialNumberRead],
            dependencies=[Depends(require_permission("inventory", "view"))])
async def list_serials(
    product_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
    status: Optional[SerialStatus] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(SerialNumber).options(*_LOAD_OPTS)
    if product_id:
        q = q.where(SerialNumber.product_id == product_id)
    if warehouse_id:
        q = q.where(SerialNumber.warehouse_id == warehouse_id)
    if status:
        q = q.where(SerialNumber.status == status)
    if search:
        q = q.where(SerialNumber.serial_no.ilike(f"%{search}%"))
    q = q.order_by(SerialNumber.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_build_serial_read(s) for s in result.scalars().all()]


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=SerialNumberRead, status_code=201)
async def create_serial(
    body: SerialNumberCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "create")),
):
    existing = (await db.execute(
        select(SerialNumber).where(SerialNumber.serial_no == body.serial_no)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Serial number '{body.serial_no}' already exists")

    serial = SerialNumber(**body.model_dump(), created_by_id=current_user.id)
    db.add(serial)
    await db.flush()
    db.add(SerialMovement(
        serial_id=serial.id,
        from_status=None,
        to_status=SerialStatus.IN_STOCK,
        to_warehouse_id=body.warehouse_id,
        reference_type="RECEIPT",
        moved_by_id=current_user.id,
    ))
    await db.commit()
    result = await db.execute(select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.id == serial.id))
    return _build_serial_read(result.scalar_one())


# ── Bulk Create ───────────────────────────────────────────────────────────────

@router.post("/bulk", response_model=List[SerialNumberRead], status_code=201)
async def bulk_create_serials(
    body: SerialBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "create")),
):
    if not body.serials:
        raise HTTPException(422, "No serials provided")

    serial_nos = [s.serial_no for s in body.serials]
    existing = (await db.execute(
        select(SerialNumber.serial_no).where(SerialNumber.serial_no.in_(serial_nos))
    )).scalars().all()
    if existing:
        raise HTTPException(409, f"Duplicate serial numbers: {', '.join(existing)}")

    created_ids = []
    for item in body.serials:
        serial = SerialNumber(**item.model_dump(), created_by_id=current_user.id)
        db.add(serial)
        await db.flush()
        db.add(SerialMovement(
            serial_id=serial.id,
            from_status=None,
            to_status=SerialStatus.IN_STOCK,
            to_warehouse_id=item.warehouse_id,
            reference_type="RECEIPT",
            moved_by_id=current_user.id,
        ))
        created_ids.append(serial.id)

    await db.commit()
    result = await db.execute(
        select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.id.in_(created_ids))
    )
    return [_build_serial_read(s) for s in result.scalars().all()]


# ── Lookup by serial_no string ────────────────────────────────────────────────

@router.get("/lookup/{serial_no}",
            response_model=SerialNumberRead,
            dependencies=[Depends(require_permission("inventory", "view"))])
async def lookup_serial(serial_no: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.serial_no == serial_no)
    )
    serial = result.scalar_one_or_none()
    if not serial:
        raise HTTPException(404, f"Serial '{serial_no}' not found")
    return _build_serial_read(serial)


# ── Get by ID ─────────────────────────────────────────────────────────────────

@router.get("/{serial_id}",
            response_model=SerialNumberRead,
            dependencies=[Depends(require_permission("inventory", "view"))])
async def get_serial(serial_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.id == serial_id)
    )
    serial = result.scalar_one_or_none()
    if not serial:
        raise HTTPException(404, "Serial not found")
    return _build_serial_read(serial)


# ── Movement History ──────────────────────────────────────────────────────────

@router.get("/{serial_id}/history",
            response_model=List[SerialMovementRead],
            dependencies=[Depends(require_permission("inventory", "view"))])
async def serial_history(serial_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SerialMovement)
        .options(
            selectinload(SerialMovement.from_warehouse),
            selectinload(SerialMovement.to_warehouse),
            selectinload(SerialMovement.moved_by),
        )
        .where(SerialMovement.serial_id == serial_id)
        .order_by(SerialMovement.created_at.asc())
    )
    return [_build_movement_read(m) for m in result.scalars().all()]


# ── Transfer / Status Change ──────────────────────────────────────────────────

@router.post("/{serial_id}/transfer", response_model=SerialNumberRead)
async def transfer_serial(
    serial_id: uuid.UUID,
    body: SerialTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("inventory", "edit")),
):
    result = await db.execute(
        select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.id == serial_id)
    )
    serial = result.scalar_one_or_none()
    if not serial:
        raise HTTPException(404, "Serial not found")

    db.add(SerialMovement(
        serial_id=serial.id,
        from_status=serial.status,
        to_status=body.to_status,
        from_warehouse_id=serial.warehouse_id,
        to_warehouse_id=body.to_warehouse_id,
        reference_type=body.reference_type,
        reference_no=body.reference_no,
        moved_by_id=current_user.id,
    ))
    serial.status = body.to_status
    if body.to_warehouse_id is not None:
        serial.warehouse_id = body.to_warehouse_id

    await db.commit()
    result = await db.execute(
        select(SerialNumber).options(*_LOAD_OPTS).where(SerialNumber.id == serial_id)
    )
    return _build_serial_read(result.scalar_one())
