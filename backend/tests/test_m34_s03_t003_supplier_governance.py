from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.models.master import SupplierQualificationStatus
from app.services.procurement_service import supplier_procurement_block_reason


def _supplier(*, active=True, qualification=None, approved_from=None, approved_until=None):
    return SimpleNamespace(
        is_active=active,
        qualification_status=qualification,
        approved_from=approved_from,
        approved_until=approved_until,
    )


def test_legacy_supplier_without_recorded_qualification_remains_eligible():
    assert supplier_procurement_block_reason(_supplier(qualification=None)) is None


@pytest.mark.parametrize(
    "status",
    [
        SupplierQualificationStatus.PENDING,
        SupplierQualificationStatus.CONDITIONAL,
        SupplierQualificationStatus.SUSPENDED,
        SupplierQualificationStatus.REJECTED,
    ],
)
def test_explicit_nonapproved_qualification_blocks_new_commitments(status):
    reason = supplier_procurement_block_reason(_supplier(qualification=status))
    assert reason is not None
    assert status.value in reason


def test_approved_supplier_must_cover_the_entire_commitment_window():
    today = date.today()
    supplier = _supplier(
        qualification=SupplierQualificationStatus.APPROVED,
        approved_from=today,
        approved_until=today + timedelta(days=30),
    )
    assert supplier_procurement_block_reason(
        supplier,
        start_date=today,
        end_date=today + timedelta(days=30),
    ) is None
    assert "expires" in supplier_procurement_block_reason(
        supplier,
        start_date=today,
        end_date=today + timedelta(days=31),
    )


def test_inactive_supplier_is_blocked_even_if_qualification_is_approved():
    supplier = _supplier(active=False, qualification=SupplierQualificationStatus.APPROVED)
    assert "Inactive" in supplier_procurement_block_reason(supplier)
