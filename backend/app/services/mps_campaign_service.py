"""
MPS Campaign Planning Service

Groups MPS lines into production campaigns to minimize changeovers.
FMCG logic: same base product → campaign, sequenced light→dark or by code.

Algorithm:
1. Load all lines for the plan
2. Group by product code prefix (first 6 chars) or exact product_id
3. Within group, sort by priority_score desc, then period_start
4. Create MPSCampaign per group, assign lines, set sequence_order
5. Estimate changeover hours (setup_time_min from work center)
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mps import MPSPlan, MPSLine, MPSCampaign, MPSStatus
from app.models.master import Product
from app.models.production_advanced import WorkCenter
from app.schemas.mps import MPSCampaignOut


def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    return v.quantize(Decimal(10) ** -dp, rounding=ROUND_HALF_UP)


# ── Campaign Key ──────────────────────────────────────────────────────────────

def _campaign_key(product: Product) -> str:
    """
    Derive campaign group key from product.
    Uses first 6 chars of product code — products sharing a prefix
    likely share a base formula and can be run in one campaign.
    Falls back to full product_id if no code.
    """
    code = (
        getattr(product, "code", None)
        or getattr(product, "sku", None)
        or getattr(product, "product_code", None)
        or str(product.id)
    )
    return code[:6].upper() if code and len(code) >= 6 else str(product.id)


# ── Main Campaign Runner ───────────────────────────────────────────────────────

async def run_campaign_grouping(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    plan_q = await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id))
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise ValueError("MPS plan not found")

    # Load lines with product info
    lines_q = await db.execute(
        select(MPSLine)
        .where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.period_start, MPSLine.priority_score.desc())
    )
    lines = list(lines_q.scalars().all())

    if not lines:
        return {"campaigns_created": 0, "lines_grouped": 0}

    # Load products
    product_ids = list({l.product_id for l in lines})
    prod_q = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products: Dict[uuid.UUID, Product] = {p.id: p for p in prod_q.scalars().all()}

    # Load work centers
    wc_q = await db.execute(select(WorkCenter))
    wcs: Dict[uuid.UUID, WorkCenter] = {wc.id: wc for wc in wc_q.scalars().all()}

    # Delete existing non-plan-locked campaigns
    await db.execute(delete(MPSCampaign).where(MPSCampaign.mps_id == mps_id))
    # Detach lines from campaigns
    for line in lines:
        line.campaign_id = None
    await db.flush()

    # Group lines by campaign key
    groups: Dict[str, List[MPSLine]] = {}
    for line in lines:
        product = products.get(line.product_id)
        if not product:
            continue
        key = _campaign_key(product)
        groups.setdefault(key, []).append(line)

    # Sort groups by earliest period_start
    def group_start(items: List[MPSLine]) -> date:
        return min(l.period_start for l in items)

    sorted_groups = sorted(groups.items(), key=lambda kv: group_start(kv[1]))

    # Count existing campaigns for seq numbering
    camp_seq_q = await db.execute(select(func.count()).select_from(MPSCampaign))
    camp_seq = (camp_seq_q.scalar() or 0) + 1

    created_campaigns = 0
    grouped_lines = 0

    for seq_order, (key, group_lines) in enumerate(sorted_groups, start=1):
        # Sort within campaign: lighter products first (by code alphabetically)
        group_lines.sort(key=lambda l: (
            l.period_start,
            -float(l.priority_score),
            getattr(products.get(l.product_id), "code", "") or "",
        ))

        # Derive campaign work center from majority of lines
        wc_votes: Dict[uuid.UUID, int] = {}
        for l in group_lines:
            if l.work_center_id:
                wc_votes[l.work_center_id] = wc_votes.get(l.work_center_id, 0) + 1
        campaign_wc_id = max(wc_votes, key=wc_votes.get) if wc_votes else None

        # Compute changeover — assume 1h per SKU transition except first
        wc = wcs.get(campaign_wc_id) if campaign_wc_id else None
        changeover_mins = wc.setup_time_min or 60 if wc else 60
        num_transitions = max(0, len(group_lines) - 1)
        total_changeover_hrs = _R(
            Decimal(str(num_transitions)) * Decimal(str(changeover_mins)) / Decimal("60")
        )

        # Total production hours
        total_prod_hrs = _R(sum(
            (_D(l.required_hours) for l in group_lines),
            Decimal("0")
        ))

        # Campaign dates
        c_start = min(l.period_start for l in group_lines)
        c_end = max(l.period_end for l in group_lines)

        # Derive campaign name from product group
        sample_product = products.get(group_lines[0].product_id)
        base_name = getattr(sample_product, "name", key) or key
        camp_name = f"Campaign {key}: {base_name[:40]}"

        campaign = MPSCampaign(
            campaign_code=f"CAMP-{mps_id.hex[:6].upper()}-{camp_seq:04d}",
            campaign_name=camp_name,
            mps_id=mps_id,
            work_center_id=campaign_wc_id,
            campaign_start=c_start,
            campaign_end=c_end,
            total_production_hrs=total_prod_hrs,
            total_changeover_hrs=total_changeover_hrs,
            sequence_order=seq_order,
            sku_count=len(group_lines),
        )
        db.add(campaign)
        await db.flush()

        for line in group_lines:
            line.campaign_id = campaign.id

        camp_seq += 1
        created_campaigns += 1
        grouped_lines += len(group_lines)

    await db.flush()
    return {
        "campaigns_created": created_campaigns,
        "lines_grouped": grouped_lines,
        "ungrouped_lines": len(lines) - grouped_lines,
    }


async def list_campaigns(db: AsyncSession, mps_id: uuid.UUID) -> List[MPSCampaign]:
    q = await db.execute(
        select(MPSCampaign)
        .where(MPSCampaign.mps_id == mps_id)
        .order_by(MPSCampaign.sequence_order)
    )
    return q.scalars().all()


async def run_campaign_grouping_validated(db: AsyncSession, mps_id: uuid.UUID) -> dict:
    """Deterministic exact-SKU campaigns; no inferred family or invented setup time."""
    from collections import defaultdict
    from app.models.planning import ChangeoverMatrix
    from app.services.mps_engine import decimal
    from app.services.mps_advanced_service import _write_diagnostics

    plan = (await db.execute(select(MPSPlan).where(MPSPlan.id == mps_id).with_for_update())).scalar_one_or_none()
    if plan is None:
        raise ValueError("MPS plan not found")
    if plan.status != MPSStatus.DRAFT:
        raise ValueError("Campaign grouping is allowed only for DRAFT plans")
    lines = list((await db.execute(
        select(MPSLine).where(MPSLine.mps_id == mps_id)
        .order_by(MPSLine.period_start, MPSLine.priority_score.desc(), MPSLine.line_no)
    )).scalars().all())
    unlocked = [line for line in lines if not line.is_locked]
    if not unlocked:
        return {"campaigns_created": 0, "lines_grouped": 0, "locked_lines_preserved": len(lines), "changeover_state": "NOT_CONFIGURED"}

    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_({l.product_id for l in unlocked})))).scalars().all()}
    wcs = {wc.id: wc for wc in (await db.execute(select(WorkCenter).where(WorkCenter.id.in_({l.work_center_id for l in unlocked if l.work_center_id})))) .scalars().all()} if any(l.work_center_id for l in unlocked) else {}
    groups: dict[tuple[uuid.UUID | None, uuid.UUID], list[MPSLine]] = defaultdict(list)
    issues_by_line: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for line in unlocked:
        if line.product_id not in products:
            issues_by_line[line.id].append({"reason_code": "PRODUCT_MASTER_MISSING", "priority": "CRITICAL"})
            continue
        groups[(line.work_center_id, line.product_id)].append(line)
    wc_ids = {wc_id for wc_id, _ in groups if wc_id}
    changeovers = (await db.execute(
        select(ChangeoverMatrix).where(
            ChangeoverMatrix.work_center_id.in_(wc_ids),
            ChangeoverMatrix.is_active.is_(True),
        )
    )).scalars().all() if wc_ids else []
    changeover_map = {
        (row.work_center_id, row.from_family.upper(), row.to_family.upper()): row.changeover_minutes
        for row in changeovers
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
            -(max((float(line.priority_score or 0) for line in entry[1]), default=0)),
            str(getattr(products[entry[0][1]], "sku", "")),
            entry[0][1].hex,
        ),
    )
    locked_sequence = (await db.execute(
        select(func.max(MPSCampaign.sequence_order)).where(
            MPSCampaign.mps_id == mps_id,
            MPSCampaign.lines.any(MPSLine.is_locked.is_(True)),
        )
    )).scalar() or 0
    created = 0
    grouped = 0
    previous_family: dict[uuid.UUID, str] = {}
    transition_not_configured = 0
    for offset, ((wc_id, product_id), items) in enumerate(sorted_groups, start=1):
        product = products[product_id]
        items.sort(key=lambda line: (line.period_start, -float(line.priority_score or 0), line.line_no, line.id.hex))
        for line in items:
            if line.batch_size_qty and decimal(line.batch_size_qty) > 0:
                quotient = decimal(line.planned_production_qty) / decimal(line.batch_size_qty)
                if quotient != quotient.to_integral_value():
                    issues_by_line[line.id].append({
                        "reason_code": "BATCH_SIZE_NOT_ALIGNED",
                        "planned_qty": str(line.planned_production_qty),
                        "batch_size_qty": str(line.batch_size_qty),
                        "priority": "MEDIUM",
                    })
        wc = wcs.get(wc_id)
        family = str(getattr(product.category, "value", product.category) or "").upper()
        changeover_minutes = None
        changeover_state = "NOT_CONFIGURED"
        had_previous_family = bool(wc_id and wc_id in previous_family)
        previous = previous_family.get(wc_id) if wc_id else None
        if had_previous_family:
            matrix_minutes = changeover_map.get((wc_id, previous_family[wc_id], family))
            if matrix_minutes is not None:
                changeover_minutes = int(matrix_minutes)
                changeover_state = "CONFIGURED"
            else:
                transition_not_configured += 1
        changeover_hours = Decimal(changeover_minutes or 0) / Decimal(60)
        if wc_id:
            previous_family[wc_id] = family
        production_hours = _R(sum((_D(line.required_hours) for line in items), Decimal("0")))
        first_line_id = min((line.id.hex for line in items), default="")
        stable_key = uuid.uuid5(uuid.NAMESPACE_URL, f"mps:{mps_id}:wc:{wc_id}:product:{product_id}:line:{first_line_id}").hex[:12].upper()
        campaign = MPSCampaign(
            campaign_code=f"CAMP-{mps_id.hex[:6].upper()}-{stable_key}",
            campaign_name=f"{getattr(product, 'sku', 'SKU')} production campaign",
            mps_id=mps_id,
            work_center_id=wc_id,
            campaign_start=min(line.period_start for line in items),
            campaign_end=max(line.period_end for line in items),
            total_production_hrs=production_hours,
            total_changeover_hrs=_R(changeover_hours),
            sequence_order=locked_sequence + offset,
            sku_count=1,
            notes=(f"Exact SKU grouping. Changeover state={changeover_state}; family source=product category; "
                   "CIP duration=NOT_CONFIGURED because no authoritative MPS CIP source exists."),
        )
        db.add(campaign)
        await db.flush()
        for line in items:
            line.campaign_id = campaign.id
        created += 1
        grouped += len(items)
        if had_previous_family and changeover_state == "NOT_CONFIGURED":
            for line in items:
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
        "sequence_policy": "work center, period, priority, SKU, UUID; stable across reruns",
        "changeover_state": "PARTIAL" if changeovers else "NOT_CONFIGURED",
        "unconfigured_transitions": transition_not_configured,
        "diagnostic_run_id": str(diagnostic_run),
    }
