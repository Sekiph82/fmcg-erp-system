"""Estimated-versus-actual landed-cost behavior and disposable-DB persistence."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, engine
from app.models.landed_cost import (
    LandedCostAllocationLine,
    LandedCostType,
)
from app.models.user import User
from app.schemas.landed_cost import (
    LandedCostHeaderCreate,
    LandedCostLineActualCreate,
    LandedCostLineCreate,
    LandedCostLineOut,
)
from app.services import landed_cost_service as service


def test_actual_source_reference_is_required_and_trimmed():
    assert LandedCostLineActualCreate(amount_fc=Decimal("12.3456"), source_reference=" INV-42 ").source_reference == "INV-42"
    with pytest.raises(ValidationError):
        LandedCostLineActualCreate(amount_fc=Decimal("12"), source_reference="   ")


def test_estimated_and_actual_amounts_fit_the_numeric_storage_range():
    assert LandedCostLineActualCreate(
        amount_fc=Decimal("9999999999.99994"), source_reference="INV-EDGE"
    ).amount_fc == Decimal("9999999999.99994")
    with pytest.raises(ValidationError):
        LandedCostLineActualCreate(amount_fc=Decimal("9999999999.99995"), source_reference="INV-OVERFLOW")
    with pytest.raises(ValidationError):
        LandedCostLineActualCreate(amount_fc=Decimal("NaN"), source_reference="INV-NAN")
    with pytest.raises(ValidationError):
        LandedCostLineCreate(
            cost_type=LandedCostType.OTHER,
            estimated_amount_fc=Decimal("10000000000"),
        )
    with pytest.raises(ValidationError):
        LandedCostLineCreate(
            cost_type=LandedCostType.OTHER,
            amount_fc=Decimal("Infinity"),
        )


def test_variance_is_actual_minus_estimate_and_respects_exchange_rate():
    line = LandedCostLineOut.model_validate(SimpleNamespace(
        id=uuid4(),
        header_id=uuid4(),
        cost_type="OTHER",
        amount_fc=Decimal("13.25"),
        estimated_amount_fc=Decimal("12.50"),
        currency_code="USD",
        exchange_rate=Decimal("130.000000"),
        amount_base=Decimal("1625"),
        actual_record=SimpleNamespace(
            id=uuid4(),
            lc_line_id=uuid4(),
            amount_fc=Decimal("13.25"),
            source_reference="INV-42",
            recorded_by_id=None,
            recorded_at=datetime.now(timezone.utc),
        ),
        allocation_method=None,
        is_included_in_valuation=True,
        description=None,
        vendor_name=None,
        account_code=None,
        remarks=None,
    ))
    assert line.variance_fc == Decimal("0.75")
    assert line.variance_base == Decimal("97.50000000")


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("M25_S02_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)
async def test_estimate_backfill_actual_recording_and_posted_amount_preservation():
    expected_name = os.environ.get("M25_S02_T003_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert re.fullmatch(r"fmcg_m25_s02_t003_[a-f0-9]{20}", expected_name)

    async with AsyncSessionLocal() as db:
        actual_name = (await db.execute(text("SELECT current_database()"))).scalar_one()
        assert actual_name == expected_name

        legacy_estimate = (await db.execute(text(
            "SELECT estimated_amount_fc FROM lc_lines WHERE id = :line_id"
        ), {"line_id": "25000000-0000-0000-0000-000000000039"})).scalar_one()
        assert legacy_estimate == Decimal("25.1250")

        user_id = uuid4()
        db.add(User(
            id=user_id,
            email=f"m25-t003-{user_id}@example.invalid",
            username=f"m25_t003_{user_id.hex}",
            full_name="Synthetic finance user",
            hashed_password="not-a-real-login",
        ))
        await db.flush()

        draft = await service.create_header(db, LandedCostHeaderCreate(
            currency_code="USD",
            cost_lines=[LandedCostLineCreate(
                cost_type=LandedCostType.FREIGHT_SEA,
                amount_fc=Decimal("10.00"),
                estimated_amount_fc=Decimal("10.00"),
                exchange_rate=Decimal("130"),
            )],
        ))
        draft_line = draft.cost_lines[0]
        draft.allocation_lines.append(LandedCostAllocationLine(
            lc_line_id=draft_line.id,
            allocated_amount=Decimal("10.0000"),
            is_posted=False,
        ))
        draft.status = "VALIDATED"
        await db.commit()

        updated = await service.record_actual_cost(
            db,
            draft.id,
            draft_line.id,
            LandedCostLineActualCreate(amount_fc=Decimal("12.50"), source_reference="INV-SYN-01"),
            recorded_by_id=user_id,
        )
        assert updated.status == "DRAFT"
        assert updated.cost_lines[0].estimated_amount_fc == Decimal("10.0000")
        assert updated.cost_lines[0].amount_fc == Decimal("12.5000")
        assert updated.cost_lines[0].amount_base == Decimal("1625.0000")
        assert updated.total_lc_amount_fc == Decimal("12.5000")
        assert updated.total_lc_amount_base == Decimal("1625.0000")
        assert updated.cost_lines[0].actual_record.amount_fc == Decimal("12.5000")
        assert updated.cost_lines[0].actual_record.source_reference == "INV-SYN-01"
        assert updated.cost_lines[0].actual_record.recorded_by_id == user_id
        updated_line = LandedCostLineOut.model_validate(updated.cost_lines[0])
        assert updated_line.variance_fc == Decimal("2.5000")
        assert updated.allocation_lines == []

        with pytest.raises(ValueError, match="already recorded"):
            await service.record_actual_cost(
                db,
                draft.id,
                draft_line.id,
                LandedCostLineActualCreate(amount_fc=Decimal("12.75"), source_reference="INV-SYN-02"),
                recorded_by_id=user_id,
            )

        inconsistent = await service.create_header(db, LandedCostHeaderCreate(
            cost_lines=[LandedCostLineCreate(
                cost_type=LandedCostType.INSURANCE,
                amount_fc=Decimal("4.00"),
            )],
        ))
        inconsistent_line = inconsistent.cost_lines[0]
        inconsistent.allocation_lines.append(LandedCostAllocationLine(
            lc_line_id=inconsistent_line.id,
            allocated_amount=Decimal("4.0000"),
            is_posted=True,
        ))
        await db.commit()
        with pytest.raises(ValueError, match="Posted allocations are immutable"):
            await service.record_actual_cost(
                db,
                inconsistent.id,
                inconsistent_line.id,
                LandedCostLineActualCreate(amount_fc=Decimal("5.00"), source_reference="INV-SYN-BLOCK"),
                recorded_by_id=user_id,
            )
        unchanged = await service.get_header(db, inconsistent.id)
        assert unchanged.cost_lines[0].amount_fc == Decimal("4.0000")
        assert unchanged.cost_lines[0].actual_record is None
        assert len(unchanged.allocation_lines) == 1

        posted = await service.create_header(db, LandedCostHeaderCreate(
            currency_code="USD",
            cost_lines=[LandedCostLineCreate(
                cost_type=LandedCostType.CUSTOMS_DUTY,
                amount_fc=Decimal("8.00"),
                estimated_amount_fc=Decimal("8.00"),
                exchange_rate=Decimal("130"),
            )],
        ))
        posted_line = posted.cost_lines[0]
        posted.status = "POSTED"
        await db.commit()
        posted_actual = await service.record_actual_cost(
            db,
            posted.id,
            posted_line.id,
            LandedCostLineActualCreate(amount_fc=Decimal("9.25"), source_reference="INV-SYN-POSTED"),
            recorded_by_id=user_id,
        )
        assert posted_actual.status == "POSTED"
        assert posted_actual.cost_lines[0].amount_fc == Decimal("8.0000")
        assert posted_actual.cost_lines[0].amount_base == Decimal("1040.0000")
        assert posted_actual.cost_lines[0].actual_record.amount_fc == Decimal("9.2500")
        posted_line = LandedCostLineOut.model_validate(posted_actual.cost_lines[0])
        assert posted_line.variance_fc == Decimal("1.2500")

    await engine.dispose()
