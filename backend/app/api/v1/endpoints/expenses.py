from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.expenses import ExpenseStatus, AdvanceSettlementStatus, ExpAIRecStatus
from app.schemas.expenses import (
    ExpenseCategoryCreate, ExpenseCategoryRead,
    ExpensePolicyCreate, ExpensePolicyRead,
    ExpenseClaimCreate, ExpenseClaimRead,
    ExpenseClaimApproveReject, ExpenseClaimPayRequest,
    ExpenseClaimLineCreate,
    ExpenseAdvanceCreate, ExpenseAdvanceRead,
    ExpenseAdvanceSettle,
    ExpenseDashboardResponse,
    ExpAIRecRead, ExpAIRecAck,
)
from app.services import expenses_service as svc

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ExpenseDashboardResponse)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[ExpenseCategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await svc.list_categories(db)


@router.post("/categories", response_model=ExpenseCategoryRead)
async def create_category(data: ExpenseCategoryCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_category(db, data)


@router.get("/categories/{category_id}", response_model=ExpenseCategoryRead)
async def get_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    cat = await svc.get_category(db, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.patch("/categories/{category_id}", response_model=ExpenseCategoryRead)
async def update_category(category_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    cat = await svc.update_category(db, category_id, data)
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


# ── Policies ──────────────────────────────────────────────────────────────────

@router.get("/policies", response_model=List[ExpensePolicyRead])
async def list_policies(db: AsyncSession = Depends(get_db)):
    return await svc.list_policies(db)


@router.post("/policies", response_model=ExpensePolicyRead)
async def create_policy(data: ExpensePolicyCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_policy(db, data)


@router.get("/policies/{policy_id}", response_model=ExpensePolicyRead)
async def get_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    pol = await svc.get_policy(db, policy_id)
    if not pol:
        raise HTTPException(404, "Policy not found")
    return pol


# ── Claims ────────────────────────────────────────────────────────────────────

@router.get("/claims", response_model=List[ExpenseClaimRead])
async def list_claims(
    employee_id: Optional[UUID] = None,
    status: Optional[ExpenseStatus] = None,
    department_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_claims(db, employee_id=employee_id, status=status, department_id=department_id, skip=skip, limit=limit)


@router.post("/claims", response_model=ExpenseClaimRead)
async def create_claim(data: ExpenseClaimCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_claim(db, data)


@router.get("/claims/{claim_id}", response_model=ExpenseClaimRead)
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    claim = await svc.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    return claim


@router.post("/claims/{claim_id}/lines", response_model=ExpenseClaimRead)
async def add_line(claim_id: UUID, data: ExpenseClaimLineCreate, db: AsyncSession = Depends(get_db)):
    claim = await svc.add_line(db, claim_id, data)
    if not claim:
        raise HTTPException(400, "Cannot add line — claim not in DRAFT or not found")
    return claim


@router.post("/claims/{claim_id}/submit", response_model=ExpenseClaimRead)
async def submit_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    claim = await svc.submit_claim(db, claim_id)
    if not claim:
        raise HTTPException(400, "Cannot submit — claim has blocking policy violations or wrong status")
    return claim


@router.post("/claims/{claim_id}/manager-approve", response_model=ExpenseClaimRead)
async def manager_approve(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db)):
    claim = await svc.manager_approve_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot approve — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/finance-approve", response_model=ExpenseClaimRead)
async def finance_approve(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db)):
    claim = await svc.finance_approve_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot approve — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/reject", response_model=ExpenseClaimRead)
async def reject_claim(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db)):
    claim = await svc.reject_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot reject — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/return", response_model=ExpenseClaimRead)
async def return_for_correction(claim_id: UUID, notes: str = Query(...), db: AsyncSession = Depends(get_db)):
    claim = await svc.return_for_correction(db, claim_id, notes)
    if not claim:
        raise HTTPException(400, "Cannot return — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/pay", response_model=ExpenseClaimRead)
async def pay_claim(claim_id: UUID, req: ExpenseClaimPayRequest, db: AsyncSession = Depends(get_db)):
    claim = await svc.pay_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot pay — claim not finance-approved or not found")
    return claim


# ── Advances ──────────────────────────────────────────────────────────────────

@router.get("/advances", response_model=List[ExpenseAdvanceRead])
async def list_advances(
    employee_id: Optional[UUID] = None,
    status: Optional[AdvanceSettlementStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_advances(db, employee_id=employee_id, status=status)


@router.post("/advances", response_model=ExpenseAdvanceRead)
async def create_advance(data: ExpenseAdvanceCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_advance(db, data)


@router.get("/advances/{advance_id}", response_model=ExpenseAdvanceRead)
async def get_advance(advance_id: UUID, db: AsyncSession = Depends(get_db)):
    adv = await svc.get_advance(db, advance_id)
    if not adv:
        raise HTTPException(404, "Advance not found")
    return adv


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/by-employee")
async def report_by_employee(db: AsyncSession = Depends(get_db)):
    return await svc.report_by_employee(db)


@router.get("/reports/by-category")
async def report_by_category(db: AsyncSession = Depends(get_db)):
    return await svc.report_by_category(db)


@router.get("/reports/policy-violations")
async def report_violations(db: AsyncSession = Depends(get_db)):
    violations = await svc.report_policy_violations(db)
    return [{"expense_line_id": str(v.expense_line_id), "receipt_no": v.receipt_no,
             "claimed_amount": str(v.claimed_amount), "note": v.policy_violation_note,
             "severity": v.policy_violation_severity} for v in violations]


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-risk-monitor")
async def run_risk_monitor(db: AsyncSession = Depends(get_db)):
    count = await svc.run_risk_monitor(db)
    return {"generated": count}


@router.post("/ai/run-policy-optimizer")
async def run_policy_optimizer(db: AsyncSession = Depends(get_db)):
    count = await svc.run_policy_optimizer(db)
    return {"generated": count}


@router.post("/ai/run-reimbursement-assistant")
async def run_reimbursement_assistant(db: AsyncSession = Depends(get_db)):
    count = await svc.run_reimbursement_assistant(db)
    return {"generated": count}


@router.get("/ai/recommendations", response_model=List[ExpAIRecRead])
async def list_recs(status: Optional[ExpAIRecStatus] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=ExpAIRecRead)
async def ack_rec(rec_id: UUID, data: ExpAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec
