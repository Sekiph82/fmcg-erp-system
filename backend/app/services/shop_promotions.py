"""Promotions for one shop (owner 2026-11-20): every shop sees the same list price; promotions are separate, defined per
shop (or region / channel / for everyone) in the promotion engine (PromoScheme + eligibility). The shop sees its own
promotion table, and an order gets the promotions it qualifies for: percentage discounts are written on the order
lines (so the invoice shows list price, discount and final price) and every applied promotion is recorded on the order
(sales_order_promos) and named on the invoice.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload


def _scope_matches_customer(scope, customer) -> bool:
    if not scope.active:
        return False
    if scope.applies_to_customer_id and str(scope.applies_to_customer_id) != str(customer.id):
        return False
    if scope.applies_to_customer_group and scope.applies_to_customer_group != (customer.customer_group_id or ""):
        return False
    if scope.applies_to_region and scope.applies_to_region not in (customer.region, customer.sales_region_id):
        return False
    channel = customer.channel.value if getattr(customer, "channel", None) is not None else None
    if scope.applies_to_channel and scope.applies_to_channel != channel:
        return False
    return True


def describe_rule(rule) -> str:
    from app.models.promotions import RewardType

    on = (rule.trigger_item.name if rule.trigger_item is not None else None) or rule.trigger_category or rule.trigger_brand or "the order"
    cond = []
    if rule.min_trigger_qty and Decimal(rule.min_trigger_qty) > 0:
        cond.append(f"from {Decimal(rule.min_trigger_qty).normalize()} units")
    if rule.min_trigger_value and Decimal(rule.min_trigger_value) > 0:
        cond.append(f"from {Decimal(rule.min_trigger_value):.2f} value")
    when = f" ({', '.join(cond)})" if cond else ""
    if rule.reward_type == RewardType.PERCENT_DISCOUNT:
        return f"{Decimal(rule.reward_percent or 0).normalize()}% off {on}{when}"
    if rule.reward_type == RewardType.FIXED_DISCOUNT:
        return f"{Decimal(rule.reward_amount or 0):.2f} off {on}{when}"
    if rule.reward_type == RewardType.FREE_GOODS:
        gift = rule.reward_item.name if rule.reward_item is not None else on
        return f"{Decimal(rule.reward_qty or 1).normalize()} free {gift} with {on}{when}"
    if rule.reward_type == RewardType.SPECIAL_PRICE:
        return f"special price {Decimal(rule.reward_special_unit_price or 0):.2f} for {on}{when}"
    return f"bundle deal on {on}{when}"


async def _active_schemes(db):
    from datetime import date

    from app.models.promotions import PromoRuleLine, PromoScheme, SchemeStatus

    today = date.today()
    return (await db.execute(select(PromoScheme).options(
        selectinload(PromoScheme.eligibility_scopes),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.trigger_item),
        selectinload(PromoScheme.rule_lines).selectinload(PromoRuleLine.reward_item),
    ).where(PromoScheme.status == SchemeStatus.ACTIVE, PromoScheme.valid_from <= today, PromoScheme.valid_to >= today)
        .order_by(PromoScheme.priority_rank))).scalars().all()


async def customer_promotions(db, customer) -> list[dict]:
    """The shop's own promotion table: active schemes it is eligible for (customer, group, region, channel or open)."""
    out = []
    for s in await _active_schemes(db):
        if s.eligibility_scopes and not any(_scope_matches_customer(sc, customer) for sc in s.eligibility_scopes):
            continue
        out.append({"code": s.scheme_code, "name": s.scheme_name, "valid_from": str(s.valid_from), "valid_to": str(s.valid_to),
                    "only_for_you": any(sc.applies_to_customer_id for sc in s.eligibility_scopes),
                    "offers": [describe_rule(r) for r in sorted(s.rule_lines, key=lambda r: r.sort_order or 0)]})
    return out


async def apply_to_order(db, so, customer) -> list[str]:
    """Evaluate the order's promotions; write percentage discounts on the lines; record the applications.
    Returns the applied promotion names (for the confirmation / invoice). Caller commits."""
    from app.models.promotions import (PromoImpactType, RewardType, SalesOrderPromo, SalesOrderPromoLine, TriggerBasis)
    from app.models.sales import SOLine
    from app.schemas.promotions import OrderLineInput
    from app.services.promotions_service import _check_eligibility, _evaluate_rule

    lines = (await db.execute(select(SOLine).options(selectinload(SOLine.product)).where(SOLine.so_id == so.id))).scalars().all()
    if not lines:
        return []
    inputs = {l.id: OrderLineInput(line_id=str(l.id), item_id=l.product_id,
                                   item_category=l.product.category.value if l.product and l.product.category else None,
                                   qty=Decimal(l.ordered_quantity), unit_price=Decimal(l.unit_price),
                                   line_total=Decimal(l.ordered_quantity) * Decimal(l.unit_price)) for l in lines}
    order_lines = list(inputs.values())
    total = sum((i.line_total for i in order_lines), Decimal("0"))
    channel = customer.channel.value if getattr(customer, "channel", None) is not None else None
    applied, exclusive_done, seq = [], False, 1
    for scheme in await _active_schemes(db):
        if exclusive_done and not scheme.stackable:
            continue
        if scheme.eligibility_scopes and not any(
                _scope_matches_customer(sc, customer)
                and _check_eligibility(sc, str(customer.id), channel, sc.applies_to_region, None, order_lines, total)
                for sc in scheme.eligibility_scopes):
            continue
        benefit, impacts = Decimal("0"), []
        for rule in scheme.rule_lines:
            impact = _evaluate_rule(rule, order_lines, total)
            if impact is None:
                continue
            if rule.reward_type == RewardType.PERCENT_DISCOUNT and rule.reward_percent:
                pct = Decimal(rule.reward_percent) / 100
                for l in lines:
                    i = inputs[l.id]
                    hit = (rule.trigger_basis in (TriggerBasis.ORDER_TOTAL, TriggerBasis.VALUE, TriggerBasis.QUANTITY, TriggerBasis.MIX_SET)
                           or (rule.trigger_basis == TriggerBasis.SKU and str(i.item_id) == str(rule.trigger_item_id))
                           or (rule.trigger_basis == TriggerBasis.CATEGORY and i.item_category == rule.trigger_category))
                    if hit:  # stacked percentages compound on the line
                        l.discount_pct = (1 - (1 - Decimal(l.discount_pct or 0)) * (1 - pct)).quantize(Decimal("0.0001"))
            benefit += Decimal(impact.discount_amount or 0)
            impacts.append((rule, impact))
        if not impacts:
            continue
        sop = SalesOrderPromo(sales_order_id=so.id, scheme_id=scheme.id, calculated_benefit_amount=benefit.quantize(Decimal("0.01")),
                              promo_cost_estimate=benefit.quantize(Decimal("0.01")), stack_sequence=seq)
        db.add(sop)
        await db.flush()
        for rule, impact in impacts:
            db.add(SalesOrderPromoLine(order_promo_id=sop.id, source_rule_id=rule.id, impact_type=impact.impact_type or PromoImpactType.DISCOUNT,
                                       impacted_amount=impact.discount_amount, reward_item_id=impact.reward_item_id,
                                       reward_qty=impact.reward_qty, notes=describe_rule(rule)))
        applied.append(f"{scheme.scheme_name}: " + "; ".join(describe_rule(r) for r, _ in impacts))
        exclusive_done = exclusive_done or bool(scheme.exclusive)
        seq += 1
    await db.flush()
    return applied


async def order_promotion_names(db, so_id) -> list[str]:
    from app.models.promotions import SalesOrderPromo

    rows = (await db.execute(select(SalesOrderPromo).options(selectinload(SalesOrderPromo.scheme), selectinload(SalesOrderPromo.line_impacts))
                             .where(SalesOrderPromo.sales_order_id == so_id).order_by(SalesOrderPromo.stack_sequence))).scalars().all()
    return [f"{r.scheme.scheme_name}: " + "; ".join(filter(None, (i.notes for i in r.line_impacts))) for r in rows]
