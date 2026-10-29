from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.models.quality import QCType, QualityGateSeverity
from app.services import qms_service


@pytest.mark.parametrize(
    "selector_name,arguments,expected_trigger,expected_module",
    [
        (
            "list_receiving_quality_gates",
            (date(2026, 10, 29),),
            qms_service.RECEIVING_GATE_TRIGGER_EVENT,
            qms_service.RECEIVING_GATE_TARGET_MODULE,
        ),
        (
            "list_production_quality_gates",
            (qms_service.PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, date(2026, 10, 29)),
            qms_service.PRODUCTION_RELEASE_GATE_TRIGGER_EVENT,
            qms_service.PRODUCTION_GATE_TARGET_MODULE,
        ),
        (
            "list_production_quality_gates",
            (qms_service.PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, date(2026, 10, 29)),
            qms_service.PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT,
            qms_service.PRODUCTION_GATE_TARGET_MODULE,
        ),
        (
            "list_finished_goods_quality_gates",
            (date(2026, 10, 29),),
            qms_service.FINISHED_GOODS_RELEASE_GATE_TRIGGER_EVENT,
            qms_service.FINISHED_GOODS_GATE_TARGET_MODULE,
        ),
        (
            "list_dispatch_quality_gates",
            (date(2026, 10, 29),),
            qms_service.DISPATCH_GATE_TRIGGER_EVENT,
            qms_service.DISPATCH_GATE_TARGET_MODULE,
        ),
    ],
)
@pytest.mark.asyncio
async def test_gate_selectors_use_their_exact_module_event_and_as_of_date(
    monkeypatch, selector_name, arguments, expected_trigger, expected_module
):
    db = object()
    expected = [SimpleNamespace(code="SYNTHETIC_GATE")]
    calls = []

    async def list_definitions(actual_db, **filters):
        calls.append((actual_db, filters))
        return expected

    monkeypatch.setattr(qms_service, "list_quality_gate_definitions", list_definitions)

    actual = await getattr(qms_service, selector_name)(db, *arguments)

    assert actual is expected
    assert calls == [
        (
            db,
            {
                "active_only": True,
                "trigger_event": expected_trigger,
                "target_module": expected_module,
                "as_of_date": date(2026, 10, 29),
            },
        )
    ]


@pytest.mark.asyncio
async def test_production_selector_rejects_unknown_trigger_without_database_lookup(monkeypatch):
    async def unexpected_lookup(*_args, **_kwargs):
        raise AssertionError("unsupported trigger must not query gate definitions")

    monkeypatch.setattr(qms_service, "list_quality_gate_definitions", unexpected_lookup)

    assert await qms_service.list_production_quality_gates(
        object(), "ON_UNSUPPORTED_EVENT", date(2026, 10, 29)
    ) == []


@pytest.mark.parametrize(
    "target_module,trigger_event,expected_scope",
    [
        (" PROCUREMENT ", "on_receipt", "GRN_LINE"),
        ("production", "ON_PRODUCTION_RELEASE", "PRODUCTION_ORDER"),
        ("production", "ON_IN_PROCESS", "PRODUCTION_ORDER"),
        ("inventory", "ON_FINISHED_GOODS_RELEASE", "LOT"),
        ("sales", "ON_DISPATCH", "SHIPMENT_LINE"),
        ("other", "ON_RECEIPT", None),
    ],
)
def test_waiver_scope_is_bound_to_supported_gate_module_and_trigger(
    target_module, trigger_event, expected_scope
):
    gate = SimpleNamespace(target_module=target_module, trigger_event=trigger_event)

    assert qms_service._expected_waiver_scope(gate) == expected_scope


@pytest.mark.parametrize(
    "target_module,trigger_event,qc_type",
    [
        ("procurement", "ON_RECEIPT", QCType.INCOMING),
        ("production", "ON_PRODUCTION_RELEASE", QCType.IN_PROCESS),
        ("production", "ON_IN_PROCESS", QCType.IN_PROCESS),
        ("inventory", "ON_FINISHED_GOODS_RELEASE", QCType.FINISHED_GOODS),
        ("sales", "ON_DISPATCH", QCType.FINISHED_GOODS),
    ],
)
def test_gate_template_scope_accepts_the_expected_inspection_type(
    target_module, trigger_event, qc_type
):
    qms_service._validate_gate_template_scope(
        target_module, trigger_event, [SimpleNamespace(qc_type=qc_type)]
    )


@pytest.mark.parametrize(
    "target_module,trigger_event,wrong_qc_type",
    [
        ("procurement", "ON_RECEIPT", QCType.IN_PROCESS),
        ("production", "ON_PRODUCTION_RELEASE", QCType.INCOMING),
        ("production", "ON_IN_PROCESS", QCType.FINISHED_GOODS),
        ("inventory", "ON_FINISHED_GOODS_RELEASE", QCType.INCOMING),
        ("sales", "ON_DISPATCH", QCType.IN_PROCESS),
    ],
)
def test_gate_template_scope_rejects_cross_module_inspection_types(
    target_module, trigger_event, wrong_qc_type
):
    with pytest.raises(ValueError, match="can link only"):
        qms_service._validate_gate_template_scope(
            target_module, trigger_event, [SimpleNamespace(qc_type=wrong_qc_type)]
        )


@pytest.mark.parametrize(
    "severity,mandatory,waivable,reason_required,approval_required",
    [
        (QualityGateSeverity.LOW, False, False, False, False),
        (QualityGateSeverity.MEDIUM, True, False, True, True),
        (QualityGateSeverity.HIGH, True, True, True, True),
        (QualityGateSeverity.CRITICAL, True, False, True, True),
    ],
)
def test_gate_policy_accepts_safe_severity_and_waiver_combinations(
    severity, mandatory, waivable, reason_required, approval_required
):
    qms_service._validate_quality_gate_policy(
        severity, mandatory, waivable, reason_required, approval_required
    )


@pytest.mark.parametrize(
    "severity,mandatory,waivable,reason_required,approval_required,message",
    [
        ("UNKNOWN", True, False, True, True, "severity must be"),
        (QualityGateSeverity.CRITICAL, False, False, True, True, "must remain mandatory"),
        (QualityGateSeverity.CRITICAL, True, True, True, True, "cannot be waived"),
        (QualityGateSeverity.HIGH, True, True, False, True, "must require a reason"),
        (QualityGateSeverity.HIGH, True, True, True, False, "must require quality approval"),
    ],
)
def test_gate_policy_rejects_unsafe_or_unknown_combinations(
    severity, mandatory, waivable, reason_required, approval_required, message
):
    with pytest.raises(ValueError, match=message):
        qms_service._validate_quality_gate_policy(
            severity, mandatory, waivable, reason_required, approval_required
        )


@pytest.mark.parametrize(
    "start,end,other_start,other_end,overlaps",
    [
        (date(2026, 1, 1), date(2026, 1, 10), date(2026, 1, 10), None, True),
        (date(2026, 1, 1), date(2026, 1, 10), date(2026, 1, 11), None, False),
        (date(2026, 1, 11), None, date(2026, 1, 1), date(2026, 1, 10), False),
        (date(2026, 1, 10), None, date(2026, 1, 1), date(2026, 1, 10), True),
        (date(2026, 1, 1), None, date(2026, 1, 2), None, True),
    ],
)
def test_gate_version_windows_use_inclusive_boundaries_and_open_ends(
    start, end, other_start, other_end, overlaps
):
    assert qms_service._gate_windows_overlap(start, end, other_start, other_end) is overlaps


def test_gate_effective_window_requires_start_and_rejects_end_before_start():
    with pytest.raises(ValueError, match="effective_from is required"):
        qms_service._validate_gate_effective_window(None, None)
    with pytest.raises(ValueError, match="effective_to must be on or after"):
        qms_service._validate_gate_effective_window(date(2026, 1, 2), date(2026, 1, 1))

    qms_service._validate_gate_effective_window(date(2026, 1, 1), date(2026, 1, 1))
    qms_service._validate_gate_effective_window(date(2026, 1, 1), None)
