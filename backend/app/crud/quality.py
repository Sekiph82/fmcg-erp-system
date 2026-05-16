from __future__ import annotations

from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quality import (
    QCParameter, QCInspection, QCTestResult,
    QCType, QCStatus,
)


# ── QC Parameters ─────────────────────────────────────────────────────────────

async def list_parameters(
    db: AsyncSession,
    qc_type: Optional[QCType] = None,
    active_only: bool = True,
    limit: int = 500,
    offset: int = 0,
) -> List[QCParameter]:
    q = select(QCParameter)
    if active_only:
        q = q.where(QCParameter.is_active == True)  # noqa: E712
    if qc_type:
        q = q.where(
            (QCParameter.applicable_types == "ALL") |
            QCParameter.applicable_types.contains(qc_type.value)
        )
    q = q.order_by(QCParameter.name)
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_parameter(db: AsyncSession, param_id: uuid.UUID) -> Optional[QCParameter]:
    result = await db.execute(select(QCParameter).where(QCParameter.id == param_id))
    return result.scalar_one_or_none()


async def create_parameter(db: AsyncSession, data: dict) -> QCParameter:
    p = QCParameter(**data)
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return p


async def update_parameter(db: AsyncSession, param: QCParameter, data: dict) -> QCParameter:
    for k, v in data.items():
        setattr(param, k, v)
    await db.flush()
    return param


# ── QC Inspections ────────────────────────────────────────────────────────────

async def list_inspections(
    db: AsyncSession,
    qc_type: Optional[QCType] = None,
    status: Optional[QCStatus] = None,
    supplier_id: Optional[uuid.UUID] = None,
    material_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[QCInspection]:
    q = select(QCInspection).options(
        selectinload(QCInspection.supplier),
        selectinload(QCInspection.material),
        selectinload(QCInspection.product),
        selectinload(QCInspection.inspector),
        selectinload(QCInspection.test_results),
    )
    if qc_type:
        q = q.where(QCInspection.qc_type == qc_type)
    if status:
        q = q.where(QCInspection.status == status)
    if supplier_id:
        q = q.where(QCInspection.supplier_id == supplier_id)
    if material_id:
        q = q.where(QCInspection.material_id == material_id)
    if product_id:
        q = q.where(QCInspection.product_id == product_id)
    q = q.order_by(QCInspection.inspection_date.desc(), QCInspection.created_at.desc())
    result = await db.execute(q.offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_inspection(db: AsyncSession, inspection_id: uuid.UUID) -> Optional[QCInspection]:
    result = await db.execute(
        select(QCInspection)
        .options(
            selectinload(QCInspection.inspector),
            selectinload(QCInspection.decided_by),
            selectinload(QCInspection.supplier),
            selectinload(QCInspection.material),
            selectinload(QCInspection.product),
            selectinload(QCInspection.lot),
            selectinload(QCInspection.production_order),
            selectinload(QCInspection.test_results).selectinload(QCTestResult.tested_by),
            selectinload(QCInspection.test_results).selectinload(QCTestResult.parameter),
        )
        .where(QCInspection.id == inspection_id)
    )
    return result.scalar_one_or_none()


async def create_inspection(
    db: AsyncSession, data: dict, inspector_id: uuid.UUID
) -> QCInspection:
    insp = QCInspection(**data, inspector_id=inspector_id, status=QCStatus.PENDING)
    db.add(insp)
    await db.flush()
    await db.refresh(insp)
    return insp


async def get_test_result(db: AsyncSession, result_id: uuid.UUID) -> Optional[QCTestResult]:
    result = await db.execute(select(QCTestResult).where(QCTestResult.id == result_id))
    return result.scalar_one_or_none()


async def add_test_result(
    db: AsyncSession,
    inspection: QCInspection,
    data: dict,
    tested_by_id: uuid.UUID,
) -> QCTestResult:
    tr = QCTestResult(inspection_id=inspection.id, tested_by_id=tested_by_id, **data)
    db.add(tr)
    # Move inspection to IN_PROGRESS if still PENDING
    if inspection.status == QCStatus.PENDING:
        inspection.status = QCStatus.IN_PROGRESS
    await db.flush()
    await db.refresh(tr)
    return tr


async def delete_test_result(db: AsyncSession, tr: QCTestResult) -> None:
    await db.delete(tr)
    await db.flush()
