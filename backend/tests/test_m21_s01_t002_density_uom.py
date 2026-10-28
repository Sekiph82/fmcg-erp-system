from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.master import UnitOfMeasure
from app.services import bom_scaling_service
from app.services.bom_scaling_service import calculate_conversion


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDatabase:
    def __init__(self, *results):
        self.results = iter(results)

    async def execute(self, _query):
        return _ScalarResult(next(self.results))


def _profile(*, source_product_id=None, density=None, ratio="1"):
    return SimpleNamespace(
        id=uuid4(),
        source_product_id=source_product_id,
        density_g_per_ml=Decimal(density) if density is not None else None,
        theoretical_conversion_ratio=Decimal(ratio),
        startup_loss_pct=Decimal("0"),
        shutdown_loss_pct=Decimal("0"),
        packaging_reject_pct=Decimal("0"),
        residual_bulk_pct=Decimal("0"),
        line_purge_loss_pct=Decimal("0"),
        standard_fill_volume=None,
    )


@pytest.mark.parametrize(
    ("quantity", "from_uom", "to_uom", "density", "expected"),
    [
        ("1000", "G", "KG", None, "1"),
        ("2", "L", "ML", None, "2000"),
        ("1", "L", "KG", "0.9", "0.9"),
        ("1800", "G", "L", "0.9", "2"),
    ],
)
def test_standard_mass_volume_uom_conversion(quantity, from_uom, to_uom, density, expected):
    result = bom_scaling_service._convert_standard_bulk_uom(
        Decimal(quantity),
        from_uom,
        to_uom,
        Decimal(density) if density is not None else None,
    )
    assert result == Decimal(expected)


@pytest.mark.parametrize(
    "density",
    [
        None,
        Decimal("0"),
        Decimal("-0.9"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_mass_volume_conversion_requires_positive_density(density):
    with pytest.raises(HTTPException) as exc_info:
        bom_scaling_service._convert_standard_bulk_uom(
            Decimal("1"), "L", "KG", density
        )
    assert exc_info.value.status_code == 422
    assert "density_g_per_ml" in exc_info.value.detail


@pytest.mark.asyncio
async def test_conversion_normalizes_input_to_source_product_uom_using_density():
    source_product_id = uuid4()
    profile = _profile(source_product_id=source_product_id, density="0.9", ratio="1000")
    db = _FakeDatabase(profile, UnitOfMeasure.KG)

    result = await calculate_conversion(
        db, profile.id, Decimal("1"), source_uom="L"
    )

    assert result.source_uom == "L"
    assert result.theoretical_units == Decimal("900.00")
    assert "Normalized source quantity = 0.9 KG" in result.notes


@pytest.mark.asyncio
async def test_conversion_uses_configured_uom_conversion_for_nonstandard_units(monkeypatch):
    source_product_id = uuid4()
    profile = _profile(source_product_id=source_product_id, ratio="10")
    calls = []

    async def configured_conversion(_db, quantity, from_uom, to_uom):
        calls.append((quantity, from_uom, to_uom))
        return quantity * Decimal("2")

    monkeypatch.setattr(bom_scaling_service, "convert_uom", configured_conversion)
    db = _FakeDatabase(profile, "CARTON")
    result = await calculate_conversion(db, profile.id, Decimal("3"), "BOX")

    assert calls == [(Decimal("3"), "BOX", "CARTON")]
    assert result.theoretical_units == Decimal("60.00")
    assert result.source_uom == "BOX"


@pytest.mark.parametrize(
    ("direct", "inverse", "expected"),
    [
        (SimpleNamespace(factor=Decimal("0.5")), None, Decimal("1.50")),
        (None, SimpleNamespace(factor=Decimal("2")), Decimal("1.50")),
    ],
)
@pytest.mark.asyncio
async def test_conversion_uses_direct_or_inverse_configured_uom_factor(direct, inverse, expected):
    source_product_id = uuid4()
    profile = _profile(source_product_id=source_product_id, ratio="1")
    db = _FakeDatabase(profile, "CARTON", direct, inverse)

    result = await calculate_conversion(db, profile.id, Decimal("3"), "BOX")

    assert result.theoretical_units == expected
    assert "Normalized source quantity = 1.5 CARTON" in result.notes


@pytest.mark.asyncio
async def test_conversion_requires_a_source_uom_without_a_linked_source_product():
    profile = _profile()
    db = _FakeDatabase(profile)

    with pytest.raises(HTTPException) as exc_info:
        await calculate_conversion(db, profile.id, Decimal("3"))
    assert exc_info.value.status_code == 422
    assert "Source UOM is required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_explicit_source_uom_is_basis_without_a_linked_source_product():
    profile = _profile(ratio="2")
    db = _FakeDatabase(profile)

    result = await calculate_conversion(db, profile.id, Decimal("3"), "L")

    assert result.source_uom == "L"
    assert result.theoretical_units == Decimal("6.00")
    assert "Normalized source quantity = 3 L" in result.notes
