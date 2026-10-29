"""Evidence-backed Kenya shipment receipt closure on task-owned PostgreSQL."""
from __future__ import annotations

import os
import re
from datetime import date
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
    ArrivalNotification,
    InternationalShipment,
    IntlShipmentStatus,
    ShipmentPOLink,
    ShipmentReceiptClosure,
    ShipmentReceiptClosureGRN,
)
from app.models.master import Supplier, Warehouse, WarehouseType
from app.models.procurement import GoodsReceipt, GRNStatus, POStatus, PurchaseOrder
from app.models.role import Permission, Role
from app.models.user import User


pytestmark = pytest.mark.skipif(
    os.environ.get("M25_S01_T004_DISPOSABLE_TEST_DATABASE") != "1",
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
    expected = os.environ.get("M25_S01_T004_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s01_t004_[a-f0-9]{20}", expected)
    assert (await db.execute(select(1))).scalar_one() == 1
    from sqlalchemy import text
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


def _actor(*permissions: str) -> User:
    permission_rows = [
        Permission(
            code=code,
            module=code.split(".", 1)[0],
            action=code.split(".", 1)[1],
            name=code,
            is_active=True,
        )
        for code in permissions
    ]
    role = Role(name=f"Synthetic M25 receipt role {uuid4().hex}", is_active=True, permissions=permission_rows)
    return User(
        email=f"m25-s01-t004-{uuid4().hex}@example.invalid",
        username=f"m25s01t004{uuid4().hex}",
        full_name="Synthetic Receipt Operator",
        hashed_password="synthetic-test-only-not-a-credential",
        is_active=True,
        is_superuser=False,
        roles=[role],
    )


@pytest.mark.asyncio
async def test_kenya_receipt_closure_requires_posted_linked_grns_and_is_immutable():
    suffix = uuid4().hex[:16]
    actor = _actor("logistics.view", "logistics.edit", "logistics.create", "procurement.view")
    active_actor = actor

    async def override_db():
        async with AsyncSessionLocal() as request_db:
            yield request_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: active_actor

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        supplier = Supplier(code=f"M25-T004-S-{suffix}", name="Synthetic receipt supplier")
        warehouse = Warehouse(
            code=f"M25-T004-W-{suffix}",
            name="Synthetic Mombasa receiving warehouse",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            country="Kenya",
        )
        shipment = InternationalShipment(
            shipment_no=f"M25-T004-SHIP-{suffix}",
            origin_country="Turkey",
            origin_city="Istanbul",
            origin_port="Synthetic origin port",
            destination_country="Kenya",
            destination_city="Mombasa",
            destination_port="Port of Mombasa",
            status=IntlShipmentStatus.OUT_FOR_DELIVERY,
        )
        db.add_all([supplier, warehouse, shipment, actor])
        await db.flush()
        po = PurchaseOrder(
            po_no=f"M25-T004-PO-{suffix}",
            supplier_id=supplier.id,
            order_date=date(2026, 10, 1),
            expected_delivery_date=date(2026, 10, 30),
            status=POStatus.PARTIALLY_RECEIVED,
        )
        unrelated_po = PurchaseOrder(
            po_no=f"M25-T004-OTHER-PO-{suffix}",
            supplier_id=supplier.id,
            order_date=date(2026, 10, 1),
            expected_delivery_date=date(2026, 10, 30),
            status=POStatus.PARTIALLY_RECEIVED,
        )
        db.add_all([po, unrelated_po])
        await db.flush()
        linked_posted = GoodsReceipt(
            grn_no=f"M25-T004-GRN-{suffix}", po_id=po.id,
            received_date=date(2026, 10, 29), warehouse_id=warehouse.id, status=GRNStatus.POSTED,
        )
        linked_draft = GoodsReceipt(
            grn_no=f"M25-T004-DRAFT-{suffix}", po_id=po.id,
            received_date=date(2026, 10, 30), warehouse_id=warehouse.id, status=GRNStatus.DRAFT,
        )
        unrelated_posted = GoodsReceipt(
            grn_no=f"M25-T004-UNLINKED-{suffix}", po_id=unrelated_po.id,
            received_date=date(2026, 10, 29), warehouse_id=warehouse.id, status=GRNStatus.POSTED,
        )
        db.add_all([linked_posted, linked_draft, unrelated_posted])
        await db.flush()
        db.add_all([
            ShipmentPOLink(shipment_id=shipment.id, po_id=po.id),
            ArrivalNotification(shipment_id=shipment.id),
        ])
        await db.commit()
        shipment_id = shipment.id
        unrelated_po_id = unrelated_po.id
        linked_grn_id = linked_posted.id
        draft_grn_id = linked_draft.id
        unrelated_grn_id = unrelated_posted.id
        closure_grn_id = linked_posted.id

    base = f"/api/v1/logistics/shipments/{shipment_id}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m25-s01-t004.test") as client:
        active_actor = _actor()
        assert (await client.get(f"{base}/receipt-options")).status_code == 403
        assert (await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(linked_grn_id)]})).status_code == 403
        active_actor = actor

        options = await client.get(f"{base}/receipt-options")
        assert options.status_code == 200, options.text
        assert [row["id"] for row in options.json()] == [str(linked_grn_id)]

        direct_delivery_date = await client.patch(
            f"{base}/arrival", json={"delivery_date": "2026-10-29", "grn_id": str(linked_grn_id)}
        )
        assert direct_delivery_date.status_code == 422
        direct_delivered_status = await client.patch(f"{base}", json={"status": "DELIVERED"})
        assert direct_delivered_status.status_code == 409

        duplicate = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(linked_grn_id), str(linked_grn_id)]})
        assert duplicate.status_code == 422
        draft = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(draft_grn_id)]})
        assert draft.status_code == 409
        unlinked = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(unrelated_grn_id)]})
        assert unlinked.status_code == 409

        response = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(linked_grn_id)]})
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["shipment_id"] == str(shipment_id)
        assert data["closed_by_id"] == str(actor.id)
        assert [item["id"] for item in data["grns"]] == [str(linked_grn_id)]
        assert data["grns"][0]["received_date"] == "2026-10-29"

        replay = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(linked_grn_id)]})
        assert replay.status_code == 200
        assert replay.json()["id"] == data["id"]
        different_replay = await client.post(f"{base}/receipt-closure", json={"grn_ids": [str(unrelated_grn_id)]})
        assert different_replay.status_code == 409

        shipment_read = await client.get(base)
        assert shipment_read.json()["status"] == "DELIVERED"
        arrival = await client.get(f"{base}/arrival")
        assert arrival.status_code == 200
        assert arrival.json()["delivery_date"] == "2026-10-29"
        assert arrival.json()["grn_id"] == str(linked_grn_id)
        history = await client.get(f"{base}/receipt-closure")
        assert history.status_code == 200
        assert history.json()["closed_by_name"] == actor.full_name
        po_links = await client.get(f"{base}/po-links")
        assert po_links.status_code == 200
        assert len(po_links.json()) == 1
        link_id = po_links.json()[0]["id"]
        add_after_closure = await client.post(
            f"{base}/po-links", json={"po_id": str(unrelated_po_id)}
        )
        assert add_after_closure.status_code == 409
        remove_after_closure = await client.delete(f"/api/v1/logistics/po-links/{link_id}")
        assert remove_after_closure.status_code == 409

    async with AsyncSessionLocal() as db:
        closure = await db.scalar(select(ShipmentReceiptClosure).where(ShipmentReceiptClosure.shipment_id == shipment_id))
        assert closure is not None
        closure_id = closure.id
        assert closure.closed_by_id == actor.id
        lines = list((await db.execute(
            select(ShipmentReceiptClosureGRN).where(ShipmentReceiptClosureGRN.closure_id == closure_id)
        )).scalars().all())
        assert len(lines) == 1
        assert lines[0].grn_id == closure_grn_id
        assert lines[0].received_date == date(2026, 10, 29)
        with pytest.raises(DBAPIError, match="append-only"):
            await db.delete(lines[0])
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(delete(ShipmentReceiptClosureGRN).where(ShipmentReceiptClosureGRN.closure_id == closure_id))
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError, match="append-only"):
            await db.delete(closure)
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(delete(GoodsReceipt).where(GoodsReceipt.id == closure_grn_id))
            await db.flush()
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(delete(User).where(User.id == actor.id))
            await db.flush()
        await db.rollback()
