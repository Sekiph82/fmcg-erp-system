from __future__ import annotations
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
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

# Every employee may file and follow their own claims/advances; everything else needs a finance/HR right
# (before M38 the whole module was open to any login — with self-service every employee is a login).
# Advances are cash handed out by finance, so finance records them (finance.edit); employees see their own.
_OWN = {("POST", "/claims"), ("GET", "/claims"), ("GET", "/advances"),
        ("GET", "/claims/{claim_id}"), ("GET", "/advances/{advance_id}"), ("POST", "/claims/{claim_id}/lines"),
        ("POST", "/claims/{claim_id}/submit"), ("GET", "/categories"), ("GET", "/categories/{category_id}"),
        ("GET", "/policies"), ("GET", "/policies/{policy_id}")}
_NEEDS = {"/claims/{claim_id}/manager-approve": ("hr.approve", "finance.approve"),
          "/claims/{claim_id}/finance-approve": ("finance.approve",), "/claims/{claim_id}/pay": ("finance.approve",),
          "/claims/{claim_id}/reject": ("hr.approve", "finance.approve"),
          "/claims/{claim_id}/return": ("hr.approve", "finance.approve")}
PRIVILEGED = ("finance.view", "hr.view")


async def _gate(request: Request, current_user=Depends(get_current_user)):
    from app.core.access_control import has_any_permission

    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    path = path[path.index("/expenses") + len("/expenses"):] if "/expenses" in path else path
    if (request.method, path) in _OWN:
        return current_user
    needed = _NEEDS.get(path) or (PRIVILEGED if request.method == "GET" else ("finance.edit",))
    if not has_any_permission(current_user, needed):
        raise HTTPException(403, "You do not have permission for this expense action.")
    return current_user


async def _scope(db: AsyncSession, user):
    """None = may see everyone's claims (finance/HR); else the user's own employee id."""
    from sqlalchemy import select

    from app.core.access_control import has_any_permission
    from app.models.hr import Employee

    if has_any_permission(user, PRIVILEGED):
        return None
    me = (await db.execute(select(Employee.id).where(Employee.user_id == user.id).limit(1))).scalar_one_or_none()
    return me or UUID(int=0)


async def _approver(db: AsyncSession, claim_id: UUID, req, current_user, stage: str):
    """The signed-in user approves; never their own claim, and finance approval by someone other than the manager."""
    from sqlalchemy import select

    from app.models.hr import Employee

    claim = await svc.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(404, "Claim not found")
    owner_user = (await db.execute(select(Employee.user_id).where(Employee.id == claim.employee_id))).scalar_one_or_none()
    if owner_user is not None and owner_user == current_user.id:
        raise HTTPException(403, "You cannot approve or reject your own claim.")
    if stage == "finance" and claim.approved_by_manager == current_user.id:
        raise HTTPException(403, "Finance approval must be done by someone other than the approving manager.")
    req.approver_id = current_user.id
    return claim


def _own_or_404(obj, scope):
    if obj is None or (scope is not None and obj.employee_id != scope):
        raise HTTPException(404, "Not found")
    return obj


router = APIRouter(dependencies=[Depends(_gate)])


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
    current_user=Depends(get_current_user),
):
    scope = await _scope(db, current_user)
    if scope is not None:
        employee_id = scope  # employees see only their own claims
    return await svc.list_claims(db, employee_id=employee_id, status=status, department_id=department_id, skip=skip, limit=limit)


@router.post("/claims", response_model=ExpenseClaimRead)
async def create_claim(data: ExpenseClaimCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """A claim is the signed-in employee's own; only HR (hr.edit) may file one for someone else."""
    from sqlalchemy import select

    from app.core.access_control import has_permission
    from app.models.hr import Employee

    me = (await db.execute(select(Employee.id).where(Employee.user_id == current_user.id).limit(1))).scalar_one_or_none()
    if data.employee_id is None or data.employee_id != me:
        if data.employee_id is not None and has_permission(current_user, "hr.edit"):
            pass
        elif me is None:
            raise HTTPException(403, "Your login is not linked to an employee record; ask HR.")
        else:
            data.employee_id = me
    if data.advance_id is not None:  # only the claimant's own advance can be deducted
        adv = await svc.get_advance(db, data.advance_id)
        if adv is None or adv.employee_id != data.employee_id:
            raise HTTPException(422, "The advance does not belong to this employee.")
    claim = await svc.create_claim(db, data)
    return await svc.get_claim(db, claim.expense_claim_id)  # reload with lines (the bare instance cannot lazy-load them)


@router.get("/claims/{claim_id}", response_model=ExpenseClaimRead)
async def get_claim(claim_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return _own_or_404(await svc.get_claim(db, claim_id), await _scope(db, current_user))


@router.post("/claims/{claim_id}/lines", response_model=ExpenseClaimRead)
async def add_line(claim_id: UUID, data: ExpenseClaimLineCreate, db: AsyncSession = Depends(get_db),
                   current_user=Depends(get_current_user)):
    _own_or_404(await svc.get_claim(db, claim_id), await _scope(db, current_user))
    claim = await svc.add_line(db, claim_id, data)
    if not claim:
        raise HTTPException(400, "Cannot add line — claim not in DRAFT or not found")
    return claim


@router.post("/claims/{claim_id}/submit", response_model=ExpenseClaimRead)
async def submit_claim(claim_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _own_or_404(await svc.get_claim(db, claim_id), await _scope(db, current_user))
    claim = await svc.submit_claim(db, claim_id)
    if not claim:
        raise HTTPException(400, "Cannot submit — claim has blocking policy violations or wrong status")
    return claim


@router.post("/claims/{claim_id}/manager-approve", response_model=ExpenseClaimRead)
async def manager_approve(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    await _approver(db, claim_id, req, current_user, "manager")
    claim = await svc.manager_approve_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot approve — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/finance-approve", response_model=ExpenseClaimRead)
async def finance_approve(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    await _approver(db, claim_id, req, current_user, "finance")
    claim = await svc.finance_approve_claim(db, claim_id, req)
    if not claim:
        raise HTTPException(400, "Cannot approve — wrong status or not found")
    return claim


@router.post("/claims/{claim_id}/reject", response_model=ExpenseClaimRead)
async def reject_claim(claim_id: UUID, req: ExpenseClaimApproveReject, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    await _approver(db, claim_id, req, current_user, "reject")
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
async def pay_claim(claim_id: UUID, req: ExpenseClaimPayRequest, db: AsyncSession = Depends(get_db),
                    current_user=Depends(get_current_user)):
    await _approver(db, claim_id, ExpenseClaimApproveReject(), current_user, "pay")  # nobody pays their own claim
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
    current_user=Depends(get_current_user),
):
    scope = await _scope(db, current_user)
    return await svc.list_advances(db, employee_id=scope if scope is not None else employee_id, status=status)


@router.post("/advances", response_model=ExpenseAdvanceRead)
async def create_advance(data: ExpenseAdvanceCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Finance records the cash it hands to an employee (finance.edit, enforced by _gate); without an employee given,
    it is the signed-in finance user's own advance."""
    from sqlalchemy import select

    from app.core.access_control import has_permission
    from app.models.hr import Employee

    me = (await db.execute(select(Employee.id).where(Employee.user_id == current_user.id).limit(1))).scalar_one_or_none()
    if data.employee_id is None:
        if me is None:
            raise HTTPException(403, "Your login is not linked to an employee record; ask HR.")
        data.employee_id = me
    return await svc.create_advance(db, data)


@router.get("/advances/{advance_id}", response_model=ExpenseAdvanceRead)
async def get_advance(advance_id: UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return _own_or_404(await svc.get_advance(db, advance_id), await _scope(db, current_user))


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
