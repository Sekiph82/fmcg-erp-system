"""Contract checks for filling, packaging, and spillage loss configuration."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from app.models.bom import BOMYieldConfig, LossCategory
from app.schemas.bom import YieldConfigCreate


def test_loss_model_has_separate_filling_packaging_and_spillage_categories():
    assert {"FILLING", "PACKAGING_REJECT", "SPILLAGE"} <= {item.value for item in LossCategory}
    columns = BOMYieldConfig.__table__.columns
    assert {"loss_category", "basis", "standard_pct", "max_allowable_pct"} <= set(columns.keys())
    assert sum(
        isinstance(constraint, CheckConstraint)
        and constraint.name in {
            "ck_bom_yield_config_standard_pct_nonnegative",
            "ck_bom_yield_config_max_allowable_pct_nonnegative",
        }
        for constraint in BOMYieldConfig.__table__.constraints
    ) == 2


@pytest.mark.parametrize("category", [LossCategory.FILLING, LossCategory.PACKAGING_REJECT, LossCategory.SPILLAGE])
def test_loss_config_requires_explicit_nonnegative_rate_without_fabricated_defaults(category):
    with pytest.raises(ValidationError):
        YieldConfigCreate(loss_category=category)

    config = YieldConfigCreate(loss_category=category, standard_pct=Decimal("0"))
    assert config.standard_pct == Decimal("0")
    assert config.max_allowable_pct is None


@pytest.mark.parametrize("value", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")])
def test_loss_config_rejects_negative_and_nonfinite_rates(value):
    with pytest.raises(ValidationError):
        YieldConfigCreate(loss_category=LossCategory.SPILLAGE, standard_pct=value)
    with pytest.raises(ValidationError):
        YieldConfigCreate(
            loss_category=LossCategory.SPILLAGE,
            standard_pct=Decimal("1"),
            max_allowable_pct=value,
        )
