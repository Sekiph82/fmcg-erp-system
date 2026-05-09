"""FEFO + Shelf-Life Control API — 32 routes at /api/v1/shelf-life/"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel as _BM
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.shelf_life import (
    ShelfLifeStatus, AlertSeverity, SLAIRecStatus,
    SLAIAgentType, DispositionStatus, FEFOContext,
)
from app.schemas.shelf_life import (
    ItemShelfLifeConfigCreate, ItemShelfLifeConfigUpdate, ItemShelfLifeConfigOut,
    PickingStrategyConfigCreate, PickingStrategyConfigOut,
    CustomerShelfLifeRuleCreate, CustomerShelfLifeRuleOut,
    LotShelfLifeProfileOut, LotShelfLifeProfileUpdate,
    FEFORankRequest, FEFORankResponse,
    FEFOValidateIssueRequest, FEFOValidateIssueResponse,
    FEFOValidateShipmentRequest, FEFOValidateShipmentResponse,
    FEFOAuditLogCreate, FEFOAuditLogOut,
    RetestRequestCreate, RetestResultCreate, RetestRequestOut,
    BulkHoldCreate, BulkHoldOut,
    ShelfLifeAlertOut,
    DispositionApproveRequest, DispositionSuggestionOut,
    SLAIRecReviewRequest, SLAIRecommendationOut,
    ShelfLifeDashboard, FEFOComplianceReport,
)
from app.services import shelf_life_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ShelfLifeDashboard)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Item Config ───────────────────────────────────────────────────────────────

@router.post("/config/item", response_model=ItemShelfLifeConfigOut, status_code=201)
async def create_item_config(data: ItemShelfLifeConfigCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_item_config(db, data)


@router.put("/config/item/{config_id}", response_model=ItemShelfLifeConfigOut)
async def update_item_config(config_id: uuid.UUID, data: ItemShelfLifeConfigUpdate,
                              db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_item_config(db, config_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/config/item", response_model=List[ItemShelfLifeConfigOut])
async def list_item_configs(db: AsyncSession = Depends(get_db)):
    return await svc.list_item_configs(db)


@router.get("/config/item/by-product/{product_id}", response_model=Optional[ItemShelfLifeConfigOut])
async def get_item_config_by_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_item_config(db, product_id=product_id)


@router.get("/config/item/by-material/{material_id}", response_model=Optional[ItemShelfLifeConfigOut])
async def get_item_config_by_material(material_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_item_config(db, material_id=material_id)


# ── Picking Strategy ──────────────────────────────────────────────────────────

@router.post("/config/picking-strategy", response_model=PickingStrategyConfigOut, status_code=201)
async def create_picking_strategy(data: PickingStrategyConfigCreate,
                                   db: AsyncSession = Depends(get_db)):
    return await svc.create_picking_strategy(db, data)


@router.get("/config/picking-strategy", response_model=List[PickingStrategyConfigOut])
async def list_picking_strategies(db: AsyncSession = Depends(get_db)):
    return await svc.list_picking_strategies(db)


# ── Customer Rules ────────────────────────────────────────────────────────────

@router.post("/config/customer-rule", response_model=CustomerShelfLifeRuleOut, status_code=201)
async def create_customer_rule(data: CustomerShelfLifeRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_customer_rule(db, data)


@router.get("/config/customer-rules", response_model=List[CustomerShelfLifeRuleOut])
async def list_customer_rules(db: AsyncSession = Depends(get_db)):
    return await svc.list_customer_rules(db)


@router.get("/config/customer-rule/{customer_id}", response_model=Optional[CustomerShelfLifeRuleOut])
async def get_customer_rule(customer_id: uuid.UUID,
                             product_id: Optional[uuid.UUID] = Query(None),
                             db: AsyncSession = Depends(get_db)):
    return await svc.get_customer_rule(db, customer_id, product_id)


# ── Lot Shelf-Life Profile ────────────────────────────────────────────────────

@router.get("/lots/{lot_id}/shelf-life", response_model=LotShelfLifeProfileOut)
async def get_lot_profile(lot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_or_create_lot_profile(db, lot_id)


@router.put("/lots/{lot_id}/shelf-life", response_model=LotShelfLifeProfileOut)
async def update_lot_profile(lot_id: uuid.UUID, data: LotShelfLifeProfileUpdate,
                              db: AsyncSession = Depends(get_db)):
    return await svc.update_lot_profile(db, lot_id, data)


@router.post("/lots/{lot_id}/recalculate", response_model=LotShelfLifeProfileOut)
async def recalculate_lot(lot_id: uuid.UUID,
                           near_expiry_days: int = Query(30),
                           db: AsyncSession = Depends(get_db)):
    return await svc.recalculate_lot_status(db, lot_id, near_expiry_days)


@router.post("/lots/batch-recalculate")
async def batch_recalculate(db: AsyncSession = Depends(get_db)):
    count = await svc.batch_recalculate_statuses(db)
    return {"updated": count}


@router.get("/lots", response_model=List[LotShelfLifeProfileOut])
async def list_lot_profiles(
    status: Optional[ShelfLifeStatus] = Query(None),
    limit: int = Query(200, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_all_lot_profiles(db, status=status, limit=limit, offset=offset)


# ── Near-Expiry & Expired ─────────────────────────────────────────────────────

@router.get("/near-expiry", response_model=List[LotShelfLifeProfileOut])
async def near_expiry(days: int = Query(30), db: AsyncSession = Depends(get_db)):
    return await svc.list_near_expiry(db, days=days)


@router.get("/expired", response_model=List[LotShelfLifeProfileOut])
async def expired(db: AsyncSession = Depends(get_db)):
    return await svc.list_expired(db)


# ── FEFO Ranking ──────────────────────────────────────────────────────────────

@router.post("/fefo/rank", response_model=FEFORankResponse)
async def rank_fefo(req: FEFORankRequest, db: AsyncSession = Depends(get_db)):
    return await svc.rank_lots_fefo(db, req)


@router.post("/fefo/validate-issue", response_model=FEFOValidateIssueResponse)
async def validate_issue(req: FEFOValidateIssueRequest, db: AsyncSession = Depends(get_db)):
    return await svc.validate_issue(db, req)


@router.post("/fefo/validate-shipment", response_model=FEFOValidateShipmentResponse)
async def validate_shipment(req: FEFOValidateShipmentRequest, db: AsyncSession = Depends(get_db)):
    return await svc.validate_shipment(db, req)


# ── FEFO Audit ────────────────────────────────────────────────────────────────

@router.post("/fefo/audit-log", response_model=FEFOAuditLogOut, status_code=201)
async def log_fefo_audit(data: FEFOAuditLogCreate, db: AsyncSession = Depends(get_db)):
    return await svc.log_fefo_audit(db, data)


@router.get("/fefo/audit-log", response_model=List[FEFOAuditLogOut])
async def list_audit_log(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    context: Optional[FEFOContext] = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_fefo_audit(db, warehouse_id=warehouse_id, context=context, limit=limit)


@router.get("/compliance", response_model=FEFOComplianceReport)
async def compliance_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_fefo_compliance_report(db, date_from=date_from, date_to=date_to)


# ── Retest ────────────────────────────────────────────────────────────────────

@router.post("/retest-request", response_model=RetestRequestOut, status_code=201)
async def create_retest(data: RetestRequestCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_retest_request(db, data)


@router.post("/retest-request/{request_id}/result", response_model=RetestRequestOut)
async def record_retest(request_id: uuid.UUID, data: RetestResultCreate,
                         db: AsyncSession = Depends(get_db)):
    try:
        return await svc.record_retest_result(db, request_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/retest-queue", response_model=List[RetestRequestOut])
async def retest_queue(db: AsyncSession = Depends(get_db)):
    return await svc.list_retest_queue(db)


# ── Bulk Hold ─────────────────────────────────────────────────────────────────

@router.post("/bulk-hold", response_model=BulkHoldOut, status_code=201)
async def create_bulk_hold(data: BulkHoldCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_bulk_hold(db, data)


@router.get("/bulk-hold", response_model=List[BulkHoldOut])
async def list_bulk_holds(active_only: bool = Query(True), db: AsyncSession = Depends(get_db)):
    return await svc.list_bulk_holds(db, active_only=active_only)


@router.post("/bulk-hold/refresh")
async def refresh_bulk_holds(db: AsyncSession = Depends(get_db)):
    count = await svc.refresh_bulk_hold_statuses(db)
    return {"updated": count}


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.post("/alerts/generate")
async def generate_alerts(db: AsyncSession = Depends(get_db)):
    count = await svc.generate_alerts(db)
    return {"created": count}


@router.get("/alerts", response_model=List[ShelfLifeAlertOut])
async def list_alerts(
    resolved: bool = Query(False),
    severity: Optional[AlertSeverity] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_alerts(db, resolved=resolved, severity=severity, limit=limit)


@router.post("/alerts/{alert_id}/resolve", response_model=ShelfLifeAlertOut)
async def resolve_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.resolve_alert(db, alert_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Disposition Suggestions ───────────────────────────────────────────────────

@router.post("/disposition-suggestions/generate")
async def generate_dispositions(db: AsyncSession = Depends(get_db)):
    count = await svc.generate_disposition_suggestions(db)
    return {"created": count}


@router.get("/disposition-suggestions", response_model=List[DispositionSuggestionOut])
async def list_dispositions(
    status: Optional[DispositionStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_disposition_suggestions(db, status=status)


@router.post("/disposition-suggestions/{suggestion_id}/approve", response_model=DispositionSuggestionOut)
async def approve_disposition(suggestion_id: uuid.UUID, data: DispositionApproveRequest,
                               db: AsyncSession = Depends(get_db)):
    try:
        return await svc.approve_disposition(db, suggestion_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/run-ai-agents")
async def run_ai_agents(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_all_ai_agents(db)
    return {"generated": len(recs)}


@router.get("/ai-recommendations", response_model=List[SLAIRecommendationOut])
async def list_ai_recs(
    status: Optional[SLAIRecStatus] = Query(None),
    agent_type: Optional[SLAIAgentType] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recommendations(db, status=status, agent_type=agent_type, limit=limit)


@router.post("/ai-recommendations/{rec_id}/review", response_model=SLAIRecommendationOut)
async def review_ai_rec(rec_id: uuid.UUID, data: SLAIRecReviewRequest,
                         db: AsyncSession = Depends(get_db)):
    try:
        return await svc.review_ai_recommendation(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Shelf-Life Extension Approval ─────────────────────────────────────────────

class ExtensionIn(_BM):
    lot_id: str
    lot_number: Optional[str] = None
    product_name: Optional[str] = None
    original_expiry: date
    proposed_expiry: date
    justification: str
    risk_assessment: Optional[str] = None
    test_results_attached: bool = False
    requested_by: Optional[str] = None


@router.post("/extensions", status_code=201)
async def request_extension(payload: ExtensionIn, db: AsyncSession = Depends(get_db)):
    from app.models.shelf_life import ShelfLifeExtension
    ext_days = (payload.proposed_expiry - payload.original_expiry).days
    if ext_days <= 0:
        raise HTTPException(400, "proposed_expiry must be after original_expiry")
    ext = ShelfLifeExtension(
        lot_id=uuid.UUID(payload.lot_id),
        lot_number=payload.lot_number,
        product_name=payload.product_name,
        original_expiry=payload.original_expiry,
        proposed_expiry=payload.proposed_expiry,
        extension_days=ext_days,
        justification=payload.justification,
        risk_assessment=payload.risk_assessment,
        test_results_attached=payload.test_results_attached,
        requested_by=payload.requested_by,
    )
    db.add(ext)
    await db.commit()
    await db.refresh(ext)
    return {
        "id": str(ext.id), "lot_number": ext.lot_number,
        "product_name": ext.product_name,
        "original_expiry": str(ext.original_expiry),
        "proposed_expiry": str(ext.proposed_expiry),
        "extension_days": ext.extension_days,
        "status": ext.status,
    }


@router.get("/extensions")
async def list_extensions(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.shelf_life import ShelfLifeExtension
    q = select(ShelfLifeExtension)
    if status:
        q = q.where(ShelfLifeExtension.status == status)
    q = q.order_by(desc(ShelfLifeExtension.created_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id), "lot_number": r.lot_number, "product_name": r.product_name,
            "original_expiry": str(r.original_expiry), "proposed_expiry": str(r.proposed_expiry),
            "extension_days": r.extension_days, "status": r.status,
            "requested_by": r.requested_by, "approved_by": r.approved_by,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


@router.post("/extensions/{ext_id}/approve")
async def approve_extension(
    ext_id: str,
    approved_by: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from app.models.shelf_life import ShelfLifeExtension, ExtensionStatus
    r = await db.execute(select(ShelfLifeExtension).where(ShelfLifeExtension.id == uuid.UUID(ext_id)))
    ext = r.scalar_one_or_none()
    if not ext:
        raise HTTPException(404, "Extension request not found")
    ext.status = ExtensionStatus.APPROVED
    ext.approved_by = approved_by
    ext.approved_at = datetime.utcnow()
    await db.commit()
    return {"id": ext_id, "status": "APPROVED", "new_expiry": str(ext.proposed_expiry)}


@router.post("/extensions/{ext_id}/reject")
async def reject_extension(
    ext_id: str,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    from app.models.shelf_life import ShelfLifeExtension, ExtensionStatus
    r = await db.execute(select(ShelfLifeExtension).where(ShelfLifeExtension.id == uuid.UUID(ext_id)))
    ext = r.scalar_one_or_none()
    if not ext:
        raise HTTPException(404, "Extension request not found")
    ext.status = ExtensionStatus.REJECTED
    ext.rejection_reason = reason
    await db.commit()
    return {"id": ext_id, "status": "REJECTED"}
