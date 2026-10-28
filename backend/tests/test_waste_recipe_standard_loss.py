from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.crud.production_advanced import _recipe_standard_loss_pct, _weighted_recipe_loss_pct, create_waste_record, update_waste_record
from app.schemas.production_advanced import WasteRecordCreate, WasteRecordUpdate


class Rows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values

    def scalar_one_or_none(self):
        return self.values


def test_recipe_item_loss_uses_quantity_weighting_within_one_material_and_uom():
    rows = [(Decimal("10"), Decimal("2")), (Decimal("30"), Decimal("4"))]
    assert _weighted_recipe_loss_pct(rows) == Decimal("3.500")


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [(Decimal("0"), Decimal("2"))],
        [(Decimal("-1"), Decimal("2"))],
        [(Decimal("1"), Decimal("-2"))],
        [(Decimal("10"), Decimal("NaN"))],
    ],
)
def test_recipe_item_loss_is_unavailable_for_missing_or_invalid_basis(rows):
    assert _weighted_recipe_loss_pct(rows) is None


@pytest.mark.asyncio
async def test_standard_loss_uses_production_order_recipe_and_material_uom():
    recipe_id = uuid4()
    material_id = uuid4()
    order_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(recipe_id=recipe_id)
    db.execute.return_value = Rows([
        (Decimal("10"), Decimal("2")),
        (Decimal("30"), Decimal("4")),
    ])
    record = SimpleNamespace(
        material_id=material_id,
        material_code=None,
        uom="kg",
        production_order_id=order_id,
    )

    result = await _recipe_standard_loss_pct(db, record)

    assert result == Decimal("3.500")
    db.get.assert_awaited_once()
    db.execute.assert_awaited_once()
    query = str(db.execute.await_args.args[0])
    assert "recipe_items.unit" in query
    assert "upper(trim(recipe_items.unit))" in query.lower()


@pytest.mark.asyncio
async def test_create_snapshots_recipe_standard_and_update_preserves_it():
    db = AsyncMock()
    db.add = Mock()
    db.get.return_value = SimpleNamespace(recipe_id=uuid4())
    db.execute.return_value = Rows([(Decimal("100"), Decimal("2.5"))])
    data = WasteRecordCreate(
        waste_id="SYN-T003-1",
        production_order_id=uuid4(),
        material_id=uuid4(),
        expected_qty=Decimal("100"),
        actual_qty=Decimal("96"),
        uom="KG",
    )

    record = await create_waste_record(db, data)

    assert record.standard_loss_pct == Decimal("2.500")
    assert record.loss_pct == Decimal("4.000")
    updated = await update_waste_record(
        db,
        record,
        WasteRecordUpdate(actual_qty=Decimal("97")),
    )
    assert updated.standard_loss_pct == Decimal("2.500")
    assert updated.loss_pct == Decimal("3.000")


@pytest.mark.asyncio
async def test_standard_loss_resolves_material_code_and_leaves_unmatched_records_unknown():
    material_id = uuid4()
    db = AsyncMock()
    db.execute.side_effect = [
        Rows(material_id),
        Rows([]),
    ]
    db.get.return_value = SimpleNamespace(recipe_id=uuid4())
    record = SimpleNamespace(
        material_id=None,
        material_code=" MAT-1 ",
        uom="KG",
        production_order_id=uuid4(),
    )

    result = await _recipe_standard_loss_pct(db, record)

    assert result is None
    assert record.material_id == material_id
    assert record.material_code == "MAT-1"
    assert db.execute.await_count == 2