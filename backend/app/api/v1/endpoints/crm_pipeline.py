from __future__ import annotations
from datetime import date
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
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
async def list_stages(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await svc.get_stages(db, active_only=active_only)


@router.post("/stages", response_model=CRMStageRead, status_code=201)
async def create_stage(data: CRMStageCreate, db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
    return await svc.create_stage(db, data)


@router.patch("/stages/{stage_id}", response_model=CRMStageRead)
async def update_stage(stage_id: str, data: CRMStageUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_any_permission(CRM_CONFIG))):
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
    rec = await svc.update_record(db, record_id, data)
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
async def get_forecast(months_ahead: int = 6, db: AsyncSession = Depends(get_db)):
    return await svc.get_forecast(db, months_ahead=months_ahead)


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
                        db: AsyncSession = Depends(get_db)):
    """Stage conversion, aging of open records, rep performance and loss reasons for records created in range."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must not be after date_to")
    try:
        return await intel.funnel(db, date_from, date_to, assigned_rep_id, territory_id)
    except ValueError:
        raise HTTPException(422, "territory_id must be a UUID")
