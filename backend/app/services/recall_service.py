"""
Recall Management Service — initiation, scope, containment, actions, returns, AI.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traceability import (
    RecallHeader, RecallScopeLine, RecallAction, RecallCustomerImpact,
    RecallReturnRecord, TRRecAIRecommendation,
    RecallStatus, RecallActionStatus, RecallRiskStatus,
    RecallActionType, TRRecAIAgentType, TRRecAIRecStatus,
    TraceEventType, TraceEventLine, LotGenealogyLink,
)
from app.models.inventory import Lot, Stock
from app.models.sales import SalesOrder
from app.schemas.traceability import (
    RecallCreate, RecallStatusUpdate, RecallActionCreate, RecallActionComplete,
    RecallReturnCreate, TRRecAIRecReview,
    RecallHeaderOut, RecallDetail, RecallDashboard,
    RecallScopeLineOut, RecallActionOut, RecallCustomerImpactOut,
    RecallReturnOut, TRRecAIRecommendationOut, RecallRegulatoryReport,
)
from app.services import traceability_service as trace_svc


# ─────────────────────────────────────────────────────────────────────────────
# Recall Number Generator
# ─────────────────────────────────────────────────────────────────────────────

def _gen_recall_no(recall_type: str) -> str:
    prefix = {"mock_recall": "MOCK", "regulatory": "REG", "market": "MKT"}.get(recall_type, "RCL")
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


# ─────────────────────────────────────────────────────────────────────────────
# Recall CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def initiate_recall(db: AsyncSession, data: RecallCreate) -> RecallHeader:
    recall = RecallHeader(
        recall_no=_gen_recall_no(data.recall_type.value),
        recall_type=data.recall_type,
        recall_reason=data.recall_reason,
        trigger_source=data.trigger_source,
        severity_level=data.severity_level,
        status=RecallStatus.draft,
        initiation_datetime=datetime.utcnow(),
        initiated_by_id=data.initiated_by_id,
        source_lot_id=data.source_lot_id,
        source_product_id=data.source_product_id,
        source_material_id=data.source_material_id,
        source_supplier_id=data.source_supplier_id,
        target_market=data.target_market,
        country_scope=data.country_scope,
        product_scope_notes=data.product_scope_notes,
        linked_qc_case_id=data.linked_qc_case_id,
        linked_complaint_id=data.linked_complaint_id,
        notes=data.notes,
    )
    db.add(recall)
    await db.commit()
    await db.refresh(recall)
    return recall


async def get_recall(db: AsyncSession, recall_id: uuid.UUID) -> Optional[RecallHeader]:
    return await db.get(RecallHeader, recall_id)


async def list_recalls(db: AsyncSession, status: Optional[RecallStatus] = None,
                        limit: int = 100) -> List[RecallHeader]:
    q = select(RecallHeader).order_by(desc(RecallHeader.initiation_datetime)).limit(limit)
    if status:
        q = q.where(RecallHeader.status == status)
    r = await db.execute(q)
    return list(r.scalars().all())


async def update_recall_status(db: AsyncSession, recall_id: uuid.UUID,
                                data: RecallStatusUpdate) -> RecallHeader:
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    recall.status = data.status
    now = datetime.utcnow()

    if data.status == RecallStatus.active and recall.scope_calculated_at:
        recall.contained_at = now
    elif data.status == RecallStatus.completed:
        recall.completed_at = now
        if recall.initiation_datetime:
            recall.time_to_contain_hours = Decimal(str(
                round((now - recall.initiation_datetime).total_seconds() / 3600, 2)
            ))
    elif data.status == RecallStatus.closed:
        recall.closed_at = now

    if data.approved_by_id:
        recall.approved_by_id = data.approved_by_id
        recall.approved_at = now

    if data.notes:
        recall.notes = (recall.notes or "") + f"\n[{now.date()}] {data.notes}"

    await db.commit()
    await db.refresh(recall)
    return recall


# ─────────────────────────────────────────────────────────────────────────────
# Scope Calculation
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_scope(db: AsyncSession, recall_id: uuid.UUID) -> List[RecallScopeLine]:
    """Run forward traceability from the source lot, build scope lines."""
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    # Clear existing scope lines
    existing_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    for sl in existing_r.scalars().all():
        await db.delete(sl)
    await db.flush()

    scope_lines: List[RecallScopeLine] = []
    start_time = datetime.utcnow()

    # Source lots to trace
    root_lots: List[uuid.UUID] = []
    if recall.source_lot_id:
        root_lots.append(recall.source_lot_id)

    # If source_product_id only, find lots for that product
    if not root_lots and recall.source_product_id:
        lots_r = await db.execute(
            select(Lot).where(Lot.product_id == recall.source_product_id).limit(50)
        )
        root_lots = [l.id for l in lots_r.scalars().all()]

    if not root_lots and recall.source_material_id:
        lots_r = await db.execute(
            select(Lot).where(Lot.material_id == recall.source_material_id).limit(50)
        )
        root_lots = [l.id for l in lots_r.scalars().all()]

    all_affected_lot_ids: set[uuid.UUID] = set(root_lots)
    all_affected_customers: set[uuid.UUID] = set()

    # Forward trace from each root lot
    for root_lot_id in root_lots:
        fwd = await trace_svc.forward_trace(db, root_lot_id, max_depth=8)
        for al in fwd.affected_lots:
            all_affected_lot_ids.add(uuid.UUID(al["lot_id"]))
        for ac in fwd.affected_customers:
            if ac.get("customer_id"):
                all_affected_customers.add(uuid.UUID(ac["customer_id"]))

    # Build scope lines for each affected lot
    total_affected_qty = Decimal("0")
    for lot_id in all_affected_lot_ids:
        lot = await db.get(Lot, lot_id)
        if not lot:
            continue

        fwd = await trace_svc.forward_trace(db, lot_id, max_depth=2)

        sl = RecallScopeLine(
            recall_id=recall_id,
            affected_item_id=lot.product_id,
            affected_material_id=lot.material_id,
            affected_lot_id=lot_id,
            affected_qty_total=fwd.total_affected_qty,
            affected_qty_in_stock=fwd.qty_in_stock,
            affected_qty_shipped=fwd.qty_shipped,
            affected_qty_returned=fwd.qty_returned,
            affected_qty_scrapped=fwd.qty_scrapped,
            affected_qty_quarantined=fwd.qty_quarantined,
            affected_qty_reworked=fwd.qty_reworked,
            affected_customer_count=len(fwd.affected_customers),
            risk_status=_derive_risk(lot, fwd),
        )
        db.add(sl)
        scope_lines.append(sl)
        total_affected_qty += fwd.total_affected_qty

    # Update recall header
    recall.scope_calculated_at = datetime.utcnow()
    recall.total_affected_qty = total_affected_qty
    recall.total_affected_customers = len(all_affected_customers)
    recall.status = RecallStatus.active

    trace_secs = (datetime.utcnow() - start_time).total_seconds()
    recall.time_to_trace_hours = Decimal(str(round(trace_secs / 3600, 4)))

    await db.commit()
    return scope_lines


def _derive_risk(lot: Lot, fwd) -> RecallRiskStatus:
    """Derive risk status from lot expiry and shipped quantity."""
    if fwd.qty_shipped > 1000:
        return RecallRiskStatus.critical
    if fwd.qty_shipped > 100:
        return RecallRiskStatus.high
    if fwd.qty_shipped > 10:
        return RecallRiskStatus.medium
    return RecallRiskStatus.low


# ─────────────────────────────────────────────────────────────────────────────
# Containment
# ─────────────────────────────────────────────────────────────────────────────

async def contain_recall(db: AsyncSession, recall_id: uuid.UUID) -> Dict[str, int]:
    """Place holds on all scope line lots and block shipments."""
    scope_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    scope_lines = list(scope_r.scalars().all())
    holds_placed = 0
    now = datetime.utcnow()

    for sl in scope_lines:
        if sl.affected_lot_id and not sl.hold_placed:
            # Place quarantine on associated stocks
            stocks_r = await db.execute(
                select(Stock).where(Stock.lot_id == sl.affected_lot_id)
            )
            for stock in stocks_r.scalars().all():
                stock.is_blocked = True
            sl.hold_placed = True
            sl.hold_placed_at = now
            sl.action_status = RecallActionStatus.in_progress
            holds_placed += 1

    recall = await db.get(RecallHeader, recall_id)
    if recall:
        recall.status = RecallStatus.contained
        recall.contained_at = now

    await db.commit()
    return {"holds_placed": holds_placed}


# ─────────────────────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────────────────────

async def create_action(db: AsyncSession, recall_id: uuid.UUID,
                         data: RecallActionCreate) -> RecallAction:
    action = RecallAction(recall_id=recall_id, **data.model_dump())
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def complete_action(db: AsyncSession, action_id: uuid.UUID,
                           data: RecallActionComplete) -> RecallAction:
    action = await db.get(RecallAction, action_id)
    if not action:
        raise ValueError("RecallAction not found")
    action.status        = RecallActionStatus.completed
    action.completed_at  = datetime.utcnow()
    action.completed_by_id = data.completed_by_id
    action.evidence_note = data.evidence_note
    await db.commit()
    await db.refresh(action)
    return action


async def list_actions(db: AsyncSession, recall_id: uuid.UUID) -> List[RecallAction]:
    r = await db.execute(
        select(RecallAction).where(RecallAction.recall_id == recall_id)
        .order_by(RecallAction.due_date)
    )
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Customer Impact
# ─────────────────────────────────────────────────────────────────────────────

async def build_customer_impact(db: AsyncSession, recall_id: uuid.UUID) -> List[RecallCustomerImpact]:
    """Generate or refresh customer impact records from scope lines."""
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    # Clear existing
    existing_r = await db.execute(
        select(RecallCustomerImpact).where(RecallCustomerImpact.recall_id == recall_id)
    )
    for ci in existing_r.scalars().all():
        await db.delete(ci)
    await db.flush()

    scope_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    scope_lines = list(scope_r.scalars().all())

    impacts: List[RecallCustomerImpact] = []

    for sl in scope_lines:
        if not sl.affected_lot_id:
            continue

        # Find shipment event lines for this lot
        ship_lines_r = await db.execute(
            select(TraceEventLine).where(
                TraceEventLine.source_lot_id == sl.affected_lot_id,
            )
        )
        for line in ship_lines_r.scalars().all():
            from app.models.traceability import TraceEvent
            event = await db.get(TraceEvent, line.event_id)
            if event and event.trace_event_type == TraceEventType.shipment and line.linked_customer_id:
                ci = RecallCustomerImpact(
                    recall_id=recall_id,
                    customer_id=line.linked_customer_id,
                    affected_lot_id=sl.affected_lot_id,
                    shipment_reference=str(line.linked_shipment_id) if line.linked_shipment_id else None,
                    qty_delivered=line.quantity,
                    risk_level=sl.risk_status,
                    priority_rank=1 if sl.risk_status == RecallRiskStatus.critical else
                                  2 if sl.risk_status == RecallRiskStatus.high else 3,
                )
                db.add(ci)
                impacts.append(ci)

    await db.commit()
    return impacts


async def list_customer_impacts(db: AsyncSession, recall_id: uuid.UUID) -> List[RecallCustomerImpact]:
    r = await db.execute(
        select(RecallCustomerImpact).where(RecallCustomerImpact.recall_id == recall_id)
        .order_by(RecallCustomerImpact.priority_rank)
    )
    return list(r.scalars().all())


async def notify_customer(db: AsyncSession, impact_id: uuid.UUID,
                           method: str = "email") -> RecallCustomerImpact:
    ci = await db.get(RecallCustomerImpact, impact_id)
    if not ci:
        raise ValueError("CustomerImpact not found")
    ci.notification_sent    = True
    ci.notification_sent_at = datetime.utcnow()
    ci.notification_method  = method
    await db.commit()
    await db.refresh(ci)
    return ci


# ─────────────────────────────────────────────────────────────────────────────
# Returns
# ─────────────────────────────────────────────────────────────────────────────

async def record_return(db: AsyncSession, recall_id: uuid.UUID,
                         data: RecallReturnCreate) -> RecallReturnRecord:
    received = data.qty_received or Decimal("0")
    requested = data.qty_requested or Decimal("0")
    discrepancy = abs(requested - received) if requested else None

    ret = RecallReturnRecord(
        recall_id=recall_id,
        customer_id=data.customer_id,
        lot_id=data.lot_id,
        qty_requested=data.qty_requested,
        qty_confirmed=data.qty_confirmed,
        qty_received=data.qty_received,
        qty_destroyed_at_customer=data.qty_destroyed_at_customer,
        qty_quarantined_on_return=data.qty_quarantined_on_return,
        qty_reworked=data.qty_reworked,
        qty_written_off=data.qty_written_off,
        return_date=data.return_date,
        return_ref=data.return_ref,
        return_refused=data.return_refused,
        discrepancy=discrepancy,
        follow_up_required=data.return_refused or (discrepancy is not None and discrepancy > 0),
        evidence_notes=data.evidence_notes,
    )
    db.add(ret)
    await _update_recall_recovery(db, recall_id)
    await db.commit()
    await db.refresh(ret)
    return ret


async def _update_recall_recovery(db: AsyncSession, recall_id: uuid.UUID) -> None:
    """Recompute recovery_pct based on all returns vs scope."""
    recall = await db.get(RecallHeader, recall_id)
    if not recall or not recall.total_affected_qty:
        return

    returns_r = await db.execute(
        select(func.sum(RecallReturnRecord.qty_received)).where(
            RecallReturnRecord.recall_id == recall_id
        )
    )
    total_returned = returns_r.scalar() or Decimal("0")
    scrapped_r = await db.execute(
        select(func.sum(RecallReturnRecord.qty_destroyed_at_customer)).where(
            RecallReturnRecord.recall_id == recall_id
        )
    )
    total_scrapped = scrapped_r.scalar() or Decimal("0")
    recovered = total_returned + total_scrapped

    total = recall.total_affected_qty or Decimal("1")
    recall.recovery_pct = Decimal(str(round(float(recovered) / float(total) * 100, 2)))


async def list_returns(db: AsyncSession, recall_id: uuid.UUID) -> List[RecallReturnRecord]:
    r = await db.execute(
        select(RecallReturnRecord).where(RecallReturnRecord.recall_id == recall_id)
        .order_by(desc(RecallReturnRecord.return_date))
    )
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Close Recall
# ─────────────────────────────────────────────────────────────────────────────

async def close_recall(db: AsyncSession, recall_id: uuid.UUID,
                        effectiveness_score: Optional[Decimal] = None) -> RecallHeader:
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    now = datetime.utcnow()
    recall.status       = RecallStatus.closed
    recall.closed_at    = now
    recall.completed_at = recall.completed_at or now

    if recall.initiation_datetime:
        recall.time_to_contain_hours = recall.time_to_contain_hours or Decimal(str(
            round((now - recall.initiation_datetime).total_seconds() / 3600, 2)
        ))

    if effectiveness_score is not None:
        recall.effectiveness_score = effectiveness_score

    await db.commit()
    await db.refresh(recall)
    return recall


# ─────────────────────────────────────────────────────────────────────────────
# Regulatory Report
# ─────────────────────────────────────────────────────────────────────────────

async def generate_regulatory_report(db: AsyncSession, recall_id: uuid.UUID) -> RecallRegulatoryReport:
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    scope_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    scope_lines = list(scope_r.scalars().all())

    actions_r = await db.execute(
        select(RecallAction).where(RecallAction.recall_id == recall_id)
    )
    actions = list(actions_r.scalars().all())

    source_lot_number = None
    if recall.source_lot_id:
        lot = await db.get(Lot, recall.source_lot_id) # type: ignore[import]
        if lot:
            source_lot_number = lot.lot_number

    affected_lots = [
        str(sl.affected_lot_id) for sl in scope_lines if sl.affected_lot_id
    ]

    actions_taken = [
        f"{a.action_type.value}: {a.status.value}{' — ' + a.evidence_note if a.evidence_note else ''}"
        for a in actions
    ]

    narrative = (
        f"Recall {recall.recall_no} was initiated on {recall.initiation_datetime.date()} "
        f"due to: {recall.recall_reason}. "
        f"Severity: {recall.severity_level.value.upper()}. "
        f"Trigger: {recall.trigger_source.value}. "
        f"Total affected quantity: {recall.total_affected_qty or 0} units across "
        f"{len(affected_lots)} lot(s) and {recall.total_affected_customers or 0} customer(s). "
        f"Recovery rate: {recall.recovery_pct or 0}%. "
        f"Current status: {recall.status.value.upper()}."
    )

    return RecallRegulatoryReport(
        recall_no=recall.recall_no,
        recall_type=recall.recall_type,
        severity_level=recall.severity_level,
        trigger_source=recall.trigger_source,
        initiation_datetime=recall.initiation_datetime,
        recall_reason=recall.recall_reason,
        source_lot_number=source_lot_number,
        total_affected_qty=recall.total_affected_qty,
        total_affected_customers=recall.total_affected_customers,
        affected_lots=affected_lots,
        affected_markets=recall.country_scope or recall.target_market or "—",
        actions_taken=actions_taken,
        recovery_pct=recall.recovery_pct,
        time_to_trace_hours=recall.time_to_trace_hours,
        time_to_contain_hours=recall.time_to_contain_hours,
        status=recall.status,
        summary_narrative=narrative,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

async def get_recall_dashboard(db: AsyncSession) -> RecallDashboard:
    total_r = await db.execute(select(func.count(RecallHeader.id)))
    total = total_r.scalar() or 0

    active_r = await db.execute(
        select(func.count(RecallHeader.id)).where(
            RecallHeader.status.in_([RecallStatus.active, RecallStatus.contained, RecallStatus.in_progress])
        )
    )
    active = active_r.scalar() or 0

    crit_r = await db.execute(
        select(func.count(RecallHeader.id)).where(
            RecallHeader.severity_level == "critical",
            RecallHeader.status.in_([RecallStatus.active, RecallStatus.contained]),
        )
    )
    critical = crit_r.scalar() or 0

    comp_r = await db.execute(
        select(func.count(RecallHeader.id)).where(
            RecallHeader.status.in_([RecallStatus.completed, RecallStatus.closed])
        )
    )
    completed = comp_r.scalar() or 0

    avg_trace_r = await db.execute(
        select(func.avg(RecallHeader.time_to_trace_hours)).where(
            RecallHeader.time_to_trace_hours.isnot(None)
        )
    )
    avg_trace = avg_trace_r.scalar()
    avg_trace_dec = Decimal(str(round(float(avg_trace), 2))) if avg_trace else None

    avg_rec_r = await db.execute(
        select(func.avg(RecallHeader.recovery_pct)).where(RecallHeader.recovery_pct.isnot(None))
    )
    avg_rec = avg_rec_r.scalar()
    avg_rec_dec = Decimal(str(round(float(avg_rec), 2))) if avg_rec else None

    recent_r = await db.execute(
        select(RecallHeader).order_by(desc(RecallHeader.initiation_datetime)).limit(10)
    )
    recent = list(recent_r.scalars().all())

    pending_actions_r = await db.execute(
        select(func.count(RecallAction.id)).where(RecallAction.status == RecallActionStatus.pending)
    )
    pending_actions = pending_actions_r.scalar() or 0

    open_scope_r = await db.execute(
        select(func.count(RecallScopeLine.id)).where(
            RecallScopeLine.action_status.in_([RecallActionStatus.pending, RecallActionStatus.in_progress])
        )
    )
    open_scope = open_scope_r.scalar() or 0

    return RecallDashboard(
        total_recalls=total,
        active_recalls=active,
        critical_recalls=critical,
        completed_recalls=completed,
        avg_time_to_trace_h=avg_trace_dec,
        avg_recovery_pct=avg_rec_dec,
        recent_recalls=[RecallHeaderOut.model_validate(r) for r in recent],
        pending_actions=pending_actions,
        open_scope_lines=open_scope,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI Agents
# ─────────────────────────────────────────────────────────────────────────────

async def _run_scope_validator(db: AsyncSession, recall_id: uuid.UUID) -> List[TRRecAIRecommendation]:
    recs: List[TRRecAIRecommendation] = []
    scope_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    scope_lines = list(scope_r.scalars().all())

    # Check for lots with zero genealogy links (potential missing traceability)
    for sl in scope_lines:
        if not sl.affected_lot_id:
            continue
        link_r = await db.execute(
            select(func.count(LotGenealogyLink.id)).where(
                (LotGenealogyLink.parent_lot_id == sl.affected_lot_id) |
                (LotGenealogyLink.child_lot_id  == sl.affected_lot_id)
            )
        )
        link_count = link_r.scalar() or 0
        if link_count == 0:
            rec = TRRecAIRecommendation(
                agent_type=TRRecAIAgentType.scope_validator,
                status=TRRecAIRecStatus.pending,
                recall_id=recall_id,
                lot_id=sl.affected_lot_id,
                title="Isolated Lot — No Genealogy Links Found",
                explanation=(
                    f"Lot {sl.affected_lot_id} appears in the recall scope but has no genealogy "
                    f"links recorded. This may indicate missing traceability data or a receipt "
                    f"without proper lot linkage."
                ),
                recommendation=(
                    "Manually investigate the source and destination of this lot. "
                    "Check GRN records, production logs, and material flow transactions "
                    "to confirm whether additional lots should be in scope."
                ),
                confidence_score=Decimal("0.82"),
                priority_score=1,
            )
            recs.append(rec)

    return recs


async def _run_risk_prioritizer(db: AsyncSession, recall_id: uuid.UUID) -> List[TRRecAIRecommendation]:
    recs: List[TRRecAIRecommendation] = []

    # Find highest-risk scope lines (critical + not yet held)
    scope_r = await db.execute(
        select(RecallScopeLine).where(
            RecallScopeLine.recall_id == recall_id,
            RecallScopeLine.risk_status.in_([RecallRiskStatus.critical, RecallRiskStatus.high]),
            RecallScopeLine.hold_placed == False,
        )
    )
    critical_lines = list(scope_r.scalars().all())

    if critical_lines:
        rec = TRRecAIRecommendation(
            agent_type=TRRecAIAgentType.risk_prioritizer,
            status=TRRecAIRecStatus.pending,
            recall_id=recall_id,
            title=f"{len(critical_lines)} High/Critical Scope Lines Without Hold",
            explanation=(
                f"There are {len(critical_lines)} high or critical risk scope lines where "
                f"containment holds have not yet been placed. These represent the highest "
                f"exposure in this recall."
            ),
            recommendation=(
                "Prioritize placing holds on these lots immediately. "
                "Use the Containment action to block all associated stocks "
                "and prevent further shipment."
            ),
            confidence_score=Decimal("0.95"),
            priority_score=1,
        )
        recs.append(rec)

    # Customer impact priority
    notif_r = await db.execute(
        select(func.count(RecallCustomerImpact.id)).where(
            RecallCustomerImpact.recall_id == recall_id,
            RecallCustomerImpact.notification_sent == False,
        )
    )
    unnotified = notif_r.scalar() or 0

    if unnotified > 0:
        rec = TRRecAIRecommendation(
            agent_type=TRRecAIAgentType.risk_prioritizer,
            status=TRRecAIRecStatus.pending,
            recall_id=recall_id,
            title=f"{unnotified} Customers Not Yet Notified",
            explanation=(
                f"{unnotified} customers in the impact list have not been notified. "
                f"Delayed notification increases regulatory risk and customer trust exposure."
            ),
            recommendation=(
                "Send customer notifications immediately for critical and high-risk customers. "
                "Use the Customer Impact panel to filter by risk level and send notifications."
            ),
            confidence_score=Decimal("0.90"),
            priority_score=2,
        )
        recs.append(rec)

    return recs


async def _run_investigation_assistant(db: AsyncSession, recall_id: uuid.UUID) -> List[TRRecAIRecommendation]:
    recs: List[TRRecAIRecommendation] = []
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        return recs

    # Suggest backward trace on source lot
    if recall.source_lot_id:
        rec = TRRecAIRecommendation(
            agent_type=TRRecAIAgentType.investigation_assistant,
            status=TRRecAIRecStatus.pending,
            recall_id=recall_id,
            lot_id=recall.source_lot_id,
            title="Run Backward Traceability on Source Lot",
            explanation=(
                f"The source lot for this recall has not been fully backward-traced. "
                f"Running backward traceability will identify the raw materials, suppliers, "
                f"and production orders that contributed to the defective batch."
            ),
            recommendation=(
                "Use the Backward Traceability tool to trace the source lot to its origin. "
                "Identify the supplier GRN, raw material lot, and production batch. "
                "If the defect is traced to a supplier, initiate a supplier quality alert."
            ),
            confidence_score=Decimal("0.88"),
            priority_score=1,
        )
        recs.append(rec)

    # Check if there are sibling lots from same production order
    if recall.source_lot_id:
        source_lot = await db.get(Lot, recall.source_lot_id)
        if source_lot and source_lot.batch_number:
            sibling_r = await db.execute(
                select(Lot).where(
                    Lot.batch_number == source_lot.batch_number,
                    Lot.id != recall.source_lot_id,
                ).limit(10)
            )
            siblings = list(sibling_r.scalars().all())
            if siblings:
                rec = TRRecAIRecommendation(
                    agent_type=TRRecAIAgentType.investigation_assistant,
                    status=TRRecAIRecStatus.pending,
                    recall_id=recall_id,
                    lot_id=recall.source_lot_id,
                    title=f"{len(siblings)} Sibling Lots from Same Batch — Review for Expansion",
                    explanation=(
                        f"Found {len(siblings)} other lots sharing the same batch number as the source lot. "
                        f"If the defect is batch-wide, these lots may also be affected and should be "
                        f"evaluated for inclusion in the recall scope."
                    ),
                    recommendation=(
                        "Review the sibling lots from the same batch. "
                        "If the investigation confirms batch-level contamination or defect, "
                        "expand the recall scope to include these lots."
                    ),
                    confidence_score=Decimal("0.75"),
                    priority_score=2,
                )
                recs.append(rec)

    return recs


async def run_recall_ai_agents(db: AsyncSession, recall_id: uuid.UUID) -> List[TRRecAIRecommendation]:
    """Run all 3 AI agents for a specific recall."""
    all_recs: List[TRRecAIRecommendation] = []
    for runner in [_run_scope_validator, _run_risk_prioritizer, _run_investigation_assistant]:
        recs = await runner(db, recall_id)
        for rec in recs:
            db.add(rec)
            all_recs.append(rec)
    await db.commit()
    return all_recs


async def list_ai_recommendations(db: AsyncSession, recall_id: uuid.UUID) -> List[TRRecAIRecommendation]:
    r = await db.execute(
        select(TRRecAIRecommendation).where(TRRecAIRecommendation.recall_id == recall_id)
        .order_by(TRRecAIRecommendation.priority_score)
    )
    return list(r.scalars().all())


async def review_ai_recommendation(db: AsyncSession, rec_id: uuid.UUID,
                                    data: TRRecAIRecReview) -> TRRecAIRecommendation:
    rec = await db.get(TRRecAIRecommendation, rec_id)
    if not rec:
        raise ValueError("TRRecAIRecommendation not found")
    rec.status         = data.status
    rec.reviewed_by_id = data.reviewed_by_id
    rec.reviewed_at    = datetime.utcnow()
    rec.review_note    = data.review_note
    await db.commit()
    await db.refresh(rec)
    return rec


# ─────────────────────────────────────────────────────────────────────────────
# Recall Detail Builder
# ─────────────────────────────────────────────────────────────────────────────

async def get_recall_detail(db: AsyncSession, recall_id: uuid.UUID) -> RecallDetail:
    recall = await db.get(RecallHeader, recall_id)
    if not recall:
        raise ValueError("Recall not found")

    scope_r = await db.execute(
        select(RecallScopeLine).where(RecallScopeLine.recall_id == recall_id)
    )
    scope_lines = list(scope_r.scalars().all())

    actions = await list_actions(db, recall_id)
    customer_impacts = await list_customer_impacts(db, recall_id)
    returns = await list_returns(db, recall_id)
    ai_recs = await list_ai_recommendations(db, recall_id)

    detail = RecallDetail(
        **{
            col: getattr(recall, col)
            for col in [
                "id", "recall_no", "recall_type", "recall_reason", "trigger_source",
                "severity_level", "status", "initiation_datetime", "initiated_by_id",
                "approved_by_id", "approved_at", "source_lot_id", "source_product_id",
                "source_material_id", "source_supplier_id", "target_market",
                "country_scope", "product_scope_notes", "scope_calculated_at",
                "contained_at", "completed_at", "closed_at", "total_affected_qty",
                "total_affected_customers", "recovery_pct", "effectiveness_score",
                "time_to_trace_hours", "time_to_contain_hours", "notes",
                "created_at", "updated_at",
            ]
        },
        scope_lines=[RecallScopeLineOut.model_validate(sl) for sl in scope_lines],
        actions=[RecallActionOut.model_validate(a) for a in actions],
        customer_impacts=[RecallCustomerImpactOut.model_validate(ci) for ci in customer_impacts],
        returns=[RecallReturnOut.model_validate(r) for r in returns],
        ai_recs=[TRRecAIRecommendationOut.model_validate(r) for r in ai_recs],
    )
    return detail
