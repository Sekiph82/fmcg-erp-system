from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.landed_cost import LCAllocationMethod
from app.schemas.landed_cost import LandedCostHeaderCreate, LandedCostLineCreate
from app.models.landed_cost import LandedCostType
from app.schemas.procurement import GRNLineCreate
from app.services.landed_cost_service import _allocate_amounts, _compute_basis


def _grn_line(
    line_id: str,
    *,
    quantity: str = "1",
    weight: str | None = None,
    volume: str | None = None,
    unit_price: str | None = None,
    exchange_rate: str = "1",
    item_kind: str = "material",
):
    item = SimpleNamespace(
        weight_kg=Decimal(weight) if weight is not None else None,
        name=f"Synthetic {item_kind} {line_id}",
    )
    po = SimpleNamespace(exchange_rate=Decimal(exchange_rate))
    po_line = SimpleNamespace(
        unit_price=Decimal(unit_price) if unit_price is not None else None,
        po=po,
    )
    return SimpleNamespace(
        id=line_id,
        accepted_quantity=Decimal(quantity),
        accepted_volume_m3=Decimal(volume) if volume is not None else None,
        material=item if item_kind == "material" else None,
        product=item if item_kind == "product" else None,
        po_line=po_line if unit_price is not None else None,
        lot_number=None,
    )


@pytest.mark.parametrize(
    ("method", "line", "expected"),
    [
        (LCAllocationMethod.BY_QUANTITY, _grn_line("qty", quantity="4"), Decimal("4")),
        (
            LCAllocationMethod.BY_WEIGHT,
            _grn_line("weight", quantity="3", weight="2.5"),
            Decimal("7.5"),
        ),
        (
            LCAllocationMethod.BY_WEIGHT,
            _grn_line("product-weight", quantity="2", weight="1.25", item_kind="product"),
            Decimal("2.50"),
        ),
        (
            LCAllocationMethod.BY_VOLUME,
            _grn_line("volume", quantity="20", volume="0.75"),
            Decimal("0.75"),
        ),
        (
            LCAllocationMethod.BY_VALUE,
            _grn_line("value", quantity="5", unit_price="2.4", exchange_rate="130"),
            Decimal("1560.0"),
        ),
    ],
)
def test_supported_landed_cost_bases(method, line, expected):
    assert _compute_basis(method, [line]) == {line.id: expected}


@pytest.mark.parametrize(
    ("method", "line", "message"),
    [
        (
            LCAllocationMethod.BY_WEIGHT,
            _grn_line("missing-weight"),
            "positive item weight",
        ),
        (
            LCAllocationMethod.BY_VOLUME,
            _grn_line("missing-volume"),
            "accepted volume in m³",
        ),
        (
            LCAllocationMethod.BY_VALUE,
            _grn_line("missing-value"),
            "positive PO-backed base purchase value",
        ),
    ],
)
def test_basis_method_fails_closed_on_missing_inputs(method, line, message):
    with pytest.raises(ValueError, match=message):
        _compute_basis(method, [line])


@pytest.mark.parametrize("method", ["BY_QUANTITY", "BY_WEIGHT", "BY_VOLUME", "BY_VALUE", "EQUAL_SPLIT"])
def test_document_inputs_accept_supported_allocation_methods(method):
    assert LandedCostHeaderCreate(allocation_method=method).allocation_method == method
    assert LandedCostLineCreate(
        cost_type=LandedCostType.OTHER,
        allocation_method=method,
    ).allocation_method == method


def test_unimplemented_manual_allocation_is_not_accepted_for_new_documents():
    with pytest.raises(ValidationError):
        LandedCostHeaderCreate(allocation_method="CUSTOM")
    with pytest.raises(ValidationError):
        LandedCostLineCreate(
            cost_type=LandedCostType.OTHER,
            allocation_method="CUSTOM",
        )


def test_volume_basis_requires_strictly_positive_receipt_volume():
    with pytest.raises(ValidationError):
        GRNLineCreate(
            received_quantity=Decimal("2"),
            accepted_quantity=Decimal("2"),
            accepted_volume_m3=Decimal("0"),
        )

    accepted = GRNLineCreate(
        received_quantity=Decimal("2"),
        accepted_quantity=Decimal("2"),
        accepted_volume_m3=Decimal("0.125"),
    )
    assert accepted.accepted_volume_m3 == Decimal("0.125")

    with pytest.raises(ValidationError):
        GRNLineCreate(
            received_quantity=Decimal("2"),
            accepted_quantity=Decimal("0"),
            accepted_volume_m3=Decimal("0.125"),
        )


def test_allocations_reconcile_to_source_amount_after_rounding():
    allocations = _allocate_amounts(
        Decimal("10"),
        {"a": Decimal("1"), "b": Decimal("1"), "c": Decimal("1")},
        LCAllocationMethod.BY_VALUE,
    )

    assert sum(allocations.values(), Decimal("0")) == Decimal("10.0000")
    assert sorted(allocations.values()) == [
        Decimal("3.3333"), Decimal("3.3333"), Decimal("3.3334")
    ]


def test_rounding_residual_keeps_tiny_cost_on_one_positive_basis_line():
    allocations = _allocate_amounts(
        Decimal("0.0001"),
        {key: Decimal("1") for key in range(5)},
        LCAllocationMethod.BY_QUANTITY,
    )

    assert sum(allocations.values(), Decimal("0")) == Decimal("0.0001")
    assert sum(value > 0 for value in allocations.values()) == 1


def test_negative_basis_is_rejected_before_allocation():
    with pytest.raises(ValueError, match="negative value"):
        _allocate_amounts(
            Decimal("10"),
            {"valid": Decimal("2"), "invalid": Decimal("-1")},
            LCAllocationMethod.BY_QUANTITY,
        )
