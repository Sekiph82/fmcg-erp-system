"""Co-Packing / Toll Manufacturing endpoints.

Prefix: /api/v1/copacking
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.copacking import (
    CoPackingContract, CoPackingRun, CustomerTool,
    ContractType, CoPackingContractStatus, ToolStatus,
)

router = APIRouter()
_SEQ = 0


def _ref(prefix: str) -> str:
    global _SEQ
    _SEQ += 1
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d')}-{_SEQ:04d}"


def _contract_out(c: CoPackingContract) -> dict:
    return {
        "id": str(c.id), "contract_ref": c.contract_ref,
        "contract_type": c.contract_type, "customer_name": c.customer_name,
        "brand_name": c.brand_name, "product_description": c.product_description,
        "sku_count": c.sku_count,
        "start_date": str(c.start_date), "end_date": str(c.end_date) if c.end_date else None,
        "minimum_order_qty": float(c.minimum_order_qty) if c.minimum_order_qty else None,
        "moq_uom": c.moq_uom,
        "processing_fee_per_unit": float(c.processing_fee_per_unit) if c.processing_fee_per_unit else None,
        "currency": c.currency, "status": c.status,
        "quality_standards": c.quality_standards, "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


def _run_out(r: CoPackingRun) -> dict:
    return {
        "id": str(r.id), "run_ref": r.run_ref,
        "contract_id": str(r.contract_id), "run_date": str(r.run_date),
        "qty_planned": float(r.qty_planned) if r.qty_planned else None,
        "qty_produced": float(r.qty_produced) if r.qty_produced else None,
        "uom": r.uom, "batch_ref": r.batch_ref,
        "processing_fee_total": float(r.processing_fee_total) if r.processing_fee_total else None,
        "materials_supplied_by_customer": r.materials_supplied_by_customer,
        "quality_passed": r.quality_passed, "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


def _tool_out(t: CustomerTool) -> dict:
    life_pct = None
    if t.units_produced is not None and t.max_units_life and t.max_units_life > 0:
        life_pct = round(t.units_produced / t.max_units_life * 100, 1)
    return {
        "id": str(t.id), "tool_ref": t.tool_ref, "customer_name": t.customer_name,
        "tool_name": t.tool_name, "tool_type": t.tool_type,
        "serial_number": t.serial_number, "status": t.status,
        "units_produced": t.units_produced,
        "max_units_life": t.max_units_life, "life_used_pct": life_pct,
        "depreciation_per_unit": float(t.depreciation_per_unit) if t.depreciation_per_unit else None,
        "storage_location": t.storage_location, "notes": t.notes,
        "date_received": str(t.date_received) if t.date_received else None,
        "created_at": t.created_at.isoformat() if t.created_at else "",
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContractIn(BaseModel):
    customer_name: str
    contract_type: ContractType = ContractType.COPACKING
    brand_name: Optional[str] = None
    product_description: Optional[str] = None
    sku_count: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    minimum_order_qty: Optional[float] = None
    moq_uom: str = "KG"
    processing_fee_per_unit: Optional[float] = None
    currency: str = "KES"
    quality_standards: Optional[str] = None
    notes: Optional[str] = None


class RunIn(BaseModel):
    contract_id: str
    run_date: date
    qty_planned: Optional[float] = None
    qty_produced: Optional[float] = None
    uom: str = "KG"
    batch_ref: Optional[str] = None
    materials_supplied_by_customer: bool = False
    quality_passed: Optional[bool] = None
    notes: Optional[str] = None


class ToolIn(BaseModel):
    customer_name: str
    tool_name: str
    contract_id: Optional[str] = None
    tool_description: Optional[str] = None
    tool_type: Optional[str] = None
    serial_number: Optional[str] = None
    date_received: Optional[date] = None
    max_units_life: Optional[int] = None
    depreciation_per_unit: Optional[float] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


# ── Contracts ─────────────────────────────────────────────────────────────────

@router.post("/contracts", status_code=201)
async def create_contract(payload: ContractIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    c = CoPackingContract(contract_ref=_ref("CPC"), **payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _contract_out(c)


@router.get("/contracts")
async def list_contracts(
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CoPackingContract)
    if status:
        q = q.where(CoPackingContract.status == status)
    if contract_type:
        q = q.where(CoPackingContract.contract_type == contract_type)
    q = q.order_by(desc(CoPackingContract.start_date)).limit(limit)
    result = await db.execute(q)
    return [_contract_out(c) for c in result.scalars().all()]


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(CoPackingContract)
        .options(selectinload(CoPackingContract.runs), selectinload(CoPackingContract.tools))
        .where(CoPackingContract.id == uuid.UUID(contract_id))
    )
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")
    out = _contract_out(c)
    out["runs"] = [_run_out(r) for r in sorted(c.runs, key=lambda x: x.run_date, reverse=True)]
    out["tools"] = [_tool_out(t) for t in c.tools]
    return out


@router.patch("/contracts/{contract_id}/status")
async def update_contract_status(
    contract_id: str,
    status: CoPackingContractStatus,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(CoPackingContract).where(CoPackingContract.id == uuid.UUID(contract_id)))
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")
    c.status = status
    await db.commit()
    return {"contract_id": contract_id, "status": status}


# ── Production Runs ───────────────────────────────────────────────────────────

@router.post("/runs", status_code=201)
async def create_run(payload: RunIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    # Look up processing fee from contract
    c_r = await db.execute(select(CoPackingContract).where(CoPackingContract.id == uuid.UUID(payload.contract_id)))
    contract = c_r.scalar_one_or_none()

    fee_total = None
    if contract and contract.processing_fee_per_unit and payload.qty_produced:
        fee_total = float(contract.processing_fee_per_unit) * payload.qty_produced

    run = CoPackingRun(
        run_ref=_ref("CPR"),
        **{k: v for k, v in payload.model_dump().items() if k != "contract_id"},
        contract_id=uuid.UUID(payload.contract_id),
        processing_fee_total=fee_total,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return _run_out(run)


@router.get("/runs")
async def list_runs(
    contract_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CoPackingRun)
    if contract_id:
        q = q.where(CoPackingRun.contract_id == uuid.UUID(contract_id))
    q = q.order_by(desc(CoPackingRun.run_date)).limit(limit)
    result = await db.execute(q)
    return [_run_out(r) for r in result.scalars().all()]


# ── Customer Tools ────────────────────────────────────────────────────────────

@router.post("/tools", status_code=201)
async def register_tool(payload: ToolIn, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    t = CustomerTool(
        tool_ref=_ref("TL"),
        **{k: v for k, v in payload.model_dump().items() if k != "contract_id"},
        contract_id=uuid.UUID(payload.contract_id) if payload.contract_id else None,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _tool_out(t)


@router.get("/tools")
async def list_tools(
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CustomerTool)
    if status:
        q = q.where(CustomerTool.status == status)
    if customer_name:
        q = q.where(CustomerTool.customer_name.ilike(f"%{customer_name}%"))
    q = q.order_by(CustomerTool.customer_name).limit(limit)
    result = await db.execute(q)
    return [_tool_out(t) for t in result.scalars().all()]


@router.post("/tools/{tool_id}/log-usage")
async def log_tool_usage(
    tool_id: str,
    units_used: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(select(CustomerTool).where(CustomerTool.id == uuid.UUID(tool_id)))
    tool = r.scalar_one_or_none()
    if not tool:
        raise HTTPException(404, "Tool not found")
    tool.units_produced += units_used
    if tool.max_units_life and tool.units_produced >= tool.max_units_life:
        tool.status = ToolStatus.RETIRED
    await db.commit()
    return _tool_out(tool)


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def copacking_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    active_r = await db.execute(
        select(func.count()).select_from(CoPackingContract).where(CoPackingContract.status == CoPackingContractStatus.ACTIVE)
    )
    total_runs_r = await db.execute(select(func.count()).select_from(CoPackingRun))
    total_tools_r = await db.execute(
        select(func.count()).select_from(CustomerTool).where(CustomerTool.status == ToolStatus.ACTIVE)
    )
    near_eol_r = await db.execute(
        select(func.count()).select_from(CustomerTool).where(
            CustomerTool.max_units_life.isnot(None),
            CustomerTool.units_produced >= CustomerTool.max_units_life * 0.9,
            CustomerTool.status == ToolStatus.ACTIVE,
        )
    )
    return {
        "active_contracts": active_r.scalar() or 0,
        "total_production_runs": total_runs_r.scalar() or 0,
        "active_customer_tools": total_tools_r.scalar() or 0,
        "tools_near_end_of_life": near_eol_r.scalar() or 0,
    }
