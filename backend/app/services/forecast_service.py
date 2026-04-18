"""
Demand Forecasting Service
──────────────────────────
Supports: Moving Average, Weighted MA, Exponential Smoothing, Seasonal Index.
Prophet-style AI forecasting is stubbed for future integration.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mrp import (
    DemandForecast, DemandForecastLine,
    ForecastModelType, ForecastStatus, PeriodType,
)
from app.models.sales import SalesOrder, SOLine, SOStatus
from app.models.master import Product


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _R(v: Decimal, dp: int = 3) -> Decimal:
    if v is None:
        return Decimal("0")
    q = Decimal("0." + "0" * dp)
    return v.quantize(q, rounding=ROUND_HALF_UP)


def _period_start(d: date, period_type: PeriodType) -> date:
    if period_type == PeriodType.DAILY:
        return d
    if period_type == PeriodType.WEEKLY:
        return d - timedelta(days=d.weekday())   # Monday
    # MONTHLY
    return d.replace(day=1)


def _next_period(d: date, period_type: PeriodType) -> date:
    if period_type == PeriodType.DAILY:
        return d + timedelta(days=1)
    if period_type == PeriodType.WEEKLY:
        return d + timedelta(weeks=1)
    # MONTHLY — advance by ~30 days then snap to month start
    next_m = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_m


# ── Sales history query ───────────────────────────────────────────────────────

async def _get_sales_history(
    db: AsyncSession,
    product_id: UUID,
    from_date: date,
    to_date: date,
    period_type: PeriodType,
    warehouse_id: Optional[UUID] = None,
) -> list[tuple[date, Decimal]]:
    """Return list of (period_start, total_qty) from confirmed sales orders."""
    period_expr = {
        PeriodType.DAILY:   func.date(SalesOrder.order_date),
        PeriodType.WEEKLY:  func.date_trunc("week", SalesOrder.order_date),
        PeriodType.MONTHLY: func.date_trunc("month", SalesOrder.order_date),
    }[period_type]

    q = (
        select(
            period_expr.label("period"),
            func.sum(SOLine.ordered_quantity).label("qty"),
        )
        .join(SalesOrder, SOLine.so_id == SalesOrder.id)
        .where(
            SOLine.product_id == product_id,
            SalesOrder.order_date >= from_date,
            SalesOrder.order_date <= to_date,
            SalesOrder.status.notin_([SOStatus.DRAFT, SOStatus.CANCELLED]),
        )
        .group_by(period_expr)
        .order_by(period_expr)
    )
    if warehouse_id:
        q = q.where(SalesOrder.warehouse_id == warehouse_id)

    rows = (await db.execute(q)).all()
    return [(r.period if isinstance(r.period, date) else r.period.date(), _D(r.qty))
            for r in rows]


# ── Forecasting algorithms ─────────────────────────────────────────────────────

def _moving_average(history: list[Decimal], n: int) -> Decimal:
    window = history[-n:] if len(history) >= n else history
    if not window:
        return Decimal("0")
    return _R(sum(window) / Decimal(str(len(window))))


def _weighted_moving_average(history: list[Decimal], n: int) -> Decimal:
    window = history[-n:] if len(history) >= n else history
    if not window:
        return Decimal("0")
    m = len(window)
    weights = [Decimal(str(i + 1)) for i in range(m)]
    total_weight = sum(weights)
    weighted_sum = sum(w * v for w, v in zip(weights, window))
    return _R(weighted_sum / total_weight)


def _exponential_smoothing(history: list[Decimal], alpha: float = 0.3) -> list[Decimal]:
    """Return full smoothed series (same length as history)."""
    if not history:
        return []
    a = Decimal(str(alpha))
    smoothed = [history[0]]
    for v in history[1:]:
        s = a * v + (Decimal("1") - a) * smoothed[-1]
        smoothed.append(_R(s))
    return smoothed


def _seasonal_indices(history: list[tuple[date, Decimal]], period_type: PeriodType) -> dict[int, Decimal]:
    """
    Calculate seasonal multipliers.
    Returns a dict mapping period key (month 1-12 or weekday 0-6) → index.
    Index > 1 means above-average, < 1 means below-average.
    """
    if period_type == PeriodType.MONTHLY:
        key_fn = lambda d: d.month
        n_keys = 12
    elif period_type == PeriodType.WEEKLY:
        key_fn = lambda d: d.isocalendar()[1] % 52  # ISO week 1-52
        n_keys = 52
    else:
        return {}   # no seasonality for daily

    buckets: dict[int, list[Decimal]] = {k: [] for k in range(1, n_keys + 1)}
    for d, qty in history:
        k = key_fn(d)
        if 1 <= k <= n_keys:
            buckets[k].append(qty)

    all_vals = [q for vals in buckets.values() for q in vals if q > 0]
    if not all_vals:
        return {}
    grand_avg = sum(all_vals) / Decimal(str(len(all_vals)))
    if grand_avg == 0:
        return {}

    indices: dict[int, Decimal] = {}
    for k, vals in buckets.items():
        if vals:
            period_avg = sum(vals) / Decimal(str(len(vals)))
            indices[k] = _R(period_avg / grand_avg)
        else:
            indices[k] = Decimal("1")
    return indices


def _detect_spike(value: Decimal, mean: Decimal, std_dev: float, z_threshold: float = 2.5) -> bool:
    if std_dev == 0 or mean == 0:
        return False
    z = abs(float(value - mean)) / std_dev
    return z > z_threshold


# ── Main forecast generation ───────────────────────────────────────────────────

async def generate_forecast(
    db: AsyncSession,
    *,
    product_id: UUID,
    warehouse_id: Optional[UUID] = None,
    forecast_model: str = "EXPONENTIAL_SMOOTHING",
    period_type: str = "MONTHLY",
    periods_ahead: int = 6,
    history_periods: int = 12,
    model_params: Optional[dict] = None,
    created_by: Optional[UUID] = None,
) -> DemandForecast:
    pt = PeriodType(period_type)
    fm = ForecastModelType(forecast_model)
    params = model_params or {}

    today = date.today()

    # History window
    if pt == PeriodType.MONTHLY:
        history_from = (today.replace(day=1) - timedelta(days=history_periods * 30)).replace(day=1)
    elif pt == PeriodType.WEEKLY:
        history_from = today - timedelta(weeks=history_periods)
    else:
        history_from = today - timedelta(days=history_periods)

    history = await _get_sales_history(db, product_id, history_from, today, pt, warehouse_id)
    history_values = [qty for _, qty in history]

    # Compute base forecast per period
    alpha = float(params.get("alpha", 0.3))
    n_ma = int(params.get("n", 3))

    if fm == ForecastModelType.EXPONENTIAL_SMOOTHING:
        smoothed = _exponential_smoothing(history_values, alpha)
        base = smoothed[-1] if smoothed else Decimal("0")
        forecast_base = [base] * periods_ahead

    elif fm == ForecastModelType.MOVING_AVG:
        base = _moving_average(history_values, n_ma)
        forecast_base = [base] * periods_ahead

    elif fm == ForecastModelType.WEIGHTED_MOVING_AVG:
        base = _weighted_moving_average(history_values, n_ma)
        forecast_base = [base] * periods_ahead

    elif fm == ForecastModelType.SEASONAL:
        # ES base + seasonal adjustment
        smoothed = _exponential_smoothing(history_values, alpha)
        base = smoothed[-1] if smoothed else Decimal("0")
        forecast_base = [base] * periods_ahead   # will be multiplied by seasonal index below

    else:  # PROPHET stub — fall back to ES
        smoothed = _exponential_smoothing(history_values, alpha)
        base = smoothed[-1] if smoothed else Decimal("0")
        forecast_base = [base] * periods_ahead

    # Seasonal indices (used for SEASONAL model and optionally others)
    seasonal_idx = {}
    if fm in (ForecastModelType.SEASONAL,):
        seasonal_idx = _seasonal_indices(history, pt)

    # Spike / outlier detection on history
    hist_non_zero = [float(v) for v in history_values if v > 0]
    hist_mean = Decimal(str(statistics.mean(hist_non_zero))) if hist_non_zero else Decimal("0")
    hist_std  = statistics.stdev(hist_non_zero) if len(hist_non_zero) > 1 else 0.0

    # Build forecast periods
    start_period = _period_start(today, pt)
    # Start one period ahead
    current_period = _next_period(start_period, pt)
    forecast_start = current_period

    lines: list[DemandForecastLine] = []
    for i in range(periods_ahead):
        qty = forecast_base[i]
        if fm == ForecastModelType.SEASONAL and seasonal_idx:
            key = current_period.month if pt == PeriodType.MONTHLY else current_period.isocalendar()[1] % 52
            idx = seasonal_idx.get(key, Decimal("1"))
            qty = _R(qty * idx)

        qty = max(Decimal("0"), _R(qty))
        is_spike = _detect_spike(qty, hist_mean, hist_std)
        is_outlier = qty > hist_mean * Decimal("3") if hist_mean > 0 else False

        lines.append(DemandForecastLine(
            period_date=current_period,
            forecast_qty=qty,
            is_spike=is_spike,
            is_outlier=is_outlier,
        ))
        current_period = _next_period(current_period, pt)

    forecast_end = lines[-1].period_date if lines else forecast_start

    # Compute MAPE over history if we have actuals
    mape = await _compute_mape(db, product_id, history_from, today, pt, history, fm, params)

    # Upsert forecast header (or create new)
    existing_q = await db.execute(
        select(DemandForecast).where(
            DemandForecast.product_id == product_id,
            DemandForecast.period_type == pt,
            DemandForecast.start_date == forecast_start,
            DemandForecast.forecast_model == fm,
        )
    )
    existing = existing_q.scalar_one_or_none()

    if existing:
        # Delete old lines, replace
        for line in existing.lines:
            await db.delete(line)
        await db.flush()
        forecast = existing
        forecast.end_date = forecast_end
        forecast.mape = mape
        forecast.status = ForecastStatus.DRAFT
        forecast.is_approved = False
        forecast.model_params = params
    else:
        forecast = DemandForecast(
            product_id=product_id,
            warehouse_id=warehouse_id,
            forecast_model=fm,
            period_type=pt,
            start_date=forecast_start,
            end_date=forecast_end,
            status=ForecastStatus.DRAFT,
            mape=mape,
            model_params=params,
            created_by=created_by,
        )
        db.add(forecast)
        await db.flush()

    for line in lines:
        line.forecast_id = forecast.id
        db.add(line)

    await db.flush()
    await db.refresh(forecast)
    return forecast


async def _compute_mape(
    db: AsyncSession,
    product_id: UUID,
    from_date: date,
    to_date: date,
    period_type: PeriodType,
    history: list[tuple[date, Decimal]],
    fm: ForecastModelType,
    params: dict,
) -> Optional[Decimal]:
    """Compute out-of-sample MAPE using leave-one-out on historical data."""
    if len(history) < 4:
        return None

    # Use last 30% as test set
    split = max(1, int(len(history) * 0.7))
    train = [qty for _, qty in history[:split]]
    test = [(d, qty) for d, qty in history[split:]]

    errors = []
    alpha = float(params.get("alpha", 0.3))
    n_ma = int(params.get("n", 3))

    for i, (_, actual) in enumerate(test):
        if actual == 0:
            continue
        train_window = train + [qty for _, qty in test[:i]]

        if fm == ForecastModelType.EXPONENTIAL_SMOOTHING:
            smoothed = _exponential_smoothing(train_window, alpha)
            pred = smoothed[-1] if smoothed else Decimal("0")
        elif fm == ForecastModelType.MOVING_AVG:
            pred = _moving_average(train_window, n_ma)
        elif fm == ForecastModelType.WEIGHTED_MOVING_AVG:
            pred = _weighted_moving_average(train_window, n_ma)
        else:
            smoothed = _exponential_smoothing(train_window, alpha)
            pred = smoothed[-1] if smoothed else Decimal("0")

        if actual > 0:
            err = abs(float(pred - actual)) / float(actual) * 100
            errors.append(err)

    if not errors:
        return None
    return _R(Decimal(str(sum(errors) / len(errors))), 2)


async def backfill_actuals(
    db: AsyncSession,
    forecast_id: UUID,
) -> int:
    """Back-fill actual_qty on past forecast lines from real SO data. Returns lines updated."""
    forecast = await db.get(DemandForecast, forecast_id)
    if not forecast:
        return 0

    today = date.today()
    updated = 0
    for line in forecast.lines:
        if line.period_date >= today:
            continue
        history = await _get_sales_history(
            db, forecast.product_id,
            line.period_date,
            _next_period(line.period_date, forecast.period_type) - timedelta(days=1),
            forecast.period_type,
            forecast.warehouse_id,
        )
        actual = sum(qty for _, qty in history) if history else Decimal("0")
        line.actual_qty = actual
        effective = line.adjusted_qty if line.adjusted_qty is not None else line.forecast_qty
        if actual > 0 and effective > 0:
            line.error_pct = _R(abs(effective - actual) / actual * 100, 2)
        updated += 1

    await db.flush()
    return updated
