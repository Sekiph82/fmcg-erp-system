"""Fixed Asset depreciation engine and business logic."""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
from dateutil.relativedelta import relativedelta

from app.models.fixed_assets import (
    FAFixedAsset, FADepreciationSchedule, FAAssetEvent, FAAssetDisposal,
    FAAssetComponent, FAAIRecommendation,
    DepreciationMethod, FAAssetStatus, ScheduleStatus,
    AssetEventType, DisposalMethod, FAIAgentType, FAIRecStatus,
    DepreciationStartRule,
)
from app.models.fixed_assets import DepreciationFrequency


# ── Helpers ────────────────────────────────────────────────────────────────────

def _month_end(d: date) -> date:
    """Return last day of the month containing d."""
    next_month = d.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


def _first_of_next_month(d: date) -> date:
    return (d.replace(day=1) + relativedelta(months=1))


def _period_months(freq: DepreciationFrequency) -> int:
    return {
        DepreciationFrequency.MONTHLY: 1,
        DepreciationFrequency.QUARTERLY: 3,
        DepreciationFrequency.YEARLY: 12,
    }[freq]


def _round4(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ── Depreciation start date ────────────────────────────────────────────────────

def compute_depreciation_start(
    asset: FAFixedAsset,
    start_rule: DepreciationStartRule,
) -> date:
    base_date = asset.in_service_date or asset.capitalization_date or date.today()
    if start_rule == DepreciationStartRule.CAPITALIZATION_DATE:
        return asset.capitalization_date or base_date
    if start_rule == DepreciationStartRule.IN_SERVICE_DATE:
        return asset.in_service_date or base_date
    # FIRST_OF_NEXT_MONTH
    return _first_of_next_month(base_date)


# ── Per-period depreciation amount ────────────────────────────────────────────

def period_depreciation_amount(
    asset: FAFixedAsset,
    current_nbv: Decimal,
    period_start: date,
    period_end: date,
    actual_units: Optional[Decimal] = None,
) -> Decimal:
    """Return scheduled depreciation for one period."""
    freq_months = _period_months(asset.depreciation_frequency)

    if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
        if not asset.useful_life_months or asset.useful_life_months <= 0:
            return Decimal("0")
        total_periods = Decimal(str(asset.useful_life_months)) / Decimal(str(freq_months))
        amount = asset.depreciable_base / total_periods

    elif asset.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
        rate = asset.declining_balance_rate or Decimal("0")
        # Annualise rate, then apply to period
        period_rate = (rate / Decimal("100")) * (Decimal(str(freq_months)) / Decimal("12"))
        amount = current_nbv * period_rate

    elif asset.depreciation_method == DepreciationMethod.UNITS_OF_PRODUCTION:
        if not asset.total_production_units or asset.total_production_units == 0:
            return Decimal("0")
        units = actual_units or Decimal("0")
        rate_per_unit = asset.depreciable_base / asset.total_production_units
        amount = rate_per_unit * units

    else:  # MANUAL
        return Decimal("0")

    # Cap at remaining depreciable base
    remaining = max(Decimal("0"), current_nbv - asset.salvage_value)
    return _round4(min(amount, remaining))


# ── Schedule generation ────────────────────────────────────────────────────────

def generate_depreciation_schedule(
    asset: FAFixedAsset,
    start_rule: DepreciationStartRule,
    through_date: date,
) -> List[FADepreciationSchedule]:
    """
    Generate PLANNED schedule lines for asset from its depreciation start date
    through `through_date`. Does not touch already-POSTED lines.
    """
    if asset.status not in (FAAssetStatus.ACTIVE, FAAssetStatus.IMPAIRED):
        return []

    dep_start = asset.depreciation_start_date
    if not dep_start:
        dep_start = compute_depreciation_start(asset, start_rule)

    dep_end = asset.depreciation_end_date
    if not dep_end and asset.useful_life_months:
        dep_end = dep_start + relativedelta(months=asset.useful_life_months)

    freq_months = _period_months(asset.depreciation_frequency)

    # Collect existing posted lines to honour
    posted = {(l.period_start, l.period_end) for l in asset.schedule_lines
              if l.schedule_status == ScheduleStatus.POSTED}

    new_lines: List[FADepreciationSchedule] = []
    current_nbv = asset.net_book_value
    period_start = dep_start

    while period_start <= through_date:
        period_end = min(
            _month_end(period_start + relativedelta(months=freq_months - 1)),
            through_date,
        )
        if dep_end and period_start > dep_end:
            break
        if (period_start, period_end) in posted:
            period_start = period_end + timedelta(days=1)
            continue

        if current_nbv <= asset.salvage_value:
            break

        amount = period_depreciation_amount(asset, current_nbv, period_start, period_end)
        closing = _round4(max(asset.salvage_value, current_nbv - amount))

        new_lines.append(FADepreciationSchedule(
            asset_id=asset.id,
            period_start=period_start,
            period_end=period_end,
            scheduled_amount=amount,
            schedule_status=ScheduleStatus.PLANNED,
            opening_nbv=current_nbv,
            closing_nbv=closing,
        ))

        current_nbv = closing
        period_start = period_end + timedelta(days=1)

    return new_lines


# ── Post a single schedule line ────────────────────────────────────────────────

def post_depreciation_line(
    line: FADepreciationSchedule,
    posting_date: date,
    actual_units: Optional[Decimal] = None,
) -> Tuple[FADepreciationSchedule, FAAssetEvent]:
    """Mark a schedule line as posted and return it with an event record."""
    asset = line.asset
    amount = line.scheduled_amount

    if asset.depreciation_method == DepreciationMethod.UNITS_OF_PRODUCTION and actual_units is not None:
        amount = period_depreciation_amount(
            asset, line.opening_nbv, line.period_start, line.period_end, actual_units
        )
        line.actual_production_units = actual_units
        line.scheduled_amount = amount
        closing = _round4(max(asset.salvage_value, line.opening_nbv - amount))
        line.closing_nbv = closing

    line.posted_amount = amount
    line.posting_date = posting_date
    line.schedule_status = ScheduleStatus.POSTED

    nbv_before = asset.net_book_value
    asset.accumulated_depreciation = _round4(asset.accumulated_depreciation + amount)
    asset.net_book_value = line.closing_nbv
    asset.last_depreciation_date = posting_date

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.DEPRECIATION,
        event_date=posting_date,
        amount=amount,
        nbv_before=nbv_before,
        nbv_after=asset.net_book_value,
        notes=f"Depreciation posted for period {line.period_start} – {line.period_end}",
    )
    return line, event


# ── Capitalization ─────────────────────────────────────────────────────────────

def capitalize_asset(
    asset: FAFixedAsset,
    capitalization_date: date,
    in_service_date: Optional[date],
    depreciation_start_date: Optional[date],
    start_rule: DepreciationStartRule,
    user_id,
) -> FAAssetEvent:
    asset.status = FAAssetStatus.ACTIVE
    asset.capitalization_date = capitalization_date
    if in_service_date:
        asset.in_service_date = in_service_date
    if depreciation_start_date:
        asset.depreciation_start_date = depreciation_start_date
    else:
        asset.depreciation_start_date = compute_depreciation_start(asset, start_rule)

    if asset.useful_life_months:
        asset.depreciation_end_date = asset.depreciation_start_date + relativedelta(months=asset.useful_life_months)

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.CAPITALIZATION,
        event_date=capitalization_date,
        amount=asset.local_currency_cost,
        nbv_before=asset.net_book_value,
        nbv_after=asset.net_book_value,
        user_id=user_id,
        notes=f"Asset capitalized on {capitalization_date}",
    )
    return event


# ── Transfer ───────────────────────────────────────────────────────────────────

def transfer_asset(asset: FAFixedAsset, req, user_id) -> FAAssetEvent:
    old_loc = f"{asset.location} / {asset.cost_center}"
    if req.new_location is not None:
        asset.location = req.new_location
    if req.new_plant is not None:
        asset.plant = req.new_plant
    if req.new_department is not None:
        asset.department = req.new_department
    if req.new_cost_center is not None:
        asset.cost_center = req.new_cost_center
    if req.new_custodian_employee_id is not None:
        asset.custodian_employee_id = req.new_custodian_employee_id

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.TRANSFER,
        event_date=req.effective_date,
        nbv_before=asset.net_book_value,
        nbv_after=asset.net_book_value,
        user_id=user_id,
        reason=req.reason,
        notes=f"Transferred from {old_loc} to {req.new_location}/{req.new_cost_center}",
    )
    return event


# ── Revaluation ────────────────────────────────────────────────────────────────

def revalue_asset(asset: FAFixedAsset, req, user_id) -> FAAssetEvent:
    old_nbv = asset.net_book_value
    adjustment = req.new_carrying_value - old_nbv
    asset.net_book_value = _round4(req.new_carrying_value)
    # Recalculate depreciable base from new NBV
    asset.depreciable_base = _round4(req.new_carrying_value - asset.salvage_value)

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.REVALUATION,
        event_date=req.revaluation_date,
        amount=adjustment,
        nbv_before=old_nbv,
        nbv_after=asset.net_book_value,
        user_id=user_id,
        reason=req.reason,
        notes=f"Revaluation: NBV {old_nbv} → {asset.net_book_value} (treatment: {req.treatment})",
    )
    return event


# ── Impairment ─────────────────────────────────────────────────────────────────

def impair_asset(asset: FAFixedAsset, req, user_id) -> FAAssetEvent:
    old_nbv = asset.net_book_value
    new_nbv = _round4(max(Decimal("0"), old_nbv - req.impairment_amount))
    asset.net_book_value = new_nbv
    asset.accumulated_depreciation = _round4(asset.local_currency_cost - new_nbv)
    asset.status = FAAssetStatus.IMPAIRED

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.IMPAIRMENT,
        event_date=req.impairment_date,
        amount=req.impairment_amount,
        nbv_before=old_nbv,
        nbv_after=new_nbv,
        user_id=user_id,
        reason=req.reason,
        notes=req.notes,
    )
    return event


# ── Disposal ───────────────────────────────────────────────────────────────────

def dispose_asset(asset: FAFixedAsset, req, user_id) -> Tuple[FAAssetDisposal, FAAssetEvent]:
    gain_loss = _round4(req.sale_proceeds - asset.net_book_value)

    disposal = FAAssetDisposal(
        asset_id=asset.id,
        disposal_method=req.disposal_method,
        disposal_date=req.disposal_date,
        sale_proceeds=req.sale_proceeds,
        nbv_at_disposal=asset.net_book_value,
        cost_at_disposal=asset.local_currency_cost,
        accum_depr_at_disposal=asset.accumulated_depreciation,
        gain_loss=gain_loss,
        buyer_name=req.buyer_name,
        reason=req.reason,
        approved_by_id=user_id,
        notes=req.notes,
    )

    event = FAAssetEvent(
        asset_id=asset.id,
        event_type=AssetEventType.DISPOSAL,
        event_date=req.disposal_date,
        amount=req.sale_proceeds,
        nbv_before=asset.net_book_value,
        nbv_after=Decimal("0"),
        user_id=user_id,
        reason=req.reason,
        notes=f"Disposal ({req.disposal_method.value}), gain/loss: {gain_loss}",
    )

    asset.status = FAAssetStatus.DISPOSED
    asset.net_book_value = Decimal("0")

    return disposal, event


# ── AI recommendations ─────────────────────────────────────────────────────────

def run_ai_agents(assets: List[FAFixedAsset]) -> List[FAAIRecommendation]:
    recs: List[FAAIRecommendation] = []
    for asset in assets:
        # Agent 1: Risk Monitor
        if asset.net_book_value > 0 and asset.accumulated_depreciation > 0:
            depr_pct = asset.accumulated_depreciation / asset.local_currency_cost * 100
            if depr_pct > Decimal("90"):
                recs.append(FAAIRecommendation(
                    asset_id=asset.id,
                    agent_type=FAIAgentType.RISK_MONITOR,
                    status=FAIRecStatus.PENDING,
                    title=f"Asset {asset.asset_code} nearly fully depreciated",
                    detail=f"Accumulated depreciation is {depr_pct:.1f}% of cost. Consider replacement planning.",
                    severity="warning",
                ))

        # Agent 2: Depreciation Review
        if asset.useful_life_months and asset.useful_life_months < 12:
            recs.append(FAAIRecommendation(
                asset_id=asset.id,
                agent_type=FAIAgentType.DEPRECIATION_REVIEW,
                status=FAIRecStatus.PENDING,
                title=f"Short useful life on {asset.asset_code}",
                detail=f"Useful life set to {asset.useful_life_months} months. Verify this is intentional.",
                severity="info",
            ))

        # Agent 3: Capitalization Checker
        if asset.status == FAAssetStatus.ACTIVE and not asset.cost_center:
            recs.append(FAAIRecommendation(
                asset_id=asset.id,
                agent_type=FAIAgentType.CAPITALIZATION_CHECKER,
                status=FAIRecStatus.PENDING,
                title=f"Asset {asset.asset_code} missing cost center",
                detail="Active asset has no cost center assigned. Depreciation allocation will be incomplete.",
                severity="warning",
            ))

    return recs
