"""M34.S02.T002 price-break and commitment acceptance tests."""
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import (
    create_bpa,
    list_bpa_price_breaks,
    replace_bpa_price_breaks,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditEvent, AuditLog
from app.models.master import Supplier
from app.models.procurement import BPAStatus, BlanketAgreementPriceBreak, BlanketPurchaseAgreement
from app.models.user import User
from app.schemas.procurement import (
    BlanketAgreementCreate,
    BlanketAgreementPriceBreakInput,
    BlanketAgreementPriceBreakScheduleUpdate,
)
from app.services.procurement_service import resolve_bpa_unit_price


TASK_DB_ENV = "M34_S02_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S02_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s02_t002_[a-f0-9]{24}")


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


def _break(minimum: str, price: str, start: date, end: date):
    return SimpleNamespace(
        min_quantity=Decimal(minimum),
        unit_price=Decimal(price),
        effective_from=start,
        effective_to=end,
    )


def test_price_break_schema_and_all_units_resolution_enforce_dates_and_commitment():
    today = date.today()
    agreement = SimpleNamespace(
        status=BPAStatus.ACTIVE,
        valid_from=today,
        valid_to=today + timedelta(days=60),
        agreed_quantity=Decimal("1000.000"),
        consumed_quantity=Decimal("100.000"),
        agreed_unit_price=Decimal("12.0000"),
        price_breaks=[
            _break("100", "11.0000", today, today + timedelta(days=9)),
            _break("100", "10.5000", today + timedelta(days=10), today + timedelta(days=60)),
            _break("500", "9.5000", today, today + timedelta(days=60)),
        ],
    )

    assert resolve_bpa_unit_price(agreement, Decimal("50"), today) == Decimal("12.0000")
    assert resolve_bpa_unit_price(agreement, Decimal("200"), today) == Decimal("11.0000")
    assert resolve_bpa_unit_price(agreement, Decimal("200"), today + timedelta(days=20)) == Decimal("10.5000")
    assert resolve_bpa_unit_price(agreement, Decimal("600"), today) == Decimal("9.5000")

    with pytest.raises(ValueError, match="remaining"):
        resolve_bpa_unit_price(agreement, Decimal("901"), today)
    with pytest.raises(ValueError, match="validity"):
        resolve_bpa_unit_price(agreement, Decimal("10"), today - timedelta(days=1))
    with pytest.raises(ValueError, match="finite"):
        resolve_bpa_unit_price(agreement, Decimal("NaN"), today)

    with pytest.raises(ValueError):
        BlanketAgreementPriceBreakInput(
            min_quantity="10", unit_price="2", effective_from=today,
            effective_to=today - timedelta(days=1),
        )
    with pytest.raises(ValueError):
        BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[{
            "min_quantity": "Infinity", "unit_price": "2",
            "effective_from": today, "effective_to": today + timedelta(days=1),
        }])


def test_price_break_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s02_t002_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_bpa_price_break_schedule_is_audited_and_respects_validity_commitment_and_consumption():
    _require_task_database()
    suffix = uuid4().hex[:16]
    today = date.today()
    valid_to = today + timedelta(days=60)
    supplier = Supplier(code=f"M34S02T002-{suffix}", name="Synthetic price-break supplier", is_active=True)
    actor = User(
        email=f"m34-s02-t002-{suffix}@example.invalid",
        username=f"m34s02t002{suffix}",
        full_name="Synthetic BPA price-break actor",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )

    async with AsyncSessionLocal() as db:
        db.add_all([supplier, actor])
        await db.commit()
        try:
            agreement = await create_bpa(
                BlanketAgreementCreate(
                    bpa_no=f"M34-S02-T002-{suffix}",
                    supplier_id=supplier.id,
                    agreed_unit_price=Decimal("12.0000"),
                    currency="KES",
                    agreed_quantity=Decimal("1000.000"),
                    unit="KG",
                    valid_from=today,
                    valid_to=valid_to,
                ),
                db,
                actor,
            )
            schedule = BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("100"), unit_price=Decimal("11.0000"),
                    effective_from=today, effective_to=today + timedelta(days=9),
                ),
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("100"), unit_price=Decimal("10.5000"),
                    effective_from=today + timedelta(days=10), effective_to=valid_to,
                ),
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("500"), unit_price=Decimal("9.5000"),
                    effective_from=today, effective_to=valid_to,
                ),
            ])
            saved = await replace_bpa_price_breaks(agreement.id, schedule, db, actor)
            assert len(saved) == 3

            listed = await list_bpa_price_breaks(agreement.id, db, actor)
            assert [(row.min_quantity, row.unit_price) for row in listed] == [
                (Decimal("100.000"), Decimal("11.0000")),
                (Decimal("100.000"), Decimal("10.5000")),
                (Decimal("500.000"), Decimal("9.5000")),
            ]
            persisted = await db.get(BlanketPurchaseAgreement, agreement.id)
            await db.refresh(persisted, attribute_names=["price_breaks"])
            assert resolve_bpa_unit_price(persisted, Decimal("200"), today) == Decimal("11.0000")
            assert resolve_bpa_unit_price(persisted, Decimal("200"), today + timedelta(days=20)) == Decimal("10.5000")
            assert resolve_bpa_unit_price(persisted, Decimal("600"), today) == Decimal("9.5000")

            events = (
                await db.execute(
                    select(AuditLog).where(AuditLog.target_id == str(agreement.id)).order_by(AuditLog.created_at)
                )
            ).scalars().all()
            assert [event.event_type for event in events] == [
                AuditEvent.BPA_CREATED,
                AuditEvent.BPA_PRICE_BREAKS_UPDATED,
            ]
            assert events[1].details == {"break_count": 3, "pricing_method": "ALL_UNITS"}

            invalid_db_values = (
                {"min_quantity": Decimal("NaN"), "unit_price": Decimal("1.0000")},
                {"min_quantity": Decimal("1.000"), "unit_price": Decimal("NaN")},
            )
            for values in invalid_db_values:
                with pytest.raises(IntegrityError):
                    async with db.begin_nested():
                        db.add(BlanketAgreementPriceBreak(
                            agreement_id=agreement.id,
                            min_quantity=values["min_quantity"],
                            unit_price=values["unit_price"],
                            effective_from=today,
                            effective_to=valid_to,
                        ))
                        await db.flush()

            overlap = BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("100"), unit_price=Decimal("11"),
                    effective_from=today, effective_to=today + timedelta(days=20),
                ),
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("100"), unit_price=Decimal("10"),
                    effective_from=today + timedelta(days=20), effective_to=valid_to,
                ),
            ])
            with pytest.raises(HTTPException) as overlapping_windows:
                await replace_bpa_price_breaks(agreement.id, overlap, db, actor)
            assert overlapping_windows.value.status_code == 422

            out_of_period = BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("100"), unit_price=Decimal("11"),
                    effective_from=today - timedelta(days=1), effective_to=valid_to,
                ),
            ])
            with pytest.raises(HTTPException) as invalid_period:
                await replace_bpa_price_breaks(agreement.id, out_of_period, db, actor)
            assert invalid_period.value.status_code == 422

            over_commitment = BlanketAgreementPriceBreakScheduleUpdate(price_breaks=[
                BlanketAgreementPriceBreakInput(
                    min_quantity=Decimal("1001"), unit_price=Decimal("11"),
                    effective_from=today, effective_to=valid_to,
                ),
            ])
            with pytest.raises(HTTPException) as invalid_commitment:
                await replace_bpa_price_breaks(agreement.id, over_commitment, db, actor)
            assert invalid_commitment.value.status_code == 422

            persisted.consumed_quantity = Decimal("10.000")
            await db.commit()
            with pytest.raises(HTTPException) as locked_schedule:
                await replace_bpa_price_breaks(agreement.id, schedule, db, actor)
            assert locked_schedule.value.status_code == 409
        finally:
            await db.rollback()
