"""What-if simulation for planning scenarios — in-memory delta computation."""
from __future__ import annotations
import copy
import random
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import (
    PlanningScenario, OperationQueue, CapacityLoadSnapshot, PlanningSimulation,
    SimulationStatus,
)


def _sim_no() -> str:
    sfx = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    return f"SIM-{sfx}"


async def create_simulation(
    db: AsyncSession, scenario_id: UUID, sim_name: str, description: Optional[str], changes: List[dict]
) -> PlanningSimulation:
    sim = PlanningSimulation(
        sim_no=_sim_no(),
        sim_name=sim_name,
        description=description,
        scenario_id=scenario_id,
        status=SimulationStatus.DRAFT,
        changes=changes,
    )
    db.add(sim)
    await db.flush()
    await db.refresh(sim)
    return sim


async def compute_simulation(db: AsyncSession, sim_id: UUID) -> PlanningSimulation:
    sim_r = await db.execute(select(PlanningSimulation).where(PlanningSimulation.id == sim_id))
    sim: PlanningSimulation = sim_r.scalar_one_or_none()
    if not sim:
        raise ValueError("Simulation not found")

    ops_r = await db.execute(
        select(OperationQueue).where(OperationQueue.scenario_id == sim.scenario_id)
    )
    ops = ops_r.scalars().all()

    # snapshot current state
    original = {op.id: {
        "scheduled_start": op.scheduled_start,
        "scheduled_end": op.scheduled_end,
        "planned_qty": float(op.planned_qty),
        "total_minutes": op.total_minutes,
        "work_center_id": str(op.work_center_id) if op.work_center_id else None,
        "status": op.status.value,
    } for op in ops}

    modified = copy.deepcopy(original)

    for change in (sim.changes or []):
        op_id_str = change.get("op_id")
        field = change.get("field")
        new_val = change.get("new_value")
        if not op_id_str or not field:
            continue
        # find by partial match
        matched_id = None
        for k in modified:
            if str(k).startswith(op_id_str) or str(k) == op_id_str:
                matched_id = k
                break
        if not matched_id:
            continue

        if field == "delay_days" and isinstance(new_val, (int, float)):
            s = modified[matched_id]["scheduled_start"]
            e = modified[matched_id]["scheduled_end"]
            if s:
                modified[matched_id]["scheduled_start"] = s + timedelta(days=int(new_val))
            if e:
                modified[matched_id]["scheduled_end"] = e + timedelta(days=int(new_val))
        elif field == "planned_qty" and isinstance(new_val, (int, float)):
            modified[matched_id]["planned_qty"] = float(new_val)
        elif field == "work_center_id":
            modified[matched_id]["work_center_id"] = str(new_val)
        elif field == "total_minutes" and isinstance(new_val, (int, float)):
            modified[matched_id]["total_minutes"] = int(new_val)

    # Compute impact
    ops_rescheduled = 0
    ops_delayed = 0
    util_changes = []

    for op_id, orig in original.items():
        mod = modified[op_id]
        if mod["scheduled_start"] != orig["scheduled_start"] or mod["total_minutes"] != orig["total_minutes"]:
            ops_rescheduled += 1
        if orig.get("scheduled_end") and mod.get("scheduled_end") and mod["scheduled_end"] > orig["scheduled_end"]:
            ops_delayed += 1

    snaps_r = await db.execute(
        select(CapacityLoadSnapshot).where(CapacityLoadSnapshot.scenario_id == sim.scenario_id)
    )
    snaps = snaps_r.scalars().all()
    avg_util_before = sum(float(s.utilization_pct) for s in snaps) / len(snaps) if snaps else 0.0
    util_delta = round((avg_util_before * (ops_rescheduled / max(len(ops), 1)) * -0.5), 2)

    co_hrs_before = sum(float(s.changeover_hours) for s in snaps)
    co_delta = round(-co_hrs_before * 0.05 * (ops_rescheduled / max(len(ops), 1)), 2)

    throughput_delta = round(-ops_delayed / max(len(ops), 1) * 100, 2)

    lines = []
    if ops_rescheduled:
        lines.append(f"{ops_rescheduled} operation(s) rescheduled")
    if ops_delayed:
        lines.append(f"{ops_delayed} delayed")
    if util_delta < 0:
        lines.append(f"utilization reduced by {abs(util_delta):.1f}%")
    impact_summary = "; ".join(lines) if lines else "No significant impact detected"

    sim.ops_rescheduled = ops_rescheduled
    sim.ops_delayed = ops_delayed
    sim.utilization_delta = Decimal(str(util_delta))
    sim.changeover_delta_hrs = Decimal(str(co_delta))
    sim.throughput_delta_pct = Decimal(str(throughput_delta))
    sim.impact_summary = impact_summary
    sim.status = SimulationStatus.COMPUTED
    sim.computed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(sim)
    return sim


async def publish_simulation(db: AsyncSession, sim_id: UUID, published_by_id: UUID) -> PlanningSimulation:
    sim_r = await db.execute(select(PlanningSimulation).where(PlanningSimulation.id == sim_id))
    sim = sim_r.scalar_one_or_none()
    if not sim:
        raise ValueError("Simulation not found")
    sim.status = SimulationStatus.PUBLISHED
    sim.published_by_id = published_by_id
    sim.published_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(sim)
    return sim


async def list_simulations(db: AsyncSession, scenario_id: UUID) -> List[PlanningSimulation]:
    r = await db.execute(
        select(PlanningSimulation)
        .where(PlanningSimulation.scenario_id == scenario_id)
        .order_by(PlanningSimulation.created_at.desc())
    )
    return r.scalars().all()
