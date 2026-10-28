from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.bom import BOMType, BasisType, ComponentType
from app.services.bom_scaling_service import calculate_package_components


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class _FakeDatabase:
    def __init__(self, *results):
        self.results = iter(results)

    async def execute(self, _query):
        return _Result(next(self.results))


def _line(*, line_no, item_name, component_type, quantity, wastage="0"):
    return SimpleNamespace(
        line_no=line_no,
        item_id=uuid4(),
        item_name=item_name,
        item_code=f"PKG-{line_no}",
        component_type=component_type,
        required_qty=Decimal(quantity),
        required_uom="PCS",
        basis_type=BasisType.PER_UNIT,
        wastage_pct=Decimal(wastage),
        process_loss_pct=Decimal("0"),
        fixed_consumption=False,
        critical_component=False,
    )


@pytest.mark.asyncio
async def test_package_requirements_are_scaled_for_exact_target_sku_and_filter_nonpack_lines():
    profile_id = uuid4()
    product_id = uuid4()
    bom_id = uuid4()
    profile = SimpleNamespace(
        id=profile_id,
        target_product_id=product_id,
        linked_packaging_bom_id=bom_id,
    )
    product = SimpleNamespace(
        id=product_id, sku="SKU-500ML", name="Synthetic 500 ml SKU", uom="PCS"
    )
    bom = SimpleNamespace(
        id=bom_id,
        bom_type=BOMType.PACKAGING,
        product_id=product_id,
        base_qty=Decimal("100"),
        base_uom="PCS",
    )
    lines = [
        _line(
            line_no=1,
            item_name="Synthetic bottle",
            component_type=ComponentType.PACKAGING,
            quantity="1",
        ),
        _line(
            line_no=2,
            item_name="Synthetic cap",
            component_type=ComponentType.PACKAGING,
            quantity="1",
            wastage="2",
        ),
        _line(
            line_no=3,
            item_name="Bulk liquid",
            component_type=ComponentType.INTERMEDIATE,
            quantity="0.5",
        ),
    ]
    db = _FakeDatabase(profile, product, bom, lines)

    result = await calculate_package_components(db, profile_id, Decimal("250"))

    assert result.target_sku == "SKU-500ML"
    assert result.target_product_id == product_id
    assert result.normalized_qty == Decimal("250")
    assert result.normalized_uom == "PCS"
    assert [component.item_name for component in result.components] == [
        "Synthetic bottle",
        "Synthetic cap",
    ]
    assert [component.scaled_qty for component in result.components] == [
        Decimal("250.0000"),
        Decimal("250.0000"),
    ]
    assert result.components[1].adjusted_qty == Decimal("255.0000")


@pytest.mark.asyncio
async def test_package_requirements_reject_a_bom_for_another_sku():
    profile_id = uuid4()
    product_id = uuid4()
    profile = SimpleNamespace(
        id=profile_id,
        target_product_id=product_id,
        linked_packaging_bom_id=uuid4(),
    )
    product = SimpleNamespace(id=product_id, sku="SKU-A", name="SKU A", uom="PCS")
    bom = SimpleNamespace(
        id=profile.linked_packaging_bom_id,
        bom_type=BOMType.PACKAGING,
        product_id=uuid4(),
        base_qty=Decimal("1"),
        base_uom="PCS",
    )
    db = _FakeDatabase(profile, product, bom)

    with pytest.raises(HTTPException) as exc_info:
        await calculate_package_components(db, profile_id, Decimal("1"))

    assert exc_info.value.status_code == 422
    assert "target product/SKU" in exc_info.value.detail


@pytest.mark.parametrize(
    "target_qty",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")],
)
@pytest.mark.asyncio
async def test_package_requirements_reject_nonpositive_or_nonfinite_target_quantity(target_qty):
    with pytest.raises(HTTPException) as exc_info:
        await calculate_package_components(_FakeDatabase(), uuid4(), target_qty)

    assert exc_info.value.status_code == 422
    assert "positive and finite" in exc_info.value.detail
