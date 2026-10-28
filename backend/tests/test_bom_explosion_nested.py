from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import bom as bom_routes
from app.models.bom import BasisType, ComponentType, ItemLinkType
from app.services import bom_explosion_service as explosion


_AUTO_ITEM_ID = object()


def _line(*, item_name, required_qty, required_uom="KG", child_bom_id=None,
          wastage_pct=0, process_loss_pct=0, item_id=_AUTO_ITEM_ID, item_code=None,
          item_type=ItemLinkType.MATERIAL, component_type=ComponentType.RAW):
    return SimpleNamespace(
        id=uuid4(),
        child_bom_id=child_bom_id,
        fixed_consumption=False,
        basis_type=BasisType.PER_BATCH,
        required_qty=Decimal(str(required_qty)),
        required_uom=required_uom,
        wastage_pct=Decimal(str(wastage_pct)),
        process_loss_pct=Decimal(str(process_loss_pct)),
        substitute_group=None,
        item_name=item_name,
        item_code=item_code if item_code is not None else item_name.upper(),
        item_type=item_type,
        component_type=component_type,
        item_id=uuid4() if item_id is _AUTO_ITEM_ID else item_id,
        consumption_stage=None,
        allergen_flag=False,
        critical_component=False,
    )


def _bom(name, *, base_qty=Decimal("100"), base_uom="KG", lines=None):
    return SimpleNamespace(
        id=uuid4(),
        bom_code=name.upper(),
        bom_name=name,
        base_qty=Decimal(str(base_qty)),
        base_uom=base_uom,
        lines=lines or [],
    )


@pytest.mark.asyncio
async def test_nested_explosion_scales_and_applies_losses_at_each_level(monkeypatch):
    root_id, child_id = uuid4(), uuid4()
    leaf = _line(item_name="Sugar", required_qty=3, wastage_pct=2)
    child = _bom("Intermediate", base_qty=10, lines=[leaf])
    child.id = child_id
    parent_line = _line(
        item_name="Premix", required_qty=25, child_bom_id=child_id,
        wastage_pct=4,
    )
    root = _bom("Finished", lines=[parent_line])
    root.id = root_id
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result({root_id: root, child_id: child}.get(bom_id)),
    )

    result = await explosion.explode_bom(None, root_id, Decimal("100"))

    assert result.total_levels == 2
    assert result.nodes[0].children[0].item_name == "Sugar"
    assert result.flat_requirements[0]["total_qty"] == 7.8
    assert result.flat_requirements[0]["total_adjusted_qty"] == 7.956


@pytest.mark.asyncio
async def test_repeated_intermediate_bom_branches_are_both_aggregated(monkeypatch):
    child_id = uuid4()
    child = _bom("Intermediate", base_qty=10, lines=[_line(item_name="Sugar", required_qty=3)])
    child.id = child_id
    root = _bom("Finished", lines=[
        _line(item_name="Premix A", required_qty=10, child_bom_id=child_id),
        _line(item_name="Premix B", required_qty=10, child_bom_id=child_id),
    ])
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result({root.id: root, child_id: child}.get(bom_id)),
    )

    result = await explosion.explode_bom(None, root.id, Decimal("100"))

    assert result.flat_requirements[0]["total_qty"] == 6.0
    assert len(result.nodes[0].children) == 1
    assert len(result.nodes[1].children) == 1


@pytest.mark.asyncio
async def test_flat_requirements_keep_same_uuid_in_distinct_item_namespaces_separate(monkeypatch):
    shared_id = uuid4()
    root = _bom("Finished", lines=[
        _line(item_name="Material", required_qty=2, item_id=shared_id, item_code="MAT-1"),
        _line(item_name="Product", required_qty=3, item_id=shared_id, item_code="FG-1", item_type=ItemLinkType.PRODUCT),
        _line(item_name="Packaging", required_qty=4, item_id=shared_id, item_code="MAT-1", component_type=ComponentType.PACKAGING),
    ])
    monkeypatch.setattr(explosion, "_load_bom_with_lines", lambda _db, _bom_id: _async_result(root))

    result = await explosion.explode_bom(None, root.id)

    assert len(result.flat_requirements) == 3
    assert {row["item_type"] for row in result.flat_requirements} == {"MATERIAL", "PRODUCT"}
    assert {row["component_type"] for row in result.flat_requirements} == {"RAW", "PACKAGING"}
    assert {row["total_qty"] for row in result.flat_requirements} == {2.0, 3.0, 4.0}


@pytest.mark.asyncio
async def test_flat_requirements_use_item_code_when_master_id_is_missing(monkeypatch):
    root = _bom("Finished", lines=[
        _line(item_name="Cocoa", required_qty=2, item_id=None, item_code="MAT-01"),
        _line(item_name="Cocoa", required_qty=3, item_id=None, item_code="MAT-02"),
    ])
    monkeypatch.setattr(explosion, "_load_bom_with_lines", lambda _db, _bom_id: _async_result(root))

    result = await explosion.explode_bom(None, root.id)

    assert len(result.flat_requirements) == 2
    assert {row["item_code"] for row in result.flat_requirements} == {"MAT-01", "MAT-02"}


@pytest.mark.asyncio
async def test_leaf_without_any_item_identity_fails_closed(monkeypatch):
    root = _bom("Finished", lines=[
        _line(item_name="", required_qty=2, item_id=None, item_code=""),
    ])
    monkeypatch.setattr(explosion, "_load_bom_with_lines", lambda _db, _bom_id: _async_result(root))

    with pytest.raises(explosion.BOMExplosionError, match="has no item ID, code, or name"):
        await explosion.explode_bom(None, root.id)


@pytest.mark.asyncio
async def test_missing_child_bom_fails_closed(monkeypatch):
    missing_id = uuid4()
    root = _bom("Finished", lines=[_line(item_name="Premix", required_qty=10, child_bom_id=missing_id)])
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result(root if bom_id == root.id else None),
    )

    with pytest.raises(explosion.BOMExplosionError, match="missing or unavailable"):
        await explosion.explode_bom(None, root.id, Decimal("100"))


@pytest.mark.asyncio
async def test_child_uom_mismatch_fails_closed(monkeypatch):
    child_id = uuid4()
    child = _bom("Intermediate", base_qty=10, base_uom="L")
    child.id = child_id
    root = _bom("Finished", lines=[
        _line(item_name="Premix", required_qty=10, required_uom="KG", child_bom_id=child_id)
    ])
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result({root.id: root, child_id: child}.get(bom_id)),
    )

    with pytest.raises(explosion.BOMExplosionError, match="does not match line UOM"):
        await explosion.explode_bom(None, root.id, Decimal("100"))


@pytest.mark.asyncio
async def test_zero_base_quantity_on_nested_bom_fails_closed(monkeypatch):
    child_id = uuid4()
    child = _bom("Intermediate", base_qty=0, lines=[_line(item_name="Sugar", required_qty=3)])
    child.id = child_id
    root = _bom("Finished", lines=[
        _line(item_name="Premix", required_qty=10, child_bom_id=child_id)
    ])
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result({root.id: root, child_id: child}.get(bom_id)),
    )

    with pytest.raises(explosion.BOMExplosionError, match="positive finite base quantity"):
        await explosion.explode_bom(None, root.id, Decimal("100"))


@pytest.mark.asyncio
async def test_nested_cycle_fails_with_path(monkeypatch):
    root_id, child_id = uuid4(), uuid4()
    root = _bom("Finished")
    child = _bom("Intermediate")
    root.id = root_id
    child.id = child_id
    root.lines = [_line(item_name="Premix", required_qty=10, child_bom_id=child_id)]
    child.lines = [_line(item_name="Finished", required_qty=10, child_bom_id=root_id)]
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result({root_id: root, child_id: child}.get(bom_id)),
    )

    with pytest.raises(explosion.BOMExplosionError, match="BOM cycle detected"):
        await explosion.explode_bom(None, root_id, Decimal("100"))


@pytest.mark.asyncio
async def test_nesting_beyond_limit_fails_closed(monkeypatch):
    boms = [_bom(f"Level {index}") for index in range(explosion._MAX_DEPTH + 1)]
    for parent, child in zip(boms, boms[1:]):
        parent.lines = [_line(item_name=child.bom_name, required_qty=1, child_bom_id=child.id)]
    bom_by_id = {bom.id: bom for bom in boms}
    monkeypatch.setattr(
        explosion,
        "_load_bom_with_lines",
        lambda _db, bom_id: _async_result(bom_by_id.get(bom_id)),
    )

    with pytest.raises(explosion.BOMExplosionError, match="exceeds maximum depth"):
        await explosion.explode_bom(None, boms[0].id, Decimal("100"))


@pytest.mark.asyncio
async def test_explosion_route_returns_422_for_invalid_nested_structure(monkeypatch):
    async def fail_explosion(*_args, **_kwargs):
        raise explosion.BOMExplosionError("BOM cycle detected")

    monkeypatch.setattr(bom_routes.explode_svc, "explode_bom", fail_explosion)

    with pytest.raises(HTTPException) as exc:
        await bom_routes.explode_bom(uuid4(), Decimal("100"), None, None)

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_explosion_route_preserves_not_found_status(monkeypatch):
    async def missing_bom(*_args, **_kwargs):
        raise ValueError("BOM not found")

    monkeypatch.setattr(bom_routes.explode_svc, "explode_bom", missing_bom)

    with pytest.raises(HTTPException) as exc:
        await bom_routes.explode_bom(uuid4(), Decimal("100"), None, None)

    assert exc.value.status_code == 404


def _async_result(value):
    async def resolve():
        return value

    return resolve()
