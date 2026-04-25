from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.landed_cost import (
    LandedCostHeaderCreate, LandedCostHeaderUpdate,
    LandedCostLineCreate, LandedCostGRNLinkCreate,
    LandedCostOut, LandedCostSummary,
    LCAIRecOut, LCDashboard,
)
from app.services import landed_cost_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=LCDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=LandedCostOut, status_code=201)
async def create(payload: LandedCostHeaderCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_header(db, payload)


@router.get("", response_model=List[LandedCostSummary])
async def list_all(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_headers(db, status=status, limit=limit, offset=offset)


@router.get("/{header_id}", response_model=LandedCostOut)
async def get_one(header_id: UUID, db: AsyncSession = Depends(get_db)):
    hdr = await svc.get_header(db, header_id)
    if not hdr:
        raise HTTPException(404, "Landed cost document not found")
    return hdr


@router.patch("/{header_id}", response_model=LandedCostOut)
async def update(header_id: UUID, payload: LandedCostHeaderUpdate, db: AsyncSession = Depends(get_db)):
    hdr = await svc.update_header(db, header_id, payload)
    if not hdr:
        raise HTTPException(404, "Landed cost document not found")
    return hdr


# ── Cost Lines ────────────────────────────────────────────────────────────────

@router.post("/{header_id}/lines", response_model=LandedCostOut, status_code=201)
async def add_cost_line(
    header_id: UUID,
    payload: LandedCostLineCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_cost_line(db, header_id, payload)


# ── GRN Links ─────────────────────────────────────────────────────────────────

@router.post("/{header_id}/grn-links", response_model=LandedCostOut, status_code=201)
async def add_grn_link(
    header_id: UUID,
    payload: LandedCostGRNLinkCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.add_grn_link(db, header_id, payload)


# ── Allocation ────────────────────────────────────────────────────────────────

@router.post("/{header_id}/allocate", response_model=LandedCostOut)
async def allocate(header_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.run_allocation(db, header_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Post / Cancel ─────────────────────────────────────────────────────────────

@router.post("/{header_id}/post", response_model=LandedCostOut)
async def post(header_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.post_landed_cost(db, header_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{header_id}/cancel", response_model=LandedCostOut)
async def cancel(header_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.cancel_landed_cost(db, header_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/cost-by-type")
async def report_cost_by_type(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.report_cost_by_type(db, date_from=date_from, date_to=date_to)


@router.get("/reports/allocation-by-material")
async def report_allocation_by_material(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.report_allocation_by_material(db, date_from=date_from, date_to=date_to)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", status_code=200)
async def run_ai(db: AsyncSession = Depends(get_db)):
    count = await svc.run_ai_agents(db)
    return {"recommendations_created": count}


@router.post("/{header_id}/ai/run", status_code=200)
async def run_ai_for_doc(header_id: UUID, db: AsyncSession = Depends(get_db)):
    count = await svc.run_ai_agents(db, header_id=header_id)
    return {"recommendations_created": count}


@router.get("/ai/recs", response_model=List[LCAIRecOut])
async def list_ai_recs(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, status=status)


@router.get("/{header_id}/ai/recs", response_model=List[LCAIRecOut])
async def list_ai_recs_for_doc(
    header_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, header_id=header_id)


@router.post("/ai/recs/{rec_id}/action", response_model=LCAIRecOut)
async def action_rec(
    rec_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    status = payload.get("status", "ACCEPTED")
    rec = await svc.action_ai_rec(db, rec_id, status)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
