"""Deterministic, evidence-aware MPS campaign planning service."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import (
    MPSPlan, MPSLine, MPSCampaign, MPSFeasibilityStatus, MPSStatus,
)
from app.models.master import Product
from app.models.production_advanced import WorkCenter, WorkCenterStatus
from app.schemas.mps import MPSCampaignOut


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


async def run_campaign_grouping(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Compatibility entry point for the validated deterministic campaign runner."""
    return await run_campaign_grouping_validated(db, mps_id)


async def list_campaigns(db: AsyncSession, mps_id: uuid.UUID) -> List[MPSCampaign]:
    q = await db.execute(
        select(MPSCampaign)
        .where(MPSCampaign.mps_id == mps_id)
        .order_by(MPSCampaign.work_center_id, MPSCampaign.sequence_order, MPSCampaign.campaign_code)
    )
    return q.scalars().all()


async def run_campaign_grouping_validated(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Deterministic exact-SKU campaigns; no inferred family or invented setup time."""
    from collections import defaultdict
    from app.models.planning import ChangeoverMatrix
    from app.services.mps_engine import PlanningInputError, decimal
    from app.services.mps_advanced_service import _write_diagnostics

    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())).scalar_one_or_none()
    if plan is None:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Campaign grouping is allowed only for DRAFT plans")
    if plan.end_date < plan.start_date:
        raise ValueError("Campaign grouping requires a valid plan date range")
    lines = list((await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.period_start, MPSLine.priority_score.desc(), MPSLine.line_no)
    )).scalars().all())
    issues_by_line: dict[uuid.UUID, list[dict]] = defaultdict(list)
    unlocked = [line for line in lines if not line.is_locked]
    if not lines:
        await db.execute(delete(MPSCampaign).where(MPSCampaign.mps_id == mps_id))
        await db.flush()
        return {"campaigns_created": 0, "lines_grouped": 0, "ungrouped_lines": 0, "locked_lines_preserved": 0, "changeover_state": "NOT_CONFIGURED"}
    products = {p.id: p for p in (await db.execute(
        select(Product).where(Product.id.in_({line.product_id for line in lines}))
    )).scalars().all()}
    line_wc_ids = {line.work_center_id for line in lines if line.work_center_id}
    wcs = {wc.id: wc for wc in (await db.execute(
        select(WorkCenter).where(WorkCenter.id.in_(line_wc_ids))
    )).scalars().all()} if line_wc_ids else {}
    locked_campaigns = (await db.execute(
        select(MPSCampaign).where(
            MPSCampaign.mps_id == mps_id,
            MPSCampaign.lines.any(MPSLine.is_locked.is_(True)),
        ).order_by(MPSCampaign.sequence_order, MPSCampaign.id)
    )).scalars().all()
    locked_anchors: dict[uuid.UUID, list[tuple[int, uuid.UUID, date | None, date | None, str | None]]] = defaultdict(list)
    locked_anchor_problems: dict[uuid.UUID, set[str]] = defaultdict(set)
    for line in lines:
        if line.is_locked and line.campaign_id is None:
            issues_by_line[line.id].append({
                "reason_code": "LOCKED_CAMPAIGN_SEQUENCE_NOT_CONFIGURED",
                "state": "SEQUENCE_NOT_ESTABLISHED",
                "provenance": "The locked line has no campaign assignment from which a fixed sequence anchor can be established.",
                "priority": "HIGH",
            })
            if line.work_center_id:
                locked_anchor_problems[line.work_center_id].add("LOCKED_CAMPAIGN_SEQUENCE_NOT_CONFIGURED")
    for campaign in locked_campaigns:
        members = [line for line in lines if line.is_locked and line.campaign_id == campaign.id]
        member_wc_ids = {line.work_center_id for line in members if line.work_center_id}
        if campaign.work_center_id:
            member_wc_ids.add(campaign.work_center_id)
        if len(member_wc_ids) != 1:
            for line in members:
                issues_by_line[line.id].append({
                    "reason_code": "LOCKED_CAMPAIGN_WORK_CENTER_AMBIGUOUS",
                    "work_center_id": str(line.work_center_id) if line.work_center_id else None,
                    "campaign_work_center_id": str(campaign.work_center_id) if campaign.work_center_id else None,
                    "state": "SEQUENCE_NOT_ESTABLISHED",
                    "provenance": "The locked campaign and its locked members do not identify exactly one work center; unlocked placement was not guessed.",
                    "priority": "HIGH",
                })
            for ambiguous_wc_id in member_wc_ids:
                locked_anchor_problems[ambiguous_wc_id].add("LOCKED_CAMPAIGN_WORK_CENTER_AMBIGUOUS")
            continue
        work_center_id = next(iter(member_wc_ids))
        member_families = {
            str(getattr(products[line.product_id].category, "value", products[line.product_id].category) or "").strip().upper()
            for line in members if line.product_id in products
        }
        family = next(iter(member_families)) if len(member_families) == 1 else None
        campaign_start = campaign.campaign_start or (min(line.period_start for line in members) if members else None)
        campaign_end = campaign.campaign_end or (max(line.period_end for line in members) if members else None)
        if members:
            member_start = min(line.period_start for line in members)
            member_end = max(line.period_end for line in members)
            campaign_start = min(campaign_start, member_start) if campaign_start else member_start
            campaign_end = max(campaign_end, member_end) if campaign_end else member_end
        locked_anchors[work_center_id].append((
            campaign.sequence_order, campaign.id, campaign_start, campaign_end, family,
        ))
    groups: dict[tuple[uuid.UUID | None, uuid.UUID], list[MPSLine]] = defaultdict(list)
    invalid_lines: set[uuid.UUID] = set()
    ungroupable_lines: set[uuid.UUID] = set()
    for line in unlocked:
        product = products.get(line.product_id)
        if product is None or not product.is_active:
            code = "PRODUCT_MASTER_MISSING" if product is None else "PRODUCT_MASTER_INACTIVE"
            issues_by_line[line.id].append({"reason_code": code, "priority": "CRITICAL"})
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        if line.period_end < line.period_start:
            issues_by_line[line.id].append({
                "reason_code": "CAMPAIGN_PERIOD_INVALID",
                "from_date": line.period_start.isoformat(), "to_date": line.period_end.isoformat(),
                "priority": "CRITICAL",
            })
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        if line.period_start < plan.start_date or line.period_end > plan.end_date:
            issues_by_line[line.id].append({
                "reason_code": "CAMPAIGN_PERIOD_OUTSIDE_PLAN",
                "plan_start": plan.start_date.isoformat(), "plan_end": plan.end_date.isoformat(),
                "line_start": line.period_start.isoformat(), "line_end": line.period_end.isoformat(),
                "priority": "CRITICAL",
            })
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        if not line.work_center_id:
            issues_by_line[line.id].append({"reason_code": "WORK_CENTER_MISSING", "priority": "CRITICAL"})
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        work_center = wcs.get(line.work_center_id)
        if work_center is None or work_center.status != WorkCenterStatus.ACTIVE:
            code = "WORK_CENTER_MISSING" if work_center is None else "WORK_CENTER_INACTIVE"
            issues_by_line[line.id].append({"reason_code": code, "work_center_id": str(line.work_center_id), "priority": "CRITICAL"})
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        try:
            quantity = decimal(line.planned_production_qty)
        except PlanningInputError:
            quantity = Decimal("-1")
        if quantity < 0:
            issues_by_line[line.id].append({
                "reason_code": "PRODUCTION_QUANTITY_INVALID",
                "planned_qty": str(line.planned_production_qty), "priority": "CRITICAL",
            })
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
            continue
        try:
            line_priority = decimal(line.priority_score)
        except PlanningInputError:
            line_priority = Decimal("0")
            issues_by_line[line.id].append({
                "reason_code": "CAMPAIGN_PRIORITY_INVALID",
                "priority_score": str(line.priority_score), "priority": "CRITICAL",
            })
            invalid_lines.add(line.id)
            ungroupable_lines.add(line.id)
        batch_size = None
        if line.batch_size_qty is not None:
            try:
                batch_size = decimal(line.batch_size_qty)
            except PlanningInputError:
                batch_size = Decimal("0")
            if batch_size <= 0:
                issues_by_line[line.id].append({
                    "reason_code": "BATCH_SIZE_INVALID", "batch_size_qty": str(line.batch_size_qty),
                    "priority": "CRITICAL",
                })
                invalid_lines.add(line.id)
                continue
            if quantity % batch_size != 0:
                issues_by_line[line.id].append({
                    "reason_code": "BATCH_SIZE_NOT_ALIGNED",
                    "planned_qty": str(line.planned_production_qty),
                    "batch_size_qty": str(line.batch_size_qty),
                    "priority": "HIGH",
                })
                invalid_lines.add(line.id)
            if line.num_batches is not None:
                if line.num_batches <= 0:
                    issues_by_line[line.id].append({
                        "reason_code": "BATCH_COUNT_INVALID", "num_batches": line.num_batches,
                        "priority": "CRITICAL",
                    })
                    invalid_lines.add(line.id)
                    ungroupable_lines.add(line.id)
                elif quantity != batch_size * Decimal(line.num_batches):
                    issues_by_line[line.id].append({
                        "reason_code": "BATCH_COUNT_MISMATCH", "num_batches": line.num_batches,
                        "planned_qty": str(line.planned_production_qty),
                        "batch_size_qty": str(line.batch_size_qty), "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
            else:
                issues_by_line[line.id].append({
                    "reason_code": "BATCH_COUNT_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                    "num_batches": None, "priority": "LOW",
                })
        else:
            issues_by_line[line.id].append({
                "reason_code": "BATCH_SIZE_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                "batch_size_qty": None, "priority": "LOW",
            })
            if line.num_batches is not None and line.num_batches <= 0:
                issues_by_line[line.id].append({
                    "reason_code": "BATCH_COUNT_INVALID", "num_batches": line.num_batches,
                    "priority": "CRITICAL",
                })
                invalid_lines.add(line.id)
                ungroupable_lines.add(line.id)
        if line.required_hours is None:
            issues_by_line[line.id].append({
                "reason_code": "PRODUCTION_HOURS_NOT_CONFIGURED",
                "state": "NOT_CONFIGURED", "required_hours": None, "priority": "LOW",
            })
            ungroupable_lines.add(line.id)
            if line.feasibility_status == MPSFeasibilityStatus.FEASIBLE:
                line.feasibility_status = MPSFeasibilityStatus.PENDING
        else:
            try:
                required_hours = decimal(line.required_hours)
            except PlanningInputError:
                required_hours = Decimal("-1")
            if (
                required_hours < 0
                or (quantity > 0 and required_hours == 0)
                or (quantity == 0 and required_hours > 0)
            ):
                issues_by_line[line.id].append({
                    "reason_code": "PRODUCTION_HOURS_INVALID",
                    "planned_qty": str(line.planned_production_qty),
                    "required_hours": str(line.required_hours), "priority": "CRITICAL",
                })
                invalid_lines.add(line.id)
                ungroupable_lines.add(line.id)
        if line.id not in ungroupable_lines:
            groups[(line.work_center_id, line.product_id)].append(line)
    wc_ids = {wc_id for wc_id, _ in groups if wc_id}
    changeovers = (await db.execute(
        select(ChangeoverMatrix).where(
            ChangeoverMatrix.work_center_id.in_(wc_ids),
            ChangeoverMatrix.is_active.is_(True),
        )
    )).scalars().all() if wc_ids else []
    changeover_values: dict[tuple[uuid.UUID, str, str], list[int]] = defaultdict(list)
    for row in changeovers:
        key = (row.work_center_id, row.from_family.strip().upper(), row.to_family.strip().upper())
        changeover_values[key].append(row.changeover_minutes)
    changeover_map = {
        key: values[0] for key, values in changeover_values.items()
        if len(values) == 1 and values[0] >= 0 and key[1] and key[2]
    }
    invalid_changeovers = {
        key for key, values in changeover_values.items()
        if len(values) != 1 or values[0] < 0 or not key[1] or not key[2]
    }

    # Keep campaigns referenced by locked orders; remove only recalculable groups.
    await db.execute(delete(MPSCampaign).where(
        MPSCampaign.mps_id == mps_id,
        ~MPSCampaign.lines.any(MPSLine.is_locked.is_(True)),
    ))
    for line in unlocked:
        line.campaign_id = None
    await db.flush()

    sorted_groups = sorted(
        groups.items(),
        key=lambda entry: (
            entry[0][0].hex if entry[0][0] else "",
            min(line.period_start for line in entry[1]),
            -(max((decimal(line.priority_score) for line in entry[1]), default=Decimal("0"))),
            str(getattr(products[entry[0][1]], "sku", "")),
            entry[0][1].hex,
        ),
    )
    # Sequence numbers are scoped to a work center. Place unlocked groups in the
    # date window around immutable locked campaigns instead of appending every
    # group after the globally latest locked sequence.
    sequence_by_group: dict[tuple[uuid.UUID | None, uuid.UUID], int] = {}
    groups_by_wc: dict[uuid.UUID, list[tuple[tuple[uuid.UUID | None, uuid.UUID], list[MPSLine]]]] = defaultdict(list)
    for entry in sorted_groups:
        if entry[0][0] is not None:
            groups_by_wc[entry[0][0]].append(entry)
    for work_center_id, wc_groups in groups_by_wc.items():
        anchors = sorted(locked_anchors.get(work_center_id, []), key=lambda item: (item[0], item[1].hex))
        wc_groups.sort(key=lambda entry: (
            min(line.period_start for line in entry[1]),
            -(max((decimal(line.priority_score) for line in entry[1]), default=Decimal("0"))),
            str(getattr(products[entry[0][1]], "sku", "")), entry[0][1].hex,
        ))
        anchor_problem = bool(locked_anchor_problems.get(work_center_id)) or any(
            seq <= 0 or start is None or end is None or end < start
            for seq, _, start, end, _ in anchors
        ) or len({seq for seq, _, _, _, _ in anchors}) != len(anchors)
        anchor_problem = anchor_problem or any(
            left_seq >= right_seq or left_end is None or right_start is None or left_end >= right_start
            for (left_seq, _, _, left_end, _), (right_seq, _, right_start, _, _) in zip(anchors, anchors[1:])
        )
        if not anchors and not anchor_problem:
            for seq, (key, _) in enumerate(wc_groups, start=1):
                sequence_by_group[key] = seq
            continue
        if anchor_problem:
            for key, items in wc_groups:
                for line in items:
                    issues_by_line[line.id].append({
                        "reason_code": "LOCKED_CAMPAIGN_SEQUENCE_INVALID",
                        "state": "SEQUENCE_NOT_ESTABLISHED",
                        "provenance": "Locked campaign sequence or date windows are incomplete, duplicated, or inconsistent; unlocked campaign placement was not guessed.",
                        "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
                    ungroupable_lines.add(line.id)
            continue

        bins: list[tuple[tuple[date | None, str | None] | None, list[tuple[tuple[uuid.UUID | None, uuid.UUID], list[MPSLine]]]]] = [
            (None, []) for _ in range(len(anchors) + 1)
        ]
        for key, items in wc_groups:
            start = min(line.period_start for line in items)
            end = max(line.period_end for line in items)
            overlapping_anchor = next((
                anchor for anchor in anchors
                if start <= anchor[3] and anchor[2] <= end
            ), None)
            if overlapping_anchor:
                for line in items:
                    issues_by_line[line.id].append({
                        "reason_code": "CAMPAIGN_WINDOWS_OVERLAP_LOCKED",
                        "previous_campaign_end": overlapping_anchor[3].isoformat() if overlapping_anchor[3] else None,
                        "campaign_start": start.isoformat(),
                        "state": "LOCKED_WINDOW_CONFLICT",
                        "provenance": "The unlocked campaign window overlaps an immutable locked campaign window; no sequence or transition was assigned.",
                        "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
                    ungroupable_lines.add(line.id)
                continue
            bin_index = next((
                index for index, anchor in enumerate(anchors)
                if end < anchor[2]
            ), len(anchors))
            predecessor = None if bin_index == 0 else (anchors[bin_index - 1][3], anchors[bin_index - 1][4])
            bins[bin_index][1].append((key, items))

        # A locked anchor fixes its sequence. Only use integer slots that fit
        # between adjacent anchors; any overflow is left ungrouped with a reason.
        for bin_index, (_, bin_groups) in enumerate(bins):
            if not bin_groups:
                continue
            if bin_index == 0:
                high = anchors[0][0] - 1
                low = high - len(bin_groups) + 1
                if low < 1:
                    available = max(0, high)
                    overflow = bin_groups[:len(bin_groups) - available]
                    bin_groups = bin_groups[len(overflow):]
                    for key, items in overflow:
                        for line in items:
                            issues_by_line[line.id].append({
                                "reason_code": "LOCKED_CAMPAIGN_SEQUENCE_GAP_EXHAUSTED",
                                "state": "SEQUENCE_NOT_ESTABLISHED", "priority": "HIGH",
                            })
                            invalid_lines.add(line.id)
                            ungroupable_lines.add(line.id)
                first_sequence = anchors[0][0] - len(bin_groups)
            elif bin_index < len(anchors):
                previous_sequence = anchors[bin_index - 1][0]
                next_sequence = anchors[bin_index][0]
                available = next_sequence - previous_sequence - 1
                if len(bin_groups) > available:
                    overflow = bin_groups[available:]
                    bin_groups = bin_groups[:available]
                    for key, items in overflow:
                        for line in items:
                            issues_by_line[line.id].append({
                                "reason_code": "LOCKED_CAMPAIGN_SEQUENCE_GAP_EXHAUSTED",
                                "state": "SEQUENCE_NOT_ESTABLISHED", "priority": "HIGH",
                            })
                            invalid_lines.add(line.id)
                            ungroupable_lines.add(line.id)
                first_sequence = previous_sequence + 1
            else:
                first_sequence = anchors[-1][0] + 1
            for offset, (key, _) in enumerate(bin_groups):
                sequence_by_group[key] = first_sequence + offset

    # Groups blocked by an invalid lock or an exhausted sequence gap must not
    # leave a campaign shell behind.
    sorted_groups = [entry for entry in sorted_groups if entry[0] in sequence_by_group]
    created = 0
    grouped = 0
    previous_family: dict[uuid.UUID, str] = {}
    previous_campaign_end: dict[uuid.UUID, date] = {}
    previous_campaign_present: set[uuid.UUID] = set()
    previous_campaign_is_locked: dict[uuid.UUID, bool] = {}
    last_generated_campaign: dict[uuid.UUID, tuple[MPSCampaign, list[MPSLine], str]] = {}
    transition_not_configured = 0
    configured_transition_count = 0
    # Process groups by their per-work-center sequence. Inject locked anchors
    # as history reset points so earlier groups never inherit a future lock.
    execution: list[tuple[int, uuid.UUID, str, object]] = []
    for (wc_id, product_id), items in sorted_groups:
        if wc_id is not None:
            execution.append((sequence_by_group[(wc_id, product_id)], wc_id, "group", ((wc_id, product_id), items)))
    for wc_id, anchors in locked_anchors.items():
        for anchor in anchors:
            execution.append((anchor[0], wc_id, "lock", anchor))
    execution.sort(key=lambda item: (
        item[1].hex, item[0], 0 if item[2] == "lock" else 1,
        str(item[3][0][1]) if item[2] == "group" else item[3][1].hex,
    ))
    for sequence_order, wc_id, entry_type, payload in execution:
        if entry_type == "lock":
            _, locked_campaign_id, locked_start, locked_end, locked_family = payload
            if (
                wc_id in previous_campaign_present
                and wc_id in previous_campaign_end
                and locked_start is not None
                and previous_campaign_end[wc_id] < locked_start
            ):
                prior_family = previous_family.get(wc_id)
                prior_generated = last_generated_campaign.get(wc_id)
                diagnostic_lines = (
                    prior_generated[1] if prior_generated and not previous_campaign_is_locked.get(wc_id, False)
                    else [line for line in lines if line.is_locked and line.campaign_id == locked_campaign_id]
                )
                if not prior_family or not locked_family:
                    issue = {
                        "reason_code": "LOCKED_CAMPAIGN_FAMILY_NOT_CONFIGURED",
                        "state": "NOT_CONFIGURED", "duration_minutes": None,
                        "provenance": "A campaign family at the locked boundary cannot be established from its member products.",
                        "priority": "HIGH",
                    }
                    for line in diagnostic_lines:
                        issues_by_line[line.id].append(issue)
                    transition_not_configured += 1
                else:
                    transition_key = (wc_id, prior_family, locked_family)
                    matrix_minutes = changeover_map.get(transition_key)
                    if transition_key in invalid_changeovers:
                        issue = {
                            "reason_code": "CHANGEOVER_CONFIGURATION_INVALID",
                            "work_center_id": str(wc_id), "from_family": prior_family,
                            "to_family": locked_family, "state": "INVALID_CONFIGURATION",
                            "duration_minutes": None,
                            "provenance": "Matching active changeover rows are negative or ambiguous after family normalization; setup was not applied.",
                            "priority": "HIGH",
                        }
                        for line in diagnostic_lines:
                            issues_by_line[line.id].append(issue)
                        if prior_generated and not previous_campaign_is_locked.get(wc_id, False):
                            invalid_lines.update(line.id for line in diagnostic_lines)
                        transition_not_configured += 1
                    elif matrix_minutes is None:
                        issue = {
                            "reason_code": "CHANGEOVER_TO_LOCKED_CAMPAIGN_NOT_CONFIGURED",
                            "work_center_id": str(wc_id), "from_family": prior_family,
                            "to_family": locked_family, "state": "NOT_CONFIGURED",
                            "duration_minutes": None,
                            "provenance": "No matching active changeover_matrix row; no default duration was applied.",
                            "priority": "LOW",
                        }
                        for line in diagnostic_lines:
                            issues_by_line[line.id].append(issue)
                        transition_not_configured += 1
                    else:
                        issue = {
                            "reason_code": "CHANGEOVER_TO_LOCKED_CAMPAIGN_CONFIGURED",
                            "work_center_id": str(wc_id), "from_family": prior_family,
                            "to_family": locked_family, "state": "CONFIGURED",
                            "duration_minutes": int(matrix_minutes),
                            "provenance": "Duration comes from the unique active changeover_matrix row for this work center and family transition.",
                            "priority": "LOW",
                        }
                        if prior_generated and not previous_campaign_is_locked.get(wc_id, False):
                            campaign, generated_lines, _ = prior_generated
                            campaign.total_changeover_hrs = _R(
                                _D(campaign.total_changeover_hrs) + Decimal(matrix_minutes) / Decimal(60)
                            )
                        for line in diagnostic_lines:
                            issues_by_line[line.id].append(issue)
                        configured_transition_count += 1
            previous_campaign_present.add(wc_id)
            previous_campaign_is_locked[wc_id] = True
            if locked_end is not None:
                previous_campaign_end[wc_id] = locked_end
            if locked_family:
                previous_family[wc_id] = locked_family
            else:
                previous_family.pop(wc_id, None)
            continue
        (wc_id, product_id), items = payload
        product = products[product_id]
        items.sort(key=lambda line: (line.period_start, -decimal(line.priority_score), line.line_no, line.id.hex))
        family = str(getattr(product.category, "value", product.category) or "").upper()
        changeover_minutes = None
        changeover_state = "NOT_CONFIGURED"
        had_previous_campaign = bool(wc_id and wc_id in previous_campaign_present)
        had_previous_family = bool(wc_id and wc_id in previous_family)
        previous = previous_family.get(wc_id) if wc_id else None
        prior_end = previous_campaign_end.get(wc_id) if wc_id else None
        prior_is_locked = previous_campaign_is_locked.get(wc_id, False) if wc_id else False
        campaign_start = min(line.period_start for line in items)
        campaign_end = max(line.period_end for line in items)
        windows_sequenced = bool(
            had_previous_campaign and wc_id and prior_end is not None and prior_end < campaign_start
        )
        if had_previous_family and windows_sequenced:
            transition_key = (wc_id, previous_family[wc_id], family)
            matrix_minutes = changeover_map.get(transition_key)
            if transition_key in invalid_changeovers:
                changeover_state = "INVALID_CONFIGURATION"
                transition_not_configured += 1
            elif matrix_minutes is not None:
                changeover_minutes = int(matrix_minutes)
                changeover_state = "CONFIGURED"
                configured_transition_count += 1
            else:
                transition_not_configured += 1
        elif had_previous_campaign:
            transition_not_configured += 1
        changeover_hours = Decimal(changeover_minutes or 0) / Decimal(60)
        if wc_id:
            previous_family[wc_id] = family
            previous_campaign_end[wc_id] = campaign_end
            previous_campaign_present.add(wc_id)
            previous_campaign_is_locked[wc_id] = False
        production_hours = _R(sum((_D(line.required_hours) for line in items), Decimal("0")))
        first_line_id = min((line.id.hex for line in items), default="")
        stable_key = uuid.uuid5(uuid.NAMESPACE_URL, f"mps:{mps_id}:wc:{wc_id}:product:{product_id}:line:{first_line_id}").hex[:12].upper()
        campaign = MPSCampaign(
            campaign_code=f"CAMP-{mps_id.hex[:6].upper()}-{stable_key}",
            campaign_name=f"{getattr(product, 'sku', 'SKU')} production campaign",
            mps_id=mps_id,
            work_center_id=wc_id,
            campaign_start=campaign_start,
            campaign_end=campaign_end,
            total_production_hrs=production_hours,
            total_changeover_hrs=_R(changeover_hours),
            sequence_order=sequence_order,
            sku_count=1,
            notes=(f"Exact SKU grouping. Changeover state={changeover_state}; family source=product category; "
                   "CIP duration=NOT_CONFIGURED because no authoritative MPS CIP source exists."),
        )
        db.add(campaign)
        await db.flush()
        for line in items:
            line.campaign_id = campaign.id
        if wc_id:
            last_generated_campaign[wc_id] = (campaign, items, family)
        created += 1
        grouped += len(items)
        if had_previous_campaign:
            for line in items:
                if not windows_sequenced:
                    locked_conflict = prior_is_locked
                    overlap_code = (
                        "CAMPAIGN_WINDOWS_OVERLAP_LOCKED" if locked_conflict
                        else "CAMPAIGN_WINDOWS_OVERLAP"
                    )
                    unknown_anchor = prior_end is None and locked_conflict
                    issues_by_line[line.id].append({
                        "reason_code": "LOCKED_CAMPAIGN_WINDOW_NOT_CONFIGURED" if unknown_anchor else overlap_code,
                        "previous_campaign_end": prior_end.isoformat() if prior_end else None,
                        "campaign_start": campaign_start.isoformat(),
                        "state": "LOCKED_WINDOW_UNKNOWN" if unknown_anchor else "SEQUENCE_NOT_ESTABLISHED",
                        "provenance": (
                            "The locked campaign has no authoritative end date; sequence order cannot be validated."
                            if unknown_anchor else
                            "Campaign windows overlap or touch; the locked assignment was preserved and no transition setup was applied."
                            if locked_conflict else
                            "Campaign windows overlap or touch; transition setup was not applied."
                        ),
                        "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
                elif had_previous_campaign and not had_previous_family:
                    issues_by_line[line.id].append({
                        "reason_code": "LOCKED_CAMPAIGN_FAMILY_NOT_CONFIGURED",
                        "state": "NOT_CONFIGURED", "duration_minutes": None,
                        "provenance": "Locked campaign family cannot be established from its member products.",
                        "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
                elif changeover_state == "INVALID_CONFIGURATION":
                    issues_by_line[line.id].append({
                        "reason_code": "CHANGEOVER_CONFIGURATION_INVALID",
                        "work_center_id": str(wc_id),
                        "from_family": previous, "to_family": family,
                        "state": "INVALID_CONFIGURATION", "duration_minutes": None,
                        "provenance": "Matching active changeover rows are negative or ambiguous after family normalization; setup was not applied.",
                        "priority": "HIGH",
                    })
                    invalid_lines.add(line.id)
                elif changeover_state == "NOT_CONFIGURED":
                    issues_by_line[line.id].append({
                        "reason_code": "CHANGEOVER_NOT_CONFIGURED",
                        "work_center_id": str(wc_id),
                        "from_family": previous, "to_family": family,
                        "state": "NOT_CONFIGURED", "duration_minutes": None,
                        "provenance": "No matching active changeover_matrix row; no default duration was applied.",
                        "priority": "LOW",
                    })
        for line in items:
            issues_by_line[line.id].append({
                "reason_code": "CIP_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                "duration_minutes": None,
                "provenance": "No authoritative MPS CIP duration source is configured.",
                "priority": "LOW",
            })
            issues_by_line[line.id].append({
                "reason_code": "MINIMUM_RUN_NOT_CONFIGURED", "state": "NOT_CONFIGURED",
                "minimum_run_qty": None,
                "provenance": "No authoritative minimum production run quantity is configured on product or work center master data.",
                "priority": "LOW",
            })

    diagnostics = []
    for line in lines:
        issues = issues_by_line[line.id]
        if not line.is_locked and line.id in invalid_lines and line.feasibility_status in (
            MPSFeasibilityStatus.PENDING, MPSFeasibilityStatus.FEASIBLE,
        ):
            line.feasibility_status = MPSFeasibilityStatus.INFEASIBLE
        diagnostics.append((line.id, {
            "reason_codes": list(dict.fromkeys(issue["reason_code"] for issue in issues)),
            "issues": issues, "status": str(getattr(line.feasibility_status, "value", line.feasibility_status)),
            "plan_id": str(mps_id), "locked": bool(line.is_locked),
        }))
    diagnostic_run = await _write_diagnostics(db, mps_id, diagnostics)
    await db.flush()
    return {
        "campaigns_created": created,
        "lines_grouped": grouped,
        "ungrouped_lines": len(unlocked) - grouped,
        "locked_lines_preserved": len(lines) - len(unlocked),
        "sequence_policy": "per work center, chronological windows around immutable locked sequence anchors, then priority, SKU, UUID; stable across reruns",
        "changeover_state": (
            "NOT_CONFIGURED" if configured_transition_count == 0
            else "PARTIAL" if transition_not_configured else "CONFIGURED"
        ),
        "configured_transitions": configured_transition_count,
        "unconfigured_transitions": transition_not_configured,
        "diagnostic_run_id": str(diagnostic_run),
    }
