"""Pure validation coverage for the shop-floor operation completion boundary."""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.shop_floor_service import finish_work_order


@pytest.mark.parametrize(
    ("qty_good", "qty_scrap", "qty_rework", "run_time_actual", "message"),
    [
        (Decimal("-0.1"), Decimal("0"), Decimal("0"), None, "Completion quantities"),
        (Decimal("0"), Decimal("NaN"), Decimal("0"), None, "Completion quantities"),
        (Decimal("0"), Decimal("0"), Decimal("Infinity"), None, "Completion quantities"),
        (Decimal("0"), Decimal("0"), Decimal("0"), Decimal("-0.1"), "Actual runtime"),
        (Decimal("0"), Decimal("0"), Decimal("0"), Decimal("NaN"), "Actual runtime"),
    ],
)
@pytest.mark.asyncio
async def test_finish_rejects_invalid_quantities_before_database_mutation(
    qty_good, qty_scrap, qty_rework, run_time_actual, message
):
    with pytest.raises(ValueError, match=message):
        await finish_work_order(
            db=None,
            wo_id=uuid4(),
            qty_good=qty_good,
            qty_scrap=qty_scrap,
            qty_rework=qty_rework,
            run_time_actual=run_time_actual,
            session_id=None,
            operator_name="Synthetic operator",
            remarks=None,
        )
