"""M35 — pure-rule tests for app/services/qa_enterprise_service.py (no database)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app.services import qa_enterprise_service as qa

TODAY = date(2026, 11, 10)
NOW = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


# ── S01 specifications / plans ───────────────────────────────────────────────

def _spec(version, status, start, end=None, **kw):
    return NS(spec_code="SPEC-PH", version=version, status=status, effective_from=start, effective_to=end,
              created_by_id="author", **kw)


def test_effective_spec_picks_window_and_ignores_drafts():
    v1 = _spec(1, "SUPERSEDED", date(2026, 1, 1), date(2026, 6, 30))
    v2 = _spec(2, "APPROVED", date(2026, 7, 1))
    v3 = _spec(3, "DRAFT", date(2026, 8, 1))
    assert qa.effective_spec([v1, v2, v3], date(2026, 3, 1)) is v1
    assert qa.effective_spec([v1, v2, v3], date(2026, 9, 1)) is v2
    assert qa.effective_spec([v1, v2, v3], date(2025, 12, 31)) is None


def test_spec_approval_requires_other_approver_and_future_date():
    spec = _spec(1, "DRAFT", TODAY - timedelta(days=1))
    errors = qa.spec_approval_errors(spec, "author", today=TODAY)
    assert any("author" in e for e in errors)
    assert any("past" in e for e in errors)
    assert qa.spec_approval_errors(_spec(1, "DRAFT", TODAY), "qa-manager", today=TODAY) == []


def test_spec_new_version_requires_approved_matching_change_request():
    spec = _spec(2, "DRAFT", TODAY)
    assert "change request" in qa.spec_approval_errors(spec, "qa", today=TODAY)[0]
    draft_cr = NS(status="SUBMITTED", target_reference="SPEC-PH")
    other_cr = NS(status="APPROVED", target_reference="SPEC-OTHER")
    good_cr = NS(status="APPROVED", target_reference="SPEC-PH")
    assert qa.spec_approval_errors(spec, "qa", draft_cr, today=TODAY)
    assert qa.spec_approval_errors(spec, "qa", other_cr, today=TODAY)
    assert qa.spec_approval_errors(spec, "qa", good_cr, today=TODAY) == []


def test_supersede_end_dates_previous_version():
    v1 = _spec(1, "APPROVED", date(2026, 1, 1))
    v2 = _spec(2, "DRAFT", date(2026, 12, 1))
    assert qa.supersede_previous([v1, v2], v2) == [v1]
    assert v1.status == "SUPERSEDED" and v1.effective_to == date(2026, 11, 30)


def test_plan_coverage_reports_missing_and_failed_mandatory_steps():
    steps = [NS(sequence=1, qc_type="INCOMING", qc_sub_type=None, is_mandatory=True),
             NS(sequence=2, qc_type="IN_PROCESS", qc_sub_type="MIXING", is_mandatory=True),
             NS(sequence=3, qc_type="FINISHED_GOODS", qc_sub_type=None, is_mandatory=True),
             NS(sequence=4, qc_type="RETEST", qc_sub_type=None, is_mandatory=False)]
    inspections = [NS(qc_type="INCOMING", qc_sub_type=None, status="PASSED"),
                   NS(qc_type="IN_PROCESS", qc_sub_type="BULK", status="PASSED"),
                   NS(qc_type="FINISHED_GOODS", qc_sub_type=None, status="FAILED")]
    cov = qa.plan_coverage(steps, inspections)
    assert cov["complete"] is False
    assert cov["missing_steps"] == [2] and cov["failed_steps"] == [3]
    assert [s["state"] for s in cov["steps"]] == ["SATISFIED", "NOT_STARTED", "FAILED", "NOT_STARTED"]


# ── S02 AQL ──────────────────────────────────────────────────────────────────

def _plan(lo, hi, n, ac, re_, **kw):
    base = dict(lot_size_min=lo, lot_size_max=hi, sample_size=n, acceptance_number=ac, rejection_number=re_,
                is_active=True, applies_to_type="INCOMING", product_id=None, material_id=None, plan_code="P")
    base.update(kw)
    return NS(**base)


def test_aql_plan_validation():
    assert qa.aql_plan_errors(dict(lot_size_min=1, lot_size_max=500, sample_size=50,
                                   acceptance_number=1, rejection_number=2)) == []
    errors = qa.aql_plan_errors(dict(lot_size_min=10, lot_size_max=5, sample_size=0,
                                     acceptance_number=2, rejection_number=2))
    assert len(errors) == 3


def test_select_aql_plan_prefers_item_specific_then_narrowest():
    generic_wide = _plan(1, 10000, 125, 3, 4)
    generic_narrow = _plan(501, 1200, 80, 2, 3)
    specific = _plan(1, 5000, 50, 1, 2, material_id="mat-1")
    plans = [generic_wide, generic_narrow, specific]
    assert qa.select_aql_plan(plans, 800, "INCOMING") is generic_narrow
    assert qa.select_aql_plan(plans, 800, "INCOMING", material_id="mat-1") is specific
    assert qa.select_aql_plan(plans, 20000, "INCOMING") is None
    assert qa.select_aql_plan(plans, 800, "FINISHED_GOODS") is None


@pytest.mark.parametrize("defects,decision", [(0, "ACCEPT"), (2, "ACCEPT"), (3, "SECOND_SAMPLE"), (5, "REJECT")])
def test_evaluate_aql(defects, decision):
    assert qa.evaluate_aql(_plan(1, 500, 50, 2, 5), 50, defects)["decision"] == decision


def test_evaluate_aql_incomplete_sample():
    assert qa.evaluate_aql(_plan(1, 500, 50, 2, 3), 49, 0)["decision"] == "INCOMPLETE"


# ── S02 SPC ──────────────────────────────────────────────────────────────────

def test_individuals_limits_known_values():
    lim = qa.individuals_limits([10, 12, 11, 13, 12])
    assert lim["center"] == pytest.approx(11.6)
    assert lim["mr_bar"] == pytest.approx(1.5)
    assert lim["ucl"] == pytest.approx(11.6 + 3 * 1.5 / 1.128)
    assert lim["lcl"] == pytest.approx(11.6 - 3 * 1.5 / 1.128)


def test_xbar_r_limits_known_values():
    lim = qa.xbar_r_limits([[1, 2, 3], [2, 3, 4]])
    assert lim["center"] == pytest.approx(2.5)
    assert lim["r_bar"] == pytest.approx(2)
    assert lim["ucl"] == pytest.approx(2.5 + 1.023 * 2)
    with pytest.raises(ValueError):
        qa.xbar_r_limits([[1, 2], [1, 2, 3]])


def test_capability_two_and_one_sided():
    assert qa.capability([9, 10, 11], 7, 13)["pp"] == pytest.approx(1.0)
    assert qa.capability([9, 10, 11], 7, 13)["ppk"] == pytest.approx(1.0)
    one = qa.capability([9, 10, 11], None, 12)
    assert one["pp"] is None and one["ppk"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("values,index,rule", [
    ([0, 0, 3.5], 2, "WE1_BEYOND_3_SIGMA"),
    ([0, 0, -3.1], 2, "WE1_BEYOND_3_SIGMA"),
    ([2.5, 0, 2.5], 2, "WE2_2_OF_3_BEYOND_2_SIGMA"),
    ([1.5, 1.5, 0, 1.5, 1.5], 4, "WE3_4_OF_5_BEYOND_1_SIGMA"),
    ([0.5] * 8, 7, "WE4_8_SAME_SIDE"),
])
def test_western_electric_rules(values, index, rule):
    assert (index, rule) in qa.western_electric_violations(values, 0.0, 1.0)


def test_in_control_series_has_no_violations():
    assert qa.western_electric_violations([0.2, -0.3, 0.1, -0.2, 0.4, -0.1, 0.3, -0.4], 0.0, 1.0) == []


def test_spc_signal_severity():
    assert qa.spc_signal_severity("WE1_BEYOND_3_SIGMA") == "HIGH"
    assert qa.spc_signal_severity("WE4_8_SAME_SIDE") == "MEDIUM"


def test_analyse_spc_flags_shifted_point():
    results = [NS(id=i, numeric_value=Decimal(v), min_spec=Decimal("5"), max_spec=Decimal("15"))
               for i, v in enumerate(["10", "10.2", "9.8", "10.1", "9.9", "10", "14"])]
    out = qa.analyse_spc(results)
    assert out["lsl"] == 5 and out["usl"] == 15
    assert out["limits"]["ucl"] == pytest.approx(10.5714 + 3 * (5.2 / 6) / 1.128, abs=1e-3)
    assert {"index": 6, "rule": "WE1_BEYOND_3_SIGMA", "test_result_id": "6", "value": 14.0} in out["violations"]


# ── S03 NCR / CAPA / concessions / cost ──────────────────────────────────────

@pytest.mark.parametrize("cur,tgt,ok", [
    ("OPEN", "UNDER_REVIEW", True), ("OPEN", "RESOLVED", True), ("UNDER_REVIEW", "RESOLVED", True),
    ("RESOLVED", "CLOSED", True), ("RESOLVED", "UNDER_REVIEW", True),
    ("OPEN", "CLOSED", False), ("UNDER_REVIEW", "OPEN", False), ("RESOLVED", "OPEN", False),
    ("CLOSED", "OPEN", False),
])
def test_deviation_transitions(cur, tgt, ok):
    assert (qa.deviation_transition_error(cur, tgt) is None) is ok


def _capa(status="IN_PROGRESS", root="Seal worn", steps=None, owner="owner", due=None):
    return NS(status=status, root_cause_analysis=root, steps=steps or [], assigned_to_id=owner, due_date=due)


def test_capa_completion_needs_root_cause_and_steps():
    open_step = NS(step_no=2, is_completed=False)
    assert qa.capa_transition_errors(_capa(root=" ", steps=[open_step]), "COMPLETED") == [
        "A documented root cause is required to complete a CAPA.", "CAPA steps [2] are not completed."]
    assert qa.capa_transition_errors(_capa(steps=[NS(step_no=1, is_completed=True)]), "COMPLETED") == []


def test_capa_cannot_be_verified_by_patch_or_reopened_after_verify():
    assert qa.capa_transition_errors(_capa(), "VERIFIED")
    assert qa.capa_transition_errors(_capa(status="VERIFIED"), "IN_PROGRESS")


def test_capa_verification_rules():
    assert qa.capa_verification_errors(_capa(status="OPEN"), "qa", "ok")
    assert qa.capa_verification_errors(_capa(status="COMPLETED"), "owner", "ok")
    assert qa.capa_verification_errors(_capa(status="COMPLETED"), "qa", "  ")
    assert qa.capa_verification_errors(_capa(status="COMPLETED"), "qa", "No recurrence in 30 lots") == []


def test_capa_overdue():
    assert qa.capa_is_overdue(_capa(due=TODAY - timedelta(days=1)), TODAY)
    assert not qa.capa_is_overdue(_capa(status="COMPLETED", due=TODAY - timedelta(days=1)), TODAY)


def test_concession_decision_rules():
    c = NS(status="PENDING", requested_by_id="req", conditions=None, valid_until=None)
    assert qa.concession_decision_errors(c, "req", approve=False, now=NOW)
    errors = qa.concession_decision_errors(c, "qa", approve=True, now=NOW)
    assert len(errors) == 2
    c.conditions, c.valid_until = "Sell only to industrial customers", NOW + timedelta(days=7)
    assert qa.concession_decision_errors(c, "qa", approve=True, now=NOW) == []


def test_concession_active_window():
    c = NS(status="APPROVED", valid_until=NOW + timedelta(hours=1))
    assert qa.concession_is_active(c, NOW)
    assert not qa.concession_is_active(c, NOW + timedelta(hours=2))
    assert not qa.concession_is_active(NS(status="REVOKED", valid_until=c.valid_until), NOW)


def test_quality_cost_summary():
    entries = [NS(category="PREVENTION", amount=Decimal("100"), risk_level=None, currency="KES"),
               NS(category="APPRAISAL", amount=Decimal("100"), risk_level=None, currency="KES"),
               NS(category="INTERNAL_FAILURE", amount=Decimal("300"), risk_level="HIGH", currency="KES"),
               NS(category="EXTERNAL_FAILURE", amount=Decimal("500"), risk_level="CRITICAL", currency="KES")]
    s = qa.summarize_quality_costs(entries)
    assert s["cost_of_poor_quality"] == "800.00" and s["cost_of_good_quality"] == "200.00"
    assert s["total"] == "1000.00" and s["copq_share_pct"] == "80.00"
    assert s["by_risk_level"] == {"HIGH": "300.00", "CRITICAL": "500.00"}
    assert s["mixed_currency"] is False
    assert qa.summarize_quality_costs([])["copq_share_pct"] is None


# ── S04 CoA / retain / instruments ───────────────────────────────────────────

def _coa(**kw):
    base = dict(status="DRAFT", issued_by_id="prep", overall_result="PASS", lot_id="lot",
                valid_until=None, issue_date=TODAY)
    base.update(kw)
    return NS(**base)


def test_coa_issue_rules():
    passed = NS(status="PASSED", lot_id="lot")
    released = NS(hold_flag=False, quarantine_flag=False)
    assert qa.coa_issue_errors(_coa(), "qa", passed, released) == []
    assert qa.coa_issue_errors(_coa(), "prep", passed, released)
    assert qa.coa_issue_errors(_coa(), "qa", None, released)
    assert qa.coa_issue_errors(_coa(), "qa", NS(status="FAILED", lot_id="lot"), released)
    assert qa.coa_issue_errors(_coa(), "qa", NS(status="PASSED", lot_id="other"), released)
    assert qa.coa_issue_errors(_coa(), "qa", NS(status="PASSED", lot_id=None), released)  # order-only inspection
    assert qa.coa_issue_errors(_coa(), "qa", passed, None)  # no release status record
    assert qa.coa_issue_errors(_coa(), "qa", passed, NS(hold_flag=True, quarantine_flag=False))
    assert qa.coa_issue_errors(_coa(overall_result="FAIL"), "qa", passed, released)
    assert qa.coa_issue_errors(_coa(status="ISSUED"), "qa", passed, released)


def test_retain_sample_rules():
    s = NS(status="STORED", quantity_remaining=Decimal("5"), retain_until=TODAY + timedelta(days=30))
    assert qa.retain_withdraw_errors(s, Decimal("6"))
    assert qa.retain_withdraw_errors(s, Decimal("0"))
    assert qa.retain_withdraw_errors(s, Decimal("5")) == []
    assert len(qa.retain_dispose_errors(s, None, early_authorized=False, today=TODAY)) == 2
    assert qa.retain_dispose_errors(s, "Lab audit", early_authorized=True, today=TODAY) == []
    expired = NS(status="STORED", retain_until=TODAY - timedelta(days=1))
    assert qa.retain_dispose_errors(expired, None, early_authorized=False, today=TODAY) == []
    assert qa.retain_samples_due([s, expired], TODAY) == [expired]


def _instrument(**kw):
    base = dict(instrument_id="PH-01", is_active=True, status="CURRENT", instrument_type="pH meter",
                next_calibration_due=TODAY + timedelta(days=60))
    base.update(kw)
    return NS(**base)


def test_instrument_usage_rules():
    method = NS(method_code="TM-PH", requires_instrument=True, instrument_type="PH Meter")
    assert qa.instrument_usage_errors(None, method, TODAY)
    assert qa.instrument_usage_errors(None, None, TODAY) == []
    assert qa.instrument_usage_errors(_instrument(), method, TODAY) == []
    assert qa.instrument_usage_errors(_instrument(status="OVERDUE"), method, TODAY)
    assert qa.instrument_usage_errors(_instrument(status="OUT_OF_SERVICE"), method, TODAY)
    assert qa.instrument_usage_errors(_instrument(next_calibration_due=TODAY - timedelta(days=1)), method, TODAY)
    assert qa.instrument_usage_errors(_instrument(is_active=False), method, TODAY)
    assert qa.instrument_usage_errors(_instrument(instrument_type="Balance"), method, TODAY)


# ── S05 audits / change control ──────────────────────────────────────────────

def test_audit_close_rules():
    pending = NS(closed_at=None, items=[{"result": "pass"}, {"result": "pending"}])
    assert "[1]" in qa.audit_close_errors(pending)[0]
    assert qa.audit_close_errors(NS(closed_at=None, items=[]))
    assert qa.audit_close_errors(NS(closed_at=NOW, items=[{"result": "pass"}]))
    done = NS(closed_at=None, items=[{"result": "pass"}, {"result": "fail", "finding": "x"}, {"result": "na"}])
    assert qa.audit_close_errors(done) == []
    assert qa.audit_failed_items(done) == [{"result": "fail", "finding": "x"}]


def test_change_request_lifecycle_rules():
    cr = NS(status="DRAFT", risk_assessment=None, requested_by_id="req", verification_notes=None)
    assert qa.change_request_transition_errors(cr, "SUBMITTED", "req")
    cr.risk_assessment = "Low: tighter pH limit"
    assert qa.change_request_transition_errors(cr, "SUBMITTED", "req") == []
    assert qa.change_request_transition_errors(cr, "APPROVED", "qa")
    cr.status = "SUBMITTED"
    assert qa.change_request_transition_errors(cr, "APPROVED", "req")
    assert qa.change_request_transition_errors(cr, "APPROVED", "qa") == []
    cr.status = "IMPLEMENTED"
    assert qa.change_request_transition_errors(cr, "CLOSED", "qa")
    assert qa.change_request_transition_errors(cr, "CLOSED", "qa", "Verified on 3 batches") == []
    cr.status = "CLOSED"
    assert qa.change_request_transition_errors(cr, "DRAFT", "qa")
