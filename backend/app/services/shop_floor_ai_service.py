"""Shop Floor AI agents — anomaly detection, supervisor assistance, operator guidance."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_execution import ExecWorkOrder, ProdExecOrder
from app.models.shop_floor import (
    SFAIRec, SFDowntimeLog, WOActivityLog,
    SFAIAgentType, SFAIRecStatus,
)


async def run_execution_anomaly_detector(db: AsyncSession) -> list[SFAIRec]:
    """Detect anomalies in recent shop floor execution."""
    now = datetime.now(timezone.utc)
    window = now - timedelta(hours=8)

    # Clear old pending recs from this agent
    old = await db.execute(
        select(SFAIRec).where(
            SFAIRec.agent_type == SFAIAgentType.EXECUTION_ANOMALY_DETECTOR,
            SFAIRec.status == SFAIRecStatus.PENDING,
        )
    )
    for r in old.scalars().all():
        await db.delete(r)

    recs: list[SFAIRec] = []

    # Fetch active work orders
    result = await db.execute(
        select(ExecWorkOrder).where(
            ExecWorkOrder.status.in_(["IN_PROGRESS", "PAUSED", "READY"])
        )
    )
    wos = result.scalars().all()

    for wo in wos:
        # Scrap spike: scrap_qty > 5% of completed
        if wo.completed_qty and wo.completed_qty > 0:
            scrap_pct = float(wo.scrap_qty or 0) / float(wo.completed_qty) * 100
            if scrap_pct > 5:
                recs.append(SFAIRec(
                    id=uuid.uuid4(),
                    work_order_id=wo.id,
                    agent_type=SFAIAgentType.EXECUTION_ANOMALY_DETECTOR,
                    status=SFAIRecStatus.PENDING,
                    title=f"High scrap rate: {scrap_pct:.1f}% on WO {wo.step_name}",
                    explanation=(
                        f"Work order '{wo.step_name}' (step {wo.step_sequence}) has "
                        f"scrap rate of {scrap_pct:.1f}%, exceeding the 5% threshold. "
                        f"Scrap qty: {wo.scrap_qty}, Completed: {wo.completed_qty}."
                    ),
                    impact_summary="High scrap increases material cost and may indicate process or quality issues.",
                    confidence_score=Decimal("0.88"),
                ))

        # Run time deviation: actual > 1.5x planned
        if wo.run_time_planned and wo.run_time_planned > 0 and wo.run_time_actual:
            ratio = float(wo.run_time_actual) / float(wo.run_time_planned)
            if ratio > 1.5:
                recs.append(SFAIRec(
                    id=uuid.uuid4(),
                    work_order_id=wo.id,
                    agent_type=SFAIAgentType.EXECUTION_ANOMALY_DETECTOR,
                    status=SFAIRecStatus.PENDING,
                    title=f"Run time deviation {ratio:.1f}x planned on '{wo.step_name}'",
                    explanation=(
                        f"Actual run time ({wo.run_time_actual:.0f} min) is "
                        f"{ratio:.1f}x the planned time ({wo.run_time_planned:.0f} min). "
                        "This may indicate machine issues, material delays, or operator capacity constraints."
                    ),
                    impact_summary="Excessive run time delays downstream work orders and affects OEE.",
                    confidence_score=Decimal("0.82"),
                ))

        # Overdue: IN_PROGRESS past planned_end
        if wo.status == "IN_PROGRESS" and wo.planned_end and wo.planned_end < now:
            overdue_min = int((now - wo.planned_end).total_seconds() / 60)
            recs.append(SFAIRec(
                id=uuid.uuid4(),
                work_order_id=wo.id,
                agent_type=SFAIAgentType.EXECUTION_ANOMALY_DETECTOR,
                status=SFAIRecStatus.PENDING,
                title=f"Work order overdue by {overdue_min} minutes: '{wo.step_name}'",
                explanation=(
                    f"WO '{wo.step_name}' passed its planned end time by {overdue_min} minutes. "
                    "Consider escalating to supervisor or adjusting the schedule."
                ),
                impact_summary="Overdue work orders risk delaying downstream steps and final production targets.",
                confidence_score=Decimal("0.91"),
            ))

    # Downtime frequency: any line with > 3 downtime events in 8-hour window
    dt_result = await db.execute(
        select(SFDowntimeLog).where(SFDowntimeLog.start_time >= window)
    )
    dt_logs = dt_result.scalars().all()

    line_dt_count: dict[str, int] = {}
    for dt in dt_logs:
        if dt.line_id:
            line_dt_count[dt.line_id] = line_dt_count.get(dt.line_id, 0) + 1

    for line_id, count in line_dt_count.items():
        if count > 3:
            recs.append(SFAIRec(
                id=uuid.uuid4(),
                work_order_id=None,
                agent_type=SFAIAgentType.EXECUTION_ANOMALY_DETECTOR,
                status=SFAIRecStatus.PENDING,
                title=f"High downtime frequency on line {line_id}: {count} events in 8h",
                explanation=(
                    f"Line '{line_id}' has experienced {count} downtime events in the last 8 hours. "
                    "Frequent interruptions indicate recurring equipment or process issues requiring investigation."
                ),
                impact_summary="Recurring downtime reduces OEE and throughput. Preventive maintenance or root cause analysis recommended.",
                confidence_score=Decimal("0.85"),
            ))

    for rec in recs:
        db.add(rec)
    await db.flush()
    return recs


async def run_supervisor_assistant(db: AsyncSession) -> list[SFAIRec]:
    """Identify orders/lines requiring supervisor attention."""
    now = datetime.now(timezone.utc)
    window_2h = now - timedelta(hours=2)

    old = await db.execute(
        select(SFAIRec).where(
            SFAIRec.agent_type == SFAIAgentType.SUPERVISOR_ASSISTANT,
            SFAIRec.status == SFAIRecStatus.PENDING,
        )
    )
    for r in old.scalars().all():
        await db.delete(r)

    recs: list[SFAIRec] = []

    # Open help requests in last 2 hours
    help_result = await db.execute(
        select(WOActivityLog).where(
            WOActivityLog.event_type == "HELP_REQUEST",
            WOActivityLog.timestamp_start >= window_2h,
        )
    )
    help_logs = help_result.scalars().all()
    if help_logs:
        wo_ids = list({str(h.work_order_id) for h in help_logs})
        recs.append(SFAIRec(
            id=uuid.uuid4(),
            work_order_id=help_logs[0].work_order_id,
            agent_type=SFAIAgentType.SUPERVISOR_ASSISTANT,
            status=SFAIRecStatus.PENDING,
            title=f"{len(help_logs)} open help request(s) need supervisor response",
            explanation=(
                f"{len(help_logs)} help requests have been raised in the last 2 hours on "
                f"{len(wo_ids)} work order(s). Operators are waiting for supervisor assistance."
            ),
            impact_summary="Unresolved help requests stall execution and reduce operator efficiency.",
            confidence_score=Decimal("0.95"),
        ))

    # QC holds older than 1 hour
    qc_result = await db.execute(
        select(WOActivityLog).where(
            WOActivityLog.event_type == "QC_TRIGGER",
            WOActivityLog.timestamp_start < now - timedelta(hours=1),
            WOActivityLog.timestamp_end.is_(None),
        )
    )
    qc_logs = qc_result.scalars().all()
    if qc_logs:
        recs.append(SFAIRec(
            id=uuid.uuid4(),
            work_order_id=qc_logs[0].work_order_id,
            agent_type=SFAIAgentType.SUPERVISOR_ASSISTANT,
            status=SFAIRecStatus.PENDING,
            title=f"{len(qc_logs)} QC hold(s) unresolved for over 1 hour",
            explanation=(
                f"{len(qc_logs)} work order(s) have been waiting for QC clearance for more than 1 hour. "
                "Supervisor should expedite QC review to unblock production."
            ),
            impact_summary="Long QC holds delay production order completion and affect customer delivery timelines.",
            confidence_score=Decimal("0.90"),
        ))

    # Long-running open downtime > 45 minutes
    dt_result = await db.execute(
        select(SFDowntimeLog).where(
            SFDowntimeLog.is_closed == False,
            SFDowntimeLog.start_time < now - timedelta(minutes=45),
        )
    )
    long_dt = dt_result.scalars().all()
    for dt in long_dt:
        elapsed = int((now - dt.start_time).total_seconds() / 60)
        recs.append(SFAIRec(
            id=uuid.uuid4(),
            work_order_id=dt.work_order_id,
            agent_type=SFAIAgentType.SUPERVISOR_ASSISTANT,
            status=SFAIRecStatus.PENDING,
            title=f"Downtime on {dt.line_id or 'unknown line'} running {elapsed} min ({dt.downtime_category})",
            explanation=(
                f"A {dt.downtime_category} downtime event on line '{dt.line_id}' has been running "
                f"for {elapsed} minutes. Impact level: {dt.impact_level}. "
                f"Root reason: {dt.root_reason or 'not specified'}."
            ),
            impact_summary="Extended downtime is significantly reducing line throughput. Supervisor escalation or maintenance dispatch recommended.",
            confidence_score=Decimal("0.93"),
        ))

    # Multiple paused orders
    paused_result = await db.execute(
        select(ExecWorkOrder).where(ExecWorkOrder.status == "PAUSED")
    )
    paused = paused_result.scalars().all()
    if len(paused) >= 3:
        recs.append(SFAIRec(
            id=uuid.uuid4(),
            work_order_id=None,
            agent_type=SFAIAgentType.SUPERVISOR_ASSISTANT,
            status=SFAIRecStatus.PENDING,
            title=f"{len(paused)} work orders currently paused — review required",
            explanation=(
                f"{len(paused)} work orders are in PAUSED state. Cluster pauses may indicate "
                "a systemic issue (material shortage, quality hold, equipment problem) that needs supervisor assessment."
            ),
            impact_summary="Multiple paused orders will cascade delays across the production schedule.",
            confidence_score=Decimal("0.80"),
        ))

    for rec in recs:
        db.add(rec)
    await db.flush()
    return recs


async def run_operator_guidance_assistant(db: AsyncSession) -> list[SFAIRec]:
    """Provide guidance and reminders to operators based on current WO state."""
    now = datetime.now(timezone.utc)

    old = await db.execute(
        select(SFAIRec).where(
            SFAIRec.agent_type == SFAIAgentType.OPERATOR_GUIDANCE,
            SFAIRec.status == SFAIRecStatus.PENDING,
        )
    )
    for r in old.scalars().all():
        await db.delete(r)

    recs: list[SFAIRec] = []

    # WOs in READY state for more than 30 minutes without being started
    ready_result = await db.execute(
        select(ExecWorkOrder).where(
            ExecWorkOrder.status == "READY",
            ExecWorkOrder.planned_start < now - timedelta(minutes=30),
        )
    )
    ready_wos = ready_result.scalars().all()
    for wo in ready_wos:
        wait_min = int((now - wo.planned_start).total_seconds() / 60) if wo.planned_start else 0
        recs.append(SFAIRec(
            id=uuid.uuid4(),
            work_order_id=wo.id,
            agent_type=SFAIAgentType.OPERATOR_GUIDANCE,
            status=SFAIRecStatus.PENDING,
            title=f"WO '{wo.step_name}' has been READY for {wait_min} min — start when available",
            explanation=(
                f"Work order '{wo.step_name}' (step {wo.step_sequence}) is ready to begin "
                f"but has not been started. It was scheduled to start {wait_min} minutes ago. "
                "Ensure materials and machines are confirmed before starting."
            ),
            impact_summary="Delayed start reduces available production window and may push order into next shift.",
            confidence_score=Decimal("0.78"),
        ))

    # QC required flag on IN_PROGRESS orders with no QC trigger
    qc_needed_result = await db.execute(
        select(ExecWorkOrder).where(
            ExecWorkOrder.status == "IN_PROGRESS",
            ExecWorkOrder.qc_required_flag == True,
            ExecWorkOrder.qc_passed.is_(None),
        )
    )
    qc_needed = qc_needed_result.scalars().all()

    for wo in qc_needed:
        # Check if QC trigger has been fired
        qc_log_result = await db.execute(
            select(WOActivityLog).where(
                WOActivityLog.work_order_id == wo.id,
                WOActivityLog.event_type == "QC_TRIGGER",
            )
        )
        triggered = qc_log_result.scalars().first()
        if not triggered:
            recs.append(SFAIRec(
                id=uuid.uuid4(),
                work_order_id=wo.id,
                agent_type=SFAIAgentType.OPERATOR_GUIDANCE,
                status=SFAIRecStatus.PENDING,
                title=f"QC checkpoint required for WO '{wo.step_name}'",
                explanation=(
                    f"Work order '{wo.step_name}' requires a QC inspection before completion. "
                    "No QC trigger has been recorded yet. Please trigger QC check when "
                    "the batch reaches the inspection point."
                ),
                impact_summary="Skipping QC checkpoint risks releasing non-conforming product.",
                confidence_score=Decimal("0.92"),
            ))

    # Operator has not logged a qty update in > 1 hour for running WO
    running_result = await db.execute(
        select(ExecWorkOrder).where(ExecWorkOrder.status == "IN_PROGRESS")
    )
    running_wos = running_result.scalars().all()
    window_1h = now - timedelta(hours=1)

    for wo in running_wos:
        last_qty_result = await db.execute(
            select(WOActivityLog).where(
                WOActivityLog.work_order_id == wo.id,
                WOActivityLog.event_type.in_(["QTY_UPDATE", "SCRAP", "START"]),
            ).order_by(WOActivityLog.timestamp_start.desc()).limit(1)
        )
        last_qty_log = last_qty_result.scalars().first()
        if last_qty_log and last_qty_log.timestamp_start < window_1h:
            idle_min = int((now - last_qty_log.timestamp_start).total_seconds() / 60)
            recs.append(SFAIRec(
                id=uuid.uuid4(),
                work_order_id=wo.id,
                agent_type=SFAIAgentType.OPERATOR_GUIDANCE,
                status=SFAIRecStatus.PENDING,
                title=f"No quantity update logged for '{wo.step_name}' in {idle_min} min",
                explanation=(
                    f"Work order '{wo.step_name}' is running but no quantity update has been "
                    f"recorded in the last {idle_min} minutes. Please log production count or "
                    "report any issues preventing progress."
                ),
                impact_summary="Lack of quantity reporting makes it impossible to track actual vs planned progress.",
                confidence_score=Decimal("0.75"),
            ))

    for rec in recs:
        db.add(rec)
    await db.flush()
    return recs


async def run_all_agents(db: AsyncSession) -> dict:
    anomaly_recs = await run_execution_anomaly_detector(db)
    supervisor_recs = await run_supervisor_assistant(db)
    guidance_recs = await run_operator_guidance_assistant(db)
    await db.commit()
    return {
        "anomaly_detector": len(anomaly_recs),
        "supervisor_assistant": len(supervisor_recs),
        "operator_guidance": len(guidance_recs),
        "total": len(anomaly_recs) + len(supervisor_recs) + len(guidance_recs),
    }
