"""
Production AI Intelligence Service
────────────────────────────────────
Six AI agents using statistical / rule-based hybrid logic.

All agents:
  - Return structured output with confidence_score (0–1) and explanation
  - Persist results to ai_predictions / ai_anomalies / ai_suggestions tables
  - Are callable individually or via run_all_agents()

Agents:
  1. PREDICTION   – Completion time, output quantity, delay risk
  2. ANOMALY      – Material overuse, efficiency drop, downtime, waste spikes
  3. OPTIMIZATION – Batch size, scheduling, resource allocation
  4. RECIPE       – QC trend analysis, high-cost ingredient detection
  5. COST         – Cost per unit trend, waste cost analysis
  6. MAINTENANCE  – MTBF calculation, failure prediction
"""
from __future__ import annotations

import math
import statistics
import uuid
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, and_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production import (
    ProductionOrder, MaterialConsumption, ProductionOrderStatus,
)
from app.models.production_advanced import (
    WorkCenter, WorkOrder, DowntimeEvent, OEERecord,
    WasteRecord, WasteCategory, AdvQCInspection, AdvQCStatus,
    AdvQCResult, QCResultValue, LaborLog,
)
from app.models.production_ai import (
    ProductionPrediction, ProductionAnomaly, ProductionSuggestion, ProductionAIMetrics,
    AgentType, AnomalySeverity, AnomalyType, SuggestionType, SuggestionStatus,
)
from app.models.master import Material, Product
from app.models.recipe import Recipe, RecipeItem


# ── Constants / Thresholds ─────────────────────────────────────────────────────

MATERIAL_OVERUSE_THRESHOLD   = 10.0   # % above standard → anomaly
EFFICIENCY_DROP_THRESHOLD    = 15.0   # % below historical avg OEE
DOWNTIME_SPIKE_THRESHOLD     = 3      # more than 3 events in 24h → anomaly
WASTE_SPIKE_THRESHOLD        = 2.0    # Z-score deviation in loss_pct
QC_FAIL_RATE_THRESHOLD       = 15.0   # >15% fail rate on recent inspections
COST_OVERRUN_THRESHOLD       = 10.0   # cost_variance_pct > 10%
MIN_SAMPLE_SIZE              = 3      # minimum historical orders for reliable stats
DELAY_RISK_HIGH              = 70.0   # % delay risk → RED
DELAY_RISK_MEDIUM            = 35.0   # % delay risk → YELLOW
MTBF_WARNING_FACTOR          = 0.85   # alert when within 85% of historical MTBF


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _gen_no(prefix: str) -> str:
    return f"{prefix}-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _zscore(value: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return abs(value - mean) / std


def _risk_level(delay_risk_pct: float) -> str:
    if delay_risk_pct >= DELAY_RISK_HIGH:
        return "RED"
    if delay_risk_pct >= DELAY_RISK_MEDIUM:
        return "YELLOW"
    return "GREEN"


def _confidence(sample_size: int, base: float = 0.6, cap: float = 0.95) -> float:
    """Confidence grows with sample size, capped at `cap`."""
    if sample_size <= 0:
        return 0.30
    growth = 1.0 - math.exp(-sample_size / 8.0)
    return min(cap, base + (cap - base) * growth)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — PRODUCTION PREDICTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def run_prediction_agent(
    db: AsyncSession,
    order: ProductionOrder,
    persist: bool = True,
) -> dict:
    """
    Predicts completion time, output quantity, and delay risk for one order.

    Logic:
      - Get last N completed orders for the same product
      - Compute historical avg (actual/planned) duration ratio
      - Compute historical avg (actual/planned) quantity ratio
      - Compute historical delay rate (% orders that finished > scheduled_end)
      - If order is IN_PROGRESS, adjust based on elapsed time vs historical avg rate
    """
    product_id    = order.product_id
    planned_qty   = float(_dec(order.planned_quantity))
    scheduled_end = order.scheduled_end

    # ── Historical data ────────────────────────────────────────────────────────
    hist_q = await db.execute(
        select(
            ProductionOrder.planned_quantity,
            ProductionOrder.actual_quantity,
            ProductionOrder.scheduled_start,
            ProductionOrder.scheduled_end,
            ProductionOrder.actual_start,
            ProductionOrder.actual_end,
        )
        .where(
            and_(
                ProductionOrder.product_id == product_id,
                ProductionOrder.status == ProductionOrderStatus.COMPLETED,
                ProductionOrder.actual_end.isnot(None),
                ProductionOrder.actual_start.isnot(None),
            )
        )
        .order_by(desc(ProductionOrder.actual_end))
        .limit(20)
    )
    hist = hist_q.all()
    n = len(hist)

    # Duration ratios (actual / planned)
    duration_ratios: List[float] = []
    qty_ratios:      List[float] = []
    delays:          List[bool]  = []

    for row in hist:
        planned_dur = (row.scheduled_end - row.scheduled_start).total_seconds()
        actual_dur  = (row.actual_end    - row.actual_start).total_seconds()
        if planned_dur > 0:
            duration_ratios.append(actual_dur / planned_dur)
        if row.planned_quantity and float(row.planned_quantity) > 0 and row.actual_quantity:
            qty_ratios.append(float(row.actual_quantity) / float(row.planned_quantity))
        if row.actual_end and row.scheduled_end:
            delays.append(row.actual_end > row.scheduled_end)

    avg_duration_ratio = statistics.mean(duration_ratios) if duration_ratios else 1.0
    avg_qty_ratio      = statistics.mean(qty_ratios)      if qty_ratios      else 1.0
    delay_rate_pct     = (sum(delays) / len(delays) * 100) if delays else 20.0

    # ── Adjust for in-progress order ──────────────────────────────────────────
    now = _now()
    predicted_completion_at = None
    efficiency_forecast_pct = None

    if order.status == ProductionOrderStatus.IN_PROGRESS and order.actual_start:
        planned_dur_sec = (order.scheduled_end - order.scheduled_start).total_seconds()
        predicted_total_sec = planned_dur_sec * avg_duration_ratio
        predicted_completion_at = order.actual_start + timedelta(seconds=predicted_total_sec)

        elapsed_sec     = (now - order.actual_start).total_seconds()
        remaining_pct   = max(0, 1 - elapsed_sec / predicted_total_sec) if predicted_total_sec > 0 else 0
        efficiency_forecast_pct = round((1 / avg_duration_ratio) * 100, 1)

        # Increase delay risk if currently running behind schedule
        if now > order.scheduled_end:
            overtime_pct = min(50, (now - order.scheduled_end).total_seconds() / 3600 * 10)
            delay_rate_pct = min(99, delay_rate_pct + overtime_pct)

    elif order.status == ProductionOrderStatus.PLANNED:
        planned_dur_sec = (order.scheduled_end - order.scheduled_start).total_seconds()
        predicted_completion_at = order.scheduled_start + timedelta(
            seconds=planned_dur_sec * avg_duration_ratio
        )
        efficiency_forecast_pct = round((1 / avg_duration_ratio) * 100, 1)

    # Predicted output
    predicted_output_qty = round(planned_qty * avg_qty_ratio, 3)

    # Explanation
    if n == 0:
        explanation = (
            f"No historical data for this product. Using defaults: "
            f"delay risk {delay_rate_pct:.0f}%, expected output {predicted_output_qty:.1f} {order.uom}."
        )
    else:
        trend = "over" if avg_duration_ratio > 1.05 else ("under" if avg_duration_ratio < 0.95 else "on")
        explanation = (
            f"Based on {n} completed orders for this product: "
            f"orders typically run {trend} schedule (avg {avg_duration_ratio:.2f}× planned duration). "
            f"Historical delay rate: {delay_rate_pct:.0f}%. "
            f"Avg yield: {avg_qty_ratio*100:.1f}% of planned quantity."
        )
        if efficiency_forecast_pct and efficiency_forecast_pct < 85:
            explanation += f" Efficiency forecast {efficiency_forecast_pct:.0f}% — below target 85%."

    risk_lvl       = _risk_level(delay_rate_pct)
    confidence     = _confidence(n)

    result = {
        "predicted_completion_at":  predicted_completion_at.isoformat() if predicted_completion_at else None,
        "predicted_output_qty":     predicted_output_qty,
        "predicted_output_uom":     order.uom,
        "delay_risk_pct":           round(delay_rate_pct, 2),
        "efficiency_forecast_pct":  efficiency_forecast_pct,
        "historical_sample_size":   n,
        "confidence_score":         round(confidence, 4),
        "explanation":              explanation,
        "risk_level":               risk_lvl,
    }

    if persist:
        rec = ProductionPrediction(
            prediction_no          = _gen_no("PRD"),
            production_order_id    = order.id,
            agent_type             = AgentType.PREDICTION,
            predicted_completion_at= predicted_completion_at,
            predicted_output_qty   = predicted_output_qty,
            predicted_output_uom   = order.uom,
            delay_risk_pct         = delay_rate_pct,
            efficiency_forecast_pct= efficiency_forecast_pct,
            historical_sample_size = n,
            confidence_score       = confidence,
            explanation            = explanation,
            risk_level             = risk_lvl,
        )
        db.add(rec)
        await db.flush()
        result["prediction_id"] = str(rec.id)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — ANOMALY DETECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def run_anomaly_agent(
    db: AsyncSession,
    order: Optional[ProductionOrder] = None,
    look_back_days: int = 7,
    persist: bool = True,
) -> List[dict]:
    """
    Detects anomalies across material consumption, efficiency, downtime, waste.
    If order is None, runs a global scan across recent data.
    Returns list of detected anomalies.
    """
    anomalies: List[dict] = []
    since = _now() - timedelta(days=look_back_days)

    # ── 1. Material Consumption Anomalies ────────────────────────────────────
    mat_filter = [MaterialConsumption.actual_quantity.isnot(None)]
    if order:
        mat_filter.append(MaterialConsumption.production_order_id == order.id)
    else:
        mat_filter.append(
            MaterialConsumption.created_at >= since
        )

    mat_q = await db.execute(
        select(
            MaterialConsumption.production_order_id,
            MaterialConsumption.actual_quantity,
            MaterialConsumption.standard_quantity,
            Material.name.label("material_name"),
            Material.code.label("material_code"),
        )
        .join(Material, MaterialConsumption.material_id == Material.id)
        .where(and_(*mat_filter))
    )
    mat_rows = mat_q.all()

    for row in mat_rows:
        std = float(_dec(row.standard_quantity))
        act = float(_dec(row.actual_quantity))
        if std <= 0:
            continue
        deviation_pct = (act - std) / std * 100
        if abs(deviation_pct) > MATERIAL_OVERUSE_THRESHOLD:
            atype = AnomalyType.MATERIAL_OVERUSE if deviation_pct > 0 else AnomalyType.MATERIAL_UNDERUSE
            severity = (AnomalySeverity.HIGH if abs(deviation_pct) > 25
                       else AnomalySeverity.MEDIUM)
            explanation = (
                f"'{row.material_name}' consumption was {act:.3f} vs standard {std:.3f} "
                f"({deviation_pct:+.1f}%). Threshold: ±{MATERIAL_OVERUSE_THRESHOLD}%."
            )
            a = {
                "anomaly_type":        atype.value,
                "severity":            severity.value,
                "affected_area":       f"Material: {row.material_code}",
                "affected_material":   row.material_name,
                "deviation_pct":       round(deviation_pct, 3),
                "actual_value":        act,
                "expected_value":      std,
                "baseline_source":     "BOM standard quantity",
                "confidence_score":    0.90,
                "explanation":         explanation,
                "production_order_id": str(row.production_order_id),
            }
            anomalies.append(a)
            if persist:
                db.add(ProductionAnomaly(
                    anomaly_no          = _gen_no("ANM"),
                    production_order_id = row.production_order_id,
                    anomaly_type        = atype,
                    severity            = severity,
                    affected_area       = f"Material: {row.material_code}",
                    affected_material   = row.material_name,
                    deviation_pct       = deviation_pct,
                    actual_value        = act,
                    expected_value      = std,
                    baseline_source     = "BOM standard quantity",
                    confidence_score    = 0.90,
                    explanation         = explanation,
                ))

    # ── 2. OEE Efficiency Drop ────────────────────────────────────────────────
    oee_q = await db.execute(
        select(
            OEERecord.work_center_id,
            OEERecord.oee_score,
            OEERecord.record_date,
        )
        .where(OEERecord.record_date >= (date.today() - timedelta(days=30)))
        .order_by(OEERecord.record_date)
    )
    oee_rows = oee_q.all()

    if len(oee_rows) >= MIN_SAMPLE_SIZE:
        scores_by_wc: dict = {}
        for r in oee_rows:
            if r.work_center_id not in scores_by_wc:
                scores_by_wc[r.work_center_id] = []
            if r.oee_score is not None:
                scores_by_wc[r.work_center_id].append(float(r.oee_score))

        for wc_id, scores in scores_by_wc.items():
            if len(scores) < MIN_SAMPLE_SIZE:
                continue
            mean_oee  = statistics.mean(scores[:-1])  # avg of all but last
            last_oee  = scores[-1]
            drop_pct  = (mean_oee - last_oee) / mean_oee * 100 if mean_oee > 0 else 0
            if drop_pct > EFFICIENCY_DROP_THRESHOLD:
                explanation = (
                    f"OEE dropped {drop_pct:.1f}% below 30-day average "
                    f"({last_oee*100:.1f}% vs avg {mean_oee*100:.1f}%). "
                    f"Threshold: {EFFICIENCY_DROP_THRESHOLD}% drop."
                )
                a = {
                    "anomaly_type":   AnomalyType.EFFICIENCY_DROP.value,
                    "severity":       (AnomalySeverity.HIGH if drop_pct > 30
                                      else AnomalySeverity.MEDIUM).value,
                    "affected_area":  f"Work Center",
                    "deviation_pct":  round(drop_pct, 3),
                    "actual_value":   round(last_oee * 100, 2),
                    "expected_value": round(mean_oee * 100, 2),
                    "baseline_source": "30-day rolling average OEE",
                    "confidence_score": _confidence(len(scores)),
                    "explanation":    explanation,
                    "work_center_id": str(wc_id),
                }
                anomalies.append(a)
                if persist:
                    db.add(ProductionAnomaly(
                        anomaly_no       = _gen_no("ANM"),
                        work_center_id   = wc_id,
                        anomaly_type     = AnomalyType.EFFICIENCY_DROP,
                        severity         = (AnomalySeverity.HIGH if drop_pct > 30
                                           else AnomalySeverity.MEDIUM),
                        affected_area    = "Work Center",
                        deviation_pct    = drop_pct,
                        actual_value     = last_oee * 100,
                        expected_value   = mean_oee * 100,
                        baseline_source  = "30-day rolling average OEE",
                        confidence_score = _confidence(len(scores)),
                        explanation      = explanation,
                    ))

    # ── 3. Downtime Spike Detection ───────────────────────────────────────────
    dt_q = await db.execute(
        select(
            DowntimeEvent.work_center_id,
            func.count(DowntimeEvent.id).label("event_count"),
        )
        .where(DowntimeEvent.start_time >= since)
        .group_by(DowntimeEvent.work_center_id)
    )
    dt_rows = dt_q.all()

    # Get historical average downtime events per work center per 7 days
    hist_dt_q = await db.execute(
        select(
            DowntimeEvent.work_center_id,
            func.count(DowntimeEvent.id).label("total_events"),
        )
        .where(DowntimeEvent.start_time >= _now() - timedelta(days=90))
        .group_by(DowntimeEvent.work_center_id)
    )
    hist_dt = {r.work_center_id: r.total_events / (90 / look_back_days)
               for r in hist_dt_q.all()}

    for row in dt_rows:
        wc_id    = row.work_center_id
        count    = row.event_count
        hist_avg = hist_dt.get(wc_id, 1.0)
        if count >= DOWNTIME_SPIKE_THRESHOLD and count > hist_avg * 1.5:
            deviation_pct = (count - hist_avg) / hist_avg * 100 if hist_avg > 0 else 100
            explanation = (
                f"{count} downtime events in last {look_back_days} days vs historical avg "
                f"{hist_avg:.1f}. Spike of {deviation_pct:.0f}% above normal frequency."
            )
            a = {
                "anomaly_type":   AnomalyType.EXCESSIVE_DOWNTIME.value,
                "severity":       (AnomalySeverity.HIGH if count >= DOWNTIME_SPIKE_THRESHOLD * 2
                                  else AnomalySeverity.MEDIUM).value,
                "affected_area":  "Machine / Line",
                "deviation_pct":  round(deviation_pct, 2),
                "actual_value":   float(count),
                "expected_value": round(hist_avg, 2),
                "baseline_source": f"90-day rolling average",
                "confidence_score": 0.85,
                "explanation":    explanation,
                "work_center_id": str(wc_id),
            }
            anomalies.append(a)
            if persist:
                db.add(ProductionAnomaly(
                    anomaly_no       = _gen_no("ANM"),
                    work_center_id   = wc_id,
                    anomaly_type     = AnomalyType.EXCESSIVE_DOWNTIME,
                    severity         = (AnomalySeverity.HIGH if count >= DOWNTIME_SPIKE_THRESHOLD * 2
                                       else AnomalySeverity.MEDIUM),
                    affected_area    = "Machine / Line",
                    deviation_pct    = deviation_pct,
                    actual_value     = count,
                    expected_value   = hist_avg,
                    baseline_source  = "90-day rolling average",
                    confidence_score = 0.85,
                    explanation      = explanation,
                ))

    # ── 4. Waste Spike Detection (Z-score) ───────────────────────────────────
    waste_q = await db.execute(
        select(
            WasteRecord.production_order_id,
            WasteRecord.loss_pct,
            WasteRecord.waste_category,
            Material.name.label("material_name"),
        )
        .join(Material, WasteRecord.material_id == Material.id, isouter=True)
        .where(WasteRecord.created_at >= since)
        .where(WasteRecord.loss_pct.isnot(None))
    )
    waste_rows = waste_q.all()

    all_loss_pcts = [float(r.loss_pct) for r in waste_rows if r.loss_pct is not None]
    if len(all_loss_pcts) >= MIN_SAMPLE_SIZE:
        mean_loss = statistics.mean(all_loss_pcts)
        std_loss  = statistics.stdev(all_loss_pcts) if len(all_loss_pcts) > 1 else 0
        for row in waste_rows:
            lp = float(row.loss_pct)
            z  = _zscore(lp, mean_loss, std_loss)
            if z > WASTE_SPIKE_THRESHOLD and lp > mean_loss:
                explanation = (
                    f"Loss rate {lp:.2f}% is {z:.1f} standard deviations above the "
                    f"7-day mean ({mean_loss:.2f}%). Category: {row.waste_category}."
                )
                a = {
                    "anomaly_type":        AnomalyType.WASTE_SPIKE.value,
                    "severity":            (AnomalySeverity.HIGH if z > 3
                                           else AnomalySeverity.MEDIUM).value,
                    "affected_area":       "Waste / Yield",
                    "affected_material":   row.material_name,
                    "deviation_pct":       round((lp - mean_loss) / mean_loss * 100, 2),
                    "actual_value":        lp,
                    "expected_value":      round(mean_loss, 3),
                    "baseline_source":     "7-day rolling mean loss rate",
                    "confidence_score":    min(0.95, 0.6 + z * 0.07),
                    "explanation":         explanation,
                    "production_order_id": str(row.production_order_id),
                }
                anomalies.append(a)
                if persist:
                    db.add(ProductionAnomaly(
                        anomaly_no          = _gen_no("ANM"),
                        production_order_id = row.production_order_id,
                        anomaly_type        = AnomalyType.WASTE_SPIKE,
                        severity            = (AnomalySeverity.HIGH if z > 3
                                              else AnomalySeverity.MEDIUM),
                        affected_area       = "Waste / Yield",
                        affected_material   = row.material_name,
                        deviation_pct       = (lp - mean_loss) / mean_loss * 100,
                        actual_value        = lp,
                        expected_value      = mean_loss,
                        baseline_source     = "7-day rolling mean loss rate",
                        confidence_score    = min(0.95, 0.6 + z * 0.07),
                        explanation         = explanation,
                    ))

    # ── 5. QC Fail Rate Spike ────────────────────────────────────────────────
    qc_q = await db.execute(
        select(
            AdvQCInspection.production_order_id,
            func.count(AdvQCInspection.id).label("total"),
            func.sum(
                func.cast(AdvQCInspection.status == AdvQCStatus.FAILED, func.Integer.__class__)
            ).label("failed"),
        )
        .where(AdvQCInspection.created_at >= since)
        .group_by(AdvQCInspection.production_order_id)
    )
    # Simplified: use status filter directly
    qc_total_q = await db.execute(
        select(func.count(AdvQCInspection.id))
        .where(AdvQCInspection.created_at >= since)
    )
    qc_fail_q = await db.execute(
        select(func.count(AdvQCInspection.id))
        .where(and_(
            AdvQCInspection.created_at >= since,
            AdvQCInspection.status == AdvQCStatus.FAILED,
        ))
    )
    qc_total = qc_total_q.scalar() or 0
    qc_fail  = qc_fail_q.scalar()  or 0
    if qc_total >= MIN_SAMPLE_SIZE:
        fail_rate = qc_fail / qc_total * 100
        if fail_rate > QC_FAIL_RATE_THRESHOLD:
            explanation = (
                f"QC fail rate is {fail_rate:.1f}% ({qc_fail}/{qc_total} inspections) "
                f"in the last {look_back_days} days. Threshold: {QC_FAIL_RATE_THRESHOLD}%."
            )
            a = {
                "anomaly_type":   AnomalyType.QC_FAIL_SPIKE.value,
                "severity":       (AnomalySeverity.CRITICAL if fail_rate > 30
                                  else AnomalySeverity.HIGH).value,
                "affected_area":  "Quality Control",
                "deviation_pct":  round(fail_rate - QC_FAIL_RATE_THRESHOLD, 2),
                "actual_value":   round(fail_rate, 2),
                "expected_value": QC_FAIL_RATE_THRESHOLD,
                "baseline_source": f"Last {look_back_days} days QC records",
                "confidence_score": _confidence(qc_total),
                "explanation":    explanation,
            }
            anomalies.append(a)
            if persist:
                db.add(ProductionAnomaly(
                    anomaly_no       = _gen_no("ANM"),
                    anomaly_type     = AnomalyType.QC_FAIL_SPIKE,
                    severity         = (AnomalySeverity.CRITICAL if fail_rate > 30
                                       else AnomalySeverity.HIGH),
                    affected_area    = "Quality Control",
                    deviation_pct    = fail_rate - QC_FAIL_RATE_THRESHOLD,
                    actual_value     = fail_rate,
                    expected_value   = QC_FAIL_RATE_THRESHOLD,
                    baseline_source  = f"Last {look_back_days} days QC records",
                    confidence_score = _confidence(qc_total),
                    explanation      = explanation,
                ))

    if persist:
        await db.flush()

    return anomalies


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — PRODUCTION OPTIMIZATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def run_optimization_agent(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
    persist: bool = True,
) -> List[dict]:
    """
    Suggests batch size optimization and resource allocation improvements.
    """
    suggestions: List[dict] = []

    # ── 1. Batch Size Optimization ───────────────────────────────────────────
    filters = [
        ProductionOrder.status == ProductionOrderStatus.COMPLETED,
        ProductionOrder.costing_finalized_at.isnot(None),
        ProductionOrder.actual_quantity.isnot(None),
        ProductionOrder.cost_per_unit.isnot(None),
    ]
    if product_id:
        filters.append(ProductionOrder.product_id == product_id)

    batch_q = await db.execute(
        select(
            ProductionOrder.product_id,
            ProductionOrder.actual_quantity,
            ProductionOrder.cost_per_unit,
            ProductionOrder.actual_start,
            ProductionOrder.actual_end,
        )
        .where(and_(*filters))
        .order_by(desc(ProductionOrder.actual_end))
        .limit(50)
    )
    batch_rows = batch_q.all()

    if len(batch_rows) >= MIN_SAMPLE_SIZE:
        # Group by product and find optimal batch size (lowest cost_per_unit)
        from collections import defaultdict
        by_product: dict = defaultdict(list)
        for r in batch_rows:
            by_product[r.product_id].append({
                "qty":          float(_dec(r.actual_quantity)),
                "cost_per_unit": float(_dec(r.cost_per_unit)),
            })

        for prod_id, records in by_product.items():
            if len(records) < MIN_SAMPLE_SIZE:
                continue
            sorted_by_qty = sorted(records, key=lambda x: x["qty"])
            # Find the batch size with lowest cost_per_unit (bottom 20%)
            best_range = sorted_by_qty[len(sorted_by_qty)//2:]  # upper half by qty
            worst_range = sorted_by_qty[:max(1, len(sorted_by_qty)//4)]  # bottom 25%

            best_cpu  = statistics.mean(r["cost_per_unit"] for r in best_range)
            worst_cpu = statistics.mean(r["cost_per_unit"] for r in worst_range)
            best_qty  = statistics.mean(r["qty"] for r in best_range)
            worst_qty = statistics.mean(r["qty"] for r in worst_range)

            if worst_cpu > best_cpu * 1.05 and best_qty > worst_qty * 1.1:
                gain_pct = (worst_cpu - best_cpu) / worst_cpu * 100
                explanation = (
                    f"Larger batches (~{best_qty:.0f} {records[0].get('uom','kg')}) achieve "
                    f"{gain_pct:.1f}% lower cost per unit vs smaller batches (~{worst_qty:.0f}). "
                    f"Based on {len(records)} completed orders."
                )
                s = {
                    "agent_type":                 AgentType.OPTIMIZATION.value,
                    "suggestion_type":            SuggestionType.BATCH_OPTIMIZATION.value,
                    "product_id":                 str(prod_id),
                    "issue_detected":             f"Small batch sizes increase cost per unit",
                    "suggested_change":           f"Increase batch size to ~{best_qty:.0f} units",
                    "current_value":              round(worst_qty, 2),
                    "recommended_value":          round(best_qty, 2),
                    "value_unit":                 "units",
                    "expected_efficiency_gain_pct": round(gain_pct * 0.5, 2),
                    "expected_cost_reduction_pct":  round(gain_pct, 2),
                    "confidence_score":           _confidence(len(records)),
                    "explanation":                explanation,
                }
                suggestions.append(s)
                if persist:
                    db.add(ProductionSuggestion(
                        suggestion_no             = _gen_no("SUG"),
                        agent_type                = AgentType.OPTIMIZATION,
                        suggestion_type           = SuggestionType.BATCH_OPTIMIZATION,
                        product_id                = prod_id,
                        issue_detected            = "Small batch sizes increase cost per unit",
                        suggested_change          = f"Increase batch size to ~{best_qty:.0f} units",
                        current_value             = worst_qty,
                        recommended_value         = best_qty,
                        value_unit                = "units",
                        expected_efficiency_gain_pct = gain_pct * 0.5,
                        expected_cost_reduction_pct  = gain_pct,
                        confidence_score          = _confidence(len(records)),
                        explanation               = explanation,
                        status                    = SuggestionStatus.PENDING,
                    ))

    # ── 2. Work Center Utilization — recommend underloaded centers ────────────
    wc_q = await db.execute(
        select(
            WorkCenter.id,
            WorkCenter.name,
            WorkCenter.department,
        )
        .where(WorkCenter.status == "active")
    )
    work_centers = wc_q.all()

    # Count active work orders per work center in last 30 days
    wo_q = await db.execute(
        select(
            WorkOrder.work_center_id,
            func.count(WorkOrder.id).label("wo_count"),
        )
        .where(WorkOrder.start_time >= _now() - timedelta(days=30))
        .group_by(WorkOrder.work_center_id)
    )
    wo_counts = {r.work_center_id: r.wo_count for r in wo_q.all()}

    if work_centers and wo_counts:
        counts  = list(wo_counts.values())
        avg_wos = statistics.mean(counts) if counts else 0
        std_wos = statistics.stdev(counts) if len(counts) > 1 else 0

        for wc in work_centers:
            count = wo_counts.get(wc.id, 0)
            if avg_wos > 0 and count < avg_wos * 0.5 and std_wos > 0:
                util_pct = count / avg_wos * 100
                explanation = (
                    f"Work center '{wc.name}' used {count} times in last 30 days "
                    f"vs factory avg {avg_wos:.0f} ({util_pct:.0f}% utilization). "
                    f"Routing more jobs here could balance workload."
                )
                s = {
                    "agent_type":      AgentType.OPTIMIZATION.value,
                    "suggestion_type": SuggestionType.RESOURCE_ALLOCATION.value,
                    "work_center_id":  str(wc.id),
                    "issue_detected":  f"Work center '{wc.name}' is underutilized at {util_pct:.0f}%",
                    "suggested_change": f"Route suitable jobs to '{wc.name}' to balance workload",
                    "current_value":   round(count, 0),
                    "recommended_value": round(avg_wos * 0.8, 0),
                    "value_unit":      "work orders / 30 days",
                    "expected_efficiency_gain_pct": round((avg_wos - count) / avg_wos * 15, 2),
                    "confidence_score": _confidence(len(counts)),
                    "explanation":     explanation,
                }
                suggestions.append(s)
                if persist:
                    db.add(ProductionSuggestion(
                        suggestion_no             = _gen_no("SUG"),
                        agent_type                = AgentType.OPTIMIZATION,
                        suggestion_type           = SuggestionType.RESOURCE_ALLOCATION,
                        work_center_id            = wc.id,
                        issue_detected            = f"Work center '{wc.name}' underutilized",
                        suggested_change          = f"Route suitable jobs to '{wc.name}'",
                        current_value             = count,
                        recommended_value         = avg_wos * 0.8,
                        value_unit                = "work orders / 30 days",
                        expected_efficiency_gain_pct = (avg_wos - count) / avg_wos * 15,
                        confidence_score          = _confidence(len(counts)),
                        explanation               = explanation,
                        status                    = SuggestionStatus.PENDING,
                    ))
            if len(suggestions) >= 10:  # cap at 10 optimization suggestions
                break

    if persist:
        await db.flush()

    return suggestions


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — RECIPE IMPROVEMENT ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def run_recipe_agent(
    db: AsyncSession,
    recipe_id: Optional[uuid.UUID] = None,
    persist: bool = True,
) -> List[dict]:
    """
    Analyses recipes for QC instability and high-cost components.
    """
    suggestions: List[dict] = []

    # ── 1. QC instability per recipe ─────────────────────────────────────────
    since_90 = _now() - timedelta(days=90)
    qc_recipe_q = await db.execute(
        select(
            ProductionOrder.recipe_id,
            func.count(AdvQCInspection.id).label("total"),
        )
        .join(AdvQCInspection, AdvQCInspection.production_order_id == ProductionOrder.id)
        .where(AdvQCInspection.created_at >= since_90)
        .group_by(ProductionOrder.recipe_id)
    )
    qc_fail_q2 = await db.execute(
        select(
            ProductionOrder.recipe_id,
            func.count(AdvQCInspection.id).label("failed"),
        )
        .join(AdvQCInspection, AdvQCInspection.production_order_id == ProductionOrder.id)
        .where(and_(
            AdvQCInspection.created_at >= since_90,
            AdvQCInspection.status == AdvQCStatus.FAILED,
        ))
        .group_by(ProductionOrder.recipe_id)
    )
    total_by_recipe  = {r.recipe_id: r.total   for r in qc_recipe_q.all()}
    failed_by_recipe = {r.recipe_id: r.failed  for r in qc_fail_q2.all()}

    for rid, total in total_by_recipe.items():
        if recipe_id and rid != recipe_id:
            continue
        if total < 3:
            continue
        fails     = failed_by_recipe.get(rid, 0)
        fail_rate = fails / total * 100
        if fail_rate > QC_FAIL_RATE_THRESHOLD:
            # Get recipe name
            recipe_q  = await db.execute(select(Recipe).where(Recipe.id == rid))
            recipe    = recipe_q.scalar_one_or_none()
            recipe_name = recipe.name if recipe else str(rid)
            explanation = (
                f"Recipe '{recipe_name}' has a {fail_rate:.1f}% QC failure rate "
                f"({fails}/{total} inspections in 90 days). "
                f"Review process parameters and ingredient ratios for stability."
            )
            s = {
                "agent_type":       AgentType.RECIPE.value,
                "suggestion_type":  SuggestionType.RECIPE_ADJUSTMENT.value,
                "recipe_id":        str(rid),
                "issue_detected":   f"High QC failure rate: {fail_rate:.1f}%",
                "suggested_change": "Review and adjust ingredient ratios; tighten process parameters",
                "expected_quality_improvement": "Reduced QC failure rate and more consistent output",
                "confidence_score": _confidence(total),
                "explanation":      explanation,
            }
            suggestions.append(s)
            if persist:
                db.add(ProductionSuggestion(
                    suggestion_no    = _gen_no("SUG"),
                    agent_type       = AgentType.RECIPE,
                    suggestion_type  = SuggestionType.RECIPE_ADJUSTMENT,
                    recipe_id        = rid,
                    issue_detected   = f"High QC failure rate: {fail_rate:.1f}%",
                    suggested_change = "Review and adjust ingredient ratios; tighten process parameters",
                    expected_quality_improvement = "Reduced QC failure rate",
                    confidence_score = _confidence(total),
                    explanation      = explanation,
                    status           = SuggestionStatus.PENDING,
                ))

    # ── 2. High-cost ingredient identification ────────────────────────────────
    recipe_filter = [] if not recipe_id else [RecipeItem.recipe_id == recipe_id]
    items_q = await db.execute(
        select(
            RecipeItem.recipe_id,
            RecipeItem.quantity,
            Material.name.label("material_name"),
            Material.standard_cost,
        )
        .join(Material, RecipeItem.material_id == Material.id)
        .where(and_(Material.standard_cost.isnot(None), *recipe_filter))
        .order_by(desc(RecipeItem.quantity * Material.standard_cost))
        .limit(50)
    )
    items = items_q.all()

    # Group by recipe, find top-cost ingredient
    from collections import defaultdict
    by_recipe: dict = defaultdict(list)
    for item in items:
        cost = float(_dec(item.quantity)) * float(_dec(item.standard_cost))
        by_recipe[item.recipe_id].append({
            "name": item.material_name,
            "cost": cost,
            "qty":  float(_dec(item.quantity)),
        })

    for rid, components in by_recipe.items():
        if len(components) < 2:
            continue
        total_cost = sum(c["cost"] for c in components)
        if total_cost <= 0:
            continue
        top = max(components, key=lambda x: x["cost"])
        top_pct = top["cost"] / total_cost * 100
        if top_pct > 40:  # single ingredient >40% of recipe cost
            recipe_q  = await db.execute(select(Recipe).where(Recipe.id == rid))
            recipe    = recipe_q.scalar_one_or_none()
            recipe_name = recipe.name if recipe else str(rid)
            explanation = (
                f"'{top['name']}' accounts for {top_pct:.1f}% of recipe material cost "
                f"in '{recipe_name}'. Consider sourcing alternatives or negotiating price."
            )
            s = {
                "agent_type":       AgentType.RECIPE.value,
                "suggestion_type":  SuggestionType.COST_REDUCTION.value,
                "recipe_id":        str(rid),
                "issue_detected":   f"'{top['name']}' is {top_pct:.1f}% of recipe cost",
                "suggested_change": "Evaluate alternative materials or renegotiate pricing",
                "expected_cost_reduction_pct": round(top_pct * 0.1, 2),
                "confidence_score": 0.78,
                "explanation":      explanation,
            }
            suggestions.append(s)
            if persist:
                db.add(ProductionSuggestion(
                    suggestion_no            = _gen_no("SUG"),
                    agent_type               = AgentType.RECIPE,
                    suggestion_type          = SuggestionType.COST_REDUCTION,
                    recipe_id                = rid,
                    issue_detected           = f"'{top['name']}' is {top_pct:.1f}% of recipe cost",
                    suggested_change         = "Evaluate alternative materials or renegotiate pricing",
                    expected_cost_reduction_pct = top_pct * 0.1,
                    confidence_score         = 0.78,
                    explanation              = explanation,
                    status                   = SuggestionStatus.PENDING,
                ))

    if persist:
        await db.flush()
    return suggestions


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5 — COST OPTIMIZATION INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

async def run_cost_agent(
    db: AsyncSession,
    look_back_days: int = 60,
    persist: bool = True,
) -> List[dict]:
    """
    Identifies rising cost trends and high-waste products for cost reduction.
    """
    suggestions: List[dict] = []
    since = _now() - timedelta(days=look_back_days)

    # Cost trend: compare last 30 days vs prior 30 days per product
    mid = _now() - timedelta(days=look_back_days // 2)
    recent_q = await db.execute(
        select(
            ProductionOrder.product_id,
            func.avg(ProductionOrder.cost_per_unit).label("avg_cpu"),
            func.count(ProductionOrder.id).label("count"),
        )
        .where(and_(
            ProductionOrder.status == ProductionOrderStatus.COMPLETED,
            ProductionOrder.costing_finalized_at.isnot(None),
            ProductionOrder.actual_end >= mid,
        ))
        .group_by(ProductionOrder.product_id)
    )
    prior_q = await db.execute(
        select(
            ProductionOrder.product_id,
            func.avg(ProductionOrder.cost_per_unit).label("avg_cpu"),
        )
        .where(and_(
            ProductionOrder.status == ProductionOrderStatus.COMPLETED,
            ProductionOrder.costing_finalized_at.isnot(None),
            ProductionOrder.actual_end >= since,
            ProductionOrder.actual_end < mid,
        ))
        .group_by(ProductionOrder.product_id)
    )
    recent_cpu = {r.product_id: (float(r.avg_cpu or 0), r.count)  for r in recent_q.all()}
    prior_cpu  = {r.product_id:  float(r.avg_cpu or 0)            for r in prior_q.all()}

    for prod_id, (recent, cnt) in recent_cpu.items():
        prior = prior_cpu.get(prod_id)
        if not prior or prior <= 0 or cnt < MIN_SAMPLE_SIZE:
            continue
        change_pct = (recent - prior) / prior * 100
        if change_pct > COST_OVERRUN_THRESHOLD:
            product_q = await db.execute(select(Product).where(Product.id == prod_id))
            product   = product_q.scalar_one_or_none()
            prod_name = product.name if product else str(prod_id)
            explanation = (
                f"Cost per unit for '{prod_name}' increased {change_pct:.1f}% "
                f"(KES {prior:.2f} → {recent:.2f}) over the last {look_back_days} days. "
                f"Investigate material prices, waste levels, and machine efficiency."
            )
            s = {
                "agent_type":       AgentType.COST.value,
                "suggestion_type":  SuggestionType.COST_REDUCTION.value,
                "product_id":       str(prod_id),
                "issue_detected":   f"Cost per unit rising {change_pct:.1f}% over {look_back_days} days",
                "suggested_change": "Review material procurement, reduce waste, and check machine efficiency",
                "current_value":    round(recent, 4),
                "recommended_value": round(prior, 4),
                "value_unit":       "KES per unit",
                "expected_cost_reduction_pct": round(change_pct * 0.6, 2),
                "estimated_kes_saving": round((recent - prior) * 1000, 2),
                "confidence_score": _confidence(cnt),
                "explanation":      explanation,
            }
            suggestions.append(s)
            if persist:
                db.add(ProductionSuggestion(
                    suggestion_no            = _gen_no("SUG"),
                    agent_type               = AgentType.COST,
                    suggestion_type          = SuggestionType.COST_REDUCTION,
                    product_id               = prod_id,
                    issue_detected           = f"Cost per unit rising {change_pct:.1f}%",
                    suggested_change         = "Review material procurement, reduce waste, check machine efficiency",
                    current_value            = recent,
                    recommended_value        = prior,
                    value_unit               = "KES per unit",
                    expected_cost_reduction_pct = change_pct * 0.6,
                    estimated_kes_saving     = (recent - prior) * 1000,
                    confidence_score         = _confidence(cnt),
                    explanation              = explanation,
                    status                   = SuggestionStatus.PENDING,
                ))

    if persist:
        await db.flush()
    return suggestions


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 6 — PREDICTIVE MAINTENANCE
# ══════════════════════════════════════════════════════════════════════════════

async def run_maintenance_agent(
    db: AsyncSession,
    persist: bool = True,
) -> List[dict]:
    """
    Predicts machine failures based on MTBF (Mean Time Between Failures).
    Uses downtime event history to estimate time to next failure.
    """
    suggestions: List[dict] = []

    # Get all work centers with at least 3 downtime events
    wc_q = await db.execute(
        select(WorkCenter.id, WorkCenter.name, WorkCenter.department)
        .where(WorkCenter.status == "active")
    )
    work_centers = wc_q.all()

    for wc in work_centers:
        # Get downtime events sorted by time
        dt_q = await db.execute(
            select(DowntimeEvent.start_time)
            .where(
                and_(
                    DowntimeEvent.work_center_id == wc.id,
                    DowntimeEvent.start_time.isnot(None),
                )
            )
            .order_by(asc(DowntimeEvent.start_time))
        )
        dt_times = [r.start_time for r in dt_q.all()]

        if len(dt_times) < MIN_SAMPLE_SIZE:
            continue

        # Compute inter-failure intervals in hours
        intervals = []
        for i in range(1, len(dt_times)):
            delta_h = (dt_times[i] - dt_times[i-1]).total_seconds() / 3600
            if delta_h > 0:
                intervals.append(delta_h)

        if len(intervals) < 2:
            continue

        mtbf_hours  = statistics.mean(intervals)
        mtbf_std    = statistics.stdev(intervals) if len(intervals) > 1 else mtbf_hours * 0.2
        last_event  = dt_times[-1]
        hours_since = (_now() - last_event).total_seconds() / 3600
        pct_of_mtbf = hours_since / mtbf_hours * 100 if mtbf_hours > 0 else 0

        # Predict next failure
        predicted_next = last_event + timedelta(hours=mtbf_hours)
        time_to_failure_h = (predicted_next - _now()).total_seconds() / 3600

        if pct_of_mtbf >= MTBF_WARNING_FACTOR * 100:
            severity_label = "CRITICAL" if time_to_failure_h < 24 else "HIGH"
            confidence = _confidence(len(dt_times), base=0.55, cap=0.88)
            explanation = (
                f"Work center '{wc.name}' has a historical MTBF of {mtbf_hours:.0f}h "
                f"(±{mtbf_std:.0f}h, n={len(dt_times)} events). "
                f"Last failure was {hours_since:.0f}h ago ({pct_of_mtbf:.0f}% of MTBF). "
                f"Predicted next failure: {predicted_next.strftime('%Y-%m-%d %H:%M')} UTC. "
                f"Schedule maintenance before this window."
            )
            s = {
                "agent_type":       AgentType.MAINTENANCE.value,
                "suggestion_type":  SuggestionType.MAINTENANCE_ACTION.value,
                "work_center_id":   str(wc.id),
                "issue_detected":   f"Machine approaching MTBF limit ({pct_of_mtbf:.0f}%)",
                "suggested_change": f"Schedule preventive maintenance within {max(0, time_to_failure_h):.0f}h",
                "current_value":    round(hours_since, 1),
                "recommended_value": round(mtbf_hours * 0.85, 1),
                "value_unit":       "hours since last event",
                "confidence_score": confidence,
                "explanation":      explanation,
                "predicted_next_failure": predicted_next.isoformat(),
                "hours_to_failure": round(time_to_failure_h, 1),
                "mtbf_hours":       round(mtbf_hours, 1),
                "pct_of_mtbf":      round(pct_of_mtbf, 1),
            }
            suggestions.append(s)
            if persist:
                db.add(ProductionSuggestion(
                    suggestion_no   = _gen_no("SUG"),
                    agent_type      = AgentType.MAINTENANCE,
                    suggestion_type = SuggestionType.MAINTENANCE_ACTION,
                    work_center_id  = wc.id,
                    issue_detected  = f"Machine approaching MTBF limit ({pct_of_mtbf:.0f}%)",
                    suggested_change= f"Schedule preventive maintenance within {max(0, time_to_failure_h):.0f}h",
                    current_value   = hours_since,
                    recommended_value = mtbf_hours * 0.85,
                    value_unit      = "hours since last event",
                    confidence_score= confidence,
                    explanation     = explanation,
                    status          = SuggestionStatus.PENDING,
                ))

    if persist:
        await db.flush()
    return suggestions


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR — run all agents
# ══════════════════════════════════════════════════════════════════════════════

async def run_all_agents(
    db: AsyncSession,
    order: Optional[ProductionOrder] = None,
) -> dict:
    """Run all 6 agents and return combined output."""
    anomalies   = await run_anomaly_agent(db, order=order, persist=True)
    suggestions = await run_optimization_agent(db, persist=True)
    recipe_sug  = await run_recipe_agent(db, persist=True)
    cost_sug    = await run_cost_agent(db, persist=True)
    maint_sug   = await run_maintenance_agent(db, persist=True)

    prediction = None
    if order:
        prediction = await run_prediction_agent(db, order=order, persist=True)

    await db.commit()

    return {
        "prediction":  prediction,
        "anomalies":   anomalies,
        "suggestions": suggestions + recipe_sug + cost_sug + maint_sug,
        "summary": {
            "anomaly_count":    len(anomalies),
            "suggestion_count": len(suggestions) + len(recipe_sug) + len(cost_sug) + len(maint_sug),
            "critical_anomalies": sum(1 for a in anomalies if a.get("severity") in ("critical","high")),
        },
    }


# ── Suggestion status update ──────────────────────────────────────────────────

async def update_suggestion_status(
    db: AsyncSession,
    suggestion_id: uuid.UUID,
    new_status: SuggestionStatus,
    actioned_by: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> ProductionSuggestion:
    q = await db.execute(
        select(ProductionSuggestion).where(ProductionSuggestion.id == suggestion_id)
    )
    sug = q.scalar_one_or_none()
    if not sug:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    sug.status           = new_status
    sug.actioned_by      = actioned_by
    sug.actioned_at      = _now()
    sug.rejection_reason = rejection_reason
    await db.flush()
    return sug


# ── Anomaly resolution ────────────────────────────────────────────────────────

async def resolve_anomaly(
    db: AsyncSession,
    anomaly_id: uuid.UUID,
    resolved_by: str,
    notes: Optional[str] = None,
) -> ProductionAnomaly:
    q = await db.execute(
        select(ProductionAnomaly).where(ProductionAnomaly.id == anomaly_id)
    )
    anom = q.scalar_one_or_none()
    if not anom:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anom.is_resolved      = True
    anom.resolved_at      = _now()
    anom.resolved_by      = resolved_by
    anom.resolution_notes = notes
    await db.flush()
    return anom


# ── Dashboard summary ─────────────────────────────────────────────────────────

async def get_ai_dashboard(db: AsyncSession) -> dict:
    """Top-level AI dashboard data."""
    since_7d = _now() - timedelta(days=7)

    # Recent anomaly counts by severity
    anom_q = await db.execute(
        select(
            ProductionAnomaly.severity,
            func.count(ProductionAnomaly.id).label("cnt"),
        )
        .where(and_(
            ProductionAnomaly.created_at >= since_7d,
            ProductionAnomaly.is_resolved == False,  # noqa: E712
        ))
        .group_by(ProductionAnomaly.severity)
    )
    severity_counts = {r.severity: r.cnt for r in anom_q.all()}

    # Pending suggestions
    sug_q = await db.execute(
        select(func.count(ProductionSuggestion.id))
        .where(ProductionSuggestion.status == SuggestionStatus.PENDING)
    )
    pending_sug = sug_q.scalar() or 0

    # Accepted vs rejected ratio
    acc_q = await db.execute(
        select(
            ProductionSuggestion.status,
            func.count(ProductionSuggestion.id).label("cnt"),
        )
        .where(ProductionSuggestion.status.in_(
            [SuggestionStatus.ACCEPTED, SuggestionStatus.REJECTED]
        ))
        .group_by(ProductionSuggestion.status)
    )
    action_counts = {r.status.value: r.cnt for r in acc_q.all()}

    # Recent predictions
    pred_q = await db.execute(
        select(
            ProductionPrediction.risk_level,
            func.count(ProductionPrediction.id).label("cnt"),
        )
        .where(ProductionPrediction.created_at >= since_7d)
        .group_by(ProductionPrediction.risk_level)
    )
    risk_counts = {r.risk_level: r.cnt for r in pred_q.all()}

    return {
        "anomalies_7d": {
            "critical": severity_counts.get("critical", 0),
            "high":     severity_counts.get("high", 0),
            "medium":   severity_counts.get("medium", 0),
            "low":      severity_counts.get("low", 0),
            "total":    sum(severity_counts.values()),
        },
        "suggestions": {
            "pending":  int(pending_sug),
            "accepted": action_counts.get("accepted", 0),
            "rejected": action_counts.get("rejected", 0),
        },
        "predictions_7d": {
            "green":  risk_counts.get("GREEN",  0),
            "yellow": risk_counts.get("YELLOW", 0),
            "red":    risk_counts.get("RED",    0),
        },
    }
