from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expenses import (
    ExpenseCategory, ExpensePolicy, ExpenseClaim, ExpenseClaimLine,
    ExpenseAdvance, ExpenseAccountingEntry, ExpAIRecommendation,
    ExpenseStatus, AdvanceSettlementStatus, PolicyViolationSeverity,
    ExpAIAgentType, ExpAIRecStatus, ReimbursementMethod,
)
from app.schemas.expenses import (
    ExpenseCategoryCreate, ExpensePolicyCreate, ExpenseClaimCreate,
    ExpenseClaimApproveReject, ExpenseClaimPayRequest,
    ExpenseAdvanceCreate, ExpenseAdvanceSettle, ExpAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _next_claim_no(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(ExpenseClaim))
    n = result.scalar_one() + 1
    return f"EXP-{n:06d}"


async def _next_advance_no(db: AsyncSession) -> str:
    result = await db.execute(select(func.count()).select_from(ExpenseAdvance))
    n = result.scalar_one() + 1
    return f"ADV-{n:06d}"


# ── Category CRUD ─────────────────────────────────────────────────────────────

async def list_categories(db: AsyncSession) -> List[ExpenseCategory]:
    result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.active_flag == True).order_by(ExpenseCategory.category_name))
    return list(result.scalars().all())


async def create_category(db: AsyncSession, data: ExpenseCategoryCreate) -> ExpenseCategory:
    cat = ExpenseCategory(**data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def get_category(db: AsyncSession, category_id: UUID) -> Optional[ExpenseCategory]:
    result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.expense_category_id == category_id))
    return result.scalar_one_or_none()


async def update_category(db: AsyncSession, category_id: UUID, data: dict) -> Optional[ExpenseCategory]:
    cat = await get_category(db, category_id)
    if not cat:
        return None
    for k, v in data.items():
        setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    return cat


# ── Policy CRUD ───────────────────────────────────────────────────────────────

async def list_policies(db: AsyncSession) -> List[ExpensePolicy]:
    result = await db.execute(select(ExpensePolicy).where(ExpensePolicy.active_flag == True).order_by(ExpensePolicy.policy_name))
    return list(result.scalars().all())


async def create_policy(db: AsyncSession, data: ExpensePolicyCreate) -> ExpensePolicy:
    pol = ExpensePolicy(**data.model_dump())
    db.add(pol)
    await db.commit()
    await db.refresh(pol)
    return pol


async def get_policy(db: AsyncSession, policy_id: UUID) -> Optional[ExpensePolicy]:
    result = await db.execute(select(ExpensePolicy).where(ExpensePolicy.expense_policy_id == policy_id))
    return result.scalar_one_or_none()


# ── Policy Validation ─────────────────────────────────────────────────────────

async def _validate_lines_against_policy(
    db: AsyncSession,
    lines: List[ExpenseClaimLine],
    employee_id: UUID,
    department_id: Optional[UUID],
) -> None:
    categories = {str(ln.expense_category_id) for ln in lines}
    result = await db.execute(
        select(ExpensePolicy).where(
            and_(
                ExpensePolicy.active_flag == True,
                ExpensePolicy.category_id.in_([UUID(c) for c in categories]),
            )
        )
    )
    policies = result.scalars().all()
    policy_map: dict = {}
    for p in policies:
        key = str(p.category_id)
        policy_map[key] = p

    for ln in lines:
        p = policy_map.get(str(ln.expense_category_id))
        if not p:
            continue
        violation = False
        note_parts = []
        severity = PolicyViolationSeverity.WARNING

        if p.max_amount_per_line and ln.claimed_amount > p.max_amount_per_line:
            violation = True
            note_parts.append(f"Exceeds per-line limit {p.max_amount_per_line}")
            severity = PolicyViolationSeverity.BLOCK

        if p.receipt_required_above_amount and ln.claimed_amount > p.receipt_required_above_amount and not ln.attachment_ref:
            violation = True
            note_parts.append(f"Receipt required above {p.receipt_required_above_amount}")
            severity = PolicyViolationSeverity.BLOCK

        ln.policy_violation_flag = violation
        ln.policy_violation_note = "; ".join(note_parts) if note_parts else None
        ln.policy_violation_severity = severity if violation else None


async def _check_duplicate_receipt(db: AsyncSession, lines: List[ExpenseClaimLine]) -> None:
    for ln in lines:
        if not ln.receipt_no:
            continue
        result = await db.execute(
            select(ExpenseClaimLine).where(
                and_(
                    ExpenseClaimLine.receipt_no == ln.receipt_no,
                    ExpenseClaimLine.expense_line_id != ln.expense_line_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            ln.policy_violation_flag = True
            ln.policy_violation_note = (ln.policy_violation_note or "") + f" Duplicate receipt {ln.receipt_no}."
            ln.policy_violation_severity = PolicyViolationSeverity.BLOCK


# ── Claim CRUD ────────────────────────────────────────────────────────────────

async def list_claims(
    db: AsyncSession,
    employee_id: Optional[UUID] = None,
    status: Optional[ExpenseStatus] = None,
    department_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[ExpenseClaim]:
    q = select(ExpenseClaim).options(selectinload(ExpenseClaim.lines))
    filters = []
    if employee_id:
        filters.append(ExpenseClaim.employee_id == employee_id)
    if status:
        filters.append(ExpenseClaim.status == status)
    if department_id:
        filters.append(ExpenseClaim.department_id == department_id)
    if filters:
        q = q.where(and_(*filters))
    q = q.order_by(ExpenseClaim.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_claim(db: AsyncSession, claim_id: UUID) -> Optional[ExpenseClaim]:
    result = await db.execute(
        select(ExpenseClaim)
        .options(selectinload(ExpenseClaim.lines))
        .where(ExpenseClaim.expense_claim_id == claim_id)
    )
    return result.scalar_one_or_none()


async def create_claim(db: AsyncSession, data: ExpenseClaimCreate) -> ExpenseClaim:
    claim_no = await _next_claim_no(db)
    claim = ExpenseClaim(
        claim_no=claim_no,
        employee_id=data.employee_id,
        department_id=data.department_id,
        claim_date=data.claim_date,
        period_start=data.period_start,
        period_end=data.period_end,
        currency=data.currency,
        reimbursement_method=data.reimbursement_method,
        advance_id=data.advance_id,
        notes=data.notes,
        status=ExpenseStatus.DRAFT,
    )
    db.add(claim)
    await db.flush()

    lines = []
    total = Decimal("0")
    for ld in data.lines:
        ln = ExpenseClaimLine(
            expense_claim_id=claim.expense_claim_id,
            **ld.model_dump(),
        )
        db.add(ln)
        lines.append(ln)
        total += ld.claimed_amount

    await db.flush()
    await _validate_lines_against_policy(db, lines, data.employee_id, data.department_id)
    await _check_duplicate_receipt(db, lines)

    claim.total_claimed_amount = total
    await db.commit()
    await db.refresh(claim)
    return claim


async def add_line(db: AsyncSession, claim_id: UUID, data) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status not in (ExpenseStatus.DRAFT,):
        return None
    ln = ExpenseClaimLine(expense_claim_id=claim_id, **data.model_dump())
    db.add(ln)
    await db.flush()
    await _validate_lines_against_policy(db, [ln], claim.employee_id, claim.department_id)
    await _check_duplicate_receipt(db, [ln])
    claim.total_claimed_amount = sum(l.claimed_amount for l in claim.lines) + ln.claimed_amount
    await db.commit()
    await db.refresh(claim)
    return claim


async def submit_claim(db: AsyncSession, claim_id: UUID) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status != ExpenseStatus.DRAFT:
        return None
    blocking = [ln for ln in claim.lines if ln.policy_violation_severity == PolicyViolationSeverity.BLOCK]
    if blocking:
        return None
    claim.status = ExpenseStatus.SUBMITTED
    claim.submitted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(claim)
    return claim


async def manager_approve_claim(db: AsyncSession, claim_id: UUID, req: ExpenseClaimApproveReject) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status != ExpenseStatus.SUBMITTED:
        return None
    _apply_line_approvals(claim, req.line_approvals)
    claim.status = ExpenseStatus.MANAGER_APPROVED
    claim.approved_by_manager = req.approver_id
    claim.manager_approved_at = datetime.utcnow()
    _recalculate_totals(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


async def finance_approve_claim(db: AsyncSession, claim_id: UUID, req: ExpenseClaimApproveReject) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status != ExpenseStatus.MANAGER_APPROVED:
        return None
    _apply_line_approvals(claim, req.line_approvals)
    claim.status = ExpenseStatus.FINANCE_APPROVED
    claim.approved_by_finance = req.approver_id
    claim.finance_approved_at = datetime.utcnow()
    _recalculate_totals(claim)
    await _post_accounting_entries(db, claim)
    await db.commit()
    await db.refresh(claim)
    return claim


async def reject_claim(db: AsyncSession, claim_id: UUID, req: ExpenseClaimApproveReject) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status in (ExpenseStatus.PAID, ExpenseStatus.CANCELLED):
        return None
    claim.status = ExpenseStatus.REJECTED
    claim.rejected_by = req.approver_id
    claim.rejected_at = datetime.utcnow()
    claim.rejection_reason = req.notes
    for ln in claim.lines:
        ln.line_status = "rejected"
    await db.commit()
    await db.refresh(claim)
    return claim


async def pay_claim(db: AsyncSession, claim_id: UUID, req: ExpenseClaimPayRequest) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status != ExpenseStatus.FINANCE_APPROVED:
        return None
    claim.status = ExpenseStatus.PAID
    claim.paid_at = req.paid_at or datetime.utcnow()
    claim.payment_reference = req.payment_reference
    if req.advance_deducted:
        claim.advance_deducted = req.advance_deducted
        if claim.advance_id:
            adv = await get_advance(db, claim.advance_id)
            if adv:
                adv.settled_amount = (adv.settled_amount or Decimal("0")) + req.advance_deducted
                remaining = adv.advance_amount - adv.settled_amount
                if remaining <= 0:
                    adv.settlement_status = AdvanceSettlementStatus.SETTLED
                else:
                    adv.settlement_status = AdvanceSettlementStatus.PARTIALLY_SETTLED
    await db.commit()
    await db.refresh(claim)
    return claim


async def return_for_correction(db: AsyncSession, claim_id: UUID, notes: str) -> Optional[ExpenseClaim]:
    claim = await get_claim(db, claim_id)
    if not claim or claim.status not in (ExpenseStatus.SUBMITTED, ExpenseStatus.MANAGER_APPROVED):
        return None
    claim.status = ExpenseStatus.DRAFT
    claim.rejection_reason = notes
    await db.commit()
    await db.refresh(claim)
    return claim


def _apply_line_approvals(claim: ExpenseClaim, line_approvals) -> None:
    if not line_approvals:
        for ln in claim.lines:
            if ln.line_status != "rejected":
                ln.approved_amount = ln.claimed_amount
                ln.line_status = "approved"
        return
    la_map = {str(la.expense_line_id): la for la in line_approvals}
    for ln in claim.lines:
        la = la_map.get(str(ln.expense_line_id))
        if la:
            ln.approved_amount = la.approved_amount
            ln.line_status = "approved" if la.approved_amount > 0 else "rejected"
            if la.notes:
                ln.notes = la.notes
        else:
            ln.approved_amount = ln.claimed_amount
            ln.line_status = "approved"


def _recalculate_totals(claim: ExpenseClaim) -> None:
    approved = Decimal("0")
    rejected = Decimal("0")
    for ln in claim.lines:
        if ln.line_status == "approved":
            approved += ln.approved_amount or ln.claimed_amount
        elif ln.line_status == "rejected":
            rejected += ln.claimed_amount
    claim.total_approved_amount = approved
    claim.total_rejected_amount = rejected


async def _post_accounting_entries(db: AsyncSession, claim: ExpenseClaim) -> None:
    entry = ExpenseAccountingEntry(
        expense_claim_id=claim.expense_claim_id,
        entry_date=date.today(),
        debit_account="Expense Account",
        credit_account="Employee Payable",
        amount=claim.total_approved_amount,
        tax_amount=sum(ln.tax_amount or 0 for ln in claim.lines),
        description=f"Expense reimbursement {claim.claim_no}",
    )
    db.add(entry)


# ── Advance ───────────────────────────────────────────────────────────────────

async def list_advances(
    db: AsyncSession,
    employee_id: Optional[UUID] = None,
    status: Optional[AdvanceSettlementStatus] = None,
) -> List[ExpenseAdvance]:
    q = select(ExpenseAdvance)
    filters = []
    if employee_id:
        filters.append(ExpenseAdvance.employee_id == employee_id)
    if status:
        filters.append(ExpenseAdvance.settlement_status == status)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q.order_by(ExpenseAdvance.advance_date.desc()))
    return list(result.scalars().all())


async def get_advance(db: AsyncSession, advance_id: UUID) -> Optional[ExpenseAdvance]:
    result = await db.execute(select(ExpenseAdvance).where(ExpenseAdvance.advance_id == advance_id))
    return result.scalar_one_or_none()


async def create_advance(db: AsyncSession, data: ExpenseAdvanceCreate) -> ExpenseAdvance:
    advance_no = await _next_advance_no(db)
    adv = ExpenseAdvance(advance_no=advance_no, **data.model_dump())
    db.add(adv)
    await db.commit()
    await db.refresh(adv)
    return adv


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count()).select_from(ExpenseClaim))).scalar_one()
    pending = (await db.execute(
        select(func.count()).select_from(ExpenseClaim).where(
            ExpenseClaim.status.in_([ExpenseStatus.SUBMITTED, ExpenseStatus.MANAGER_APPROVED])
        )
    )).scalar_one()
    approved_unpaid = (await db.execute(
        select(func.count()).select_from(ExpenseClaim).where(ExpenseClaim.status == ExpenseStatus.FINANCE_APPROVED)
    )).scalar_one()
    from datetime import timedelta
    month_start = date.today().replace(day=1)
    reimbursed = (await db.execute(
        select(func.coalesce(func.sum(ExpenseClaim.total_approved_amount), 0)).where(
            and_(ExpenseClaim.status == ExpenseStatus.PAID, ExpenseClaim.paid_at >= month_start)
        )
    )).scalar_one()
    claimed = (await db.execute(
        select(func.coalesce(func.sum(ExpenseClaim.total_claimed_amount), 0)).where(
            ExpenseClaim.claim_date >= month_start
        )
    )).scalar_one()
    violations = (await db.execute(
        select(func.count()).select_from(ExpenseClaimLine).where(ExpenseClaimLine.policy_violation_flag == True)
    )).scalar_one()
    overdue_advances = (await db.execute(
        select(func.count()).select_from(ExpenseAdvance).where(
            and_(
                ExpenseAdvance.settlement_status == AdvanceSettlementStatus.OPEN,
                ExpenseAdvance.due_date < date.today(),
            )
        )
    )).scalar_one()
    ai_alerts = (await db.execute(
        select(func.count()).select_from(ExpAIRecommendation).where(ExpAIRecommendation.status == ExpAIRecStatus.PENDING)
    )).scalar_one()
    return {
        "total_claims": total,
        "pending_approval": pending,
        "approved_unpaid": approved_unpaid,
        "total_reimbursed_month": Decimal(str(reimbursed)),
        "total_claimed_month": Decimal(str(claimed)),
        "policy_violations_open": violations,
        "overdue_advances": overdue_advances,
        "ai_alerts": ai_alerts,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_by_employee(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            ExpenseClaim.employee_id,
            func.count(ExpenseClaim.expense_claim_id).label("claim_count"),
            func.sum(ExpenseClaim.total_claimed_amount).label("total_claimed"),
            func.sum(ExpenseClaim.total_approved_amount).label("total_approved"),
        ).group_by(ExpenseClaim.employee_id)
    )
    return [dict(r._mapping) for r in result.all()]


async def report_by_category(db: AsyncSession) -> list:
    result = await db.execute(
        select(
            ExpenseCategory.category_name,
            func.count(ExpenseClaimLine.expense_line_id).label("line_count"),
            func.sum(ExpenseClaimLine.claimed_amount).label("total_claimed"),
            func.sum(ExpenseClaimLine.approved_amount).label("total_approved"),
        )
        .join(ExpenseClaimLine, ExpenseClaimLine.expense_category_id == ExpenseCategory.expense_category_id)
        .group_by(ExpenseCategory.category_name)
    )
    return [dict(r._mapping) for r in result.all()]


async def report_policy_violations(db: AsyncSession) -> list:
    result = await db.execute(
        select(ExpenseClaimLine)
        .where(ExpenseClaimLine.policy_violation_flag == True)
        .order_by(ExpenseClaimLine.created_at.desc())
    )
    return list(result.scalars().all())


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def _save_rec(db: AsyncSession, agent: ExpAIAgentType, subject: str, body: str, **kwargs) -> None:
    rec = ExpAIRecommendation(agent_type=agent, subject=subject, body=body, **kwargs)
    db.add(rec)


async def run_risk_monitor(db: AsyncSession) -> int:
    count = 0

    # duplicate receipt detection
    result = await db.execute(
        select(ExpenseClaimLine.receipt_no, func.count().label("cnt"))
        .where(ExpenseClaimLine.receipt_no.isnot(None))
        .group_by(ExpenseClaimLine.receipt_no)
        .having(func.count() > 1)
    )
    dups = result.all()
    for row in dups:
        await _save_rec(
            db, ExpAIAgentType.RISK_MONITOR,
            f"Duplicate receipt: {row.receipt_no}",
            f"Receipt number {row.receipt_no} appears {row.cnt} times. Review for potential duplicate claims.",
        )
        count += 1

    # unusually high claims
    result = await db.execute(
        select(ExpenseClaim).where(
            and_(
                ExpenseClaim.total_claimed_amount > 50000,
                ExpenseClaim.status == ExpenseStatus.SUBMITTED,
            )
        )
    )
    high = result.scalars().all()
    for c in high:
        await _save_rec(
            db, ExpAIAgentType.RISK_MONITOR,
            f"High-value claim {c.claim_no}",
            f"Claim {c.claim_no} has a total of {c.total_claimed_amount} KES which is unusually high. Enhanced review recommended.",
            ref_expense_claim_id=c.expense_claim_id,
        )
        count += 1

    await db.commit()
    return count


async def run_policy_optimizer(db: AsyncSession) -> int:
    count = 0
    result = await db.execute(
        select(
            ExpenseClaimLine.expense_category_id,
            func.count().label("violations"),
        )
        .where(ExpenseClaimLine.policy_violation_flag == True)
        .group_by(ExpenseClaimLine.expense_category_id)
        .having(func.count() > 5)
    )
    rows = result.all()
    for row in rows:
        cat = await get_category(db, row.expense_category_id)
        name = cat.category_name if cat else str(row.expense_category_id)
        await _save_rec(
            db, ExpAIAgentType.POLICY_OPTIMIZER,
            f"Policy review: {name}",
            f"Category '{name}' has {row.violations} policy violations. Consider revising the limits or receipt thresholds.",
        )
        count += 1
    await db.commit()
    return count


async def run_reimbursement_assistant(db: AsyncSession) -> int:
    count = 0
    result = await db.execute(
        select(ExpenseClaim).where(ExpenseClaim.status == ExpenseStatus.FINANCE_APPROVED)
    )
    ready = result.scalars().all()
    if ready:
        await _save_rec(
            db, ExpAIAgentType.REIMBURSEMENT_ASSISTANT,
            f"{len(ready)} claims ready for payment",
            f"There are {len(ready)} finance-approved claims awaiting payment totalling {sum(c.total_approved_amount for c in ready):,.2f} KES.",
        )
        count += 1

    # overdue advances
    result2 = await db.execute(
        select(ExpenseAdvance).where(
            and_(
                ExpenseAdvance.settlement_status == AdvanceSettlementStatus.OPEN,
                ExpenseAdvance.due_date < date.today(),
            )
        )
    )
    overdue = result2.scalars().all()
    for adv in overdue:
        await _save_rec(
            db, ExpAIAgentType.REIMBURSEMENT_ASSISTANT,
            f"Overdue advance {adv.advance_no}",
            f"Advance {adv.advance_no} of {adv.advance_amount} KES is overdue for settlement.",
            ref_employee_id=adv.employee_id,
        )
        count += 1

    await db.commit()
    return count


async def list_ai_recs(db: AsyncSession, status: Optional[ExpAIRecStatus] = None) -> List[ExpAIRecommendation]:
    q = select(ExpAIRecommendation)
    if status:
        q = q.where(ExpAIRecommendation.status == status)
    result = await db.execute(q.order_by(ExpAIRecommendation.created_at.desc()))
    return list(result.scalars().all())


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: ExpAIRecAck) -> Optional[ExpAIRecommendation]:
    result = await db.execute(select(ExpAIRecommendation).where(ExpAIRecommendation.rec_id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    rec.actioned_at = datetime.utcnow()
    if data.notes:
        rec.notes = data.notes
    await db.commit()
    await db.refresh(rec)
    return rec
