"""M34.S02.T004 contract consumption from accepted receipt quantities."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import create_bpa, create_bpa_release_order
from app.crud.procurement import create_grn, get_grn, get_po
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditEvent, AuditLog
from app.models.master import Product, ProductCategory, Supplier, Warehouse, WarehouseType
from app.models.inventory import Stock, StockMovement
from app.models.procurement import (
    BPAStatus,
    BlanketPurchaseAgreement,
    GoodsReceipt,
    POStatus,
    PurchaseOrder,
)
from app.models.user import User
from app.schemas.procurement import BlanketAgreementCreate, BlanketAgreementReleaseCreate
from app.services import procurement_service as svc


TASK_DB_ENV = "M34_S02_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S02_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s02_t004_[a-f0-9]{24}")


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
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for this task's disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's passwordless loopback database.")


def test_consumption_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s02_t004_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_bpa_consumption_tracks_accepted_receipts_and_rejects_overreceipt(monkeypatch):
    _require_task_database()
    suffix = uuid4().hex[:16]
    today = date.today()
    valid_to = today + timedelta(days=60)
    supplier = Supplier(code=f"M34S02T004-{suffix}", name="Synthetic consumption supplier", is_active=True)
    product = Product(sku=f"M34S02T004-{suffix}", name="Synthetic consumption product", category=ProductCategory.OTHER, is_active=True)
    warehouse = Warehouse(code=f"M34S02T004-{suffix}", name="Synthetic receipt warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
    actor = User(
        email=f"m34-s02-t004-{suffix}@example.invalid",
        username=f"m34s02t004{suffix}",
        full_name="Synthetic consumption actor",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    agreement_id = None
    supplier_id = None
    product_id = None
    warehouse_id = None
    actor_id = None
    try:
        async with AsyncSessionLocal() as db:
            db.add_all([supplier, product, warehouse, actor])
            await db.commit()
            supplier_id, product_id, warehouse_id, actor_id = supplier.id, product.id, warehouse.id, actor.id
            agreement_read = await create_bpa(
                BlanketAgreementCreate(
                    bpa_no=f"M34-S02-T004-{suffix}",
                    supplier_id=supplier_id,
                    product_id=product_id,
                    description="Synthetic receipt-tracked agreement",
                    agreed_unit_price=Decimal("12.5000"),
                    currency="KES",
                    agreed_quantity=Decimal("30.000"),
                    unit="KG",
                    valid_from=today,
                    valid_to=valid_to,
                ),
                db,
                actor,
            )
            agreement_id = agreement_read.id

            async def create_release(label: str, quantity: str):
                release = await create_bpa_release_order(
                    agreement_id,
                    BlanketAgreementReleaseCreate(
                        po_no=f"M34-S02-T004-PO-{suffix}-{label}",
                        release_date=today,
                        expected_delivery_date=today + timedelta(days=7),
                        quantity=Decimal(quantity),
                    ),
                    db,
                    actor,
                )
                po = await get_po(db, release.id)
                po.status = POStatus.ORDERED
                return release.id, po.lines[0].id

            first_po_id, first_po_line_id = await create_release("A", "15")
            second_po_id, second_po_line_id = await create_release("B", "7")
            third_po_id, third_po_line_id = await create_release("C", "8")
            await db.commit()

            async def skip_valuation(*_args, **_kwargs):
                return None

            monkeypatch.setattr(svc, "post_grn_inventory_valuation", skip_valuation)

            def receipt(grn_no: str, po_id, po_line_id, received: str, accepted: str, rejected: str):
                return {
                    "grn_no": grn_no,
                    "po_id": po_id,
                    "received_date": today,
                    "warehouse_id": warehouse_id,
                    "lines": [{
                        "po_line_id": po_line_id,
                        "product_id": product_id,
                        "received_quantity": Decimal(received),
                        "accepted_quantity": Decimal(accepted),
                        "rejected_quantity": Decimal(rejected),
                        "unit": "KG",
                    }],
                }

            first = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-1", first_po_id, first_po_line_id, "12", "10", "2"),
                actor_id,
            )
            await db.commit()
            first = await get_grn(db, first.id)
            await svc.post_grn(db, first, actor_id)
            await db.commit()

            persisted = await db.get(BlanketPurchaseAgreement, agreement_id)
            assert persisted.consumed_quantity == Decimal("10.000")
            assert await svc.bpa_open_release_quantity(db, agreement_id) == Decimal("20.000")
            first_events = (await db.execute(select(AuditLog).where(
                AuditLog.target_id == str(agreement_id),
                AuditLog.event_type == AuditEvent.BPA_CONSUMPTION_RECORDED,
            ))).scalars().all()
            assert len(first_events) == 1
            assert first_events[0].before_value["consumed_quantity"] == "0.000"
            assert first_events[0].after_value["consumed_quantity"] == "10.000"
            assert first_events[0].details["goods_receipt_id"] == str(first.id)

            with pytest.raises(HTTPException) as duplicate_post:
                await svc.post_grn(db, first, actor_id)
            assert duplicate_post.value.status_code == 422
            await db.rollback()

            malformed = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-BAD", first_po_id, first_po_line_id, "5", "4", "-1"),
                actor_id,
            )
            await db.commit()
            malformed = await get_grn(db, malformed.id)
            with pytest.raises(HTTPException) as rejected_bad_split:
                await svc.post_grn(db, malformed, actor_id)
            assert rejected_bad_split.value.status_code == 422
            await db.rollback()

            mismatched = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-MISMATCH", first_po_id, first_po_line_id, "5", "3", "1"),
                actor_id,
            )
            await db.commit()
            mismatched = await get_grn(db, mismatched.id)
            with pytest.raises(HTTPException) as rejected_mismatch:
                await svc.post_grn(db, mismatched, actor_id)
            assert rejected_mismatch.value.status_code == 422
            await db.rollback()

            overreceipt = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-OVER", first_po_id, first_po_line_id, "6", "6", "0"),
                actor_id,
            )
            await db.commit()
            overreceipt = await get_grn(db, overreceipt.id)
            with pytest.raises(HTTPException) as rejected_overreceipt:
                await svc.post_grn(db, overreceipt, actor_id)
            assert rejected_overreceipt.value.status_code == 409
            await db.rollback()

            second = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-2", first_po_id, first_po_line_id, "7", "5", "2"),
                actor_id,
            )
            await db.commit()
            second = await get_grn(db, second.id)
            await svc.post_grn(db, second, actor_id)
            await db.commit()

            persisted = await db.get(BlanketPurchaseAgreement, agreement_id)
            assert persisted.consumed_quantity == Decimal("15.000")
            assert await svc.bpa_open_release_quantity(db, agreement_id) == Decimal("15.000")

            concurrent_first = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-3", second_po_id, second_po_line_id, "7", "7", "0"),
                actor_id,
            )
            concurrent_second = await create_grn(
                db,
                receipt(f"M34-S02-T004-GRN-{suffix}-4", third_po_id, third_po_line_id, "8", "8", "0"),
                actor_id,
            )
            await db.commit()
            concurrent_ids = (concurrent_first.id, concurrent_second.id)

        async def post_receipt(grn_id):
            async with AsyncSessionLocal() as db:
                try:
                    grn = await get_grn(db, grn_id)
                    await svc.post_grn(db, grn, actor_id)
                    await db.commit()
                    return None
                except HTTPException as exc:
                    await db.rollback()
                    return exc

        results = await __import__("asyncio").gather(*(post_receipt(grn_id) for grn_id in concurrent_ids))
        assert results == [None, None]

        async with AsyncSessionLocal() as db:
            persisted = await db.get(BlanketPurchaseAgreement, agreement_id)
            assert persisted.consumed_quantity == Decimal("30.000")
            assert await svc.bpa_open_release_quantity(db, agreement_id) == Decimal("0.000")
            events = (await db.execute(select(AuditLog).where(
                AuditLog.target_id == str(agreement_id),
                AuditLog.event_type == AuditEvent.BPA_CONSUMPTION_RECORDED,
            ))).scalars().all()
            assert len(events) == 4
            assert sorted(Decimal(event.after_value["consumed_quantity"]) for event in events) == [
                Decimal("10.000"), Decimal("15.000"), Decimal("22.000"), Decimal("30.000")
            ]
            second = await get_grn(db, concurrent_ids[0])
            with pytest.raises(HTTPException) as duplicate_post:
                await svc.post_grn(db, second, actor_id)
            assert duplicate_post.value.status_code == 422
            await db.rollback()
            persisted = await db.get(BlanketPurchaseAgreement, agreement_id)
            assert persisted.consumed_quantity == Decimal("30.000")
    finally:
        if agreement_id:
            async with AsyncSessionLocal() as db:
                orders = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.bpa_id == agreement_id))).scalars().all()
                order_ids = [order.id for order in orders]
                grns = (await db.execute(select(GoodsReceipt).where(GoodsReceipt.po_id.in_(order_ids)))).scalars().all() if order_ids else []
                grn_numbers = [row.grn_no for row in grns]
                if grn_numbers:
                    movements = (await db.execute(select(StockMovement).where(StockMovement.reference_number.in_(grn_numbers)))).scalars().all()
                    for movement in movements:
                        await db.delete(movement)
                stocks = (await db.execute(select(Stock).where(Stock.warehouse_id == warehouse_id, Stock.product_id == product_id))).scalars().all()
                for stock in stocks:
                    await db.delete(stock)
                for grn in grns:
                    await db.delete(grn)
                for order in orders:
                    await db.delete(order)
                await db.commit()
                persisted_agreement = await db.get(BlanketPurchaseAgreement, agreement_id)
                if persisted_agreement:
                    await db.delete(persisted_agreement)
                await db.commit()
        async with AsyncSessionLocal() as db:
            for model, object_id in ((Supplier, supplier_id), (Product, product_id), (Warehouse, warehouse_id), (User, actor_id)):
                persisted = await db.get(model, object_id)
                if persisted:
                    await db.delete(persisted)
            await db.commit()
