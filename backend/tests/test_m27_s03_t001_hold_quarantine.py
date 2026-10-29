from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.quality import QCDecision, QCStatus
from app.services import qms_service, quality_service


@pytest.fixture(autouse=True)
def _stub_audit_persistence_for_service_contract_tests(monkeypatch):
    async def record(**kwargs):
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(qms_service, "_record_quality_gate_audit_event", record)


@pytest.mark.asyncio
async def test_mandatory_failed_inspection_holds_lot_even_when_request_disables_quarantine(monkeypatch):
    inspection = SimpleNamespace(
        status=QCStatus.IN_PROGRESS, decision=None, decided_by_id=None, decided_at=None,
        decision_notes=None, rework_candidate=False, lot_id=uuid4(), warehouse_id=uuid4(),
        material_id=None, product_id=uuid4(), is_mandatory=True, blocks_progression=True,
        release_required=True, inspection_no="SYN-T001-REJECT",
    )
    events = []

    async def hold(*_args, **kwargs):
        events.append(("hold", kwargs["quarantine"]))
        return 1

    async def sync(_db, current_inspection):
        events.append(("sync", current_inspection.decision))

    monkeypatch.setattr(quality_service, "_quarantine_lot_stock", hold)
    monkeypatch.setattr(qms_service, "update_lot_qc_status_from_inspection", sync)
    db = SimpleNamespace(flush=AsyncMock())

    result = await quality_service.make_decision(
        db, inspection, QCDecision.REJECT, uuid4(), "Synthetic failed mandatory QC", False, False,
    )

    assert result.status == QCStatus.FAILED
    assert result.quarantine_applied is True
    assert events == [("hold", True), ("sync", QCDecision.REJECT)]


@pytest.mark.asyncio
async def test_accepting_an_inspection_does_not_clear_an_existing_lot_hold(monkeypatch):
    inspection = SimpleNamespace(
        id=uuid4(), status=QCStatus.PENDING,
        test_results=[SimpleNamespace(is_passed=True, is_critical=False)],
        lot_id=uuid4(), decision=None, decided_by_id=None, decided_at=None,
        decision_notes=None, rework_candidate=False,
    )
    status = SimpleNamespace(
        last_inspection_id=None, qc_status="FAILED", hold_flag=True,
        quarantine_flag=True, release_status=qms_service.ReleaseStatus.QUARANTINED,
        fefo_eligible=False, shipment_eligible=False,
    )

    class Result:
        def __init__(self, value=None):
            self.value = value

        def scalar_one(self):
            return self.value

    class DB:
        def __init__(self):
            self.results = [Result(), Result(status)]

        async def execute(self, _statement):
            return self.results.pop(0)

        async def flush(self):
            return None

    result = await quality_service.make_decision(
        DB(), inspection, QCDecision.ACCEPT, uuid4(), "Synthetic accepted retest", False, False,
    )

    assert result.status == QCStatus.PASSED
    assert status.last_inspection_id == inspection.id
    assert status.qc_status == "PASSED"
    assert status.hold_flag is True
    assert status.quarantine_flag is True
    assert status.release_status == qms_service.ReleaseStatus.QUARANTINED
    assert status.shipment_eligible is False


@pytest.mark.asyncio
async def test_accepting_first_unheld_lot_inspection_keeps_legacy_release_eligibility(monkeypatch):
    inspection = SimpleNamespace(id=uuid4(), lot_id=uuid4(), decision=QCDecision.ACCEPT)
    status = SimpleNamespace(
        last_inspection_id=None, qc_status="PENDING", hold_flag=False,
        quarantine_flag=False, release_status=qms_service.ReleaseStatus.UNRELEASED,
        fefo_eligible=False, shipment_eligible=False,
    )

    class Result:
        def __init__(self, value=None):
            self.value = value

        def scalar_one(self):
            return self.value

    class DB:
        def __init__(self):
            self.results = [Result(), Result(status)]

        async def execute(self, _statement):
            return self.results.pop(0)

    await qms_service.update_lot_qc_status_from_inspection(DB(), inspection)

    assert status.release_status == qms_service.ReleaseStatus.RELEASED
    assert status.fefo_eligible is True
    assert status.shipment_eligible is True


@pytest.mark.asyncio
async def test_manual_release_cannot_bypass_active_finished_goods_gate(monkeypatch):
    lot = SimpleNamespace(is_quarantine=True)
    status = SimpleNamespace()

    class Result:
        def __init__(self, value=None):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

        def scalar_one(self):
            return self.value

    class DB:
        def __init__(self):
            self.results = [Result(lot), Result(), Result(status)]

        async def execute(self, _statement):
            return self.results.pop(0)

    async def no_op(*_args):
        return None

    async def locked_inspections(*_args):
        return []

    async def active_gate(*_args):
        return [SimpleNamespace(is_mandatory=True)]

    async def should_not_unblock(*_args, **_kwargs):
        raise AssertionError("gate failure must happen before changing physical stock")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", no_op)
    monkeypatch.setattr(qms_service, "_lock_lot_quality_inspections", locked_inspections)
    monkeypatch.setattr(qms_service, "list_finished_goods_quality_gates", active_gate)
    monkeypatch.setattr(qms_service, "_set_lot_stock_blocked", should_not_unblock)

    with pytest.raises(ValueError, match="active release gates"):
        await qms_service.release_lot(DB(), uuid4(), uuid4(), "Synthetic release attempt")


@pytest.mark.asyncio
async def test_active_finished_goods_gate_rejects_untraceable_accepted_inspection(monkeypatch):
    lot_id = uuid4()
    inspection = SimpleNamespace(
        id=uuid4(), lot_id=lot_id,
        qc_type=qms_service.QCType.FINISHED_GOODS, status=QCStatus.PASSED,
        decision=QCDecision.ACCEPT, is_mandatory=True, release_required=True,
        production_order_id=None,
    )

    class Result:
        def __init__(self, value=None):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

        def scalar_one(self):
            return self.value

    class DB:
        def __init__(self):
            self.results = [Result(SimpleNamespace(is_quarantine=True)), Result(), Result(SimpleNamespace())]

        async def execute(self, _statement):
            return self.results.pop(0)

    async def no_op(*_args):
        return None

    async def locked_inspections(*_args):
        return [inspection]

    async def active_gate(*_args):
        return [SimpleNamespace(is_mandatory=True)]

    async def should_not_unblock(*_args, **_kwargs):
        raise AssertionError("untraceable QC must be rejected before physical release")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", no_op)
    monkeypatch.setattr(qms_service, "_lock_lot_quality_inspections", locked_inspections)
    monkeypatch.setattr(qms_service, "list_finished_goods_quality_gates", active_gate)
    monkeypatch.setattr(qms_service, "_set_lot_stock_blocked", should_not_unblock)

    with pytest.raises(ValueError, match="production-order traceability"):
        await qms_service.release_lot(DB(), lot_id, uuid4(), "Synthetic untraceable release attempt")
