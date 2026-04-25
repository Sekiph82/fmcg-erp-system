"""Bank Reconciliation — API Endpoints"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.bank_reconciliation import BRStatementStatus, BRAIRecStatus
from app.schemas.bank_reconciliation import (
    BRBankAccountCreate, BRBankAccountOut, BRBankAccountUpdate,
    BRStatementCreate, BRStatementOut,
    BRStatementLineCreate, BRStatementLineOut,
    BRMatchCreate, BRMatchOut,
    ManualMatchRequest, SplitMatchRequest,
    BRRuleCreate, BRRuleOut, BRRuleUpdate,
    BRAdjustmentCreate, BRAdjustmentOut,
    CSVImportRequest,
    BRDashboard, BROpenItemRow, BRBalanceSummaryRow,
    BRAIRecOut,
)
from app.services import bank_reconciliation_service as svc

router = APIRouter()


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=BRDashboard)
async def dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.get_dashboard(db)


# ─── Bank Accounts ────────────────────────────────────────────────────────────

@router.post("/accounts", response_model=BRBankAccountOut, status_code=201)
async def create_account(data: BRBankAccountCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_bank_account(db, data)


@router.get("/accounts", response_model=List[BRBankAccountOut])
async def list_accounts(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_bank_accounts(db, active_only)


@router.get("/accounts/{account_id}", response_model=BRBankAccountOut)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.get_bank_account(db, account_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/accounts/{account_id}", response_model=BRBankAccountOut)
async def update_account(account_id: UUID, data: BRBankAccountUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_bank_account(db, account_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ─── Statements ───────────────────────────────────────────────────────────────

@router.post("/statements", response_model=BRStatementOut, status_code=201)
async def create_statement(data: BRStatementCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_statement(db, data)


@router.post("/statements/import", response_model=BRStatementOut, status_code=201)
async def import_statement(data: CSVImportRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.import_statement(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/statements", response_model=List[BRStatementOut])
async def list_statements(
    bank_account_id: Optional[UUID] = Query(None),
    status: Optional[BRStatementStatus] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_statements(db, bank_account_id, status, limit)


@router.get("/statements/{stmt_id}", response_model=BRStatementOut)
async def get_statement(stmt_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.get_statement(db, stmt_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/statements/{stmt_id}/lines", response_model=List[BRStatementLineOut])
async def get_lines(stmt_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.get_statement_lines(db, stmt_id)


@router.post("/statements/{stmt_id}/lines", response_model=BRStatementLineOut, status_code=201)
async def add_line(stmt_id: UUID, data: BRStatementLineCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.add_manual_line(db, stmt_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/statements/{stmt_id}/auto-match")
async def auto_match(
    stmt_id: UUID,
    confidence_threshold: float = Query(0.70),
    auto_apply_threshold: float = Query(0.90),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.run_auto_match(db, stmt_id, confidence_threshold, auto_apply_threshold)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/statements/{stmt_id}/close", response_model=BRStatementOut)
async def close_statement(
    stmt_id: UUID,
    closed_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.close_statement(db, stmt_id, closed_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/statements/{stmt_id}/lock", response_model=BRStatementOut)
async def lock_statement(
    stmt_id: UUID,
    locked_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.lock_statement(db, stmt_id, locked_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/statements/{stmt_id}/reopen", response_model=BRStatementOut)
async def reopen_statement(
    stmt_id: UUID,
    reopened_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.reopen_statement(db, stmt_id, reopened_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/statements/{stmt_id}/report", response_model=dict)
async def statement_report(stmt_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.report_match_summary(db, stmt_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/statements/{stmt_id}/adjustments", response_model=List[BRAdjustmentOut])
async def list_adjustments(stmt_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_adjustments(db, stmt_id)


@router.get("/statements/{stmt_id}/ai-recs", response_model=List[BRAIRecOut])
async def list_stmt_ai_recs(stmt_id: UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, stmt_id=stmt_id)


# ─── Line Actions ─────────────────────────────────────────────────────────────

@router.post("/lines/{line_id}/manual-match", response_model=BRMatchOut, status_code=201)
async def manual_match(
    line_id: UUID,
    req: ManualMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.manual_match(db, line_id, req)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/lines/{line_id}/split-match", response_model=List[BRMatchOut], status_code=201)
async def split_match(
    line_id: UUID,
    req: SplitMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.split_match(db, line_id, req)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/lines/{line_id}/unmatch", response_model=BRStatementLineOut)
async def unmatch_line(line_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.unmatch_line(db, line_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/lines/{line_id}/ignore", response_model=BRStatementLineOut)
async def ignore_line(
    line_id: UUID,
    notes: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.mark_line_ignored(db, line_id, notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/matches/{match_id}/confirm", response_model=BRMatchOut)
async def confirm_match(
    match_id: UUID,
    approved_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.confirm_suggestion(db, match_id, approved_by)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Adjustments ─────────────────────────────────────────────────────────────

@router.post("/adjustments", response_model=BRAdjustmentOut, status_code=201)
async def create_adjustment(data: BRAdjustmentCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_adjustment(db, data)


@router.post("/adjustments/{adj_id}/post", response_model=BRAdjustmentOut)
async def post_adjustment(
    adj_id: UUID,
    posted_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.post_adjustment(db, adj_id, posted_by)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ─── Rules ────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=List[BRRuleOut])
async def list_rules(
    bank_account_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_rules(db, bank_account_id)


@router.post("/rules", response_model=BRRuleOut, status_code=201)
async def create_rule(data: BRRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_rule(db, data)


@router.patch("/rules/{rule_id}", response_model=BRRuleOut)
async def update_rule(rule_id: UUID, data: BRRuleUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_rule(db, rule_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    await svc.delete_rule(db, rule_id)


# ─── Open Items ───────────────────────────────────────────────────────────────

@router.get("/open-items", response_model=List[BROpenItemRow])
async def open_items(
    bank_account_id: Optional[UUID] = Query(None),
    min_days: int = Query(0),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_open_items(db, bank_account_id, min_days, limit)


# ─── Balance Summary ──────────────────────────────────────────────────────────

@router.get("/balance-summary", response_model=List[BRBalanceSummaryRow])
async def balance_summary(db: AsyncSession = Depends(get_db)):
    return await svc.get_balance_summary(db)


# ─── Reports ─────────────────────────────────────────────────────────────────

@router.get("/reports/unreconciled")
async def report_unreconciled(db: AsyncSession = Depends(get_db)):
    return await svc.report_unreconciled(db)


@router.get("/reports/aged-open-items")
async def report_aged(db: AsyncSession = Depends(get_db)):
    return await svc.report_aged_open_items(db)


# ─── AI ───────────────────────────────────────────────────────────────────────

@router.post("/ai/run")
async def run_ai(
    stmt_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.run_ai(db, stmt_id)


@router.get("/ai/recs", response_model=List[BRAIRecOut])
async def list_ai_recs(
    status: Optional[BRAIRecStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, status)


@router.post("/ai/recs/{rec_id}/action", response_model=BRAIRecOut)
async def action_rec(
    rec_id: UUID,
    status: BRAIRecStatus,
    actioned_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.action_ai_rec(db, rec_id, status, actioned_by)
    except ValueError as e:
        raise HTTPException(404, str(e))
