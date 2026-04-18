"""
CRUD helpers for UtilityAlarmRule and UtilityAlarmEvent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import (
    AlarmCategory,
    AlarmDetectionType,
    AlarmOperator,
    AlarmSeverity,
    AlarmStatus,
    UtilityAlarmEvent,
    UtilityAlarmRule,
    UtilityType,
)
from app.schemas.utility_alarm import (
    AlarmEventRead,
    AlarmRuleCreate,
    AlarmRuleRead,
    AlarmRuleUpdate,
)

logger = logging.getLogger(__name__)


# ── Sequence generator ─────────────────────────────────────────────────────────

async def _next_event_no(db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    like_pattern = f"ALM-{today}-%"
    result = await db.execute(
        select(func.count()).select_from(UtilityAlarmEvent).where(
            UtilityAlarmEvent.event_no.like(like_pattern)
        )
    )
    n = result.scalar_one() + 1
    return f"ALM-{today}-{n:05d}"


# ── Read helpers ───────────────────────────────────────────────────────────────

def _enum_val(v) -> Optional[str]:
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _rule_to_read(rule: UtilityAlarmRule, event_count: int = 0) -> AlarmRuleRead:
    return AlarmRuleRead(
        id=rule.id,
        rule_code=rule.rule_code,
        name=rule.name,
        description=rule.description,
        utility_type=_enum_val(rule.utility_type),
        device_id=rule.device_id,
        asset_id=rule.asset_id,
        alarm_type=rule.alarm_type,
        source_module=rule.source_module,
        alarm_category=_enum_val(rule.alarm_category) or "GENERAL",
        detection_type=_enum_val(rule.detection_type) or "THRESHOLD",
        parameter=rule.parameter,
        operator=_enum_val(rule.operator),
        threshold_value=float(rule.threshold_value) if rule.threshold_value is not None else 0.0,
        threshold_unit=rule.threshold_unit,
        rolling_window_hours=rule.rolling_window_hours,
        delta_pct_threshold=float(rule.delta_pct_threshold) if rule.delta_pct_threshold is not None else None,
        standard_value=float(rule.standard_value) if rule.standard_value is not None else None,
        comparison_asset_id=rule.comparison_asset_id,
        severity=_enum_val(rule.severity) or "WARNING",
        cooldown_minutes=rule.cooldown_minutes,
        evaluation_frequency_min=rule.evaluation_frequency_min,
        is_active=rule.is_active,
        notification_emails=rule.notification_emails,
        notification_channel=rule.notification_channel,
        notes=rule.notes,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        created_by_name=(
            rule.created_by.full_name if rule.created_by else None
        ),
        device_name=rule.device.name if rule.device else None,
        asset_name=rule.asset.name if rule.asset else None,
        event_count=event_count,
    )


def _event_to_read(event: UtilityAlarmEvent) -> AlarmEventRead:
    return AlarmEventRead(
        id=event.id,
        event_no=event.event_no,
        rule_id=event.rule_id,
        device_id=event.device_id,
        asset_id=event.asset_id,
        triggered_at=event.triggered_at,
        acknowledged_at=event.acknowledged_at,
        resolved_at=event.resolved_at,
        status=_enum_val(event.status),
        severity=_enum_val(event.severity),
        alarm_type=event.alarm_type,
        source_module=event.source_module,
        detection_type=_enum_val(event.detection_type),
        parameter=event.parameter,
        triggered_value=float(event.triggered_value) if event.triggered_value is not None else None,
        expected_value=float(event.expected_value) if event.expected_value is not None else None,
        threshold_value=float(event.threshold_value) if event.threshold_value is not None else None,
        threshold_unit=event.threshold_unit,
        deviation_pct=float(event.deviation_pct) if event.deviation_pct is not None else None,
        root_cause=event.root_cause,
        corrective_action=event.corrective_action,
        notes=event.notes,
        created_at=event.created_at,
        rule_code=event.rule.rule_code if event.rule else None,
        rule_name=event.rule.name if event.rule else None,
        device_name=event.device.name if event.device else None,
        asset_name=event.asset.name if event.asset else None,
        assigned_to_name=(
            event.assigned_to.full_name if event.assigned_to else None
        ),
        acknowledged_by_name=(
            event.acknowledged_by.full_name if event.acknowledged_by else None
        ),
        resolved_by_name=(
            event.resolved_by.full_name if event.resolved_by else None
        ),
    )


# ── Rules CRUD ─────────────────────────────────────────────────────────────────

_RULE_OPTIONS = [
    selectinload(UtilityAlarmRule.device),
    selectinload(UtilityAlarmRule.asset),
    selectinload(UtilityAlarmRule.created_by),
]


async def list_rules(
    db: AsyncSession,
    *,
    utility_type: Optional[str] = None,
    severity: Optional[str] = None,
    is_active: Optional[bool] = None,
    detection_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[AlarmRuleRead]:
    clauses = []
    if utility_type:
        try:
            clauses.append(UtilityAlarmRule.utility_type == UtilityType(utility_type))
        except ValueError:
            pass
    if severity:
        try:
            clauses.append(UtilityAlarmRule.severity == AlarmSeverity(severity))
        except ValueError:
            pass
    if is_active is not None:
        clauses.append(UtilityAlarmRule.is_active == is_active)
    if detection_type:
        try:
            clauses.append(UtilityAlarmRule.detection_type == AlarmDetectionType(detection_type))
        except ValueError:
            pass

    stmt = (
        select(UtilityAlarmRule)
        .options(*_RULE_OPTIONS)
        .where(and_(*clauses))
        .order_by(UtilityAlarmRule.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    results = []
    for rule in rows:
        cnt_result = await db.execute(
            select(func.count()).select_from(UtilityAlarmEvent).where(
                and_(
                    UtilityAlarmEvent.rule_id == rule.id,
                    UtilityAlarmEvent.status == AlarmStatus.ACTIVE,
                )
            )
        )
        results.append(_rule_to_read(rule, event_count=cnt_result.scalar_one()))
    return results


async def get_rule(db: AsyncSession, rule_id: UUID) -> Optional[UtilityAlarmRule]:
    stmt = (
        select(UtilityAlarmRule)
        .options(*_RULE_OPTIONS)
        .where(UtilityAlarmRule.id == rule_id)
    )
    return (await db.execute(stmt)).scalars().first()


async def get_rule_by_code(db: AsyncSession, code: str) -> Optional[UtilityAlarmRule]:
    stmt = (
        select(UtilityAlarmRule)
        .options(*_RULE_OPTIONS)
        .where(UtilityAlarmRule.rule_code == code)
    )
    return (await db.execute(stmt)).scalars().first()


async def create_rule(
    db: AsyncSession,
    data: AlarmRuleCreate,
    created_by_id=None,
) -> UtilityAlarmRule:
    obj = UtilityAlarmRule(
        rule_code=data.rule_code,
        name=data.name,
        description=data.description,
        utility_type=UtilityType(data.utility_type),
        device_id=data.device_id,
        asset_id=data.asset_id,
        alarm_type=data.alarm_type,
        source_module=data.source_module,
        alarm_category=AlarmCategory(data.alarm_category),
        detection_type=AlarmDetectionType(data.detection_type),
        parameter=data.parameter,
        operator=AlarmOperator(data.operator),
        threshold_value=data.threshold_value,
        threshold_unit=data.threshold_unit,
        rolling_window_hours=data.rolling_window_hours,
        delta_pct_threshold=data.delta_pct_threshold,
        standard_value=data.standard_value,
        comparison_asset_id=data.comparison_asset_id,
        severity=AlarmSeverity(data.severity),
        cooldown_minutes=data.cooldown_minutes,
        evaluation_frequency_min=data.evaluation_frequency_min,
        is_active=data.is_active,
        notification_emails=data.notification_emails,
        notification_channel=data.notification_channel,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_rule(
    db: AsyncSession,
    rule: UtilityAlarmRule,
    data: AlarmRuleUpdate,
) -> AlarmRuleRead:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "utility_type" and value is not None:
            setattr(rule, field, UtilityType(value))
        elif field == "alarm_category" and value is not None:
            setattr(rule, field, AlarmCategory(value))
        elif field == "detection_type" and value is not None:
            setattr(rule, field, AlarmDetectionType(value))
        elif field == "operator" and value is not None:
            setattr(rule, field, AlarmOperator(value))
        elif field == "severity" and value is not None:
            setattr(rule, field, AlarmSeverity(value))
        else:
            setattr(rule, field, value)
    await db.flush()
    await db.refresh(rule)
    cnt_result = await db.execute(
        select(func.count()).select_from(UtilityAlarmEvent).where(
            and_(
                UtilityAlarmEvent.rule_id == rule.id,
                UtilityAlarmEvent.status == AlarmStatus.ACTIVE,
            )
        )
    )
    return _rule_to_read(rule, event_count=cnt_result.scalar_one())


async def delete_rule(db: AsyncSession, rule: UtilityAlarmRule) -> None:
    await db.delete(rule)
    await db.flush()


# ── Events CRUD ────────────────────────────────────────────────────────────────

_EVENT_OPTIONS = [
    selectinload(UtilityAlarmEvent.rule),
    selectinload(UtilityAlarmEvent.device),
    selectinload(UtilityAlarmEvent.asset),
    selectinload(UtilityAlarmEvent.assigned_to),
    selectinload(UtilityAlarmEvent.acknowledged_by),
    selectinload(UtilityAlarmEvent.resolved_by),
]


async def list_events(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    utility_type: Optional[str] = None,
    date_from=None,
    date_to=None,
    assigned_to_id: Optional[UUID] = None,
    rule_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[AlarmEventRead]:
    clauses = []
    if status:
        try:
            clauses.append(UtilityAlarmEvent.status == AlarmStatus(status))
        except ValueError:
            pass
    if severity:
        try:
            clauses.append(UtilityAlarmEvent.severity == AlarmSeverity(severity))
        except ValueError:
            pass
    if utility_type:
        # Filter via join to rule
        try:
            ut = UtilityType(utility_type)
            clauses.append(
                UtilityAlarmEvent.rule_id.in_(
                    select(UtilityAlarmRule.id).where(UtilityAlarmRule.utility_type == ut)
                )
            )
        except ValueError:
            pass
    if date_from:
        clauses.append(UtilityAlarmEvent.triggered_at >= date_from)
    if date_to:
        clauses.append(UtilityAlarmEvent.triggered_at <= date_to)
    if assigned_to_id:
        clauses.append(UtilityAlarmEvent.assigned_to_id == assigned_to_id)
    if rule_id:
        clauses.append(UtilityAlarmEvent.rule_id == rule_id)

    stmt = (
        select(UtilityAlarmEvent)
        .options(*_EVENT_OPTIONS)
        .where(and_(*clauses))
        .order_by(UtilityAlarmEvent.triggered_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_event_to_read(e) for e in rows]


async def count_events(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    utility_type: Optional[str] = None,
) -> int:
    clauses = []
    if status:
        try:
            clauses.append(UtilityAlarmEvent.status == AlarmStatus(status))
        except ValueError:
            pass
    if severity:
        try:
            clauses.append(UtilityAlarmEvent.severity == AlarmSeverity(severity))
        except ValueError:
            pass
    if utility_type:
        try:
            ut = UtilityType(utility_type)
            clauses.append(
                UtilityAlarmEvent.rule_id.in_(
                    select(UtilityAlarmRule.id).where(UtilityAlarmRule.utility_type == ut)
                )
            )
        except ValueError:
            pass
    stmt = select(func.count()).select_from(UtilityAlarmEvent).where(and_(*clauses))
    return (await db.execute(stmt)).scalar_one()


async def get_event(db: AsyncSession, event_id: UUID) -> Optional[UtilityAlarmEvent]:
    stmt = (
        select(UtilityAlarmEvent)
        .options(*_EVENT_OPTIONS)
        .where(UtilityAlarmEvent.id == event_id)
    )
    return (await db.execute(stmt)).scalars().first()


async def create_event(
    db: AsyncSession,
    rule: UtilityAlarmRule,
    triggered_value: float,
    expected_value: Optional[float] = None,
    deviation_pct: Optional[float] = None,
) -> UtilityAlarmEvent:
    event_no = await _next_event_no(db)
    obj = UtilityAlarmEvent(
        event_no=event_no,
        rule_id=rule.id,
        device_id=rule.device_id,
        asset_id=rule.asset_id,
        triggered_at=datetime.now(timezone.utc),
        status=AlarmStatus.ACTIVE,
        severity=rule.severity,
        alarm_type=rule.alarm_type,
        source_module=rule.source_module,
        detection_type=rule.detection_type,
        parameter=rule.parameter,
        triggered_value=triggered_value,
        expected_value=expected_value,
        threshold_value=rule.threshold_value,
        threshold_unit=rule.threshold_unit,
        deviation_pct=deviation_pct,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def acknowledge_event(
    db: AsyncSession,
    event: UtilityAlarmEvent,
    user_id,
    notes: Optional[str] = None,
) -> AlarmEventRead:
    event.status = AlarmStatus.ACKNOWLEDGED
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by_id = user_id
    if notes:
        event.notes = notes
    await db.flush()
    await db.refresh(event)
    # reload relationships
    stmt = select(UtilityAlarmEvent).options(*_EVENT_OPTIONS).where(UtilityAlarmEvent.id == event.id)
    refreshed = (await db.execute(stmt)).scalars().first()
    return _event_to_read(refreshed)


async def assign_event(
    db: AsyncSession,
    event: UtilityAlarmEvent,
    assigned_to_id: UUID,
) -> AlarmEventRead:
    event.assigned_to_id = assigned_to_id
    await db.flush()
    await db.refresh(event)
    stmt = select(UtilityAlarmEvent).options(*_EVENT_OPTIONS).where(UtilityAlarmEvent.id == event.id)
    refreshed = (await db.execute(stmt)).scalars().first()
    return _event_to_read(refreshed)


async def resolve_event(
    db: AsyncSession,
    event: UtilityAlarmEvent,
    user_id,
    root_cause: str,
    corrective_action: str,
    notes: Optional[str] = None,
) -> AlarmEventRead:
    event.status = AlarmStatus.RESOLVED
    event.resolved_at = datetime.now(timezone.utc)
    event.resolved_by_id = user_id
    event.root_cause = root_cause
    event.corrective_action = corrective_action
    if notes:
        event.notes = notes
    await db.flush()
    await db.refresh(event)
    stmt = select(UtilityAlarmEvent).options(*_EVENT_OPTIONS).where(UtilityAlarmEvent.id == event.id)
    refreshed = (await db.execute(stmt)).scalars().first()
    return _event_to_read(refreshed)


async def suppress_event(
    db: AsyncSession,
    event: UtilityAlarmEvent,
    user_id,
) -> AlarmEventRead:
    event.status = AlarmStatus.SUPPRESSED
    await db.flush()
    await db.refresh(event)
    stmt = select(UtilityAlarmEvent).options(*_EVENT_OPTIONS).where(UtilityAlarmEvent.id == event.id)
    refreshed = (await db.execute(stmt)).scalars().first()
    return _event_to_read(refreshed)


# ── Summary ────────────────────────────────────────────────────────────────────

async def get_alarm_summary(db: AsyncSession) -> dict:
    active_statuses = [AlarmStatus.ACTIVE, AlarmStatus.ACKNOWLEDGED]

    # Counts by status
    total_active = (await db.execute(
        select(func.count()).select_from(UtilityAlarmEvent).where(
            UtilityAlarmEvent.status == AlarmStatus.ACTIVE
        )
    )).scalar_one()

    total_acknowledged = (await db.execute(
        select(func.count()).select_from(UtilityAlarmEvent).where(
            UtilityAlarmEvent.status == AlarmStatus.ACKNOWLEDGED
        )
    )).scalar_one()

    # Severity counts across active + acknowledged
    severity_rows = (await db.execute(
        select(UtilityAlarmEvent.severity, func.count().label("cnt"))
        .where(UtilityAlarmEvent.status.in_(active_statuses))
        .group_by(UtilityAlarmEvent.severity)
    )).all()

    severity_map: dict[str, int] = {}
    for row in severity_rows:
        key = row.severity.value if hasattr(row.severity, "value") else str(row.severity)
        severity_map[key] = row.cnt

    # By utility type — join to rules
    ut_rows = (await db.execute(
        select(UtilityAlarmRule.utility_type, func.count(UtilityAlarmEvent.id).label("cnt"))
        .join(UtilityAlarmEvent, UtilityAlarmEvent.rule_id == UtilityAlarmRule.id)
        .where(UtilityAlarmEvent.status.in_(active_statuses))
        .group_by(UtilityAlarmRule.utility_type)
    )).all()

    by_utility_type = {}
    for row in ut_rows:
        key = row.utility_type.value if hasattr(row.utility_type, "value") else str(row.utility_type)
        by_utility_type[key] = row.cnt

    # By alarm category — join to rules
    cat_rows = (await db.execute(
        select(UtilityAlarmRule.alarm_category, func.count(UtilityAlarmEvent.id).label("cnt"))
        .join(UtilityAlarmEvent, UtilityAlarmEvent.rule_id == UtilityAlarmRule.id)
        .where(UtilityAlarmEvent.status.in_(active_statuses))
        .group_by(UtilityAlarmRule.alarm_category)
    )).all()

    by_category = {}
    for row in cat_rows:
        key = row.alarm_category.value if hasattr(row.alarm_category, "value") else str(row.alarm_category)
        by_category[key] = row.cnt

    return {
        "total_active": total_active,
        "total_acknowledged": total_acknowledged,
        "critical_count": severity_map.get("CRITICAL", 0),
        "alert_count": severity_map.get("ALERT", 0),
        "warning_count": severity_map.get("WARNING", 0),
        "info_count": severity_map.get("INFO", 0),
        "by_utility_type": by_utility_type,
        "by_category": by_category,
    }
