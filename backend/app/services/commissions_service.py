"""Sales Commission Tracking — rule engine, calculation, approvals, payouts, AI."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commissions import (
    CommissionRule, CommissionRuleLine, CommissionTarget,
    CommissionTxn, CommissionAdjustment, CommissionPayout,
    CMAIRecommendation,
    CommissionAppliesTo, CommissionScope, RuleStatus,
    CommissionType, TxnStatus, PayoutStatus,
    CMAIAgentType, CMAIRecStatus,
)
from app.schemas.commissions import (
    CommissionRuleCreate, CommissionRuleUpdate,
    TargetCreate, CommissionCalcRequest,
    AdjustmentCreate, PayoutCreate,
    ApproveRequest, RejectRequest, CMAIRecAck,
)


def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _period_from_date(d: date) -> str:
    return d.strftime("%Y-%m")


# ── Rule CRUD ─────────────────────────────────────────────────────────────────

async def list_rules(
    db: AsyncSession,
    applies_to: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[CommissionRule]:
    q = select(CommissionRule).options(selectinload(CommissionRule.lines))
    if applies_to:
        q = q.where(CommissionRule.applies_to == applies_to)
    if status:
        q = q.where(CommissionRule.status == status)
    result = await db.execute(q.order_by(CommissionRule.priority, CommissionRule.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def get_rule(db: AsyncSession, rule_id: uuid.UUID) -> Optional[CommissionRule]:
    result = await db.execute(
        select(CommissionRule).options(selectinload(CommissionRule.lines)).where(CommissionRule.id == rule_id)
    )
    return result.scalars().first()


async def create_rule(db: AsyncSession, payload: CommissionRuleCreate, user_id: Optional[uuid.UUID]) -> CommissionRule:
    rule = CommissionRule(
        rule_code=payload.rule_code,
        rule_name=payload.rule_name,
        applies_to=payload.applies_to,
        applicable_scope=payload.applicable_scope,
        scope_ref_id=payload.scope_ref_id,
        priority=payload.priority,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=RuleStatus.DRAFT.value,
        contract_id=payload.contract_id,
        created_by=user_id,
        notes=payload.notes,
    )
    db.add(rule)
    await db.flush()
    for lp in payload.lines:
        db.add(CommissionRuleLine(rule_id=rule.id, **lp.model_dump()))
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(db: AsyncSession, rule: CommissionRule, payload: CommissionRuleUpdate) -> CommissionRule:
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def activate_rule(db: AsyncSession, rule: CommissionRule) -> CommissionRule:
    rule.status = RuleStatus.ACTIVE.value
    await db.commit()
    await db.refresh(rule)
    return rule


# ── Rule resolution ───────────────────────────────────────────────────────────

async def _find_best_rule(
    db: AsyncSession,
    applies_to: str,
    calc_date: date,
    customer_id: Optional[uuid.UUID] = None,
    product_id: Optional[uuid.UUID] = None,
) -> Optional[CommissionRule]:
    """Resolve highest-priority active rule for the entity + context."""
    q = select(CommissionRule).options(selectinload(CommissionRule.lines)).where(
        CommissionRule.applies_to == applies_to,
        CommissionRule.status == RuleStatus.ACTIVE.value,
        CommissionRule.start_date <= calc_date,
        or_(CommissionRule.end_date.is_(None), CommissionRule.end_date >= calc_date),
    ).order_by(CommissionRule.priority)

    result = await db.execute(q)
    rules = result.scalars().all()

    # Priority: most-specific scope first (customer > product > category > global)
    for rule in rules:
        if rule.applicable_scope == CommissionScope.CUSTOMER.value and customer_id and rule.scope_ref_id == customer_id:
            return rule
    for rule in rules:
        if rule.applicable_scope == CommissionScope.PRODUCT.value and product_id and rule.scope_ref_id == product_id:
            return rule
    for rule in rules:
        if rule.applicable_scope == CommissionScope.GLOBAL.value:
            return rule

    return rules[0] if rules else None


def _apply_rule_line(line: CommissionRuleLine, base_amount: Decimal) -> Decimal:
    if line.commission_type == CommissionType.PERCENTAGE.value:
        return base_amount * _D(line.commission_value) / 100
    return _D(line.commission_value)  # fixed


def _resolve_line(lines: List[CommissionRuleLine], base_amount: Decimal) -> tuple[Optional[CommissionRuleLine], Decimal]:
    """Pick the matching tier line for base_amount and compute commission."""
    sorted_lines = sorted(lines, key=lambda l: (l.sort_order, _D(l.min_threshold or 0)))
    for line in sorted_lines:
        min_t = _D(line.min_threshold) if line.min_threshold is not None else None
        max_t = _D(line.max_threshold) if line.max_threshold is not None else None
        if min_t is not None and base_amount < min_t:
            continue
        if max_t is not None and base_amount > max_t:
            continue
        return line, _apply_rule_line(line, base_amount)
    # Fallback: last line
    if sorted_lines:
        line = sorted_lines[-1]
        return line, _apply_rule_line(line, base_amount)
    return None, Decimal("0")


# ── Calculation Engine ────────────────────────────────────────────────────────

async def calculate_commission(
    db: AsyncSession, payload: CommissionCalcRequest, user_id: Optional[uuid.UUID]
) -> CommissionTxn:
    # Dedup: same order/invoice for same rep
    if payload.sales_order_id or payload.invoice_id:
        dup_q = await db.execute(
            select(CommissionTxn).where(
                CommissionTxn.sales_order_id == payload.sales_order_id if payload.sales_order_id else True,
                CommissionTxn.invoice_id == payload.invoice_id if payload.invoice_id else True,
                CommissionTxn.sales_rep_id == payload.sales_rep_id if payload.sales_rep_id else True,
                CommissionTxn.distributor_id == payload.distributor_id if payload.distributor_id else True,
                CommissionTxn.is_reversal == payload.is_reversal,
            )
        )
        if dup_q.scalars().first():
            raise ValueError("Commission already calculated for this transaction")

    applies_to = (
        CommissionAppliesTo.SALES_REP.value if payload.sales_rep_id
        else CommissionAppliesTo.DISTRIBUTOR.value
    )

    rule = await _find_best_rule(
        db, applies_to, payload.calculation_date,
        customer_id=payload.customer_id,
    )

    period = payload.period or _period_from_date(payload.calculation_date)
    base = _D(payload.base_amount)

    if payload.is_reversal:
        base = -base

    if rule and rule.lines:
        line, commission = _resolve_line(rule.lines, abs(base))
        if payload.is_reversal:
            commission = -commission
        detail = {
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "line_condition": line.condition_type if line else None,
            "commission_value": float(line.commission_value) if line else 0,
            "commission_type": line.commission_type if line else None,
            "base_amount": float(base),
        }
        pct = (line.commission_value if line and line.commission_type == CommissionType.PERCENTAGE.value else None)
    else:
        commission = Decimal("0")
        detail = {"note": "No matching rule found"}
        pct = None
        rule = None

    txn = CommissionTxn(
        rule_id=rule.id if rule else None,
        sales_order_id=payload.sales_order_id,
        invoice_id=payload.invoice_id,
        sales_rep_id=payload.sales_rep_id,
        distributor_id=payload.distributor_id,
        customer_id=payload.customer_id,
        base_amount=base,
        commission_pct=pct,
        commission_amount=commission,
        calculation_date=payload.calculation_date,
        period=period,
        status=TxnStatus.PENDING.value,
        is_reversal=payload.is_reversal,
        calc_detail=detail,
        notes=payload.notes,
    )
    db.add(txn)

    # Update target actuals
    entity_id = payload.sales_rep_id or payload.distributor_id
    if entity_id and not payload.is_reversal:
        tgt_q = await db.execute(
            select(CommissionTarget).where(
                CommissionTarget.entity_id == entity_id,
                CommissionTarget.period == period,
            )
        )
        target = tgt_q.scalars().first()
        if target:
            target.actual_value = (_D(target.actual_value) + base)
            if _D(target.target_value) > 0:
                target.achievement_pct = _D(target.actual_value) / _D(target.target_value) * 100
            if target.achievement_pct and target.achievement_pct >= 100:
                target.bonus_earned = (_D(target.actual_value) - _D(target.target_value)) * Decimal("0.01")

    await db.commit()
    await db.refresh(txn)
    return txn


async def list_transactions(
    db: AsyncSession,
    sales_rep_id: Optional[uuid.UUID] = None,
    distributor_id: Optional[uuid.UUID] = None,
    period: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, limit: int = 100,
) -> List[CommissionTxn]:
    q = select(CommissionTxn)
    if sales_rep_id:
        q = q.where(CommissionTxn.sales_rep_id == sales_rep_id)
    if distributor_id:
        q = q.where(CommissionTxn.distributor_id == distributor_id)
    if period:
        q = q.where(CommissionTxn.period == period)
    if status:
        q = q.where(CommissionTxn.status == status)
    result = await db.execute(q.order_by(CommissionTxn.calculation_date.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def approve_txn(db: AsyncSession, txn: CommissionTxn, user_id: Optional[uuid.UUID], comments: Optional[str]) -> CommissionTxn:
    txn.status = TxnStatus.APPROVED.value
    txn.approved_by = user_id
    txn.approved_at = datetime.utcnow()
    if comments:
        txn.notes = (txn.notes or "") + f"\n[Approved] {comments}"
    await db.commit()
    await db.refresh(txn)
    return txn


async def reject_txn(db: AsyncSession, txn: CommissionTxn, reason: str, user_id: Optional[uuid.UUID]) -> CommissionTxn:
    txn.status = TxnStatus.REJECTED.value
    txn.rejection_reason = reason
    await db.commit()
    await db.refresh(txn)
    return txn


async def get_txn(db: AsyncSession, txn_id: uuid.UUID) -> Optional[CommissionTxn]:
    result = await db.execute(
        select(CommissionTxn).options(selectinload(CommissionTxn.adjustments)).where(CommissionTxn.id == txn_id)
    )
    return result.scalars().first()


# ── Adjustments ───────────────────────────────────────────────────────────────

async def add_adjustment(db: AsyncSession, txn: CommissionTxn, payload: AdjustmentCreate, user_id: Optional[uuid.UUID]) -> CommissionAdjustment:
    adj = CommissionAdjustment(
        txn_id=txn.id,
        adjustment_amount=payload.adjustment_amount,
        reason=payload.reason,
        approved_by=user_id,
        notes=payload.notes,
    )
    db.add(adj)
    await db.commit()
    await db.refresh(adj)
    return adj


# ── Targets ───────────────────────────────────────────────────────────────────

async def upsert_target(db: AsyncSession, payload: TargetCreate) -> CommissionTarget:
    existing = await db.execute(
        select(CommissionTarget).where(
            CommissionTarget.entity_id == payload.entity_id,
            CommissionTarget.period == payload.period,
            CommissionTarget.applies_to == payload.applies_to,
        )
    )
    target = existing.scalars().first()
    if target:
        target.target_value = payload.target_value
    else:
        target = CommissionTarget(
            entity_id=payload.entity_id,
            applies_to=payload.applies_to,
            period=payload.period,
            target_value=payload.target_value,
            actual_value=Decimal("0"),
            notes=payload.notes,
        )
        db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def list_targets(db: AsyncSession, entity_id: Optional[uuid.UUID] = None, period: Optional[str] = None) -> List[CommissionTarget]:
    q = select(CommissionTarget)
    if entity_id:
        q = q.where(CommissionTarget.entity_id == entity_id)
    if period:
        q = q.where(CommissionTarget.period == period)
    result = await db.execute(q.order_by(CommissionTarget.period.desc()))
    return result.scalars().all()


# ── Payout ────────────────────────────────────────────────────────────────────

async def create_payout(db: AsyncSession, payload: PayoutCreate, user_id: Optional[uuid.UUID]) -> CommissionPayout:
    # Sum approved commissions for entity/period
    txn_q = await db.execute(
        select(CommissionTxn).where(
            or_(
                CommissionTxn.sales_rep_id == payload.entity_id,
                CommissionTxn.distributor_id == payload.entity_id,
            ),
            CommissionTxn.period == payload.period,
            CommissionTxn.status == TxnStatus.APPROVED.value,
        )
    )
    txns = txn_q.scalars().all()
    total = sum(_D(t.commission_amount) for t in txns)
    txn_ids = [str(t.id) for t in txns]

    # Sum adjustments
    adj_total = Decimal("0")
    for t in txns:
        adj_q = await db.execute(select(CommissionAdjustment).where(CommissionAdjustment.txn_id == t.id))
        for adj in adj_q.scalars().all():
            adj_total += _D(adj.adjustment_amount)

    net = total + adj_total

    payout = CommissionPayout(
        entity_id=payload.entity_id,
        applies_to=payload.applies_to,
        period=payload.period,
        total_commission=total,
        adjustments_total=adj_total,
        net_commission=net,
        paid_amount=Decimal("0"),
        status=PayoutStatus.DRAFT.value,
        txn_ids=txn_ids,
        notes=payload.notes,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return payout


async def approve_payout(db: AsyncSession, payout: CommissionPayout, user_id: Optional[uuid.UUID]) -> CommissionPayout:
    payout.status = PayoutStatus.APPROVED.value
    payout.approved_by = user_id
    await db.commit()
    await db.refresh(payout)
    return payout


async def mark_payout_paid(db: AsyncSession, payout: CommissionPayout, payment_date: date) -> CommissionPayout:
    payout.status = PayoutStatus.PAID.value
    payout.paid_amount = payout.net_commission
    payout.payment_date = payment_date
    # Mark included txns as paid
    if payout.txn_ids:
        for tid in payout.txn_ids:
            txn = await db.get(CommissionTxn, uuid.UUID(tid))
            if txn:
                txn.status = TxnStatus.PAID.value
    await db.commit()
    await db.refresh(payout)
    return payout


async def list_payouts(
    db: AsyncSession, entity_id: Optional[uuid.UUID] = None,
    period: Optional[str] = None, status: Optional[str] = None
) -> List[CommissionPayout]:
    q = select(CommissionPayout)
    if entity_id:
        q = q.where(CommissionPayout.entity_id == entity_id)
    if period:
        q = q.where(CommissionPayout.period == period)
    if status:
        q = q.where(CommissionPayout.status == status)
    result = await db.execute(q.order_by(CommissionPayout.period.desc()))
    return result.scalars().all()


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_summary(db: AsyncSession) -> Dict[str, Any]:
    total = (await db.execute(select(func.count()).select_from(CommissionTxn))).scalar_one()
    pending = (await db.execute(select(func.count()).select_from(CommissionTxn).where(CommissionTxn.status == TxnStatus.PENDING.value))).scalar_one()
    approved = (await db.execute(select(func.count()).select_from(CommissionTxn).where(CommissionTxn.status == TxnStatus.APPROVED.value))).scalar_one()
    total_amount = (await db.execute(
        select(func.sum(CommissionTxn.commission_amount)).where(CommissionTxn.status != TxnStatus.REJECTED.value)
    )).scalar_one()
    paid_amount = (await db.execute(
        select(func.sum(CommissionTxn.commission_amount)).where(CommissionTxn.status == TxnStatus.PAID.value)
    )).scalar_one()
    return {
        "total_txns": total, "pending": pending, "approved": approved,
        "total_commission": float(total_amount or 0),
        "paid_commission": float(paid_amount or 0),
    }


async def report_by_period(db: AsyncSession, period: Optional[str] = None) -> List[Dict]:
    q = select(
        CommissionTxn.period,
        CommissionTxn.sales_rep_id,
        func.sum(CommissionTxn.commission_amount).label("total"),
        func.count().label("count"),
    ).where(CommissionTxn.status != TxnStatus.REJECTED.value)
    if period:
        q = q.where(CommissionTxn.period == period)
    q = q.group_by(CommissionTxn.period, CommissionTxn.sales_rep_id).order_by(CommissionTxn.period.desc())
    result = await db.execute(q)
    return [
        {"period": r.period, "sales_rep_id": str(r.sales_rep_id) if r.sales_rep_id else None,
         "total_commission": float(r.total or 0), "txn_count": r.count}
        for r in result.all()
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[CMAIRecommendation]:
    recs: list[CMAIRecommendation] = []
    today = date.today()
    period = _period_from_date(today)

    # Agent 1 — Incentive Optimizer: reps with zero commission this month
    txn_rep_q = await db.execute(
        select(CommissionTxn.sales_rep_id, func.count().label("cnt"))
        .where(CommissionTxn.period == period, CommissionTxn.sales_rep_id.isnot(None))
        .group_by(CommissionTxn.sales_rep_id)
    )
    active_reps = {str(r.sales_rep_id) for r in txn_rep_q.all()}

    if not active_reps:
        rec = CMAIRecommendation(
            agent_type=CMAIAgentType.INCENTIVE_OPTIMIZER.value,
            severity="INFO",
            title=f"No commission transactions recorded for {period}",
            body="No commission has been calculated this month. Run the commission calculation engine against posted invoices/orders to generate rep commissions.",
            data={"period": period},
        )
        db.add(rec)
        recs.append(rec)

    # Agent 2 — Fraud Detection: commission spikes > 3× average
    avg_q = await db.execute(
        select(func.avg(CommissionTxn.commission_amount)).where(CommissionTxn.status != TxnStatus.REJECTED.value)
    )
    avg = float(avg_q.scalar_one() or 0)
    if avg > 0:
        spike_q = await db.execute(
            select(CommissionTxn).where(
                CommissionTxn.commission_amount > avg * 3,
                CommissionTxn.status == TxnStatus.PENDING.value,
            ).limit(10)
        )
        spikes = spike_q.scalars().all()
        for txn in spikes:
            rec = CMAIRecommendation(
                agent_type=CMAIAgentType.FRAUD_DETECTION.value,
                severity="WARNING",
                entity_id=txn.sales_rep_id or txn.distributor_id,
                title=f"Commission spike detected: KES {float(txn.commission_amount):,.0f} (avg KES {avg:,.0f})",
                body=(
                    f"Transaction {txn.id} shows commission {float(txn.commission_amount):,.0f} which is "
                    f"more than 3× the average ({avg:,.0f}). Review the base amount, rule applied, and "
                    "ensure no price manipulation occurred before approving."
                ),
                data={"txn_id": str(txn.id), "commission": float(txn.commission_amount), "avg": avg},
            )
            db.add(rec)
            recs.append(rec)

    # Agent 3 — Performance Advisor: targets with <50% achievement
    low_targets_q = await db.execute(
        select(CommissionTarget).where(
            CommissionTarget.period == period,
            CommissionTarget.achievement_pct.isnot(None),
            CommissionTarget.achievement_pct < 50,
        ).limit(10)
    )
    for t in low_targets_q.scalars().all():
        rec = CMAIRecommendation(
            agent_type=CMAIAgentType.PERFORMANCE_ADVISOR.value,
            severity="WARNING",
            entity_id=t.entity_id,
            title=f"Rep below 50% target: {float(t.achievement_pct or 0):.1f}% achieved in {t.period}",
            body=(
                f"This sales rep/distributor has achieved {float(t.achievement_pct or 0):.1f}% "
                f"of their {t.period} target (KES {float(t.actual_value):,.0f} of KES {float(t.target_value):,.0f}). "
                "Consider coaching, reviewing territory coverage, or adjusting targets if market conditions changed."
            ),
            data={"achievement_pct": float(t.achievement_pct or 0), "period": t.period},
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        await db.commit()
    return recs


async def list_ai_recs(db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None) -> List[CMAIRecommendation]:
    q = select(CMAIRecommendation)
    if agent_type:
        q = q.where(CMAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(CMAIRecommendation.status == status)
    result = await db.execute(q.order_by(CMAIRecommendation.created_at.desc()).limit(100))
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: uuid.UUID, payload: CMAIRecAck) -> Optional[CMAIRecommendation]:
    rec = await db.get(CMAIRecommendation, rec_id)
    if rec:
        rec.status = payload.status
        await db.commit()
        await db.refresh(rec)
    return rec
