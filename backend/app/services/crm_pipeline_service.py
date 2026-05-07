from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from collections import defaultdict

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm import (
    CRMTerritory, CRMPipelineStage, CRMRecord, CRMInterestLine, CRMActivity,
    CRMCompetitor, CRMWinLoss, CRMAIRecommendation,
    CRMRecordType, CRMStatus, CRMTemperature,
    CRMAIAgentType, CRMAIRecStatus,
    CRMActivityResult,
)
from app.schemas.crm import (
    CRMStageCreate, CRMStageUpdate,
    CRMRecordCreate, CRMRecordUpdate,
    CRMInterestLineCreate, CRMActivityCreate, CRMActivityComplete,
    CRMCompetitorCreate,
    CRMQualifyRequest, CRMConvertRequest,
    CRMCloseWonRequest, CRMCloseLostRequest,
    CRMAIRecAck,
    CRMTerritoryCreate, CRMTerritoryUpdate,
)


# ── Stages ────────────────────────────────────────────────────────────────────

async def get_stages(db: AsyncSession, active_only: bool = False):
    q = select(CRMPipelineStage).order_by(CRMPipelineStage.sequence_no)
    if active_only:
        q = q.where(CRMPipelineStage.active_flag.is_(True))
    result = await db.execute(q)
    return result.scalars().all()


async def create_stage(db: AsyncSession, data: CRMStageCreate) -> CRMPipelineStage:
    stage = CRMPipelineStage(**data.model_dump())
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage


async def update_stage(db: AsyncSession, stage_id: str, data: CRMStageUpdate) -> Optional[CRMPipelineStage]:
    result = await db.execute(select(CRMPipelineStage).where(CRMPipelineStage.id == stage_id))
    stage = result.scalar_one_or_none()
    if not stage:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(stage, k, v)
    await db.commit()
    await db.refresh(stage)
    return stage


async def seed_default_stages(db: AsyncSession):
    from app.models.crm import CRMStageType
    defaults = [
        ("NEW_LEAD",      "New Lead",          CRMStageType.LEAD,        10, 10,  "#6B7280"),
        ("CONTACTED",     "Contacted",         CRMStageType.LEAD,        20, 20,  "#3B82F6"),
        ("QUALIFIED",     "Qualified",         CRMStageType.OPPORTUNITY, 30, 40,  "#8B5CF6"),
        ("PROPOSAL",      "Proposal Sent",     CRMStageType.OPPORTUNITY, 40, 60,  "#F59E0B"),
        ("NEGOTIATION",   "Negotiation",       CRMStageType.OPPORTUNITY, 50, 75,  "#EF4444"),
        ("VERBAL_COMMIT", "Verbal Commitment", CRMStageType.OPPORTUNITY, 60, 90,  "#10B981"),
        ("WON",           "Won",               CRMStageType.TERMINAL,    70, 100, "#059669"),
        ("LOST",          "Lost",              CRMStageType.TERMINAL,    80, 0,   "#DC2626"),
        ("ON_HOLD",       "On Hold",           CRMStageType.NURTURING,   90, 20,  "#6B7280"),
        ("NURTURING",     "Nurturing",         CRMStageType.NURTURING,   100, 15, "#0EA5E9"),
    ]
    existing = {r[0] for r in (await db.execute(select(CRMPipelineStage.stage_code))).all()}
    for code, name, stype, seq, prob, color in defaults:
        if code not in existing:
            db.add(CRMPipelineStage(
                stage_code=code, stage_name=name, stage_type=stype,
                sequence_no=seq, default_probability=prob,
                color_code=color, active_flag=True,
            ))
    await db.commit()
    return await get_stages(db)


# ── Auto-code generation ──────────────────────────────────────────────────────

async def _next_lead_code(db: AsyncSession) -> str:
    n = (await db.execute(
        select(func.count(CRMRecord.id)).where(CRMRecord.record_type == CRMRecordType.LEAD)
    )).scalar() or 0
    return f"LD-{n + 1:05d}"


async def _next_opp_code(db: AsyncSession) -> str:
    n = (await db.execute(
        select(func.count(CRMRecord.id)).where(CRMRecord.record_type == CRMRecordType.OPPORTUNITY)
    )).scalar() or 0
    return f"OPP-{n + 1:05d}"


# ── Records ───────────────────────────────────────────────────────────────────

async def _load_record(db: AsyncSession, record_id: str) -> Optional[CRMRecord]:
    result = await db.execute(
        select(CRMRecord)
        .where(CRMRecord.id == record_id)
        .options(
            selectinload(CRMRecord.stage),
            selectinload(CRMRecord.interest_lines),
            selectinload(CRMRecord.activities),
            selectinload(CRMRecord.competitors),
            selectinload(CRMRecord.win_loss),
        )
    )
    return result.scalar_one_or_none()


async def get_records(
    db: AsyncSession,
    record_type: Optional[str] = None,
    status: Optional[str] = None,
    assigned_rep_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    temperature: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    q = select(CRMRecord).options(selectinload(CRMRecord.stage))
    if record_type:
        q = q.where(CRMRecord.record_type == record_type)
    if status:
        q = q.where(CRMRecord.status == status)
    if assigned_rep_id:
        q = q.where(CRMRecord.assigned_rep_id == assigned_rep_id)
    if stage_id:
        q = q.where(CRMRecord.stage_id == stage_id)
    if temperature:
        q = q.where(CRMRecord.temperature == temperature)
    q = q.order_by(CRMRecord.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_record(db: AsyncSession, record_id: str) -> Optional[CRMRecord]:
    return await _load_record(db, record_id)


async def create_record(db: AsyncSession, data: CRMRecordCreate) -> CRMRecord:
    payload = data.model_dump()
    if data.record_type == CRMRecordType.LEAD:
        payload["lead_code"] = await _next_lead_code(db)
    else:
        payload["opportunity_code"] = await _next_opp_code(db)
    if data.stage_id and not payload.get("probability_pct"):
        st = await db.get(CRMPipelineStage, data.stage_id)
        if st:
            payload["probability_pct"] = st.default_probability
    record = CRMRecord(**payload)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_record(db: AsyncSession, record_id: str, data: CRMRecordUpdate) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    updates = data.model_dump(exclude_none=True)
    if "stage_id" in updates and not updates.get("probability_override") and not record.probability_override:
        st = await db.get(CRMPipelineStage, updates["stage_id"])
        if st:
            updates["probability_pct"] = st.default_probability
    for k, v in updates.items():
        setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


async def qualify_record(db: AsyncSession, record_id: str, data: CRMQualifyRequest) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    fit_flags = [data.budget_fit, data.need_fit, data.timeline_fit, data.authority_fit, data.product_fit, data.geo_fit]
    bonus = sum(1 for f in fit_flags if f) * 15
    record.lead_score = min(100, (record.lead_score or 0) + bonus)
    record.qualified_flag = True
    record.qualified_date = date.today()
    if data.notes:
        record.notes = (record.notes or "") + f"\n[Qualification] {data.notes}"
    await db.commit()
    await db.refresh(record)
    return record


async def convert_to_opportunity(db: AsyncSession, record_id: str, data: CRMConvertRequest) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    record.record_type = CRMRecordType.OPPORTUNITY
    if not record.opportunity_code:
        record.opportunity_code = await _next_opp_code(db)
    record.converted_date = date.today()
    if data.expected_revenue is not None:
        record.expected_revenue = data.expected_revenue
    if data.expected_close_date:
        record.expected_close_date = data.expected_close_date
    if data.stage_id:
        record.stage_id = data.stage_id
    if data.notes:
        record.notes = (record.notes or "") + f"\n[Converted to Opportunity] {data.notes}"
    await db.commit()
    await db.refresh(record)
    return record


async def close_won(db: AsyncSession, record_id: str, data: CRMCloseWonRequest) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    record.status = CRMStatus.WON
    if data.linked_order_id:
        record.linked_order_id = data.linked_order_id
    wl = CRMWinLoss(
        crm_record_id=record.id,
        final_status="WON",
        close_date=date.today(),
        final_revenue=data.final_revenue or record.expected_revenue or Decimal("0"),
        final_margin=data.final_margin or record.expected_margin,
        win_reason_code=data.win_reason_code,
        competitor_name=data.competitor_name,
        narrative=data.narrative,
        recorded_by=data.recorded_by,
    )
    db.add(wl)
    await db.commit()
    await db.refresh(record)
    return record


async def close_lost(db: AsyncSession, record_id: str, data: CRMCloseLostRequest) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    record.status = CRMStatus.LOST
    wl = CRMWinLoss(
        crm_record_id=record.id,
        final_status="LOST",
        close_date=date.today(),
        final_revenue=Decimal("0"),
        loss_reason_code=data.loss_reason_code,
        competitor_name=data.competitor_name,
        narrative=data.narrative,
        recorded_by=data.recorded_by,
    )
    db.add(wl)
    await db.commit()
    await db.refresh(record)
    return record


async def put_on_hold(db: AsyncSession, record_id: str, notes: Optional[str] = None) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    record.status = CRMStatus.ON_HOLD
    if notes:
        record.notes = (record.notes or "") + f"\n[On Hold] {notes}"
    await db.commit()
    await db.refresh(record)
    return record


async def reopen_record(db: AsyncSession, record_id: str) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    record.status = CRMStatus.OPEN
    await db.commit()
    await db.refresh(record)
    return record


# ── Interest Lines ────────────────────────────────────────────────────────────

async def add_interest_line(db: AsyncSession, data: CRMInterestLineCreate) -> CRMInterestLine:
    line = CRMInterestLine(**data.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def delete_interest_line(db: AsyncSession, line_id: str) -> bool:
    result = await db.execute(select(CRMInterestLine).where(CRMInterestLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        return False
    await db.delete(line)
    await db.commit()
    return True


# ── Activities ────────────────────────────────────────────────────────────────

async def get_activities(
    db: AsyncSession,
    record_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    result_status: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 200,
):
    q = select(CRMActivity)
    if record_id:
        q = q.where(CRMActivity.crm_record_id == record_id)
    if assigned_to:
        q = q.where(CRMActivity.assigned_to == assigned_to)
    if result_status:
        q = q.where(CRMActivity.result_status == result_status)
    if overdue_only:
        now = datetime.utcnow()
        q = q.where(
            and_(CRMActivity.due_datetime < now, CRMActivity.result_status == CRMActivityResult.PLANNED)
        )
    q = q.order_by(CRMActivity.due_datetime.asc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def create_activity(db: AsyncSession, data: CRMActivityCreate) -> CRMActivity:
    activity = CRMActivity(**data.model_dump())
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


async def complete_activity(db: AsyncSession, activity_id: str, data: CRMActivityComplete) -> Optional[CRMActivity]:
    result = await db.execute(select(CRMActivity).where(CRMActivity.id == activity_id))
    act = result.scalar_one_or_none()
    if not act:
        return None
    act.result_status = data.result_status
    act.completed_datetime = datetime.utcnow()
    if data.outcome_code:
        act.outcome_code = data.outcome_code
    if data.next_step:
        act.next_step = data.next_step
    if data.notes:
        act.notes = data.notes
    await db.commit()
    await db.refresh(act)
    return act


# ── Competitors ───────────────────────────────────────────────────────────────

async def add_competitor(db: AsyncSession, data: CRMCompetitorCreate) -> CRMCompetitor:
    comp = CRMCompetitor(**data.model_dump())
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp


# ── Deduplication ─────────────────────────────────────────────────────────────

async def check_duplicates(db: AsyncSession, company_name: str, email: Optional[str] = None, phone: Optional[str] = None):
    conds = [func.lower(CRMRecord.company_name) == company_name.lower()]
    if email:
        conds.append(func.lower(CRMRecord.contact_email) == email.lower())
    if phone:
        conds.append(CRMRecord.contact_phone == phone)
    result = await db.execute(select(CRMRecord).where(or_(*conds)).limit(5))
    return result.scalars().all()


# ── Lead Scoring ──────────────────────────────────────────────────────────────

async def update_lead_score(db: AsyncSession, record_id: str) -> Optional[CRMRecord]:
    record = await _load_record(db, record_id)
    if not record:
        return None
    score = 0
    if str(record.source_type) in {"REFERRAL", "INBOUND", "FIELD_SALES"}:
        score += 20
    completed = [a for a in (record.activities or []) if a.result_status == CRMActivityResult.COMPLETED]
    score += min(30, len(completed) * 5)
    if record.qualified_flag:
        score += 20
    rev = record.expected_revenue or Decimal("0")
    if rev > 500000:
        score += 15
    elif rev > 100000:
        score += 10
    if record.next_action_date:
        score += 5
    score += min(10, len(record.interest_lines or []) * 3)
    record.lead_score = min(100, score)
    if score >= 70:
        record.temperature = CRMTemperature.HOT
    elif score >= 40:
        record.temperature = CRMTemperature.WARM
    else:
        record.temperature = CRMTemperature.COLD
    await db.commit()
    await db.refresh(record)
    return record


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    total_leads = (await db.execute(
        select(func.count(CRMRecord.id)).where(CRMRecord.record_type == CRMRecordType.LEAD)
    )).scalar() or 0

    total_opps = (await db.execute(
        select(func.count(CRMRecord.id)).where(CRMRecord.record_type == CRMRecordType.OPPORTUNITY)
    )).scalar() or 0

    open_count = (await db.execute(
        select(func.count(CRMRecord.id)).where(CRMRecord.status == CRMStatus.OPEN)
    )).scalar() or 0

    won_month = (await db.execute(
        select(func.count(CRMRecord.id)).where(
            and_(CRMRecord.status == CRMStatus.WON, CRMRecord.updated_at >= month_start)
        )
    )).scalar() or 0

    lost_month = (await db.execute(
        select(func.count(CRMRecord.id)).where(
            and_(CRMRecord.status == CRMStatus.LOST, CRMRecord.updated_at >= month_start)
        )
    )).scalar() or 0

    pipeline_val = (await db.execute(
        select(func.coalesce(func.sum(CRMRecord.expected_revenue), 0)).where(CRMRecord.status == CRMStatus.OPEN)
    )).scalar() or Decimal("0")

    weighted_rows = (await db.execute(
        select(CRMRecord.expected_revenue, CRMRecord.probability_pct).where(CRMRecord.status == CRMStatus.OPEN)
    )).all()
    weighted = sum(
        (Decimal(str(r[0] or 0))) * (Decimal(str(r[1] or 0))) / 100
        for r in weighted_rows
    )

    overdue_act = (await db.execute(
        select(func.count(CRMActivity.id)).where(
            and_(CRMActivity.due_datetime < datetime.utcnow(), CRMActivity.result_status == CRMActivityResult.PLANNED)
        )
    )).scalar() or 0

    hot_count = (await db.execute(
        select(func.count(CRMRecord.id)).where(
            and_(CRMRecord.temperature == CRMTemperature.HOT, CRMRecord.status == CRMStatus.OPEN)
        )
    )).scalar() or 0

    total_closed = won_month + lost_month
    conversion = round(won_month / total_closed * 100, 1) if total_closed > 0 else 0.0

    avg_deal = (await db.execute(
        select(func.coalesce(func.avg(CRMRecord.expected_revenue), 0)).where(CRMRecord.status == CRMStatus.OPEN)
    )).scalar() or Decimal("0")

    stage_rows = (await db.execute(
        select(
            CRMPipelineStage.stage_name, CRMPipelineStage.color_code,
            func.count(CRMRecord.id),
            func.coalesce(func.sum(CRMRecord.expected_revenue), 0),
        )
        .join(CRMRecord, CRMRecord.stage_id == CRMPipelineStage.id, isouter=True)
        .where(or_(CRMRecord.status == CRMStatus.OPEN, CRMRecord.id.is_(None)))
        .group_by(CRMPipelineStage.stage_name, CRMPipelineStage.color_code, CRMPipelineStage.sequence_no)
        .order_by(CRMPipelineStage.sequence_no)
    )).all()
    stage_dist = [{"stage": r[0], "color": r[1], "count": r[2], "value": float(r[3])} for r in stage_rows]

    rep_rows = (await db.execute(
        select(CRMRecord.assigned_rep_id, func.count(CRMRecord.id), func.coalesce(func.sum(CRMRecord.expected_revenue), 0))
        .where(and_(CRMRecord.status == CRMStatus.OPEN, CRMRecord.assigned_rep_id.isnot(None)))
        .group_by(CRMRecord.assigned_rep_id)
        .order_by(func.sum(CRMRecord.expected_revenue).desc())
        .limit(5)
    )).all()
    top_reps = [{"rep": r[0], "count": r[1], "value": float(r[2])} for r in rep_rows]

    return {
        "total_leads": total_leads,
        "total_opportunities": total_opps,
        "open_records": open_count,
        "won_this_month": won_month,
        "lost_this_month": lost_month,
        "total_pipeline_value": float(pipeline_val),
        "weighted_pipeline_value": float(weighted),
        "overdue_activities": overdue_act,
        "hot_records": hot_count,
        "conversion_rate_pct": conversion,
        "avg_deal_size": float(avg_deal),
        "stage_distribution": stage_dist,
        "top_reps": top_reps,
    }


# ── Forecast ──────────────────────────────────────────────────────────────────

async def get_forecast(db: AsyncSession, months_ahead: int = 6) -> List[dict]:
    rows = (await db.execute(
        select(CRMRecord.expected_close_date, CRMRecord.expected_revenue, CRMRecord.probability_pct)
        .where(and_(CRMRecord.status == CRMStatus.OPEN, CRMRecord.expected_close_date.isnot(None)))
    )).all()

    buckets: dict = defaultdict(lambda: {"expected": Decimal("0"), "weighted": Decimal("0"), "count": 0})
    for r in rows:
        if r[0]:
            key = r[0].strftime("%Y-%m")
            rev = Decimal(str(r[1] or 0))
            prob = Decimal(str(r[2] or 0))
            buckets[key]["expected"] += rev
            buckets[key]["weighted"] += rev * prob / 100
            buckets[key]["count"] += 1

    today = date.today()
    result = []
    for i in range(months_ahead):
        month_raw = today.month + i
        year_val = today.year + (month_raw - 1) // 12
        month_val = ((month_raw - 1) % 12) + 1
        key = f"{year_val}-{month_val:02d}"
        b = buckets.get(key, {"expected": Decimal("0"), "weighted": Decimal("0"), "count": 0})
        result.append({
            "month": key,
            "expected_revenue": float(b["expected"]),
            "weighted_revenue": float(b["weighted"]),
            "deal_count": b["count"],
        })
    return result


# ── Pipeline Report ───────────────────────────────────────────────────────────

async def pipeline_report(db: AsyncSession) -> List[dict]:
    rows = (await db.execute(
        select(
            CRMPipelineStage.stage_name, CRMPipelineStage.stage_code,
            func.count(CRMRecord.id),
            func.coalesce(func.sum(CRMRecord.expected_revenue), 0),
            func.coalesce(func.avg(CRMRecord.probability_pct), 0),
        )
        .join(CRMRecord, CRMRecord.stage_id == CRMPipelineStage.id, isouter=True)
        .where(or_(CRMRecord.status == CRMStatus.OPEN, CRMRecord.id.is_(None)))
        .group_by(CRMPipelineStage.stage_name, CRMPipelineStage.stage_code, CRMPipelineStage.sequence_no)
        .order_by(CRMPipelineStage.sequence_no)
    )).all()
    return [
        {
            "stage_name": r[0],
            "stage_code": r[1],
            "record_count": r[2],
            "total_value": float(r[3]),
            "weighted_value": float(r[3]) * float(r[4]) / 100,
            "avg_probability": float(r[4]),
        }
        for r in rows
    ]


# ── Win/Loss Analysis ─────────────────────────────────────────────────────────

async def win_loss_report(db: AsyncSession) -> dict:
    total_lost_n = (await db.execute(
        select(func.count(CRMWinLoss.id)).where(CRMWinLoss.final_status == "LOST")
    )).scalar() or 1

    loss_rows = (await db.execute(
        select(CRMWinLoss.loss_reason_code, func.count(CRMWinLoss.id), func.coalesce(func.sum(CRMRecord.expected_revenue), 0))
        .join(CRMRecord, CRMRecord.id == CRMWinLoss.crm_record_id)
        .where(CRMWinLoss.final_status == "LOST")
        .group_by(CRMWinLoss.loss_reason_code)
        .order_by(func.count(CRMWinLoss.id).desc())
    )).all()

    total_won_n = (await db.execute(
        select(func.count(CRMWinLoss.id)).where(CRMWinLoss.final_status == "WON")
    )).scalar() or 1

    win_rows = (await db.execute(
        select(CRMWinLoss.win_reason_code, func.count(CRMWinLoss.id), func.coalesce(func.sum(CRMWinLoss.final_revenue), 0))
        .where(CRMWinLoss.final_status == "WON")
        .group_by(CRMWinLoss.win_reason_code)
        .order_by(func.count(CRMWinLoss.id).desc())
    )).all()

    comp_rows = (await db.execute(
        select(CRMWinLoss.competitor_name, func.count(CRMWinLoss.id))
        .where(and_(CRMWinLoss.final_status == "LOST", CRMWinLoss.competitor_name.isnot(None)))
        .group_by(CRMWinLoss.competitor_name)
        .order_by(func.count(CRMWinLoss.id).desc())
        .limit(10)
    )).all()

    tw = int(total_won_n) - 1  # actual won (we added 1 to avoid zero division)
    tl = int(total_lost_n) - 1
    # Re-fetch actual counts
    actual_won = (await db.execute(select(func.count(CRMWinLoss.id)).where(CRMWinLoss.final_status == "WON"))).scalar() or 0
    actual_lost = (await db.execute(select(func.count(CRMWinLoss.id)).where(CRMWinLoss.final_status == "LOST"))).scalar() or 0
    win_rate = round(actual_won / (actual_won + actual_lost) * 100, 1) if (actual_won + actual_lost) > 0 else 0.0

    return {
        "total_won": actual_won,
        "total_lost": actual_lost,
        "win_rate_pct": win_rate,
        "loss_by_reason": [
            {"reason_code": str(r[0]) if r[0] else "OTHER", "count": r[1], "total_revenue": float(r[2]), "pct_of_total": round(r[1] / max(actual_lost, 1) * 100, 1)}
            for r in loss_rows
        ],
        "win_by_reason": [
            {"reason_code": str(r[0]) if r[0] else "OTHER", "count": r[1], "total_revenue": float(r[2]), "pct_of_total": round(r[1] / max(actual_won, 1) * 100, 1)}
            for r in win_rows
        ],
        "top_competitors_causing_loss": [{"competitor": r[0], "loss_count": r[1]} for r in comp_rows],
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_lead_prioritization(db: AsyncSession) -> List[CRMAIRecommendation]:
    recs = []
    today = date.today()
    cutoff = datetime.utcnow() - timedelta(days=7)

    open_leads = (await db.execute(
        select(CRMRecord)
        .options(selectinload(CRMRecord.activities))
        .where(and_(CRMRecord.record_type == CRMRecordType.LEAD, CRMRecord.status == CRMStatus.OPEN))
        .limit(50)
    )).scalars().all()

    for record in open_leads:
        activities = record.activities or []
        recent = [a for a in activities if a.activity_datetime and a.activity_datetime > cutoff]
        if not recent:
            rec = CRMAIRecommendation(
                agent_type=CRMAIAgentType.LEAD_PRIORITIZATION,
                crm_record_id=record.id,
                title=f"Stale Lead: {record.company_name}",
                body=f"Lead {record.lead_code} has no activity in 7+ days. Score: {record.lead_score}. Temperature: {record.temperature}. Action recommended.",
                priority="HIGH" if record.temperature == CRMTemperature.HOT else "MEDIUM",
                action_label="Schedule Follow-Up",
                status=CRMAIRecStatus.PENDING,
            )
            db.add(rec)
            recs.append(rec)

    upcoming_opps = (await db.execute(
        select(CRMRecord).where(
            and_(
                CRMRecord.record_type == CRMRecordType.OPPORTUNITY,
                CRMRecord.status == CRMStatus.OPEN,
                CRMRecord.expected_close_date <= today + timedelta(days=30),
                CRMRecord.expected_close_date >= today,
            )
        ).limit(20)
    )).scalars().all()

    for record in upcoming_opps:
        rec = CRMAIRecommendation(
            agent_type=CRMAIAgentType.LEAD_PRIORITIZATION,
            crm_record_id=record.id,
            title=f"Closing Soon: {record.company_name}",
            body=f"Opportunity {record.opportunity_code} closes within 30 days. Expected revenue: {record.currency} {record.expected_revenue:,}. Ensure proposal/negotiation is on track.",
            priority="HIGH",
            action_label="Review Opportunity",
            status=CRMAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)

    await db.commit()
    return recs


async def run_pipeline_risk(db: AsyncSession) -> List[CRMAIRecommendation]:
    recs = []
    today = date.today()

    overdue = (await db.execute(
        select(CRMRecord).where(
            and_(CRMRecord.status == CRMStatus.OPEN, CRMRecord.expected_close_date < today, CRMRecord.expected_close_date.isnot(None))
        ).limit(30)
    )).scalars().all()

    for record in overdue:
        rec = CRMAIRecommendation(
            agent_type=CRMAIAgentType.PIPELINE_RISK,
            crm_record_id=record.id,
            title=f"Overdue Close Date: {record.company_name}",
            body=f"Record {record.lead_code or record.opportunity_code} had expected close date {record.expected_close_date} which is now past. Update or close.",
            priority="HIGH",
            action_label="Update Close Date",
            status=CRMAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)

    bottleneck_rows = (await db.execute(
        select(CRMPipelineStage.stage_name, CRMPipelineStage.id, func.count(CRMRecord.id))
        .join(CRMRecord, CRMRecord.stage_id == CRMPipelineStage.id)
        .where(CRMRecord.status == CRMStatus.OPEN)
        .group_by(CRMPipelineStage.stage_name, CRMPipelineStage.id)
        .having(func.count(CRMRecord.id) > 5)
    )).all()

    for row in bottleneck_rows:
        rec = CRMAIRecommendation(
            agent_type=CRMAIAgentType.PIPELINE_RISK,
            title=f"Stage Bottleneck: {row[0]}",
            body=f"Stage '{row[0]}' has {row[2]} open records. This indicates a conversion bottleneck. Review and push records forward.",
            priority="MEDIUM",
            action_label="Review Stage",
            status=CRMAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)

    await db.commit()
    return recs


async def run_win_loss_insight(db: AsyncSession) -> List[CRMAIRecommendation]:
    recs = []

    loss_patterns = (await db.execute(
        select(CRMWinLoss.loss_reason_code, func.count(CRMWinLoss.id))
        .where(CRMWinLoss.final_status == "LOST")
        .group_by(CRMWinLoss.loss_reason_code)
        .having(func.count(CRMWinLoss.id) >= 3)
        .order_by(func.count(CRMWinLoss.id).desc())
        .limit(5)
    )).all()

    for row in loss_patterns:
        if row[0]:
            rec = CRMAIRecommendation(
                agent_type=CRMAIAgentType.WIN_LOSS_INSIGHT,
                title=f"Recurring Loss Pattern: {row[0]}",
                body=f"Loss reason '{row[0]}' has occurred {row[1]} times. This is a systematic issue. Investigate and address root cause.",
                priority="HIGH" if row[1] >= 5 else "MEDIUM",
                action_label="Investigate Pattern",
                status=CRMAIRecStatus.PENDING,
            )
            db.add(rec)
            recs.append(rec)

    comp_patterns = (await db.execute(
        select(CRMWinLoss.competitor_name, func.count(CRMWinLoss.id))
        .where(and_(CRMWinLoss.final_status == "LOST", CRMWinLoss.competitor_name.isnot(None)))
        .group_by(CRMWinLoss.competitor_name)
        .having(func.count(CRMWinLoss.id) >= 2)
        .order_by(func.count(CRMWinLoss.id).desc())
        .limit(3)
    )).all()

    for row in comp_patterns:
        rec = CRMAIRecommendation(
            agent_type=CRMAIAgentType.WIN_LOSS_INSIGHT,
            title=f"Competitor Threat: {row[0]}",
            body=f"You have lost {row[1]} deals to '{row[0]}'. Review competitive intelligence and improve positioning.",
            priority="HIGH",
            action_label="Competitor Analysis",
            status=CRMAIRecStatus.PENDING,
        )
        db.add(rec)
        recs.append(rec)

    await db.commit()
    return recs


async def get_ai_recommendations(db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None):
    q = select(CRMAIRecommendation).order_by(CRMAIRecommendation.created_at.desc())
    if agent_type:
        q = q.where(CRMAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(CRMAIRecommendation.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_recommendation(db: AsyncSession, rec_id: str, data: CRMAIRecAck) -> Optional[CRMAIRecommendation]:
    result = await db.execute(select(CRMAIRecommendation).where(CRMAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    if data.acknowledged_by:
        rec.acknowledged_by = data.acknowledged_by
    if data.notes:
        rec.notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Territory Management ──────────────────────────────────────────────────────

async def get_territories(db: AsyncSession, active_only: bool = False) -> List[CRMTerritory]:
    q = select(CRMTerritory).order_by(CRMTerritory.territory_name)
    if active_only:
        q = q.where(CRMTerritory.active_flag.is_(True))
    result = await db.execute(q)
    return result.scalars().all()


async def create_territory(db: AsyncSession, data: CRMTerritoryCreate) -> CRMTerritory:
    territory = CRMTerritory(**data.model_dump())
    db.add(territory)
    await db.commit()
    await db.refresh(territory)
    return territory


async def update_territory(db: AsyncSession, territory_id: str, data: CRMTerritoryUpdate) -> Optional[CRMTerritory]:
    result = await db.execute(select(CRMTerritory).where(CRMTerritory.id == territory_id))
    territory = result.scalar_one_or_none()
    if not territory:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(territory, k, v)
    await db.commit()
    await db.refresh(territory)
    return territory


async def get_territory_performance(db: AsyncSession) -> List[dict]:
    territories = (await db.execute(select(CRMTerritory).where(CRMTerritory.active_flag.is_(True)))).scalars().all()
    result = []
    for t in territories:
        rows = (await db.execute(
            select(CRMRecord.status, func.count(CRMRecord.id), func.coalesce(func.sum(CRMRecord.expected_revenue), 0), func.coalesce(func.sum(CRMRecord.probability_pct), 0))
            .where(CRMRecord.territory_id == t.id)
            .group_by(CRMRecord.status)
        )).all()
        counts = {str(r[0]): {"count": r[1], "revenue": Decimal(str(r[2])), "prob_sum": Decimal(str(r[3]))} for r in rows}
        total = sum(v["count"] for v in counts.values())
        open_c = counts.get("OPEN", {}).get("count", 0)
        won_c = counts.get("WON", {}).get("count", 0)
        lost_c = counts.get("LOST", {}).get("count", 0)
        pipeline = counts.get("OPEN", {}).get("revenue", Decimal("0"))
        closed = won_c + lost_c
        win_rate = round(won_c / closed * 100, 1) if closed > 0 else 0.0
        weighted = Decimal("0")
        if open_c > 0:
            open_rows = (await db.execute(
                select(CRMRecord.expected_revenue, CRMRecord.probability_pct)
                .where(and_(CRMRecord.territory_id == t.id, CRMRecord.status == CRMStatus.OPEN))
            )).all()
            weighted = sum((Decimal(str(r[0] or 0))) * (Decimal(str(r[1] or 0))) / 100 for r in open_rows)
        result.append({
            "territory_id": str(t.id),
            "territory_name": t.territory_name,
            "region": t.region,
            "assigned_rep_ids": t.assigned_rep_ids,
            "total_records": total,
            "open_records": open_c,
            "won_records": won_c,
            "lost_records": lost_c,
            "pipeline_value": float(pipeline),
            "weighted_value": float(weighted),
            "win_rate_pct": win_rate,
        })
    return result


# ── Customer 360 View ─────────────────────────────────────────────────────────

async def get_record_360(db: AsyncSession, record_id: str) -> Optional[dict]:
    record = await _load_record(db, record_id)
    if not record:
        return None

    today = date.today()
    now = datetime.utcnow()
    pipeline_age_days = (today - record.created_at.date()).days if record.created_at else 0

    activities = record.activities or []
    total_activities = len(activities)
    completed = [a for a in activities if a.result_status == CRMActivityResult.COMPLETED]
    completed_count = len(completed)
    overdue = [a for a in activities if a.result_status == CRMActivityResult.PLANNED and a.due_datetime and a.due_datetime < now]
    overdue_count = len(overdue)
    completion_rate = round(completed_count / total_activities * 100, 1) if total_activities > 0 else 0.0

    last_activity_days: Optional[int] = None
    last_activity_type: Optional[str] = None
    if completed:
        last_act = max(completed, key=lambda a: a.completed_datetime or a.activity_datetime or now)
        ref_dt = last_act.completed_datetime or last_act.activity_datetime
        if ref_dt:
            last_activity_days = (now - ref_dt).days
            last_activity_type = str(last_act.activity_type)

    if last_activity_days is None:
        communication_risk = "HIGH"
    elif last_activity_days <= 7:
        communication_risk = "LOW"
    elif last_activity_days <= 21:
        communication_risk = "MEDIUM"
    else:
        communication_risk = "HIGH"

    interest_count = len(record.interest_lines or [])
    expected_revenue = float(record.expected_revenue or 0)
    probability_pct = float(record.probability_pct or 0)
    weighted_value = expected_revenue * probability_pct / 100

    deal_risk_flag = bool(
        record.expected_close_date and record.expected_close_date < today and record.status == CRMStatus.OPEN
    )

    days_to_close: Optional[int] = None
    if record.expected_close_date and record.status == CRMStatus.OPEN:
        days_to_close = (record.expected_close_date - today).days

    activity_health_score = min(100, int(
        completion_rate * 0.4
        + (max(0, 30 - (last_activity_days or 30)) / 30 * 30)
        + (10 if not overdue_count else 0)
        + (20 if interest_count > 0 else 0)
    ))

    flags: List[str] = []
    if deal_risk_flag:
        flags.append("OVERDUE_CLOSE_DATE")
    if communication_risk == "HIGH":
        flags.append("NO_RECENT_CONTACT")
    if overdue_count > 0:
        flags.append(f"{overdue_count}_OVERDUE_ACTIVITIES")
    if not record.qualified_flag and record.record_type == CRMRecordType.LEAD:
        flags.append("NOT_YET_QUALIFIED")
    if interest_count == 0:
        flags.append("NO_PRODUCT_INTEREST_LOGGED")
    if record.lead_score < 30:
        flags.append("LOW_LEAD_SCORE")

    territory_name: Optional[str] = None
    if record.territory:
        territory_name = record.territory.territory_name

    return {
        "record_id": str(record.id),
        "company_name": record.company_name,
        "record_type": str(record.record_type),
        "status": str(record.status),
        "lead_score": record.lead_score,
        "temperature": str(record.temperature),
        "pipeline_age_days": pipeline_age_days,
        "days_since_last_activity": last_activity_days,
        "last_activity_type": last_activity_type,
        "total_activities": total_activities,
        "completed_activities": completed_count,
        "overdue_activities": overdue_count,
        "activity_completion_rate": completion_rate,
        "communication_risk": communication_risk,
        "interest_product_count": interest_count,
        "expected_revenue": expected_revenue,
        "probability_pct": probability_pct,
        "weighted_value": weighted_value,
        "deal_risk_flag": deal_risk_flag,
        "credit_signal": "UNKNOWN",
        "qualified_flag": record.qualified_flag,
        "territory_name": territory_name,
        "assigned_rep_id": record.assigned_rep_id,
        "next_action_date": record.next_action_date,
        "expected_close_date": record.expected_close_date,
        "days_to_close": days_to_close,
        "activity_health_score": activity_health_score,
        "summary_flags": flags,
    }
