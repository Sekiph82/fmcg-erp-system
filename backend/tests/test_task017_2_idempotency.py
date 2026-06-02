"""
TASK-017.2: post_bill_to_finance idempotency via AccountingPostingBatch.

Tests:
1. Import check — all required symbols importable.
2. First call creates JournalEntry, marks batch POSTED.
3. Second call (batch=POSTED) returns same data without new rows.
4. Existing batch in non-POSTED state raises ValueError.
5. Bill already linked to journal (defensive guard) raises ValueError.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.finance import PostingBatchStatus
from app.services.utility_integration_service import post_bill_to_finance


def _make_bill(journal_entry_id=None):
    bill = MagicMock()
    bill.id = uuid4()
    bill.bill_no = "BILL-TEST-001"
    bill.invoice_date = None
    bill.total_amount = Decimal("1000.00")
    bill.currency_code = "USD"
    bill.journal_entry_id = journal_entry_id
    return bill


def _make_db(bill):
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = bill
    db.execute.return_value = execute_result
    return db


# ── 1. Import check ───────────────────────────────────────────────────────────

def test_imports_ok():
    from app.services.utility_integration_service import post_bill_to_finance
    from app.services.finance_service import get_or_create_posting_batch, validate_journal_lines_balance
    from app.models.finance import PostingBatchStatus, AccountingPostingBatch
    assert callable(post_bill_to_finance)
    assert callable(get_or_create_posting_batch)
    assert callable(validate_journal_lines_balance)
    assert PostingBatchStatus.POSTED
    assert PostingBatchStatus.DRAFT


# ── 2. First call creates JournalEntry and marks batch POSTED ─────────────────

async def test_first_call_creates_journal_and_marks_batch_posted():
    bill = _make_bill()
    db = _make_db(bill)

    batch_mock = MagicMock()
    batch_mock.status = PostingBatchStatus.DRAFT

    with patch(
        "app.services.utility_integration_service.get_or_create_posting_batch",
        new_callable=AsyncMock,
        return_value=(batch_mock, True),
    ):
        result = await post_bill_to_finance(
            db,
            bill_id=bill.id,
            debit_account_id=uuid4(),
            credit_account_id=uuid4(),
        )

    assert result["bill_id"] == bill.id
    assert result["journal_entry_id"] is not None
    assert result["entry_no"] == f"JE-UTIL-{bill.bill_no}"
    assert result["amount"] == Decimal("1000.00")
    # Batch marked POSTED
    assert batch_mock.status == PostingBatchStatus.POSTED
    # db.add called (journal entry, lines, bill, batch) + db.flush called
    assert db.add.called
    assert db.flush.called


# ── 3. Second call returns same data, no new JournalEntry ─────────────────────

async def test_second_call_idempotent_no_new_journal():
    existing_je_id = uuid4()
    bill = _make_bill(journal_entry_id=existing_je_id)
    db = _make_db(bill)

    batch_mock = MagicMock()
    batch_mock.status = PostingBatchStatus.POSTED

    with patch(
        "app.services.utility_integration_service.get_or_create_posting_batch",
        new_callable=AsyncMock,
        return_value=(batch_mock, False),  # already exists
    ):
        result = await post_bill_to_finance(
            db,
            bill_id=bill.id,
            debit_account_id=uuid4(),
            credit_account_id=uuid4(),
        )

    # Same journal_entry_id returned
    assert result["journal_entry_id"] == existing_je_id
    # No db.add called — nothing was created
    db.add.assert_not_called()
    # No db.flush called
    db.flush.assert_not_called()


# ── 4. Existing batch in non-POSTED state raises ValueError ───────────────────

async def test_incomplete_batch_raises_value_error():
    bill = _make_bill()
    db = _make_db(bill)

    for bad_status in (PostingBatchStatus.FAILED, PostingBatchStatus.DRAFT):
        batch_mock = MagicMock()
        batch_mock.status = bad_status  # real enum — .value works directly

        with patch(
            "app.services.utility_integration_service.get_or_create_posting_batch",
            new_callable=AsyncMock,
            return_value=(batch_mock, False),
        ):
            with pytest.raises(ValueError, match="incomplete posting batch"):
                await post_bill_to_finance(
                    db,
                    bill_id=bill.id,
                    debit_account_id=uuid4(),
                    credit_account_id=uuid4(),
                )


# ── 5. Defensive guard: journal_entry_id already set on new batch ─────────────

async def test_defensive_guard_existing_journal_entry_id_raises():
    existing_je_id = uuid4()
    bill = _make_bill(journal_entry_id=existing_je_id)
    db = _make_db(bill)

    batch_mock = MagicMock()
    batch_mock.status = PostingBatchStatus.DRAFT

    with patch(
        "app.services.utility_integration_service.get_or_create_posting_batch",
        new_callable=AsyncMock,
        return_value=(batch_mock, True),  # new batch, but bill already linked
    ):
        with pytest.raises(ValueError, match="already linked to journal"):
            await post_bill_to_finance(
                db,
                bill_id=bill.id,
                debit_account_id=uuid4(),
                credit_account_id=uuid4(),
            )
