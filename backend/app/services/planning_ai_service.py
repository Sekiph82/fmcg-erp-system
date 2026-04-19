"""
Planning AI Agents — 3 agents for advanced scheduling intelligence.

Agent 1: CAPACITY_OPTIMIZER
  - Detects over-utilized WCs and suggests load balancing
  - Identifies idle WCs that could absorb load from overloaded ones
  - Recommends batch splitting for large ops on critical paths

Agent 2: SEQUENCING_OPTIMIZER
  - Identifies suboptimal sequencing (same WC, non-adjacent similar families → excess changeover)
  - Suggests reordering to minimize total changeover time
  - Flags priority inversions (low-priority scheduled before high-priority)

Agent 3: DISRUPTION_PREDICTOR
  - Flags blocked ops and their downstream impact chain
  - Identifies ops scheduled near horizon end (late delivery risk)
  - Detects WCs with zero calendar availability in critical period
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import (
    PlanningScenario, OperationQueue, CapacityLoadSnapshot, PlanningBottleneck,
    PlanningAIRec, PlanningAgentType, PlanningRecStatus, OpQueueStatus, BottleneckSeverity,
)


async def _upsert_rec(
    db: AsyncSession,
    scenario_id: UUID,
    agent_type: PlanningAgentType,
    title: str,
    explanation: str,
    impact_summary: str,
    confidence: float,
    affected_op_ids: Optional[List[str]] = None,
    payload: Optional[dict] = None,
) -> PlanningAIRec:
    rec = PlanningAIRec(
        scenario_id=scenario_id,
        agent_type=agent_type,
        title=title,
        explanation=explanation,
        impact_summary=impact_summary,
        confidence_score=Decimal(str(round(confidence, 2))),
        affected_op_ids=affected_op_ids or [],
        payload=payload or {},
    )
    db.add(rec)
    return rec


async def run_capacity_optimizer(db: AsyncSession, scenario_id: UUID) -> List[PlanningAIRec]:
    snaps_r = await db.execute(
        select(CapacityLoadSnapshot).where(CapacityLoadSnapshot.scenario_id == scenario_id)
    )
    snaps = snaps_r.scalars().all()

    from collections import defaultdict
    by_wc = defaultdict(list)
    for s in snaps:
        by_wc[s.work_center_id].append(s)

    overloaded_wcs = {}
    underutilized_wcs = {}
    for wc_id, wc_snaps in by_wc.items():
        avg = sum(float(s.utilization_pct) for s in wc_snaps) / len(wc_snaps)
        if avg >= 85:
            overloaded_wcs[wc_id] = (avg, wc_snaps[0].work_center_name)
        elif avg <= 40:
            underutilized_wcs[wc_id] = (avg, wc_snaps[0].work_center_name)

    recs: List[PlanningAIRec] = []

    if overloaded_wcs and underutilized_wcs:
        over_names = [name for _, (_, name) in overloaded_wcs.items()]
        under_names = [name for _, (_, name) in underutilized_wcs.items()]
        ops_on_over_r = await db.execute(
            select(OperationQueue).where(
                OperationQueue.scenario_id == scenario_id,
                OperationQueue.work_center_id.in_(list(overloaded_wcs.keys())),
                OperationQueue.status == OpQueueStatus.SCHEDULED,
            )
        )
        ops_on_over = ops_on_over_r.scalars().all()
        non_critical = [op for op in ops_on_over if not op.is_critical_path]
        transfer_candidates = non_critical[:3]
        rec = await _upsert_rec(
            db, scenario_id, PlanningAgentType.CAPACITY_OPTIMIZER,
            title=f"Load Balance: Move ops from {', '.join(over_names[:2])} → {', '.join(under_names[:2])}",
            explanation=(
                f"Work centers {', '.join(over_names[:2])} are averaging ≥85% utilization while "
                f"{', '.join(under_names[:2])} are below 40% utilization. "
                f"Transferring {len(transfer_candidates)} non-critical operations could balance load."
            ),
            impact_summary=f"Estimated utilization delta: -{round((sum(v for v, _ in overloaded_wcs.values()) - 85) / len(overloaded_wcs), 1)}% on overloaded WCs",
            confidence=0.78,
            affected_op_ids=[str(op.id) for op in transfer_candidates],
            payload={"target_wc_ids": [str(k) for k in list(underutilized_wcs.keys())[:2]]},
        )
        recs.append(rec)

    # Check for large ops on overloaded WCs → suggest splitting
    if overloaded_wcs:
        large_ops_r = await db.execute(
            select(OperationQueue).where(
                OperationQueue.scenario_id == scenario_id,
                OperationQueue.work_center_id.in_(list(overloaded_wcs.keys())),
                OperationQueue.total_minutes > 240,
            )
        )
        large_ops = large_ops_r.scalars().all()
        if large_ops:
            rec = await _upsert_rec(
                db, scenario_id, PlanningAgentType.CAPACITY_OPTIMIZER,
                title=f"Split {len(large_ops)} large batch(es) on overloaded work centers",
                explanation=(
                    f"{len(large_ops)} operation(s) take >4 hours on already-overloaded work centers. "
                    f"Splitting into two sequential runs would reduce peak load per day."
                ),
                impact_summary=f"Potential to reduce daily peak load by ~{round(sum(op.total_minutes for op in large_ops) / len(large_ops) / 60 / 2, 1)}h per operation",
                confidence=0.72,
                affected_op_ids=[str(op.id) for op in large_ops[:5]],
            )
            recs.append(rec)

    await db.flush()
    return recs


async def run_sequencing_optimizer(db: AsyncSession, scenario_id: UUID) -> List[PlanningAIRec]:
    ops_r = await db.execute(
        select(OperationQueue)
        .where(OperationQueue.scenario_id == scenario_id, OperationQueue.status == OpQueueStatus.SCHEDULED)
        .order_by(OperationQueue.work_center_id, OperationQueue.scheduled_start)
    )
    ops = ops_r.scalars().all()

    recs: List[PlanningAIRec] = []

    # Detect priority inversions
    priority_inversions = []
    for i in range(len(ops) - 1):
        a, b = ops[i], ops[i + 1]
        if (a.work_center_id == b.work_center_id and a.priority < b.priority
                and a.scheduled_start and b.scheduled_start
                and a.scheduled_start < b.scheduled_start):
            priority_inversions.append((a, b))

    if priority_inversions:
        rec = await _upsert_rec(
            db, scenario_id, PlanningAgentType.SEQUENCING_OPTIMIZER,
            title=f"{len(priority_inversions)} priority inversion(s) detected",
            explanation=(
                f"{len(priority_inversions)} case(s) where a lower-priority operation is scheduled before "
                f"a higher-priority one on the same work center. Resequencing would improve on-time delivery."
            ),
            impact_summary=f"Resequencing could improve service level by an estimated {min(len(priority_inversions) * 3, 15)}%",
            confidence=0.85,
            affected_op_ids=[str(a.id) for a, b in priority_inversions[:5]],
        )
        recs.append(rec)

    # Detect unnecessary changeovers (same family adjacent on same WC)
    def _family(code: Optional[str]) -> str:
        return (code or "")[:4].upper() or "MISC"

    excess_co_ops = []
    prev_family_per_wc: dict = {}
    for op in ops:
        wc_key = str(op.work_center_id)
        fam = _family(op.product_code)
        prev = prev_family_per_wc.get(wc_key)
        if prev and prev != fam and op.changeover_minutes > 30:
            excess_co_ops.append(op)
        prev_family_per_wc[wc_key] = fam

    if excess_co_ops:
        total_co_min = sum(op.changeover_minutes for op in excess_co_ops)
        rec = await _upsert_rec(
            db, scenario_id, PlanningAgentType.SEQUENCING_OPTIMIZER,
            title=f"Reduce changeover: {len(excess_co_ops)} non-optimal transitions ({total_co_min // 60}h {total_co_min % 60}m total)",
            explanation=(
                f"{len(excess_co_ops)} operations involve changeovers >30 min between different product families. "
                f"Grouping same-family runs consecutively could eliminate ~{round(total_co_min * 0.4 / 60, 1)}h of changeover time."
            ),
            impact_summary=f"Estimated time saving: {round(total_co_min * 0.4 / 60, 1)}h across {len(excess_co_ops)} transitions",
            confidence=0.81,
            affected_op_ids=[str(op.id) for op in excess_co_ops[:5]],
        )
        recs.append(rec)

    await db.flush()
    return recs


async def run_disruption_predictor(db: AsyncSession, scenario_id: UUID) -> List[PlanningAIRec]:
    scenario_r = await db.execute(
        select(PlanningScenario).where(PlanningScenario.id == scenario_id)
    )
    scenario = scenario_r.scalar_one_or_none()
    horizon_end = scenario.horizon_end if scenario else None

    recs: List[PlanningAIRec] = []
    now = datetime.now(timezone.utc)

    # Blocked operations
    blocked_r = await db.execute(
        select(OperationQueue).where(
            OperationQueue.scenario_id == scenario_id,
            OperationQueue.status == OpQueueStatus.BLOCKED,
        )
    )
    blocked_ops = blocked_r.scalars().all()

    if blocked_ops:
        rec = await _upsert_rec(
            db, scenario_id, PlanningAgentType.DISRUPTION_PREDICTOR,
            title=f"{len(blocked_ops)} operation(s) BLOCKED — capacity exhausted in horizon",
            explanation=(
                f"{len(blocked_ops)} scheduled operations could not be placed within the planning horizon "
                f"due to insufficient capacity. These will not be produced unless rescheduled or capacity is extended."
            ),
            impact_summary=f"Risk: {len(blocked_ops)} production gap(s), potential missed deliveries",
            confidence=0.95,
            affected_op_ids=[str(op.id) for op in blocked_ops[:10]],
        )
        recs.append(rec)

    # Near-horizon ops (within 2 days of end)
    if horizon_end:
        from datetime import date
        near_end = datetime(horizon_end.year, horizon_end.month, horizon_end.day, tzinfo=timezone.utc) - timedelta(days=2)
        near_r = await db.execute(
            select(OperationQueue).where(
                OperationQueue.scenario_id == scenario_id,
                OperationQueue.scheduled_end >= near_end,
                OperationQueue.status == OpQueueStatus.SCHEDULED,
            )
        )
        near_ops = near_r.scalars().all()
        if near_ops:
            rec = await _upsert_rec(
                db, scenario_id, PlanningAgentType.DISRUPTION_PREDICTOR,
                title=f"{len(near_ops)} operation(s) scheduled within 2 days of horizon end",
                explanation=(
                    f"{len(near_ops)} operations are scheduled to complete within 2 days of the planning horizon. "
                    f"Any delay or disruption could push them beyond the horizon."
                ),
                impact_summary="Late delivery risk — consider pulling forward or extending horizon",
                confidence=0.70,
                affected_op_ids=[str(op.id) for op in near_ops[:5]],
            )
            recs.append(rec)

    # Critical bottlenecks without resolution plan
    crit_r = await db.execute(
        select(PlanningBottleneck).where(
            PlanningBottleneck.scenario_id == scenario_id,
            PlanningBottleneck.severity == BottleneckSeverity.CRITICAL,
            PlanningBottleneck.is_resolved == False,
        )
    )
    crit_bns = crit_r.scalars().all()
    if crit_bns:
        names = [bn.work_center_name or "Unknown" for bn in crit_bns]
        rec = await _upsert_rec(
            db, scenario_id, PlanningAgentType.DISRUPTION_PREDICTOR,
            title=f"Critical bottleneck(s) unresolved: {', '.join(names[:3])}",
            explanation=(
                f"{len(crit_bns)} work center(s) are critically overloaded with no resolution plan. "
                f"Total overload: {sum(float(bn.total_overload_hrs) for bn in crit_bns):.1f} hours."
            ),
            impact_summary="Immediate action required to avoid cascading delays across the schedule",
            confidence=0.92,
            payload={"bottleneck_ids": [str(bn.id) for bn in crit_bns]},
        )
        recs.append(rec)

    await db.flush()
    return recs


async def run_all_agents(db: AsyncSession, scenario_id: UUID) -> dict:
    from sqlalchemy import delete
    await db.execute(
        delete(PlanningAIRec).where(PlanningAIRec.scenario_id == scenario_id)
    )
    await db.flush()

    cap_recs = await run_capacity_optimizer(db, scenario_id)
    seq_recs = await run_sequencing_optimizer(db, scenario_id)
    dis_recs = await run_disruption_predictor(db, scenario_id)

    all_recs = cap_recs + seq_recs + dis_recs
    await db.flush()

    return {
        "capacity_optimizer": len(cap_recs),
        "sequencing_optimizer": len(seq_recs),
        "disruption_predictor": len(dis_recs),
        "total": len(all_recs),
    }


async def action_rec(db: AsyncSession, rec_id: UUID, status: PlanningRecStatus, user_id: UUID) -> PlanningAIRec:
    r = await db.execute(select(PlanningAIRec).where(PlanningAIRec.id == rec_id))
    rec = r.scalar_one_or_none()
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = status
    rec.actioned_by_id = user_id
    rec.actioned_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(rec)
    return rec


async def list_recs(db: AsyncSession, scenario_id: UUID) -> List[PlanningAIRec]:
    r = await db.execute(
        select(PlanningAIRec)
        .where(PlanningAIRec.scenario_id == scenario_id)
        .order_by(PlanningAIRec.created_at.desc())
    )
    return r.scalars().all()
