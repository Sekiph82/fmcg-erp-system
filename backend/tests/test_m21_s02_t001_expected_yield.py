"""Contract checks for the expected process-yield percentage on BOMs."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from app.models.bom import AdvancedBOM
from app.schemas.bom import BOMCreate, BOMSummary, BOMUpdate


def test_bom_model_and_api_contract_expose_optional_expected_yield():
    columns = AdvancedBOM.__table__.columns
    assert "expected_process_yield_pct" in columns
    assert columns["expected_process_yield_pct"].nullable
    assert any(
        isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_advanced_bom_expected_process_yield_nonnegative"
        for constraint in AdvancedBOM.__table__.constraints
    )
    assert "expected_process_yield_pct" in BOMCreate.model_fields
    assert "expected_process_yield_pct" in BOMUpdate.model_fields
    assert "expected_process_yield_pct" in BOMSummary.model_fields


def test_bom_yield_is_optional_and_preserves_configured_percentage():
    assert BOMCreate(bom_name="Synthetic BOM").expected_process_yield_pct is None
    assert BOMCreate(
        bom_name="Synthetic BOM",
        expected_process_yield_pct=Decimal("91.2500"),
    ).expected_process_yield_pct == Decimal("91.2500")
    assert BOMUpdate(expected_process_yield_pct=None).expected_process_yield_pct is None


@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")])
def test_bom_expected_yield_rejects_negative_and_nonfinite_values(value):
    with pytest.raises(ValidationError):
        BOMCreate(bom_name="Synthetic BOM", expected_process_yield_pct=value)
    with pytest.raises(ValidationError):
        BOMUpdate(expected_process_yield_pct=value)
