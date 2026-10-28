"""Disposable-PostgreSQL integration for profile versions and date windows."""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.bom import BOMConversionProfile
from app.schemas.bom import ConversionProfileCreate
from app.services.bom_scaling_service import calculate_conversion
from app.services.bom_service import create_conversion_profile, list_conversion_profiles


pytestmark = pytest.mark.skipif(
    os.environ.get("M21_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest.mark.asyncio
async def test_conversion_profile_versions_are_effective_on_inclusive_dates():
    expected_database = os.environ.get("M21_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert expected_database.startswith("fmcg_m21_s01_t004_")
    profile_code = f"M21-T004-FAMILY-{uuid4().hex[:12]}"

    async with AsyncSessionLocal() as db:
        try:
            actual_database = (await db.execute(text("SELECT current_database()"))).scalar_one()
            assert actual_database == expected_database

            first = BOMConversionProfile(
                profile_code=profile_code,
                profile_name="Synthetic bulk conversion",
                version_no="1.0",
                effective_from=date(2026, 10, 1),
                effective_to=date(2026, 10, 31),
                theoretical_conversion_ratio=Decimal("5"),
                startup_loss_pct=Decimal("0"),
                shutdown_loss_pct=Decimal("0"),
                packaging_reject_pct=Decimal("0"),
                residual_bulk_pct=Decimal("0"),
                line_purge_loss_pct=Decimal("0"),
            )
            second = BOMConversionProfile(
                profile_code=profile_code,
                profile_name="Synthetic bulk conversion",
                version_no="2.0",
                effective_from=date(2026, 11, 1),
                effective_to=None,
                theoretical_conversion_ratio=Decimal("6"),
                startup_loss_pct=Decimal("0"),
                shutdown_loss_pct=Decimal("0"),
                packaging_reject_pct=Decimal("0"),
                residual_bulk_pct=Decimal("0"),
                line_purge_loss_pct=Decimal("0"),
            )
            db.add_all([first, second])
            await db.flush()

            october_profiles = await list_conversion_profiles(db, date(2026, 10, 31))
            november_profiles = await list_conversion_profiles(db, date(2026, 11, 1))
            october_versions = [p.version_no for p in october_profiles if p.profile_code == profile_code]
            november_versions = [p.version_no for p in november_profiles if p.profile_code == profile_code]
            assert october_versions == ["1.0"]
            assert november_versions == ["2.0"]

            boundary_result = await calculate_conversion(
                db,
                first.id,
                Decimal("2"),
                source_uom="L",
                as_of_date=date(2026, 10, 31),
            )
            assert boundary_result.profile_code == profile_code
            assert boundary_result.version_no == "1.0"
            assert boundary_result.as_of_date == date(2026, 10, 31)
            assert boundary_result.theoretical_units == Decimal("10.00")

            next_version_result = await calculate_conversion(
                db,
                second.id,
                Decimal("2"),
                source_uom="L",
                as_of_date=date(2026, 11, 1),
            )
            assert next_version_result.version_no == "2.0"
            assert next_version_result.theoretical_units == Decimal("12.00")

            with pytest.raises(HTTPException) as exc_info:
                await calculate_conversion(
                    db,
                    first.id,
                    Decimal("2"),
                    source_uom="L",
                    as_of_date=date(2026, 11, 1),
                )
            assert exc_info.value.status_code == 422
            assert "expired on" in exc_info.value.detail

            with pytest.raises(HTTPException) as duplicate_info:
                await create_conversion_profile(
                    db,
                    ConversionProfileCreate(
                        profile_code=profile_code,
                        profile_name="Duplicate version",
                        version_no="1.0",
                    ),
                )
            assert duplicate_info.value.status_code == 409
        finally:
            await db.rollback()
