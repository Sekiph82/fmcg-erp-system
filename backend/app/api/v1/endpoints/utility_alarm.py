"""
Utility Alarm & Anomaly Detection — FastAPI router.

Prefixed at /alarms by the main router.

Routes:
  Rules
    GET  /rules                         list with filters
    GET  /rules/templates               predefined rule templates
    POST /rules                         create rule
    GET  /rules/{rule_id}               get rule
    PATCH /rules/{rule_id}              update rule
    DELETE /rules/{rule_id}             delete rule (no active events)
    POST /rules/{rule_id}/toggle        toggle is_active

  Events
    GET  /events/summary                AlarmSummary counts
    GET  /events                        list with filters
    GET  /events/{event_id}             get event detail
    POST /events/{event_id}/acknowledge acknowledge
    POST /events/{event_id}/assign      assign to user
    POST /events/{event_id}/resolve     resolve with RCA
    POST /events/{event_id}/suppress    suppress

  Engine
    POST /evaluate                      trigger evaluation of all active rules
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.crud.utility_alarm import (
    acknowledge_event,
    assign_event,
    create_rule,
    delete_rule,
    get_alarm_summary,
    get_event,
    get_rule,
    get_rule_by_code,
    list_events,
    list_rules,
    resolve_event,
    suppress_event,
    update_rule,
    _rule_to_read,
    _event_to_read,
)
from app.schemas.utility_alarm import (
    AlarmEventAcknowledge,
    AlarmEventAssign,
    AlarmEventRead,
    AlarmEventResolve,
    AlarmRuleCreate,
    AlarmRuleRead,
    AlarmRuleTemplate,
    AlarmRuleUpdate,
    AlarmSummary,
)
from app.services.utility_alarm_service import evaluate_all_active_rules

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Predefined templates ───────────────────────────────────────────────────────

_TEMPLATES: List[AlarmRuleTemplate] = [
    AlarmRuleTemplate(
        template_key="elec_threshold_high",
        name="Electricity Above Threshold",
        description="Fires when electricity consumption exceeds configured kWh threshold.",
        alarm_type="ELECTRICITY_HIGH",
        source_module="electricity",
        utility_type="ELECTRICITY",
        alarm_category="ENERGY",
        detection_type="THRESHOLD",
        parameter="consumption_kwh",
        operator="GT",
        threshold_value=500,
        threshold_unit="kWh",
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="water_sudden_spike",
        name="Abnormal Water Spike",
        description="Detects a sudden spike in water consumption exceeding delta threshold.",
        alarm_type="WATER_SPIKE",
        source_module="water",
        utility_type="WATER",
        alarm_category="WATER",
        detection_type="SUDDEN_JUMP",
        parameter="consumption_m3",
        operator="GT",
        threshold_value=50,
        threshold_unit="m³",
        delta_pct_threshold=30.0,
        severity="ALERT",
    ),
    AlarmRuleTemplate(
        template_key="gas_sudden_increase",
        name="Unusual Gas Increase",
        description="Detects abnormal step-increase in natural gas consumption.",
        alarm_type="GAS_SPIKE",
        source_module="gas",
        utility_type="NATURAL_GAS",
        alarm_category="ENERGY",
        detection_type="SUDDEN_JUMP",
        parameter="gas_nm3",
        operator="GT",
        threshold_value=100,
        threshold_unit="Nm³",
        delta_pct_threshold=25.0,
        severity="ALERT",
    ),
    AlarmRuleTemplate(
        template_key="boiler_efficiency_decline",
        name="Boiler Efficiency Decline",
        description="Rolling-average efficiency drop below acceptable range over 72-hour window.",
        alarm_type="BOILER_EFFICIENCY_DECLINE",
        source_module="steam",
        utility_type="STEAM",
        alarm_category="BOILER_STEAM",
        detection_type="ROLLING_DEVIATION",
        parameter="boiler_efficiency_pct",
        operator="LT",
        threshold_value=80,
        threshold_unit="%",
        rolling_window_hours=72,
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="excessive_blowdown",
        name="Excessive Blowdown Loss",
        description="Boiler blowdown loss exceeds the configured limit, indicating water chemistry issues.",
        alarm_type="EXCESSIVE_BLOWDOWN",
        source_module="steam",
        utility_type="STEAM",
        alarm_category="BOILER_STEAM",
        detection_type="THRESHOLD",
        parameter="blowdown_loss_pct",
        operator="GT",
        threshold_value=5,
        threshold_unit="%",
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="poor_condensate_return",
        name="Poor Condensate Return",
        description="Condensate recovery rate falls below acceptable minimum, increasing make-up water cost.",
        alarm_type="LOW_CONDENSATE_RECOVERY",
        source_module="steam",
        utility_type="STEAM",
        alarm_category="BOILER_STEAM",
        detection_type="THRESHOLD",
        parameter="condensate_recovery_pct",
        operator="LT",
        threshold_value=60,
        threshold_unit="%",
        severity="ALERT",
    ),
    AlarmRuleTemplate(
        template_key="high_compressor_idle",
        name="High Compressor Idle Time",
        description="Compressor average load percentage suggests excessive idle or unloaded running.",
        alarm_type="HIGH_COMPRESSOR_IDLE",
        source_module="compressor",
        utility_type="COMPRESSED_AIR",
        alarm_category="COMPRESSED_AIR",
        detection_type="THRESHOLD",
        parameter="avg_load_pct",
        operator="GT",
        threshold_value=20,
        threshold_unit="%",
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="air_leak_likely",
        name="Likely Compressed Air Leak",
        description="Rolling-average specific energy (kWh/Nm³) indicates probable system leak.",
        alarm_type="AIR_LEAK_SUSPECT",
        source_module="compressor",
        utility_type="COMPRESSED_AIR",
        alarm_category="COMPRESSED_AIR",
        detection_type="ROLLING_DEVIATION",
        parameter="air_kwh_per_nm3",
        operator="GT",
        threshold_value=0.12,
        threshold_unit="kWh/Nm³",
        rolling_window_hours=168,
        severity="ALERT",
    ),
    AlarmRuleTemplate(
        template_key="solar_underperformance",
        name="Solar Underperformance",
        description="Solar array performance ratio drops below standard, indicating soiling or faults.",
        alarm_type="SOLAR_UNDERPERFORMANCE",
        source_module="solar",
        utility_type="SOLAR",
        alarm_category="SOLAR",
        detection_type="VS_STANDARD",
        parameter="avg_pr_ratio",
        operator="LT",
        threshold_value=0.70,
        standard_value=0.80,
        threshold_unit="PR",
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="soft_water_hardness",
        name="Soft Water Hardness Out of Limit",
        description="Softener product hardness exceeds acceptable limit — resin exhaustion or fault.",
        alarm_type="HIGH_SOFTWATER_HARDNESS",
        source_module="soft_water",
        utility_type="SOFT_WATER",
        alarm_category="WATER",
        detection_type="THRESHOLD",
        parameter="avg_product_hardness",
        operator="GT",
        threshold_value=50,
        threshold_unit="mg/L CaCO₃",
        severity="ALERT",
    ),
    AlarmRuleTemplate(
        template_key="high_salt_use",
        name="High Softener Salt Consumption",
        description="Salt consumption per m³ is above rolling average, indicating inefficient regeneration.",
        alarm_type="HIGH_SALT_CONSUMPTION",
        source_module="soft_water",
        utility_type="SOFT_WATER",
        alarm_category="WATER",
        detection_type="ROLLING_DEVIATION",
        parameter="salt_per_m3",
        operator="GT",
        threshold_value=0.5,
        threshold_unit="kg/m³",
        rolling_window_hours=168,
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="ww_ph_out_of_range",
        name="Wastewater pH Out of Range",
        description="Effluent pH exceeds regulatory discharge limit — compliance risk.",
        alarm_type="WW_PH_VIOLATION",
        source_module="wastewater",
        utility_type="WASTEWATER",
        alarm_category="COMPLIANCE",
        detection_type="THRESHOLD",
        parameter="avg_effluent_ph",
        operator="GT",
        threshold_value=9.0,
        threshold_unit="pH",
        severity="CRITICAL",
    ),
    AlarmRuleTemplate(
        template_key="cod_compliance_risk",
        name="COD/BOD Compliance Risk",
        description="COD removal efficiency drops below minimum, risking effluent discharge non-compliance.",
        alarm_type="COD_COMPLIANCE_RISK",
        source_module="wastewater",
        utility_type="WASTEWATER",
        alarm_category="COMPLIANCE",
        detection_type="THRESHOLD",
        parameter="cod_removal_pct",
        operator="LT",
        threshold_value=75,
        threshold_unit="%",
        severity="CRITICAL",
    ),
    AlarmRuleTemplate(
        template_key="excess_chemical_dose",
        name="Excessive Utility Chemical Consumption",
        description="Chemical dose rate per m³ is running above rolling average, driving up treatment cost.",
        alarm_type="EXCESS_CHEMICAL_DOSE",
        source_module="chemical_treatment",
        utility_type="WATER",
        alarm_category="CHEMICAL",
        detection_type="ROLLING_DEVIATION",
        parameter="dose_rate_kg_m3",
        operator="GT",
        threshold_value=0.8,
        threshold_unit="kg/m³",
        rolling_window_hours=120,
        severity="WARNING",
    ),
    AlarmRuleTemplate(
        template_key="night_base_load",
        name="Abnormal Night Base Load",
        description="Night-shift electricity exceeds threshold compared to prior day, indicating standby waste.",
        alarm_type="HIGH_NIGHT_BASE_LOAD",
        source_module="electricity",
        utility_type="ELECTRICITY",
        alarm_category="ENERGY",
        detection_type="SHIFT_COMPARISON",
        parameter="kwh_night",
        operator="GT",
        threshold_value=300,
        threshold_unit="kWh",
        severity="WARNING",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Rules
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rules/templates", response_model=List[AlarmRuleTemplate])
async def get_rule_templates(
    _: dict = Depends(get_current_user),
):
    return _TEMPLATES


@router.get("/rules", response_model=List[AlarmRuleRead])
async def list_rules_route(
    utility_type:   Optional[str]  = Query(None),
    severity:       Optional[str]  = Query(None),
    is_active:      Optional[bool] = Query(None),
    detection_type: Optional[str]  = Query(None),
    skip:           int = Query(0, ge=0),
    limit:          int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await list_rules(
        db,
        utility_type=utility_type,
        severity=severity,
        is_active=is_active,
        detection_type=detection_type,
        skip=skip,
        limit=limit,
    )


@router.post("/rules", response_model=AlarmRuleRead, status_code=201)
async def create_rule_route(
    body: AlarmRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    existing = await get_rule_by_code(db, body.rule_code)
    if existing:
        raise HTTPException(400, f"Rule code '{body.rule_code}' already exists")
    async with db.begin():
        rule = await create_rule(db, body, created_by_id=user.get("id"))
    refreshed = await get_rule(db, rule.id)
    return _rule_to_read(refreshed, event_count=0)


@router.get("/rules/{rule_id}", response_model=AlarmRuleRead)
async def get_rule_route(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rule = await get_rule(db, rule_id)
    if not rule:
        raise HTTPException(404, "Alarm rule not found")
    return _rule_to_read(rule)


@router.patch("/rules/{rule_id}", response_model=AlarmRuleRead)
async def update_rule_route(
    rule_id: UUID,
    body: AlarmRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        rule = await get_rule(db, rule_id)
        if not rule:
            raise HTTPException(404, "Alarm rule not found")
        return await update_rule(db, rule, body)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule_route(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rule = await get_rule(db, rule_id)
    if not rule:
        raise HTTPException(404, "Alarm rule not found")
    from sqlalchemy import and_, func, select
    from app.models.utility_management import UtilityAlarmEvent, AlarmStatus
    stmt = select(func.count()).select_from(UtilityAlarmEvent).where(
        and_(
            UtilityAlarmEvent.rule_id == rule_id,
            UtilityAlarmEvent.status == AlarmStatus.ACTIVE,
        )
    )
    rule_active_count = (await db.execute(stmt)).scalar_one()
    if rule_active_count > 0:
        raise HTTPException(400, f"Cannot delete rule with {rule_active_count} active alarm event(s)")
    async with db.begin():
        rule = await get_rule(db, rule_id)
        await delete_rule(db, rule)


@router.post("/rules/{rule_id}/toggle", response_model=AlarmRuleRead)
async def toggle_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        rule = await get_rule(db, rule_id)
        if not rule:
            raise HTTPException(404, "Alarm rule not found")
        update_data = AlarmRuleUpdate(is_active=not rule.is_active)
        return await update_rule(db, rule, update_data)


# ═══════════════════════════════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/events/summary", response_model=AlarmSummary)
async def alarm_summary(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await get_alarm_summary(db)


@router.get("/events", response_model=List[AlarmEventRead])
async def list_events_route(
    status:         Optional[str]      = Query(None),
    severity:       Optional[str]      = Query(None),
    utility_type:   Optional[str]      = Query(None),
    date_from:      Optional[datetime] = Query(None),
    date_to:        Optional[datetime] = Query(None),
    assigned_to_id: Optional[UUID]     = Query(None),
    rule_id:        Optional[UUID]     = Query(None),
    skip:           int = Query(0, ge=0),
    limit:          int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await list_events(
        db,
        status=status,
        severity=severity,
        utility_type=utility_type,
        date_from=date_from,
        date_to=date_to,
        assigned_to_id=assigned_to_id,
        rule_id=rule_id,
        skip=skip,
        limit=limit,
    )


@router.get("/events/{event_id}", response_model=AlarmEventRead)
async def get_event_route(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    event = await get_event(db, event_id)
    if not event:
        raise HTTPException(404, "Alarm event not found")
    return _event_to_read(event)


@router.post("/events/{event_id}/acknowledge", response_model=AlarmEventRead)
async def acknowledge_event_route(
    event_id: UUID,
    body: AlarmEventAcknowledge,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        event = await get_event(db, event_id)
        if not event:
            raise HTTPException(404, "Alarm event not found")
        from app.models.utility_management import AlarmStatus
        if event.status not in (AlarmStatus.ACTIVE,):
            raise HTTPException(400, f"Cannot acknowledge event with status '{event.status.value}'")
        return await acknowledge_event(db, event, user_id=user.get("id"), notes=body.notes)


@router.post("/events/{event_id}/assign", response_model=AlarmEventRead)
async def assign_event_route(
    event_id: UUID,
    body: AlarmEventAssign,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        event = await get_event(db, event_id)
        if not event:
            raise HTTPException(404, "Alarm event not found")
        return await assign_event(db, event, assigned_to_id=body.assigned_to_id)


@router.post("/events/{event_id}/resolve", response_model=AlarmEventRead)
async def resolve_event_route(
    event_id: UUID,
    body: AlarmEventResolve,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        event = await get_event(db, event_id)
        if not event:
            raise HTTPException(404, "Alarm event not found")
        from app.models.utility_management import AlarmStatus
        if event.status == AlarmStatus.RESOLVED:
            raise HTTPException(400, "Event is already resolved")
        return await resolve_event(
            db,
            event,
            user_id=user.get("id"),
            root_cause=body.root_cause,
            corrective_action=body.corrective_action,
            notes=body.notes,
        )


@router.post("/events/{event_id}/suppress", response_model=AlarmEventRead)
async def suppress_event_route(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    async with db.begin():
        event = await get_event(db, event_id)
        if not event:
            raise HTTPException(404, "Alarm event not found")
        from app.models.utility_management import AlarmStatus
        if event.status in (AlarmStatus.RESOLVED, AlarmStatus.SUPPRESSED):
            raise HTTPException(400, f"Cannot suppress event with status '{event.status.value}'")
        return await suppress_event(db, event, user_id=user.get("id"))


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/evaluate")
async def trigger_evaluation(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    async with db.begin():
        events = await evaluate_all_active_rules(db)
    return {"new_events": len(events), "event_nos": [e.event_no for e in events]}
