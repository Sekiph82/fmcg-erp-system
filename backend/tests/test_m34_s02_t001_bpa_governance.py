"""M34.S02.T001 blanket agreement lifecycle and governance acceptance."""
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

from app.api.v1.endpoints.procurement import create_bpa, list_bpas, update_bpa
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditEvent, AuditLog
from app.models.master import Supplier
from app.models.procurement import BPAStatus, BlanketPurchaseAgreement
from app.models.user import User
from app.schemas.procurement import BlanketAgreementCreate, BlanketAgreementUpdate


TASK_DB_ENV = "M34_S02_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S02_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s02_t001_[a-f0-9]{24}")


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
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's passwordless loopback database.")


def test_bpa_create_and_update_schemas_validate_commercial_terms_and_dates():
    today = date.today()
    base = {
        "bpa_no": " BPA-TEST-01 ",
        "supplier_id": uuid4(),
        "agreed_unit_price": "12.3400",
        "currency": "kes",
        "valid_from": today,
        "valid_to": today + timedelta(days=30),
    }
    valid = BlanketAgreementCreate(**base)
    assert valid.bpa_no == "BPA-TEST-01"
    assert valid.currency == "KES"

    for field, value in (
        ("agreed_unit_price", "0"),
        ("agreed_unit_price", "NaN"),
        ("agreed_quantity", "Infinity"),
        ("currency", "US1"),
    ):
        with pytest.raises(ValueError):
            BlanketAgreementCreate(**{**base, field: value})

    with pytest.raises(ValueError):
        BlanketAgreementCreate(**{**base, "valid_to": today - timedelta(days=1)})
    with pytest.raises(ValueError):
        BlanketAgreementUpdate(agreed_quantity="-1")
    with pytest.raises(ValueError):
        BlanketAgreementUpdate(valid_to=None)


def test_bpa_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s02_t001_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_bpa_updates_are_locked_by_lifecycle_and_consumption():
    _require_task_database()
    suffix = uuid4().hex[:16]
    supplier = Supplier(code=f"M34S02T001-{suffix}", name="Synthetic BPA supplier", is_active=True)
    today = date.today()
    actor = User(
        email=f"m34-s02-t001-{suffix}@example.invalid",
        username=f"m34s02t001{suffix}",
        full_name="Synthetic BPA governance actor",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    partially_consumed = BlanketPurchaseAgreement(
        bpa_no=f"M34-S02-T001-B-{suffix}", supplier=supplier,
        agreed_unit_price=Decimal("20.0000"), currency="KES",
        agreed_quantity=Decimal("100.000"), consumed_quantity=Decimal("10.000"),
        unit="KG", valid_from=today, valid_to=today + timedelta(days=30),
        status=BPAStatus.ACTIVE,
    )
    expired = BlanketPurchaseAgreement(
        bpa_no=f"M34-S02-T001-C-{suffix}", supplier=supplier,
        agreed_unit_price=Decimal("30.0000"), currency="KES",
        agreed_quantity=Decimal("100.000"), consumed_quantity=Decimal("0.000"),
        unit="KG", valid_from=today - timedelta(days=60), valid_to=today - timedelta(days=1),
        status=BPAStatus.ACTIVE,
    )
    fully_consumed = BlanketPurchaseAgreement(
        bpa_no=f"M34-S02-T001-D-{suffix}", supplier=supplier,
        agreed_unit_price=Decimal("40.0000"), currency="KES",
        agreed_quantity=Decimal("100.000"), consumed_quantity=Decimal("100.000"),
        unit="KG", valid_from=today - timedelta(days=30), valid_to=today + timedelta(days=30),
        status=BPAStatus.ACTIVE,
    )
    scheduled = BlanketPurchaseAgreement(
        bpa_no=f"M34-S02-T001-E-{suffix}", supplier=supplier,
        agreed_unit_price=Decimal("50.0000"), currency="KES",
        agreed_quantity=Decimal("100.000"), consumed_quantity=Decimal("0.000"),
        unit="KG", valid_from=today + timedelta(days=1), valid_to=today + timedelta(days=60),
        status=BPAStatus.ACTIVE,
    )

    async with AsyncSessionLocal() as db:
        db.add_all([supplier, actor, partially_consumed, expired, fully_consumed, scheduled])
        await db.commit()
        try:
            created = await create_bpa(
                BlanketAgreementCreate(
                    bpa_no=f"M34-S02-T001-A-{suffix}",
                    supplier_id=supplier.id,
                    agreed_unit_price=Decimal("10.0000"),
                    currency="KES",
                    agreed_quantity=Decimal("100.000"),
                    unit="KG",
                    valid_from=today,
                    valid_to=today + timedelta(days=30),
                ),
                db,
                actor,
            )
            active_id = created.id
            changed = await update_bpa(
                active_id,
                BlanketAgreementUpdate(agreed_unit_price="11.5000", notes="Synthetic active amendment."),
                db,
                actor,
            )
            assert changed.agreed_unit_price == Decimal("11.5000")
            assert changed.notes == "Synthetic active amendment."

            active_events = (
                await db.execute(
                    select(AuditLog).where(AuditLog.target_id == str(active_id)).order_by(AuditLog.created_at)
                )
            ).scalars().all()
            assert [event.event_type for event in active_events] == [
                AuditEvent.BPA_CREATED,
                AuditEvent.BPA_UPDATED,
            ]
            assert active_events[1].before_value == {"agreed_unit_price": "10.0000", "notes": None}
            assert active_events[1].after_value == {
                "agreed_unit_price": "11.5000",
                "notes": "Synthetic active amendment.",
            }

            with pytest.raises(HTTPException) as mixed_cancel_edit:
                await update_bpa(
                    active_id,
                    BlanketAgreementUpdate(status=BPAStatus.CANCELLED, notes="Must not piggyback on cancel."),
                    db,
                    actor,
                )
            assert mixed_cancel_edit.value.status_code == 422
            assert (await db.get(BlanketPurchaseAgreement, active_id)).status == BPAStatus.ACTIVE

            with pytest.raises(HTTPException) as consumed_terms:
                await update_bpa(
                    partially_consumed.id,
                    BlanketAgreementUpdate(agreed_unit_price="21.0000"),
                    db,
                    actor,
                )
            assert consumed_terms.value.status_code == 409

            with pytest.raises(HTTPException) as consumed_payment_terms:
                await update_bpa(
                    partially_consumed.id,
                    BlanketAgreementUpdate(payment_terms="Net 30"),
                    db,
                    actor,
                )
            assert consumed_payment_terms.value.status_code == 409

            cancelled = await update_bpa(
                partially_consumed.id,
                BlanketAgreementUpdate(status=BPAStatus.CANCELLED),
                db,
                actor,
            )
            assert cancelled.status == BPAStatus.CANCELLED
            with pytest.raises(HTTPException) as cancelled_edit:
                await update_bpa(
                    partially_consumed.id,
                    BlanketAgreementUpdate(notes="After terminal cancellation."),
                    db,
                    actor,
                )
            assert cancelled_edit.value.status_code == 409

            with pytest.raises(HTTPException) as expired_edit:
                await update_bpa(expired.id, BlanketAgreementUpdate(notes="Late amendment."), db, actor)
            assert expired_edit.value.status_code == 409

            with pytest.raises(HTTPException) as full_cancel:
                await update_bpa(fully_consumed.id, BlanketAgreementUpdate(status=BPAStatus.CANCELLED), db, actor)
            assert full_cancel.value.status_code == 409

            rows = await list_bpas(status=BPAStatus.EXPIRED, limit=200, db=db, current_user=actor)
            expired_row = next(row for row in rows if row.id == expired.id)
            assert expired_row.status == BPAStatus.EXPIRED
            active_rows = await list_bpas(status=BPAStatus.ACTIVE, limit=200, db=db, current_user=actor)
            assert all(row.id != expired.id for row in active_rows)
            assert all(row.id != scheduled.id for row in active_rows)
            all_rows = await list_bpas(limit=200, db=db, current_user=actor)
            scheduled_row = next(row for row in all_rows if row.id == scheduled.id)
            assert scheduled_row.is_scheduled is True
            assert scheduled_row.is_expired is False
        finally:
            await db.rollback()
