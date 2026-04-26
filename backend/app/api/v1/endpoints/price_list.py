from __future__ import annotations
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.price_list import (
    PLHeaderCreate, PLHeaderUpdate, PLHeaderOut,
    PLLineCreate, PLLineUpdate, PLLineOut,
    PLTierCreate, PLTierOut,
    PLAssignmentCreate, PLAssignmentOut,
    PLDiscountRuleCreate, PLDiscountRuleOut,
    PLApprovalSubmit, PLApprovalReview, PLApprovalOut,
    PriceResolveRequest,
    MarginCheckRequest,
    PLBulkImportRequest, PLBulkImportResult,
    PLChangeHistoryOut,
    PLAIRecAck, PLAIRecOut,
)
import app.services.price_list_service as svc

router = APIRouter()


# ── Headers ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PLHeaderOut])
async def list_headers(
    status: Optional[str] = Query(None),
    pl_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_headers(db, status=status, pl_type=pl_type, active_only=active_only)


@router.post("/", response_model=PLHeaderOut)
async def create_header(payload: PLHeaderCreate, db: AsyncSession = Depends(get_db)):
    hdr = await svc.create_header(db, payload)
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.get("/pending-approval", response_model=List[PLHeaderOut])
async def pending_approval(db: AsyncSession = Depends(get_db)):
    return await svc.list_pending_approvals(db)


@router.get("/{header_id}", response_model=PLHeaderOut)
async def get_header(header_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    hdr = await svc.get_header(db, header_id)
    if not hdr:
        raise HTTPException(status_code=404, detail="Price list not found")
    return hdr


@router.put("/{header_id}", response_model=PLHeaderOut)
async def update_header(
    header_id: uuid.UUID,
    payload: PLHeaderUpdate,
    updated_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    hdr = await svc.update_header(db, header_id, payload, updated_by=updated_by)
    if not hdr:
        raise HTTPException(status_code=400, detail="Cannot update: not found or already active/approved/archived")
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.post("/{header_id}/submit", response_model=PLHeaderOut)
async def submit_for_approval(header_id: uuid.UUID, payload: PLApprovalSubmit, db: AsyncSession = Depends(get_db)):
    hdr = await svc.submit_for_approval(db, header_id, payload)
    if not hdr:
        raise HTTPException(status_code=400, detail="Cannot submit: not found or not in DRAFT")
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.post("/{header_id}/approve", response_model=PLHeaderOut)
async def review_approval(header_id: uuid.UUID, payload: PLApprovalReview, db: AsyncSession = Depends(get_db)):
    hdr = await svc.review_approval(db, header_id, payload)
    if not hdr:
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.post("/{header_id}/activate", response_model=PLHeaderOut)
async def activate(header_id: uuid.UUID, activated_by: str = Query("system"), db: AsyncSession = Depends(get_db)):
    hdr = await svc.activate_header(db, header_id, activated_by=activated_by)
    if not hdr:
        raise HTTPException(status_code=400, detail="Cannot activate: not found or not in APPROVED/DRAFT state")
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.post("/{header_id}/archive", response_model=PLHeaderOut)
async def archive(header_id: uuid.UUID, archived_by: str = Query("system"), db: AsyncSession = Depends(get_db)):
    hdr = await svc.archive_header(db, header_id, archived_by=archived_by)
    if not hdr:
        raise HTTPException(status_code=404, detail="Price list not found")
    await db.commit()
    await db.refresh(hdr)
    return hdr


@router.get("/{header_id}/history", response_model=List[PLChangeHistoryOut])
async def get_history(header_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_change_history(db, header_id)


@router.get("/{header_id}/approvals", response_model=List[PLApprovalOut])
async def get_approvals(header_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_approval_history(db, header_id)


# ── Lines ──────────────────────────────────────────────────────────────────────

@router.get("/{header_id}/lines", response_model=List[PLLineOut])
async def list_lines(header_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_lines(db, header_id)


@router.post("/{header_id}/lines", response_model=PLLineOut)
async def add_line(
    header_id: uuid.UUID,
    payload: PLLineCreate,
    added_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    try:
        line = await svc.add_line(db, header_id, payload, added_by=added_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(line)
    return line


@router.put("/lines/{line_id}", response_model=PLLineOut)
async def update_line(
    line_id: uuid.UUID,
    payload: PLLineUpdate,
    updated_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    line = await svc.update_line(db, line_id, payload, updated_by=updated_by)
    if not line:
        raise HTTPException(status_code=404, detail="Price line not found")
    await db.commit()
    await db.refresh(line)
    return line


# ── Tiers ──────────────────────────────────────────────────────────────────────

@router.get("/lines/{line_id}/tiers", response_model=List[PLTierOut])
async def list_tiers(line_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_tiers(db, line_id)


@router.post("/lines/{line_id}/tiers", response_model=PLTierOut)
async def add_tier(line_id: uuid.UUID, payload: PLTierCreate, db: AsyncSession = Depends(get_db)):
    tier = await svc.add_tier(db, line_id, payload)
    await db.commit()
    await db.refresh(tier)
    return tier


# ── Assignments ────────────────────────────────────────────────────────────────

@router.get("/{header_id}/assignments", response_model=List[PLAssignmentOut])
async def list_assignments(header_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_assignments(db, header_id)


@router.post("/{header_id}/assignments", response_model=PLAssignmentOut)
async def add_assignment(header_id: uuid.UUID, payload: PLAssignmentCreate, db: AsyncSession = Depends(get_db)):
    asn = await svc.add_assignment(db, header_id, payload)
    await db.commit()
    await db.refresh(asn)
    return asn


@router.get("/customer/{customer_id}/assignments", response_model=List[PLAssignmentOut])
async def customer_assignments(customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_assignments_for_customer(db, customer_id)


# ── Discount Rules ─────────────────────────────────────────────────────────────

@router.get("/discount-rules", response_model=List[PLDiscountRuleOut])
async def list_discount_rules(active_only: bool = Query(True), db: AsyncSession = Depends(get_db)):
    return await svc.list_discount_rules(db, active_only=active_only)


@router.post("/discount-rules", response_model=PLDiscountRuleOut)
async def create_discount_rule(payload: PLDiscountRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = await svc.create_discount_rule(db, payload)
    await db.commit()
    await db.refresh(rule)
    return rule


# ── Price Resolution ───────────────────────────────────────────────────────────

@router.post("/resolve-price")
async def resolve_price(payload: PriceResolveRequest, db: AsyncSession = Depends(get_db)):
    return await svc.resolve_price(db, payload)


# ── Margin Check ───────────────────────────────────────────────────────────────

@router.post("/check-margin")
async def check_margin(payload: MarginCheckRequest, db: AsyncSession = Depends(get_db)):
    return await svc.check_margin(db, payload)


# ── Bulk Import / Export ───────────────────────────────────────────────────────

@router.post("/import", response_model=PLBulkImportResult)
async def bulk_import(payload: PLBulkImportRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.bulk_import(db, payload)
    await db.commit()
    return result


@router.get("/template")
async def download_template():
    csv_content = svc.generate_template_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=price_list_template.csv"},
    )


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/dashboard")
async def report_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.report_dashboard(db)


@router.get("/reports/expiring")
async def report_expiring(days: int = Query(30, le=365), db: AsyncSession = Depends(get_db)):
    hdrs = await svc.report_expiring_soon(db, days=days)
    return [PLHeaderOut.model_validate(h) for h in hdrs]


@router.get("/reports/below-margin")
async def report_below_margin(db: AsyncSession = Depends(get_db)):
    return await svc.report_below_margin(db)


@router.get("/reports/version-compare")
async def version_compare(
    header_id_a: uuid.UUID = Query(...),
    header_id_b: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.report_version_compare(db, header_id_a, header_id_b)


# ── AI ─────────────────────────────────────────────────────────────────────────

@router.post("/ai/run")
async def run_ai(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_ai_agents(db)
    await db.commit()
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[PLAIRecOut])
async def list_ai_recs(header_id: Optional[uuid.UUID] = Query(None), db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, header_id=header_id)


@router.post("/ai/recommendations/{rec_id}/ack", response_model=PLAIRecOut)
async def ack_rec(rec_id: uuid.UUID, payload: PLAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    await db.refresh(rec)
    return rec
