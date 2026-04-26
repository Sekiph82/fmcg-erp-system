"""Contract Management API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.contracts import (
    ContractCreate, ContractUpdate, ContractOut,
    ContractTermCreate, ContractTermOut,
    ContractRebateCreate, ContractRebateOut,
    PerformanceCreate, PerformanceOut,
    ApprovalCreate, ApprovalOut,
    VersionOut, TerminateRequest,
    CTAIRecOut, CTAIRecAck,
)
from app.services import contracts_service as svc

router = APIRouter()


def _404(label: str = "Contract"):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


# ── Contracts CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=List[ContractOut])
async def list_contracts(
    party_type: Optional[str] = None,
    status: Optional[str] = None,
    party_id: Optional[UUID] = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_contracts(db, party_type=party_type, status=status, party_id=party_id, skip=skip, limit=limit)


@router.post("", response_model=ContractOut, status_code=201)
async def create_contract(payload: ContractCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_contract(db, payload, user_id=None)


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return c


@router.patch("/{contract_id}", response_model=ContractOut)
async def update_contract(contract_id: UUID, payload: ContractUpdate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.update_contract(db, c, payload, user_id=None)


# ── Lifecycle transitions ─────────────────────────────────────────────────────

@router.post("/{contract_id}/submit", response_model=ContractOut)
async def submit(contract_id: UUID, payload: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.submit_for_approval(db, c, user_id=None, comments=payload.comments)


@router.post("/{contract_id}/approve", response_model=ContractOut)
async def approve(contract_id: UUID, payload: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.approve_contract(db, c, user_id=None, comments=payload.comments)


@router.post("/{contract_id}/reject", response_model=ContractOut)
async def reject(contract_id: UUID, payload: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.reject_contract(db, c, user_id=None, comments=payload.comments)


@router.post("/{contract_id}/activate", response_model=ContractOut)
async def activate(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.activate_contract(db, c, user_id=None)


@router.post("/{contract_id}/terminate", response_model=ContractOut)
async def terminate(contract_id: UUID, payload: TerminateRequest, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.terminate_contract(db, c, payload, user_id=None)


@router.post("/{contract_id}/archive", response_model=ContractOut)
async def archive(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.archive_contract(db, c)


# ── Terms ─────────────────────────────────────────────────────────────────────

@router.post("/{contract_id}/terms", response_model=ContractTermOut, status_code=201)
async def add_term(contract_id: UUID, payload: ContractTermCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.add_term(db, c, payload)


@router.delete("/terms/{term_id}", status_code=204)
async def delete_term(term_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await svc.delete_term(db, term_id)
    if not deleted:
        raise _404("Term")


# ── Rebates ───────────────────────────────────────────────────────────────────

@router.post("/{contract_id}/rebates", response_model=ContractRebateOut, status_code=201)
async def add_rebate(contract_id: UUID, payload: ContractRebateCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.add_rebate(db, c, payload)


# ── Performance ───────────────────────────────────────────────────────────────

@router.get("/{contract_id}/performance", response_model=List[PerformanceOut])
async def list_performance(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_performance(db, contract_id)


@router.post("/{contract_id}/performance", response_model=PerformanceOut, status_code=201)
async def upsert_performance(contract_id: UUID, payload: PerformanceCreate, db: AsyncSession = Depends(get_db)):
    c = await svc.get_contract(db, contract_id)
    if not c:
        raise _404()
    return await svc.upsert_performance(db, c, payload)


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/{contract_id}/history", response_model=List[VersionOut])
async def get_history(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_versions(db, contract_id)


@router.get("/{contract_id}/approvals", response_model=List[ApprovalOut])
async def get_approvals(contract_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_approvals(db, contract_id)


# ── Lookup for orders ─────────────────────────────────────────────────────────

@router.get("/lookup/party/{party_id}", response_model=Optional[ContractOut])
async def lookup_contract(
    party_id: UUID,
    party_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.find_active_contract(db, party_id, party_type)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/summary", response_model=Dict[str, Any])
async def report_summary(db: AsyncSession = Depends(get_db)):
    return await svc.report_summary(db)


@router.get("/reports/expiring", response_model=List[ContractOut])
async def report_expiring(days: int = 60, db: AsyncSession = Depends(get_db)):
    return await svc.report_expiring(db, days=days)


@router.get("/reports/performance", response_model=List[Dict])
async def report_performance(db: AsyncSession = Depends(get_db)):
    return await svc.report_performance(db)


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run", response_model=List[CTAIRecOut], status_code=201)
async def run_ai(db: AsyncSession = Depends(get_db)):
    return await svc.run_ai_agents(db)


@router.get("/ai/recommendations", response_model=List[CTAIRecOut])
async def ai_recs(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=CTAIRecOut)
async def ack_rec(rec_id: UUID, payload: CTAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise _404("Recommendation")
    return rec
