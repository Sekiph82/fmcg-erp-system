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
import json
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from sqlalchemy import select, func, text
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


# Change types not yet executed by the simulator. Presenting these as
# computed would be dishonest — see M20.S01.T001 F7 — so they are rejected
# rather than silently no-op'd. Full support belongs to M20.S04/M32.
_UNSUPPORTED_CHANGE_TYPES = {MPSChangeType.MERGE, MPSChangeType.SHIFT_ADD}


def _apply_change(line_snapshot: dict, change: dict) -> dict:
    """Apply one change dict to a line snapshot copy."""
    ct = change["change_type"]
    val = change["new_value"]

    if ct in _UNSUPPORTED_CHANGE_TYPES:
        raise ValueError(f"What-if change type {ct} is not yet simulated (planned for M20.S04)")

    if ct == MPSChangeType.DELAY:
        # val = number of days to delay
        delay_value = Decimal(str(val))
        if not delay_value.is_finite() or delay_value < 0 or delay_value != delay_value.to_integral_value():
            raise ValueError("DELAY must be a non-negative whole number of days")
        delay_days = int(delay_value)
        for df in ("planned_start_date", "planned_end_date", "period_start", "period_end"):
            if line_snapshot.get(df):
                d = date.fromisoformat(str(line_snapshot[df]))
                line_snapshot[df] = (d + timedelta(days=delay_days)).isoformat()

    elif ct == MPSChangeType.BATCH_SIZE:
        new_batch = Decimal(str(val))
        if not new_batch.is_finite() or new_batch <= 0:
            raise ValueError("BATCH_SIZE must be a positive finite quantity")
        old_qty = _D(line_snapshot.get("planned_production_qty", 0))
        if new_batch > 0 and old_qty > 0:
            import math
            n_batches = max(1, math.ceil(float(old_qty) / float(new_batch)))
            line_snapshot["planned_production_qty"] = str(_R(new_batch * n_batches))
            line_snapshot["batch_size_qty"] = str(new_batch)
            line_snapshot["num_batches"] = n_batches

    elif ct == MPSChangeType.QTY_ADJUST:
        new_qty = Decimal(str(val))
        if not new_qty.is_finite() or new_qty <= 0:
            raise ValueError("QTY_ADJUST must be a positive finite quantity")
        line_snapshot["planned_production_qty"] = str(new_qty)

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
    Returns service level and delay count. Monetary impact is unknown unless a
    currency and validated cost basis are available; neither is stored here.
    """
    total = len(original_lines)
    if total == 0:
        return 100.0, 0, None

    delay_count = 0

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


    on_time = total - delay_count
    svc_level = round(on_time / total * 100, 2)
    return svc_level, delay_count, None


async def create_whatif_scenario(
    db: AsyncSession,
    mps_id: uuid.UUID,
    data: MPSWhatIfCreate,
    user_id: uuid.UUID,
) -> MPSWhatIfScenario:
    if not data.changes:
        raise ValueError("What-if scenario must include at least one proposed change")
    plan_q = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")

    seq_q = await db.execute(select(func.count()).select_from(MPSWhatIfScenario))
    seq = (seq_q.scalar() or 0) + 1

    # Load affected lines
    line_ids = [c.line_id for c in data.changes]
    lines_q = await db.execute(
        select(MPSLine).where(
            MPSLine.id.in_(line_ids),
            MPSLine.mps_id == mps_id,
        )
    )
    affected_lines = {l.id: l for l in lines_q.scalars().all()}
    if len(affected_lines) != len(set(line_ids)):
        raise ValueError("All what-if changes must target lines in this MPS plan")

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
        line = affected_lines[change.line_id]
        if line.is_locked:
            raise ValueError("What-if changes cannot target a locked MPS line")
        if change.change_type == MPSChangeType.LINE_CHANGE:
            try:
                target_wc_id = uuid.UUID(str(change.new_value))
            except (TypeError, ValueError) as exc:
                raise ValueError("LINE_CHANGE requires a valid work center id") from exc
            target_wc = wcs.get(target_wc_id)
            if target_wc is None or str(getattr(target_wc.status, "value", target_wc.status)).lower() != "active":
                raise ValueError("LINE_CHANGE requires an active work center")
        if change.change_type == MPSChangeType.DELAY:
            try:
                delay = Decimal(str(change.new_value))
            except Exception as exc:
                raise ValueError("DELAY must be a non-negative whole number of days") from exc
            if not delay.is_finite() or delay < 0 or delay != delay.to_integral_value():
                raise ValueError("DELAY must be a non-negative whole number of days")
        if change.change_type in (MPSChangeType.BATCH_SIZE, MPSChangeType.QTY_ADJUST) and (not _D(change.new_value).is_finite() or _D(change.new_value) <= 0):
            raise ValueError(f"{change.change_type.value} quantity must be positive")
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
    summary_parts.append("cost impact unknown: no approved currency and cost basis are configured")
    if delays == 0:
        summary_parts.append("no modeled schedule delay detected")
    if any(c.change_type == MPSChangeType.SPLIT for c in data.changes):
        summary_parts.append(
            "SPLIT is approximated as a single-line quantity halving; a full two-line "
            "finite-capacity re-simulation is not performed (planned for M20.S04)"
        )
    impact_summary = "; ".join(summary_parts) + f". Projected service level: {svc:.1f}% (estimated)."

    scenario = MPSWhatIfScenario(
        scenario_no=f"WI-{mps_id.hex[:6].upper()}-{seq:04d}",
        scenario_name=data.scenario_name,
        mps_id=mps_id,
        description=data.description,
        changes=changes_json,
        impact_service_level_pct=Decimal(str(svc)),
        impact_delay_count=delays,
        impact_cost_delta=None,
        impact_summary=impact_summary,
        status=WhatIfStatus.COMPUTED,
        created_by_id=user_id,
    )
    db.add(scenario)
    await db.flush()
    snapshot_assumptions = {
        "engine": "mps-whatif.v1",
        "plan_id": str(mps_id),
        "changes": changes_json,
        "line_count": len(original_snaps),
        "cost_basis": None,
    }
    snapshot_results = {
        "service_level_pct": svc,
        "delay_count": delays,
        "cost_delta": None,
        "cost_delta_status": "UNKNOWN_NO_APPROVED_CURRENCY_BASIS",
        "material_shortage_count": None,
        "capacity_overload_hours": None,
        "capacity_unit": "hours",
        "changeover_hours": None,
        "unknowns": ["material and capacity were not resimulated", "changeover basis is not configured", "cost currency/basis is not configured"],
        "modified_lines": list(modified_map.values()),
    }
    await db.execute(text("""
        INSERT INTO mps_scenario_snapshots
          (id, scenario_id, snapshot_version, assumptions, results, created_by_id)
        VALUES (:id, :scenario_id, :version, CAST(:assumptions AS jsonb), CAST(:results AS jsonb), :user_id)
    """), {
        "id": uuid.uuid4(), "scenario_id": scenario.id, "version": "mps-whatif.v1",
        "assumptions": json.dumps(snapshot_assumptions), "results": json.dumps(snapshot_results),
        "user_id": user_id,
    })
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


async def compare_whatif_scenarios(
    db: AsyncSession, mps_id: uuid.UUID, baseline_id: uuid.UUID, candidate_id: uuid.UUID,
) -> dict:
    """Compare immutable saved scenario snapshots without rerunning either case."""
    rows = (await db.execute(text("""
        SELECT scenario_id, snapshot_version, assumptions, results, created_at
        FROM mps_scenario_snapshots
        WHERE scenario_id IN (:baseline_id, :candidate_id)
        ORDER BY created_at DESC
    """), {"baseline_id": baseline_id, "candidate_id": candidate_id})).mappings().all()
    snapshots = {}
    for row in rows:
        snapshots.setdefault(row["scenario_id"], row)
    if baseline_id not in snapshots or candidate_id not in snapshots:
        raise ValueError("Both scenarios must have persisted snapshots")
    baseline, candidate = snapshots[baseline_id], snapshots[candidate_id]
    if baseline["assumptions"].get("plan_id") != str(mps_id) or candidate["assumptions"].get("plan_id") != str(mps_id):
        raise ValueError("Both scenarios must belong to the requested MPS plan")
    bres, cres = baseline["results"], candidate["results"]
    return {
        "mps_id": str(mps_id),
        "baseline_scenario_id": str(baseline_id),
        "candidate_scenario_id": str(candidate_id),
        "service_level_pct_delta": round(float(cres["service_level_pct"]) - float(bres["service_level_pct"]), 2),
        "delay_count_delta": int(cres["delay_count"]) - int(bres["delay_count"]),
        "cost_delta": None,
        "cost_delta_status": "UNKNOWN_NO_APPROVED_CURRENCY_BASIS",
        "material_shortage_count_delta": None,
        "capacity_overload_hours_delta": None,
        "capacity_unit": "hours",
        "changeover_hours_delta": None,
        "unknowns": ["material and capacity were not resimulated", "changeover basis is not configured", "cost currency/basis is not configured"],
        "baseline_version": baseline["snapshot_version"],
        "candidate_version": candidate["snapshot_version"],
    }
