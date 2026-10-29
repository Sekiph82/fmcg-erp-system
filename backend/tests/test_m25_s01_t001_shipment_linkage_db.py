"""Purchase-order to international-shipment to container linkage on disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.logistics import InternationalShipment, ShipmentContainer, ShipmentPOLink
from app.models.master import Supplier
from app.models.procurement import POStatus, POLine, PurchaseOrder
from app.models.role import Permission, Role
from app.models.user import User
from app.crud.logistics import get_shipment
from app.api.v1.endpoints.logistics import _s_read


pytestmark = pytest.mark.skipif(
    os.environ.get("M25_S01_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    original_overrides = app.dependency_overrides.copy()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M25_S01_T001_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s01_t001_[a-f0-9]{20}", expected)
    assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected


def _actor(*permissions: str) -> User:
    permission_rows = [
        Permission(
            code=code,
            module="logistics",
            action=code.split(".", 1)[1],
            name=code,
            is_active=True,
        )
        for code in permissions
    ]
    role = Role(name=f"Synthetic M25 role {uuid4().hex}", is_active=True, permissions=permission_rows)
    return User(
        email=f"m25-s01-t001-{uuid4().hex}@example.invalid",
        username=f"m25s01t001{uuid4().hex}",
        full_name="Synthetic shipment linkage tester",
        hashed_password="synthetic-test-only-not-a-credential",
        is_active=True,
        is_superuser=False,
        roles=[role],
    )


@pytest.mark.asyncio
async def test_po_links_once_to_shipment_with_containers_and_permission_checks():
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
        supplier = Supplier(code=f"M25-{suffix}", name="Synthetic Kenya import supplier")
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
            status="IN_TRANSIT",
        )
        db.add_all([supplier, po, shipment])
        await db.flush()
        db.add_all([
            POLine(
                po_id=po.id,
                line_no=1,
                ordered_quantity=2,
                unit="BOX",
                unit_price=3.75,
                tax_rate=0.16,
            ),
            POLine(
                po_id=po.id,
                line_no=2,
                ordered_quantity=1,
                unit="BOX",
                unit_price=1.10,
                tax_rate=0.16,
            ),
        ])
        await db.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m25-s01-t001.test") as client:
            denied_actor = _actor()
            active_actor = denied_actor
            denied = await client.post(
                f"/api/v1/logistics/shipments/{shipment.id}/po-links",
                json={"po_id": str(po.id)},
            )
            assert denied.status_code == 403
            denied_read = await client.get(f"/api/v1/logistics/shipments/{shipment.id}/po-links")
            assert denied_read.status_code == 403
            active_actor = actor

            linked = await client.post(
                f"/api/v1/logistics/shipments/{shipment.id}/po-links",
                json={"po_id": str(po.id), "notes": "Synthetic PO-to-shipment link"},
            )
            assert linked.status_code == 201, linked.text
            assert linked.json()["shipment_id"] == str(shipment.id)
            assert linked.json()["po_id"] == str(po.id)
            assert linked.json()["po_no"] == po.po_no
            assert linked.json()["supplier_name"] == supplier.name
            assert linked.json()["po_total"] == 9.98

            duplicate = await client.post(
                f"/api/v1/logistics/shipments/{shipment.id}/po-links",
                json={"po_id": str(po.id)},
            )
            assert duplicate.status_code == 409

            missing_po = await client.post(
                f"/api/v1/logistics/shipments/{shipment.id}/po-links",
                json={"po_id": str(uuid4())},
            )
            assert missing_po.status_code == 404

            draft_po = PurchaseOrder(
                po_no=f"M25-DRAFT-{suffix}",
                supplier_id=supplier.id,
                order_date=date.today(),
                expected_delivery_date=date.today() + timedelta(days=14),
                status=POStatus.DRAFT,
            )
            db.add(draft_po)
            await db.commit()
            invalid_status = await client.post(
                f"/api/v1/logistics/shipments/{shipment.id}/po-links",
                json={"po_id": str(draft_po.id)},
            )
            assert invalid_status.status_code == 409

            missing_shipment = await client.post(
                f"/api/v1/logistics/shipments/{uuid4()}/po-links",
                json={"po_id": str(po.id)},
            )
            assert missing_shipment.status_code == 404

            active_actor = denied_actor
            denied_container = await client.post(
                "/api/v1/logistics/containers/",
                json={
                    "shipment_id": str(shipment.id),
                    "container_no": f"DENIED{suffix[:5].upper()}",
                    "container_type": "40FT_DRY",
                },
            )
            assert denied_container.status_code == 403
            active_actor = actor
            created_container = await client.post(
                "/api/v1/logistics/containers/",
                json={
                    "shipment_id": str(shipment.id),
                    "container_no": f"SYN{suffix[:7].upper()}",
                    "container_type": "40FT_DRY",
                    "contents_summary": "Synthetic dry-goods purchase order cargo",
                },
            )
            assert created_container.status_code == 201, created_container.text
            container_id = created_container.json()["id"]
            assert created_container.json()["shipment_id"] == str(shipment.id)
            assert created_container.json()["shipment_no"] == shipment.shipment_no

            missing_container_shipment = await client.post(
                "/api/v1/logistics/containers/",
                json={
                    "shipment_id": str(uuid4()),
                    "container_no": f"SYNMISSING{suffix[:5].upper()}",
                    "container_type": "40FT_DRY",
                },
            )
            assert missing_container_shipment.status_code == 404

            active_actor = denied_actor
            denied_container_edit = await client.patch(
                f"/api/v1/logistics/containers/{container_id}",
                json={"notes": "unauthorized synthetic mutation"},
            )
            assert denied_container_edit.status_code == 403
            active_actor = actor
            edited_container = await client.patch(
                f"/api/v1/logistics/containers/{container_id}",
                json={"notes": "Synthetic container edit"},
            )
            assert edited_container.status_code == 200, edited_container.text
            assert edited_container.json()["notes"] == "Synthetic container edit"

        async with AsyncSessionLocal() as verify_db:
            fresh = await get_shipment(verify_db, shipment.id)
            assert fresh is not None
            assert len(fresh.po_links) == 1
            assert fresh.po_links[0].po.id == po.id
            assert len(fresh.containers) == 1
            assert fresh.containers[0].id == UUID(container_id)
            assert _s_read(fresh).po_count == 1
            assert _s_read(fresh).container_count == 1
            assert (await verify_db.execute(
                select(func.count()).select_from(ShipmentPOLink).where(
                    ShipmentPOLink.shipment_id == shipment.id,
                    ShipmentPOLink.po_id == po.id,
                )
            )).scalar_one() == 1
            assert (await verify_db.execute(
                select(func.count()).select_from(ShipmentContainer).where(
                    ShipmentContainer.shipment_id == shipment.id,
                    ShipmentContainer.id == UUID(container_id),
                )
            )).scalar_one() == 1
            constraint_exists = await verify_db.execute(text(
                """SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'shipment_po_links'::regclass
                     AND conname = 'uq_shipment_po_links_shipment_po'"""
            ))
            assert constraint_exists.first() is not None

            verify_db.add(ShipmentPOLink(shipment_id=shipment.id, po_id=po.id))
            with pytest.raises(IntegrityError):
                await verify_db.flush()
            await verify_db.rollback()
