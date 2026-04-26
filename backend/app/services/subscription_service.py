"""Subscription / Recurring Orders service — recurrence engine + order generation."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subscription import (
    SubscriptionTemplate, SubscriptionLine,
    SubscriptionGenerationLog, SubscriptionPauseSkip,
    SubAIRecommendation,
    RecurrenceType, SubscriptionStatus, GenerationMode,
    GenerationStatus, PauseSkipAction,
    SubAIAgentType, SubAIRecStatus,
)
from app.models.sales import SalesOrder, SOLine, Customer
from app.models.master import Product
from app.schemas.subscription import (
    SubscriptionTemplateCreate, SubscriptionTemplateUpdate,
    PauseSkipCreate, GenerateNowRequest, SubAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _next_date_weekly(current: date, interval_weeks: int = 1) -> date:
    return current + timedelta(weeks=interval_weeks)


def _next_date_monthly_day(current: date, day_of_month: int) -> date:
    import calendar
    month = current.month + 1
    year = current.year
    if month > 12:
        month = 1
        year += 1
    max_day = calendar.monthrange(year, month)[1]
    d = min(day_of_month, max_day)
    return date(year, month, d)


def _next_date_monthly_weekday(current: date, weekday: int, ordinal: int) -> date:
    import calendar
    month = current.month + 1
    year = current.year
    if month > 12:
        month = 1
        year += 1
    cal = calendar.monthcalendar(year, month)
    days = [week[weekday] for week in cal if week[weekday] != 0]
    if ordinal == -1:
        return date(year, month, days[-1])
    idx = min(ordinal - 1, len(days) - 1)
    return date(year, month, days[idx])


def _calculate_next_generation_date(template: SubscriptionTemplate, from_date: date) -> Optional[date]:
    rt = template.recurrence_type
    if rt == RecurrenceType.WEEKLY:
        return _next_date_weekly(from_date, 1)
    if rt == RecurrenceType.BIWEEKLY:
        return _next_date_weekly(from_date, 2)
    if rt == RecurrenceType.MONTHLY_DATE:
        dom = template.recurrence_day_of_month or 1
        return _next_date_monthly_day(from_date, dom)
    if rt == RecurrenceType.MONTHLY_DAY:
        wd = template.recurrence_weekday or 0
        ord_ = template.recurrence_week_ordinal or 1
        return _next_date_monthly_weekday(from_date, wd, ord_)
    if rt == RecurrenceType.CUSTOM_DAYS:
        interval = template.recurrence_interval or 30
        return from_date + timedelta(days=interval)
    if rt == RecurrenceType.ROUTE_BASED:
        # Route-based: advance by 7 days as default; route schedule integration handled externally
        return from_date + timedelta(days=7)
    return None


async def _is_paused_on(db: AsyncSession, template_id: uuid.UUID, target_date: date) -> bool:
    q = await db.execute(
        select(SubscriptionPauseSkip).where(
            SubscriptionPauseSkip.template_id == template_id,
            SubscriptionPauseSkip.action_type == PauseSkipAction.PAUSE.value,
            SubscriptionPauseSkip.effective_from <= target_date,
            or_(
                SubscriptionPauseSkip.effective_to == None,
                SubscriptionPauseSkip.effective_to >= target_date,
            ),
        )
    )
    return q.scalars().first() is not None


async def _has_skip_for_date(db: AsyncSession, template_id: uuid.UUID, target_date: date) -> bool:
    q = await db.execute(
        select(SubscriptionPauseSkip).where(
            SubscriptionPauseSkip.template_id == template_id,
            SubscriptionPauseSkip.action_type == PauseSkipAction.SKIP_ONE_CYCLE.value,
            SubscriptionPauseSkip.effective_from == target_date,
        )
    )
    return q.scalars().first() is not None


async def _already_generated(db: AsyncSession, template_id: uuid.UUID, scheduled_date: date) -> bool:
    q = await db.execute(
        select(SubscriptionGenerationLog).where(
            SubscriptionGenerationLog.template_id == template_id,
            SubscriptionGenerationLog.scheduled_date == scheduled_date,
            SubscriptionGenerationLog.generation_status == GenerationStatus.GENERATED.value,
        )
    )
    return q.scalars().first() is not None


# ── Validation ────────────────────────────────────────────────────────────────

async def _validate_before_generation(
    db: AsyncSession, template: SubscriptionTemplate, target_date: date
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    customer = await db.get(Customer, template.customer_id)
    if not customer:
        errors.append("Customer not found")
    elif not getattr(customer, "is_active", True):
        errors.append("Customer is inactive")
    elif getattr(customer, "credit_hold", False):
        errors.append("Customer is on credit hold")

    if template.end_date and target_date > template.end_date:
        errors.append(f"Template expired on {template.end_date}")

    for line in template.lines:
        if not line.active_flag:
            continue
        product = await db.get(Product, line.item_id)
        if not product:
            errors.append(f"Item {line.item_id} not found")
        elif not getattr(product, "is_active", True):
            errors.append(f"Item {getattr(product, 'name', line.item_id)} is inactive")

    if await _already_generated(db, template.id, target_date):
        errors.append(f"Order already generated for {target_date}")

    if await _is_paused_on(db, template.id, target_date):
        errors.append("Template is paused on this date")

    if await _has_skip_for_date(db, template.id, target_date):
        errors.append("Cycle is marked for skip on this date")

    return len(errors) == 0, errors, warnings


# ── Core CRUD ─────────────────────────────────────────────────────────────────

async def list_templates(
    db: AsyncSession,
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[SubscriptionTemplate]:
    q = select(SubscriptionTemplate).options(selectinload(SubscriptionTemplate.lines))
    if customer_id:
        q = q.where(SubscriptionTemplate.customer_id == customer_id)
    if status:
        q = q.where(SubscriptionTemplate.status == status)
    q = q.order_by(SubscriptionTemplate.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> Optional[SubscriptionTemplate]:
    q = select(SubscriptionTemplate).options(
        selectinload(SubscriptionTemplate.lines),
        selectinload(SubscriptionTemplate.generation_logs),
        selectinload(SubscriptionTemplate.pause_skips),
    ).where(SubscriptionTemplate.id == template_id)
    result = await db.execute(q)
    return result.scalars().first()


async def create_template(
    db: AsyncSession, payload: SubscriptionTemplateCreate, user_id: Optional[uuid.UUID]
) -> SubscriptionTemplate:
    t = SubscriptionTemplate(
        template_code=payload.template_code,
        template_name=payload.template_name,
        customer_id=payload.customer_id,
        distributor_id=payload.distributor_id,
        price_list_id=payload.price_list_id,
        contract_id=payload.contract_id,
        currency=payload.currency,
        recurrence_type=payload.recurrence_type,
        recurrence_interval=payload.recurrence_interval,
        recurrence_day_of_month=payload.recurrence_day_of_month,
        recurrence_weekday=payload.recurrence_weekday,
        recurrence_week_ordinal=payload.recurrence_week_ordinal,
        start_date=payload.start_date,
        end_date=payload.end_date,
        next_generation_date=payload.next_generation_date or payload.start_date,
        status=SubscriptionStatus.DRAFT.value,
        generation_mode=payload.generation_mode,
        delivery_address_id=payload.delivery_address_id,
        route_id=payload.route_id,
        payment_terms_id=payload.payment_terms_id,
        allow_promotion_eval=payload.allow_promotion_eval,
        price_change_threshold_pct=payload.price_change_threshold_pct,
        notes=payload.notes,
        created_by=user_id,
    )
    db.add(t)
    await db.flush()

    for lp in payload.lines:
        line = SubscriptionLine(
            template_id=t.id,
            item_id=lp.item_id,
            item_variant_id=lp.item_variant_id,
            uom=lp.uom,
            quantity=lp.quantity,
            min_quantity=lp.min_quantity,
            max_quantity=lp.max_quantity,
            allow_quantity_change=lp.allow_quantity_change,
            price_source=lp.price_source,
            fixed_price=lp.fixed_price,
            active_flag=lp.active_flag,
            sort_order=lp.sort_order,
            notes=lp.notes,
        )
        db.add(line)

    await db.commit()
    await db.refresh(t)
    return t


async def update_template(
    db: AsyncSession, template: SubscriptionTemplate, payload: SubscriptionTemplateUpdate
) -> SubscriptionTemplate:
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return template


# ── Status transitions ────────────────────────────────────────────────────────

async def activate_template(
    db: AsyncSession, template: SubscriptionTemplate, user_id: Optional[uuid.UUID]
) -> SubscriptionTemplate:
    template.status = SubscriptionStatus.ACTIVE.value
    template.approved_by = user_id
    if not template.next_generation_date:
        template.next_generation_date = template.start_date
    await db.commit()
    await db.refresh(template)
    return template


async def cancel_template(db: AsyncSession, template: SubscriptionTemplate) -> SubscriptionTemplate:
    template.status = SubscriptionStatus.CANCELLED.value
    await db.commit()
    await db.refresh(template)
    return template


async def archive_template(db: AsyncSession, template: SubscriptionTemplate) -> SubscriptionTemplate:
    template.status = SubscriptionStatus.ARCHIVED.value
    await db.commit()
    await db.refresh(template)
    return template


# ── Pause / Skip / Resume ─────────────────────────────────────────────────────

async def add_pause_skip(
    db: AsyncSession,
    template: SubscriptionTemplate,
    payload: PauseSkipCreate,
    user_id: Optional[uuid.UUID],
) -> SubscriptionPauseSkip:
    ps = SubscriptionPauseSkip(
        template_id=template.id,
        action_type=payload.action_type,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        reason=payload.reason,
        requested_by=user_id,
        portal_request=payload.portal_request,
        notes=payload.notes,
    )
    db.add(ps)

    if payload.action_type == PauseSkipAction.PAUSE.value:
        template.status = SubscriptionStatus.PAUSED.value
    elif payload.action_type == PauseSkipAction.RESUME.value:
        template.status = SubscriptionStatus.ACTIVE.value
    elif payload.action_type == PauseSkipAction.CANCEL.value:
        template.status = SubscriptionStatus.CANCELLED.value

    await db.commit()
    await db.refresh(ps)
    return ps


async def list_pause_skips(
    db: AsyncSession, template_id: uuid.UUID
) -> List[SubscriptionPauseSkip]:
    q = await db.execute(
        select(SubscriptionPauseSkip)
        .where(SubscriptionPauseSkip.template_id == template_id)
        .order_by(SubscriptionPauseSkip.created_at.desc())
    )
    return q.scalars().all()


# ── Order generation ──────────────────────────────────────────────────────────

async def generate_order(
    db: AsyncSession,
    template: SubscriptionTemplate,
    target_date: date,
    req: Optional[GenerateNowRequest],
    user_id: Optional[uuid.UUID],
    system_initiated: bool = True,
) -> SubscriptionGenerationLog:
    ok, errors, warnings = await _validate_before_generation(db, template, target_date)

    if not ok and not (req and req.force):
        log = SubscriptionGenerationLog(
            template_id=template.id,
            scheduled_date=target_date,
            actual_generation_date=datetime.utcnow(),
            generation_status=GenerationStatus.FAILED.value,
            failure_reason="; ".join(errors),
            validation_warnings=warnings or None,
            generated_by_system=system_initiated,
            generated_by_user_id=user_id,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    so_status = {
        GenerationMode.DRAFT_ONLY.value: "DRAFT",
        GenerationMode.APPROVAL_REQUIRED.value: "PENDING_APPROVAL",
        GenerationMode.AUTO_CONFIRM.value: "CONFIRMED",
    }.get(template.generation_mode, "DRAFT")

    so = SalesOrder(
        customer_id=template.customer_id,
        status=so_status,
        notes=f"Auto-generated from subscription {template.template_code}",
    )
    db.add(so)
    await db.flush()

    for line in template.lines:
        if not line.active_flag:
            continue
        so_line = SOLine(
            so_id=so.id,
            product_id=line.item_id,
            ordered_quantity=line.quantity,
            unit_price=line.fixed_price or Decimal("0"),
            uom=line.uom,
        )
        db.add(so_line)

    gen_status = (
        GenerationStatus.PENDING_APPROVAL.value
        if template.generation_mode == GenerationMode.APPROVAL_REQUIRED.value
        else GenerationStatus.GENERATED.value
    )

    log = SubscriptionGenerationLog(
        template_id=template.id,
        generated_so_id=so.id,
        scheduled_date=target_date,
        actual_generation_date=datetime.utcnow(),
        generation_status=gen_status,
        validation_warnings=warnings or None,
        generated_by_system=system_initiated,
        generated_by_user_id=user_id,
        notes=req.notes if req else None,
    )
    db.add(log)

    next_date = _calculate_next_generation_date(template, target_date)
    template.last_generation_date = target_date
    template.next_generation_date = next_date

    await db.commit()
    await db.refresh(log)
    return log


async def get_generation_log(
    db: AsyncSession, template_id: uuid.UUID, skip: int = 0, limit: int = 50
) -> List[SubscriptionGenerationLog]:
    q = await db.execute(
        select(SubscriptionGenerationLog)
        .where(SubscriptionGenerationLog.template_id == template_id)
        .order_by(SubscriptionGenerationLog.scheduled_date.desc())
        .offset(skip).limit(limit)
    )
    return q.scalars().all()


# ── Scheduler run (call from cron/background task) ───────────────────────────

async def run_scheduled_generation(db: AsyncSession) -> Dict[str, Any]:
    today = date.today()
    q = await db.execute(
        select(SubscriptionTemplate).options(selectinload(SubscriptionTemplate.lines)).where(
            SubscriptionTemplate.status == SubscriptionStatus.ACTIVE.value,
            SubscriptionTemplate.next_generation_date <= today,
            or_(
                SubscriptionTemplate.end_date == None,
                SubscriptionTemplate.end_date >= today,
            ),
        )
    )
    templates = q.scalars().all()

    results = {"generated": 0, "skipped": 0, "failed": 0}
    for tmpl in templates:
        target = tmpl.next_generation_date or today
        log = await generate_order(db, tmpl, target, None, None, system_initiated=True)
        if log.generation_status == GenerationStatus.GENERATED.value:
            results["generated"] += 1
        elif log.generation_status == GenerationStatus.FAILED.value:
            results["failed"] += 1
        else:
            results["skipped"] += 1

    return results


# ── Upcoming demand ───────────────────────────────────────────────────────────

async def get_upcoming_demand(
    db: AsyncSession, from_date: date, to_date: date
) -> List[Dict]:
    q = await db.execute(
        select(SubscriptionTemplate).options(selectinload(SubscriptionTemplate.lines)).where(
            SubscriptionTemplate.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    templates = q.scalars().all()

    demand: list[dict] = []
    for tmpl in templates:
        next_d = tmpl.next_generation_date
        if not next_d:
            continue
        if next_d < from_date or next_d > to_date:
            continue
        for line in tmpl.lines:
            if not line.active_flag:
                continue
            demand.append({
                "template_id": str(tmpl.id),
                "template_code": tmpl.template_code,
                "customer_id": str(tmpl.customer_id),
                "item_id": str(line.item_id),
                "uom": line.uom,
                "quantity": float(line.quantity),
                "scheduled_date": str(next_d),
            })
    return demand


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_templates(db: AsyncSession) -> Dict:
    total = (await db.execute(select(func.count()).select_from(SubscriptionTemplate))).scalar_one()
    active = (await db.execute(select(func.count()).select_from(SubscriptionTemplate).where(
        SubscriptionTemplate.status == SubscriptionStatus.ACTIVE.value))).scalar_one()
    paused = (await db.execute(select(func.count()).select_from(SubscriptionTemplate).where(
        SubscriptionTemplate.status == SubscriptionStatus.PAUSED.value))).scalar_one()
    expired = (await db.execute(select(func.count()).select_from(SubscriptionTemplate).where(
        SubscriptionTemplate.status == SubscriptionStatus.EXPIRED.value))).scalar_one()
    return {"total": total, "active": active, "paused": paused, "expired": expired}


async def report_generation(db: AsyncSession, days: int = 30) -> List[Dict]:
    cutoff = date.today() - timedelta(days=days)
    q = await db.execute(
        select(
            SubscriptionGenerationLog.generation_status,
            func.count().label("count"),
        )
        .where(SubscriptionGenerationLog.scheduled_date >= cutoff)
        .group_by(SubscriptionGenerationLog.generation_status)
    )
    return [{"status": r.generation_status, "count": r.count} for r in q.all()]


async def report_failed(db: AsyncSession, days: int = 30) -> List[SubscriptionGenerationLog]:
    cutoff = date.today() - timedelta(days=days)
    q = await db.execute(
        select(SubscriptionGenerationLog).where(
            SubscriptionGenerationLog.generation_status == GenerationStatus.FAILED.value,
            SubscriptionGenerationLog.scheduled_date >= cutoff,
        ).order_by(SubscriptionGenerationLog.scheduled_date.desc())
    )
    return q.scalars().all()


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[SubAIRecommendation]:
    recs: list[SubAIRecommendation] = []

    # Agent 1 — Demand Predictor
    q = await db.execute(
        select(SubscriptionTemplate).where(
            SubscriptionTemplate.status == SubscriptionStatus.ACTIVE.value
        )
    )
    active_templates = q.scalars().all()

    if active_templates:
        rec = SubAIRecommendation(
            agent_type=SubAIAgentType.DEMAND_PREDICTOR.value,
            status=SubAIRecStatus.PENDING.value,
            severity="INFO",
            title=f"Recurring Demand Baseline: {len(active_templates)} active templates",
            body=(
                f"There are {len(active_templates)} active recurring order templates feeding into MRP. "
                "These represent confirmed baseline demand. Ensure MRP run includes recurring order "
                "demand for the next 4 weeks."
            ),
            data={"active_template_count": len(active_templates)},
        )
        db.add(rec)
        recs.append(rec)

    # Agent 2 — Risk Monitor: templates with recent failures
    cutoff = date.today() - timedelta(days=14)
    fail_q = await db.execute(
        select(SubscriptionGenerationLog.template_id, func.count().label("fail_count"))
        .where(
            SubscriptionGenerationLog.generation_status == GenerationStatus.FAILED.value,
            SubscriptionGenerationLog.scheduled_date >= cutoff,
        )
        .group_by(SubscriptionGenerationLog.template_id)
        .having(func.count() >= 2)
    )
    risky = fail_q.all()

    for row in risky:
        rec = SubAIRecommendation(
            agent_type=SubAIAgentType.RISK_MONITOR.value,
            status=SubAIRecStatus.PENDING.value,
            severity="WARNING",
            template_id=row.template_id,
            title=f"Recurring order template has {row.fail_count} failures in 14 days",
            body=(
                f"Template has failed to generate orders {row.fail_count} times in the last 14 days. "
                "Review customer credit hold, item availability, and price list validity."
            ),
            data={"fail_count": row.fail_count, "window_days": 14},
        )
        db.add(rec)
        recs.append(rec)

    # Agent 3 — Optimization: templates with no generation in 45 days
    stale_cutoff = date.today() - timedelta(days=45)
    stale_q = await db.execute(
        select(SubscriptionTemplate).where(
            SubscriptionTemplate.status == SubscriptionStatus.ACTIVE.value,
            or_(
                SubscriptionTemplate.last_generation_date == None,
                SubscriptionTemplate.last_generation_date < stale_cutoff,
            ),
        )
    )
    stale_templates = stale_q.scalars().all()

    for tmpl in stale_templates:
        rec = SubAIRecommendation(
            agent_type=SubAIAgentType.OPTIMIZATION_ASSISTANT.value,
            status=SubAIRecStatus.PENDING.value,
            severity="WARNING",
            template_id=tmpl.id,
            customer_id=tmpl.customer_id,
            title=f"Active subscription '{tmpl.template_code}' has not generated for 45+ days",
            body=(
                f"Subscription template '{tmpl.template_name}' is active but has not generated an order "
                "in over 45 days. Consider reviewing the recurrence settings, pausing, or cancelling "
                "if the customer no longer requires this recurring supply."
            ),
            data={"last_generation_date": str(tmpl.last_generation_date)},
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        await db.commit()
    return recs


async def list_ai_recs(
    db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None
) -> List[SubAIRecommendation]:
    q = select(SubAIRecommendation)
    if agent_type:
        q = q.where(SubAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(SubAIRecommendation.status == status)
    result = await db.execute(q.order_by(SubAIRecommendation.created_at.desc()).limit(100))
    return result.scalars().all()


async def ack_ai_rec(
    db: AsyncSession, rec_id: uuid.UUID, payload: SubAIRecAck
) -> Optional[SubAIRecommendation]:
    rec = await db.get(SubAIRecommendation, rec_id)
    if rec:
        rec.status = payload.status
        await db.commit()
        await db.refresh(rec)
    return rec
