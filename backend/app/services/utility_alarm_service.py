"""
Utility Alarm & Anomaly Detection Service

Evaluators are pluggable — each implements evaluate(db, rule) -> Optional[EvaluationResult].
Register new evaluators by adding to EVALUATOR_REGISTRY.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    AlarmDetectionType,
    AlarmOperator,
    AlarmStatus,
    BoilerSteamRecord,
    CompressorRecord,
    SoftWaterRecord,
    SolarRecord,
    TreatmentChemicalRecord,
    UtilityAlarmEvent,
    UtilityAlarmRule,
    UtilityReading,
    UtilityTransaction,
    UtilityType,
    WastewaterRecord,
)
from app.crud.utility_alarm import create_event, get_alarm_summary

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    fired: bool
    actual_value: Optional[float] = None
    expected_value: Optional[float] = None
    deviation_pct: Optional[float] = None
    detail: str = ""


class BaseEvaluator(ABC):
    @abstractmethod
    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        ...


def _apply_operator(actual: float, threshold: float, operator: AlarmOperator) -> bool:
    if operator == AlarmOperator.GT:
        return actual > threshold
    if operator == AlarmOperator.LT:
        return actual < threshold
    if operator == AlarmOperator.GTE:
        return actual >= threshold
    if operator == AlarmOperator.LTE:
        return actual <= threshold
    if operator == AlarmOperator.EQ:
        return actual == threshold
    if operator == AlarmOperator.NEQ:
        return actual != threshold
    if operator == AlarmOperator.DELTA_PCT:
        return abs(actual) > threshold
    return False


async def _latest_transaction(
    db: AsyncSession,
    rule: UtilityAlarmRule,
    hours_back: int = 24,
) -> Optional[UtilityTransaction]:
    """Return the most recent UtilityTransaction for the rule's utility_type within hours_back."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    clauses = [
        UtilityTransaction.utility_type == rule.utility_type,
        UtilityTransaction.created_at >= cutoff,
    ]
    if rule.device_id:
        clauses.append(UtilityTransaction.device_id == rule.device_id)
    if rule.asset_id:
        clauses.append(UtilityTransaction.asset_id == rule.asset_id)

    stmt = (
        select(UtilityTransaction)
        .where(and_(*clauses))
        .order_by(UtilityTransaction.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


def _get_tx_param_value(tx: UtilityTransaction, parameter: str) -> Optional[float]:
    """Extract the relevant numeric value from a UtilityTransaction by parameter name."""
    if parameter in ("consumption_kwh", "kwh_night", "quantity"):
        v = tx.quantity
    elif hasattr(tx, parameter):
        v = getattr(tx, parameter)
    else:
        # Default to quantity column
        v = tx.quantity

    if v is None:
        return None
    return float(v)


class ThresholdEvaluator(BaseEvaluator):
    """Simple value vs threshold comparison (GT/LT/GTE/LTE/EQ/NEQ)."""

    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        tx = await _latest_transaction(db, rule, hours_back=24)
        if tx is None:
            return EvaluationResult(fired=False, detail="No recent transaction found")

        actual = _get_tx_param_value(tx, rule.parameter)
        if actual is None:
            return EvaluationResult(fired=False, detail="Parameter value is null")

        threshold = float(rule.threshold_value)
        fired = _apply_operator(actual, threshold, rule.operator)

        deviation = None
        if threshold != 0:
            deviation = round(((actual - threshold) / abs(threshold)) * 100, 2)

        return EvaluationResult(
            fired=fired,
            actual_value=actual,
            expected_value=threshold,
            deviation_pct=deviation,
            detail=f"{rule.parameter}={actual} {rule.operator.value} {threshold}",
        )


class SuddenJumpEvaluator(BaseEvaluator):
    """Detect sudden % change between the last two readings."""

    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        clauses = [
            UtilityTransaction.utility_type == rule.utility_type,
            UtilityTransaction.created_at >= cutoff,
        ]
        if rule.device_id:
            clauses.append(UtilityTransaction.device_id == rule.device_id)
        if rule.asset_id:
            clauses.append(UtilityTransaction.asset_id == rule.asset_id)

        stmt = (
            select(UtilityTransaction)
            .where(and_(*clauses))
            .order_by(UtilityTransaction.created_at.desc())
            .limit(2)
        )
        rows = (await db.execute(stmt)).scalars().all()

        if len(rows) < 2:
            return EvaluationResult(fired=False, detail="Not enough readings for jump detection")

        current = _get_tx_param_value(rows[0], rule.parameter)
        previous = _get_tx_param_value(rows[1], rule.parameter)

        if current is None or previous is None:
            return EvaluationResult(fired=False, detail="Parameter value is null in one of the records")

        if previous == 0:
            return EvaluationResult(fired=False, detail="Previous value is zero, cannot compute pct change")

        pct_change = ((current - previous) / abs(previous)) * 100
        delta_limit = float(rule.delta_pct_threshold) if rule.delta_pct_threshold else float(rule.threshold_value)
        fired = abs(pct_change) > delta_limit

        return EvaluationResult(
            fired=fired,
            actual_value=current,
            expected_value=previous,
            deviation_pct=round(pct_change, 2),
            detail=f"Jump {pct_change:.1f}% (limit {delta_limit}%)",
        )


class RollingDeviationEvaluator(BaseEvaluator):
    """Detect deviation from rolling average over a configured window."""

    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        window_hours = rule.rolling_window_hours or 72
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        clauses = [
            UtilityTransaction.utility_type == rule.utility_type,
            UtilityTransaction.created_at >= cutoff,
        ]
        if rule.device_id:
            clauses.append(UtilityTransaction.device_id == rule.device_id)
        if rule.asset_id:
            clauses.append(UtilityTransaction.asset_id == rule.asset_id)

        avg_stmt = (
            select(func.avg(UtilityTransaction.quantity).label("avg_val"))
            .where(and_(*clauses))
        )
        avg_val = (await db.execute(avg_stmt)).scalar()

        if avg_val is None:
            return EvaluationResult(fired=False, detail="No data in rolling window")

        avg_val = float(avg_val)

        # Get current (latest) value
        tx = await _latest_transaction(db, rule, hours_back=24)
        if tx is None:
            return EvaluationResult(fired=False, detail="No recent transaction")

        current = _get_tx_param_value(tx, rule.parameter)
        if current is None:
            return EvaluationResult(fired=False, detail="Current parameter value is null")

        if avg_val == 0:
            return EvaluationResult(fired=False, detail="Rolling average is zero")

        deviation_pct = ((current - avg_val) / abs(avg_val)) * 100
        threshold_pct = float(rule.threshold_value)
        fired = abs(deviation_pct) > threshold_pct

        return EvaluationResult(
            fired=fired,
            actual_value=current,
            expected_value=round(avg_val, 4),
            deviation_pct=round(deviation_pct, 2),
            detail=f"Rolling avg={avg_val:.2f}, current={current:.2f}, dev={deviation_pct:.1f}%",
        )


class ShiftComparisonEvaluator(BaseEvaluator):
    """Compare current 8-hour window vs same window 24 hours ago."""

    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        now = datetime.now(timezone.utc)
        window_hours = 8

        current_start = now - timedelta(hours=window_hours)
        prior_start = current_start - timedelta(hours=24)
        prior_end = now - timedelta(hours=24)

        async def _window_total(start: datetime, end: datetime) -> Optional[float]:
            clauses = [
                UtilityTransaction.utility_type == rule.utility_type,
                UtilityTransaction.created_at >= start,
                UtilityTransaction.created_at < end,
            ]
            if rule.device_id:
                clauses.append(UtilityTransaction.device_id == rule.device_id)
            if rule.asset_id:
                clauses.append(UtilityTransaction.asset_id == rule.asset_id)
            stmt = (
                select(func.sum(UtilityTransaction.quantity).label("total"))
                .where(and_(*clauses))
            )
            val = (await db.execute(stmt)).scalar()
            return float(val) if val is not None else None

        current_total = await _window_total(current_start, now)
        prior_total = await _window_total(prior_start, prior_end)

        if current_total is None or prior_total is None:
            return EvaluationResult(fired=False, detail="Insufficient data for shift comparison")

        if prior_total == 0:
            return EvaluationResult(fired=False, detail="Prior shift total is zero")

        deviation_pct = ((current_total - prior_total) / abs(prior_total)) * 100
        threshold_pct = float(rule.threshold_value)
        fired = _apply_operator(current_total, float(rule.threshold_value), rule.operator)

        return EvaluationResult(
            fired=fired,
            actual_value=round(current_total, 4),
            expected_value=round(prior_total, 4),
            deviation_pct=round(deviation_pct, 2),
            detail=f"Current shift={current_total:.2f}, prior={prior_total:.2f}, dev={deviation_pct:.1f}%",
        )


class VsStandardEvaluator(BaseEvaluator):
    """Compare actual value against a configured standard/expected value."""

    async def evaluate(self, db: AsyncSession, rule: UtilityAlarmRule) -> EvaluationResult:
        if rule.standard_value is None:
            return EvaluationResult(fired=False, detail="No standard_value configured")

        tx = await _latest_transaction(db, rule, hours_back=24)
        if tx is None:
            return EvaluationResult(fired=False, detail="No recent transaction found")

        actual = _get_tx_param_value(tx, rule.parameter)
        if actual is None:
            return EvaluationResult(fired=False, detail="Parameter value is null")

        standard = float(rule.standard_value)
        tolerance_pct = float(rule.threshold_value)

        if standard == 0:
            return EvaluationResult(fired=False, detail="Standard value is zero")

        deviation_pct = ((actual - standard) / abs(standard)) * 100
        fired = _apply_operator(actual, standard, rule.operator) and abs(deviation_pct) > tolerance_pct

        return EvaluationResult(
            fired=fired,
            actual_value=actual,
            expected_value=standard,
            deviation_pct=round(deviation_pct, 2),
            detail=f"Actual={actual:.2f}, standard={standard:.2f}, dev={deviation_pct:.1f}%",
        )


EVALUATOR_REGISTRY: dict[AlarmDetectionType, BaseEvaluator] = {
    AlarmDetectionType.THRESHOLD: ThresholdEvaluator(),
    AlarmDetectionType.SUDDEN_JUMP: SuddenJumpEvaluator(),
    AlarmDetectionType.ROLLING_DEVIATION: RollingDeviationEvaluator(),
    AlarmDetectionType.SHIFT_COMPARISON: ShiftComparisonEvaluator(),
    AlarmDetectionType.VS_STANDARD: VsStandardEvaluator(),
    # AlarmDetectionType.MACHINE_COMPARISON: MachineComparisonEvaluator(),  # future
}


async def _in_cooldown(db: AsyncSession, rule: UtilityAlarmRule) -> bool:
    """Return True if an ACTIVE event for this rule was created within cooldown_minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=rule.cooldown_minutes)
    stmt = select(func.count()).select_from(UtilityAlarmEvent).where(
        and_(
            UtilityAlarmEvent.rule_id == rule.id,
            UtilityAlarmEvent.status == AlarmStatus.ACTIVE,
            UtilityAlarmEvent.triggered_at >= cutoff,
        )
    )
    cnt = (await db.execute(stmt)).scalar_one()
    return cnt > 0


async def evaluate_rule(
    db: AsyncSession,
    rule: UtilityAlarmRule,
) -> Optional[UtilityAlarmEvent]:
    evaluator = EVALUATOR_REGISTRY.get(rule.detection_type)
    if evaluator is None:
        logger.warning("No evaluator for detection_type=%s", rule.detection_type)
        return None

    try:
        result = await evaluator.evaluate(db, rule)
    except Exception:
        logger.exception("Error evaluating rule %s (%s)", rule.rule_code, rule.id)
        return None

    if not result.fired:
        return None

    if await _in_cooldown(db, rule):
        logger.debug("Rule %s in cooldown, skipping event creation", rule.rule_code)
        return None

    event = await create_event(
        db,
        rule,
        triggered_value=result.actual_value or 0.0,
        expected_value=result.expected_value,
        deviation_pct=result.deviation_pct,
    )
    logger.info(
        "Alarm event created: %s for rule %s — %s",
        event.event_no,
        rule.rule_code,
        result.detail,
    )
    return event


async def evaluate_all_active_rules(db: AsyncSession) -> List[UtilityAlarmEvent]:
    stmt = select(UtilityAlarmRule).where(UtilityAlarmRule.is_active == True)  # noqa: E712
    rules = (await db.execute(stmt)).scalars().all()

    fired_events: List[UtilityAlarmEvent] = []
    for rule in rules:
        event = await evaluate_rule(db, rule)
        if event:
            fired_events.append(event)

    return fired_events
