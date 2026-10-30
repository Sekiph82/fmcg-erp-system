"""M34.S01.T004 award allocation and approval workflow acceptance."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import (
    approve_rfq_award,
    create_rfq_award_proposal,
    reject_rfq_award,
    update_rfq,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import (
    ProcurementApprovalDocumentType,
    ProcurementApprovalRule,
    RFQAward,
    RFQAwardApprovalStatus,
    RFQAwardStatus,
    RFQLine,
    RFQRequest,
    RFQResponse,
    RFQResponseLineQuote,
    RFQResponseStatus,
    RFQStatus,
)
from app.models.user import User
from app.schemas.procurement import RFQAwardDecision, RFQAwardProposalCreate, RFQUpdate


TASK_DB_ENV = "M34_S01_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S01_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s01_t004_[a-f0-9]{24}")


def _is_task_database(url, expected_name: str | None) -> bool:
    return bool(
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and TASK_DB_PATTERN.fullmatch(expected_name)
        and url.database == expected_name
    )


def _require_task_database() -> None:
    expected_name = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1":
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for the task-owned disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's exact passwordless loopback database.")


def test_award_proposal_schema_rejects_duplicate_bids_bad_quantities_and_empty_reason():
    response_id = uuid4()
    with pytest.raises(ValueError):
        RFQAwardProposalCreate(
            allocations=[
                {"response_id": response_id, "quantity": "1"},
                {"response_id": response_id, "quantity": "2"},
            ],
            justification="Split",
        )
    for value in ("0", "-1", "NaN", "Infinity", "100000000000", "1.0001"):
        with pytest.raises(ValueError):
            RFQAwardProposalCreate(
                allocations=[{"response_id": uuid4(), "quantity": value}],
                justification="Valid reason",
            )
    with pytest.raises(ValueError):
        RFQAwardProposalCreate(
            allocations=[{"response_id": uuid4(), "quantity": "1"}],
            justification="  ",
        )


def test_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s01_t004_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_split_award_uses_configured_approval_levels_and_retains_decisions():
    _require_task_database()
    suffix = uuid4().hex[:16]
    proposer = User(
        email=f"m34-t004-proposer-{suffix}@example.invalid",
        username=f"m34t004p{suffix}",
        full_name="Synthetic award proposer",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    first_approver = User(
        email=f"m34-t004-first-{suffix}@example.invalid",
        username=f"m34t004a{suffix}",
        full_name="Synthetic level one approver",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    second_approver = User(
        email=f"m34-t004-second-{suffix}@example.invalid",
        username=f"m34t004b{suffix}",
        full_name="Synthetic level two approver",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    suppliers = [
        Supplier(code=f"M34T004-{suffix}-A", name="Synthetic supplier A", is_active=True),
        Supplier(code=f"M34T004-{suffix}-B", name="Synthetic supplier B", is_active=True),
        Supplier(code=f"M34T004-{suffix}-C", name="Synthetic supplier C", is_active=True),
    ]
    rfq_id = None
    async with AsyncSessionLocal() as db:
        db.add_all([proposer, first_approver, second_approver, *suppliers])
        await db.flush()
        rfq = RFQRequest(
            rfq_no=f"M34-T004-{suffix}",
            title="Synthetic multi-line split award",
            status=RFQStatus.RESPONSES_RECEIVED,
        )
        db.add(rfq)
        await db.flush()
        rfq_id = rfq.id
        lines = [
            RFQLine(rfq_id=rfq.id, line_no=1, description="Synthetic line one", quantity=Decimal("40.000"), unit="KG"),
            RFQLine(rfq_id=rfq.id, line_no=2, description="Synthetic line two", quantity=Decimal("60.000"), unit="L"),
        ]
        db.add_all(lines)
        await db.flush()
        responses = [
            RFQResponse(
                rfq_id=rfq.id,
                supplier_id=suppliers[0].id,
                quoted_currency="KES",
                status=RFQResponseStatus.SUBMITTED,
            ),
            RFQResponse(
                rfq_id=rfq.id,
                supplier_id=suppliers[1].id,
                quoted_currency="KES",
                status=RFQResponseStatus.SUBMITTED,
            ),
            RFQResponse(
                rfq_id=rfq.id,
                supplier_id=suppliers[2].id,
                quoted_currency="KES",
                status=RFQResponseStatus.SUBMITTED,
            ),
        ]
        db.add_all(responses)
        await db.flush()
        db.add_all([
            RFQResponseLineQuote(response_id=responses[0].id, rfq_line_id=lines[0].id, quoted_unit_price=Decimal("2.2500"), quoted_currency="KES"),
            RFQResponseLineQuote(response_id=responses[1].id, rfq_line_id=lines[0].id, quoted_unit_price=Decimal("3.1000"), quoted_currency="KES"),
            RFQResponseLineQuote(response_id=responses[0].id, rfq_line_id=lines[1].id, quoted_unit_price=Decimal("3.0000"), quoted_currency="KES"),
            RFQResponseLineQuote(response_id=responses[1].id, rfq_line_id=lines[1].id, quoted_unit_price=Decimal("2.5000"), quoted_currency="KES"),
            RFQResponseLineQuote(response_id=responses[2].id, rfq_line_id=lines[0].id, quoted_unit_price=Decimal("2.9000"), quoted_currency="KES"),
            RFQResponseLineQuote(response_id=responses[2].id, rfq_line_id=lines[1].id, quoted_unit_price=Decimal("2.8000"), quoted_currency="KES"),
        ])
        rules = [
            ProcurementApprovalRule(
                rule_name=f"M34 T004 level one {suffix}",
                document_type=ProcurementApprovalDocumentType.RFQ,
                approval_level=1,
                approver_user_id=first_approver.id,
                is_active=True,
            ),
            ProcurementApprovalRule(
                rule_name=f"M34 T004 level two {suffix}",
                document_type=ProcurementApprovalDocumentType.RFQ,
                approval_level=2,
                approver_user_id=second_approver.id,
                is_active=True,
            ),
            ProcurementApprovalRule(
                rule_name=f"M34 T004 USD only {suffix}",
                document_type=ProcurementApprovalDocumentType.RFQ,
                approval_level=3,
                approver_user_id=first_approver.id,
                min_amount=Decimal("1"),
                max_amount=Decimal("1000"),
                currency="USD",
                is_active=True,
            ),
        ]
        db.add_all(rules)
        await db.commit()

        try:
            actor = SimpleNamespace(id=proposer.id, is_superuser=True, roles=[])
            invalid_split = RFQAwardProposalCreate(
                allocations=[
                    {"response_id": responses[0].id, "rfq_line_id": lines[0].id, "quantity": "39.999"},
                    {"response_id": responses[0].id, "rfq_line_id": lines[1].id, "quantity": "60.000"},
                ],
                justification="Synthetic under-allocation rejection.",
            )
            with pytest.raises(HTTPException) as bad_total:
                await create_rfq_award_proposal(rfq.id, invalid_split, db, actor)
            assert bad_total.value.status_code == 422

            with pytest.raises(HTTPException) as direct_award:
                await update_rfq(
                    rfq.id,
                    RFQUpdate(status=RFQStatus.AWARDED, awarded_supplier_id=suppliers[0].id),
                    db,
                    actor,
                )
            assert direct_award.value.status_code == 409

            proposal = await create_rfq_award_proposal(
                rfq.id,
                RFQAwardProposalCreate(
                    allocations=[
                        {"response_id": responses[0].id, "rfq_line_id": lines[0].id, "quantity": "10.000"},
                        {"response_id": responses[1].id, "rfq_line_id": lines[0].id, "quantity": "30.000"},
                        {"response_id": responses[0].id, "rfq_line_id": lines[1].id, "quantity": "40.000"},
                        {"response_id": responses[1].id, "rfq_line_id": lines[1].id, "quantity": "20.000"},
                    ],
                    justification="Synthetic split meets available supplier quantities.",
                ),
                db,
                actor,
            )
            assert proposal.status == RFQAwardStatus.PENDING_APPROVAL
            assert proposal.total_amount == Decimal("285.5000000")
            assert len(proposal.allocations) == 4
            assert {row.approval_level for row in proposal.approvals} == {1, 2}
            assert all("USD only" not in row.rule_name for row in proposal.approvals)

            with pytest.raises(HTTPException) as wrong_level:
                await approve_rfq_award(
                    rfq.id,
                    proposal.id,
                    RFQAwardDecision(),
                    db,
                    SimpleNamespace(id=second_approver.id, is_superuser=True, roles=[]),
                )
            assert wrong_level.value.status_code == 403

            pending = await approve_rfq_award(
                rfq.id,
                proposal.id,
                RFQAwardDecision(comments="Level one approved."),
                db,
                SimpleNamespace(id=first_approver.id, is_superuser=True, roles=[]),
            )
            assert pending.status == RFQAwardStatus.PENDING_APPROVAL
            assert {row.approval_level for row in pending.approvals if row.decision_status == RFQAwardApprovalStatus.PENDING} == {2}

            complete = await approve_rfq_award(
                rfq.id,
                proposal.id,
                RFQAwardDecision(comments="Level two approved."),
                db,
                SimpleNamespace(id=second_approver.id, is_superuser=True, roles=[]),
            )
            assert complete.status == RFQAwardStatus.APPROVED
            assert complete.decided_at is not None
            assert all(row.decided_by_id is not None and row.decided_at is not None for row in complete.approvals)
            persisted_rfq = await db.get(RFQRequest, rfq.id)
            assert persisted_rfq.status == RFQStatus.AWARDED
            assert persisted_rfq.awarded_supplier_id is None
            persisted_responses = (
                await db.execute(select(RFQResponse).where(RFQResponse.rfq_id == rfq.id))
            ).scalars().all()
            response_statuses = {response.id: response.status for response in persisted_responses}
            assert response_statuses[responses[0].id] == RFQResponseStatus.AWARDED
            assert response_statuses[responses[1].id] == RFQResponseStatus.AWARDED
            assert response_statuses[responses[2].id] == RFQResponseStatus.REJECTED

            # Approval records remain after the RFQ reaches its terminal awarded state.
            persisted_awards = (
                await db.execute(select(RFQAward).where(RFQAward.rfq_id == rfq.id))
            ).scalars().all()
            assert len(persisted_awards) == 1

            rejection_rfq = RFQRequest(
                rfq_no=f"M34-T004-REJECT-{suffix}",
                title="Synthetic rejected award",
                quantity=Decimal("10.000"),
                unit="KG",
                status=RFQStatus.RESPONSES_RECEIVED,
            )
            db.add(rejection_rfq)
            await db.flush()
            rejection_bid = RFQResponse(
                rfq_id=rejection_rfq.id,
                supplier_id=suppliers[0].id,
                quoted_unit_price=Decimal("4.0000"),
                quoted_currency="KES",
                status=RFQResponseStatus.SUBMITTED,
            )
            db.add(rejection_bid)
            await db.commit()
            rejected_proposal = await create_rfq_award_proposal(
                rejection_rfq.id,
                RFQAwardProposalCreate(
                    allocations=[{"response_id": rejection_bid.id, "quantity": "10.000"}],
                    justification="Synthetic proposal rejected for testing.",
                ),
                db,
                actor,
            )
            rejected = await reject_rfq_award(
                rejection_rfq.id,
                rejected_proposal.id,
                RFQAwardDecision(comments="Synthetic rejection reason."),
                db,
                SimpleNamespace(id=first_approver.id, is_superuser=True, roles=[]),
            )
            assert rejected.status == RFQAwardStatus.REJECTED
            assert {row.decision_status for row in rejected.approvals} == {
                RFQAwardApprovalStatus.REJECTED,
                RFQAwardApprovalStatus.SKIPPED,
            }
            assert all(row.decided_by_id is not None and row.decided_at is not None for row in rejected.approvals)
            rejection_rfq_state = await db.get(RFQRequest, rejection_rfq.id)
            assert rejection_rfq_state.status == RFQStatus.RESPONSES_RECEIVED
        finally:
            await db.rollback()
