from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.quality import SupplierFoodSafetyStatus
from app.services.procurement_service import build_supplier_food_safety_scorecard


def _approval(approval_type, status, expiry_date, audit_score=None):
    return SimpleNamespace(
        approval_type=approval_type,
        status=status,
        expiry_date=expiry_date,
        audit_score=Decimal(str(audit_score)) if audit_score is not None else None,
    )


def test_food_safety_scorecard_keeps_latest_row_per_type_and_does_not_infer_approval():
    rows = build_supplier_food_safety_scorecard(
        [
            _approval("BRC", SupplierFoodSafetyStatus.PENDING, None),
            _approval("BRC", SupplierFoodSafetyStatus.APPROVED, date(2027, 1, 1), 90),
            _approval("HALAL", SupplierFoodSafetyStatus.APPROVED, date(2026, 10, 31), 85),
            _approval("ISO22000", SupplierFoodSafetyStatus.CONDITIONAL, None, 72),
        ],
        today=date(2026, 11, 1),
    )

    assert rows == [
        {
            "approval_type": "BRC",
            "status": "PENDING",
            "audit_score": None,
            "expiry_date": None,
            "is_current": False,
            "is_expired": False,
        },
        {
            "approval_type": "HALAL",
            "status": "APPROVED",
            "audit_score": Decimal("85"),
            "expiry_date": date(2026, 10, 31),
            "is_current": False,
            "is_expired": True,
        },
        {
            "approval_type": "ISO22000",
            "status": "CONDITIONAL",
            "audit_score": Decimal("72"),
            "expiry_date": None,
            "is_current": None,
            "is_expired": False,
        },
    ]


def test_food_safety_scorecard_empty_source_remains_empty():
    assert build_supplier_food_safety_scorecard([], today=date(2026, 11, 1)) == []
