from __future__ import annotations

from typing import List, Optional
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.maintenance import (
    Asset, PMPlan, PMWorkOrder, BreakdownRecord, PMStatus, BreakdownStatus, AssetStatus,
    MaintenancePrediction, MaintenancePredictionRisk, MaintenancePredictionStatus,
)
from app.models.iot import SensorDataPoint, MachineStateEvent, IoTAlert, AlertSeverity, MachineState
from app.models.production import DowntimeLog
from app.schemas.maintenance import MtbfMttrRow, DowntimeByMachineRow, OverduePMRow


async def compute_mtbf_mttr(db: AsyncSession) -> List[MtbfMttrRow]:
    """MTBF/MTTR per asset from BreakdownRecord table."""
    # Load all resolved breakdowns grouped by asset
    q = (
        select(
            BreakdownRecord.asset_id,
            func.count(BreakdownRecord.id).label("cnt"),
            func.sum(BreakdownRecord.downtime_minutes).label("total_dt"),
        )
        .where(BreakdownRecord.downtime_minutes.isnot(None))
        .group_by(BreakdownRecord.asset_id)
    )
    rows = (await db.execute(q)).all()

    # Get first/last breakdown dates per asset for MTBF calculation
    date_q = (
        select(
            BreakdownRecord.asset_id,
            func.min(BreakdownRecord.start_time).label("first_bd"),
            func.max(BreakdownRecord.start_time).label("last_bd"),
        )
        .group_by(BreakdownRecord.asset_id)
    )
    date_rows = {r.asset_id: r for r in (await db.execute(date_q)).all()}

    # Load asset details
    asset_ids = [r.asset_id for r in rows]
    assets = {}
    if asset_ids:
        asset_q = select(Asset).where(Asset.id.in_(asset_ids))
        assets = {a.id: a for a in (await db.execute(asset_q)).scalars().all()}

    result = []
    for row in rows:
        asset = assets.get(row.asset_id)
        if not asset:
            continue
        cnt = row.cnt or 0
        total_dt = int(row.total_dt or 0)
        mttr = total_dt / cnt if cnt > 0 else 0.0

        mtbf = None
        dr = date_rows.get(row.asset_id)
        if dr and dr.first_bd and dr.last_bd and cnt > 1:
            span_days = (dr.last_bd - dr.first_bd).days
            mtbf = round(span_days / (cnt - 1), 2)

        result.append(MtbfMttrRow(
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            line=asset.line,
            breakdown_count=cnt,
            total_downtime_minutes=total_dt,
            avg_downtime_minutes=round(mttr, 2),
            mtbf_days=mtbf,
        ))

    result.sort(key=lambda r: r.total_downtime_minutes, reverse=True)
    return result


async def compute_downtime_by_machine(db: AsyncSession) -> List[DowntimeByMachineRow]:
    """Aggregated downtime per machine, including open breakdowns."""
    q = (
        select(
            BreakdownRecord.asset_id,
            func.count(BreakdownRecord.id).label("cnt"),
            func.coalesce(func.sum(BreakdownRecord.downtime_minutes), 0).label("total_dt"),
            func.sum(
                func.cast(
                    BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR]),
                    type_=None,
                )
            ).label("open_cnt"),
        )
        .group_by(BreakdownRecord.asset_id)
    )
    rows = (await db.execute(q)).all()

    # Also pull in MES DowntimeLogs that have machine_id matching asset.asset_no
    mes_q = (
        select(
            DowntimeLog.machine_id,
            func.count(DowntimeLog.id).label("mes_cnt"),
            func.coalesce(func.sum(DowntimeLog.duration_minutes), 0).label("mes_dt"),
        )
        .where(DowntimeLog.machine_id.isnot(None))
        .group_by(DowntimeLog.machine_id)
    )
    mes_rows = {r.machine_id: r for r in (await db.execute(mes_q)).all()}

    asset_ids = [r.asset_id for r in rows]
    assets = {}
    if asset_ids:
        asset_q = select(Asset).where(Asset.id.in_(asset_ids))
        assets = {a.id: a for a in (await db.execute(asset_q)).scalars().all()}

    result = []
    for row in rows:
        asset = assets.get(row.asset_id)
        if not asset:
            continue
        # Add MES downtime if asset_no matches a machine_id in DowntimeLogs
        mes = mes_rows.get(asset.asset_no)
        extra_dt = int(mes.mes_dt) if mes else 0

        result.append(DowntimeByMachineRow(
            asset_id=str(asset.id),
            asset_no=asset.asset_no,
            asset_name=asset.name,
            line=asset.line,
            breakdown_count=int(row.cnt) + (int(mes.mes_cnt) if mes else 0),
            total_downtime_minutes=int(row.total_dt) + extra_dt,
            open_breakdowns=int(row.open_cnt or 0),
        ))

    result.sort(key=lambda r: r.total_downtime_minutes, reverse=True)
    return result


async def overdue_pm_list(db: AsyncSession) -> List[OverduePMRow]:
    """Plans where next_due_date < today and status is not completed."""
    today = date.today()
    q = (
        select(PMPlan)
        .options(selectinload(PMPlan.asset))
        .where(
            PMPlan.is_active == True,  # noqa: E712
            PMPlan.next_due_date < today,
        )
        .order_by(PMPlan.next_due_date)
    )
    plans = list((await db.execute(q)).scalars().all())

    result = []
    for p in plans:
        if not p.asset:
            continue
        days_overdue = (today - p.next_due_date).days if p.next_due_date else 0
        result.append(OverduePMRow(
            plan_id=str(p.id),
            asset_id=str(p.asset_id),
            asset_no=p.asset.asset_no,
            asset_name=p.asset.name,
            plan_name=p.name,
            frequency=p.frequency,
            next_due_date=p.next_due_date,
            days_overdue=days_overdue,
        ))

    return result


def next_wo_no(existing_count: int) -> str:
    return f"WO-{existing_count + 1:06d}"


def next_bd_no(existing_count: int) -> str:
    return f"BD-{existing_count + 1:06d}"


# Predictive Maintenance

async def generate_maintenance_predictions(
    db: AsyncSession,
    horizon_days: int = 30,
) -> List[MaintenancePrediction]:
    """
    Rule-based predictive maintenance using IoT trend signals plus breakdown history.
    The algorithm is intentionally explainable: each score component is stored in source_metrics.
    """
    horizon_days = max(7, min(horizon_days, 90))
    assets = list((await db.execute(
        select(Asset).where(Asset.status != AssetStatus.DECOMMISSIONED).order_by(Asset.asset_no)
    )).scalars().all())

    generated: List[MaintenancePrediction] = []
    for asset in assets:
        machine_id = asset.asset_no
        signal = await _prediction_signal_for_machine(db, asset, machine_id, horizon_days)
        if signal["score"] < 20:
            continue

        risk = _risk_from_score(signal["score"])
        predicted_date = date.today() + timedelta(days=_days_to_failure(signal["score"], horizon_days))
        confidence = min(0.95, max(0.35, signal["score"] / 100))

        existing = (await db.execute(
            select(MaintenancePrediction).where(
                MaintenancePrediction.machine_id == machine_id,
                MaintenancePrediction.failure_mode == signal["failure_mode"],
                MaintenancePrediction.status.in_([
                    MaintenancePredictionStatus.OPEN,
                    MaintenancePredictionStatus.REVIEWED,
                ]),
            ).order_by(MaintenancePrediction.generated_at.desc())
        )).scalars().first()

        if existing:
            pred = existing
            pred.asset_id = asset.id
            pred.machine_name = asset.name
            pred.predicted_failure_date = predicted_date
            pred.confidence = round(confidence, 4)
            pred.risk_level = risk
            pred.recommended_action = signal["recommended_action"]
            pred.evidence_summary = signal["evidence_summary"]
            pred.source_metrics = signal["source_metrics"]
            pred.generated_at = datetime.utcnow()
            if pred.status == MaintenancePredictionStatus.DISMISSED:
                pred.status = MaintenancePredictionStatus.OPEN
        else:
            pred = MaintenancePrediction(
                asset_id=asset.id,
                machine_id=machine_id,
                machine_name=asset.name,
                predicted_failure_date=predicted_date,
                confidence=round(confidence, 4),
                risk_level=risk,
                failure_mode=signal["failure_mode"],
                recommended_action=signal["recommended_action"],
                evidence_summary=signal["evidence_summary"],
                source_metrics=signal["source_metrics"],
                status=MaintenancePredictionStatus.OPEN,
                generated_at=datetime.utcnow(),
            )
            db.add(pred)
        generated.append(pred)

    await db.flush()
    for pred in generated:
        await db.refresh(pred)
    return generated


async def list_maintenance_predictions(
    db: AsyncSession,
    status: Optional[MaintenancePredictionStatus] = None,
    risk_level: Optional[MaintenancePredictionRisk] = None,
    machine_id: Optional[str] = None,
    limit: int = 100,
) -> List[MaintenancePrediction]:
    q = (
        select(MaintenancePrediction)
        .options(selectinload(MaintenancePrediction.asset))
        .order_by(MaintenancePrediction.predicted_failure_date, MaintenancePrediction.risk_level.desc())
        .limit(limit)
    )
    if status:
        q = q.where(MaintenancePrediction.status == status)
    if risk_level:
        q = q.where(MaintenancePrediction.risk_level == risk_level)
    if machine_id:
        q = q.where(MaintenancePrediction.machine_id == machine_id)
    return list((await db.execute(q)).scalars().all())


async def get_maintenance_prediction(db: AsyncSession, prediction_id) -> Optional[MaintenancePrediction]:
    return (await db.execute(
        select(MaintenancePrediction)
        .options(selectinload(MaintenancePrediction.asset))
        .where(MaintenancePrediction.id == prediction_id)
    )).scalar_one_or_none()


async def review_maintenance_prediction(
    db: AsyncSession,
    pred: MaintenancePrediction,
    status_value: MaintenancePredictionStatus,
    reviewed_by: str,
    notes: Optional[str] = None,
) -> MaintenancePrediction:
    pred.status = status_value
    pred.reviewed_by = reviewed_by
    pred.reviewed_at = datetime.utcnow()
    pred.review_notes = notes
    await db.flush()
    await db.refresh(pred)
    return pred


async def _prediction_signal_for_machine(
    db: AsyncSession,
    asset: Asset,
    machine_id: str,
    horizon_days: int,
) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=horizon_days)
    readings = list((await db.execute(
        select(SensorDataPoint)
        .where(
            SensorDataPoint.machine_id == machine_id,
            SensorDataPoint.quality_flag == True,  # noqa: E712
            SensorDataPoint.recorded_at >= cutoff,
        )
        .order_by(SensorDataPoint.metric_name, SensorDataPoint.recorded_at)
    )).scalars().all())

    metric_groups: dict[str, list[float]] = {}
    for reading in readings:
        metric_groups.setdefault(reading.metric_name.lower(), []).append(float(reading.value))

    score = 0
    evidence: list[str] = []
    metric_scores: dict[str, dict] = {}
    failure_mode = "General reliability risk"
    recommended_action = "Review machine condition and schedule a targeted inspection."

    for metric, values in metric_groups.items():
        if len(values) < 3:
            continue
        first_avg = sum(values[: max(1, len(values) // 3)]) / max(1, len(values[: max(1, len(values) // 3)]))
        last_slice = values[-max(1, len(values) // 3):]
        last_avg = sum(last_slice) / len(last_slice)
        trend_pct = ((last_avg - first_avg) / abs(first_avg) * 100) if first_avg else 0
        metric_score = 0

        if "vibration" in metric:
            if last_avg >= 7 or trend_pct >= 25:
                metric_score = 35
                failure_mode = "Bearing or alignment degradation"
                recommended_action = "Inspect bearings, shaft alignment, lubrication, and mounting bolts within the prediction window."
        elif "temp" in metric:
            if last_avg >= 80 or trend_pct >= 20:
                metric_score = 25
                failure_mode = "Thermal stress or cooling degradation"
                recommended_action = "Inspect cooling, lubrication, load, and motor ventilation before the next production run."
        elif "current" in metric or "amp" in metric:
            if trend_pct >= 18:
                metric_score = 20
                failure_mode = "Motor overload or electrical imbalance"
                recommended_action = "Check motor load, drive settings, current imbalance, and panel condition."
        elif "pressure" in metric:
            if abs(trend_pct) >= 25:
                metric_score = 15
                failure_mode = "Pneumatic or hydraulic pressure instability"
                recommended_action = "Inspect leaks, filters, regulators, valves, and compressor feed stability."

        if metric_score:
            score += metric_score
            evidence.append(f"{metric} trend {trend_pct:.1f}% with latest average {last_avg:.2f}")
            metric_scores[metric] = {
                "first_avg": round(first_avg, 4),
                "latest_avg": round(last_avg, 4),
                "trend_pct": round(trend_pct, 2),
                "score": metric_score,
                "readings": len(values),
            }

    state_rows = list((await db.execute(
        select(MachineStateEvent)
        .where(
            MachineStateEvent.machine_id == machine_id,
            MachineStateEvent.changed_at >= cutoff,
            MachineStateEvent.state.in_([MachineState.DOWN, MachineState.FAULT]),
        )
    )).scalars().all())
    if state_rows:
        add = min(20, len(state_rows) * 5)
        score += add
        evidence.append(f"{len(state_rows)} DOWN/FAULT state events in the analysis window")

    alert_rows = list((await db.execute(
        select(IoTAlert)
        .where(
            IoTAlert.machine_id == machine_id,
            IoTAlert.triggered_at >= cutoff,
            IoTAlert.severity == AlertSeverity.CRITICAL,
        )
    )).scalars().all())
    if alert_rows:
        add = min(25, len(alert_rows) * 10)
        score += add
        evidence.append(f"{len(alert_rows)} critical IoT alerts in the analysis window")

    bd_cutoff = datetime.utcnow() - timedelta(days=90)
    breakdowns = list((await db.execute(
        select(BreakdownRecord)
        .where(BreakdownRecord.asset_id == asset.id, BreakdownRecord.start_time >= bd_cutoff)
    )).scalars().all())
    if breakdowns:
        add = min(30, len(breakdowns) * 10)
        score += add
        evidence.append(f"{len(breakdowns)} breakdowns in the last 90 days")
        if not metric_scores:
            failure_mode = "Recurring breakdown pattern"
            recommended_action = "Review recent breakdown root causes and schedule reliability inspection."

    if not evidence:
        evidence.append("No adverse IoT or breakdown trend detected in the current analysis window")

    return {
        "score": min(100, score),
        "failure_mode": failure_mode,
        "recommended_action": recommended_action,
        "evidence_summary": "; ".join(evidence),
        "source_metrics": {
            "machine_id": machine_id,
            "analysis_window_days": horizon_days,
            "metric_scores": metric_scores,
            "state_events": len(state_rows),
            "critical_alerts": len(alert_rows),
            "recent_breakdowns": len(breakdowns),
            "score": min(100, score),
        },
    }


def _risk_from_score(score: int) -> MaintenancePredictionRisk:
    if score >= 75:
        return MaintenancePredictionRisk.CRITICAL
    if score >= 55:
        return MaintenancePredictionRisk.HIGH
    if score >= 35:
        return MaintenancePredictionRisk.MEDIUM
    return MaintenancePredictionRisk.LOW


def _days_to_failure(score: int, horizon_days: int) -> int:
    if score >= 75:
        return 7
    if score >= 55:
        return 14
    if score >= 35:
        return min(21, horizon_days)
    return min(45, max(21, horizon_days))
