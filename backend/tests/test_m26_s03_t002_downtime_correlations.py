from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.machine_operator import DowntimeClass, RuntimeActivity
from app.models.production_advanced import AdvQCStatus, QCInspectionType, QCResultValue, WasteCategory, WasteType
from app.services import machine_operator_service as service


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def scalars(self):
        return self


class _Session:
    def __init__(self, *results):
        self.results = list(results)

    async def execute(self, _statement):
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_downtime_correlations_require_explicit_order_and_time_evidence():
    machine_id, work_order_id, other_work_order_id, production_order_id = uuid4(), uuid4(), uuid4(), uuid4()
    operator_id, reporter_id = uuid4(), uuid4()
    downtime_id, runtime_id, mismatched_runtime_id, labor_id = uuid4(), uuid4(), uuid4(), uuid4()
    inspection_id, qc_result_id, waste_record_id = uuid4(), uuid4(), uuid4()
    start = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
    event = SimpleNamespace(
        id=downtime_id, machine_id=machine_id, work_order_id=work_order_id,
        production_order_id=production_order_id, downtime_class=DowntimeClass.MECHANICAL_BREAKDOWN,
        start_time=start, end_time=start + timedelta(hours=1), duration_minutes=Decimal("60"),
        reported_by_id=reporter_id,
    )
    machine = SimpleNamespace(id=machine_id, machine_code="M-01", machine_name="Mixer 01")
    runtime = SimpleNamespace(
        id=runtime_id, machine_id=machine_id, work_order_id=work_order_id,
        production_order_id=production_order_id, operator_id=operator_id,
        activity_type=RuntimeActivity.DOWNTIME, start_time=start, end_time=start + timedelta(hours=1),
    )
    wrong_order_runtime = SimpleNamespace(
        id=mismatched_runtime_id, machine_id=machine_id, work_order_id=other_work_order_id,
        production_order_id=production_order_id, operator_id=uuid4(),
        activity_type=RuntimeActivity.DOWNTIME, start_time=start, end_time=start + timedelta(hours=1),
    )
    labor = SimpleNamespace(
        id=labor_id, work_order_id=work_order_id, operator_id=operator_id,
        start_time=start + timedelta(minutes=5), end_time=start + timedelta(minutes=45),
        duration_minutes=Decimal("40"), approved_flag=False,
    )
    inspection = SimpleNamespace(
        id=inspection_id, qc_id="QC-001", status=AdvQCStatus.FAILED,
        inspection_type=QCInspectionType.INLINE, inspected_at=start + timedelta(minutes=30),
        work_order_id=work_order_id, production_order_id=production_order_id,
    )
    qc_result = SimpleNamespace(
        id=qc_result_id, test_type="pH", result=QCResultValue.FAIL,
        actual_value=Decimal("4.20"), unit="pH",
    )
    waste = SimpleNamespace(
        id=waste_record_id, waste_id="WASTE-001", work_order_id=work_order_id,
        production_order_id=production_order_id, waste_type=WasteType.MATERIAL,
        waste_category=WasteCategory.ABNORMAL, expected_qty=Decimal("10"),
        actual_qty=Decimal("7"), loss_qty=Decimal("3"), loss_pct=Decimal("30"),
        uom="KG", is_anomaly=True, created_at=start,
    )

    db = _Session(
        _Result([(event, machine)]),
        _Result([runtime, wrong_order_runtime]),
        _Result([labor]),
        _Result([(inspection, qc_result)]),
        _Result([waste]),
    )
    report = await service.get_downtime_production_correlations(
        db, date_from=date(2026, 11, 8), date_to=date(2026, 11, 8)
    )

    assert len(report.events) == 1
    correlated = report.events[0]
    assert correlated.downtime_id == downtime_id
    assert correlated.machine_code == "M-01"
    assert correlated.reported_by_operator_id == reporter_id
    assert correlated.observed_operator_ids == [operator_id]
    assert correlated.runtime_log_ids == [runtime_id]
    assert [row.labor_log_id for row in correlated.labor_logs] == [labor_id]
    assert correlated.labor_logs[0].approved_flag is False
    assert [row.inspection_id for row in correlated.quality_inspections] == [inspection_id]
    assert correlated.quality_inspections[0].results[0].result == "fail"
    assert [row.waste_record_id for row in correlated.waste_records] == [waste_record_id]
    assert "same_machine_time_overlap" in correlated.correlation_basis
    assert "same_recorded_work_order_or_production_order_quality_link" in correlated.correlation_basis
    assert any("not proof" in note for note in report.data_notes)
