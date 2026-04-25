"""Promotional Schemes Auto-Apply service layer — evaluation engine."""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.promotions import (
    PromoScheme, PromoEligibility, PromoRuleLine, PromoTierLine,
    SalesOrderPromo, SalesOrderPromoLine, PromoOverrideRequest,
    PromoUsageTally, PromoAIRecommendation,
    SchemeStatus, PromoApplicationType, PromoImpactType,
    OverrideStatus, PromoAIAgentType, PromoAIRecStatus,
    TriggerBasis, RewardType,
)
from app.schemas.promotions import (
    PromoSchemeCreate, PromoEligibilityCreate, PromoRuleLineCreate,
    OverrideRequestCreate, ApproveOverrideRequest,
    EvaluateOrderResult, PromoApplicationResult, PromoLineImpactResult,
    OrderLineInput,
)
import uuid as uuid_mod


# ── Scheme CRUD ────────────────────────────────────────────────────────────────

async def list_schemes(db: AsyncSession, status: SchemeStatus = None, active_only: bool = False):
    q = select(PromoScheme).options(
        selectinload(PromoScheme.eligibility_scopes),
        selectinload(PromoScheme.rule_lines),
    )
    if status:
        q = q.where(PromoScheme.status == status)
    if active_only:
        today = date.today()
        q = q.where(
            PromoScheme.status == SchemeStatus.ACTIVE,
            PromoScheme.valid_from <= today,
            PromoScheme.valid_to >= today,
        )
    result = await db.execute(q.order_by(PromoScheme.priority_rank, PromoScheme.scheme_code))
    schemes = result.scalars().all()
    # attach usage counts
    tally_q = select(
        PromoUsageTally.scheme_id,
        func.sum(PromoUsageTally.order_count).label("cnt"),
        func.sum(PromoUsageTally.total_cost).label("cost"),
    ).group_by(PromoUsageTally.scheme_id)
    tallies = {r.scheme_id: (r.cnt, r.cost) for r in (await db.execute(tally_q)).all()}
    for s in schemes:
        cnt, cost = tallies.get(s.id, (0, Decimal(0)))
        s.usage_count = cnt or 0
        s.total_cost = cost or Decimal(0)
        for rl in s.rule_lines:
            ti = rl.trigger_item
            ri = rl.reward_item
            rl.trigger_item_name = ti.product_name if ti else None
            rl.reward_item_name  = ri.product_name if ri else None
    return schemes


async def get_scheme(db: AsyncSession, scheme_id) -> PromoScheme:
    q = select(PromoScheme).options(
        selectinload(PromoScheme.eligibility_scopes),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.trigger_item),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.reward_item),
    ).where(PromoScheme.id == scheme_id)
    result = await db.execute(q)
    scheme = result.scalar_one_or_none()
    if not scheme:
        raise ValueError("Scheme not found")
    scheme.usage_count = 0
    scheme.total_cost = Decimal(0)
    for rl in scheme.rule_lines:
        rl.trigger_item_name = rl.trigger_item.product_name if rl.trigger_item else None
        rl.reward_item_name  = rl.reward_item.product_name if rl.reward_item else None
    return scheme


async def create_scheme(db: AsyncSession, data: PromoSchemeCreate, created_by_id=None) -> PromoScheme:
    elig_data = data.eligibility_scopes
    rules_data = data.rule_lines
    obj_data = data.model_dump(exclude={"eligibility_scopes", "rule_lines"})
    obj = PromoScheme(**obj_data, created_by_id=created_by_id)
    db.add(obj)
    await db.flush()
    for e in elig_data:
        db.add(PromoEligibility(scheme_id=obj.id, **e.model_dump()))
    for r in rules_data:
        tiers = r.tiers
        rule = PromoRuleLine(scheme_id=obj.id, **r.model_dump(exclude={"tiers"}))
        db.add(rule)
        await db.flush()
        for t in tiers:
            db.add(PromoTierLine(rule_line_id=rule.id, **t.model_dump()))
    await db.commit()
    await db.refresh(obj)
    return obj


async def activate_scheme(db: AsyncSession, scheme_id, approver_id=None) -> PromoScheme:
    obj = await db.get(PromoScheme, scheme_id)
    if not obj:
        raise ValueError("Scheme not found")
    obj.status = SchemeStatus.ACTIVE
    obj.approved_by_id = approver_id
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_scheme_status(db: AsyncSession, scheme_id, status: SchemeStatus) -> PromoScheme:
    obj = await db.get(PromoScheme, scheme_id)
    if not obj:
        raise ValueError("Scheme not found")
    obj.status = status
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Eligibility Check ──────────────────────────────────────────────────────────

def _check_eligibility(
    scope: PromoEligibility,
    customer_id: Optional[str],
    channel: Optional[str],
    region: Optional[str],
    price_list_id: Optional[str],
    order_lines: List[OrderLineInput],
    order_total: Decimal,
) -> bool:
    """Returns True if the eligibility scope matches the order context."""
    if not scope.active:
        return False
    if scope.applies_to_customer_id and str(scope.applies_to_customer_id) != str(customer_id or ""):
        return False
    if scope.applies_to_channel and scope.applies_to_channel != channel:
        return False
    if scope.applies_to_region and scope.applies_to_region != region:
        return False
    if scope.applies_to_price_list_id and str(scope.applies_to_price_list_id) != str(price_list_id or ""):
        return False
    if scope.min_order_value and order_total < scope.min_order_value:
        return False
    total_qty = sum(l.qty for l in order_lines)
    if scope.min_order_qty and total_qty < scope.min_order_qty:
        return False
    # Category / brand / item checks — eligible if any line matches
    if scope.applies_to_item_id:
        if not any(str(l.item_id) == str(scope.applies_to_item_id) for l in order_lines):
            return False
    if scope.applies_to_item_category:
        if not any(l.item_category == scope.applies_to_item_category for l in order_lines):
            return False
    if scope.applies_to_brand:
        if not any(l.item_brand == scope.applies_to_brand for l in order_lines):
            return False
    return True


def _is_scheme_date_valid(scheme: PromoScheme) -> bool:
    today = date.today()
    return scheme.valid_from <= today <= scheme.valid_to


# ── Rule Evaluation ────────────────────────────────────────────────────────────

def _evaluate_rule(
    rule: PromoRuleLine,
    order_lines: List[OrderLineInput],
    order_total: Decimal,
) -> Optional[PromoLineImpactResult]:
    """Evaluate a single rule against order lines. Returns impact or None."""

    if rule.trigger_basis == TriggerBasis.ORDER_TOTAL or rule.trigger_basis == TriggerBasis.VALUE:
        if order_total < rule.min_trigger_value:
            return None
        return _build_order_level_impact(rule, order_total)

    matching_lines = []
    for line in order_lines:
        match = False
        if rule.trigger_basis == TriggerBasis.SKU and rule.trigger_item_id:
            match = str(line.item_id) == str(rule.trigger_item_id)
        elif rule.trigger_basis == TriggerBasis.CATEGORY and rule.trigger_category:
            match = line.item_category == rule.trigger_category
        elif rule.trigger_basis == TriggerBasis.BRAND and rule.trigger_brand:
            match = line.item_brand == rule.trigger_brand
        elif rule.trigger_basis in (TriggerBasis.QUANTITY, TriggerBasis.MIX_SET):
            match = True
        if match:
            matching_lines.append(line)

    if not matching_lines:
        return None

    total_matching_qty = sum(l.qty for l in matching_lines)
    total_matching_value = sum(l.line_total for l in matching_lines)

    if total_matching_qty < rule.min_trigger_qty and rule.min_trigger_qty > 0:
        return None
    if total_matching_value < rule.min_trigger_value and rule.min_trigger_value > 0:
        return None

    return _build_line_impact(rule, matching_lines, total_matching_qty, total_matching_value)


def _build_line_impact(
    rule: PromoRuleLine,
    matching_lines: List[OrderLineInput],
    total_qty: Decimal,
    total_value: Decimal,
) -> PromoLineImpactResult:
    if rule.reward_type == RewardType.FREE_GOODS:
        multiplier = Decimal(1)
        if rule.repeatable and rule.min_trigger_qty > 0:
            multiplier = (total_qty // rule.min_trigger_qty)
        reward_qty = (rule.reward_qty or Decimal(1)) * multiplier
        if rule.max_reward_qty:
            reward_qty = min(reward_qty, rule.max_reward_qty)
        avg_price = (total_value / total_qty) if total_qty else Decimal(0)
        return PromoLineImpactResult(
            impact_type=PromoImpactType.FREE_GOODS,
            reward_item_id=rule.reward_item_id or (matching_lines[0].item_id if matching_lines else None),
            reward_qty=reward_qty,
            discount_amount=reward_qty * avg_price,
            notes=f"Free goods: {reward_qty} units",
        )

    elif rule.reward_type == RewardType.PERCENT_DISCOUNT:
        pct = rule.reward_percent or Decimal(0)
        disc = total_value * (pct / Decimal(100))
        return PromoLineImpactResult(
            impact_type=PromoImpactType.DISCOUNT,
            discount_pct=pct,
            discount_amount=disc,
            notes=f"{pct}% discount on qualifying lines",
        )

    elif rule.reward_type == RewardType.FIXED_DISCOUNT:
        disc = rule.reward_amount or Decimal(0)
        return PromoLineImpactResult(
            impact_type=PromoImpactType.DISCOUNT,
            discount_amount=disc,
            notes=f"Fixed discount: {disc}",
        )

    elif rule.reward_type == RewardType.SPECIAL_PRICE:
        if matching_lines:
            orig = matching_lines[0].unit_price
            special = rule.reward_special_unit_price or orig
            disc = (orig - special) * total_qty
            return PromoLineImpactResult(
                impact_type=PromoImpactType.SPECIAL_PRICE,
                discount_amount=disc,
                notes=f"Special price: {special} per unit",
            )

    elif rule.reward_type == RewardType.BUNDLE_PRICE:
        disc = rule.reward_amount or Decimal(0)
        return PromoLineImpactResult(
            impact_type=PromoImpactType.BUNDLE_ADJUSTMENT,
            discount_amount=disc,
            notes=f"Bundle deal: {disc} off",
        )

    return PromoLineImpactResult(impact_type=PromoImpactType.DISCOUNT, discount_amount=Decimal(0))


def _build_order_level_impact(rule: PromoRuleLine, order_total: Decimal) -> PromoLineImpactResult:
    if rule.reward_type == RewardType.PERCENT_DISCOUNT:
        pct = rule.reward_percent or Decimal(0)
        return PromoLineImpactResult(
            impact_type=PromoImpactType.ORDER_DISCOUNT,
            discount_pct=pct,
            discount_amount=order_total * (pct / Decimal(100)),
            notes=f"{pct}% order-level discount",
        )
    elif rule.reward_type in (RewardType.FIXED_DISCOUNT, RewardType.BUNDLE_PRICE):
        disc = rule.reward_amount or Decimal(0)
        return PromoLineImpactResult(
            impact_type=PromoImpactType.ORDER_DISCOUNT,
            discount_amount=disc,
            notes=f"Fixed order discount: {disc}",
        )
    return PromoLineImpactResult(impact_type=PromoImpactType.ORDER_DISCOUNT, discount_amount=Decimal(0))


# ── Main Evaluation Engine ─────────────────────────────────────────────────────

async def evaluate_order(
    db: AsyncSession,
    sales_order_id,
    customer_id: Optional[str],
    channel: Optional[str],
    region: Optional[str],
    price_list_id: Optional[str],
    order_lines: List[OrderLineInput],
) -> EvaluateOrderResult:
    today = date.today()
    order_total = sum(l.line_total for l in order_lines)

    # Load all active schemes ordered by priority
    q = select(PromoScheme).options(
        selectinload(PromoScheme.eligibility_scopes),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.trigger_item),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.reward_item),
    ).where(
        PromoScheme.status == SchemeStatus.ACTIVE,
        PromoScheme.valid_from <= today,
        PromoScheme.valid_to >= today,
    ).order_by(PromoScheme.priority_rank)

    result = await db.execute(q)
    schemes = result.scalars().all()

    applied: List[PromoApplicationResult] = []
    skipped: List[Dict] = []
    exclusive_applied = False
    stack_seq = 1

    for scheme in schemes:
        # Skip if exclusive already applied
        if exclusive_applied and not scheme.stackable:
            skipped.append({"scheme_id": str(scheme.id), "reason": "Exclusive promo already applied"})
            continue

        # Check eligibility
        eligible = False
        for scope in scheme.eligibility_scopes:
            if _check_eligibility(scope, customer_id, channel, region, price_list_id, order_lines, order_total):
                eligible = True
                break
        # If no scopes defined, treat as open eligibility
        if not scheme.eligibility_scopes:
            eligible = True

        if not eligible:
            skipped.append({"scheme_id": str(scheme.id), "scheme_code": scheme.scheme_code, "reason": "Eligibility not met"})
            continue

        # Evaluate rules
        line_impacts: List[PromoLineImpactResult] = []
        for rule in scheme.rule_lines:
            impact = _evaluate_rule(rule, order_lines, order_total)
            if impact:
                rule_name = rule.reward_item.product_name if rule.reward_item else None
                impact.reward_item_name = rule_name
                line_impacts.append(impact)

        if not line_impacts:
            # Build next-threshold hint
            hint = None
            for rule in scheme.rule_lines:
                if rule.min_trigger_qty > 0:
                    total_match = sum(l.qty for l in order_lines if str(l.item_id) == str(rule.trigger_item_id or ""))
                    if total_match < rule.min_trigger_qty:
                        needed = rule.min_trigger_qty - total_match
                        hint = f"Add {needed} more units to unlock this promotion."
                        break
            skipped.append({
                "scheme_id": str(scheme.id),
                "scheme_code": scheme.scheme_code,
                "reason": "Trigger conditions not met",
                "next_threshold_hint": hint,
            })
            continue

        total_discount = sum((i.discount_amount or Decimal(0)) for i in line_impacts)
        total_free_value = sum(
            (i.discount_amount or Decimal(0)) for i in line_impacts if i.impact_type == PromoImpactType.FREE_GOODS
        )

        applied.append(PromoApplicationResult(
            scheme_id=scheme.id,
            scheme_code=scheme.scheme_code,
            scheme_name=scheme.scheme_name,
            application_type=PromoApplicationType.AUTO,
            calculated_benefit=total_discount,
            promo_cost_estimate=total_discount,
            stack_sequence=stack_seq,
            line_impacts=line_impacts,
        ))

        if scheme.exclusive:
            exclusive_applied = True
        stack_seq += 1

    total_discount = sum(p.calculated_benefit for p in applied)
    total_free_value = sum(
        sum((i.discount_amount or Decimal(0)) for i in p.line_impacts if i.impact_type == PromoImpactType.FREE_GOODS)
        for p in applied
    )

    return EvaluateOrderResult(
        sales_order_id=sales_order_id,
        applied_promos=applied,
        skipped_promos=skipped,
        total_discount=total_discount,
        total_free_goods_value=total_free_value,
        total_promo_cost=total_discount,
    )


async def save_order_promos(
    db: AsyncSession,
    sales_order_id,
    eval_result: EvaluateOrderResult,
) -> List[SalesOrderPromo]:
    # Remove old applications for this order
    old_q = select(SalesOrderPromo).where(SalesOrderPromo.sales_order_id == sales_order_id)
    old_result = await db.execute(old_q)
    for old in old_result.scalars().all():
        await db.delete(old)
    await db.flush()

    saved = []
    for promo_result in eval_result.applied_promos:
        sop = SalesOrderPromo(
            sales_order_id=sales_order_id,
            scheme_id=promo_result.scheme_id,
            application_type=promo_result.application_type,
            calculated_benefit_amount=promo_result.calculated_benefit,
            promo_cost_estimate=promo_result.promo_cost_estimate,
            stack_sequence=promo_result.stack_sequence,
        )
        db.add(sop)
        await db.flush()
        for impact in promo_result.line_impacts:
            line = SalesOrderPromoLine(
                order_promo_id=sop.id,
                impact_type=impact.impact_type,
                impacted_amount=impact.discount_amount,
                reward_item_id=impact.reward_item_id,
                reward_qty=impact.reward_qty,
                notes=impact.notes,
            )
            db.add(line)
        saved.append(sop)

    await db.commit()

    # Update tally
    month = date.today().strftime("%Y-%m")
    for promo_result in eval_result.applied_promos:
        tally_q = select(PromoUsageTally).where(
            PromoUsageTally.scheme_id == promo_result.scheme_id,
            PromoUsageTally.tally_month == month,
        )
        tally_result = await db.execute(tally_q)
        tally = tally_result.scalar_one_or_none()
        if not tally:
            tally = PromoUsageTally(scheme_id=promo_result.scheme_id, tally_month=month)
            db.add(tally)
            await db.flush()
        tally.order_count = (tally.order_count or 0) + 1
        tally.total_discount = (tally.total_discount or Decimal(0)) + promo_result.calculated_benefit
        tally.total_cost = (tally.total_cost or Decimal(0)) + promo_result.promo_cost_estimate

    await db.commit()
    return saved


async def get_order_promos(db: AsyncSession, sales_order_id) -> List[SalesOrderPromo]:
    q = select(SalesOrderPromo).options(
        selectinload(SalesOrderPromo.scheme),
        selectinload(SalesOrderPromo.line_impacts).selectinload(SalesOrderPromoLine.reward_item),
    ).where(SalesOrderPromo.sales_order_id == sales_order_id)
    result = await db.execute(q)
    promos = result.scalars().all()
    for p in promos:
        p.scheme_name = p.scheme.scheme_name if p.scheme else None
        p.scheme_code = p.scheme.scheme_code if p.scheme else None
        for l in p.line_impacts:
            l.reward_item_name = l.reward_item.product_name if l.reward_item else None
    return promos


# ── Override Requests ──────────────────────────────────────────────────────────

async def create_override_request(
    db: AsyncSession, data: OverrideRequestCreate, requested_by_id=None
) -> PromoOverrideRequest:
    obj = PromoOverrideRequest(**data.model_dump(), requested_by_id=requested_by_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_override_requests(db: AsyncSession, status: OverrideStatus = None):
    q = select(PromoOverrideRequest)
    if status:
        q = q.where(PromoOverrideRequest.status == status)
    result = await db.execute(q.order_by(PromoOverrideRequest.created_at.desc()))
    return result.scalars().all()


async def approve_override(
    db: AsyncSession, req_id, data: ApproveOverrideRequest, approver_id=None
) -> PromoOverrideRequest:
    obj = await db.get(PromoOverrideRequest, req_id)
    if not obj:
        raise ValueError("Override request not found")
    obj.status = OverrideStatus.APPROVED if data.approved else OverrideStatus.REJECTED
    obj.approved_by_id = approver_id
    obj.approver_notes = data.approver_notes
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Usage Report ──────────────────────────────────────────────────────────────

async def usage_report(db: AsyncSession):
    q = select(
        PromoScheme.id,
        PromoScheme.scheme_code,
        PromoScheme.scheme_name,
        PromoScheme.scheme_type,
        func.coalesce(func.sum(PromoUsageTally.order_count), 0).label("order_count"),
        func.coalesce(func.sum(PromoUsageTally.total_discount), 0).label("total_discount"),
        func.coalesce(func.sum(PromoUsageTally.total_free_value), 0).label("total_free_value"),
        func.coalesce(func.sum(PromoUsageTally.total_cost), 0).label("total_cost"),
    ).outerjoin(PromoUsageTally, PromoUsageTally.scheme_id == PromoScheme.id
    ).group_by(PromoScheme.id, PromoScheme.scheme_code, PromoScheme.scheme_name, PromoScheme.scheme_type
    ).order_by(func.sum(PromoUsageTally.total_cost).desc().nullslast())
    result = await db.execute(q)
    return result.all()


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def dashboard_summary(db: AsyncSession):
    today = date.today()
    soon = today + timedelta(days=30)
    month = today.strftime("%Y-%m")

    active = (await db.execute(
        select(func.count()).select_from(PromoScheme).where(
            PromoScheme.status == SchemeStatus.ACTIVE,
            PromoScheme.valid_from <= today,
            PromoScheme.valid_to >= today,
        )
    )).scalar()

    expiring = (await db.execute(
        select(func.count()).select_from(PromoScheme).where(
            PromoScheme.status == SchemeStatus.ACTIVE,
            PromoScheme.valid_to.between(today, soon),
        )
    )).scalar()

    tally_q = select(
        func.coalesce(func.sum(PromoUsageTally.order_count), 0),
        func.coalesce(func.sum(PromoUsageTally.total_discount), 0),
        func.coalesce(func.sum(PromoUsageTally.total_free_value), 0),
    ).where(PromoUsageTally.tally_month == month)
    tally_row = (await db.execute(tally_q)).one()

    pending_overrides = (await db.execute(
        select(func.count()).select_from(PromoOverrideRequest).where(PromoOverrideRequest.status == OverrideStatus.PENDING)
    )).scalar()

    pending_ai = (await db.execute(
        select(func.count()).select_from(PromoAIRecommendation).where(PromoAIRecommendation.status == PromoAIRecStatus.PENDING)
    )).scalar()

    return {
        "active_schemes": active,
        "expiring_soon": expiring,
        "total_applications_month": tally_row[0],
        "total_discount_month": tally_row[1],
        "total_free_value_month": tally_row[2],
        "pending_override_requests": pending_overrides,
        "pending_ai_recs": pending_ai,
    }


# ── AI Agents ──────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[PromoAIRecommendation]:
    created = []
    today = date.today()

    # Load schemes with tallies
    schemes_q = select(PromoScheme).options(selectinload(PromoScheme.rule_lines))
    schemes = (await db.execute(schemes_q)).scalars().all()
    tally_q = select(PromoUsageTally)
    tallies_by_scheme: Dict[str, List] = {}
    for t in (await db.execute(tally_q)).scalars().all():
        tallies_by_scheme.setdefault(str(t.scheme_id), []).append(t)

    # Agent 1: Conflict Advisor — overlapping exclusive schemes
    active_schemes = [s for s in schemes if s.status == SchemeStatus.ACTIVE and s.valid_from <= today <= s.valid_to]
    exclusive_schemes = [s for s in active_schemes if s.exclusive]
    if len(exclusive_schemes) > 1:
        rec = PromoAIRecommendation(
            agent_type=PromoAIAgentType.CONFLICT_ADVISOR,
            title=f"{len(exclusive_schemes)} exclusive schemes are active simultaneously",
            detail="Multiple exclusive schemes active at the same time will conflict during order evaluation. Only the highest-priority one will apply. Review and deactivate lower-priority schemes or adjust date ranges.",
            severity="warning",
        )
        db.add(rec)
        created.append(rec)

    # Agent 1b: schemes with no rule lines
    for s in schemes:
        if not s.rule_lines:
            rec = PromoAIRecommendation(
                agent_type=PromoAIAgentType.CONFLICT_ADVISOR,
                title=f"Scheme '{s.scheme_name}' has no rule lines and will never apply",
                detail="A promotional scheme with no evaluation rules cannot be triggered. Add trigger/reward rule lines.",
                severity="warning",
                scheme_id=s.id,
            )
            db.add(rec)
            created.append(rec)

    # Agent 2: Cost Monitor — high cost schemes
    for s in schemes:
        tallies = tallies_by_scheme.get(str(s.id), [])
        total_cost = sum(t.total_cost or Decimal(0) for t in tallies)
        total_orders = sum(t.order_count or 0 for t in tallies)
        if total_orders > 0 and total_cost > Decimal(100000):
            rec = PromoAIRecommendation(
                agent_type=PromoAIAgentType.COST_MONITOR,
                title=f"Scheme '{s.scheme_name}' has accumulated cost of KES {total_cost:,.0f}",
                detail=f"Applied to {total_orders} orders with total cost KES {total_cost:,.0f}. Review if this is within budget.",
                severity="info",
                scheme_id=s.id,
            )
            db.add(rec)
            created.append(rec)

    # Agent 2b: Expiring schemes
    soon = today + timedelta(days=7)
    for s in active_schemes:
        if s.valid_to <= soon:
            rec = PromoAIRecommendation(
                agent_type=PromoAIAgentType.COST_MONITOR,
                title=f"Scheme '{s.scheme_name}' expires in {(s.valid_to - today).days} days",
                detail=f"Valid until {s.valid_to}. Renew or archive this scheme before expiry to avoid confusion.",
                severity="warning",
                scheme_id=s.id,
            )
            db.add(rec)
            created.append(rec)

    # Agent 3: Upsell Assistant — schemes with zero applications
    for s in active_schemes:
        tallies = tallies_by_scheme.get(str(s.id), [])
        total_orders = sum(t.order_count or 0 for t in tallies)
        if total_orders == 0:
            rec = PromoAIRecommendation(
                agent_type=PromoAIAgentType.UPSELL_ASSISTANT,
                title=f"Active scheme '{s.scheme_name}' has zero applications",
                detail="This promotion has never been triggered. Check eligibility scopes, trigger conditions, and whether sales reps are aware of the promotion.",
                severity="info",
                scheme_id=s.id,
            )
            db.add(rec)
            created.append(rec)

    await db.commit()
    return created


async def list_ai_recs(db: AsyncSession, status: PromoAIRecStatus = None):
    q = select(PromoAIRecommendation)
    if status:
        q = q.where(PromoAIRecommendation.status == status)
    result = await db.execute(q.order_by(PromoAIRecommendation.created_at.desc()))
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id, status: PromoAIRecStatus) -> PromoAIRecommendation:
    rec = await db.get(PromoAIRecommendation, rec_id)
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = status
    await db.commit()
    await db.refresh(rec)
    return rec
