"""
Production Execution AI — Execution Analyzer + Deviation Detector.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_execution import (
    ProdExecOrder, ExecWorkOrder, ExecOrderMaterial, ExecAIRec,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_all_exec_ai(db: AsyncSession, order_id: uuid.UUID) -> int:
    # Clear old PENDING recs
    old_result = await db.execute(
        select(ExecAIRec)
        .where(ExecAIRec.production_order_id == order_id)
        .where(ExecAIRec.status == "PENDING")
    )
    for rec in old_result.scalars().all():
        await db.delete(rec)
    await db.flush()

    order_result = await db.execute(
        select(ProdExecOrder).where(ProdExecOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        return 0

    wos_result = await db.execute(
        select(ExecWorkOrder).where(ExecWorkOrder.production_order_id == order_id)
    )
    wos = wos_result.scalars().all()

    mats_result = await db.execute(
        select(ExecOrderMaterial).where(ExecOrderMaterial.production_order_id == order_id)
    )
    mats = mats_result.scalars().all()

    recs = []
    recs.extend(await _execution_analyzer(order, wos, mats))
    recs.extend(await _deviation_detector(order, wos, mats))

    for rec_data in recs:
        rec = ExecAIRec(production_order_id=order_id, **rec_data)
        db.add(rec)

    await db.commit()
    return len(recs)


async def _execution_analyzer(
    order: ProdExecOrder,
    wos: list,
    mats: list,
) -> list:
    recs = []

    # Delay detection
    if order.planned_end and order.status in {"IN_PROGRESS", "RELEASED", "PAUSED"}:
        if _now() > order.planned_end:
            delay_hrs = round((_now() - order.planned_end).total_seconds() / 3600, 1)
            recs.append({
                "agent_type": "EXECUTION_ANALYZER",
                "status": "PENDING",
                "title": f"Order {order.order_no} is {delay_hrs}h behind schedule",
                "explanation": f"Planned end was {order.planned_end.strftime('%Y-%m-%d %H:%M')}. Consider adjusting downstream orders.",
                "impact_summary": "Schedule slip — downstream orders may be affected",
                "confidence_score": Decimal("0.95"),
            })

    # High scrap ratio
    if order.completed_qty and float(order.completed_qty) > 0:
        scrap_pct = float(order.scrap_qty or 0) / float(order.planned_qty) * 100
        if scrap_pct > 3:
            recs.append({
                "agent_type": "EXECUTION_ANALYZER",
                "status": "PENDING",
                "title": f"Scrap rate {scrap_pct:.1f}% exceeds 3% threshold",
                "explanation": "Investigate root cause — machine calibration, raw material quality, or operator error.",
                "impact_summary": f"Estimated waste cost: KES {float(order.actual_material_cost or 0) * scrap_pct / 100:,.0f}",
                "confidence_score": Decimal("0.88"),
            })

    # Long work orders with no progress
    for wo in wos:
        if wo.status == "IN_PROGRESS" and wo.started_at:
            run_hrs = (_now() - wo.started_at).total_seconds() / 3600
            planned_hrs = float(wo.run_time_planned or 0) / 60
            if planned_hrs > 0 and run_hrs > planned_hrs * 1.5:
                recs.append({
                    "agent_type": "EXECUTION_ANALYZER",
                    "status": "PENDING",
                    "title": f"Work order step '{wo.step_name}' is 50%+ over planned time",
                    "explanation": f"Planned: {planned_hrs:.1f}h, Elapsed: {run_hrs:.1f}h. Review machine performance.",
                    "impact_summary": "Cycle time overrun — may cause downstream delays",
                    "confidence_score": Decimal("0.82"),
                })

    # Material under-issue
    for mat in mats:
        if mat.required_qty and float(mat.required_qty) > 0:
            issue_pct = float(mat.issued_qty or 0) / float(mat.required_qty) * 100
            if order.status == "IN_PROGRESS" and issue_pct < 50 and float(mat.required_qty) > 10:
                recs.append({
                    "agent_type": "EXECUTION_ANALYZER",
                    "status": "PENDING",
                    "title": f"Material '{mat.item_name}' only {issue_pct:.0f}% issued",
                    "explanation": "Order is in progress but less than 50% of required material has been issued. Check stock availability.",
                    "impact_summary": "Risk of production stoppage due to material shortage",
                    "confidence_score": Decimal("0.79"),
                })
            break  # one recommendation per order is enough for material

    # Rework order without routing
    if order.is_rework and not wos:
        recs.append({
            "agent_type": "EXECUTION_ANALYZER",
            "status": "PENDING",
            "title": "Rework order has no work orders — add rework routing",
            "explanation": "Rework orders should have a dedicated rework routing to track reprocessing steps.",
            "impact_summary": "No operation tracking for rework",
            "confidence_score": Decimal("0.90"),
        })

    return recs


async def _deviation_detector(
    order: ProdExecOrder,
    wos: list,
    mats: list,
) -> list:
    recs = []

    # Abnormal scrap on individual work orders
    for wo in wos:
        if wo.status == "COMPLETED" and wo.planned_qty and float(wo.planned_qty) > 0:
            scrap_pct = float(wo.scrap_qty or 0) / float(wo.planned_qty) * 100
            if scrap_pct > 5:
                recs.append({
                    "agent_type": "DEVIATION_DETECTOR",
                    "status": "PENDING",
                    "title": f"Abnormal scrap at step '{wo.step_name}': {scrap_pct:.1f}%",
                    "explanation": f"Scrap rate {scrap_pct:.1f}% is above 5% threshold. Category: {wo.scrap_category or 'not specified'}. Reason: {wo.scrap_reason or 'not provided'}.",
                    "impact_summary": "Process deviation — root cause analysis required",
                    "confidence_score": Decimal("0.91"),
                })

    # Abnormal run time on completed work orders
    for wo in wos:
        if wo.status == "COMPLETED" and wo.run_time_planned and float(wo.run_time_planned) > 0:
            planned = float(wo.run_time_planned)
            actual = float(wo.run_time_actual or 0)
            deviation = abs(actual - planned) / planned * 100
            if deviation > 30:
                direction = "faster" if actual < planned else "slower"
                recs.append({
                    "agent_type": "DEVIATION_DETECTOR",
                    "status": "PENDING",
                    "title": f"Step '{wo.step_name}' ran {deviation:.0f}% {direction} than planned",
                    "explanation": f"Planned: {planned:.0f} min, Actual: {actual:.0f} min. Check for machine issues or operator efficiency.",
                    "impact_summary": "Cycle time deviation — update standard times if systemic",
                    "confidence_score": Decimal("0.85"),
                })

    # Material over-consumption
    for mat in mats:
        if mat.required_qty and float(mat.required_qty) > 0:
            consumed = float(mat.consumed_qty or mat.issued_qty or 0)
            required = float(mat.required_qty)
            if consumed > required * 1.1:
                over_pct = (consumed - required) / required * 100
                recs.append({
                    "agent_type": "DEVIATION_DETECTOR",
                    "status": "PENDING",
                    "title": f"Material '{mat.item_name}' over-consumed by {over_pct:.1f}%",
                    "explanation": f"Required: {required:.3f} {mat.uom}, Consumed: {consumed:.3f} {mat.uom}. Review BOM accuracy and process control.",
                    "impact_summary": "Material variance — impacts cost accuracy",
                    "confidence_score": Decimal("0.87"),
                })
            break  # one material deviation rec per run

    return recs


async def action_ai_rec(
    db: AsyncSession, rec_id: uuid.UUID, status: str
) -> ExecAIRec:
    result = await db.execute(select(ExecAIRec).where(ExecAIRec.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError("AI recommendation not found")
    rec.status = status
    rec.actioned_at = _now()
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_ai_recs(db: AsyncSession, order_id: uuid.UUID) -> list:
    result = await db.execute(
        select(ExecAIRec)
        .where(ExecAIRec.production_order_id == order_id)
        .order_by(ExecAIRec.created_at.desc())
    )
    return result.scalars().all()
