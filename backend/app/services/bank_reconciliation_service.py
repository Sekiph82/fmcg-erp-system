"""
Bank Reconciliation Service
- Bank account CRUD
- Statement import (CSV, M-Pesa, manual)
- Auto-match engine
- Manual / split match
- Close / lock / reopen workflow
- Adjustments
- Reports & dashboard
- 3 AI agents
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_reconciliation import (
    BRBankAccount, BRStatement, BRStatementLine, BRMatch, BRRule,
    BRAdjustment, BRAIRecommendation,
    BRStatementStatus, BRLineMatchStatus, BRMatchMethod, BRERPTransactionType,
    BRAIAgentType, BRAIRecStatus, BRImportSource,
)
from app.schemas.bank_reconciliation import (
    BRBankAccountCreate, BRBankAccountUpdate,
    BRStatementCreate, BRStatementLineCreate,
    BRMatchCreate, ManualMatchRequest, SplitMatchRequest,
    BRRuleCreate, BRRuleUpdate,
    BRAdjustmentCreate,
    CSVImportRequest,
    BRDashboard, BROpenItemRow, BRBalanceSummaryRow,
)


def _D(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_ref(ref: Optional[str]) -> Optional[str]:
    """Strip spaces, uppercase, remove common noise."""
    if not ref:
        return None
    return re.sub(r"[^A-Z0-9]", "", ref.upper())


def _normalize_narr(narr: Optional[str]) -> Optional[str]:
    if not narr:
        return None
    return " ".join(narr.upper().split())


async def _next_statement_no(db: AsyncSession) -> str:
    result = await db.execute(
        select(func.count()).select_from(BRStatement)
    )
    n = (result.scalar() or 0) + 1
    return f"STMT-{n:06d}"


# ─── Bank Account ─────────────────────────────────────────────────────────────

async def create_bank_account(db: AsyncSession, data: BRBankAccountCreate) -> BRBankAccount:
    obj = BRBankAccount(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_bank_accounts(db: AsyncSession, active_only: bool = True) -> List[BRBankAccount]:
    q = select(BRBankAccount)
    if active_only:
        q = q.where(BRBankAccount.active == True)
    result = await db.execute(q.order_by(BRBankAccount.bank_name))
    return result.scalars().all()


async def get_bank_account(db: AsyncSession, account_id: uuid.UUID) -> BRBankAccount:
    result = await db.execute(select(BRBankAccount).where(BRBankAccount.id == account_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"Bank account {account_id} not found")
    return obj


async def update_bank_account(db: AsyncSession, account_id: uuid.UUID, data: BRBankAccountUpdate) -> BRBankAccount:
    obj = await get_bank_account(db, account_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ─── Statement CRUD ───────────────────────────────────────────────────────────

async def create_statement(db: AsyncSession, data: BRStatementCreate) -> BRStatement:
    stmt_no = await _next_statement_no(db)
    obj = BRStatement(
        statement_no=stmt_no,
        **data.model_dump(),
        imported_at=_now() if data.import_source != BRImportSource.MANUAL else None,
        status=BRStatementStatus.DRAFT,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_statements(
    db: AsyncSession,
    bank_account_id: Optional[uuid.UUID] = None,
    status: Optional[BRStatementStatus] = None,
    limit: int = 50,
) -> List[BRStatement]:
    q = select(BRStatement)
    if bank_account_id:
        q = q.where(BRStatement.bank_account_id == bank_account_id)
    if status:
        q = q.where(BRStatement.status == status)
    q = q.order_by(BRStatement.statement_date.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_statement(db: AsyncSession, stmt_id: uuid.UUID) -> BRStatement:
    result = await db.execute(
        select(BRStatement).where(BRStatement.id == stmt_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"Statement {stmt_id} not found")
    return obj


# ─── Statement Line Import ────────────────────────────────────────────────────

async def _add_line(
    db: AsyncSession,
    stmt: BRStatement,
    line_no: int,
    line_data: BRStatementLineCreate,
) -> BRStatementLine:
    norm_ref  = _normalize_ref(line_data.external_reference or line_data.bank_reference)
    norm_narr = _normalize_narr(line_data.narration)
    amount    = abs(_D(line_data.amount))
    obj = BRStatementLine(
        statement_id=stmt.id,
        line_no=line_no,
        transaction_date=line_data.transaction_date,
        value_date=line_data.value_date,
        external_reference=line_data.external_reference,
        bank_reference=line_data.bank_reference,
        narration=line_data.narration,
        counterparty_name=line_data.counterparty_name,
        amount=amount,
        debit_credit_indicator=line_data.debit_credit_indicator.upper()[:1] or "C",
        running_balance=line_data.running_balance,
        normalized_reference=norm_ref,
        normalized_narration=norm_narr,
        unmatched_amount=amount,
        matched_amount=Decimal("0"),
    )
    db.add(obj)
    return obj


async def import_statement(db: AsyncSession, data: CSVImportRequest) -> BRStatement:
    """Import statement with lines (CSV/manual/M-Pesa)."""
    # Check for duplicate import (same account + same period)
    dup = await db.execute(
        select(BRStatement).where(
            and_(
                BRStatement.bank_account_id == data.bank_account_id,
                BRStatement.period_start_date == data.period_start_date,
                BRStatement.period_end_date == data.period_end_date,
                BRStatement.status != BRStatementStatus.DRAFT,
            )
        )
    )
    if dup.scalar_one_or_none():
        raise ValueError("A statement for this account/period has already been imported.")

    stmt_no = await _next_statement_no(db)
    stmt = BRStatement(
        statement_no=stmt_no,
        bank_account_id=data.bank_account_id,
        statement_date=data.statement_date,
        period_start_date=data.period_start_date,
        period_end_date=data.period_end_date,
        opening_balance=_D(data.opening_balance),
        closing_balance=_D(data.closing_balance),
        statement_currency=data.statement_currency,
        import_source=data.import_source,
        import_file_name=data.import_file_name if hasattr(data, "import_file_name") else None,
        status=BRStatementStatus.IMPORTED,
        imported_by=data.imported_by,
        imported_at=_now(),
        total_lines=len(data.lines),
    )
    db.add(stmt)
    await db.flush()

    total_credits = Decimal("0")
    total_debits  = Decimal("0")

    # Detect duplicate lines by reference+amount+date within the batch
    seen_keys: set = set()
    for i, line in enumerate(data.lines, start=1):
        key = (_normalize_ref(line.external_reference or line.bank_reference), str(line.amount), str(line.transaction_date))
        is_dup = key in seen_keys
        seen_keys.add(key)
        obj = await _add_line(db, stmt, i, line)
        obj.is_duplicate_suspected = is_dup
        dc = (line.debit_credit_indicator or "C").upper()[:1]
        if dc == "C":
            total_credits += abs(_D(line.amount))
        else:
            total_debits += abs(_D(line.amount))

    stmt.total_credits = total_credits
    stmt.total_debits  = total_debits

    await db.commit()
    await db.refresh(stmt)
    return stmt


async def add_manual_line(
    db: AsyncSession,
    stmt_id: uuid.UUID,
    line_data: BRStatementLineCreate,
) -> BRStatementLine:
    stmt = await get_statement(db, stmt_id)
    if stmt.status in (BRStatementStatus.CLOSED, BRStatementStatus.LOCKED):
        raise ValueError("Cannot add lines to a closed/locked statement.")
    result = await db.execute(
        select(func.count()).select_from(BRStatementLine).where(BRStatementLine.statement_id == stmt_id)
    )
    line_no = (result.scalar() or 0) + 1
    obj = await _add_line(db, stmt, line_no, line_data)
    stmt.total_lines = line_no
    dc = (line_data.debit_credit_indicator or "C").upper()[:1]
    if dc == "C":
        stmt.total_credits = _D(stmt.total_credits) + abs(_D(line_data.amount))
    else:
        stmt.total_debits = _D(stmt.total_debits) + abs(_D(line_data.amount))
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_statement_lines(db: AsyncSession, stmt_id: uuid.UUID) -> List[BRStatementLine]:
    result = await db.execute(
        select(BRStatementLine)
        .where(BRStatementLine.statement_id == stmt_id)
        .order_by(BRStatementLine.line_no)
    )
    return result.scalars().all()


# ─── Auto-Match Engine ────────────────────────────────────────────────────────

def _score_match(
    line: BRStatementLine,
    tx_amount: Decimal,
    tx_date: Optional[date],
    tx_reference: Optional[str],
    tx_description: Optional[str],
    tx_mpesa_receipt: Optional[str],
) -> float:
    score = 0.0
    line_amount = _D(line.amount)

    # Amount scoring
    if tx_amount > Decimal("0"):
        diff_pct = abs(line_amount - tx_amount) / tx_amount
        if diff_pct == 0:
            score += 0.45
        elif diff_pct < Decimal("0.005"):  # within 0.5%
            score += 0.35
        elif diff_pct < Decimal("0.02"):   # within 2%
            score += 0.15
        else:
            return 0.0  # amount mismatch is disqualifying

    # Date proximity
    if tx_date and line.transaction_date:
        delta = abs((line.transaction_date - tx_date).days)
        if delta == 0:
            score += 0.20
        elif delta <= 1:
            score += 0.12
        elif delta <= 3:
            score += 0.06

    # Reference match
    norm_line_ref = line.normalized_reference or ""
    if tx_mpesa_receipt:
        norm_mpesa = _normalize_ref(tx_mpesa_receipt) or ""
        if norm_mpesa and norm_mpesa in norm_line_ref or norm_line_ref in norm_mpesa:
            score += 0.25

    if tx_reference:
        norm_tx_ref = _normalize_ref(tx_reference) or ""
        if norm_tx_ref and norm_line_ref and (norm_tx_ref in norm_line_ref or norm_line_ref in norm_tx_ref):
            score += 0.20

    # Narration match
    norm_line_narr = line.normalized_narration or ""
    if tx_description:
        norm_tx_desc = _normalize_narr(tx_description) or ""
        if norm_tx_desc and norm_line_narr:
            words = norm_tx_desc.split()
            if any(w in norm_line_narr for w in words if len(w) > 3):
                score += 0.10

    return min(score, 1.0)


async def run_auto_match(
    db: AsyncSession,
    stmt_id: uuid.UUID,
    confidence_threshold: float = 0.70,
    auto_apply_threshold: float = 0.90,
) -> Dict[str, Any]:
    """
    Auto-match unmatched statement lines against cash_transactions.
    Returns summary of suggestions created and auto-applied.
    """
    stmt = await get_statement(db, stmt_id)
    if stmt.status == BRStatementStatus.LOCKED:
        raise ValueError("Cannot auto-match a locked statement.")

    # Update status to IN_RECONCILIATION
    if stmt.status in (BRStatementStatus.IMPORTED, BRStatementStatus.DRAFT):
        stmt.status = BRStatementStatus.IN_RECONCILIATION

    # Load unmatched lines
    lines_result = await db.execute(
        select(BRStatementLine).where(
            and_(
                BRStatementLine.statement_id == stmt_id,
                BRStatementLine.match_status.in_([
                    BRLineMatchStatus.UNMATCHED,
                    BRLineMatchStatus.SUGGESTED_MATCH,
                ]),
            )
        )
    )
    lines = lines_result.scalars().all()

    # Load candidate ERP transactions from cash_transactions
    # We query a window around the statement period
    try:
        txns_result = await db.execute(
            text("""
                SELECT id, transaction_date, direction, amount,
                       description, reference, mpesa_receipt, mpesa_name,
                       source_module, cash_account_id
                FROM cash_transactions
                WHERE transaction_date BETWEEN :start_dt AND :end_dt
                ORDER BY transaction_date
            """),
            {"start_dt": stmt.period_start_date, "end_dt": stmt.period_end_date},
        )
        txns = txns_result.fetchall()
    except Exception:
        txns = []

    # Build already-matched tx IDs
    matched_result = await db.execute(
        select(BRMatch.erp_transaction_id).where(
            and_(
                BRMatch.is_active == True,
                BRMatch.erp_transaction_type.in_([
                    BRERPTransactionType.AR_PAYMENT,
                    BRERPTransactionType.AP_PAYMENT,
                    BRERPTransactionType.MPESA_COLLECTION,
                    BRERPTransactionType.MPESA_PAYOUT,
                    BRERPTransactionType.PURCHASE_PAYMENT,
                ]),
            )
        )
    )
    already_matched_ids = {r[0] for r in matched_result.fetchall() if r[0]}

    # Apply reconciliation rules
    rules_result = await db.execute(
        select(BRRule).where(
            and_(
                BRRule.active == True,
                BRRule.auto_apply == True,
                or_(BRRule.bank_account_id == stmt.bank_account_id, BRRule.bank_account_id == None),
            )
        ).order_by(BRRule.priority)
    )
    rules = rules_result.scalars().all()

    suggestions_created = 0
    auto_applied = 0

    for line in lines:
        best_score = 0.0
        best_txn = None
        best_txn_type = BRERPTransactionType.JOURNAL_ENTRY

        # Rule-based matching first
        for rule in rules:
            ctype  = rule.condition_type.value
            cvalue = rule.condition_value.upper()
            narr   = line.normalized_narration or ""
            ref    = line.normalized_reference or ""
            match  = False

            if ctype == "NARRATION_CONTAINS" and cvalue in narr:
                match = True
            elif ctype == "REFERENCE_CONTAINS" and cvalue in ref:
                match = True
            elif ctype == "REFERENCE_STARTS_WITH" and ref.startswith(cvalue):
                match = True

            if match:
                rule_score = float(rule.confidence_weight)
                if rule_score > best_score:
                    best_score = rule_score
                    best_txn_type = rule.target_transaction_type

        # Transaction-based matching
        for txn in txns:
            txn_id = txn[0]
            if txn_id in already_matched_ids:
                continue
            txn_amount  = abs(_D(txn[2] if False else txn[3]))  # amount field
            txn_date    = txn[1]
            txn_desc    = txn[5]  # description
            txn_ref     = txn[6]  # reference
            txn_mpesa   = txn[7] if len(txn) > 7 else None  # mpesa_receipt
            src_module  = txn[9] if len(txn) > 9 else None

            score = _score_match(line, txn_amount, txn_date, txn_ref, txn_desc, txn_mpesa)
            if score > best_score:
                best_score = score
                best_txn = txn
                # Derive transaction type
                if txn_mpesa:
                    best_txn_type = (
                        BRERPTransactionType.MPESA_COLLECTION
                        if line.debit_credit_indicator == "C"
                        else BRERPTransactionType.MPESA_PAYOUT
                    )
                elif src_module == "payroll":
                    best_txn_type = BRERPTransactionType.PAYROLL
                elif src_module in ("purchase_payment", "ap"):
                    best_txn_type = BRERPTransactionType.PURCHASE_PAYMENT
                elif src_module in ("payment", "ar"):
                    best_txn_type = BRERPTransactionType.AR_PAYMENT
                else:
                    best_txn_type = (
                        BRERPTransactionType.AR_PAYMENT
                        if line.debit_credit_indicator == "C"
                        else BRERPTransactionType.AP_PAYMENT
                    )

        if best_score < confidence_threshold:
            continue

        # Create suggestion or auto-apply
        is_auto = best_score >= auto_apply_threshold
        method  = BRMatchMethod.AUTO if is_auto else BRMatchMethod.RULE_BASED

        # Deactivate any previous suggestions for this line
        await db.execute(
            text("UPDATE br_matches SET is_active = false WHERE statement_line_id = :lid AND is_active = true"),
            {"lid": str(line.id)},
        )

        match_obj = BRMatch(
            statement_line_id=line.id,
            erp_transaction_type=best_txn_type,
            erp_transaction_id=best_txn[0] if best_txn else None,
            erp_reference=best_txn[6] if best_txn else None,
            erp_transaction_date=best_txn[1] if best_txn else None,
            erp_amount=float(abs(_D(best_txn[3]))) if best_txn else None,
            erp_description=best_txn[5] if best_txn else None,
            matched_amount=float(line.unmatched_amount),
            match_method=method,
            confidence_score=best_score,
            is_active=True,
        )
        db.add(match_obj)

        if is_auto:
            line.match_status    = BRLineMatchStatus.MATCHED
            line.matched_amount  = line.amount
            line.unmatched_amount = Decimal("0")
            auto_applied += 1
        else:
            line.match_status = BRLineMatchStatus.SUGGESTED_MATCH
            suggestions_created += 1

        if best_txn:
            already_matched_ids.add(best_txn[0])

    await db.commit()

    return {
        "statement_id": str(stmt_id),
        "lines_processed": len(lines),
        "suggestions_created": suggestions_created,
        "auto_applied": auto_applied,
    }


# ─── Manual Match ─────────────────────────────────────────────────────────────

async def manual_match(
    db: AsyncSession,
    line_id: uuid.UUID,
    req: ManualMatchRequest,
) -> BRMatch:
    result = await db.execute(select(BRStatementLine).where(BRStatementLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise ValueError(f"Statement line {line_id} not found")

    stmt = await get_statement(db, line.statement_id)
    if stmt.status == BRStatementStatus.LOCKED:
        raise ValueError("Statement is locked.")

    matched_amount = _D(req.matched_amount)
    if matched_amount > _D(line.unmatched_amount):
        raise ValueError(f"Matched amount {matched_amount} exceeds unmatched balance {line.unmatched_amount}")

    match_obj = BRMatch(
        statement_line_id=line_id,
        erp_transaction_type=req.erp_transaction_type,
        erp_transaction_id=req.erp_transaction_id,
        erp_reference=req.erp_reference,
        erp_transaction_date=req.erp_transaction_date,
        erp_amount=req.erp_amount,
        erp_description=req.erp_description,
        matched_amount=matched_amount,
        match_method=BRMatchMethod.MANUAL,
        confidence_score=Decimal("1.0"),
        is_active=True,
        created_by=req.created_by,
        notes=req.notes,
    )
    db.add(match_obj)

    line.matched_amount  = _D(line.matched_amount) + matched_amount
    remaining = _D(line.amount) - _D(line.matched_amount)
    line.unmatched_amount = max(remaining, Decimal("0"))
    if line.unmatched_amount == Decimal("0"):
        line.match_status = BRLineMatchStatus.MATCHED
    else:
        line.match_status = BRLineMatchStatus.PARTIALLY_MATCHED

    await db.commit()
    await db.refresh(match_obj)
    return match_obj


async def split_match(
    db: AsyncSession,
    line_id: uuid.UUID,
    req: SplitMatchRequest,
) -> List[BRMatch]:
    total_requested = sum(_D(m.matched_amount) for m in req.matches)
    result = await db.execute(select(BRStatementLine).where(BRStatementLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise ValueError(f"Statement line {line_id} not found")

    if total_requested > _D(line.unmatched_amount) * Decimal("1.005"):  # 0.5% tolerance
        raise ValueError(f"Split total {total_requested} exceeds unmatched {line.unmatched_amount}")

    created = []
    for m in req.matches:
        obj = BRMatch(
            statement_line_id=line_id,
            erp_transaction_type=m.erp_transaction_type,
            erp_transaction_id=m.erp_transaction_id,
            erp_reference=m.erp_reference,
            erp_transaction_date=m.erp_transaction_date,
            erp_amount=m.erp_amount,
            erp_description=m.erp_description,
            matched_amount=_D(m.matched_amount),
            match_method=BRMatchMethod.SPLIT,
            confidence_score=Decimal("1.0"),
            is_active=True,
            created_by=m.created_by,
            notes=m.notes,
        )
        db.add(obj)
        created.append(obj)

    line.matched_amount  = _D(line.matched_amount) + total_requested
    remaining = _D(line.amount) - _D(line.matched_amount)
    line.unmatched_amount = max(remaining, Decimal("0"))
    if line.unmatched_amount == Decimal("0"):
        line.match_status = BRLineMatchStatus.MATCHED
    else:
        line.match_status = BRLineMatchStatus.PARTIALLY_MATCHED

    await db.commit()
    for obj in created:
        await db.refresh(obj)
    return created


async def unmatch_line(db: AsyncSession, line_id: uuid.UUID) -> BRStatementLine:
    result = await db.execute(select(BRStatementLine).where(BRStatementLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise ValueError(f"Statement line {line_id} not found")

    # Soft-delete all active matches
    await db.execute(
        text("UPDATE br_matches SET is_active = false WHERE statement_line_id = :lid"),
        {"lid": str(line_id)},
    )
    line.matched_amount   = Decimal("0")
    line.unmatched_amount = line.amount
    line.match_status     = BRLineMatchStatus.UNMATCHED

    await db.commit()
    await db.refresh(line)
    return line


async def mark_line_ignored(db: AsyncSession, line_id: uuid.UUID, notes: Optional[str] = None) -> BRStatementLine:
    result = await db.execute(select(BRStatementLine).where(BRStatementLine.id == line_id))
    line = result.scalar_one_or_none()
    if not line:
        raise ValueError(f"Statement line {line_id} not found")
    line.match_status        = BRLineMatchStatus.IGNORED
    line.reconciliation_notes = notes
    await db.commit()
    await db.refresh(line)
    return line


async def confirm_suggestion(db: AsyncSession, match_id: uuid.UUID, approved_by: Optional[str] = None) -> BRMatch:
    result = await db.execute(select(BRMatch).where(BRMatch.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise ValueError(f"Match {match_id} not found")
    match.match_method = BRMatchMethod.AUTO
    match.approved_by  = approved_by
    match.approved_at  = _now()

    # Update line status
    line_result = await db.execute(select(BRStatementLine).where(BRStatementLine.id == match.statement_line_id))
    line = line_result.scalar_one_or_none()
    if line:
        line.matched_amount  = _D(line.matched_amount) + _D(match.matched_amount)
        remaining = _D(line.amount) - _D(line.matched_amount)
        line.unmatched_amount = max(remaining, Decimal("0"))
        line.match_status = BRLineMatchStatus.MATCHED if line.unmatched_amount == Decimal("0") else BRLineMatchStatus.PARTIALLY_MATCHED

    await db.commit()
    await db.refresh(match)
    return match


# ─── Close / Lock / Reopen ────────────────────────────────────────────────────

async def close_statement(db: AsyncSession, stmt_id: uuid.UUID, closed_by: Optional[str] = None) -> BRStatement:
    stmt = await get_statement(db, stmt_id)
    if stmt.status == BRStatementStatus.LOCKED:
        raise ValueError("Statement is already locked.")
    if stmt.status not in (BRStatementStatus.IN_RECONCILIATION, BRStatementStatus.RECONCILED, BRStatementStatus.IMPORTED):
        raise ValueError(f"Cannot close statement in status {stmt.status}")

    stmt.status    = BRStatementStatus.CLOSED
    stmt.closed_by = closed_by
    stmt.closed_at = _now()
    await db.commit()
    await db.refresh(stmt)
    return stmt


async def lock_statement(db: AsyncSession, stmt_id: uuid.UUID, locked_by: Optional[str] = None) -> BRStatement:
    stmt = await get_statement(db, stmt_id)
    if stmt.status != BRStatementStatus.CLOSED:
        raise ValueError("Only closed statements can be locked.")
    stmt.status    = BRStatementStatus.LOCKED
    stmt.closed_by = locked_by or stmt.closed_by
    await db.commit()
    await db.refresh(stmt)
    return stmt


async def reopen_statement(db: AsyncSession, stmt_id: uuid.UUID, reopened_by: Optional[str] = None) -> BRStatement:
    stmt = await get_statement(db, stmt_id)
    if stmt.status not in (BRStatementStatus.CLOSED, BRStatementStatus.LOCKED):
        raise ValueError(f"Cannot reopen statement in status {stmt.status}")
    stmt.status    = BRStatementStatus.IN_RECONCILIATION
    stmt.closed_by = None
    stmt.closed_at = None
    await db.commit()
    await db.refresh(stmt)
    return stmt


# ─── Adjustments ─────────────────────────────────────────────────────────────

async def create_adjustment(db: AsyncSession, data: BRAdjustmentCreate) -> BRAdjustment:
    obj = BRAdjustment(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def post_adjustment(db: AsyncSession, adj_id: uuid.UUID, posted_by: Optional[str] = None) -> BRAdjustment:
    result = await db.execute(select(BRAdjustment).where(BRAdjustment.id == adj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"Adjustment {adj_id} not found")
    obj.posted    = True
    obj.posted_by = posted_by
    obj.posted_at = _now()
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_adjustments(db: AsyncSession, stmt_id: uuid.UUID) -> List[BRAdjustment]:
    result = await db.execute(
        select(BRAdjustment).where(BRAdjustment.statement_id == stmt_id)
    )
    return result.scalars().all()


# ─── Rules ────────────────────────────────────────────────────────────────────

async def create_rule(db: AsyncSession, data: BRRuleCreate) -> BRRule:
    obj = BRRule(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_rules(db: AsyncSession, bank_account_id: Optional[uuid.UUID] = None) -> List[BRRule]:
    q = select(BRRule)
    if bank_account_id:
        q = q.where(or_(BRRule.bank_account_id == bank_account_id, BRRule.bank_account_id == None))
    result = await db.execute(q.order_by(BRRule.priority))
    return result.scalars().all()


async def update_rule(db: AsyncSession, rule_id: uuid.UUID, data: BRRuleUpdate) -> BRRule:
    result = await db.execute(select(BRRule).where(BRRule.id == rule_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"Rule {rule_id} not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_rule(db: AsyncSession, rule_id: uuid.UUID) -> None:
    result = await db.execute(select(BRRule).where(BRRule.id == rule_id))
    obj = result.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()


# ─── Open Items ───────────────────────────────────────────────────────────────

async def get_open_items(
    db: AsyncSession,
    bank_account_id: Optional[uuid.UUID] = None,
    min_days: int = 0,
    limit: int = 200,
) -> List[BROpenItemRow]:
    q = (
        select(
            BRStatementLine.id,
            BRStatement.statement_no,
            BRBankAccount.account_name,
            BRStatementLine.transaction_date,
            BRStatementLine.amount,
            BRStatementLine.debit_credit_indicator,
            BRStatementLine.unmatched_amount,
            BRStatementLine.match_status,
            BRStatementLine.narration,
        )
        .join(BRStatement, BRStatementLine.statement_id == BRStatement.id)
        .join(BRBankAccount, BRStatement.bank_account_id == BRBankAccount.id)
        .where(
            BRStatementLine.match_status.in_([
                BRLineMatchStatus.UNMATCHED,
                BRLineMatchStatus.PARTIALLY_MATCHED,
                BRLineMatchStatus.SUGGESTED_MATCH,
                BRLineMatchStatus.NEEDS_REVIEW,
            ])
        )
    )
    if bank_account_id:
        q = q.where(BRBankAccount.id == bank_account_id)
    q = q.order_by(BRStatementLine.transaction_date).limit(limit)

    result = await db.execute(q)
    rows = result.fetchall()
    today = date.today()

    items = []
    for r in rows:
        days = (today - r[3]).days if r[3] else 0
        if days >= min_days:
            items.append(BROpenItemRow(
                line_id=r[0],
                statement_no=r[1],
                bank_account_name=r[2],
                transaction_date=r[3],
                amount=float(r[4]),
                debit_credit=r[5],
                unmatched_amount=float(r[6]),
                match_status=r[7],
                narration=r[8],
                days_outstanding=days,
            ))
    return items


# ─── Balance Summary ──────────────────────────────────────────────────────────

async def get_balance_summary(db: AsyncSession) -> List[BRBalanceSummaryRow]:
    accounts_result = await db.execute(
        select(BRBankAccount).where(BRBankAccount.active == True)
    )
    accounts = accounts_result.scalars().all()
    rows = []
    for acc in accounts:
        # Latest statement
        stmt_result = await db.execute(
            select(BRStatement)
            .where(BRStatement.bank_account_id == acc.id)
            .order_by(BRStatement.statement_date.desc())
            .limit(1)
        )
        stmt = stmt_result.scalar_one_or_none()

        # ERP book balance from cash_account
        erp_balance = 0.0
        if acc.cash_account_id:
            try:
                cb_result = await db.execute(
                    text("SELECT current_balance FROM cash_accounts WHERE id = :cid"),
                    {"cid": str(acc.cash_account_id)},
                )
                row = cb_result.fetchone()
                if row:
                    erp_balance = float(row[0])
            except Exception:
                pass

        stmt_closing = float(stmt.closing_balance) if stmt else 0.0
        variance = stmt_closing - erp_balance

        rows.append(BRBalanceSummaryRow(
            bank_account_id=acc.id,
            bank_account_name=acc.account_name,
            currency=acc.currency,
            last_statement_no=stmt.statement_no if stmt else None,
            statement_closing=stmt_closing,
            erp_book_balance=erp_balance,
            variance=variance,
            status="MATCHED" if abs(variance) < 1.0 else "VARIANCE",
        ))
    return rows


# ─── Dashboard ────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> BRDashboard:
    total_accounts = (await db.execute(
        select(func.count()).select_from(BRBankAccount).where(BRBankAccount.active == True)
    )).scalar() or 0

    active_stmts = (await db.execute(
        select(func.count()).select_from(BRStatement).where(
            BRStatement.status.in_([BRStatementStatus.IN_RECONCILIATION, BRStatementStatus.IMPORTED])
        )
    )).scalar() or 0

    unmatched = (await db.execute(
        select(func.count()).select_from(BRStatementLine).where(
            BRStatementLine.match_status == BRLineMatchStatus.UNMATCHED
        )
    )).scalar() or 0

    partial = (await db.execute(
        select(func.count()).select_from(BRStatementLine).where(
            BRStatementLine.match_status == BRLineMatchStatus.PARTIALLY_MATCHED
        )
    )).scalar() or 0

    unmatched_amt = (await db.execute(
        select(func.coalesce(func.sum(BRStatementLine.unmatched_amount), 0)).where(
            BRStatementLine.match_status.in_([
                BRLineMatchStatus.UNMATCHED, BRLineMatchStatus.PARTIALLY_MATCHED
            ])
        )
    )).scalar() or 0

    in_recon = (await db.execute(
        select(func.count()).select_from(BRStatement).where(
            BRStatement.status == BRStatementStatus.IN_RECONCILIATION
        )
    )).scalar() or 0

    locked = (await db.execute(
        select(func.count()).select_from(BRStatement).where(
            BRStatement.status == BRStatementStatus.LOCKED
        )
    )).scalar() or 0

    pending_ai = (await db.execute(
        select(func.count()).select_from(BRAIRecommendation).where(
            BRAIRecommendation.status == BRAIRecStatus.PENDING
        )
    )).scalar() or 0

    recent_result = await db.execute(
        select(BRStatement).order_by(BRStatement.created_at.desc()).limit(5)
    )
    recent = recent_result.scalars().all()

    return BRDashboard(
        total_accounts=total_accounts,
        active_statements=active_stmts,
        unmatched_items=unmatched,
        partially_matched_items=partial,
        total_unmatched_amount=float(unmatched_amt),
        statements_in_recon=in_recon,
        statements_locked=locked,
        pending_ai_recs=pending_ai,
        recent_statements=recent,
    )


# ─── Reports ──────────────────────────────────────────────────────────────────

async def report_unreconciled(db: AsyncSession) -> List[Dict]:
    result = await db.execute(
        select(
            BRBankAccount.account_name,
            BRStatement.statement_no,
            BRStatement.period_end_date,
            func.count(BRStatementLine.id).label("unmatched_lines"),
            func.coalesce(func.sum(BRStatementLine.unmatched_amount), 0).label("unmatched_total"),
        )
        .join(BRStatement, BRStatement.bank_account_id == BRBankAccount.id)
        .join(BRStatementLine, BRStatementLine.statement_id == BRStatement.id)
        .where(BRStatementLine.match_status == BRLineMatchStatus.UNMATCHED)
        .group_by(BRBankAccount.account_name, BRStatement.statement_no, BRStatement.period_end_date)
        .order_by(BRStatement.period_end_date)
    )
    rows = result.fetchall()
    return [
        {
            "account_name": r[0],
            "statement_no": r[1],
            "period_end_date": str(r[2]),
            "unmatched_lines": r[3],
            "unmatched_total": float(r[4]),
        }
        for r in rows
    ]


async def report_match_summary(db: AsyncSession, stmt_id: uuid.UUID) -> Dict:
    stmt = await get_statement(db, stmt_id)

    totals = (await db.execute(
        select(
            BRStatementLine.match_status,
            func.count(BRStatementLine.id),
            func.coalesce(func.sum(BRStatementLine.amount), 0),
            func.coalesce(func.sum(BRStatementLine.matched_amount), 0),
            func.coalesce(func.sum(BRStatementLine.unmatched_amount), 0),
        )
        .where(BRStatementLine.statement_id == stmt_id)
        .group_by(BRStatementLine.match_status)
    )).fetchall()

    by_status = {
        r[0].value: {
            "count": r[1],
            "total_amount": float(r[2]),
            "matched_amount": float(r[3]),
            "unmatched_amount": float(r[4]),
        }
        for r in totals
    }

    return {
        "statement_no": stmt.statement_no,
        "period": f"{stmt.period_start_date} → {stmt.period_end_date}",
        "opening_balance": float(stmt.opening_balance),
        "closing_balance": float(stmt.closing_balance),
        "total_credits": float(stmt.total_credits),
        "total_debits": float(stmt.total_debits),
        "by_status": by_status,
    }


async def report_aged_open_items(db: AsyncSession) -> List[Dict]:
    items = await get_open_items(db, limit=500)
    buckets: Dict[str, Dict] = {
        "0-7 days": {"count": 0, "total": 0.0},
        "8-30 days": {"count": 0, "total": 0.0},
        "31-90 days": {"count": 0, "total": 0.0},
        "90+ days": {"count": 0, "total": 0.0},
    }
    for item in items:
        d = item.days_outstanding
        amt = item.unmatched_amount
        if d <= 7:
            b = "0-7 days"
        elif d <= 30:
            b = "8-30 days"
        elif d <= 90:
            b = "31-90 days"
        else:
            b = "90+ days"
        buckets[b]["count"] += 1
        buckets[b]["total"] += amt

    return [{"bucket": k, **v} for k, v in buckets.items()]


# ─── AI Agents ────────────────────────────────────────────────────────────────

async def _agent_match_confidence(db: AsyncSession) -> int:
    """Flag statement lines with large unmatched amounts and no suggestions."""
    result = await db.execute(
        select(BRStatementLine)
        .join(BRStatement, BRStatementLine.statement_id == BRStatement.id)
        .where(
            and_(
                BRStatementLine.match_status == BRLineMatchStatus.UNMATCHED,
                BRStatementLine.unmatched_amount > 50000,
                BRStatement.status == BRStatementStatus.IN_RECONCILIATION,
            )
        )
        .limit(10)
    )
    lines = result.scalars().all()
    created = 0
    for line in lines:
        # Check no existing rec
        existing = (await db.execute(
            select(func.count()).select_from(BRAIRecommendation).where(
                and_(
                    BRAIRecommendation.statement_line_id == line.id,
                    BRAIRecommendation.status == BRAIRecStatus.PENDING,
                    BRAIRecommendation.agent_type == BRAIAgentType.MATCH_CONFIDENCE,
                )
            )
        )).scalar() or 0
        if existing:
            continue
        rec = BRAIRecommendation(
            statement_id=line.statement_id,
            statement_line_id=line.id,
            agent_type=BRAIAgentType.MATCH_CONFIDENCE,
            title=f"Large unmatched line: {float(line.unmatched_amount):,.2f} {line.debit_credit_indicator}",
            explanation=f"Statement line dated {line.transaction_date} with amount {float(line.unmatched_amount):,.2f} has no match candidate. "
                        f"Narration: {line.narration or 'N/A'}. "
                        "Review ERP payments/receipts for this date range.",
            impact_summary=f"Unmatched cash of {float(line.unmatched_amount):,.2f}",
            suggested_action="Search ERP cash transactions within ±3 days of this line's date with matching amount.",
            priority="HIGH",
            confidence_score=Decimal("0.85"),
        )
        db.add(rec)
        created += 1
    return created


async def _agent_cash_anomaly(db: AsyncSession) -> int:
    """Detect spikes in unmatched items or suspicious duplicate-looking lines."""
    result = await db.execute(
        select(BRStatementLine)
        .where(
            and_(
                BRStatementLine.is_duplicate_suspected == True,
                BRStatementLine.match_status != BRLineMatchStatus.IGNORED,
            )
        )
        .limit(20)
    )
    lines = result.scalars().all()
    created = 0
    for line in lines:
        existing = (await db.execute(
            select(func.count()).select_from(BRAIRecommendation).where(
                and_(
                    BRAIRecommendation.statement_line_id == line.id,
                    BRAIRecommendation.status == BRAIRecStatus.PENDING,
                    BRAIRecommendation.agent_type == BRAIAgentType.CASH_ANOMALY,
                )
            )
        )).scalar() or 0
        if existing:
            continue
        rec = BRAIRecommendation(
            statement_id=line.statement_id,
            statement_line_id=line.id,
            agent_type=BRAIAgentType.CASH_ANOMALY,
            title=f"Duplicate-suspected statement line: {float(line.amount):,.2f}",
            explanation=f"This statement line (ref: {line.external_reference or 'N/A'}, "
                        f"date: {line.transaction_date}) appears to be a duplicate within the imported statement. "
                        "Verify with the bank before reconciling.",
            impact_summary="Risk of double-matching a duplicate transaction",
            suggested_action="Contact bank to confirm if this line is a genuine transaction or a processing duplicate.",
            priority="HIGH",
            confidence_score=Decimal("0.90"),
        )
        db.add(rec)
        created += 1

    # Also flag accounts with >20 unmatched lines older than 30 days
    try:
        old_result = await db.execute(
            select(
                BRStatement.bank_account_id,
                func.count(BRStatementLine.id).label("cnt"),
            )
            .join(BRStatement, BRStatementLine.statement_id == BRStatement.id)
            .where(
                and_(
                    BRStatementLine.match_status == BRLineMatchStatus.UNMATCHED,
                    BRStatementLine.transaction_date <= text("CURRENT_DATE - INTERVAL '30 days'"),
                )
            )
            .group_by(BRStatement.bank_account_id)
            .having(func.count(BRStatementLine.id) > 20)
        )
        for row in old_result.fetchall():
            rec = BRAIRecommendation(
                agent_type=BRAIAgentType.CASH_ANOMALY,
                title=f"Account has {row[1]} unmatched items older than 30 days",
                explanation="High volume of aged unmatched items suggests systemic matching failure. "
                            "Review ERP transaction completeness for this bank account.",
                impact_summary=f"{row[1]} lines unreconciled > 30 days",
                suggested_action="Run auto-match for the affected statements and review any missing ERP entries.",
                priority="MEDIUM",
                confidence_score=Decimal("0.80"),
            )
            db.add(rec)
            created += 1
    except Exception:
        pass

    return created


async def _agent_rule_optimizer(db: AsyncSession) -> int:
    """Suggest new rules based on recurring manual match patterns."""
    # Find most common erp_transaction_type for MANUAL matches
    result = await db.execute(
        select(
            BRMatch.erp_transaction_type,
            func.count(BRMatch.id).label("cnt"),
        )
        .where(BRMatch.match_method == BRMatchMethod.MANUAL, BRMatch.is_active == True)
        .group_by(BRMatch.erp_transaction_type)
        .having(func.count(BRMatch.id) >= 5)
        .order_by(func.count(BRMatch.id).desc())
        .limit(3)
    )
    rows = result.fetchall()
    created = 0
    for row in rows:
        tx_type, cnt = row
        existing = (await db.execute(
            select(func.count()).select_from(BRAIRecommendation).where(
                and_(
                    BRAIRecommendation.agent_type == BRAIAgentType.RULE_OPTIMIZER,
                    BRAIRecommendation.status == BRAIRecStatus.PENDING,
                    BRAIRecommendation.title.ilike(f"%{tx_type.value}%"),
                )
            )
        )).scalar() or 0
        if existing:
            continue
        rec = BRAIRecommendation(
            agent_type=BRAIAgentType.RULE_OPTIMIZER,
            title=f"Create auto-match rule for {tx_type.value} transactions ({cnt} manual matches)",
            explanation=f"{cnt} manual matches of type {tx_type.value} suggest a pattern rule could automate this. "
                        "Review the common narration/reference patterns for these matches.",
            impact_summary=f"Potential to automate {cnt}+ future matches",
            suggested_action=f"Create a NARRATION_CONTAINS or REFERENCE_CONTAINS rule targeting {tx_type.value}.",
            priority="LOW",
            confidence_score=Decimal("0.70"),
        )
        db.add(rec)
        created += 1
    return created


async def run_ai(db: AsyncSession, stmt_id: Optional[uuid.UUID] = None) -> Dict:
    c1 = await _agent_match_confidence(db)
    c2 = await _agent_cash_anomaly(db)
    c3 = await _agent_rule_optimizer(db)
    await db.commit()
    return {"recommendations_created": c1 + c2 + c3, "by_agent": {"MATCH_CONFIDENCE": c1, "CASH_ANOMALY": c2, "RULE_OPTIMIZER": c3}}


async def list_ai_recs(
    db: AsyncSession,
    status: Optional[BRAIRecStatus] = None,
    stmt_id: Optional[uuid.UUID] = None,
) -> List[BRAIRecommendation]:
    q = select(BRAIRecommendation)
    if status:
        q = q.where(BRAIRecommendation.status == status)
    if stmt_id:
        q = q.where(BRAIRecommendation.statement_id == stmt_id)
    q = q.order_by(BRAIRecommendation.created_at.desc()).limit(100)
    result = await db.execute(q)
    return result.scalars().all()


async def action_ai_rec(
    db: AsyncSession,
    rec_id: uuid.UUID,
    status: BRAIRecStatus,
    actioned_by: Optional[str] = None,
) -> BRAIRecommendation:
    result = await db.execute(select(BRAIRecommendation).where(BRAIRecommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise ValueError(f"Recommendation {rec_id} not found")
    rec.status      = status
    rec.actioned_by = actioned_by
    rec.actioned_at = _now()
    await db.commit()
    await db.refresh(rec)
    return rec
