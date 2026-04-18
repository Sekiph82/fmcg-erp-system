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
