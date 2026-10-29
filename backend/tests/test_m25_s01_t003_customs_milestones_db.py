"""Evidence-linked customs clearance milestones on task-owned disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.logistics import (
    ClearanceStatus,
    CustomsClearance,
    CustomsClearanceMilestone,
    InternationalShipment,
    IntlShipmentStatus,
    ArrivalNotification,
)
from app.models.role import Permission, Role
from app.models.user import User


pytestmark = pytest.mark.skipif(
    os.environ.get("M25_S01_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _restore_application_and_engine():
    original_overrides = app.dependency_overrides.copy()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M25_S01_T003_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s01_t003_[a-f0-9]{20}", expected)
    assert (await db.execute(select(1))).scalar_one() == 1
    from sqlalchemy import text
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


def _actor(*permissions: str) -> User:
    rows = [
        Permission(code=code, module="logistics", action=code.split(".", 1)[1], name=code, is_active=True)
        for code in permissions
    ]
    role = Role(name=f"Synthetic M25 clearance role {uuid4().hex}", is_active=True, permissions=rows)
    return User(
        email=f"m25-s01-t003-{uuid4().hex}@example.invalid",
        username=f"m25s01t003{uuid4().hex}",
        full_name="Synthetic Clearance Tester",
        hashed_password="synthetic-test-only-not-a-credential",
        is_active=True,
        is_superuser=False,
        roles=[role],
    )


@pytest.mark.asyncio
async def test_clearance_milestones_are_ordered_permissioned_evidenced_and_append_only():
    suffix = uuid4().hex[:16]
    actor = _actor("logistics.view", "logistics.create", "logistics.edit")
    active_actor = actor

    async def override_db():
        async with AsyncSessionLocal() as request_db:
            yield request_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: active_actor

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        shipment = InternationalShipment(
            shipment_no=f"M25-SHIP-{suffix}",
            origin_country="Turkey",
            origin_city="Istanbul",
            origin_port="Synthetic origin port",
            destination_country="Kenya",
            destination_city="Mombasa",
            destination_port="Synthetic destination port",
            status=IntlShipmentStatus.ARRIVED_PORT,
        )
        db.add_all([shipment, actor])
        await db.flush()
        db.add(ArrivalNotification(shipment_id=shipment.id))
        clearance = CustomsClearance(shipment_id=shipment.id, status=ClearanceStatus.PENDING)
        db.add(clearance)
        await db.commit()
        shipment_id = shipment.id
        clearance_id = clearance.id

    prefix = f"/api/v1/logistics/shipments/{shipment_id}/clearance/milestones"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m25-s01-t003.test") as client:
        active_actor = _actor()
        denied_read = await client.get(prefix)
        assert denied_read.status_code == 403
        denied_clearance_read = await client.get(f"/api/v1/logistics/shipments/{shipment_id}/clearance")
        assert denied_clearance_read.status_code == 403
        denied_write = await client.post(prefix, json={"new_status": "DOCS_SUBMITTED", "source_reference": "SYN-IDF-1"})
        assert denied_write.status_code == 403
        active_actor = actor

        history = await client.get(prefix)
        assert history.status_code == 200
        assert history.json() == []

        no_reference = await client.post(prefix, json={"new_status": "DOCS_SUBMITTED", "source_reference": "   "})
        assert no_reference.status_code == 422
        skipped = await client.post(prefix, json={"new_status": "CLEARED", "source_reference": "SYN-RELEASE-1"})
        assert skipped.status_code == 409
        direct_status_edit = await client.patch(
            f"/api/v1/logistics/clearance/{clearance_id}", json={"status": "CLEARED"}
        )
        assert direct_status_edit.status_code == 422
        direct_shipment_hold = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}", json={"status": "CUSTOMS_HOLD"}
        )
        assert direct_shipment_hold.status_code == 409
        direct_arrival_clearance_date = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}/arrival",
            json={"customs_clearance_date": "2026-10-29"},
        )
        assert direct_arrival_clearance_date.status_code == 422

        submitted = await client.post(prefix, json={
            "new_status": "DOCS_SUBMITTED",
            "source_reference": "  SYN-IDF-2026-0001  ",
        })
        assert submitted.status_code == 201, submitted.text
        assert submitted.json()["previous_status"] == "PENDING"
        assert submitted.json()["new_status"] == "DOCS_SUBMITTED"
        assert submitted.json()["source_reference"] == "SYN-IDF-2026-0001"
        assert submitted.json()["changed_by_id"] == str(actor.id)
        assert submitted.json()["changed_by_name"] == actor.full_name

        reviewed = await client.post(prefix, json={"new_status": "UNDER_REVIEW", "source_reference": "SYN-KRA-REVIEW-1"})
        assert reviewed.status_code == 201, reviewed.text
        no_hold_reason = await client.post(prefix, json={"new_status": "HELD", "source_reference": "SYN-KRA-HOLD-1"})
        assert no_hold_reason.status_code == 422
        held = await client.post(prefix, json={
            "new_status": "HELD",
            "source_reference": "SYN-KRA-HOLD-1",
            "notes": "Synthetic review hold for automated verification.",
        })
        assert held.status_code == 201, held.text

        resume = await client.post(prefix, json={"new_status": "UNDER_REVIEW", "source_reference": "SYN-KRA-REVIEW-2"})
        assert resume.status_code == 201, resume.text
        exam = await client.post(prefix, json={"new_status": "EXAM_REQUESTED", "source_reference": "SYN-KRA-EXAM-1"})
        assert exam.status_code == 201, exam.text
        assessed = await client.post(prefix, json={"new_status": "DUTY_ASSESSED", "source_reference": "SYN-KRA-ASSESSMENT-1"})
        assert assessed.status_code == 201, assessed.text
        paid = await client.post(prefix, json={"new_status": "DUTY_PAID", "source_reference": "SYN-DUTY-RECEIPT-1"})
        assert paid.status_code == 201, paid.text
        cleared = await client.post(prefix, json={"new_status": "CLEARED", "source_reference": "SYN-KRA-RELEASE-1"})
        assert cleared.status_code == 201, cleared.text
        terminal = await client.post(prefix, json={"new_status": "UNDER_REVIEW", "source_reference": "SYN-REOPEN-1"})
        assert terminal.status_code == 409

        all_events = await client.get(prefix)
        assert all_events.status_code == 200
        assert [item["new_status"] for item in all_events.json()] == [
            "DOCS_SUBMITTED", "UNDER_REVIEW", "HELD", "UNDER_REVIEW",
            "EXAM_REQUESTED", "DUTY_ASSESSED", "DUTY_PAID", "CLEARED",
        ]

        clearance_read = await client.get(f"/api/v1/logistics/shipments/{shipment_id}/clearance")
        assert clearance_read.status_code == 200
        assert clearance_read.json()["status"] == "CLEARED"
        shipment_read = await client.get(f"/api/v1/logistics/shipments/{shipment_id}")
        assert shipment_read.status_code == 200
        assert shipment_read.json()["status"] == "CUSTOMS_CLEARED"

    async with AsyncSessionLocal() as db:
        events = list((await db.execute(
            select(CustomsClearanceMilestone)
            .where(CustomsClearanceMilestone.clearance_id == clearance_id)
            .order_by(CustomsClearanceMilestone.effective_at, CustomsClearanceMilestone.created_at)
        )).scalars().all())
        assert len(events) == 8
        assert all(item.changed_by_id == actor.id for item in events)
        with pytest.raises(DBAPIError, match="append-only"):
            await db.delete(events[0])
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(delete(CustomsClearanceMilestone).where(CustomsClearanceMilestone.clearance_id == clearance_id))
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(delete(User).where(User.id == actor.id))
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(delete(CustomsClearance).where(CustomsClearance.id == clearance_id))
            await db.flush()
        await db.rollback()
