"""
MPS What-If Simulation Service

A what-if scenario proposes a set of changes (delay, batch resize, line change, etc.)
and computes the impact WITHOUT touching the live MPS plan.

Impact metrics:
- impact_service_level_pct: % lines that remain on-time after changes
- impact_delay_count: number of lines pushed beyond period_end
- impact_cost_delta: estimated change in production cost (hours × rate)
"""
from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSWhatIfScenario,
    WhatIfStatus, MPSChangeType,
)
from app.models.production_advanced import WorkCenter
from app.schemas.mps import MPSWhatIfCreate, MPSWhatIfOut


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


def _apply_change(line_snapshot: dict, change: dict) -> dict:
    """Apply one change dict to a line snapshot copy."""
    ct = change["change_type"]
    val = change["new_value"]

    if ct == MPSChangeType.DELAY:
        # val = number of days to delay
        delay_days = int(val)
        for df in ("planned_start_date", "planned_end_date", "period_start", "period_end"):
            if line_snapshot.get(df):
                d = date.fromisoformat(str(line_snapshot[df]))
                line_snapshot[df] = (d + timedelta(days=delay_days)).isoformat()

    elif ct == MPSChangeType.BATCH_SIZE:
        new_batch = Decimal(str(val))
        old_qty = _D(line_snapshot.get("planned_production_qty", 0))
        if new_batch > 0 and old_qty > 0:
            import math
            n_batches = max(1, math.ceil(float(old_qty) / float(new_batch)))
            line_snapshot["planned_production_qty"] = str(_R(new_batch * n_batches))
            line_snapshot["batch_size_qty"] = str(new_batch)
            line_snapshot["num_batches"] = n_batches

    elif ct == MPSChangeType.QTY_ADJUST:
        line_snapshot["planned_production_qty"] = str(_D(val))

    elif ct == MPSChangeType.LINE_CHANGE:
        line_snapshot["work_center_id"] = str(val)

    elif ct == MPSChangeType.SPLIT:
        line_snapshot["_split"] = True
        line_snapshot["planned_production_qty"] = str(
            _R(_D(line_snapshot.get("planned_production_qty", 0)) / 2)
        )

    return line_snapshot


def _compute_impact(
    original_lines: List[dict],
    modified_lines: Dict[str, dict],
    wcs: Dict[uuid.UUID, WorkCenter],
) -> tuple:
    """
    Returns (service_level_pct, delay_count, cost_delta).
    """
    total = len(original_lines)
    if total == 0:
        return 100.0, 0, Decimal("0")

    delay_count = 0
    cost_delta = Decimal("0")

    for orig in original_lines:
        line_id = str(orig["id"])
        modified = modified_lines.get(line_id, orig)

        orig_end = orig.get("planned_end_date") or orig.get("period_end")
        mod_end = modified.get("planned_end_date") or modified.get("period_end")
        period_end = orig.get("period_end")

        if orig_end and mod_end and period_end:
            orig_end_d = date.fromisoformat(str(orig_end))
            mod_end_d = date.fromisoformat(str(mod_end))
            period_d = date.fromisoformat(str(period_end))
            if mod_end_d > period_d:
                delay_count += 1

        # Cost delta: change in production qty × approximate rate
        orig_qty = _D(orig.get("planned_production_qty", 0))
        mod_qty = _D(modified.get("planned_production_qty", 0))
        qty_diff = mod_qty - orig_qty

        # Rate: use work center machine_cost_per_hour / throughput as proxy
        wc_id = modified.get("work_center_id")
        rate = Decimal("1000")  # KES/unit proxy
        if wc_id:
            try:
                wc = wcs.get(uuid.UUID(str(wc_id)))
                if wc and wc.machine_cost_per_hour and wc.capacity:
                    rate = _D(wc.machine_cost_per_hour) / _D(wc.capacity)
            except Exception:
                pass
        cost_delta += qty_diff * rate

    on_time = total - delay_count
    svc_level = round(on_time / total * 100, 2)
    return svc_level, delay_count, _R(cost_delta)


async def create_whatif_scenario(
    db: AsyncSession,
    mps_id: uuid.UUID,
    data: MPSWhatIfCreate,
    user_id: uuid.UUID,
) -> MPSWhatIfScenario:
    plan_q = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")

    seq_q = await db.execute(select(func.count()).select_from(MPSWhatIfScenario))
    seq = (seq_q.scalar() or 0) + 1

    # Load affected lines
    line_ids = [c.line_id for c in data.changes]
    lines_q = await db.execute(
        select(MPSLine).where(MPSLine.id.in_(line_ids))
    )
    affected_lines = {l.id: l for l in lines_q.scalars().all()}

    # Load all plan lines for service level calc
    all_lines_q = await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
    )
    all_lines = all_lines_q.scalars().all()

    # Load work centers
    wc_q = await db.execute(select(WorkCenter))
    wcs: Dict[uuid.UUID, WorkCenter] = {wc.id: wc for wc in wc_q.scalars().all()}

    # Build snapshots
    def _snap(line: MPSLine) -> dict:
        return {
            "id": str(line.id),
            "planned_production_qty": str(line.planned_production_qty),
            "planned_start_date": str(line.planned_start_date) if line.planned_start_date else None,
            "planned_end_date": str(line.planned_end_date) if line.planned_end_date else None,
            "period_start": str(line.period_start),
            "period_end": str(line.period_end),
            "work_center_id": str(line.work_center_id) if line.work_center_id else None,
            "batch_size_qty": str(line.batch_size_qty) if line.batch_size_qty else None,
            "num_batches": line.num_batches,
        }

    original_snaps = [_snap(l) for l in all_lines]
    modified_map: Dict[str, dict] = {s["id"]: deepcopy(s) for s in original_snaps}

    # Apply changes
    changes_json = []
    for change in data.changes:
        lid = str(change.line_id)
        if lid in modified_map:
            modified_map[lid] = _apply_change(modified_map[lid], {
                "change_type": change.change_type,
                "new_value": change.new_value,
            })
        changes_json.append({
            "line_id": lid,
            "change_type": change.change_type,
            "new_value": change.new_value,
        })

    # Compute impact
    svc, delays, cost_delta = _compute_impact(original_snaps, modified_map, wcs)

    summary_parts = []
    if delays > 0:
        summary_parts.append(f"{delays} line(s) will be delayed")
    if cost_delta != 0:
        direction = "increase" if cost_delta > 0 else "decrease"
        summary_parts.append(f"cost will {direction} by KES {abs(float(cost_delta)):,.0f}")
    if not summary_parts:
        summary_parts.append("No negative impact detected")
    impact_summary = "; ".join(summary_parts) + f". Projected service level: {svc:.1f}%."

    scenario = MPSWhatIfScenario(
        scenario_no=f"WI-{mps_id.hex[:6].upper()}-{seq:04d}",
        scenario_name=data.scenario_name,
        mps_id=mps_id,
        description=data.description,
        changes=changes_json,
        impact_service_level_pct=Decimal(str(svc)),
        impact_delay_count=delays,
        impact_cost_delta=cost_delta,
        impact_summary=impact_summary,
        status=WhatIfStatus.COMPUTED,
        created_by_id=user_id,
    )
    db.add(scenario)
    await db.flush()
    return scenario


async def list_whatif_scenarios(db: AsyncSession, mps_id: uuid.UUID):
    q = await db.execute(
        select(MPSWhatIfScenario)
        .where(MPSWhatIfScenario.mps_id == mps_id)
        .order_by(MPSWhatIfScenario.created_at.desc())
    )
    return q.scalars().all()


async def get_whatif_scenario(db: AsyncSession, scenario_id: uuid.UUID):
    q = await db.execute(
        select(MPSWhatIfScenario).where(MPSWhatIfScenario.id == scenario_id)
    )
    return q.scalar_one_or_none()
