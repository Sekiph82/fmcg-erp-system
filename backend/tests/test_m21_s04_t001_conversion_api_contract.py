from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.bom import ConversionProfileCreate, ConversionProfileOut
from app.services.bom_scaling_service import calculate_conversion


def _profile(**overrides):
    values = {
        "profile_name": "Bulk to unit",
        "profile_code": "BULK-UNIT",
        "version_no": "1.0",
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
    }
    values.update(overrides)
    return ConversionProfileCreate(**values)


def test_conversion_profile_create_accepts_validated_decimal_contract():
    profile = _profile(
        theoretical_conversion_ratio=Decimal("1000.123456"),
        standard_fill_volume=Decimal("0.5000"),
        fill_volume_uom=" ml ",
        density_g_per_ml=Decimal("0.9000"),
        standard_expected_units=Decimal("900"),
        realistic_expected_units=Decimal("850"),
    )

    assert profile.fill_volume_uom == "ML"
    assert profile.theoretical_conversion_ratio == Decimal("1000.123456")


@pytest.mark.parametrize(
    "overrides",
    [
        {"profile_name": "  "},
        {"theoretical_conversion_ratio": Decimal("0")},
        {"theoretical_conversion_ratio": Decimal("-1")},
        {"theoretical_conversion_ratio": Decimal("1.0000001")},
        {"standard_fill_volume": Decimal("0")},
        {"density_g_per_ml": Decimal("0")},
        {"startup_loss_pct": Decimal("-0.001")},
        {"startup_loss_pct": Decimal("100.001")},
        {"fill_tolerance_pct": Decimal("-0.001")},
        {"standard_expected_units": Decimal("1.5")},
        {"standard_fill_volume": Decimal("1"), "fill_volume_uom": None},
        {"fill_volume_uom": "   "},
        {"effective_from": date(2026, 12, 1), "effective_to": date(2026, 1, 1)},
    ],
)
def test_conversion_profile_create_rejects_invalid_contract_values(overrides):
    with pytest.raises(ValidationError):
        _profile(**overrides)


def test_conversion_profile_output_contract_includes_foreign_keys_and_audit_notes():
    fields = set(ConversionProfileOut.model_fields)

    assert {
        "source_product_id",
        "target_product_id",
        "linked_packaging_bom_id",
        "fill_tolerance_pct",
        "density_g_per_ml",
        "notes",
        "is_active",
    } <= fields


class _NoQueryDatabase:
    async def execute(self, *_args, **_kwargs):
        raise AssertionError("Invalid source quantities must be rejected before database access")


@pytest.mark.asyncio
@pytest.mark.parametrize("source_qty", [Decimal("0"), Decimal("-1"), Decimal("Infinity"), Decimal("NaN")])
async def test_conversion_service_rejects_nonpositive_or_nonfinite_source_qty(source_qty):
    with pytest.raises(HTTPException) as error:
        await calculate_conversion(_NoQueryDatabase(), uuid4(), source_qty)

    assert error.value.status_code == 422
    assert error.value.detail == "source_qty must be positive and finite"
