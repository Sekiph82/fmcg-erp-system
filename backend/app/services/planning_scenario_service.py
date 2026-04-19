"""Planning scenario CRUD + sequence generation."""
from __future__ import annotations
import random
import string
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import (
    PlanningScenario, ScenarioStatus, ScenarioMode,
)
from app.schemas.planning import ScenarioCreate, ScenarioUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_no() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    return f"PLAN-{suffix}"


async def create_scenario(db: AsyncSession, req: ScenarioCreate, user_id: UUID) -> PlanningScenario:
    scenario = PlanningScenario(
        scenario_no=_gen_no(),
        scenario_name=req.scenario_name,
        description=req.description,
        mode=req.mode,
        horizon_start=req.horizon_start,
        horizon_end=req.horizon_end,
        mps_plan_id=req.mps_plan_id,
        created_by_id=user_id,
    )
    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)
    return scenario


async def list_scenarios(db: AsyncSession, status: Optional[ScenarioStatus] = None) -> List[PlanningScenario]:
    q = select(PlanningScenario).order_by(PlanningScenario.created_at.desc())
    if status:
        q = q.where(PlanningScenario.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def get_scenario(db: AsyncSession, scenario_id: UUID) -> Optional[PlanningScenario]:
    result = await db.execute(
        select(PlanningScenario).where(PlanningScenario.id == scenario_id)
    )
    return result.scalar_one_or_none()


async def update_scenario(db: AsyncSession, scenario: PlanningScenario, req: ScenarioUpdate) -> PlanningScenario:
    data = req.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(scenario, k, v)
    await db.flush()
    await db.refresh(scenario)
    return scenario


async def activate_scenario(db: AsyncSession, scenario: PlanningScenario) -> PlanningScenario:
    # deactivate any other ACTIVE scenario
    active = await db.execute(
        select(PlanningScenario).where(
            PlanningScenario.status == ScenarioStatus.ACTIVE,
            PlanningScenario.id != scenario.id,
        )
    )
    for s in active.scalars().all():
        s.status = ScenarioStatus.ARCHIVED

    scenario.status = ScenarioStatus.ACTIVE
    await db.flush()
    await db.refresh(scenario)
    return scenario


async def lock_scenario(db: AsyncSession, scenario: PlanningScenario) -> PlanningScenario:
    scenario.status = ScenarioStatus.LOCKED
    await db.flush()
    await db.refresh(scenario)
    return scenario


async def archive_scenario(db: AsyncSession, scenario: PlanningScenario) -> PlanningScenario:
    scenario.status = ScenarioStatus.ARCHIVED
    await db.flush()
    await db.refresh(scenario)
    return scenario


async def get_dashboard_data(db: AsyncSession) -> dict:
    from app.models.planning import OperationQueue, PlanningBottleneck, PlanningAIRec, PlanningRecStatus, OpQueueStatus

    scenarios = await list_scenarios(db)
    active = [s for s in scenarios if s.status == ScenarioStatus.ACTIVE]
    total = len(scenarios)

    all_ops_r = await db.execute(select(func.count(OperationQueue.id)))
    all_ops = all_ops_r.scalar() or 0

    sched_ops_r = await db.execute(
        select(func.count(OperationQueue.id)).where(OperationQueue.status == OpQueueStatus.SCHEDULED)
    )
    sched_ops = sched_ops_r.scalar() or 0
    scheduled_pct = round(sched_ops / all_ops * 100, 1) if all_ops else 0.0

    avg_util_r = await db.execute(
        select(func.avg(PlanningScenario.avg_utilization_pct)).where(
            PlanningScenario.avg_utilization_pct.isnot(None)
        )
    )
    avg_util = float(avg_util_r.scalar() or 0)

    from app.models.planning import BottleneckSeverity
    crit_r = await db.execute(
        select(func.count(PlanningBottleneck.id)).where(
            PlanningBottleneck.severity == BottleneckSeverity.CRITICAL,
            PlanningBottleneck.is_resolved == False,
        )
    )
    critical_bn = crit_r.scalar() or 0

    pending_ai_r = await db.execute(
        select(func.count(PlanningAIRec.id)).where(PlanningAIRec.status == PlanningRecStatus.PENDING)
    )
    pending_ai = pending_ai_r.scalar() or 0

    top_bn_r = await db.execute(
        select(PlanningBottleneck)
        .where(PlanningBottleneck.is_resolved == False)
        .order_by(PlanningBottleneck.peak_utilization_pct.desc())
        .limit(5)
    )
    top_bns = top_bn_r.scalars().all()

    ai_r = await db.execute(
        select(PlanningAIRec)
        .where(PlanningAIRec.status == PlanningRecStatus.PENDING)
        .order_by(PlanningAIRec.created_at.desc())
        .limit(5)
    )
    ai_recs = ai_r.scalars().all()

    return {
        "active_scenarios": len(active),
        "total_ops_today": all_ops,
        "scheduled_pct": scheduled_pct,
        "avg_utilization_pct": avg_util,
        "critical_bottlenecks": critical_bn,
        "pending_ai_recs": pending_ai,
        "scenarios": scenarios[:10],
        "top_bottlenecks": top_bns,
        "recent_ai_recs": ai_recs,
    }
