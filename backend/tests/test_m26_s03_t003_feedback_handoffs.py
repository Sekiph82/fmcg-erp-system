from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.machine_operator import (
    CorrelatedLaborLog,
    CorrelatedQualityInspection,
    CorrelatedQualityResult,
    CorrelatedWasteRecord,
    DowntimeProductionCorrelation,
    DowntimeProductionCorrelationReport,
    MachinePerformanceAnomaly,
    PerformanceAnomalyReportOut,
)
from app.services.machine_operator_service import build_machine_insight_follow_up_handoffs


def test_follow_up_handoffs_route_only_evidence_and_never_assign_operator_fault():
    machine_id, downtime_id, runtime_id, baseline_id = uuid4(), uuid4(), uuid4(), uuid4()
    work_order_id, production_order_id = uuid4(), uuid4()
    inspection_id, result_id, labor_id, waste_id = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)
    event = DowntimeProductionCorrelation(
        downtime_id=downtime_id,
        machine_id=machine_id,
        machine_code="M-01",
        machine_name="Mixer 01",
        work_order_id=work_order_id,
        production_order_id=production_order_id,
        downtime_class="mechanical_breakdown",
        start_time=now,
        end_time=now,
        runtime_log_ids=[runtime_id],
        labor_logs=[
            CorrelatedLaborLog(
                labor_log_id=labor_id,
                operator_id=uuid4(),
                approved_flag=True,
                start_time=now,
                end_time=now,
            )
        ],
        quality_inspections=[
            CorrelatedQualityInspection(
                inspection_id=inspection_id,
                qc_id="QC-001",
                status="fail",
                inspection_type="inline",
                inspected_at=now,
                work_order_id=work_order_id,
                production_order_id=production_order_id,
                results=[CorrelatedQualityResult(result_id=result_id, test_type="pH", result="fail")],
            )
        ],
        waste_records=[
            CorrelatedWasteRecord(
                waste_record_id=waste_id,
                waste_id="WASTE-001",
                work_order_id=work_order_id,
                production_order_id=production_order_id,
                waste_type="MATERIAL",
                waste_category="ABNORMAL",
                expected_qty=Decimal("10"),
                actual_qty=Decimal("7"),
                loss_qty=Decimal("3"),
                is_anomaly=True,
            )
        ],
    )
    correlations = DowntimeProductionCorrelationReport(
        period_start=date(2026, 11, 8), period_end=date(2026, 11, 8), events=[event]
    )
    anomalies = PerformanceAnomalyReportOut(
        period_start=date(2026, 11, 8),
        period_end=date(2026, 11, 8),
        baseline_start=date(2026, 10, 9),
        anomalies=[
            MachinePerformanceAnomaly(
                machine_id=machine_id,
                machine_code="M-01",
                machine_name="Mixer 01",
                runtime_log_id=runtime_id,
                event_start=now,
                event_end=now,
                observed_downtime_minutes=Decimal("60"),
                baseline_event_count=5,
                baseline_median_minutes=Decimal("10"),
                baseline_mad_minutes=Decimal("2"),
                alert_threshold_minutes=Decimal("16"),
                source_baseline_runtime_log_ids=[baseline_id],
            )
        ],
    )

    handoffs = build_machine_insight_follow_up_handoffs(correlations, anomalies)

    assert [item.destination for item in handoffs] == ["maintenance", "training", "planning"]
    maintenance, training, planning = handoffs
    assert {downtime_id, runtime_id, baseline_id}.issubset(set(maintenance.source_ids))
    assert {inspection_id, result_id, labor_id}.issubset(set(training.source_ids))
    assert {downtime_id, runtime_id, baseline_id, waste_id}.issubset(set(planning.source_ids))
    assert training.destination_path == "/dashboard/training/skill-matrix"
    assert planning.destination_path == "/dashboard/production/scheduling"
    assert all("does not establish cause" in item.attribution_note for item in handoffs)
    assert all("operator_id" not in item.model_dump() for item in handoffs)


def test_no_maintenance_handoff_without_anomaly_or_training_handoff_without_failed_qc():
    machine_id, downtime_id, runtime_id = uuid4(), uuid4(), uuid4()
    event = DowntimeProductionCorrelation(
        downtime_id=downtime_id,
        machine_id=machine_id,
        machine_code="M-02",
        machine_name="Mixer 02",
        downtime_class="mechanical_breakdown",
        start_time=datetime(2026, 11, 8, 8, tzinfo=timezone.utc),
        runtime_log_ids=[runtime_id],
        quality_inspections=[
            CorrelatedQualityInspection(
                inspection_id=uuid4(),
                qc_id="QC-PASS",
                status="pass",
                inspection_type="final",
                results=[CorrelatedQualityResult(result_id=uuid4(), test_type="pH", result="pass")],
            )
        ],
    )
    report = DowntimeProductionCorrelationReport(
        period_start=date(2026, 11, 8), period_end=date(2026, 11, 8), events=[event]
    )
    no_anomalies = PerformanceAnomalyReportOut(
        period_start=date(2026, 11, 8),
        period_end=date(2026, 11, 8),
        baseline_start=date(2026, 10, 9),
    )

    assert build_machine_insight_follow_up_handoffs(report, no_anomalies) == []
