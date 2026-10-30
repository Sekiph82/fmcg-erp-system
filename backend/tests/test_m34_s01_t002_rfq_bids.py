"""M34.S01.T002 RFQ invitation and bid workflow acceptance."""
from __future__ import annotations

import os
import re
import asyncio
from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.engine import URL
from fastapi import HTTPException

from app.api.v1.endpoints.procurement import add_rfq_response, create_rfq, get_rfq, issue_rfq_invitations, update_rfq
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import RFQRequest, RFQResponse, RFQInvitationStatus, RFQResponseStatus, RFQStatus
from app.schemas.procurement import RFQCreate, RFQResponseCreate, RFQUpdate


TASK_DB_ENV = "M34_S01_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S01_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s01_t002_[a-f0-9]{24}")


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


def test_quote_schema_enforces_finite_price_currency_and_lead_time():
    base = {
        "supplier_id": "2e706fc0-9f6c-4b0b-a7cf-6a9d9a579afe",
        "quoted_unit_price": "12.3456",
        "quoted_currency": "kes",
        "lead_time_days": 0,
    }
    valid = RFQResponseCreate(**base)
    assert valid.quoted_currency == "KES"
    assert valid.lead_time_days == 0

    for invalid in (
        {**base, "quoted_unit_price": "NaN"},
        {**base, "quoted_unit_price": "Infinity"},
        {**base, "quoted_unit_price": "10000000000"},
        {**base, "quoted_unit_price": "1.00001"},
        {**base, "quoted_unit_price": "0"},
        {**base, "quoted_currency": "US"},
        {**base, "lead_time_days": -1},
    ):
        with pytest.raises(ValueError):
            RFQResponseCreate(**invalid)


def test_rfqs_reject_duplicate_supplier_invites():
    supplier_id = "2e706fc0-9f6c-4b0b-a7cf-6a9d9a579afe"
    with pytest.raises(ValueError):
        RFQCreate(
            rfq_no="RFQ-DUPLICATE-INVITE",
            title="Synthetic event",
            quantity="1",
            supplier_ids=[supplier_id, supplier_id],
        )


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_invitation_issue_and_bid_submission_are_scoped_and_attributed():
    _require_task_database()
    suffix = uuid4().hex[:16]
    invited_supplier = Supplier(code=f"M34T002-{suffix}", name="Synthetic invited supplier", is_active=True)
    uninvited_supplier = Supplier(code=f"M34T002-X-{suffix}", name="Synthetic uninvited supplier", is_active=True)
    rfq_ids: list[object] = []
    race_rfq_id = None
    actor = SimpleNamespace(id=None, is_superuser=True, roles=[])
    async with AsyncSessionLocal() as db:
        db.add_all([invited_supplier, uninvited_supplier])
        await db.commit()
        try:
            race_rfq = RFQRequest(
                rfq_no=f"M34-T002-LOCK-{suffix}",
                title="Synthetic draft lock regression",
                quantity=1,
                unit="KG",
                status=RFQStatus.DRAFT,
            )
            db.add(race_rfq)
            await db.commit()
            race_rfq_id = race_rfq.id
            locker = AsyncSessionLocal()
            updater = AsyncSessionLocal()
            try:
                await locker.begin()
                locked_rfq = (await locker.execute(
                    select(RFQRequest).where(RFQRequest.id == race_rfq_id).with_for_update()
                )).scalar_one()
                update_query_started = asyncio.Event()

                def mark_locked_update_started(_conn, _cursor, statement, _parameters, _context, _executemany):
                    if "FROM rfq_requests" in statement and "FOR UPDATE" in statement.upper():
                        update_query_started.set()

                event.listen(engine.sync_engine, "before_cursor_execute", mark_locked_update_started)
                pending_update = asyncio.create_task(
                    update_rfq(race_rfq_id, RFQUpdate(title="Stale edit after issue"), updater, actor)
                )
                try:
                    await asyncio.wait_for(update_query_started.wait(), timeout=3)
                    assert not pending_update.done(), "RFQ update must wait for the lifecycle row lock"
                finally:
                    event.remove(engine.sync_engine, "before_cursor_execute", mark_locked_update_started)
                locked_rfq.status = RFQStatus.SENT
                await locker.commit()
                with pytest.raises(HTTPException) as stale_edit:
                    await pending_update
                assert stale_edit.value.status_code == 409
                persisted = await db.get(RFQRequest, race_rfq_id, populate_existing=True)
                assert persisted is not None
                assert persisted.status == RFQStatus.SENT
                assert persisted.title == "Synthetic draft lock regression"
            finally:
                await locker.close()
                await updater.close()

            draft = await create_rfq(
                RFQCreate(
                    rfq_no=f"M34-T002-{suffix}",
                    title="Synthetic invitation and bid workflow",
                    quantity="10",
                    unit="KG",
                    response_deadline=date.today() + timedelta(days=5),
                    supplier_ids=[invited_supplier.id],
                ),
                db,
                actor,
            )
            rfq_ids.append(draft.id)
            assert draft.status == RFQStatus.DRAFT
            assert draft.responses[0].invitation_status == RFQInvitationStatus.PENDING
            assert draft.responses[0].invitation_issued_at is None

            issued = await issue_rfq_invitations(draft.id, db, actor)
            assert issued.status == RFQStatus.SENT
            invitation = next(row for row in issued.responses if row.supplier_id == invited_supplier.id)
            assert invitation.invitation_status == RFQInvitationStatus.ISSUED
            assert invitation.invitation_issued_at is not None
            original_issued_at = invitation.invitation_issued_at

            for spoofed_status in (RFQStatus.DRAFT, RFQStatus.RESPONSES_RECEIVED):
                with pytest.raises(HTTPException) as spoofed:
                    await update_rfq(draft.id, RFQUpdate(status=spoofed_status), db, actor)
                assert spoofed.value.status_code == 409
            with pytest.raises(HTTPException) as repeated_issue:
                await issue_rfq_invitations(draft.id, db, actor)
            assert repeated_issue.value.status_code == 409
            refreshed = await db.get(RFQResponse, invitation.id)
            assert refreshed is not None and refreshed.invitation_issued_at == original_issued_at

            bid = await add_rfq_response(
                draft.id,
                RFQResponseCreate(
                    supplier_id=invited_supplier.id,
                    quoted_unit_price="3.1250",
                    quoted_currency="kes",
                    lead_time_days=4,
                    valid_until=date.today() + timedelta(days=10),
                ),
                db,
                actor,
            )
            assert bid.status == RFQResponseStatus.SUBMITTED
            assert bid.submitted_at is not None
            assert bid.submitted_by_id is None

            with pytest.raises(HTTPException) as duplicate:
                await add_rfq_response(
                    draft.id,
                    RFQResponseCreate(supplier_id=invited_supplier.id, quoted_unit_price="3.5"),
                    db,
                    actor,
                )
            assert duplicate.value.status_code == 409

            with pytest.raises(HTTPException) as uninvited:
                await add_rfq_response(
                    draft.id,
                    RFQResponseCreate(supplier_id=uninvited_supplier.id, quoted_unit_price="3.5"),
                    db,
                    actor,
                )
            assert uninvited.value.status_code == 403

            with pytest.raises(HTTPException) as direct_award:
                await update_rfq(
                    draft.id,
                    RFQUpdate(status=RFQStatus.AWARDED, awarded_supplier_id=invited_supplier.id),
                    db,
                    actor,
                )
            assert direct_award.value.status_code == 409
            still_unawarded = await get_rfq(draft.id, db, actor)
            assert still_unawarded.status == RFQStatus.RESPONSES_RECEIVED
            assert still_unawarded.awarded_supplier_id is None

            expired = await create_rfq(
                RFQCreate(
                    rfq_no=f"M34-T002-EXPIRED-{suffix}",
                    title="Synthetic expired deadline event",
                    quantity="1",
                    response_deadline=date.today() - timedelta(days=1),
                    supplier_ids=[uninvited_supplier.id],
                ),
                db,
                actor,
            )
            rfq_ids.append(expired.id)
            await issue_rfq_invitations(expired.id, db, actor)
            with pytest.raises(HTTPException) as deadline:
                await add_rfq_response(
                    expired.id,
                    RFQResponseCreate(supplier_id=uninvited_supplier.id, quoted_unit_price="3.5"),
                    db,
                    actor,
                )
            assert deadline.value.status_code == 409
        finally:
            for rfq_id in rfq_ids:
                await db.execute(delete(RFQResponse).where(RFQResponse.rfq_id == rfq_id))
                await db.execute(delete(RFQRequest).where(RFQRequest.id == rfq_id))
            if race_rfq_id is not None:
                await db.execute(delete(RFQRequest).where(RFQRequest.id == race_rfq_id))
            await db.execute(delete(Supplier).where(Supplier.id.in_([invited_supplier.id, uninvited_supplier.id])))
            await db.commit()
