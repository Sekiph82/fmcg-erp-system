"""Bottleneck detection: identifies constrained resources from capacity snapshots."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import (
    CapacityLoadSnapshot, OperationQueue, PlanningBottleneck,
    BottleneckSeverity, OpQueueStatus,
)


_THRESHOLDS = {
    BottleneckSeverity.CRITICAL: 110.0,
    BottleneckSeverity.HIGH: 90.0,
    BottleneckSeverity.MEDIUM: 75.0,
    BottleneckSeverity.LOW: 60.0,
}


def _severity(peak_pct: float) -> BottleneckSeverity:
    if peak_pct >= _THRESHOLDS[BottleneckSeverity.CRITICAL]:
        return BottleneckSeverity.CRITICAL
    if peak_pct >= _THRESHOLDS[BottleneckSeverity.HIGH]:
        return BottleneckSeverity.HIGH
    if peak_pct >= _THRESHOLDS[BottleneckSeverity.MEDIUM]:
        return BottleneckSeverity.MEDIUM
    return BottleneckSeverity.LOW


def _recommendation(severity: BottleneckSeverity, wc_name: str, overloaded_days: int, overload_hrs: float) -> str:
    if severity == BottleneckSeverity.CRITICAL:
        return (
            f"{wc_name} is critically overloaded for {overloaded_days} day(s) "
            f"({overload_hrs:.1f} hrs excess). Consider adding overtime, outsourcing, "
            f"or splitting batch runs across adjacent work centers."
        )
    if severity == BottleneckSeverity.HIGH:
        return (
            f"{wc_name} has high utilization over {overloaded_days} day(s). "
            f"Review batch sizes or shift changeovers to reduce load."
        )
    return (
        f"{wc_name} is approaching capacity limits. Monitor closely and pre-allocate buffers."
    )


async def detect_bottlenecks(db: AsyncSession, scenario_id: UUID) -> List[PlanningBottleneck]:
    # Clear existing bottlenecks for this scenario
    await db.execute(
        delete(PlanningBottleneck).where(PlanningBottleneck.scenario_id == scenario_id)
    )
    await db.flush()

    snaps_r = await db.execute(
        select(CapacityLoadSnapshot).where(CapacityLoadSnapshot.scenario_id == scenario_id)
    )
    snaps = snaps_r.scalars().all()

    from collections import defaultdict
    by_wc = defaultdict(list)
    for s in snaps:
        by_wc[s.work_center_id].append(s)

    bottlenecks: List[PlanningBottleneck] = []

    for wc_id, wc_snaps in by_wc.items():
        peak = max((float(s.utilization_pct) for s in wc_snaps), default=0.0)
        if peak < 60.0:
            continue  # not a bottleneck

        overloaded = [s for s in wc_snaps if s.is_overloaded]
        total_overload = sum(float(s.overload_hours) for s in overloaded)
        wc_name = wc_snaps[0].work_center_name or str(wc_id)[:8]

        # Count blocked ops on this WC
        blocked_r = await db.execute(
            select(OperationQueue).where(
                OperationQueue.scenario_id == scenario_id,
                OperationQueue.work_center_id == wc_id,
                OperationQueue.status == OpQueueStatus.BLOCKED,
            )
        )
        blocked_count = len(blocked_r.scalars().all())

        sev = _severity(peak)
        bn = PlanningBottleneck(
            scenario_id=scenario_id,
            work_center_id=wc_id,
            work_center_name=wc_name,
            severity=sev,
            peak_utilization_pct=Decimal(str(round(peak, 2))),
            overloaded_days=len(overloaded),
            total_overload_hrs=Decimal(str(round(total_overload, 2))),
            blocked_op_count=blocked_count,
            recommendation=_recommendation(sev, wc_name, len(overloaded), total_overload),
            detected_at=datetime.now(timezone.utc),
        )
        db.add(bn)
        bottlenecks.append(bn)

    await db.flush()

    # Update scenario bottleneck count
    from app.models.planning import PlanningScenario
    sc_r = await db.execute(
        select(PlanningScenario).where(PlanningScenario.id == scenario_id)
    )
    sc = sc_r.scalar_one_or_none()
    if sc:
        sc.bottleneck_count = len(bottlenecks)
        await db.flush()

    return bottlenecks


async def list_bottlenecks(db: AsyncSession, scenario_id: UUID) -> List[PlanningBottleneck]:
    r = await db.execute(
        select(PlanningBottleneck)
        .where(PlanningBottleneck.scenario_id == scenario_id)
        .order_by(PlanningBottleneck.peak_utilization_pct.desc())
    )
    return r.scalars().all()


async def resolve_bottleneck(db: AsyncSession, bn_id: UUID) -> PlanningBottleneck:
    r = await db.execute(select(PlanningBottleneck).where(PlanningBottleneck.id == bn_id))
    bn = r.scalar_one_or_none()
    if not bn:
        raise ValueError("Bottleneck not found")
    bn.is_resolved = True
    await db.flush()
    await db.refresh(bn)
    return bn
