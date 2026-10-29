"""Validate the canonical charge catalogue used by landed-cost line entry."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.landed_cost import LandedCostType
from app.schemas.landed_cost import LandedCostLineCreate, LandedCostLineOut


@pytest.mark.parametrize("cost_type", list(LandedCostType))
def test_landed_cost_line_accepts_every_supported_charge_type(cost_type: LandedCostType):
    line = LandedCostLineCreate(cost_type=cost_type.value)

    assert line.cost_type is cost_type
    assert line.model_dump(mode="json")["cost_type"] == cost_type.value


def test_landed_cost_line_rejects_unknown_charge_type():
    with pytest.raises(ValidationError):
        LandedCostLineCreate(cost_type="UNLISTED_CHARGE")


def test_landed_cost_line_output_keeps_legacy_custom_charge_labels_readable():
    stored_line = SimpleNamespace(
        cost_type="LEGACY_CUSTOM_CHARGE",
        description="Historical custom charge",
        vendor_name=None,
        amount_fc=Decimal("10.00"),
        currency_code="USD",
        exchange_rate=Decimal("1"),
        allocation_method=None,
        is_included_in_valuation=True,
        account_code=None,
        remarks=None,
        id=uuid4(),
        header_id=uuid4(),
        amount_base=Decimal("10.00"),
    )

    response = LandedCostLineOut.model_validate(stored_line)

    assert response.cost_type == "LEGACY_CUSTOM_CHARGE"
