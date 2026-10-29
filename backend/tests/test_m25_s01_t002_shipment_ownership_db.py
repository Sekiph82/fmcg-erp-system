"""Evidence-linked shipment inventory ownership on task-owned disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.logistics import InternationalShipment, ShipmentOwnershipEvent, ShipmentPOLink
from app.models.master import Supplier
from app.models.procurement import POStatus, PurchaseOrder
from app.models.role import Permission, Role
from app.models.user import User


pytestmark = pytest.mark.skipif(
    os.environ.get("M25_S01_T002_DISPOSABLE_TEST_DATABASE") != "1",
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
    expected = os.environ.get("M25_S01_T002_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s01_t002_[a-f0-9]{20}", expected)
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


def _actor(*permissions: str) -> User:
    rows = [
        Permission(code=code, module="logistics", action=code.split(".", 1)[1], name=code, is_active=True)
        for code in permissions
    ]
    role = Role(name=f"Synthetic M25 ownership role {uuid4().hex}", is_active=True, permissions=rows)
    return User(
        email=f"m25-s01-t002-{uuid4().hex}@example.invalid",
        username=f"m25s01t002{uuid4().hex}",
        full_name="Synthetic Ownership Tester",
        hashed_password="synthetic-test-only-not-a-credential",
        is_active=True,
        is_superuser=False,
        roles=[role],
    )


@pytest.mark.asyncio
async def test_ownership_requires_evidence_permission_and_transit_state_and_is_append_only():
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
        supplier = Supplier(code=f"M25-{suffix}", name="Synthetic Import Supplier")
        po = PurchaseOrder(
            po_no=f"M25-PO-{suffix}",
            supplier=supplier,
            order_date=date.today(),
            expected_delivery_date=date.today() + timedelta(days=14),
            status=POStatus.ORDERED,
        )
        shipment = InternationalShipment(
            shipment_no=f"M25-SHIP-{suffix}",
            origin_country="Turkey",
            origin_city="Istanbul",
            origin_port="Port of Istanbul",
            destination_country="Kenya",
            destination_city="Mombasa",
            destination_port="Port of Mombasa",
            incoterm="CIF",
            status="DRAFT",
        )
        db.add_all([supplier, po, shipment, actor])
        await db.commit()
        shipment_id = shipment.id
        po_id = po.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m25-s01-t002.test") as client:
        active_actor = _actor()
        denied_history = await client.get(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{uuid4()}/ownership-events"
        )
        assert denied_history.status_code == 403
        denied_write = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{uuid4()}/ownership",
            json={"new_owner": "BUYER_OWNED", "source_reference": "SYN-CONTRACT-1"},
        )
        assert denied_write.status_code == 403
        denied_status_change = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}",
            json={"status": "IN_TRANSIT"},
        )
        assert denied_status_change.status_code == 403
        active_actor = actor

        linked = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links",
            json={"po_id": str(po_id)},
        )
        assert linked.status_code == 201, linked.text
        link_id = linked.json()["id"]
        assert linked.json()["inventory_owner_status"] == "UNCONFIRMED"

        initial_history = await client.get(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership-events"
        )
        assert initial_history.status_code == 200
        assert initial_history.json() == []

        invalid_transition = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}",
            json={"status": "IN_TRANSIT"},
        )
        assert invalid_transition.status_code == 409
        booking = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}",
            json={"status": "BOOKING_CONFIRMED"},
        )
        assert booking.status_code == 200, booking.text
        before_loading = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={"new_owner": "BUYER_OWNED", "source_reference": "SYN-CONTRACT-1"},
        )
        assert before_loading.status_code == 409
        loaded = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}",
            json={"status": "CARGO_LOADED"},
        )
        assert loaded.status_code == 200, loaded.text
        in_transit = await client.patch(
            f"/api/v1/logistics/shipments/{shipment_id}",
            json={"status": "IN_TRANSIT"},
        )
        assert in_transit.status_code == 200, in_transit.text

        blank_reference = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={"new_owner": "BUYER_OWNED", "source_reference": "   "},
        )
        assert blank_reference.status_code == 422
        cannot_reset = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={"new_owner": "UNCONFIRMED", "source_reference": "SYN-CONTRACT-1"},
        )
        assert cannot_reset.status_code == 422

        first = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={
                "new_owner": "BUYER_OWNED",
                "source_reference": "SYN-COMMERCIAL-CONTRACT-001",
                "notes": "Synthetic evidence for automated workflow verification.",
            },
        )
        assert first.status_code == 201, first.text
        assert first.json()["previous_owner"] == "UNCONFIRMED"
        assert first.json()["new_owner"] == "BUYER_OWNED"
        assert first.json()["source_reference"] == "SYN-COMMERCIAL-CONTRACT-001"
        assert first.json()["changed_by_id"] == str(actor.id)
        assert first.json()["changed_by_name"] == actor.full_name

        duplicate = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={"new_owner": "BUYER_OWNED", "source_reference": "SYN-CONTRACT-2"},
        )
        assert duplicate.status_code == 409
        second = await client.post(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership",
            json={"new_owner": "SUPPLIER_OWNED", "source_reference": "SYN-REVISED-CONTRACT-002"},
        )
        assert second.status_code == 201, second.text
        assert second.json()["previous_owner"] == "BUYER_OWNED"

        history = await client.get(
            f"/api/v1/logistics/shipments/{shipment_id}/po-links/{link_id}/ownership-events"
        )
        assert history.status_code == 200
        assert [item["new_owner"] for item in history.json()] == ["BUYER_OWNED", "SUPPLIER_OWNED"]

        unlink = await client.delete(f"/api/v1/logistics/po-links/{link_id}")
        assert unlink.status_code == 409

    async with AsyncSessionLocal() as db:
        link = (await db.execute(select(ShipmentPOLink).where(ShipmentPOLink.id == link_id))).scalar_one()
        assert link.inventory_owner_status == "SUPPLIER_OWNED"
        events = list((await db.execute(
            select(ShipmentOwnershipEvent)
            .where(ShipmentOwnershipEvent.shipment_po_link_id == link_id)
            .order_by(ShipmentOwnershipEvent.effective_at, ShipmentOwnershipEvent.created_at)
        )).scalars().all())
        assert len(events) == 2
        with pytest.raises(DBAPIError, match="append-only"):
            await db.delete(events[0])
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(delete(User).where(User.id == actor.id))
        await db.rollback()
        still_attributed = (await db.execute(
            select(ShipmentOwnershipEvent.changed_by_id)
            .where(ShipmentOwnershipEvent.shipment_po_link_id == link_id)
        )).scalars().all()
        assert still_attributed == [actor.id, actor.id]
