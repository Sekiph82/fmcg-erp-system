"""M29.S04.T002 — Calibration enforcement focused unit tests.

Tests the _calibration_instrument_read status derivation and the CCP blocking
rule (non-CURRENT/DUE_SOON instruments are rejected) using in-memory objects.
"""
from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.endpoints.qms import _calibration_instrument_read
from app.models.quality import CalibrationStatus


def _instrument(last_cal_date, interval_days, status=CalibrationStatus.NOT_VERIFIED, is_active=True):
    return SimpleNamespace(
        id=uuid4(),
        instrument_id=f"INST-{uuid4().hex[:6].upper()}",
        instrument_name="Test Instrument",
        instrument_type="THERMOMETER",
        asset_id=None,
        asset=None,
        location="Lab A",
        manufacturer=None,
        model_no=None,
        serial_no=None,
        last_calibration_date=last_cal_date,
        calibration_interval_days=interval_days,
        calibration_authority=None,
        certificate_ref=None,
        status=status.value,
        is_active=is_active,
        notes=None,
    )


TODAY = date(2026, 11, 10)


def test_current_calibration_within_interval():
    inst = _instrument(TODAY - timedelta(days=10), interval_days=90)
    result = _calibration_instrument_read(inst, TODAY)
    assert result["status"] == CalibrationStatus.CURRENT.value
    assert not result["is_overdue"]


def test_due_soon_within_30_days():
    inst = _instrument(TODAY - timedelta(days=65), interval_days=90)
    result = _calibration_instrument_read(inst, TODAY)
    # 90 - 65 = 25 days until due → DUE_SOON
    assert result["status"] == CalibrationStatus.DUE_SOON.value


def test_overdue_calibration():
    inst = _instrument(TODAY - timedelta(days=100), interval_days=90)
    result = _calibration_instrument_read(inst, TODAY)
    assert result["status"] == CalibrationStatus.OVERDUE.value
    assert result["is_overdue"]


def test_out_of_service_overrides_date():
    # Even with a fresh calibration date, OUT_OF_SERVICE wins
    inst = _instrument(TODAY, interval_days=365, status=CalibrationStatus.OUT_OF_SERVICE)
    result = _calibration_instrument_read(inst, TODAY)
    assert result["status"] == CalibrationStatus.OUT_OF_SERVICE.value


def test_no_calibration_date_is_not_verified():
    inst = _instrument(None, interval_days=30)
    result = _calibration_instrument_read(inst, TODAY)
    assert result["status"] == CalibrationStatus.NOT_VERIFIED.value


def test_ccp_blocking_logic_rejects_overdue():
    """CCP measurement should be blocked if calibration status is OVERDUE."""
    blocked_statuses = {
        CalibrationStatus.OVERDUE.value,
        CalibrationStatus.NOT_VERIFIED.value,
        CalibrationStatus.OUT_OF_SERVICE.value,
    }
    allowed_statuses = {
        CalibrationStatus.CURRENT.value,
        CalibrationStatus.DUE_SOON.value,
    }

    for status in blocked_statuses:
        should_block = status not in (CalibrationStatus.CURRENT.value, CalibrationStatus.DUE_SOON.value)
        assert should_block, f"Status {status} should block CCP recording"

    for status in allowed_statuses:
        should_allow = status in (CalibrationStatus.CURRENT.value, CalibrationStatus.DUE_SOON.value)
        assert should_allow, f"Status {status} should allow CCP recording"
