from datetime import date, timedelta

import pytest

from app.models.machine_operator import CertStatus
from app.services.machine_operator_service import (
    CERTIFICATION_EXPIRING_SOON_DAYS,
    _compute_cert_status,
)


@pytest.mark.parametrize(
    ("expiry_offset_days", "required", "expected"),
    [
        (None, True, CertStatus.PENDING),
        (-1, True, CertStatus.EXPIRED),
        (0, True, CertStatus.EXPIRING_SOON),
        (CERTIFICATION_EXPIRING_SOON_DAYS, True, CertStatus.EXPIRING_SOON),
        (CERTIFICATION_EXPIRING_SOON_DAYS + 1, True, CertStatus.VALID),
        (-1, False, CertStatus.VALID),
    ],
)
def test_certification_expiry_status_uses_current_date_window(
    expiry_offset_days: int | None,
    required: bool,
    expected: CertStatus,
) -> None:
    expiry = None if expiry_offset_days is None else date.today() + timedelta(days=expiry_offset_days)

    assert _compute_cert_status(expiry, required) is expected
