"""M35.S06 — QC/QA Enterprise Upgrade verification suite.

Pure-unit tests covering QC inspection lifecycle, parameter evaluation,
SPC/sampling contracts, NCR/CAPA/deviation enums, lab evidence (CoA,
calibration), QA governance (audit standards, supplier food safety), and
quality-gate severity constraints — no database required.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.quality import (
    QCType, QCStatus, QCDecision, ParameterType, QualityGateSeverity,
    SamplingMethod, HazardType, RiskLevel, DeviationStatus,
    CorrectiveActionStatus, ReleaseStatus, CalibrationStatus,
    CoAStatus, AQLLevel, QMSAIAgentType, QMSAIRecStatus,
    AuditStandard, AuditType, AuditResult, SupplierFoodSafetyStatus,
)
from app.services.quality_service import auto_evaluate_result, _compute_inspection_outcome


# ── M35.S01 — Specifications & QC Plan: enum contracts ───────────────────────

def test_qc_type_has_all_four_types():
    values = {t.value for t in QCType}
    assert "INCOMING" in values
    assert "IN_PROCESS" in values
    assert "FINISHED_GOODS" in values
    assert "RETEST" in values


def test_qc_status_includes_conditional_release():
    values = {s.value for s in QCStatus}
    assert "CONDITIONAL_RELEASE" in values
    assert "PASSED" in values
    assert "FAILED" in values


def test_qc_decision_covers_all_outcomes():
    values = {d.value for d in QCDecision}
    assert "ACCEPT" in values
    assert "REJECT" in values
    assert "REWORK" in values
    assert "CONDITIONAL_RELEASE" in values


def test_quality_gate_severity_has_four_tiers():
    tiers = {s.value for s in QualityGateSeverity}
    assert tiers == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


# ── M35.S02 — Sampling/AQL/SPC: parameter evaluation ─────────────────────────

def _make_tr(**kwargs):
    defaults = dict(
        parameter_type=ParameterType.NUMERIC,
        numeric_value=None, text_value=None, boolean_value=None,
        min_spec=None, max_spec=None, expected_text=None,
        is_passed=None, is_critical=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_numeric_within_range_passes():
    tr = _make_tr(numeric_value=Decimal("7.0"), min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is True


def test_numeric_below_min_fails():
    tr = _make_tr(numeric_value=Decimal("4.9"), min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is False


def test_numeric_above_max_fails():
    tr = _make_tr(numeric_value=Decimal("9.1"), min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is False


def test_numeric_none_value_fails():
    tr = _make_tr(numeric_value=None, min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is False


def test_text_match_passes():
    tr = _make_tr(
        parameter_type=ParameterType.TEXT,
        text_value="Clear", expected_text="Clear",
    )
    assert auto_evaluate_result(tr) is True


def test_text_mismatch_fails():
    tr = _make_tr(
        parameter_type=ParameterType.TEXT,
        text_value="Turbid", expected_text="Clear",
    )
    assert auto_evaluate_result(tr) is False


def test_boolean_match_passes():
    tr = _make_tr(
        parameter_type=ParameterType.BOOLEAN,
        boolean_value=True, expected_text="true",
    )
    assert auto_evaluate_result(tr) is True


def test_boolean_mismatch_fails():
    tr = _make_tr(
        parameter_type=ParameterType.BOOLEAN,
        boolean_value=False, expected_text="true",
    )
    assert auto_evaluate_result(tr) is False


def test_pass_fail_explicit_false_fails():
    tr = _make_tr(parameter_type=ParameterType.PASS_FAIL, is_passed=False)
    assert auto_evaluate_result(tr) is False


# ── M35.S02 — Inspection outcome computation ──────────────────────────────────

def test_outcome_all_passed_no_critical_fail():
    trs = [
        SimpleNamespace(is_passed=True, is_critical=False),
        SimpleNamespace(is_passed=True, is_critical=True),
    ]
    all_passed, any_crit_fail = _compute_inspection_outcome(SimpleNamespace(test_results=trs), trs)
    assert all_passed is True
    assert any_crit_fail is False


def test_outcome_critical_fail_detected():
    trs = [
        SimpleNamespace(is_passed=False, is_critical=True),
        SimpleNamespace(is_passed=True, is_critical=False),
    ]
    all_passed, any_crit_fail = _compute_inspection_outcome(SimpleNamespace(test_results=trs), trs)
    assert all_passed is False
    assert any_crit_fail is True


def test_outcome_empty_results_pass():
    all_passed, any_crit_fail = _compute_inspection_outcome(SimpleNamespace(test_results=[]), [])
    assert all_passed is True
    assert any_crit_fail is False


# ── M35.S03 — NCR/CAPA/Deviation lifecycle enums ──────────────────────────────

def test_deviation_status_lifecycle():
    # OPEN → UNDER_REVIEW → RESOLVED → CLOSED
    statuses = [s.value for s in DeviationStatus]
    assert "OPEN" in statuses
    assert "UNDER_REVIEW" in statuses
    assert "RESOLVED" in statuses
    assert "CLOSED" in statuses


def test_corrective_action_status_includes_verified():
    values = {s.value for s in CorrectiveActionStatus}
    assert "OPEN" in values
    assert "COMPLETED" in values
    assert "VERIFIED" in values
    assert "OVERDUE" in values


def test_risk_level_has_critical():
    values = {r.value for r in RiskLevel}
    assert "CRITICAL" in values
    assert "LOW" in values


def test_hazard_type_covers_fmcg_hazards():
    values = {h.value for h in HazardType}
    assert "BIOLOGICAL" in values
    assert "CHEMICAL" in values
    assert "PHYSICAL" in values
    assert "ALLERGEN" in values


# ── M35.S04 — Lab & Release Evidence ──────────────────────────────────────────

def test_release_status_has_quarantined_and_released():
    values = {s.value for s in ReleaseStatus}
    assert "QUARANTINED" in values
    assert "RELEASED" in values
    assert "REJECTED" in values
    assert "REWORK" in values
    assert "SCRAPPED" in values


def test_coa_status_lifecycle():
    values = {s.value for s in CoAStatus}
    assert "DRAFT" in values
    assert "ISSUED" in values
    assert "SUPERSEDED" in values


def test_calibration_status_has_overdue():
    values = {s.value for s in CalibrationStatus}
    assert "CURRENT" in values
    assert "DUE_SOON" in values
    assert "OVERDUE" in values
    assert "OUT_OF_SERVICE" in values


def test_aql_level_has_standard_inspection_levels():
    values = {a.value for a in AQLLevel}
    assert "I" in values
    assert "II" in values
    assert "III" in values


# ── M35.S05 — QA Governance ──────────────────────────────────────────────────

def test_audit_standard_covers_food_safety_schemes():
    values = {s.value for s in AuditStandard}
    assert "BRC" in values
    assert "FSSC_22000" in values
    assert "ISO_22000" in values
    assert "HALAL" in values
    assert "HACCP_CODEX" in values


def test_audit_result_has_conditional_pass():
    values = {r.value for r in AuditResult}
    assert "PASS" in values
    assert "CONDITIONAL_PASS" in values
    assert "FAIL" in values


def test_supplier_food_safety_status_lifecycle():
    values = {s.value for s in SupplierFoodSafetyStatus}
    assert "APPROVED" in values
    assert "CONDITIONAL" in values
    assert "SUSPENDED" in values
    assert "REJECTED" in values


def test_qms_ai_agent_types_cover_quality_domains():
    values = {a.value for a in QMSAIAgentType}
    assert "QUALITY_RISK_PREDICTOR" in values
    assert "DEVIATION_ANALYZER" in values
    assert "HACCP_ASSISTANT" in values


def test_qms_ai_rec_status_lifecycle():
    values = {s.value for s in QMSAIRecStatus}
    assert "PENDING" in values
    assert "ACCEPTED" in values
    assert "REJECTED" in values
    assert "APPLIED" in values


# ── M35.S01 — Sampling methods include CCP-triggered ─────────────────────────

def test_sampling_method_has_ccp_triggered():
    values = {m.value for m in SamplingMethod}
    assert "CCP_TRIGGERED" in values
    assert "FIXED" in values
    assert "PERCENTAGE" in values


# ── M35.S02 — SPC boundary: numeric spec boundary conditions ──────────────────

def test_numeric_exactly_at_min_passes():
    tr = _make_tr(numeric_value=Decimal("5.0"), min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is True


def test_numeric_exactly_at_max_passes():
    tr = _make_tr(numeric_value=Decimal("9.0"), min_spec=Decimal("5.0"), max_spec=Decimal("9.0"))
    assert auto_evaluate_result(tr) is True


def test_numeric_no_spec_limits_always_passes():
    tr = _make_tr(numeric_value=Decimal("999.9"), min_spec=None, max_spec=None)
    assert auto_evaluate_result(tr) is True
