from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.models.procurement import GRNStatus, POStatus
from app.services.procurement_service import (
    average_supplier_evaluation_score,
    calculate_supplier_otif,
)


def _receipt(status, received_date, line_id, quantity, unit="KG"):
    return SimpleNamespace(
        status=status,
        received_date=received_date,
        lines=[SimpleNamespace(
            po_line_id=line_id,
            received_quantity=Decimal(quantity),
            unit=unit,
            material_id=None,
            product_id=None,
        )],
    )


def _po(status, expected_date, ordered_quantity, receipts, unit="KG"):
    line_id = uuid4()
    return SimpleNamespace(
        status=status,
        expected_delivery_date=expected_date,
        lines=[SimpleNamespace(
            id=line_id,
            ordered_quantity=Decimal(ordered_quantity),
            unit=unit,
            material_id=None,
            product_id=None,
        )],
        goods_receipts=[
            _receipt(receipt[0], receipt[1], line_id, receipt[2], receipt[3] if len(receipt) > 3 else unit)
            for receipt in receipts
        ],
    )


def test_otif_uses_only_due_sent_orders_and_posted_receipts_by_due_date():
    expected = date(2026, 10, 31)
    start = date(2025, 11, 1)
    orders = [
        _po(POStatus.RECEIVED, expected, "10", [
            (GRNStatus.POSTED, date(2026, 10, 30), "10"),
        ]),
        _po(POStatus.PARTIALLY_RECEIVED, expected, "10", [
            (GRNStatus.POSTED, date(2026, 10, 31), "6"),
            (GRNStatus.POSTED, date(2026, 11, 1), "4"),
        ]),
        _po(POStatus.ORDERED, expected, "5", [
            (GRNStatus.DRAFT, date(2026, 10, 30), "5"),
        ]),
        _po(POStatus.CANCELLED, expected, "5", [
            (GRNStatus.POSTED, date(2026, 10, 30), "5"),
        ]),
        _po(POStatus.RECEIVED, date(2025, 10, 31), "5", [
            (GRNStatus.POSTED, date(2025, 10, 30), "5"),
        ]),
    ]

    count, met, rate = calculate_supplier_otif(orders, period_start=start, today=date(2026, 10, 31))

    assert (count, met, rate) == (3, 1, Decimal("33.33"))


def test_otif_has_no_rate_without_eligible_orders_and_excludes_empty_orders():
    empty_order = SimpleNamespace(
        status=POStatus.RECEIVED,
        expected_delivery_date=date(2026, 10, 31),
        lines=[],
        goods_receipts=[],
    )

    assert calculate_supplier_otif(
        [empty_order], period_start=date(2025, 11, 1), today=date(2026, 10, 31)
    ) == (0, 0, None)


def test_otif_ignores_receipt_lines_linked_to_another_order_or_unit():
    expected = date(2026, 10, 31)
    order = _po(POStatus.RECEIVED, expected, "5", [], unit="KG")
    order.goods_receipts = [
        _receipt(GRNStatus.POSTED, expected, uuid4(), "5", unit="KG"),
        _receipt(GRNStatus.POSTED, expected, order.lines[0].id, "5", unit="PCS"),
        _receipt(GRNStatus.POSTED, expected, order.lines[0].id, "5", unit="KG"),
    ]
    order.goods_receipts[-1].lines[0].product_id = uuid4()

    count, met, rate = calculate_supplier_otif(
        [order], period_start=date(2025, 11, 1), today=expected
    )

    assert (count, met, rate) == (1, 0, Decimal("0.00"))


def test_evaluation_dimension_average_preserves_empty_as_missing():
    evaluations = [
        SimpleNamespace(price_competitiveness_score=Decimal("80")),
        SimpleNamespace(price_competitiveness_score=Decimal("91")),
    ]

    assert average_supplier_evaluation_score(evaluations, "price_competitiveness_score") == Decimal("85.50")
    assert average_supplier_evaluation_score([], "responsiveness_score") is None
