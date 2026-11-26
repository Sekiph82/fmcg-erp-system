from __future__ import annotations
from datetime import date
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import can_view_record, has_any_permission, require_any_permission
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.crm import (
    CRMActivity, CRMForecastSnapshot, CRMInterestLine, CRMRecord, CRMRecordType, CRMScoreRule, CRMTerritory,
)
from app.schemas.crm import (
    CRMStageCreate, CRMStageRead, CRMStageUpdate,
    CRMRecordCreate, CRMRecordRead, CRMRecordUpdate,
    CRMInterestLineCreate, CRMInterestLineRead,
    CRMActivityCreate, CRMActivityRead, CRMActivityComplete,
    CRMCompetitorCreate, CRMCompetitorRead,
    CRMQualifyRequest, CRMConvertRequest,
    CRMCloseWonRequest, CRMCloseLostRequest,
    CRMWinLossRead,
    CRMAIRecRead, CRMAIRecAck,
    CRMTerritoryCreate, CRMTerritoryRead, CRMTerritoryUpdate,
)
from app.services.commercial_access_service import build_commercial_access_hint, ensure_commercial_action_allowed
import app.services.crm_pipeline_service as svc
import app.services.crm_intelligence_service as intel


def _uuid(value: str):
    import uuid as _u

    try:
        return _u.UUID(str(value))
    except ValueError:
        raise HTTPException(404, "Not found")

CRM_VIEW_PERMISSIONS = ("crm.view", "crm.view_all", "crm.view_own_scope", "crm.view_own_region")
CRM_CREATE_PERMISSIONS = ("crm.create", "crm.create_all", "crm.create_own_scope", "crm.create_own_region")
CRM_EDIT_PERMISSIONS = ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region")

# Company-wide reads (aggregates, every record) and pipeline configuration. Scoped users
# (*_own_scope / *_own_region) only reach records through the per-record scope checks below.
CRM_BROAD_VIEW = ("crm.view", "crm.view_all")
CRM_CONFIG = ("crm.edit_all",)

router = APIRouter(dependencies=[Depends(require_any_permission(CRM_VIEW_PERMISSIONS))])


async def _scoped_record(db: AsyncSession, record_id, user, action: str) -> CRMRecord:
    """Load a CRM record and enforce the caller's commercial scope for the action (view/edit)."""
    rec = await svc.get_record(db, str(record_id))
    if not rec:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(user, rec, action, "crm")
    return rec


def _record_read(record: CRMRecord, user) -> CRMRecordRead:
    row = CRMRecordRead.model_validate(record)
    row.access = build_commercial_access_hint(user, record, "crm")
    return row


def _territory_read(territory: CRMTerritory, user) -> CRMTerritoryRead:
    row = CRMTerritoryRead.model_validate(territory)
    row.access = build_commercial_access_hint(user, territory, "crm")
    return row


# ── Stages ────────────────────────────────────────────────────────────────────

@router.get("/stages", response_model=List[CRMStageRead])
async def list_stages(active_only: bool = False, pipeline_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_stages(db, active_only=active_only, pipeline_id=pipeline_id)


def _check_required(fields) -> None:
    from app.services.crm_team_service import REQUIRABLE
    bad = [f for f in (fields or []) if f not in REQUIRABLE]
    if bad:
        raise HTTPException(422, f"Fields that cannot be required: {', '.join(bad)}")


@router.post("/stages", response_model=CRMStageRead, status_code=201)
async def create_stage(data: CRMStageCreate, db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
    _check_required(data.required_fields)
    return await svc.create_stage(db, data)


@router.patch("/stages/{stage_id}", response_model=CRMStageRead)
async def update_stage(stage_id: str, data: CRMStageUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
    _check_required(data.required_fields)
    result = await svc.update_stage(db, stage_id, data)
    if not result:
        raise HTTPException(404, "Stage not found")
    return result


@router.post("/stages/seed-defaults", response_model=List[CRMStageRead])
async def seed_default_stages(db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
    return await svc.seed_default_stages(db)


# ── Records ───────────────────────────────────────────────────────────────────

@router.get("/leads", response_model=List[CRMRecordRead])
async def list_leads(
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = await svc.get_records(db, record_type="LEAD", status=status,
                                    assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                    temperature=temperature, skip=skip, limit=limit)
    return [_record_read(record, current_user) for record in records if can_view_record(current_user, "crm", record)]


@router.post("/leads", response_model=CRMRecordRead, status_code=201)
async def create_lead(
    data: CRMRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_CREATE_PERMISSIONS)),
):
    data.record_type = CRMRecordType.LEAD
    ensure_commercial_action_allowed(current_user, CRMRecord(**data.model_dump()), "create", "crm")
    return _record_read(await svc.create_record(db, data), current_user)


@router.get("/opportunities", response_model=List[CRMRecordRead])
async def list_opportunities(
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = await svc.get_records(db, record_type="OPPORTUNITY", status=status,
                                    assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                    temperature=temperature, skip=skip, limit=limit)
    return [_record_read(record, current_user) for record in records if can_view_record(current_user, "crm", record)]


@router.post("/opportunities", response_model=CRMRecordRead, status_code=201)
async def create_opportunity(
    data: CRMRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_CREATE_PERMISSIONS)),
):
    data.record_type = CRMRecordType.OPPORTUNITY
    ensure_commercial_action_allowed(current_user, CRMRecord(**data.model_dump()), "create", "crm")
    return _record_read(await svc.create_record(db, data), current_user)


@router.get("/records", response_model=List[CRMRecordRead])
async def list_all_records(
    record_type: Optional[str] = None,
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = await svc.get_records(db, record_type=record_type, status=status,
                                    assigned_rep_id=assigned_rep_id, stage_id=stage_id,
                                    temperature=temperature, skip=skip, limit=limit)
    return [_record_read(record, current_user) for record in records if can_view_record(current_user, "crm", record)]


@router.post("/records", response_model=CRMRecordRead, status_code=201)
async def create_record(
    data: CRMRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_CREATE_PERMISSIONS)),
):
    ensure_commercial_action_allowed(current_user, CRMRecord(**data.model_dump()), "create", "crm")
    return _record_read(await svc.create_record(db, data), current_user)


@router.get("/records/{record_id}", response_model=CRMRecordRead)
async def get_record(record_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rec = await svc.get_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, rec, "view", "crm")
    return _record_read(rec, current_user)


@router.patch("/records/{record_id}", response_model=CRMRecordRead)
async def update_record(
    record_id: str,
    data: CRMRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS)),
):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.update_record(db, record_id, data, actor_id=current_user.id)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/qualify", response_model=CRMRecordRead)
async def qualify_record(record_id: str, data: CRMQualifyRequest, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.qualify_record(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/convert-to-opportunity", response_model=CRMRecordRead)
async def convert_to_opportunity(record_id: str, data: CRMConvertRequest, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "convert", "crm")
    rec = await svc.convert_to_opportunity(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/close-won", response_model=CRMRecordRead)
async def close_won(record_id: str, data: CRMCloseWonRequest, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.close_won(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/customer")
async def ensure_record_customer(record_id: str, db: AsyncSession = Depends(get_db),
                                 current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    """M47.S01.T002: create (or link an existing) customer for this lead/opportunity."""
    from app.core.access_control import can_modify_record
    from app.services.crm_customer_link_service import ensure_customer

    rec = await _scoped_record(db, _uuid(record_id), current_user, "view")   # WON records are not "editable"
    if not can_modify_record(current_user, "crm", "edit", rec):              # but linking a customer needs edit scope
        raise HTTPException(403, "You can link a customer only to records in your edit scope.")
    if getattr(rec.status, "value", rec.status) == "LOST":
        raise HTTPException(409, "A lost record does not become a customer.")
    cust, created = await ensure_customer(db, rec, current_user)
    await db.commit()
    return {"customer_id": str(cust.id), "customer_code": cust.code, "customer_name": cust.name, "created": created}


@router.post("/records/{record_id}/close-lost", response_model=CRMRecordRead)
async def close_lost(record_id: str, data: CRMCloseLostRequest, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.close_lost(db, record_id, data)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/on-hold", response_model=CRMRecordRead)
async def put_on_hold(record_id: str, notes: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.put_on_hold(db, record_id, notes)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/reopen", response_model=CRMRecordRead)
async def reopen_record(record_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    existing = await svc.get_record(db, record_id)
    if not existing:
        raise HTTPException(404, "Record not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    rec = await svc.reopen_record(db, record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(rec, current_user)


@router.post("/records/{record_id}/update-score", response_model=CRMRecordRead)
async def update_lead_score(record_id: str, db: AsyncSession = Depends(get_db),
                            current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    await _scoped_record(db, record_id, current_user, "edit")
    rec = await intel.rescore_record(db, record_id, current_user.username)
    if not rec:
        raise HTTPException(404, "Record not found")
    return _record_read(await svc.get_record(db, record_id), current_user)


@router.get("/records/{record_id}/score-history")
async def get_score_history(record_id: str, db: AsyncSession = Depends(get_db),
                            current_user=Depends(get_current_user)):
    """Every score change with the rule-by-rule breakdown that explains it."""
    await _scoped_record(db, record_id, current_user, "view")
    return await intel.score_history(db, record_id)


# ── Interest Lines ────────────────────────────────────────────────────────────

@router.post("/records/{record_id}/interest-lines", response_model=CRMInterestLineRead, status_code=201)
async def add_interest_line(record_id: str, data: CRMInterestLineCreate, db: AsyncSession = Depends(get_db),
                            current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    if str(data.crm_record_id) != record_id:
        raise HTTPException(422, "crm_record_id must match the record in the path.")
    await _scoped_record(db, record_id, current_user, "edit")
    return await svc.add_interest_line(db, data)


@router.delete("/interest-lines/{line_id}", status_code=204)
async def delete_interest_line(line_id: str, db: AsyncSession = Depends(get_db),
                               current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    line = await db.get(CRMInterestLine, _uuid(line_id))
    if line is None:
        raise HTTPException(404, "Interest line not found")
    await _scoped_record(db, line.crm_record_id, current_user, "edit")
    if not await svc.delete_interest_line(db, line_id):
        raise HTTPException(404, "Interest line not found")


# ── Activities ────────────────────────────────────────────────────────────────

@router.get("/activities", response_model=List[CRMActivityRead])
async def list_activities(
    record_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    result_status: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if record_id:
        await _scoped_record(db, record_id, current_user, "view")
    elif not has_any_permission(current_user, CRM_BROAD_VIEW):
        raise HTTPException(403, "Listing activities across records needs company-wide CRM view; pass record_id.")
    return await svc.get_activities(db, record_id=record_id, assigned_to=assigned_to,
                                     result_status=result_status, overdue_only=overdue_only,
                                     skip=skip, limit=limit)


@router.post("/activities", response_model=CRMActivityRead, status_code=201)
async def create_activity(data: CRMActivityCreate, db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    await _scoped_record(db, data.crm_record_id, current_user, "edit")
    return await svc.create_activity(db, data)


@router.post("/activities/{activity_id}/complete", response_model=CRMActivityRead)
async def complete_activity(activity_id: str, data: CRMActivityComplete, db: AsyncSession = Depends(get_db),
                            current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    activity = await db.get(CRMActivity, _uuid(activity_id))
    if activity is None:
        raise HTTPException(404, "Activity not found")
    await _scoped_record(db, activity.crm_record_id, current_user, "edit")
    act = await svc.complete_activity(db, activity_id, data)
    if not act:
        raise HTTPException(404, "Activity not found")
    return act


# ── Competitors ───────────────────────────────────────────────────────────────

@router.post("/competitors", response_model=CRMCompetitorRead, status_code=201)
async def add_competitor(data: CRMCompetitorCreate, db: AsyncSession = Depends(get_db),
                         current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    await _scoped_record(db, data.crm_record_id, current_user, "edit")
    return await svc.add_competitor(db, data)


# ── Deduplication ─────────────────────────────────────────────────────────────

@router.get("/check-duplicates", response_model=List[CRMRecordRead], dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def check_duplicates(
    company_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.check_duplicates(db, company_name, email, phone)


# ── Dashboard & Reports ───────────────────────────────────────────────────────

@router.get("/dashboard", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


@router.get("/forecast", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def get_forecast(months_ahead: int = 6, pipeline_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_forecast(db, months_ahead=months_ahead, pipeline_id=pipeline_id)


@router.get("/reports/pipeline", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def pipeline_report(db: AsyncSession = Depends(get_db)):
    return await svc.pipeline_report(db)


@router.get("/reports/win-loss", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def win_loss_report(db: AsyncSession = Depends(get_db)):
    return await svc.win_loss_report(db)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-lead-prioritization", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def run_lead_prioritization(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_lead_prioritization(db)
    return {"generated": len(recs), "message": f"Lead Prioritization agent generated {len(recs)} recommendations"}


@router.post("/ai/run-pipeline-risk", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def run_pipeline_risk(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_pipeline_risk(db)
    return {"generated": len(recs), "message": f"Pipeline Risk agent generated {len(recs)} recommendations"}


@router.post("/ai/run-win-loss-insight", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def run_win_loss_insight(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_win_loss_insight(db)
    return {"generated": len(recs), "message": f"Win/Loss Insight agent generated {len(recs)} recommendations"}


@router.get("/ai/recommendations", response_model=List[CRMAIRecRead], dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def get_ai_recommendations(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_ai_recommendations(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=CRMAIRecRead, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def ack_recommendation(rec_id: str, data: CRMAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_recommendation(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec


# ── Territory Management ──────────────────────────────────────────────────────

@router.get("/territories", response_model=List[CRMTerritoryRead])
async def list_territories(active_only: bool = False, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    territories = await svc.get_territories(db, active_only=active_only)
    return [_territory_read(territory, current_user) for territory in territories if can_view_record(current_user, "crm", territory)]


@router.post("/territories", response_model=CRMTerritoryRead, status_code=201)
async def create_territory(
    data: CRMTerritoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_CREATE_PERMISSIONS)),
):
    ensure_commercial_action_allowed(current_user, CRMTerritory(**data.model_dump()), "create", "crm")
    return _territory_read(await svc.create_territory(db, data), current_user)


@router.patch("/territories/{territory_id}", response_model=CRMTerritoryRead)
async def update_territory(
    territory_id: str,
    data: CRMTerritoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS)),
):
    existing = next((territory for territory in await svc.get_territories(db, active_only=False) if str(territory.id) == str(territory_id)), None)
    if not existing:
        raise HTTPException(404, "Territory not found")
    ensure_commercial_action_allowed(current_user, existing, "edit", "crm")
    result = await svc.update_territory(db, territory_id, data)
    if not result:
        raise HTTPException(404, "Territory not found")
    return _territory_read(result, current_user)


@router.get("/territories/performance", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def territory_performance(db: AsyncSession = Depends(get_db)):
    return await svc.get_territory_performance(db)


# ── Customer 360 View ─────────────────────────────────────────────────────────

@router.get("/records/{record_id}/360")
async def get_record_360(record_id: str, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    await _scoped_record(db, record_id, current_user, "view")
    view = await svc.get_record_360(db, record_id)
    if not view:
        raise HTTPException(404, "Record not found")
    return view


# ── M36.S02 lead scoring rules, prioritised queue ─────────────────────────────

class ScoreRuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: Literal["FIT", "ENGAGEMENT"] = "FIT"
    field: str
    operator: str
    value: Optional[str] = Field(None, max_length=500)
    points: int = Field(ge=-100, le=100)
    max_points: Optional[int] = Field(None, ge=0, le=100)
    active_flag: bool = True
    sequence_no: int = 0


class ScoreRulePatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    value: Optional[str] = Field(None, max_length=500)
    points: Optional[int] = Field(None, ge=-100, le=100)
    max_points: Optional[int] = Field(None, ge=0, le=100)
    active_flag: Optional[bool] = None
    sequence_no: Optional[int] = None


def _rule_out(r: CRMScoreRule) -> dict:
    return {"id": str(r.id), "name": r.name, "category": r.category, "field": r.field, "operator": r.operator,
            "value": r.value, "points": r.points, "max_points": r.max_points, "active_flag": r.active_flag,
            "sequence_no": r.sequence_no}


@router.get("/score-rules", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_score_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CRMScoreRule).order_by(CRMScoreRule.sequence_no, CRMScoreRule.name))).scalars().all()
    defaults = [vars(r) for r in intel.DEFAULT_RULES] if not any(r.active_flag for r in rows) else []
    return {"rules": [_rule_out(r) for r in rows], "using_defaults": bool(defaults), "defaults": defaults,
            "fields": {k: v[1] for k, v in intel.SCORE_FIELDS.items()}}


@router.post("/score-rules", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_score_rule(body: ScoreRuleIn, db: AsyncSession = Depends(get_db)):
    try:
        intel.validate_rule(body.field, body.operator, body.value)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    rule = CRMScoreRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    return _rule_out(rule)


@router.patch("/score-rules/{rule_id}", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def update_score_rule(rule_id: str, body: ScoreRulePatch, db: AsyncSession = Depends(get_db)):
    rule = await db.get(CRMScoreRule, _uuid(rule_id))
    if rule is None:
        raise HTTPException(404, "Rule not found")
    changes = body.model_dump(exclude_unset=True)
    try:
        intel.validate_rule(rule.field, rule.operator, changes.get("value", rule.value))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    for k, v in changes.items():
        setattr(rule, k, v)
    await db.commit()
    return _rule_out(rule)


@router.post("/score-rules/seed-defaults", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def seed_score_rules(db: AsyncSession = Depends(get_db)):
    """Copy the built-in rules into editable rows (only when no rules exist yet)."""
    if (await db.execute(select(CRMScoreRule.id).limit(1))).first():
        raise HTTPException(409, "Score rules already exist.")
    for n, r in enumerate(intel.DEFAULT_RULES):
        db.add(CRMScoreRule(name=r.name, category=r.category, field=r.field, operator=r.operator, value=r.value,
                            points=r.points, max_points=r.max_points, sequence_no=n))
    await db.commit()
    return {"created": len(intel.DEFAULT_RULES)}


@router.post("/scores/recalculate", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def recalculate_scores(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await intel.rescore_all(db, current_user.username)


@router.get("/scores/queue")
async def lead_score_queue(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db),
                           current_user=Depends(get_current_user)):
    """Open leads the caller may see, best score first, each with why it scored that way."""
    out, offset, batch = [], 0, max(limit, 100)
    while len(out) < limit:  # scoped users: keep paging until enough visible leads or none left
        rows = await intel.score_queue_candidates(db, batch, offset)
        offset += batch
        for record, breakdown in rows:
            if not can_view_record(current_user, "crm", record):
                continue
            out.append({"id": str(record.id), "lead_code": record.lead_code, "company_name": record.company_name,
                        "lead_score": record.lead_score or 0, "temperature": getattr(record.temperature, "value", record.temperature),
                        "assigned_rep_id": record.assigned_rep_id, "breakdown": breakdown})
        if len(rows) < batch:
            break
    return out[:limit]


# ── M36.S02 forecast detail and snapshots, funnel analytics ────────────────────

@router.get("/forecast/detail", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def forecast_detail(months_ahead: int = Query(6, ge=1, le=24), assigned_rep_id: Optional[str] = None,
                          territory_id: Optional[str] = None, stage_id: Optional[str] = None,
                          db: AsyncSession = Depends(get_db)):
    try:
        return await intel.forecast_detail(db, months_ahead, assigned_rep_id, territory_id, stage_id)
    except ValueError:
        raise HTTPException(422, "territory_id and stage_id must be UUIDs")


class SnapshotIn(BaseModel):
    label: Optional[str] = Field(None, max_length=150)
    months_ahead: int = Field(6, ge=1, le=24)
    assigned_rep_id: Optional[str] = None
    territory_id: Optional[str] = None
    stage_id: Optional[str] = None


@router.post("/forecast/snapshots", status_code=201, dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def create_forecast_snapshot(body: SnapshotIn, db: AsyncSession = Depends(get_db),
                                   current_user=Depends(get_current_user)):
    try:
        detail = await intel.forecast_detail(db, body.months_ahead, body.assigned_rep_id, body.territory_id, body.stage_id)
    except ValueError:
        raise HTTPException(422, "territory_id and stage_id must be UUIDs")
    return intel.snapshot_out(await intel.save_snapshot(db, detail, body.label, current_user.id), with_rows=True)


@router.get("/forecast/snapshots", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_forecast_snapshots(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CRMForecastSnapshot).order_by(CRMForecastSnapshot.taken_at.desc()).limit(limit))).scalars()
    return [intel.snapshot_out(s) for s in rows]


@router.get("/forecast/snapshots/{snapshot_id}", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def get_forecast_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    snap = await db.get(CRMForecastSnapshot, _uuid(snapshot_id))
    if snap is None:
        raise HTTPException(404, "Snapshot not found")
    return intel.snapshot_out(snap, with_rows=True)


@router.get("/reports/funnel", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def funnel_report(date_from: Optional[date] = None, date_to: Optional[date] = None,
                        assigned_rep_id: Optional[str] = None, territory_id: Optional[str] = None,
                        pipeline_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Stage conversion, aging of open records, rep performance and loss reasons for records created in range."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must not be after date_to")
    try:
        return await intel.funnel(db, date_from, date_to, assigned_rep_id, territory_id, pipeline_id)
    except ValueError:
        raise HTTPException(422, "territory_id and pipeline_id must be UUIDs")


# ── M36.S03.T002 unified customer timeline ─────────────────────────────────────

@router.get("/customers/{customer_id}/timeline")
async def customer_timeline(customer_id: str, limit: int = Query(50, ge=1, le=200), before: Optional[str] = None,
                            types: Optional[str] = Query(None, description="comma-separated event types"),
                            db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Newest-first events touching the customer. Each source is shown only with its own view permission;
    `hidden_sources` lists what the caller may not see. Page with `before` = previous `next`."""
    from app.models.sales import Customer
    from app.services import customer_timeline_service as timeline_svc

    customer = await db.get(Customer, _uuid(customer_id))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    if not (can_view_record(current_user, "crm", customer) or can_view_record(current_user, "sales", customer)):
        raise HTTPException(403, "Customer is outside your commercial scope.")
    try:
        result = await timeline_svc.timeline(db, customer.id, current_user, limit, before,
                                             {t.strip() for t in types.split(",") if t.strip()} if types else None)
    except ValueError:
        raise HTTPException(422, "before must be a cursor returned as `next`.")
    return {"customer": {"id": str(customer.id), "code": customer.code, "name": customer.name}, **result}


# ── M36.S02.T001 website lead forms (admin) ────────────────────────────────────

class LeadFormIn(BaseModel):
    slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=200)
    intro: Optional[str] = Field(None, max_length=2000)
    consent_text: Optional[str] = Field(None, max_length=2000)
    require_consent: bool = True
    success_message: Optional[str] = Field(None, max_length=300)
    active_flag: bool = True
    assigned_rep_id: Optional[str] = Field(None, max_length=50)
    territory_id: Optional[str] = None
    company_id: Optional[str] = None
    branch_id: Optional[str] = None
    sales_region_id: Optional[str] = Field(None, max_length=100)
    sales_team_id: Optional[str] = Field(None, max_length=100)


class LeadFormPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    intro: Optional[str] = Field(None, max_length=2000)
    consent_text: Optional[str] = Field(None, max_length=2000)
    require_consent: Optional[bool] = None
    success_message: Optional[str] = Field(None, max_length=300)
    active_flag: Optional[bool] = None
    assigned_rep_id: Optional[str] = Field(None, max_length=50)
    sales_region_id: Optional[str] = Field(None, max_length=100)
    sales_team_id: Optional[str] = Field(None, max_length=100)


async def _check_form_refs(db: AsyncSession, data: dict) -> None:
    """Lead forms stamp their scope on every lead: referenced territory/company/branch must exist."""
    from app.models.company import Branch, Company

    for key, model in (("territory_id", CRMTerritory), ("company_id", Company), ("branch_id", Branch)):
        if data.get(key):
            data[key] = _uuid(data[key])
            if await db.get(model, data[key]) is None:
                raise HTTPException(422, f"{key} does not exist.")
        else:
            data[key] = None


def _form_out(f) -> dict:
    return {"id": str(f.id), "slug": f.slug, "name": f.name, "title": f.title, "intro": f.intro,
            "consent_text": f.consent_text, "require_consent": f.require_consent, "success_message": f.success_message,
            "active_flag": f.active_flag, "assigned_rep_id": f.assigned_rep_id,
            "territory_id": str(f.territory_id) if f.territory_id else None,
            "company_id": str(f.company_id) if f.company_id else None,
            "branch_id": str(f.branch_id) if f.branch_id else None,
            "sales_region_id": f.sales_region_id, "sales_team_id": f.sales_team_id}


@router.get("/lead-forms", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_lead_forms(db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMLeadForm

    return [_form_out(f) for f in (await db.execute(select(CRMLeadForm).order_by(CRMLeadForm.name))).scalars()]


@router.post("/lead-forms", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_lead_form(body: LeadFormIn, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMLeadForm

    if body.require_consent and not (body.consent_text or "").strip():
        raise HTTPException(422, "consent_text is required when consent is required.")
    if (await db.execute(select(CRMLeadForm.id).where(CRMLeadForm.slug == body.slug))).first():
        raise HTTPException(409, "A form with this slug already exists.")
    data = body.model_dump()
    await _check_form_refs(db, data)
    form = CRMLeadForm(**data)
    db.add(form)
    await db.commit()
    return _form_out(form)


@router.patch("/lead-forms/{form_id}", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def update_lead_form(form_id: str, body: LeadFormPatch, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMLeadForm

    form = await db.get(CRMLeadForm, _uuid(form_id))
    if form is None:
        raise HTTPException(404, "Form not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is None and k in ("name", "title", "require_consent", "active_flag"):
            raise HTTPException(422, f"{k} cannot be empty.")
        setattr(form, k, v)
    if form.require_consent and not (form.consent_text or "").strip():
        raise HTTPException(422, "consent_text is required when consent is required.")
    await db.commit()
    return _form_out(form)


@router.get("/lead-forms/{form_id}/submissions", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_lead_submissions(form_id: str, limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMLeadSubmission

    rows = (await db.execute(select(CRMLeadSubmission).where(CRMLeadSubmission.form_id == _uuid(form_id))
                             .order_by(CRMLeadSubmission.received_at.desc()).limit(limit))).scalars()
    return [{"id": str(r.id), "received_at": r.received_at.isoformat(), "status": r.status,
             "crm_record_id": str(r.crm_record_id) if r.crm_record_id else None, "contact_email": r.contact_email,
             "consent_given": r.consent_given, "utm_source": r.utm_source, "utm_medium": r.utm_medium,
             "utm_campaign": r.utm_campaign, "referrer": r.referrer, "landing_page": r.landing_page} for r in rows]


# ── M36.S01.T004 CRM workflow automation ───────────────────────────────────────

class AutomationRuleIn(BaseModel):
    rule_name: str = Field(min_length=1, max_length=200)
    trigger_event: str
    condition_field: Optional[str] = None
    condition_operator: Optional[str] = None
    condition_value: Optional[str] = Field(None, max_length=500)
    action_type: str
    action_payload: dict = Field(default_factory=dict)
    active_flag: bool = True
    notes: Optional[str] = Field(None, max_length=2000)


class AutomationRulePatch(BaseModel):
    rule_name: Optional[str] = Field(None, min_length=1, max_length=200)
    active_flag: Optional[bool] = None
    action_payload: Optional[dict] = None
    condition_value: Optional[str] = Field(None, max_length=500)


def _auto_rule_out(r) -> dict:
    return {"rule_id": r.rule_id, "rule_name": r.rule_name, "trigger_event": r.trigger_event,
            "condition_field": r.condition_field, "condition_operator": r.condition_operator,
            "condition_value": r.condition_value, "action_type": r.action_type, "action_payload": r.action_payload or {},
            "active_flag": r.active_flag, "created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/automation/rules", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_automation_rules(db: AsyncSession = Depends(get_db)):
    from app.models.custom_fields import EntityType, WorkflowTriggerRule
    from app.services import crm_automation_service as auto

    rows = (await db.execute(select(WorkflowTriggerRule).where(WorkflowTriggerRule.entity_type == EntityType.CRM_RECORD)
                             .order_by(WorkflowTriggerRule.created_at))).scalars()
    return {"rules": [_auto_rule_out(r) for r in rows], "triggers": list(auto.TRIGGERS), "actions": list(auto.ACTIONS),
            "condition_fields": list(auto.CONDITION_FIELDS), "settable_fields": auto.SETTABLE}


@router.post("/automation/rules", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_automation_rule(body: AutomationRuleIn, db: AsyncSession = Depends(get_db),
                                 current_user=Depends(get_current_user)):
    from app.models.custom_fields import EntityType, WorkflowTriggerRule
    from app.services import crm_automation_service as auto

    from datetime import datetime as _dt, timezone as _tz

    try:
        auto.validate(body.trigger_event, body.condition_field, body.condition_operator, body.action_type, body.action_payload)
        if body.action_type == "notify":
            await auto.check_recipients(db, body.action_payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    now = _dt.now(_tz.utc)
    rule = WorkflowTriggerRule(entity_type=EntityType.CRM_RECORD, created_by=current_user.username,
                               activated_at=now, enqueued_until=now, **body.model_dump())
    db.add(rule)
    await db.commit()
    return _auto_rule_out(rule)


@router.patch("/automation/rules/{rule_id}", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def update_automation_rule(rule_id: str, body: AutomationRulePatch, db: AsyncSession = Depends(get_db)):
    from app.models.custom_fields import EntityType, WorkflowTriggerRule
    from app.services import crm_automation_service as auto

    rule = (await db.execute(select(WorkflowTriggerRule).where(
        WorkflowTriggerRule.rule_id == rule_id, WorkflowTriggerRule.entity_type == EntityType.CRM_RECORD))).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "Rule not found")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("rule_name", "x") is None or changes.get("active_flag", True) is None:
        raise HTTPException(422, "rule_name and active_flag cannot be empty")
    payload = changes["action_payload"] if "action_payload" in changes else (rule.action_payload or {})
    try:
        auto.validate(rule.trigger_event, rule.condition_field, rule.condition_operator, rule.action_type, payload)
        if rule.action_type == "notify" and "action_payload" in changes:
            await auto.check_recipients(db, payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc))
    reactivated = changes.get("active_flag") is True and not rule.active_flag
    for k, v in changes.items():
        setattr(rule, k, v)
    if reactivated or "condition_value" in changes:  # no replay of events from the paused/old-condition period
        from datetime import datetime as _dt, timezone as _tz

        rule.activated_at = rule.enqueued_until = _dt.now(_tz.utc)
    await db.commit()
    return _auto_rule_out(rule)


@router.get("/automation/runs", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_automation_runs(status: Optional[str] = None, limit: int = Query(100, ge=1, le=500),
                               db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMAutomationRun

    q = select(CRMAutomationRun, CRMRecord.company_name).join(CRMRecord, CRMRecord.id == CRMAutomationRun.crm_record_id)
    if status:
        q = q.where(CRMAutomationRun.status == status.upper())
    rows = (await db.execute(q.order_by(CRMAutomationRun.created_at.desc()).limit(limit))).all()
    return [{"id": str(r.id), "rule_id": r.rule_id, "rule_name": r.rule_name, "event_type": r.event_type,
             "crm_record_id": str(r.crm_record_id), "company_name": name, "status": r.status, "attempts": r.attempts,
             "result": r.result, "error": r.error, "created_at": r.created_at.isoformat(),
             "finished_at": r.finished_at.isoformat() if r.finished_at else None} for r, name in rows]


@router.post("/automation/runs/{run_id}/retry", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def retry_automation_run(run_id: str, db: AsyncSession = Depends(get_db)):
    from datetime import datetime as _dt, timezone as _tz

    from app.models.crm import CRMAutomationRun

    run = await db.get(CRMAutomationRun, _uuid(run_id))
    if run is None:
        raise HTTPException(404, "Run not found")
    if run.status != "FAILED":
        raise HTTPException(409, "Only failed runs can be retried.")
    run.status, run.attempts, run.next_attempt_at, run.finished_at = "PENDING", 0, _dt.now(_tz.utc), None
    await db.commit()
    return {"status": "PENDING"}


@router.post("/automation/process", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def process_automation_now(db: AsyncSession = Depends(get_db)):
    """Run one automation tick now (the background task does this every 15 seconds)."""
    from app.services import crm_automation_service as auto

    queued = await auto.enqueue(db)
    return {"queued": queued, **await auto.process(db)}


# ── M36 consent register and outbox ───────────────────────────────────────────

class OutboxIn(BaseModel):
    to_email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject: str = Field(min_length=1, max_length=300, pattern=r"^[^\r\n]+$")
    body: str = Field(min_length=1, max_length=20000)
    crm_record_id: Optional[str] = None
    track_engagement: bool = False       # M43.S01.T006 opt-in open/click tracking
    signature_id: Optional[str] = None   # M43.S01.T013 one of the sender's signatures


MANUAL_DAILY_CAP = 100


class ConsentIn(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    status: Literal["SUBSCRIBED", "UNSUBSCRIBED", "BOUNCED", "COMPLAINED"]
    consent_text: Optional[str] = Field(None, max_length=2000)


def _msg_out(m) -> dict:
    return {"id": str(m.id), "purpose": m.purpose, "to_email": m.to_email, "subject": m.subject, "status": m.status,
            "status_reason": m.status_reason, "attempts": m.attempts,
            "crm_record_id": str(m.crm_record_id) if m.crm_record_id else None,
            "created_by": m.created_by, "created_at": m.created_at.isoformat(),
            "sent_at": m.sent_at.isoformat() if m.sent_at else None}


@router.get("/outbox", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_outbox(status: Optional[str] = None, limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    from app.core.config import settings
    from app.models.crm import CRMOutboundMessage

    q = select(CRMOutboundMessage)
    if status:
        q = q.where(CRMOutboundMessage.status == status.upper())
    rows = (await db.execute(q.order_by(CRMOutboundMessage.created_at.desc()).limit(limit))).scalars()
    return {"delivery_enabled": bool(settings.CRM_OUTBOUND_EMAIL_ENABLED and settings.SMTP_HOST),
            "messages": [_msg_out(m) for m in rows]}


@router.post("/outbox", status_code=201)
async def queue_email(body: OutboxIn, db: AsyncSession = Depends(get_db),
                      current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    """One-to-one e-mail to the contact of a CRM record the caller may edit (MANUAL). Free addresses need
    company-wide CRM edit. Suppressed addresses are never mailed; each user may queue 100 a day."""
    import uuid as _u
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz

    from app.models.crm import CRMOutboundMessage
    from app.models.sales import Customer
    from app.services import crm_outbound_service as outbound

    record_id = None
    to = outbound.norm(body.to_email)
    if body.crm_record_id:
        rec = await _scoped_record(db, body.crm_record_id, current_user, "edit")
        known = {outbound.norm(rec.contact_email or "")}
        if rec.assigned_customer_id:
            cust = await db.get(Customer, rec.assigned_customer_id)
            known.add(outbound.norm(cust.email or "") if cust else "")
        if to not in known:
            raise HTTPException(422, "The address must be the record's contact e-mail.")
        record_id = rec.id
    elif not has_any_permission(current_user, CRM_CONFIG):
        raise HTTPException(403, "E-mail must be sent from a CRM record (or by a company-wide CRM editor).")
    sent_today = (await db.execute(select(func.count()).where(
        CRMOutboundMessage.created_by == current_user.username, CRMOutboundMessage.purpose == "MANUAL",
        CRMOutboundMessage.created_at >= _dt.now(_tz.utc) - _td(days=1)))).scalar()
    if sent_today >= MANUAL_DAILY_CAP:
        raise HTTPException(429, "Daily e-mail limit reached.")
    text = body.body
    if body.signature_id:
        from app.models.crm import CRMEmailSignature
        sig = await db.get(CRMEmailSignature, _uuid(body.signature_id))
        if sig is None or sig.user_id != current_user.id:
            raise HTTPException(422, "Unknown signature")
        text = f"{text}\n\n{sig.body}"
    msg = await outbound.queue(db, to_email=body.to_email, subject=body.subject, body=text, purpose="MANUAL",
                               dedupe_key=f"manual:{_u.uuid4()}", crm_record_id=record_id, created_by=current_user.username,
                               track=body.track_engagement)
    await db.commit()
    return _msg_out(msg)


@router.post("/outbox/{message_id}/cancel", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def cancel_email(message_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMOutboundMessage

    from sqlalchemy import update as _update

    done = (await db.execute(_update(CRMOutboundMessage).where(  # atomic: never cancels a message being sent
        CRMOutboundMessage.id == _uuid(message_id), CRMOutboundMessage.status == "QUEUED")
        .values(status="CANCELLED", status_reason="cancelled by user"))).rowcount
    await db.commit()
    msg = await db.get(CRMOutboundMessage, _uuid(message_id))
    if msg is None:
        raise HTTPException(404, "Message not found")
    if not done:
        raise HTTPException(409, "Only queued messages can be cancelled.")
    await db.refresh(msg)
    return _msg_out(msg)


@router.post("/outbox/{message_id}/retry", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def retry_email(message_id: str, db: AsyncSession = Depends(get_db)):
    """Re-queue a FAILED message after a person checked it was not delivered."""
    from datetime import datetime as _dt, timezone as _tz

    from sqlalchemy import update as _update

    from app.models.crm import CRMOutboundMessage

    done = (await db.execute(_update(CRMOutboundMessage).where(
        CRMOutboundMessage.id == _uuid(message_id), CRMOutboundMessage.status == "FAILED")
        .values(status="QUEUED", attempts=0, status_reason="re-queued by user", next_attempt_at=_dt.now(_tz.utc)))).rowcount
    await db.commit()
    if not done:
        raise HTTPException(409, "Only failed messages can be retried.")
    return {"status": "QUEUED"}


@router.get("/consents", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def list_consents(status: Optional[str] = None, email: Optional[str] = None,
                        limit: int = Query(200, ge=1, le=1000), db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMContactConsent

    q = select(CRMContactConsent)
    if status:
        q = q.where(CRMContactConsent.status == status.upper())
    if email:
        q = q.where(CRMContactConsent.email == email.strip().lower())
    rows = (await db.execute(q.order_by(CRMContactConsent.updated_at.desc()).limit(limit))).scalars()
    return [{"email": r.email, "status": r.status, "source": r.source, "updated_at": r.updated_at.isoformat()} for r in rows]


@router.post("/consents", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def set_consent(body: ConsentIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Record a consent event by hand (e.g. a signed paper form, a bounce report, a phone opt-out)."""
    from app.services import crm_outbound_service as outbound

    row = await outbound.record_consent(db, body.email, body.status, f"manual:{current_user.username}", body.consent_text,
                                        may_lift_unsubscribe=True)  # an authorised person recording proof
    await db.commit()
    return {"email": row.email, "status": row.status, "source": row.source}


# ── M36.S01.T002 sales sequences ──────────────────────────────────────────────

class SequenceStepIn(BaseModel):
    step_no: int = Field(ge=1, le=50)
    delay_days: int = Field(0, ge=0, le=365)
    subject: str = Field(min_length=1, max_length=300, pattern=r"^[^\r\n]+$")
    body: str = Field(min_length=1, max_length=20000)


class SequenceIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    notes: Optional[str] = Field(None, max_length=2000)
    steps: List[SequenceStepIn] = Field(min_length=1, max_length=50)
    track_engagement: bool = False


def _seq_out(seq, steps, counts) -> dict:
    return {"id": str(seq.id), "name": seq.name, "active_flag": seq.active_flag, "notes": seq.notes,
            "track_engagement": bool(seq.track_engagement),
            "steps": [{"step_no": s.step_no, "delay_days": s.delay_days, "subject": s.subject, "body": s.body} for s in steps],
            "enrollments": counts}


@router.get("/sequences", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_sequences(db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMSequence, CRMSequenceEnrollment, CRMSequenceStep

    out = []
    for seq in (await db.execute(select(CRMSequence).order_by(CRMSequence.name))).scalars().all():
        steps = (await db.execute(select(CRMSequenceStep).where(CRMSequenceStep.sequence_id == seq.id)
                                  .order_by(CRMSequenceStep.step_no))).scalars().all()
        counts = dict((await db.execute(select(CRMSequenceEnrollment.status, func.count()).where(
            CRMSequenceEnrollment.sequence_id == seq.id).group_by(CRMSequenceEnrollment.status))).all())
        out.append(_seq_out(seq, steps, counts))
    return out


@router.post("/sequences", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_sequence(body: SequenceIn, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMSequence, CRMSequenceStep

    if len({s.step_no for s in body.steps}) != len(body.steps):
        raise HTTPException(422, "step numbers must be unique")
    if (await db.execute(select(CRMSequence.id).where(CRMSequence.name == body.name))).first():
        raise HTTPException(409, "A sequence with this name exists.")
    from sqlalchemy.exc import IntegrityError as _IntegrityError

    seq = CRMSequence(name=body.name, notes=body.notes, track_engagement=body.track_engagement)
    db.add(seq)
    try:
        await db.flush()
    except _IntegrityError:
        await db.rollback()
        raise HTTPException(409, "A sequence with this name exists.")
    steps = [CRMSequenceStep(sequence_id=seq.id, **s.model_dump()) for s in sorted(body.steps, key=lambda s: s.step_no)]
    db.add_all(steps)
    await db.commit()
    return _seq_out(seq, steps, {})


@router.patch("/sequences/{sequence_id}", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def pause_sequence(sequence_id: str, active_flag: bool, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMSequence

    seq = await db.get(CRMSequence, _uuid(sequence_id))
    if seq is None:
        raise HTTPException(404, "Sequence not found")
    seq.active_flag = active_flag
    await db.commit()
    return {"id": str(seq.id), "active_flag": seq.active_flag}


@router.post("/sequences/{sequence_id}/enroll", status_code=201)
async def enroll_record(sequence_id: str, record_id: str, db: AsyncSession = Depends(get_db),
                        current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    from app.models.crm import CRMSequence
    from app.services import crm_sequence_service as sequences

    seq = await db.get(CRMSequence, _uuid(sequence_id))
    if seq is None:
        raise HTTPException(404, "Sequence not found")
    record = await _scoped_record(db, record_id, current_user, "edit")
    try:
        row = await sequences.enroll(db, seq, record, current_user.username)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    await db.commit()
    return {"id": str(row.id), "status": row.status, "next_step_no": row.next_step_no, "next_due_at": row.next_due_at.isoformat()}


@router.get("/sequences/{sequence_id}/enrollments", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_enrollments(sequence_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMSequenceEnrollment

    rows = (await db.execute(select(CRMSequenceEnrollment, CRMRecord.company_name).join(
        CRMRecord, CRMRecord.id == CRMSequenceEnrollment.crm_record_id).where(
        CRMSequenceEnrollment.sequence_id == _uuid(sequence_id)).order_by(CRMSequenceEnrollment.enrolled_at.desc()))).all()
    return [{"id": str(e.id), "crm_record_id": str(e.crm_record_id), "company_name": name, "email": e.email,
             "status": e.status, "stop_reason": e.stop_reason, "next_step_no": e.next_step_no,
             "next_due_at": e.next_due_at.isoformat(), "enrolled_at": e.enrolled_at.isoformat()} for e, name in rows]


@router.post("/sequence-enrollments/{enrollment_id}/stop")
async def stop_enrollment(enrollment_id: str, reason: str = Query("stopped by user", max_length=200),
                          db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    """Stop an enrolment, e.g. when the contact replied by phone or the rep logged a reply."""
    from datetime import datetime as _dt, timezone as _tz

    from app.models.crm import CRMSequenceEnrollment

    e = await db.get(CRMSequenceEnrollment, _uuid(enrollment_id))
    if e is None:
        raise HTTPException(404, "Enrollment not found")
    await _scoped_record(db, e.crm_record_id, current_user, "edit")
    if e.status != "ACTIVE":
        raise HTTPException(409, "Enrollment is not active.")
    from sqlalchemy import update as _update

    from app.models.crm import CRMOutboundMessage

    e.status, e.stop_reason, e.finished_at = "STOPPED", reason, _dt.now(_tz.utc)
    cancelled = (await db.execute(_update(CRMOutboundMessage).where(  # already-queued step mail is withdrawn too
        CRMOutboundMessage.dedupe_key.like(f"seq:{e.id}:%"), CRMOutboundMessage.status == "QUEUED")
        .values(status="CANCELLED", status_reason="sequence stopped"))).rowcount
    await db.commit()
    return {"id": str(e.id), "status": e.status, "cancelled_messages": cancelled}


# ── M36.S02.T005 segment e-mail campaigns ─────────────────────────────────────

class EmailCampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    subject: str = Field(min_length=1, max_length=300, pattern=r"^[^\r\n]+$")
    body: str = Field(min_length=1, max_length=50000)
    segment_id: str
    company_id: str                       # required: a campaign only ever reaches one company's customers
    marketing_campaign_id: Optional[str] = None
    track_engagement: bool = False
    design_id: Optional[str] = None      # M44.S01.T001 published e-mail design
    ab_split_pct: int = Field(0, ge=0, le=50)            # M44.S01.T012: share of recipients getting variant B
    variant_b_subject: Optional[str] = Field(None, max_length=300, pattern=r"^[^\r\n]+$")
    variant_b_body: Optional[str] = Field(None, max_length=50000)
    variant_b_design_id: Optional[str] = None
    send_time_optimize: bool = False


async def _published_design(db, design_id):
    if not design_id:
        return None
    from app.models.crm import EmailDesign
    d = await db.get(EmailDesign, _uuid(design_id))
    if d is None or d.status != "PUBLISHED":
        raise HTTPException(422, "Choose a published e-mail design.")
    return d.id


async def _campaign_out(db, c) -> dict:
    from app.services import crm_campaign_service as campaigns

    return {"id": str(c.id), "name": c.name, "subject": c.subject, "body": c.body, "segment_id": str(c.segment_id),
            "company_id": str(c.company_id) if c.company_id else None, "status": c.status,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "queued_at": c.queued_at.isoformat() if c.queued_at else None, "audience_size": c.audience_size,
            "track_engagement": bool(c.track_engagement), "ab_split_pct": c.ab_split_pct,
            "send_time_optimize": bool(c.send_time_optimize), "approval_status": c.approval_status,
            "design_id": str(c.design_id) if c.design_id else None,
            "stats": await campaigns.stats(db, c)}


@router.get("/email-campaigns", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def list_email_campaigns(db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMEmailCampaign

    rows = (await db.execute(select(CRMEmailCampaign).order_by(CRMEmailCampaign.created_at.desc()))).scalars().all()
    return [await _campaign_out(db, c) for c in rows]


@router.post("/email-campaigns", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_email_campaign(body: EmailCampaignIn, db: AsyncSession = Depends(get_db),
                                current_user=Depends(get_current_user)):
    from app.models.company import Company
    from app.models.crm import CRMEmailCampaign
    from app.models.marketing import CustomerSegment
    from app.services import crm_campaign_service as campaigns

    seg = await db.get(CustomerSegment, _uuid(body.segment_id))
    if seg is None or not seg.is_active:
        raise HTTPException(422, "segment_id is not an active segment")
    if await db.get(Company, _uuid(body.company_id)) is None:
        raise HTTPException(422, "company_id does not exist")
    unknown = campaigns.unknown_placeholders(body.subject + body.body + (body.variant_b_subject or "") + (body.variant_b_body or ""))
    if unknown:
        raise HTTPException(422, "Unknown placeholder(s): " + ", ".join("{%s}" % u for u in sorted(unknown))
                            + "; use {contact_name} or {company_name}")
    c = CRMEmailCampaign(name=body.name, subject=body.subject, body=body.body, segment_id=_uuid(body.segment_id),
                         company_id=_uuid(body.company_id),
                         marketing_campaign_id=_uuid(body.marketing_campaign_id) if body.marketing_campaign_id else None,
                         status="DRAFT", created_by=current_user.username, track_engagement=body.track_engagement,
                         design_id=await _published_design(db, body.design_id), ab_split_pct=body.ab_split_pct,
                         variant_b_subject=body.variant_b_subject, variant_b_body=body.variant_b_body,
                         variant_b_design_id=await _published_design(db, body.variant_b_design_id),
                         send_time_optimize=body.send_time_optimize)
    db.add(c)
    await db.commit()
    return await _campaign_out(db, c)


@router.get("/email-campaigns/segments", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def campaign_segments(db: AsyncSession = Depends(get_db)):
    """Active customer segments with member counts (for choosing a campaign audience)."""
    from app.models.marketing import CRMProfile, CustomerSegment

    rows = (await db.execute(select(CustomerSegment, func.count(CRMProfile.id)).outerjoin(
        CRMProfile, CRMProfile.segment_id == CustomerSegment.id).where(CustomerSegment.is_active.is_(True))
        .group_by(CustomerSegment.id).order_by(CustomerSegment.segment_name))).all()
    return [{"id": str(sg.id), "name": sg.segment_name, "members": n} for sg, n in rows]


@router.get("/email-campaigns/companies", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def campaign_companies(db: AsyncSession = Depends(get_db)):
    """Active companies a campaign can be sent for: campaign authors need the names without the company-admin right."""
    from app.models.company import Company

    rows = (await db.execute(select(Company).where(Company.is_active.is_(True)).order_by(Company.name))).scalars().all()
    return [{"id": str(c.id), "name": c.name} for c in rows]


@router.get("/email-campaigns/{campaign_id}/preview", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def preview_email_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMEmailCampaign
    from app.services import crm_campaign_service as campaigns

    c = await db.get(CRMEmailCampaign, _uuid(campaign_id))
    if c is None:
        raise HTTPException(404, "Campaign not found")
    return await campaigns.audience_preview(db, c)


@router.post("/email-campaigns/{campaign_id}/schedule", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def schedule_email_campaign(campaign_id: str, at: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Schedule a DRAFT campaign (now when `at` is omitted). Recipients are resolved at send time."""
    from datetime import datetime as _dt, timezone as _tz

    from app.models.crm import CRMEmailCampaign
    from app.services import crm_campaign_service as campaigns

    try:
        when = _dt.fromisoformat(at.replace("Z", "+00:00")) if at else _dt.now(_tz.utc)
    except ValueError:
        raise HTTPException(422, "at must be an ISO date-time")
    if when.tzinfo is None:
        raise HTTPException(422, "at must include a time-zone offset (e.g. +03:00 or Z)")
    c = (await db.execute(select(CRMEmailCampaign).where(CRMEmailCampaign.id == _uuid(campaign_id))
                          .with_for_update())).scalar_one_or_none()  # serialises against a concurrent cancel
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.status not in ("DRAFT", "FAILED"):
        raise HTTPException(409, "Only draft or failed campaigns can be scheduled.")
    from app.core.config import settings as _settings
    if _settings.MARKETING_EMAIL_APPROVAL_REQUIRED and c.approval_status != "APPROVED":   # M44.S01.T012
        raise HTTPException(409, "This campaign needs approval by a second editor before it is scheduled.")
    if (await campaigns.audience_preview(db, c))["addresses"] == 0:
        raise HTTPException(422, "The segment has no customers with an e-mail address for this company.")
    c.status, c.scheduled_at = "SCHEDULED", when
    await db.commit()
    return await _campaign_out(db, c)


@router.post("/email-campaigns/{campaign_id}/cancel", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def cancel_email_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a draft/scheduled campaign, or withdraw the not-yet-sent mail of a queued one."""
    from sqlalchemy import update as _update

    from app.models.crm import CRMEmailCampaign, CRMOutboundMessage

    c = (await db.execute(select(CRMEmailCampaign).where(CRMEmailCampaign.id == _uuid(campaign_id))
                          .with_for_update())).scalar_one_or_none()
    if c is None:
        raise HTTPException(404, "Campaign not found")
    withdrawn = 0
    if c.status == "QUEUED":
        withdrawn = (await db.execute(_update(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like(f"camp:{c.id}:%"), CRMOutboundMessage.status == "QUEUED")
            .values(status="CANCELLED", status_reason="campaign cancelled"))).rowcount
    elif c.status == "CANCELLED":
        raise HTTPException(409, "Campaign is already cancelled.")
    c.status = "CANCELLED"
    await db.commit()
    return {**(await _campaign_out(db, c)), "withdrawn_messages": withdrawn}


# ── M36.S01.T003 unified conversations inbox ───────────────────────────────────

class InboxPatch(BaseModel):
    assignee_id: Optional[str] = Field(None, description="user id; empty string unassigns")
    status: Optional[Literal["OPEN", "PENDING", "CLOSED"]] = None


@router.get("/inbox")
async def inbox(view: Literal["all", "mine", "unassigned", "unread"] = "all",
                channel: Optional[Literal["EMAIL", "WHATSAPP", "TICKET", "CHAT", "MESSENGER", "INSTAGRAM", "CUSTOM"]] = None,
                status: Optional[Literal["OPEN", "PENDING", "CLOSED"]] = None,
                limit: int = Query(100, ge=1, le=300),
                db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """E-mail threads, WhatsApp numbers and helpdesk tickets as one list, newest first. Each channel is
    shown only to who may see it (personal mailboxes to their owner); closed ones only with status=CLOSED."""
    from app.services import crm_inbox_service as inbox_svc
    return await inbox_svc.list_conversations(db, current_user, view=view, channel=channel, status=status, limit=limit)


@router.post("/inbox/{conversation_id}/read")
async def inbox_mark_read(conversation_id: str, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    from app.services import crm_inbox_service as inbox_svc
    conv = await inbox_svc.get_visible(db, current_user, _uuid(conversation_id))
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    await inbox_svc.mark_read(db, current_user, conv)
    await db.commit()
    return {"id": str(conv.id), "unread": False}


@router.patch("/inbox/{conversation_id}")
async def inbox_update(conversation_id: str, data: InboxPatch, db: AsyncSession = Depends(get_db),
                       current_user=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    """Assign (or unassign with an empty string) and set OPEN / PENDING / CLOSED. Ticket status stays in the helpdesk."""
    from app.models.user import User
    from app.services import crm_inbox_service as inbox_svc
    conv = await inbox_svc.get_visible(db, current_user, _uuid(conversation_id))
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    if data.assignee_id is not None:
        if conv.channel == "TICKET" and not has_any_permission(current_user, ("quality.edit", "quality.edit_all")):
            raise HTTPException(403, "Reassigning a support ticket needs quality edit rights.")
        assignee = None
        if data.assignee_id:
            assignee = await db.get(User, _uuid(data.assignee_id))
            if assignee is None or not assignee.is_active:
                raise HTTPException(422, "Assignee must be an active user")
        await inbox_svc.assign(db, conv, assignee.id if assignee else None)
    if data.status is not None:
        try:
            inbox_svc.set_status(conv, data.status)
        except ValueError as e:
            raise HTTPException(409, str(e))
    await db.commit()
    return {"id": str(conv.id), "assignee_id": str(conv.assignee_id) if conv.assignee_id else None, "status": conv.status}


@router.get("/inbox-assignees")
async def inbox_assignees(db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_EDIT_PERMISSIONS))):
    """Active users (id + name only) for the inbox assignee picker."""
    from app.models.user import User
    rows = (await db.execute(select(User.id, User.full_name, User.username).where(User.is_active.is_(True))
                             .order_by(User.full_name).limit(500))).all()
    return [{"id": str(i), "name": n or u} for i, n, u in rows]


# ── M36.S04.T001 AI sales copilot ───────────────────────────────────────────────

class CopilotIn(BaseModel):
    note: Optional[str] = Field(None, max_length=500, description="what the representative wants help with (optional)")


@router.post("/customers/{customer_id}/copilot")
async def customer_copilot(customer_id: str, body: CopilotIn, db: AsyncSession = Depends(get_db),
                           current_user=Depends(get_current_user)):
    """Summary, follow-ups and a draft e-mail for one customer, built only from timeline evidence the caller
    may see, each claim citing evidence ids. Nothing is sent or saved on the customer: the draft is for the
    representative to edit and send. Without an AI provider the brief is rule-based (mode='rule_based')."""
    from app.core.ai_rate_limiter import check_rate_limit
    from app.core.config import settings
    from app.models.sales import Customer
    from app.services import crm_copilot_service as copilot

    await check_rate_limit(str(current_user.id), "crm_copilot", settings.AI_RATE_LIMIT_GENERATE)  # LLM spend per user/hour
    customer = await db.get(Customer, _uuid(customer_id))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    if not (can_view_record(current_user, "crm", customer) or can_view_record(current_user, "sales", customer)):
        raise HTTPException(403, "Customer is outside your commercial scope.")
    result = await copilot.brief(db, customer, current_user, body.note)
    await db.commit()  # the AI request log
    return {"customer": {"id": str(customer.id), "name": customer.name}, **result}


# ── M36.S05.T001 customer journey attribution ──────────────────────────────────

@router.get("/reports/attribution", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def attribution_report(date_from: date, date_to: date, model: Literal["first", "last", "linear"] = "first",
                             company_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Source -> lead -> opportunity -> order -> repeat purchase, by first / last / linear touch, per currency,
    with a reconciliation flag and the stated assumptions."""
    from app.services import crm_attribution_service as attribution

    if date_from > date_to:
        raise HTTPException(422, "date_from must not be after date_to")
    if (date_to - date_from).days > 731:
        raise HTTPException(422, "Choose a period of at most two years")
    return await attribution.report(db, date_from, date_to, model, str(_uuid(company_id)) if company_id else None)


# ── M36.S03.T003 mobile quick notes ─────────────────────────────────────────────

class QuickNoteIn(BaseModel):
    channel: Literal["call", "visit", "note", "message"] = "note"
    summary: str = Field(min_length=2, max_length=2000)
    outcome: Optional[str] = Field(None, max_length=500)
    follow_up_date: Optional[date] = None
    client_ref: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$",
                            description="random id made by the phone; resending the same note never duplicates it")


@router.post("/customers/{customer_id}/notes", status_code=201)
async def customer_quick_note(customer_id: str, body: QuickNoteIn, db: AsyncSession = Depends(get_db),
                              current_user=Depends(require_any_permission(CRM_CREATE_PERMISSIONS))):
    """Log a call, visit or note on a customer from a phone. Offline policy: the phone keeps the note and
    resends it with the same client_ref when back online; the server stores it once (first write wins)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.marketing import CRMProfile, CustomerInteraction
    from app.models.sales import Customer

    customer = await db.get(Customer, _uuid(customer_id))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    if not (can_view_record(current_user, "crm", customer) or can_view_record(current_user, "sales", customer)):
        raise HTTPException(403, "Customer is outside your commercial scope.")
    async def replay():
        """A retry is the same user on the same customer; any other reuse of the key is refused, not leaked."""
        row = (await db.execute(select(CustomerInteraction.id, CustomerInteraction.recorded_by_id, CRMProfile.customer_id)
                                .join(CRMProfile, CRMProfile.id == CustomerInteraction.crm_profile_id)
                                .where(CustomerInteraction.client_ref == body.client_ref))).first()
        if row is None:
            return None
        if row[1] != current_user.id or row[2] != customer.id:
            raise HTTPException(409, "This note id was already used; send the note again as a new note.")
        return {"id": str(row[0]), "duplicate": True}

    done = await replay()
    if done is not None:
        return done
    await db.execute(pg_insert(CRMProfile).values(id=_uuid_new(), customer_id=customer.id)
                     .on_conflict_do_nothing(index_elements=["customer_id"]))
    profile_id = (await db.execute(select(CRMProfile.id).where(CRMProfile.customer_id == customer.id))).scalar_one()
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    stmt = pg_insert(CustomerInteraction).values(
        id=_uuid_new(), crm_profile_id=profile_id, interaction_date=_dt.now(ZoneInfo("Africa/Nairobi")).date(),
        channel=body.channel, summary=body.summary.strip(), outcome=body.outcome, follow_up_date=body.follow_up_date,
        recorded_by_id=current_user.id, client_ref=body.client_ref,
    ).on_conflict_do_nothing(index_elements=["client_ref"]).returning(CustomerInteraction.id)
    new_id = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    if new_id is None:  # a concurrent retry won the race
        return await replay()
    return {"id": str(new_id), "duplicate": False}


def _uuid_new():
    import uuid as _u
    return _u.uuid4()


# ── M36.S03.T005 website chat (staff side) ─────────────────────────────────────

class ChatReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


async def _chat(db, chat_id: str):
    from app.models.crm import CRMChatSession
    sess = await db.get(CRMChatSession, _uuid(chat_id), with_for_update=True)
    if sess is None:
        raise HTTPException(404, "Chat not found")
    return sess


@router.get("/chats/{chat_id}", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def chat_transcript(chat_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMChatSession
    from app.services import crm_chat_service as chat

    sess = await db.get(CRMChatSession, _uuid(chat_id))
    if sess is None:
        raise HTTPException(404, "Chat not found")
    return {"id": str(sess.id), "status": sess.status, "visitor_name": sess.visitor_name, "visitor_email": sess.visitor_email,
            "consent_given": sess.consent_given, "crm_record_id": str(sess.crm_record_id) if sess.crm_record_id else None,
            "page_url": sess.page_url, "messages": await chat.messages(db, sess)}


@router.post("/chats/{chat_id}/messages", status_code=201)
async def chat_reply(chat_id: str, body: ChatReplyIn, db: AsyncSession = Depends(get_db),
                     current_user=Depends(require_any_permission(("crm.edit", "crm.edit_all")))):
    from app.services import crm_chat_service as chat

    sess = await _chat(db, chat_id)
    try:
        await chat.agent_says(db, sess, body.body.strip(), current_user.id)
    except chat.ChatRefused as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {"status": sess.status}


@router.post("/chats/{chat_id}/close")
async def chat_close(chat_id: str, db: AsyncSession = Depends(get_db),
                     current_user=Depends(require_any_permission(("crm.edit", "crm.edit_all")))):
    from datetime import datetime as _dt, timezone as _tz
    sess = await _chat(db, chat_id)
    if sess.status != "CLOSED":
        sess.status, sess.closed_at = "CLOSED", _dt.now(_tz.utc)
        from app.core.config import settings as _settings
        from app.models.crm import CRMChatMessage
        from app.services import service_desk_service as sd   # M45.S01.T019 post-chat survey, once per chat
        tok = await sd.create_survey(db, "POST_CHAT", sess.id, None, sess.assignee_id)
        if tok:
            db.add(CRMChatMessage(session_id=sess.id, sender="BOT", created_at=_dt.now(_tz.utc),
                                  body=f"Thanks for chatting with us. How did we do? {_settings.PUBLIC_APP_URL.rstrip('/')}/survey/{tok}"))
    await db.commit()
    return {"status": sess.status}



# ── M43.S01.T011 multiple pipelines ───────────────────────────────────────────

class PipelineIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    record_type: Optional[str] = Field(None, pattern="^(LEAD|OPPORTUNITY)$")
    company_id: Optional[str] = None
    is_default: bool = False
    active_flag: bool = True
    sequence_no: int = Field(0, ge=0, le=1000)


def _pipe_out(p) -> dict:
    return {"id": str(p.id), "name": p.name, "record_type": p.record_type,
            "company_id": str(p.company_id) if p.company_id else None, "is_default": p.is_default,
            "active_flag": p.active_flag, "sequence_no": p.sequence_no}


@router.get("/pipelines", dependencies=[Depends(require_any_permission(CRM_VIEW_PERMISSIONS))])
async def list_pipelines(db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMPipeline
    rows = (await db.execute(select(CRMPipeline).order_by(CRMPipeline.sequence_no, CRMPipeline.name))).scalars()
    return [_pipe_out(p) for p in rows]


@router.post("/pipelines", status_code=201, dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def create_pipeline(body: PipelineIn, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update as _update

    from app.models.crm import CRMPipeline
    if (await db.execute(select(CRMPipeline.id).where(CRMPipeline.name == body.name))).first():
        raise HTTPException(409, "A pipeline with this name exists.")
    if body.is_default:
        await db.execute(_update(CRMPipeline).values(is_default=False))
    p = CRMPipeline(name=body.name, record_type=body.record_type, company_id=_uuid(body.company_id) if body.company_id else None,
                    is_default=body.is_default, active_flag=body.active_flag, sequence_no=body.sequence_no)
    db.add(p)
    await db.commit()
    return _pipe_out(p)


@router.put("/pipelines/{pipeline_id}", dependencies=[Depends(require_any_permission(CRM_CONFIG))])
async def update_pipeline(pipeline_id: str, body: PipelineIn, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update as _update

    from app.models.crm import CRMPipeline
    p = await db.get(CRMPipeline, _uuid(pipeline_id))
    if p is None:
        raise HTTPException(404, "Pipeline not found")
    if p.is_default and not body.is_default:
        raise HTTPException(422, "Make another pipeline the default instead.")
    if body.is_default and not p.is_default:
        await db.execute(_update(CRMPipeline).values(is_default=False))
    p.name, p.record_type, p.is_default, p.active_flag, p.sequence_no = (
        body.name, body.record_type, body.is_default, body.active_flag, body.sequence_no)
    p.company_id = _uuid(body.company_id) if body.company_id else None
    await db.commit()
    return _pipe_out(p)



# ── M44.S01.T012 campaign approval and A/B result ─────────────────────────────

@router.post("/email-campaigns/{campaign_id}/approval/{action}")
async def campaign_approval(campaign_id: str, action: str, db: AsyncSession = Depends(get_db),
                            current_user=Depends(get_current_user)):
    from datetime import datetime as _dt, timezone as _tz
    from app.models.crm import CRMEmailCampaign
    if not (current_user.is_superuser or has_any_permission(current_user, ("marketing.edit", "crm.edit_all"))):
        raise HTTPException(403, "Marketing editors only.")
    c = await db.get(CRMEmailCampaign, _uuid(campaign_id))
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if action == "request":
        if c.status != "DRAFT":
            raise HTTPException(409, "Only a draft can be sent for approval.")
        c.approval_status, c.approval_requested_by = "PENDING", current_user.username
    elif action in ("approve", "reject"):
        if c.approval_status != "PENDING":
            raise HTTPException(409, "Nothing waiting for approval.")
        if c.approval_requested_by == current_user.username:
            raise HTTPException(403, "A second editor must approve.")
        c.approval_status = "APPROVED" if action == "approve" else "REJECTED"
        c.approved_by, c.approved_at = current_user.username, _dt.now(_tz.utc)
    else:
        raise HTTPException(404, "Unknown action")
    await db.commit()
    return await _campaign_out(db, c)


@router.get("/email-campaigns/{campaign_id}/ab-result", dependencies=[Depends(require_any_permission(CRM_BROAD_VIEW))])
async def campaign_ab_result(campaign_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.crm import CRMEmailCampaign
    from app.services import crm_campaign_service as campaigns
    c = await db.get(CRMEmailCampaign, _uuid(campaign_id))
    if c is None:
        raise HTTPException(404, "Campaign not found")
    return await campaigns.ab_result(db, c)
