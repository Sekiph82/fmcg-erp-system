"""Procurement Suggestion Engine — API endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.procurement_suggestion import PSUrgencyLevel, PSSuggestionStatus
from app.schemas.procurement_suggestion import (
    ConvertGroupToPRRequest,
    PSDashboard,
    PSGroupOut,
    PSLineOut,
    PSLineUpdate,
    PSRunCreate,
    PSRunOut,
    ShortageReportRow,
    SupplierCompareResult,
    SupplierItemPriceCreate,
    SupplierItemPriceOut,
    SupplierItemPriceUpdate,
    PSAIRecOut,
)
from app.services import procurement_suggestion_service as svc

router = APIRouter()

# No auth middleware yet — user_id is None in dev mode (FK is nullable)
MOCK_USER: Optional[UUID] = None


def _line_out(line) -> PSLineOut:
    out = PSLineOut.model_validate(line)
    if line.material:
        out.material_name = line.material.name
        out.material_code = line.material.code
    if line.supplier:
        out.supplier_name = line.supplier.name
    return out


def _group_out(group) -> PSGroupOut:
    out = PSGroupOut.model_validate(group)
    if group.supplier:
        out.supplier_name = group.supplier.name
    if hasattr(group, "lines"):
        out.lines = [_line_out(l) for l in group.lines]
    return out


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=PSDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Runs ──────────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[PSRunOut])
async def list_runs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    runs = await svc.list_runs(db, skip=skip, limit=limit)
    result = []
    for r in runs:
        out = PSRunOut.model_validate(r)
        if r.warehouse:
            out.warehouse_name = r.warehouse.name
        if r.mrp_run:
            out.mrp_run_no = r.mrp_run.run_no
        result.append(out)
    return result


@router.post("/runs", response_model=PSRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: PSRunCreate,
    db: AsyncSession = Depends(get_db),
):
    run = await svc.create_run(db, payload, MOCK_USER)
    await db.commit()
    await db.refresh(run)
    return PSRunOut.model_validate(run)


@router.get("/runs/{run_id}", response_model=PSRunOut)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    run = await svc.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    out = PSRunOut.model_validate(run)
    if run.warehouse:
        out.warehouse_name = run.warehouse.name
    return out


@router.post("/runs/{run_id}/execute", response_model=PSRunOut)
async def execute_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        run = await svc.execute_run(db, run_id)
        await db.commit()
        await db.refresh(run)
        return PSRunOut.model_validate(run)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Suggestions ───────────────────────────────────────────────────────────────

@router.get("/suggestions", response_model=List[PSLineOut])
async def list_suggestions(
    run_id: UUID,
    urgency: Optional[PSUrgencyLevel] = None,
    risk_only: bool = Query(False),
    status_filter: Optional[PSSuggestionStatus] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    lines = await svc.list_lines(db, run_id, urgency=urgency, risk_only=risk_only, status=status_filter, skip=skip, limit=limit)
    return [_line_out(l) for l in lines]


@router.patch("/suggestions/{line_id}", response_model=PSLineOut)
async def update_suggestion(
    line_id: UUID,
    payload: PSLineUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        line = await svc.update_line(db, line_id, payload)
        await db.commit()
        await db.refresh(line)
        return _line_out(line)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/suggestions/{line_id}/approve", response_model=PSLineOut)
async def approve_suggestion(line_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        line = await svc.approve_line(db, line_id)
        await db.commit()
        await db.refresh(line)
        return _line_out(line)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/suggestions/{line_id}/reject", response_model=PSLineOut)
async def reject_suggestion(
    line_id: UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        line = await svc.reject_line(db, line_id, reason)
        await db.commit()
        await db.refresh(line)
        return _line_out(line)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[PSGroupOut])
async def list_groups(run_id: UUID, db: AsyncSession = Depends(get_db)):
    groups = await svc.list_groups(db, run_id)
    return [_group_out(g) for g in groups]


@router.post("/groups/convert-to-pr", status_code=status.HTTP_201_CREATED)
async def convert_group_to_pr(
    payload: ConvertGroupToPRRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        pr = await svc.convert_group_to_pr(db, payload, MOCK_USER)
        await db.commit()
        return {"pr_id": str(pr.id), "pr_no": pr.pr_no, "status": pr.status.value}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Supplier Compare ──────────────────────────────────────────────────────────

@router.get("/suppliers/{material_id}/compare", response_model=SupplierCompareResult)
async def compare_suppliers(material_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.compare_suppliers_for_material(db, material_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Supplier Item Prices ──────────────────────────────────────────────────────

@router.get("/supplier-prices", response_model=List[SupplierItemPriceOut])
async def list_supplier_prices(
    material_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    sips = await svc.list_supplier_prices(db, material_id=material_id, supplier_id=supplier_id, skip=skip, limit=limit)
    result = []
    for sip in sips:
        out = SupplierItemPriceOut.model_validate(sip)
        if sip.supplier:
            out.supplier_name = sip.supplier.name
        if sip.material:
            out.material_name = sip.material.name
            out.material_code = sip.material.code
        result.append(out)
    return result


@router.post("/supplier-prices", response_model=SupplierItemPriceOut, status_code=status.HTTP_201_CREATED)
async def create_supplier_price(
    payload: SupplierItemPriceCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        sip = await svc.create_supplier_price(db, payload)
        await db.commit()
        await db.refresh(sip)
        return SupplierItemPriceOut.model_validate(sip)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.patch("/supplier-prices/{sip_id}", response_model=SupplierItemPriceOut)
async def update_supplier_price(
    sip_id: UUID,
    payload: SupplierItemPriceUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        sip = await svc.update_supplier_price(db, sip_id, payload)
        await db.commit()
        await db.refresh(sip)
        return SupplierItemPriceOut.model_validate(sip)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/supplier-prices/{sip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier_price(sip_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        await svc.delete_supplier_price(db, sip_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/runs/{run_id}/ai/run", status_code=status.HTTP_200_OK)
async def run_ai_agents(run_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        counts = await svc.run_ai_agents(db, run_id)
        await db.commit()
        total = sum(counts.values())
        return {"generated": total, "by_agent": counts}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/runs/{run_id}/ai/recommendations", response_model=List[PSAIRecOut])
async def list_ai_recs(run_id: UUID, db: AsyncSession = Depends(get_db)):
    recs = await svc.list_ai_recs(db, run_id)
    result = []
    for r in recs:
        out = PSAIRecOut.model_validate(r)
        if r.material:
            out.material_name = r.material.name
        if r.supplier:
            out.supplier_name = r.supplier.name
        result.append(out)
    return result


@router.post("/ai/recommendations/{rec_id}/action", response_model=PSAIRecOut)
async def action_ai_rec(
    rec_id: UUID,
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        rec = await svc.action_ai_rec(db, rec_id, notes)
        await db.commit()
        await db.refresh(rec)
        return PSAIRecOut.model_validate(rec)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/shortages", response_model=List[ShortageReportRow])
async def shortage_report(run_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_shortage_report(db, run_id)
