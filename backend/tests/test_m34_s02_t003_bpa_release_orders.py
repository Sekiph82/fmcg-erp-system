"""M34.S02.T003 BPA release-to-purchase-order acceptance tests."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import (
    add_po_line,
    create_bpa,
    create_bpa_release_order,
    list_bpa_release_orders,
    replace_bpa_price_breaks,
    update_po,
    update_bpa,
    _require_exactly_one_bpa_release_target,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditEvent, AuditLog
from app.models.master import Product, ProductCategory, Supplier
from app.models.procurement import BPAStatus, BlanketPurchaseAgreement, POLine, POStatus, PurchaseOrder
from app.models.user import User
from app.schemas.procurement import (
    BlanketAgreementCreate,
    BlanketAgreementPriceBreakInput,
    BlanketAgreementPriceBreakScheduleUpdate,
    BlanketAgreementReleaseCreate,
    BlanketAgreementUpdate,
    POUpdate,
    POLineCreate,
)
from app.services import procurement_service as svc


TASK_DB_ENV = "M34_S02_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S02_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s02_t003_[a-f0-9]{24}")


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


def test_bpa_release_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s02_t003_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


def test_release_target_requires_exactly_one_material_or_product():
    for target in (
        SimpleNamespace(material_id=None, product_id=None),
        SimpleNamespace(material_id=uuid4(), product_id=uuid4()),
    ):
        with pytest.raises(HTTPException) as invalid_target:
            _require_exactly_one_bpa_release_target(target)
        assert invalid_target.value.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_bpa_release_creates_scoped_draft_po_reserves_commitment_and_is_serialized():
    _require_task_database()
    suffix = uuid4().hex[:16]
    today = date.today()
    valid_to = today + timedelta(days=60)
    supplier = Supplier(code=f"M34S02T003-{suffix}", name="Synthetic BPA supplier", is_active=True)
    product = Product(sku=f"M34S02T003-{suffix}", name="Synthetic release product", category=ProductCategory.OTHER, is_active=True)
    actor = User(
        email=f"m34-s02-t003-{suffix}@example.invalid",
        username=f"m34s02t003{suffix}",
        full_name="Synthetic BPA release actor",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    agreement = None
    duplicate_test_agreement_id = None
    try:
        async with AsyncSessionLocal() as db:
            db.add_all([supplier, actor, product])
            await db.commit()
            agreement_read = await create_bpa(
                BlanketAgreementCreate(
                    bpa_no=f"M34-S02-T003-{suffix}",
                    supplier_id=supplier.id,
                    product_id=product.id,
                    description="Synthetic release test item",
                    agreed_unit_price=Decimal("12.5000"),
                    currency="KES",
                    agreed_quantity=Decimal("100.000"),
                    unit="KG",
                    valid_from=today,
                    valid_to=valid_to,
                ),
                db,
                actor,
            )
            agreement = await db.get(BlanketPurchaseAgreement, agreement_read.id)
            await replace_bpa_price_breaks(
                agreement.id,
                BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                    BlanketAgreementPriceBreakInput(
                        min_quantity=Decimal("20"),
                        unit_price=Decimal("10.2500"),
                        effective_from=today,
                        effective_to=valid_to,
                    ),
                ]),
                db,
                actor,
            )

            def request(po_no: str, quantity: str) -> BlanketAgreementReleaseCreate:
                return BlanketAgreementReleaseCreate(
                    po_no=po_no,
                    release_date=today,
                    expected_delivery_date=today + timedelta(days=7),
                    quantity=Decimal(quantity),
                    notes="Synthetic call-off",
                )

            first = await create_bpa_release_order(agreement.id, request(f"M34-S02-T003-PO-{suffix}-1", "30"), db, actor)
            assert first.bpa_id == agreement.id
            assert first.status == POStatus.DRAFT
            assert first.supplier_id == supplier.id
            assert first.lines[0].product_id == product.id
            assert first.currency == "KES"
            assert len(first.lines) == 1
            assert first.lines[0].ordered_quantity == Decimal("30.000")
            assert first.lines[0].unit_price == Decimal("10.2500")
            assert await svc.bpa_open_release_quantity(db, agreement.id) == Decimal("30.000")

            with pytest.raises(HTTPException) as linked_price_break_change:
                await replace_bpa_price_breaks(
                    agreement.id,
                    BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                        BlanketAgreementPriceBreakInput(
                            min_quantity=Decimal("20"),
                            unit_price=Decimal("9.0000"),
                            effective_from=today,
                            effective_to=valid_to,
                        ),
                    ]),
                    db,
                    actor,
                )
            assert linked_price_break_change.value.status_code == 409

            with pytest.raises(HTTPException) as linked_line_change:
                await add_po_line(first.id, POLineCreate(
                    line_no=2,
                    description="Uncontracted line",
                    ordered_quantity=Decimal("1"),
                ), db, actor)
            assert linked_line_change.value.status_code == 409
            with pytest.raises(HTTPException) as linked_scope_change:
                await update_po(first.id, POUpdate(department="Out of agreement scope"), db, actor)
            assert linked_scope_change.value.status_code == 409
            with pytest.raises(HTTPException) as linked_terms_change:
                await update_po(first.id, POUpdate(payment_terms="Immediate"), db, actor)
            assert linked_terms_change.value.status_code == 409
            with pytest.raises(HTTPException) as agreement_term_change:
                await update_bpa(agreement.id, BlanketAgreementUpdate(agreed_unit_price=Decimal("13")), db, actor)
            assert agreement_term_change.value.status_code == 409
            with pytest.raises(HTTPException) as agreement_cancel:
                await update_bpa(agreement.id, BlanketAgreementUpdate(status=BPAStatus.CANCELLED), db, actor)
            assert agreement_cancel.value.status_code == 409

            first_model = await db.get(PurchaseOrder, first.id)
            first_line = await db.get(POLine, first.lines[0].id)
            first_line.received_quantity = first_line.ordered_quantity
            first_model.status = POStatus.RECEIVED
            agreement.consumed_quantity = Decimal("30.000")
            await db.commit()
            with pytest.raises(HTTPException) as completed_release_agreement_cancel:
                await update_bpa(agreement.id, BlanketAgreementUpdate(status=BPAStatus.CANCELLED), db, actor)
            assert completed_release_agreement_cancel.value.status_code == 409

            with pytest.raises(HTTPException) as over_reserved:
                await create_bpa_release_order(agreement.id, request(f"M34-S02-T003-PO-{suffix}-2", "71"), db, actor)
            assert over_reserved.value.status_code == 422

            listed = await list_bpa_release_orders(agreement.id, db, actor)
            assert [row.po_no for row in listed] == [first.po_no]
            audit = (await db.execute(select(AuditLog).where(
                AuditLog.target_id == str(agreement.id),
                AuditLog.event_type == AuditEvent.BPA_RELEASE_CREATED,
            ))).scalars().all()
            assert len(audit) == 1
            assert audit[0].after_value["purchase_order_id"] == str(first.id)

        # Two separate transactions contend on the agreement row. Only one
        # 40-unit call-off can reserve the 70 units remaining after 30 were consumed.
        async def concurrent_release(suffix_part: str):
            async with AsyncSessionLocal() as db:
                try:
                    return await create_bpa_release_order(
                        agreement.id,
                        request(f"M34-S02-T003-PO-{suffix}-{suffix_part}", "40"),
                        db,
                        actor,
                    )
                except HTTPException as exc:
                    await db.rollback()
                    return exc

        outcomes = await __import__("asyncio").gather(
            concurrent_release("A"),
            concurrent_release("B"),
        )
        successes = [item for item in outcomes if not isinstance(item, HTTPException)]
        failures = [item for item in outcomes if isinstance(item, HTTPException)]
        assert len(successes) == 1
        assert len(failures) == 1 and failures[0].status_code == 409

        async with AsyncSessionLocal() as db:
            order = await db.get(PurchaseOrder, successes[0].id)
            order.status = POStatus.CANCELLED
            second_agreement_read = await create_bpa(
                BlanketAgreementCreate(
                    bpa_no=f"M34-S02-T003-DUP-{suffix}",
                    supplier_id=supplier.id,
                    product_id=product.id,
                    description="Synthetic duplicate-number agreement",
                    agreed_unit_price=Decimal("12.5000"),
                    currency="KES",
                    agreed_quantity=Decimal("100.000"),
                    unit="KG",
                    valid_from=today,
                    valid_to=valid_to,
                ),
                db,
                actor,
            )
            duplicate_test_agreement_id = second_agreement_read.id
            await db.commit()

        duplicate_po_no = f"M34-S02-T003-DUP-PO-{suffix}"

        async def concurrent_duplicate(agreement_id):
            async with AsyncSessionLocal() as db:
                try:
                    return await create_bpa_release_order(
                        agreement_id,
                        request(duplicate_po_no, "10"),
                        db,
                        actor,
                    )
                except HTTPException as exc:
                    await db.rollback()
                    return exc

        duplicate_outcomes = await __import__("asyncio").gather(
            concurrent_duplicate(agreement.id),
            concurrent_duplicate(duplicate_test_agreement_id),
        )
        duplicate_successes = [item for item in duplicate_outcomes if not isinstance(item, HTTPException)]
        duplicate_failures = [item for item in duplicate_outcomes if isinstance(item, HTTPException)]
        assert len(duplicate_successes) == 1
        assert len(duplicate_failures) == 1 and duplicate_failures[0].status_code == 409
    finally:
        for agreement_id in (agreement.id if agreement else None, duplicate_test_agreement_id):
            if agreement_id is None:
                continue
            async with AsyncSessionLocal() as db:
                orders = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.bpa_id == agreement_id))).scalars().all()
                for order in orders:
                    await db.delete(order)
                await db.commit()
                persisted_agreement = await db.get(BlanketPurchaseAgreement, agreement_id)
                if persisted_agreement:
                    await db.delete(persisted_agreement)
                await db.commit()
        async with AsyncSessionLocal() as db:
            persisted_supplier = await db.get(Supplier, supplier.id)
            persisted_product = await db.get(Product, product.id)
            persisted_actor = await db.get(User, actor.id)
            if persisted_supplier:
                await db.delete(persisted_supplier)
            if persisted_product:
                await db.delete(persisted_product)
            if persisted_actor:
                await db.delete(persisted_actor)
            await db.commit()
