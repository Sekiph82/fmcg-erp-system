from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.db.session import get_db
from app.schemas.invoice_match import (
    RunMatchRequest, ReviewCreate,
    ToleranceRuleCreate, ToleranceRuleUpdate,
    MatchHeaderOut, MatchHeaderSummary, MatchDecisionRequest,
    ToleranceRuleOut, DuplicateLogOut,
    IMAIRecOut, IMDashboard,
)
from app.services import invoice_match_service as svc

router = APIRouter()


def _actor_role_names(current_user) -> set[str]:
    if getattr(current_user, "is_superuser", False):
        return {"*"}
    return {
        role.name.strip()
        for role in getattr(current_user, "roles", [])
        if isinstance(getattr(role, "name", None), str) and role.name.strip()
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=IMDashboard)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.get_dashboard(db)


# ── Run Match ─────────────────────────────────────────────────────────────────

@router.post("/run", response_model=MatchHeaderOut)
async def run_match(
    payload: RunMatchRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "edit")),
):
    try:
        return await svc.run_match(db, payload.invoice_id, payload.force_rerun)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── List / Get ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[MatchHeaderSummary])
async def list_matches(
    status: Optional[str] = Query(None),
    review_required: Optional[bool] = Query(None),
    duplicate_flag: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.list_headers(
        db, status=status, review_required=review_required,
        duplicate_flag=duplicate_flag, limit=limit, offset=offset,
    )


@router.get("/blocked-invoices", response_model=List[MatchHeaderSummary])
async def blocked_invoices(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.get_blocked_invoices(db)


@router.get("/duplicate-suspicions", response_model=List[DuplicateLogOut])
async def duplicate_suspicions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(200, ge=1, le=500),
    _: None = Depends(require_permission("finance", "view")),
):
    items = await svc.get_duplicate_suspicions(db)
    return items[:limit]


# ── Review / Approval ─────────────────────────────────────────────────────────

@router.post("/{header_id}/review", response_model=MatchHeaderOut)
async def review(
    header_id: UUID,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    try:
        payload = payload.model_copy(update={"reviewer_name": current_user.email, "reviewer_role": None})
        return await svc.submit_review(
            db, header_id, payload, actor_role_names=_actor_role_names(current_user),
        )
    except svc.InvoiceMatchApprovalRoleError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{header_id}/approve-exception", response_model=MatchHeaderOut)
async def approve_exception(
    header_id: UUID,
    body: MatchDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    payload = ReviewCreate(
        action="APPROVED_EXCEPTION",
        reviewer_name=current_user.email,
        reviewer_role=None,
        justification=body.justification,
        expected_run_at=body.expected_run_at,
    )
    try:
        return await svc.submit_review(
            db, header_id, payload, actor_role_names=_actor_role_names(current_user),
        )
    except svc.InvoiceMatchApprovalRoleError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{header_id}/reject", response_model=MatchHeaderOut)
async def reject_invoice(
    header_id: UUID,
    body: MatchDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    payload = ReviewCreate(
        action="REJECTED",
        reviewer_name=current_user.email,
        reviewer_role=None,
        justification=body.justification,
        expected_run_at=body.expected_run_at,
    )
    try:
        return await svc.submit_review(
            db, header_id, payload, actor_role_names=_actor_role_names(current_user),
        )
    except svc.InvoiceMatchApprovalRoleError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Duplicate Resolution ──────────────────────────────────────────────────────

@router.post("/duplicate-suspicions/{dup_id}/resolve", response_model=DuplicateLogOut)
async def resolve_duplicate(
    dup_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    result = await svc.resolve_duplicate(
        db, dup_id,
        resolved_by=current_user.email,
        resolution_notes=body.get("resolution_notes", ""),
    )
    if not result:
        raise HTTPException(404, "Duplicate log not found")
    return result


# ── Tolerance Rules ───────────────────────────────────────────────────────────

@router.get("/tolerance-rules", response_model=List[ToleranceRuleOut])
async def list_tolerance_rules(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.list_tolerance_rules(db, active_only=active_only)


@router.get("/{header_id}", response_model=MatchHeaderOut)
async def get_match(
    header_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    hdr = await svc.get_header(db, header_id)
    if not hdr:
        raise HTTPException(404, "Match record not found")
    return hdr


@router.post("/tolerance-rules", response_model=ToleranceRuleOut, status_code=201)
async def create_tolerance_rule(
    payload: ToleranceRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "configure")),
):
    return await svc.create_tolerance_rule(db, payload)


@router.patch("/tolerance-rules/{rule_id}", response_model=ToleranceRuleOut)
async def update_tolerance_rule(
    rule_id: UUID,
    payload: ToleranceRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "configure")),
):
    rule = await svc.update_tolerance_rule(db, rule_id, payload)
    if not rule:
        raise HTTPException(404, "Tolerance rule not found")
    return rule


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/mismatch-summary")
async def report_mismatch_summary(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.report_mismatch_summary(db)


@router.get("/reports/supplier-accuracy")
async def report_supplier_accuracy(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.report_supplier_accuracy(db)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run")
async def run_ai(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "edit")),
):
    count = await svc.run_ai_agents(db)
    return {"recommendations_created": count}


@router.post("/{header_id}/ai/run")
async def run_ai_for_match(
    header_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "edit")),
):
    count = await svc.run_ai_agents(db, header_id=header_id)
    return {"recommendations_created": count}


@router.get("/ai/recs", response_model=List[IMAIRecOut])
async def list_ai_recs(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("finance", "view")),
):
    return await svc.list_ai_recs(db, status=status)


@router.post("/ai/recs/{rec_id}/action", response_model=IMAIRecOut)
async def action_rec(
    rec_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("finance", "approve")),
):
    rec = await svc.action_ai_rec(
        db, rec_id, body.get("status", "ACCEPTED"), actioned_by=current_user.email,
    )
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
