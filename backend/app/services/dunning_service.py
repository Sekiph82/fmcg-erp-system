from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dunning import (
    DunningPolicy, DunningLevel, DunningTemplate, DunningCase,
    DunningCaseInvoice, DunningActionLog, DunningPTP, DunningException,
    DunningAIRecommendation,
    DunningActionType, DunningCaseStatus, DunningActionOutcome,
    PTPStatus, DunningExceptionType, DunningAIAgentType, DunningAIRecStatus,
)
from app.models.sales import Invoice, InvoiceStatus, Customer
from app.schemas.dunning import (
    DunningPolicyCreate, DunningPolicyUpdate,
    DunningLevelCreate, DunningTemplateCreate,
    DunningCaseNoteUpdate, DunningCaseAssign,
    DunningDisputeSet, DunningReminderRequest, DunningManualNote,
    DunningPTPCreate, DunningPTPUpdate,
    DunningExceptionCreate,
    CreditHoldApply, CreditHoldRelease,
    DunningAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return date.today()


async def _next_case_no(db: AsyncSession) -> str:
    n = (await db.execute(select(func.count(DunningCase.id)))).scalar() or 0
    return f"DUN-{n + 1:06d}"


def _days_overdue(due: date) -> int:
    delta = (_today() - due).days
    return max(0, delta)


def _compute_priority(total_overdue: Decimal, oldest_due: Optional[date], broken_ptps: int) -> int:
    score = 0
    score += min(int(total_overdue / 10000), 40)
    if oldest_due:
        age = _days_overdue(oldest_due)
        score += min(age, 40)
    score += min(broken_ptps * 10, 20)
    return min(score, 100)


def _render_template(template: Optional[DunningTemplate], case: DunningCase, customer: Customer) -> tuple[str, str]:
    if not template:
        subject = f"Payment Reminder — Outstanding Balance"
        body = (
            f"Dear {customer.name},\n\n"
            f"This is a reminder that you have an outstanding overdue balance of "
            f"{case.total_overdue_amount:,.2f}. "
            f"Please arrange payment at your earliest convenience.\n\n"
            f"Thank you."
        )
        return subject, body
    subject = template.subject.replace("{{customer_name}}", customer.name)
    body = (
        template.body_text
        .replace("{{customer_name}}", customer.name)
        .replace("{{overdue_amount}}", f"{case.total_overdue_amount:,.2f}")
        .replace("{{oldest_due_date}}", str(case.oldest_due_date or ""))
        .replace("{{case_no}}", case.case_no)
    )
    return subject, body


# ── Policy CRUD ───────────────────────────────────────────────────────────────

async def create_policy(db: AsyncSession, payload: DunningPolicyCreate) -> DunningPolicy:
    pol = DunningPolicy(**payload.model_dump())
    db.add(pol)
    await db.flush()
    await db.refresh(pol)
    return pol


async def list_policies(db: AsyncSession, active_only: bool = False) -> List[DunningPolicy]:
    q = select(DunningPolicy)
    if active_only:
        q = q.where(DunningPolicy.active_flag == True)
    return list((await db.execute(q.order_by(DunningPolicy.created_at.desc()))).scalars())


async def get_policy(db: AsyncSession, policy_id: uuid.UUID) -> Optional[DunningPolicy]:
    return (await db.execute(select(DunningPolicy).where(DunningPolicy.id == policy_id))).scalar_one_or_none()


async def update_policy(db: AsyncSession, policy_id: uuid.UUID, payload: DunningPolicyUpdate) -> Optional[DunningPolicy]:
    pol = await get_policy(db, policy_id)
    if not pol:
        return None
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(pol, k, v)
    await db.flush()
    await db.refresh(pol)
    return pol


async def add_level(db: AsyncSession, policy_id: uuid.UUID, payload: DunningLevelCreate) -> DunningLevel:
    level = DunningLevel(policy_id=policy_id, **payload.model_dump())
    db.add(level)
    await db.flush()
    await db.refresh(level)
    return level


async def list_levels(db: AsyncSession, policy_id: uuid.UUID) -> List[DunningLevel]:
    rows = await db.execute(
        select(DunningLevel).where(DunningLevel.policy_id == policy_id).order_by(DunningLevel.level_no)
    )
    return list(rows.scalars())


# ── Template CRUD ─────────────────────────────────────────────────────────────

async def create_template(db: AsyncSession, payload: DunningTemplateCreate) -> DunningTemplate:
    tmpl = DunningTemplate(**payload.model_dump())
    db.add(tmpl)
    await db.flush()
    await db.refresh(tmpl)
    return tmpl


async def list_templates(db: AsyncSession) -> List[DunningTemplate]:
    rows = await db.execute(select(DunningTemplate).where(DunningTemplate.active_flag == True))
    return list(rows.scalars())


async def _get_template(db: AsyncSession, code: Optional[str], channel: DunningActionType) -> Optional[DunningTemplate]:
    if not code:
        return None
    row = await db.execute(
        select(DunningTemplate).where(
            DunningTemplate.template_code == code,
            DunningTemplate.channel == channel,
            DunningTemplate.active_flag == True,
        ).limit(1)
    )
    return row.scalar_one_or_none()


# ── Policy Resolution ─────────────────────────────────────────────────────────

async def resolve_policy(db: AsyncSession, customer: Customer) -> Optional[DunningPolicy]:
    # Priority: customer-specific → segment → channel → region/country → default
    checks = [
        and_(DunningPolicy.applies_to_customer_id == customer.id, DunningPolicy.active_flag == True),
        and_(DunningPolicy.applies_to_segment == customer.segment, DunningPolicy.active_flag == True, DunningPolicy.applies_to_segment != None),
        and_(DunningPolicy.applies_to_channel == customer.channel.value, DunningPolicy.active_flag == True, DunningPolicy.applies_to_channel != None),
        and_(DunningPolicy.applies_to_country == customer.country, DunningPolicy.active_flag == True, DunningPolicy.applies_to_country != None),
        and_(DunningPolicy.default_flag == True, DunningPolicy.active_flag == True),
    ]
    for cond in checks:
        row = (await db.execute(select(DunningPolicy).where(cond).limit(1))).scalar_one_or_none()
        if row:
            return row
    return None


async def _resolve_level(db: AsyncSession, policy_id: uuid.UUID, days_overdue: int) -> Optional[DunningLevel]:
    rows = await db.execute(
        select(DunningLevel).where(
            DunningLevel.policy_id == policy_id,
            DunningLevel.active_flag == True,
            DunningLevel.days_overdue_from <= days_overdue,
        ).order_by(DunningLevel.days_overdue_from.desc()).limit(1)
    )
    return rows.scalar_one_or_none()


# ── Overdue Detection ─────────────────────────────────────────────────────────

async def detect_overdue_invoices(db: AsyncSession) -> List[dict]:
    today = _today()
    rows = await db.execute(
        select(Invoice).where(
            Invoice.due_date < today,
            Invoice.status.in_(["ISSUED", "SENT", "OVERDUE", "PARTIAL"]),
        ).order_by(Invoice.due_date)
    )
    result = []
    for inv in rows.scalars():
        balance = float(inv.total_amount - inv.paid_amount)
        if balance <= 0:
            continue
        result.append({
            "invoice_id": str(inv.id),
            "invoice_no": inv.invoice_no,
            "customer_id": str(inv.customer_id),
            "due_date": inv.due_date,
            "balance": Decimal(str(balance)),
            "days_overdue": _days_overdue(inv.due_date),
        })
    return result


async def run_overdue_detection(db: AsyncSession) -> dict:
    overdue = await detect_overdue_invoices(db)
    by_customer: dict[str, list] = {}
    for item in overdue:
        cid = item["customer_id"]
        by_customer.setdefault(cid, []).append(item)

    created, updated = 0, 0
    for cid, items in by_customer.items():
        customer_uuid = uuid.UUID(cid)
        customer = (await db.execute(select(Customer).where(Customer.id == customer_uuid))).scalar_one_or_none()
        if not customer:
            continue

        policy = await resolve_policy(db, customer)

        # Find or create open case for this customer
        existing_case = (await db.execute(
            select(DunningCase).where(
                DunningCase.customer_id == customer_uuid,
                DunningCase.case_status.in_([DunningCaseStatus.OPEN, DunningCaseStatus.PROMISE_TO_PAY, DunningCaseStatus.ESCALATED]),
            ).limit(1)
        )).scalar_one_or_none()

        total_overdue = sum(i["balance"] for i in items)
        oldest_due = min(i["due_date"] for i in items)
        max_days = max(i["days_overdue"] for i in items)

        if existing_case:
            existing_case.total_overdue_amount = total_overdue
            existing_case.oldest_due_date = oldest_due
            if policy:
                existing_case.policy_id = policy.id
            updated += 1
            dc = existing_case
        else:
            dc = DunningCase(
                case_no=await _next_case_no(db),
                customer_id=customer_uuid,
                policy_id=policy.id if policy else None,
                case_status=DunningCaseStatus.OPEN,
                total_overdue_amount=total_overdue,
                oldest_due_date=oldest_due,
            )
            db.add(dc)
            await db.flush()
            created += 1

        # Sync invoice links
        for item in items:
            inv_uuid = uuid.UUID(item["invoice_id"])
            link = (await db.execute(
                select(DunningCaseInvoice).where(
                    DunningCaseInvoice.case_id == dc.id,
                    DunningCaseInvoice.invoice_id == inv_uuid,
                )
            )).scalar_one_or_none()
            if not link:
                link = DunningCaseInvoice(
                    case_id=dc.id,
                    invoice_id=inv_uuid,
                    invoice_number=item["invoice_no"],
                    invoice_due_date=item["due_date"],
                    invoice_balance_amount=item["balance"],
                    days_overdue=item["days_overdue"],
                )
                db.add(link)
            else:
                link.invoice_balance_amount = item["balance"]
                link.days_overdue = item["days_overdue"]

        # Determine credit hold from policy
        if policy and policy.auto_credit_hold_days and max_days >= policy.auto_credit_hold_days:
            if not dc.credit_hold_flag:
                dc.credit_hold_flag = True
                dc.credit_hold_reason = f"Auto-hold: {max_days} days overdue (policy threshold: {policy.auto_credit_hold_days})"
                dc.credit_hold_date = _today()
        if policy and policy.auto_credit_hold_amount and total_overdue >= policy.auto_credit_hold_amount:
            if not dc.credit_hold_flag:
                dc.credit_hold_flag = True
                dc.credit_hold_reason = f"Auto-hold: overdue amount {total_overdue:,.2f} exceeds threshold"
                dc.credit_hold_date = _today()

        # Compute priority
        broken_ptps = (await db.execute(
            select(func.count(DunningPTP.id)).where(
                DunningPTP.case_id == dc.id,
                DunningPTP.status == PTPStatus.BROKEN,
            )
        )).scalar() or 0
        dc.priority_score = _compute_priority(total_overdue, oldest_due, broken_ptps)

        # Determine current level
        if policy:
            lvl = await _resolve_level(db, policy.id, max_days)
            if lvl:
                dc.current_level_no = lvl.level_no

    await db.flush()
    return {"cases_created": created, "cases_updated": updated, "overdue_invoices": len(overdue)}


# ── Case CRUD ─────────────────────────────────────────────────────────────────

async def list_cases(
    db: AsyncSession,
    status: Optional[str] = None,
    collector_id: Optional[uuid.UUID] = None,
    credit_hold: Optional[bool] = None,
    limit: int = 100,
) -> List[DunningCase]:
    q = select(DunningCase)
    if status:
        q = q.where(DunningCase.case_status == status)
    if collector_id:
        q = q.where(DunningCase.assigned_collector_id == collector_id)
    if credit_hold is not None:
        q = q.where(DunningCase.credit_hold_flag == credit_hold)
    return list((await db.execute(
        q.order_by(DunningCase.priority_score.desc()).limit(limit)
    )).scalars())


async def get_case(db: AsyncSession, case_id: uuid.UUID) -> Optional[DunningCase]:
    return (await db.execute(select(DunningCase).where(DunningCase.id == case_id))).scalar_one_or_none()


async def update_case_notes(db: AsyncSession, case_id: uuid.UUID, payload: DunningCaseNoteUpdate) -> Optional[DunningCase]:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.collector_notes = payload.collector_notes
    await db.flush()
    await db.refresh(case)
    return case


async def assign_case(db: AsyncSession, case_id: uuid.UUID, payload: DunningCaseAssign) -> Optional[DunningCase]:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.assigned_collector_id = payload.assigned_collector_id
    await db.flush()
    await db.refresh(case)
    return case


async def get_case_invoices(db: AsyncSession, case_id: uuid.UUID) -> List[DunningCaseInvoice]:
    rows = await db.execute(
        select(DunningCaseInvoice).where(DunningCaseInvoice.case_id == case_id)
        .order_by(DunningCaseInvoice.days_overdue.desc())
    )
    return list(rows.scalars())


async def set_dispute(db: AsyncSession, case_id: uuid.UUID, payload: DunningDisputeSet) -> Optional[DunningCaseInvoice]:
    link = (await db.execute(
        select(DunningCaseInvoice).where(
            DunningCaseInvoice.case_id == case_id,
            DunningCaseInvoice.invoice_id == payload.invoice_id,
        )
    )).scalar_one_or_none()
    if not link:
        return None
    link.dispute_flag = payload.dispute_flag
    link.dispute_reason = payload.dispute_reason
    link.excluded_from_dunning = payload.dispute_flag
    await db.flush()
    # Update case status
    case = await get_case(db, case_id)
    if case and payload.dispute_flag:
        non_disputed = (await db.execute(
            select(func.count(DunningCaseInvoice.id)).where(
                DunningCaseInvoice.case_id == case_id,
                DunningCaseInvoice.dispute_flag == False,
            )
        )).scalar() or 0
        if non_disputed == 0:
            case.case_status = DunningCaseStatus.DISPUTED
    await db.flush()
    await db.refresh(link)
    return link


# ── Reminder / Action ─────────────────────────────────────────────────────────

async def send_reminder(
    db: AsyncSession,
    case_id: uuid.UUID,
    payload: DunningReminderRequest,
) -> DunningActionLog:
    case = await get_case(db, case_id)
    if not case:
        raise ValueError("Case not found")

    customer = (await db.execute(select(Customer).where(Customer.id == case.customer_id))).scalar_one_or_none()

    tmpl = None
    if case.policy_id:
        level = (await db.execute(
            select(DunningLevel).where(
                DunningLevel.policy_id == case.policy_id,
                DunningLevel.level_no == case.current_level_no,
            ).limit(1)
        )).scalar_one_or_none()
        if level and level.template_code:
            tmpl = await _get_template(db, level.template_code, payload.channel)

    subject, body = _render_template(tmpl, case, customer) if customer else ("Reminder", "")

    log = DunningActionLog(
        case_id=case_id,
        level_no=case.current_level_no,
        action_type=payload.channel,
        channel_type=payload.channel.value,
        action_datetime=_now(),
        sent_by_system_flag=payload.user_id is None,
        user_id=payload.user_id,
        template_code=tmpl.template_code if tmpl else None,
        outcome_status=DunningActionOutcome.SENT,
        rendered_subject=subject,
        rendered_body=payload.manual_note or body,
    )
    db.add(log)
    case.latest_action_date = _now()
    case.next_action_date = _today() + timedelta(days=7)
    await db.flush()
    await db.refresh(log)
    return log


async def add_manual_note(
    db: AsyncSession,
    case_id: uuid.UUID,
    payload: DunningManualNote,
) -> DunningActionLog:
    case = await get_case(db, case_id)
    if not case:
        raise ValueError("Case not found")
    log = DunningActionLog(
        case_id=case_id,
        level_no=case.current_level_no,
        action_type=DunningActionType.CALL_REMINDER,
        action_datetime=_now(),
        sent_by_system_flag=False,
        user_id=payload.user_id,
        outcome_status=DunningActionOutcome.MANUAL_LOGGED,
        rendered_body=payload.notes,
        notes=payload.notes,
    )
    db.add(log)
    case.latest_action_date = _now()
    await db.flush()
    await db.refresh(log)
    return log


async def list_action_logs(db: AsyncSession, case_id: uuid.UUID) -> List[DunningActionLog]:
    rows = await db.execute(
        select(DunningActionLog).where(DunningActionLog.case_id == case_id)
        .order_by(DunningActionLog.action_datetime.desc())
    )
    return list(rows.scalars())


# ── PTP ───────────────────────────────────────────────────────────────────────

async def create_ptp(db: AsyncSession, case_id: uuid.UUID, payload: DunningPTPCreate) -> DunningPTP:
    case = await get_case(db, case_id)
    if not case:
        raise ValueError("Case not found")
    ptp = DunningPTP(
        case_id=case_id,
        customer_id=case.customer_id,
        promised_amount=payload.promised_amount,
        promised_date=payload.promised_date,
        recorded_by=payload.recorded_by,
        recorded_at=_now(),
        status=PTPStatus.OPEN,
        notes=payload.notes,
    )
    db.add(ptp)
    case.case_status = DunningCaseStatus.PROMISE_TO_PAY
    await db.flush()
    await db.refresh(ptp)
    return ptp


async def update_ptp(db: AsyncSession, ptp_id: uuid.UUID, payload: DunningPTPUpdate) -> Optional[DunningPTP]:
    ptp = (await db.execute(select(DunningPTP).where(DunningPTP.id == ptp_id))).scalar_one_or_none()
    if not ptp:
        return None
    ptp.status = payload.status
    if payload.notes:
        ptp.notes = payload.notes
    await db.flush()
    await db.refresh(ptp)
    return ptp


async def list_ptps(db: AsyncSession, case_id: uuid.UUID) -> List[DunningPTP]:
    rows = await db.execute(
        select(DunningPTP).where(DunningPTP.case_id == case_id).order_by(DunningPTP.promised_date)
    )
    return list(rows.scalars())


async def check_broken_ptps(db: AsyncSession) -> int:
    today = _today()
    rows = await db.execute(
        select(DunningPTP).where(
            DunningPTP.promised_date < today,
            DunningPTP.status == PTPStatus.OPEN,
        )
    )
    count = 0
    for ptp in rows.scalars():
        ptp.status = PTPStatus.BROKEN
        count += 1
        # Recompute priority
        case = await get_case(db, ptp.case_id)
        if case:
            broken = (await db.execute(
                select(func.count(DunningPTP.id)).where(
                    DunningPTP.case_id == case.id,
                    DunningPTP.status == PTPStatus.BROKEN,
                )
            )).scalar() or 0
            case.priority_score = _compute_priority(case.total_overdue_amount, case.oldest_due_date, broken)
    await db.flush()
    return count


# ── Exception ─────────────────────────────────────────────────────────────────

async def create_exception(db: AsyncSession, case_id: uuid.UUID, payload: DunningExceptionCreate) -> DunningException:
    exc = DunningException(case_id=case_id, **payload.model_dump())
    db.add(exc)
    await db.flush()
    await db.refresh(exc)
    return exc


async def list_exceptions(db: AsyncSession, case_id: uuid.UUID) -> List[DunningException]:
    rows = await db.execute(select(DunningException).where(DunningException.case_id == case_id))
    return list(rows.scalars())


# ── Credit Hold ───────────────────────────────────────────────────────────────

async def apply_credit_hold(db: AsyncSession, case_id: uuid.UUID, payload: CreditHoldApply) -> Optional[DunningCase]:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.credit_hold_flag = True
    case.credit_hold_reason = f"{payload.reason} (applied by {payload.applied_by})"
    case.credit_hold_date = _today()
    await db.flush()
    log = DunningActionLog(
        case_id=case_id,
        level_no=case.current_level_no,
        action_type=DunningActionType.CREDIT_HOLD,
        action_datetime=_now(),
        sent_by_system_flag=False,
        outcome_status=DunningActionOutcome.MANUAL_LOGGED,
        notes=f"Credit hold applied by {payload.applied_by}: {payload.reason}",
    )
    db.add(log)
    await db.flush()
    await db.refresh(case)
    return case


async def release_credit_hold(db: AsyncSession, case_id: uuid.UUID, payload: CreditHoldRelease) -> Optional[DunningCase]:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.credit_hold_flag = False
    case.credit_hold_reason = None
    await db.flush()
    log = DunningActionLog(
        case_id=case_id,
        level_no=case.current_level_no,
        action_type=DunningActionType.CREDIT_HOLD,
        action_datetime=_now(),
        sent_by_system_flag=False,
        outcome_status=DunningActionOutcome.MANUAL_LOGGED,
        notes=f"Credit hold released by {payload.released_by}. {payload.notes or ''}",
    )
    db.add(log)
    await db.flush()
    await db.refresh(case)
    return case


async def close_case(db: AsyncSession, case_id: uuid.UUID) -> Optional[DunningCase]:
    case = await get_case(db, case_id)
    if not case:
        return None
    case.case_status = DunningCaseStatus.CLOSED
    case.credit_hold_flag = False
    await db.flush()
    await db.refresh(case)
    return case


# ── Aging Report ──────────────────────────────────────────────────────────────

async def aging_report(db: AsyncSession) -> List[dict]:
    today = _today()
    rows = await db.execute(
        select(Invoice).where(
            Invoice.status.in_(["ISSUED", "SENT", "OVERDUE", "PARTIAL"])
        )
    )
    by_customer: dict[str, dict] = {}
    for inv in rows.scalars():
        cid = str(inv.customer_id)
        balance = float(inv.total_amount - inv.paid_amount)
        if balance <= 0:
            continue
        days = (today - inv.due_date).days if inv.due_date else 0
        rec = by_customer.setdefault(cid, {
            "customer_id": cid,
            "currency": inv.currency,
            "current": 0.0,
            "overdue_1_7": 0.0,
            "overdue_8_14": 0.0,
            "overdue_15_30": 0.0,
            "overdue_31_60": 0.0,
            "overdue_61_90": 0.0,
            "overdue_90_plus": 0.0,
        })
        if days <= 0:
            rec["current"] += balance
        elif days <= 7:
            rec["overdue_1_7"] += balance
        elif days <= 14:
            rec["overdue_8_14"] += balance
        elif days <= 30:
            rec["overdue_15_30"] += balance
        elif days <= 60:
            rec["overdue_31_60"] += balance
        elif days <= 90:
            rec["overdue_61_90"] += balance
        else:
            rec["overdue_90_plus"] += balance

    result = []
    for cid, rec in by_customer.items():
        cust = (await db.execute(select(Customer).where(Customer.id == uuid.UUID(cid)))).scalar_one_or_none()
        case = (await db.execute(
            select(DunningCase).where(
                DunningCase.customer_id == uuid.UUID(cid),
                DunningCase.case_status.in_([DunningCaseStatus.OPEN, DunningCaseStatus.PROMISE_TO_PAY, DunningCaseStatus.ESCALATED])
            ).limit(1)
        )).scalar_one_or_none()
        total_overdue = (
            rec["overdue_1_7"] + rec["overdue_8_14"] + rec["overdue_15_30"]
            + rec["overdue_31_60"] + rec["overdue_61_90"] + rec["overdue_90_plus"]
        )
        result.append({
            "customer_id": cid,
            "customer_name": cust.name if cust else "Unknown",
            "customer_code": cust.code if cust else "—",
            "currency": rec["currency"],
            "current": round(rec["current"], 2),
            "overdue_1_7": round(rec["overdue_1_7"], 2),
            "overdue_8_14": round(rec["overdue_8_14"], 2),
            "overdue_15_30": round(rec["overdue_15_30"], 2),
            "overdue_31_60": round(rec["overdue_31_60"], 2),
            "overdue_61_90": round(rec["overdue_61_90"], 2),
            "overdue_90_plus": round(rec["overdue_90_plus"], 2),
            "total_overdue": round(total_overdue, 2),
            "credit_hold": case.credit_hold_flag if case else False,
            "case_id": str(case.id) if case else None,
            "priority_score": case.priority_score if case else 0,
        })
    result.sort(key=lambda x: x["total_overdue"], reverse=True)
    return result


async def report_dashboard(db: AsyncSession) -> dict:
    total_cases = (await db.execute(select(func.count(DunningCase.id)).where(DunningCase.case_status == DunningCaseStatus.OPEN))).scalar() or 0
    total_overdue = (await db.execute(select(func.sum(DunningCase.total_overdue_amount)).where(DunningCase.case_status != DunningCaseStatus.CLOSED))).scalar() or Decimal("0")
    credit_holds = (await db.execute(select(func.count(DunningCase.id)).where(DunningCase.credit_hold_flag == True))).scalar() or 0
    disputed = (await db.execute(select(func.count(DunningCase.id)).where(DunningCase.case_status == DunningCaseStatus.DISPUTED))).scalar() or 0
    ptps_open = (await db.execute(select(func.count(DunningPTP.id)).where(DunningPTP.status == PTPStatus.OPEN))).scalar() or 0
    ptps_broken = (await db.execute(select(func.count(DunningPTP.id)).where(DunningPTP.status == PTPStatus.BROKEN))).scalar() or 0
    return {
        "open_cases": total_cases,
        "total_overdue_amount": float(total_overdue),
        "credit_hold_count": credit_holds,
        "disputed_cases": disputed,
        "open_ptps": ptps_open,
        "broken_ptps": ptps_broken,
    }


async def report_effectiveness(db: AsyncSession) -> List[dict]:
    rows = await db.execute(
        select(DunningActionLog.level_no, DunningActionLog.action_type,
               func.count(DunningActionLog.id).label("total"),
               func.count(DunningActionLog.id).filter(DunningActionLog.outcome_status == DunningActionOutcome.SENT).label("sent"),
               func.count(DunningActionLog.id).filter(DunningActionLog.outcome_status == DunningActionOutcome.DELIVERED).label("delivered"),
               )
        .group_by(DunningActionLog.level_no, DunningActionLog.action_type)
        .order_by(DunningActionLog.level_no)
    )
    return [
        {
            "level_no": r.level_no,
            "action_type": r.action_type,
            "total_actions": r.total,
            "sent": r.sent,
            "delivered": r.delivered,
        }
        for r in rows
    ]


async def report_collector_workqueue(db: AsyncSession, collector_id: Optional[uuid.UUID] = None) -> List[dict]:
    q = select(DunningCase).where(
        DunningCase.case_status.in_([DunningCaseStatus.OPEN, DunningCaseStatus.PROMISE_TO_PAY, DunningCaseStatus.ESCALATED])
    )
    if collector_id:
        q = q.where(DunningCase.assigned_collector_id == collector_id)
    cases = list((await db.execute(q.order_by(DunningCase.priority_score.desc()).limit(200))).scalars())
    result = []
    for c in cases:
        cust = (await db.execute(select(Customer).where(Customer.id == c.customer_id))).scalar_one_or_none()
        open_ptps = (await db.execute(
            select(func.count(DunningPTP.id)).where(DunningPTP.case_id == c.id, DunningPTP.status == PTPStatus.OPEN)
        )).scalar() or 0
        result.append({
            "case_id": str(c.id),
            "case_no": c.case_no,
            "customer_name": cust.name if cust else "Unknown",
            "customer_code": cust.code if cust else "—",
            "total_overdue": float(c.total_overdue_amount),
            "oldest_due_date": str(c.oldest_due_date) if c.oldest_due_date else None,
            "current_level": c.current_level_no,
            "status": c.case_status,
            "credit_hold": c.credit_hold_flag,
            "priority_score": c.priority_score,
            "next_action_date": str(c.next_action_date) if c.next_action_date else None,
            "open_ptps": open_ptps,
        })
    return result


async def report_ptp_fulfillment(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count(DunningPTP.id)))).scalar() or 0
    met = (await db.execute(select(func.count(DunningPTP.id)).where(DunningPTP.status == PTPStatus.MET))).scalar() or 0
    broken = (await db.execute(select(func.count(DunningPTP.id)).where(DunningPTP.status == PTPStatus.BROKEN))).scalar() or 0
    open_ = (await db.execute(select(func.count(DunningPTP.id)).where(DunningPTP.status == PTPStatus.OPEN))).scalar() or 0
    return {
        "total": total,
        "met": met,
        "broken": broken,
        "open": open_,
        "success_rate_pct": round(met / total * 100, 1) if total > 0 else 0,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[DunningAIRecommendation]:
    recs: List[DunningAIRecommendation] = []

    # Agent 1: Collection Prioritization Assistant
    high_priority = list((await db.execute(
        select(DunningCase).where(
            DunningCase.case_status == DunningCaseStatus.OPEN,
            DunningCase.priority_score >= 70,
            DunningCase.assigned_collector_id == None,
        ).order_by(DunningCase.priority_score.desc()).limit(10)
    )).scalars())
    for c in high_priority:
        r = DunningAIRecommendation(
            case_id=c.id,
            customer_id=c.customer_id,
            agent_type=DunningAIAgentType.COLLECTION_PRIORITIZATION,
            status=DunningAIRecStatus.PENDING,
            title="High-Priority Case Unassigned",
            body=f"Case {c.case_no} has priority score {c.priority_score}/100 and overdue amount {c.total_overdue_amount:,.2f} but no collector assigned. Assign immediately.",
            severity="WARNING",
            reference_type="DunningCase",
            reference_id=str(c.id),
        )
        db.add(r)
        recs.append(r)

    # Agent 2: Payment Risk Monitor — repeated broken PTPs
    broken_counts = await db.execute(
        select(DunningPTP.case_id, func.count(DunningPTP.id).label("broken_count"))
        .where(DunningPTP.status == PTPStatus.BROKEN)
        .group_by(DunningPTP.case_id)
        .having(func.count(DunningPTP.id) >= 2)
    )
    for row in broken_counts:
        case = await get_case(db, row.case_id)
        if case:
            r = DunningAIRecommendation(
                case_id=case.id,
                customer_id=case.customer_id,
                agent_type=DunningAIAgentType.PAYMENT_RISK_MONITOR,
                status=DunningAIRecStatus.PENDING,
                title="Repeated Broken Promises — Escalation Needed",
                body=f"Case {case.case_no} has {row.broken_count} broken payment promises. This customer shows a pattern of non-payment. Consider escalation to manager or legal review.",
                severity="CRITICAL",
                reference_type="DunningCase",
                reference_id=str(case.id),
            )
            db.add(r)
            recs.append(r)

    # Agent 3: Effectiveness — cases stuck at same level for 14+ days
    two_weeks_ago = _now() - timedelta(days=14)
    stale_cases = list((await db.execute(
        select(DunningCase).where(
            DunningCase.case_status == DunningCaseStatus.OPEN,
            or_(
                DunningCase.latest_action_date < two_weeks_ago,
                DunningCase.latest_action_date == None,
            ),
            DunningCase.total_overdue_amount > 0,
        ).limit(20)
    )).scalars())
    for c in stale_cases:
        r = DunningAIRecommendation(
            case_id=c.id,
            customer_id=c.customer_id,
            agent_type=DunningAIAgentType.EFFECTIVENESS_ASSISTANT,
            status=DunningAIRecStatus.PENDING,
            title="Stale Dunning Case — No Action in 14 Days",
            body=f"Case {c.case_no} at level {c.current_level_no} has had no dunning action for over 14 days. Review the policy level or contact the customer directly.",
            severity="WARNING",
            reference_type="DunningCase",
            reference_id=str(c.id),
        )
        db.add(r)
        recs.append(r)

    await db.flush()
    return recs


async def list_ai_recs(db: AsyncSession, case_id: Optional[uuid.UUID] = None) -> List[DunningAIRecommendation]:
    q = select(DunningAIRecommendation)
    if case_id:
        q = q.where(DunningAIRecommendation.case_id == case_id)
    return list((await db.execute(q.order_by(DunningAIRecommendation.created_at.desc()).limit(200))).scalars())


async def ack_ai_rec(db: AsyncSession, rec_id: uuid.UUID, payload: DunningAIRecAck) -> Optional[DunningAIRecommendation]:
    rec = (await db.execute(select(DunningAIRecommendation).where(DunningAIRecommendation.id == rec_id))).scalar_one_or_none()
    if not rec:
        return None
    rec.status = payload.status
    rec.actioned_by = payload.actioned_by
    rec.actioned_at = _now()
    await db.flush()
    await db.refresh(rec)
    return rec


# ── Templates CRUD ────────────────────────────────────────────────────────────

async def get_template(db: AsyncSession, template_id: uuid.UUID) -> Optional[DunningTemplate]:
    return (await db.execute(select(DunningTemplate).where(DunningTemplate.id == template_id))).scalar_one_or_none()
