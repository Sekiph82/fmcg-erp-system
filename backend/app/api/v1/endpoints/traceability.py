"""Lot Traceability + Batch Recall Management — 36 routes at /api/v1/traceability/"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.traceability import (
    TraceEventType, RecallStatus, RecallActionStatus,
    TRRecAIAgentType, TRRecAIRecStatus,
)
from app.schemas.traceability import (
    TraceEventCreate, TraceEventOut,
    GenealogyLinkCreate, GenealogyLinkOut,
    GenealogyTree, TraceabilitySearchRequest, TraceabilitySearchResult,
    ForwardTraceResult, BackwardTraceResult,
    RecallCreate, RecallStatusUpdate, RecallActionCreate, RecallActionComplete,
    RecallReturnCreate, TRRecAIRecReview,
    RecallHeaderOut, RecallDetail, RecallDashboard,
    RecallScopeLineOut, RecallActionOut, RecallCustomerImpactOut,
    RecallReturnOut, TRRecAIRecommendationOut, RecallRegulatoryReport,
    RecallTemplateCreate, RecallTemplateUpdate, RecallTemplateOut,
    RecallEvidenceCreate, RecallEvidenceOut, RecallStatusLogOut,
)
from app.services import traceability_service as trace_svc
from app.services import recall_service as recall_svc

router = APIRouter()


# ── Traceability Events ───────────────────────────────────────────────────────

@router.post("/events", response_model=TraceEventOut, status_code=201)
async def create_trace_event(data: TraceEventCreate, db: AsyncSession = Depends(get_db)):
    return await trace_svc.create_trace_event(db, data)


@router.get("/events", response_model=List[TraceEventOut])
async def list_trace_events(
    lot_id:     Optional[uuid.UUID] = Query(None),
    event_type: Optional[TraceEventType] = Query(None),
    limit:      int = Query(200, le=500),
    db:         AsyncSession = Depends(get_db),
):
    events = await trace_svc.list_trace_events(db, lot_id=lot_id, event_type=event_type, limit=limit)
    return [
        TraceEventOut(
            id=e.id, trace_event_type=e.trace_event_type, event_datetime=e.event_datetime,
            reference_number=e.reference_number, source_document_type=e.source_document_type,
            source_document_id=e.source_document_id, production_order_id=e.production_order_id,
            warehouse_id=e.warehouse_id, performed_by_id=e.performed_by_id,
            recall_id=e.recall_id, notes=e.notes, lines=[], created_at=e.created_at,
        )
        for e in events
    ]


# ── Genealogy Links ───────────────────────────────────────────────────────────

@router.post("/genealogy/links", response_model=GenealogyLinkOut, status_code=201)
async def create_genealogy_link(data: GenealogyLinkCreate, db: AsyncSession = Depends(get_db)):
    return await trace_svc.create_genealogy_link(db, data)


@router.get("/genealogy/links/{lot_id}", response_model=List[GenealogyLinkOut])
async def list_genealogy_links(
    lot_id:    uuid.UUID,
    direction: str = Query("both"),
    db:        AsyncSession = Depends(get_db),
):
    return await trace_svc.list_genealogy_links(db, lot_id, direction)


@router.get("/genealogy/{lot_id}", response_model=GenealogyTree)
async def get_genealogy_tree(
    lot_id:    uuid.UUID,
    direction: str = Query("both"),
    max_depth: int = Query(6, le=12),
    db:        AsyncSession = Depends(get_db),
):
    return await trace_svc.get_genealogy_tree(db, lot_id, direction=direction, max_depth=max_depth)


# ── Trace Search ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=List[TraceabilitySearchResult])
async def search_traceability(req: TraceabilitySearchRequest, db: AsyncSession = Depends(get_db)):
    return await trace_svc.search_traceability(db, req)


# ── Forward / Backward ───────────────────────────────────────────────────────

@router.get("/forward/{lot_id}", response_model=ForwardTraceResult)
async def forward_trace(
    lot_id:    uuid.UUID,
    max_depth: int = Query(8, le=15),
    db:        AsyncSession = Depends(get_db),
):
    return await trace_svc.forward_trace(db, lot_id, max_depth=max_depth)


@router.get("/backward/{lot_id}", response_model=BackwardTraceResult)
async def backward_trace(
    lot_id:    uuid.UUID,
    max_depth: int = Query(8, le=15),
    db:        AsyncSession = Depends(get_db),
):
    return await trace_svc.backward_trace(db, lot_id, max_depth=max_depth)


# ── Recall Dashboard ──────────────────────────────────────────────────────────

@router.get("/recalls/dashboard", response_model=RecallDashboard)
async def recall_dashboard(db: AsyncSession = Depends(get_db)):
    return await recall_svc.get_recall_dashboard(db)


# ── Recall CRUD ───────────────────────────────────────────────────────────────

@router.post("/recalls", response_model=RecallHeaderOut, status_code=201)
async def initiate_recall(data: RecallCreate, db: AsyncSession = Depends(get_db)):
    return await recall_svc.initiate_recall(db, data)


@router.get("/recalls", response_model=List[RecallHeaderOut])
async def list_recalls(
    status: Optional[RecallStatus] = Query(None),
    limit:  int = Query(100, le=500),
    db:     AsyncSession = Depends(get_db),
):
    return await recall_svc.list_recalls(db, status=status, limit=limit)


@router.get("/recalls/{recall_id}", response_model=RecallDetail)
async def get_recall_detail(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await recall_svc.get_recall_detail(db, recall_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/recalls/{recall_id}/status", response_model=RecallHeaderOut)
async def update_recall_status(recall_id: uuid.UUID, data: RecallStatusUpdate,
                                db: AsyncSession = Depends(get_db)):
    try:
        return await recall_svc.update_recall_status(db, recall_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Scope Calculation ─────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/scope-calculate", response_model=List[RecallScopeLineOut])
async def calculate_scope(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        scope_lines = await recall_svc.calculate_scope(db, recall_id)
        return [RecallScopeLineOut.model_validate(sl) for sl in scope_lines]
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Containment ───────────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/contain")
async def contain_recall(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await recall_svc.contain_recall(db, recall_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Recall Actions ────────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/actions", response_model=RecallActionOut, status_code=201)
async def create_action(recall_id: uuid.UUID, data: RecallActionCreate,
                         db: AsyncSession = Depends(get_db)):
    return await recall_svc.create_action(db, recall_id, data)


@router.post("/recalls/actions/{action_id}/complete", response_model=RecallActionOut)
async def complete_action(action_id: uuid.UUID, data: RecallActionComplete,
                           db: AsyncSession = Depends(get_db)):
    try:
        return await recall_svc.complete_action(db, action_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/recalls/{recall_id}/actions", response_model=List[RecallActionOut])
async def list_actions(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await recall_svc.list_actions(db, recall_id)


# ── Customer Impact ───────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/customer-impact/build", response_model=List[RecallCustomerImpactOut])
async def build_customer_impact(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        impacts = await recall_svc.build_customer_impact(db, recall_id)
        return [RecallCustomerImpactOut.model_validate(ci) for ci in impacts]
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/recalls/{recall_id}/customer-impact", response_model=List[RecallCustomerImpactOut])
async def get_customer_impact(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await recall_svc.list_customer_impacts(db, recall_id)


@router.post("/recalls/customer-impact/{impact_id}/notify", response_model=RecallCustomerImpactOut)
async def notify_customer(impact_id: uuid.UUID, method: str = Query("email"),
                           db: AsyncSession = Depends(get_db)):
    try:
        ci = await recall_svc.notify_customer(db, impact_id, method=method)
        return RecallCustomerImpactOut.model_validate(ci)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Returns ───────────────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/returns", response_model=RecallReturnOut, status_code=201)
async def record_return(recall_id: uuid.UUID, data: RecallReturnCreate,
                         db: AsyncSession = Depends(get_db)):
    ret = await recall_svc.record_return(db, recall_id, data)
    return RecallReturnOut.model_validate(ret)


@router.get("/recalls/{recall_id}/returns", response_model=List[RecallReturnOut])
async def list_returns(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    returns = await recall_svc.list_returns(db, recall_id)
    return [RecallReturnOut.model_validate(r) for r in returns]


# ── Close ─────────────────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/close", response_model=RecallHeaderOut)
async def close_recall(
    recall_id: uuid.UUID,
    effectiveness_score: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        score = Decimal(str(effectiveness_score)) if effectiveness_score else None
        return await recall_svc.close_recall(db, recall_id, effectiveness_score=score)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Regulatory Report ─────────────────────────────────────────────────────────

@router.get("/recalls/{recall_id}/regulatory-report", response_model=RecallRegulatoryReport)
async def regulatory_report(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await recall_svc.generate_regulatory_report(db, recall_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/recalls/{recall_id}/run-ai-agents")
async def run_ai_agents(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recs = await recall_svc.run_recall_ai_agents(db, recall_id)
    return {"generated": len(recs)}


@router.get("/recalls/{recall_id}/ai-recommendations", response_model=List[TRRecAIRecommendationOut])
async def list_ai_recs(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recs = await recall_svc.list_ai_recommendations(db, recall_id)
    return [TRRecAIRecommendationOut.model_validate(r) for r in recs]


@router.post("/recalls/ai-recommendations/{rec_id}/review", response_model=TRRecAIRecommendationOut)
async def review_ai_rec(rec_id: uuid.UUID, data: TRRecAIRecReview,
                         db: AsyncSession = Depends(get_db)):
    try:
        rec = await recall_svc.review_ai_recommendation(db, rec_id, data)
        return TRRecAIRecommendationOut.model_validate(rec)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Communication Templates ───────────────────────────────────────────────────

@router.get("/recall-templates", response_model=List[RecallTemplateOut])
async def list_recall_templates(
    audience: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    templates = await recall_svc.list_templates(db, audience=audience, active_only=active_only)
    return [RecallTemplateOut.model_validate(t) for t in templates]


@router.post("/recall-templates", response_model=RecallTemplateOut, status_code=201)
async def create_recall_template(
    data: RecallTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    tmpl = await recall_svc.create_template(db, data)
    return RecallTemplateOut.model_validate(tmpl)


@router.patch("/recall-templates/{template_id}", response_model=RecallTemplateOut)
async def update_recall_template(
    template_id: uuid.UUID,
    data: RecallTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        tmpl = await recall_svc.update_template(db, template_id, data)
        return RecallTemplateOut.model_validate(tmpl)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Status Audit Log ──────────────────────────────────────────────────────────

@router.get("/recalls/{recall_id}/audit-log", response_model=List[RecallStatusLogOut])
async def recall_audit_log(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    logs = await recall_svc.list_status_logs(db, recall_id)
    out = []
    for log in logs:
        row = RecallStatusLogOut.model_validate(log)
        if log.changed_by:
            row.changed_by_name = log.changed_by.full_name or log.changed_by.username
        out.append(row)
    return out


# ── Evidence Attachments ──────────────────────────────────────────────────────

@router.get("/recalls/{recall_id}/evidence", response_model=List[RecallEvidenceOut])
async def list_recall_evidence(recall_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    evidence = await recall_svc.list_evidence(db, recall_id)
    return [RecallEvidenceOut.model_validate(e) for e in evidence]


@router.post("/recalls/{recall_id}/evidence", response_model=RecallEvidenceOut, status_code=201)
async def add_recall_evidence(
    recall_id: uuid.UUID,
    data: RecallEvidenceCreate,
    db: AsyncSession = Depends(get_db),
):
    ev = await recall_svc.add_evidence(db, recall_id, data)
    return RecallEvidenceOut.model_validate(ev)
