from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.models.bom import ComponentType, ItemLinkType
from app.services.bom_costing_service import compute_bom_cost


class _Rows:
    def __init__(self, scalar=None, rows=None):
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_co_product_and_by_product_quantities_are_reported_without_cost_credits():
    bom = SimpleNamespace(
        id=uuid4(), bom_code="MULTI-OUTPUT", bom_name="Synthetic multi-output BOM",
        base_qty=Decimal("2"), base_uom="KG", standard_batch_cost=None,
        standard_cost_per_uom=None, total_raw_cost=None,
        total_packaging_cost=None, by_product_credit=None, costing_updated_at=None,
    )
    co_product_id = uuid4()
    by_product_id = uuid4()
    lines = [
        SimpleNamespace(
            line_no=1, component_type=ComponentType.RAW, item_type=ItemLinkType.MATERIAL,
            item_id=uuid4(), item_code="RAW-1", item_name="Raw input", required_qty=Decimal("10"),
            required_uom="KG", wastage_pct=Decimal("0"), process_loss_pct=Decimal("0"),
            unit_cost=Decimal("2"),
        ),
        SimpleNamespace(
            line_no=2, component_type=ComponentType.CO_PRODUCT, item_type=ItemLinkType.PRODUCT,
            item_id=co_product_id, item_code="CO-1", item_name="Co-product",
            required_qty=Decimal("3.5"), required_uom="L",
        ),
        SimpleNamespace(
            line_no=3, component_type=ComponentType.BY_PRODUCT, item_type=ItemLinkType.PRODUCT,
            item_id=by_product_id, item_code="BY-1", item_name="By-product",
            required_qty=Decimal("1.25"), required_uom="KG",
        ),
    ]
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Rows(scalar=bom), _Rows(rows=lines)]),
        flush=AsyncMock(),
    )

    result = await compute_bom_cost(db, bom.id)

    assert result.raw_material_cost == Decimal("20.0000")
    assert result.total_batch_cost == Decimal("20.0000")
    assert result.cost_per_uom == Decimal("10.0000")
    assert result.by_product_credit == Decimal("0.0000")
    assert bom.by_product_credit == Decimal("0.0000")
    assert len(result.lines) == 1
    assert [output.model_dump() for output in result.co_product_outputs] == [{
        "line_no": 2, "item_id": str(co_product_id), "item_type": "PRODUCT",
        "item_code": "CO-1", "item_name": "Co-product", "component_type": "CO_PRODUCT",
        "quantity": Decimal("3.5000"), "uom": "L",
    }]
    assert [output.model_dump() for output in result.by_product_outputs] == [{
        "line_no": 3, "item_id": str(by_product_id), "item_type": "PRODUCT",
        "item_code": "BY-1", "item_name": "By-product", "component_type": "BY_PRODUCT",
        "quantity": Decimal("1.2500"), "uom": "KG",
    }]
