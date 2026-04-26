"""Contract Management service — lifecycle, terms, rebates, performance, AI."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contracts import (
    Contract, ContractTerm, ContractRebate, ContractPerformance,
    ContractVersion, ContractApproval, CTAIRecommendation,
    ContractStatus, ApprovalAction,
    CTAIAgentType, CTAIRecStatus,
)
from app.schemas.contracts import (
    ContractCreate, ContractUpdate, ContractTermCreate, ContractRebateCreate,
    PerformanceCreate, PerformanceUpdate, ApprovalCreate,
    TerminateRequest, CTAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _gen_code() -> str:
    import random
    return f"CT-{datetime.utcnow().strftime('%Y%m')}-{random.randint(1000, 9999)}"


def _snapshot(contract: Contract) -> dict:
    return {
        "id": str(contract.id),
        "contract_code": contract.contract_code,
        "contract_name": contract.contract_name,
        "status": contract.status,
        "start_date": str(contract.start_date),
        "end_date": str(contract.end_date) if contract.end_date else None,
        "version": contract.current_version,
    }


# ── Contract CRUD ─────────────────────────────────────────────────────────────

async def list_contracts(
    db: AsyncSession,
    party_type: Optional[str] = None,
    status: Optional[str] = None,
    party_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Contract]:
    q = select(Contract).options(
        selectinload(Contract.terms),
        selectinload(Contract.rebates),
    )
    if party_type:
        q = q.where(Contract.party_type == party_type)
    if status:
        q = q.where(Contract.status == status)
    if party_id:
        q = q.where(Contract.party_id == party_id)
    result = await db.execute(q.order_by(Contract.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


async def get_contract(db: AsyncSession, contract_id: uuid.UUID) -> Optional[Contract]:
    result = await db.execute(
        select(Contract).options(
            selectinload(Contract.terms),
            selectinload(Contract.rebates),
            selectinload(Contract.performance),
            selectinload(Contract.versions),
            selectinload(Contract.approvals),
        ).where(Contract.id == contract_id)
    )
    return result.scalars().first()


async def create_contract(
    db: AsyncSession, payload: ContractCreate, user_id: Optional[uuid.UUID]
) -> Contract:
    c = Contract(
        contract_code=payload.contract_code or _gen_code(),
        contract_name=payload.contract_name,
        contract_type=payload.contract_type,
        party_type=payload.party_type,
        party_id=payload.party_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=ContractStatus.DRAFT.value,
        currency=payload.currency,
        payment_terms_id=payload.payment_terms_id,
        price_list_id=payload.price_list_id,
        auto_renew=payload.auto_renew,
        renewal_notice_days=payload.renewal_notice_days,
        linked_promo_ids=payload.linked_promo_ids,
        linked_tpm_plan_id=payload.linked_tpm_plan_id,
        notes=payload.notes,
        created_by=user_id,
        current_version=1,
    )
    db.add(c)
    await db.flush()

    for tp in payload.terms:
        db.add(ContractTerm(contract_id=c.id, **tp.model_dump()))

    for rp in payload.rebates:
        db.add(ContractRebate(contract_id=c.id, **rp.model_dump()))

    db.add(ContractVersion(
        contract_id=c.id,
        version_no=1,
        change_summary="Initial creation",
        effective_date=payload.start_date,
        snapshot=_snapshot(c),
    ))

    await db.commit()
    await db.refresh(c)
    return c


async def update_contract(
    db: AsyncSession, contract: Contract, payload: ContractUpdate, user_id: Optional[uuid.UUID]
) -> Contract:
    changed = False
    for field, value in payload.model_dump(exclude_none=True, exclude={"change_summary"}).items():
        if getattr(contract, field, None) != value:
            setattr(contract, field, value)
            changed = True

    if changed and payload.change_summary:
        contract.current_version += 1
        db.add(ContractVersion(
            contract_id=contract.id,
            version_no=contract.current_version,
            change_summary=payload.change_summary,
            effective_date=date.today(),
            approved_by=user_id,
            snapshot=_snapshot(contract),
        ))

    await db.commit()
    await db.refresh(contract)
    return contract


# ── Terms ─────────────────────────────────────────────────────────────────────

async def add_term(
    db: AsyncSession, contract: Contract, payload: ContractTermCreate
) -> ContractTerm:
    term = ContractTerm(contract_id=contract.id, **payload.model_dump())
    db.add(term)
    await db.commit()
    await db.refresh(term)
    return term


async def delete_term(db: AsyncSession, term_id: uuid.UUID) -> bool:
    term = await db.get(ContractTerm, term_id)
    if term:
        await db.delete(term)
        await db.commit()
        return True
    return False


# ── Rebates ───────────────────────────────────────────────────────────────────

async def add_rebate(
    db: AsyncSession, contract: Contract, payload: ContractRebateCreate
) -> ContractRebate:
    rebate = ContractRebate(contract_id=contract.id, **payload.model_dump())
    db.add(rebate)
    await db.commit()
    await db.refresh(rebate)
    return rebate


async def accrue_rebate(
    db: AsyncSession, rebate: ContractRebate, accrual_amount: Decimal
) -> ContractRebate:
    rebate.accrued_amount = (rebate.accrued_amount or Decimal("0")) + accrual_amount
    await db.commit()
    await db.refresh(rebate)
    return rebate


async def settle_rebate(
    db: AsyncSession, rebate: ContractRebate, settlement_amount: Decimal
) -> ContractRebate:
    rebate.settled_amount = (rebate.settled_amount or Decimal("0")) + settlement_amount
    await db.commit()
    await db.refresh(rebate)
    return rebate


# ── Approval Lifecycle ────────────────────────────────────────────────────────

async def submit_for_approval(
    db: AsyncSession, contract: Contract, user_id: Optional[uuid.UUID], comments: Optional[str]
) -> Contract:
    contract.status = ContractStatus.UNDER_REVIEW.value
    db.add(ContractApproval(
        contract_id=contract.id,
        action=ApprovalAction.SUBMITTED.value,
        actioned_by=user_id,
        comments=comments,
    ))
    await db.commit()
    await db.refresh(contract)
    return contract


async def approve_contract(
    db: AsyncSession, contract: Contract, user_id: Optional[uuid.UUID], comments: Optional[str]
) -> Contract:
    contract.status = ContractStatus.APPROVED.value
    contract.approved_by = user_id
    contract.approved_at = datetime.utcnow()
    db.add(ContractApproval(
        contract_id=contract.id,
        action=ApprovalAction.APPROVED.value,
        actioned_by=user_id,
        comments=comments,
    ))
    await db.commit()
    await db.refresh(contract)
    return contract


async def reject_contract(
    db: AsyncSession, contract: Contract, user_id: Optional[uuid.UUID], comments: Optional[str]
) -> Contract:
    contract.status = ContractStatus.DRAFT.value
    db.add(ContractApproval(
        contract_id=contract.id,
        action=ApprovalAction.REJECTED.value,
        actioned_by=user_id,
        comments=comments,
    ))
    await db.commit()
    await db.refresh(contract)
    return contract


async def activate_contract(
    db: AsyncSession, contract: Contract, user_id: Optional[uuid.UUID]
) -> Contract:
    contract.status = ContractStatus.ACTIVE.value
    await db.commit()
    await db.refresh(contract)
    return contract


async def terminate_contract(
    db: AsyncSession, contract: Contract, payload: TerminateRequest, user_id: Optional[uuid.UUID]
) -> Contract:
    contract.status = ContractStatus.TERMINATED.value
    contract.terminated_by = user_id
    contract.terminated_at = datetime.utcnow()
    contract.termination_reason = payload.reason
    await db.commit()
    await db.refresh(contract)
    return contract


async def archive_contract(db: AsyncSession, contract: Contract) -> Contract:
    contract.status = ContractStatus.ARCHIVED.value
    await db.commit()
    await db.refresh(contract)
    return contract


# ── Performance ───────────────────────────────────────────────────────────────

async def list_performance(
    db: AsyncSession, contract_id: uuid.UUID
) -> List[ContractPerformance]:
    result = await db.execute(
        select(ContractPerformance)
        .where(ContractPerformance.contract_id == contract_id)
        .order_by(ContractPerformance.period.desc())
    )
    return result.scalars().all()


async def upsert_performance(
    db: AsyncSession, contract: Contract, payload: PerformanceCreate
) -> ContractPerformance:
    existing = await db.execute(
        select(ContractPerformance).where(
            ContractPerformance.contract_id == contract.id,
            ContractPerformance.period == payload.period,
        )
    )
    perf = existing.scalars().first()

    if perf:
        if payload.actual_value is not None:
            perf.actual_value = payload.actual_value
    else:
        perf = ContractPerformance(
            contract_id=contract.id,
            period=payload.period,
            target_value=payload.target_value,
            actual_value=payload.actual_value or Decimal("0"),
            notes=payload.notes,
        )
        db.add(perf)

    await db.flush()

    if perf.target_value and perf.actual_value is not None and _D(perf.target_value) > 0:
        perf.achievement_pct = (_D(perf.actual_value) / _D(perf.target_value)) * 100

    # Calculate rebate earned from active rebates
    rebates_result = await db.execute(
        select(ContractRebate).where(
            ContractRebate.contract_id == contract.id,
            ContractRebate.active_flag == True,
        )
    )
    rebates = rebates_result.scalars().all()
    total_rebate = Decimal("0")
    for r in rebates:
        if perf.actual_value is not None:
            actual = _D(perf.actual_value)
            if r.threshold is None or actual >= _D(r.threshold):
                if r.rebate_pct:
                    total_rebate += actual * _D(r.rebate_pct) / 100
                elif r.rebate_amount:
                    total_rebate += _D(r.rebate_amount)
    perf.rebate_earned = total_rebate

    await db.commit()
    await db.refresh(perf)
    return perf


async def get_versions(db: AsyncSession, contract_id: uuid.UUID) -> List[ContractVersion]:
    result = await db.execute(
        select(ContractVersion)
        .where(ContractVersion.contract_id == contract_id)
        .order_by(ContractVersion.version_no.desc())
    )
    return result.scalars().all()


async def get_approvals(db: AsyncSession, contract_id: uuid.UUID) -> List[ContractApproval]:
    result = await db.execute(
        select(ContractApproval)
        .where(ContractApproval.contract_id == contract_id)
        .order_by(ContractApproval.created_at.desc())
    )
    return result.scalars().all()


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_summary(db: AsyncSession) -> Dict[str, Any]:
    today = date.today()
    total = (await db.execute(select(func.count()).select_from(Contract))).scalar_one()
    active = (await db.execute(select(func.count()).select_from(Contract).where(Contract.status == ContractStatus.ACTIVE.value))).scalar_one()
    expiring_30 = (await db.execute(
        select(func.count()).select_from(Contract).where(
            Contract.status == ContractStatus.ACTIVE.value,
            Contract.end_date.isnot(None),
            Contract.end_date <= today + timedelta(days=30),
            Contract.end_date >= today,
        )
    )).scalar_one()
    draft = (await db.execute(select(func.count()).select_from(Contract).where(Contract.status == ContractStatus.DRAFT.value))).scalar_one()
    under_review = (await db.execute(select(func.count()).select_from(Contract).where(Contract.status == ContractStatus.UNDER_REVIEW.value))).scalar_one()
    return {"total": total, "active": active, "expiring_30_days": expiring_30, "draft": draft, "under_review": under_review}


async def report_expiring(db: AsyncSession, days: int = 60) -> List[Contract]:
    cutoff = date.today() + timedelta(days=days)
    result = await db.execute(
        select(Contract).where(
            Contract.status == ContractStatus.ACTIVE.value,
            Contract.end_date.isnot(None),
            Contract.end_date <= cutoff,
            Contract.end_date >= date.today(),
        ).order_by(Contract.end_date)
    )
    return result.scalars().all()


async def report_performance(db: AsyncSession) -> List[Dict]:
    result = await db.execute(
        select(
            ContractPerformance.contract_id,
            func.avg(ContractPerformance.achievement_pct).label("avg_achievement"),
            func.sum(ContractPerformance.rebate_earned).label("total_rebate"),
            func.count().label("periods"),
        ).group_by(ContractPerformance.contract_id)
    )
    return [
        {
            "contract_id": str(r.contract_id),
            "avg_achievement_pct": float(r.avg_achievement or 0),
            "total_rebate_earned": float(r.total_rebate or 0),
            "periods": r.periods,
        }
        for r in result.all()
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[CTAIRecommendation]:
    recs: list[CTAIRecommendation] = []
    today = date.today()

    # Agent 1 — Risk Monitor: underperforming contracts (<60% achievement)
    perf_result = await db.execute(
        select(
            ContractPerformance.contract_id,
            func.avg(ContractPerformance.achievement_pct).label("avg_ach"),
        ).group_by(ContractPerformance.contract_id)
        .having(func.avg(ContractPerformance.achievement_pct) < 60)
        .having(func.avg(ContractPerformance.achievement_pct).isnot(None))
    )
    for row in perf_result.all():
        contract = await db.get(Contract, row.contract_id)
        if not contract or contract.status != ContractStatus.ACTIVE.value:
            continue
        rec = CTAIRecommendation(
            agent_type=CTAIAgentType.RISK_MONITOR.value,
            severity="WARNING",
            contract_id=row.contract_id,
            party_id=contract.party_id,
            title=f"Contract underperforming: {round(float(row.avg_ach or 0), 1)}% average achievement",
            body=(
                f"Contract '{contract.contract_name}' is averaging {round(float(row.avg_ach or 0), 1)}% "
                "target achievement. Review whether volume targets are realistic, check if the party is "
                "purchasing through alternate channels, and consider whether rebate tiers need adjustment."
            ),
            data={"avg_achievement_pct": float(row.avg_ach or 0)},
        )
        db.add(rec)
        recs.append(rec)

    # Agent 2 — Renewal Advisor: contracts expiring in 45 days
    cutoff_45 = today + timedelta(days=45)
    exp_result = await db.execute(
        select(Contract).where(
            Contract.status == ContractStatus.ACTIVE.value,
            Contract.end_date.isnot(None),
            Contract.end_date <= cutoff_45,
            Contract.end_date >= today,
            Contract.auto_renew == False,
        )
    )
    for contract in exp_result.scalars().all():
        days_left = (contract.end_date - today).days
        rec = CTAIRecommendation(
            agent_type=CTAIAgentType.RENEWAL_ADVISOR.value,
            severity="WARNING" if days_left <= 14 else "INFO",
            contract_id=contract.id,
            party_id=contract.party_id,
            title=f"Contract '{contract.contract_code}' expires in {days_left} days",
            body=(
                f"Contract '{contract.contract_name}' expires on {contract.end_date}. "
                f"Auto-renew is disabled. Initiate renewal negotiation with the party. "
                "Review current commercial terms vs market rates before renewal."
            ),
            data={"end_date": str(contract.end_date), "days_left": days_left},
        )
        db.add(rec)
        recs.append(rec)

    # Agent 3 — Compliance Monitor: high rebate accrual contracts (>500k KES unsettled)
    rebate_result = await db.execute(
        select(
            ContractRebate.contract_id,
            func.sum(ContractRebate.accrued_amount - ContractRebate.settled_amount).label("unsettled"),
        ).group_by(ContractRebate.contract_id)
        .having(func.sum(ContractRebate.accrued_amount - ContractRebate.settled_amount) > 500000)
    )
    for row in rebate_result.all():
        contract = await db.get(Contract, row.contract_id)
        if not contract:
            continue
        rec = CTAIRecommendation(
            agent_type=CTAIAgentType.COMPLIANCE_MONITOR.value,
            severity="WARNING",
            contract_id=row.contract_id,
            party_id=contract.party_id if contract else None,
            title=f"Large unsettled rebate balance: KES {float(row.unsettled or 0):,.0f}",
            body=(
                f"Contract '{contract.contract_name if contract else row.contract_id}' has an unsettled "
                f"rebate balance of KES {float(row.unsettled or 0):,.0f}. "
                "Review rebate settlement schedule and process outstanding claims to avoid disputes."
            ),
            data={"unsettled_amount": float(row.unsettled or 0)},
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        await db.commit()
    return recs


async def list_ai_recs(
    db: AsyncSession, agent_type: Optional[str] = None, status: Optional[str] = None
) -> List[CTAIRecommendation]:
    q = select(CTAIRecommendation)
    if agent_type:
        q = q.where(CTAIRecommendation.agent_type == agent_type)
    if status:
        q = q.where(CTAIRecommendation.status == status)
    result = await db.execute(q.order_by(CTAIRecommendation.created_at.desc()).limit(100))
    return result.scalars().all()


async def ack_ai_rec(
    db: AsyncSession, rec_id: uuid.UUID, payload: CTAIRecAck
) -> Optional[CTAIRecommendation]:
    rec = await db.get(CTAIRecommendation, rec_id)
    if rec:
        rec.status = payload.status
        await db.commit()
        await db.refresh(rec)
    return rec


# ── Contract resolution (for order integration) ───────────────────────────────

async def find_active_contract(
    db: AsyncSession, party_id: uuid.UUID, party_type: str
) -> Optional[Contract]:
    today = date.today()
    result = await db.execute(
        select(Contract).options(
            selectinload(Contract.terms),
            selectinload(Contract.rebates),
        ).where(
            Contract.party_id == party_id,
            Contract.party_type == party_type,
            Contract.status == ContractStatus.ACTIVE.value,
            Contract.start_date <= today,
            or_(Contract.end_date.is_(None), Contract.end_date >= today),
        ).order_by(Contract.start_date.desc())
    )
    return result.scalars().first()
