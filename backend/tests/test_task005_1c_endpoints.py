"""
TASK-005.1C: eTIMS submit/retry/cancel/status-poll endpoint logic.

Tests cover the helper function and status-transition rules.
Full DB integration tests are skipped — ETimsSubmission requires a live async
session with PostgreSQL enum types; mocking the full async session stack would
not add confidence beyond the connector tests in test_task005_1b_connector.py.
The helper (_apply_etims_response_to_submission) is the core new logic and is
fully tested here using bare SQLAlchemy model instances (no DB required).

Tests:
1.  Helper applies ACCEPTED response — all key fields set correctly.
2.  Helper applies REJECTED response — error fields set, accepted_at preserved as None.
3.  Helper clears error fields on success.
4.  Helper sets error fields on failure.
5.  Helper increments both retry_count and attempt_count by 1.
6.  Helper skips increment when increment_attempt=False.
7.  Helper sets transmitted_at when update_transmitted=True.
8.  Helper skips transmitted_at when update_transmitted=False (default).
9.  Retry blocked for ACCEPTED, CANCELLED, PENDING, SUBMITTED statuses.
10. Retry allowed for REJECTED, FAILED, ERROR, RETRY_PENDING.
11. ETimsCancelRequest schema — defaults correct.
12. ETimsCancelRequest schema — allow_cancel_accepted=True accepted.
13. Helper preserves existing control_unit_invoice_no when result has None.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.api.v1.endpoints.tax_regulatory import (
    _apply_etims_response_to_submission,
    _RETRY_ALLOWED_STATUSES,
)
from app.models.tax_regulatory import ETimsSubmission, ETimsStatus
from app.schemas.tax_regulatory import ETimsCancelRequest
from app.services.etims_connector import ETimsConnectorResponse


# ── Factories ──────────────────────────────────────────────────────────────────

def _make_sub(status: ETimsStatus) -> ETimsSubmission:
    sub = ETimsSubmission()
    sub.id = uuid.uuid4()
    sub.invoice_id = uuid.uuid4()
    sub.status = status
    sub.retry_count = 0
    sub.attempt_count = 0
    sub.provider_reference = "SIM-REF-001"
    sub.control_unit_invoice_no = None
    sub.signed_invoice_hash = None
    sub.invoice_qr_data = None
    sub.accepted_at = None
    sub.error_code = None
    sub.error_message = None
    sub.transmitted_at = None
    sub.request_payload = {}
    sub.response_payload = {}
    return sub


def _accepted_result() -> ETimsConnectorResponse:
    return ETimsConnectorResponse(
        success=True,
        status="ACCEPTED",
        provider_name="simulation",
        environment="simulation",
        provider_reference="SIM-ETIMS-INV-001-ABCD1234",
        control_unit_invoice_no="KRA-INV-001-20260602",
        signed_invoice_hash="deadbeef",
        invoice_qr_data="INV=INV-001|HASH=dead",
        kra_response_code="00",
        kra_response_message="Accepted",
        accepted_at=datetime.now(timezone.utc),
        raw_response={"simulationMode": True, "accepted": True},
    )


def _rejected_result() -> ETimsConnectorResponse:
    return ETimsConnectorResponse(
        success=False,
        status="REJECTED",
        provider_name="simulation",
        environment="simulation",
        provider_reference="SIM-ETIMS-INV-001-ABCD1234",
        kra_response_code="REJECT-001",
        kra_response_message="Simulated rejection",
        error_code="REJECT-001",
        error_message="Invoice failed validation",
        raw_response={"simulationMode": True, "reject": True},
    )


_NOW = datetime.now(timezone.utc)
_PAYLOAD = {"invoiceNo": "INV-001", "totalAmt": 1000.0}


# ── 1. Helper — ACCEPTED response ─────────────────────────────────────────────

def test_helper_accepted_sets_all_fields():
    sub = _make_sub(ETimsStatus.PENDING)
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.status == ETimsStatus.ACCEPTED
    assert sub.kra_response_code == "00"
    assert sub.control_unit_invoice_no == "KRA-INV-001-20260602"
    assert sub.signed_invoice_hash == "deadbeef"
    assert sub.invoice_qr_data == "INV=INV-001|HASH=dead"
    assert sub.accepted_at is not None
    assert sub.provider_name == "simulation"
    assert sub.provider_reference == "SIM-ETIMS-INV-001-ABCD1234"
    assert sub.environment == "simulation"
    assert sub.last_attempt_at == _NOW
    assert sub.request_payload == _PAYLOAD
    assert sub.response_payload == {"simulationMode": True, "accepted": True}


# ── 2. Helper — REJECTED response ─────────────────────────────────────────────

def test_helper_rejected_sets_error_fields():
    sub = _make_sub(ETimsStatus.PENDING)
    result = _rejected_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.status == ETimsStatus.REJECTED
    assert sub.error_code == "REJECT-001"
    assert sub.error_message == "Invoice failed validation"
    assert sub.accepted_at is None


# ── 3. Helper — clears errors on success ──────────────────────────────────────

def test_helper_clears_error_on_success():
    sub = _make_sub(ETimsStatus.REJECTED)
    sub.error_code = "OLD-ERR"
    sub.error_message = "Previous failure"
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.error_code is None
    assert sub.error_message is None


# ── 4. Helper — sets errors on failure ────────────────────────────────────────

def test_helper_sets_error_on_failure():
    sub = _make_sub(ETimsStatus.PENDING)
    result = _rejected_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.error_code == "REJECT-001"
    assert sub.error_message == "Invoice failed validation"


# ── 5. Helper — increments attempt counts ─────────────────────────────────────

def test_helper_increments_both_counts():
    sub = _make_sub(ETimsStatus.PENDING)
    sub.retry_count = 2
    sub.attempt_count = 3
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW, increment_attempt=True)

    assert sub.retry_count == 3
    assert sub.attempt_count == 4


# ── 6. Helper — no increment when disabled ────────────────────────────────────

def test_helper_no_increment_when_disabled():
    sub = _make_sub(ETimsStatus.PENDING)
    sub.retry_count = 2
    sub.attempt_count = 3
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW, increment_attempt=False)

    assert sub.retry_count == 2
    assert sub.attempt_count == 3


# ── 7. Helper — sets transmitted_at when flag True ────────────────────────────

def test_helper_sets_transmitted_at():
    sub = _make_sub(ETimsStatus.PENDING)
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW, update_transmitted=True)

    assert sub.transmitted_at == _NOW


# ── 8. Helper — skips transmitted_at by default ───────────────────────────────

def test_helper_skips_transmitted_at_by_default():
    sub = _make_sub(ETimsStatus.PENDING)
    result = _accepted_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.transmitted_at is None


# ── 9. Retry blocked for non-retryable statuses ───────────────────────────────

@pytest.mark.parametrize("status", [
    ETimsStatus.ACCEPTED,
    ETimsStatus.CANCELLED,
    ETimsStatus.PENDING,
    ETimsStatus.SUBMITTED,
    ETimsStatus.DRAFT,
    ETimsStatus.READY,
])
def test_retry_blocked_for_non_retryable(status):
    assert status not in _RETRY_ALLOWED_STATUSES


# ── 10. Retry allowed for retryable statuses ──────────────────────────────────

@pytest.mark.parametrize("status", [
    ETimsStatus.REJECTED,
    ETimsStatus.FAILED,
    ETimsStatus.ERROR,
    ETimsStatus.RETRY_PENDING,
])
def test_retry_allowed_for_retryable(status):
    assert status in _RETRY_ALLOWED_STATUSES


# ── 11. ETimsCancelRequest defaults ───────────────────────────────────────────

def test_cancel_request_defaults():
    req = ETimsCancelRequest(reason="Customer request")
    assert req.reason == "Customer request"
    assert req.allow_cancel_accepted is False


# ── 12. ETimsCancelRequest allow_cancel_accepted=True ─────────────────────────

def test_cancel_request_allow_accepted_flag():
    req = ETimsCancelRequest(reason="Error correction", allow_cancel_accepted=True)
    assert req.allow_cancel_accepted is True


# ── 13. Helper preserves existing value when result field is None ──────────────

def test_helper_preserves_existing_control_unit_no_when_result_none():
    sub = _make_sub(ETimsStatus.RETRY_PENDING)
    sub.control_unit_invoice_no = "KRA-EXISTING-001"
    # REJECTED result has no control_unit_invoice_no
    result = _rejected_result()

    _apply_etims_response_to_submission(sub, _PAYLOAD, result, _NOW)

    assert sub.control_unit_invoice_no == "KRA-EXISTING-001"
