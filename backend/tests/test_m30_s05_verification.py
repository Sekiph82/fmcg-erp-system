"""M30.S05 — Verification suite: deterministic fallback, safety/approval/rollback guards.

All tests are pure-unit (no database, no live AI provider).
Covers M30.S05.T001 (deterministic fallback) and M30.S05.T003 (safety/approval/rollback).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.ai import AIDecisionDomain, AIRiskTier, AIDecisionStatus
from app.services.ai_decision_service import (
    classify_risk_tier,
    evaluate_approval_requirement,
    build_observation_payload,
    validate_constraints,
    compare_kpi_impact,
    assert_approvable,
    assert_executable,
    compute_kpi_feedback,
    deterministic_fallback_recommendation,
)


# ── M30.S01.T001 — Risk tier registry ─────────────────────────────────────────

def test_classify_known_domain_returns_default_tier():
    tier = classify_risk_tier(AIDecisionDomain.QUALITY_DISPOSITION.value)
    assert tier == AIRiskTier.CRITICAL.value


def test_classify_maintenance_is_high():
    tier = classify_risk_tier(AIDecisionDomain.MAINTENANCE_ACTION.value)
    assert tier == AIRiskTier.HIGH.value


def test_classify_inventory_reorder_is_low():
    tier = classify_risk_tier(AIDecisionDomain.INVENTORY_REORDER.value)
    assert tier == AIRiskTier.LOW.value


def test_classify_unknown_domain_defaults_medium():
    tier = classify_risk_tier("NONEXISTENT_DOMAIN")
    assert tier == AIRiskTier.MEDIUM.value


def test_classify_registry_override_wins():
    tier = classify_risk_tier(AIDecisionDomain.INVENTORY_REORDER.value, registry_override="CRITICAL")
    assert tier == AIRiskTier.CRITICAL.value


def test_classify_invalid_override_falls_back_to_domain_default():
    tier = classify_risk_tier(AIDecisionDomain.INVENTORY_REORDER.value, registry_override="INVALID_TIER")
    assert tier == AIRiskTier.LOW.value


# ── M30.S01.T002 — Approval policy ────────────────────────────────────────────

def test_low_tier_high_confidence_auto_approves():
    result = evaluate_approval_requirement(AIRiskTier.LOW.value, confidence_score=0.95)
    assert result["auto_approved"] is True
    assert result["requires_approval"] is False


def test_low_tier_low_confidence_requires_approval():
    result = evaluate_approval_requirement(AIRiskTier.LOW.value, confidence_score=0.50)
    assert result["requires_approval"] is True
    assert result["auto_approved"] is False


def test_high_tier_always_requires_approval_regardless_of_confidence():
    result = evaluate_approval_requirement(AIRiskTier.HIGH.value, confidence_score=0.99)
    assert result["requires_approval"] is True
    assert result["auto_approved"] is False


def test_critical_tier_always_requires_approval():
    result = evaluate_approval_requirement(AIRiskTier.CRITICAL.value, confidence_score=1.0)
    assert result["requires_approval"] is True


def test_none_confidence_requires_approval():
    result = evaluate_approval_requirement(AIRiskTier.LOW.value, confidence_score=None)
    assert result["requires_approval"] is True
    assert result["reason"] == "confidence_unknown"


def test_policy_object_no_approval_overrides_tier():
    policy = SimpleNamespace(requires_human_approval=False, auto_approve_min_confidence=None)
    result = evaluate_approval_requirement(AIRiskTier.CRITICAL.value, confidence_score=0.1, policy=policy)
    assert result["auto_approved"] is True
    assert result["requires_approval"] is False


# ── M30.S02.T001 — Observation payload ────────────────────────────────────────

def test_build_observation_payload_structure():
    payload = build_observation_payload(
        domain="PRODUCTION_SCHEDULE",
        subject_id="order-123",
        context_data={"oee": 0.82, "pending_orders": 5},
    )
    assert payload["domain"] == "PRODUCTION_SCHEDULE"
    assert payload["subject_id"] == "order-123"
    assert "as_of" in payload
    assert payload["context"]["oee"] == 0.82


# ── M30.S02.T003 — Constraint validation ──────────────────────────────────────

def test_constraint_validation_passes_clean_recommendation():
    result = validate_constraints(
        "Increase production by 10%",
        constraints=[{"name": "no_halt", "rule": "forbidden_keyword", "value": "halt"}],
    )
    assert result["passed"] is True
    assert result["violations"] == []


def test_constraint_violation_detected():
    result = validate_constraints(
        "Halt all production lines immediately",
        constraints=[{"name": "no_halt", "rule": "forbidden_keyword", "value": "halt"}],
    )
    assert result["passed"] is False
    assert len(result["violations"]) == 1
    assert result["violations"][0]["constraint"] == "no_halt"


# ── M30.S03.T002 — KPI impact comparison ──────────────────────────────────────

def test_kpi_impact_positive_delta():
    comparison = compare_kpi_impact(
        baseline_kpis={"oee": 0.75, "throughput": 100.0},
        predicted_kpis={"oee": 0.82, "throughput": 110.0},
    )
    assert comparison["oee"]["delta"] == pytest.approx(0.07, abs=1e-6)
    assert comparison["throughput"]["delta_pct"] == pytest.approx(10.0, abs=1e-6)


def test_kpi_impact_missing_key_returns_none_delta():
    comparison = compare_kpi_impact(
        baseline_kpis={"oee": 0.75},
        predicted_kpis={"throughput": 100.0},
    )
    assert comparison["oee"]["delta"] is None
    assert comparison["throughput"]["delta"] is None


# ── M30.S03.T003 — Approval guards (M30.S05.T003) ─────────────────────────────

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_approvable_pending_approval_decision():
    d = SimpleNamespace(status=AIDecisionStatus.PENDING_APPROVAL.value, expires_at=None, requires_approval=True)
    assert assert_approvable(d, NOW)["ok"] is True


def test_approvable_already_executed_is_terminal():
    d = SimpleNamespace(status=AIDecisionStatus.EXECUTED.value, expires_at=None, requires_approval=True)
    result = assert_approvable(d, NOW)
    assert result["ok"] is False
    assert "terminal_state" in result["reason"]


def test_approvable_expired_window():
    d = SimpleNamespace(
        status=AIDecisionStatus.PENDING_APPROVAL.value,
        expires_at=NOW - timedelta(hours=1),
        requires_approval=True,
    )
    result = assert_approvable(d, NOW)
    assert result["ok"] is False
    assert result["reason"] == "approval_window_expired"


# ── M30.S03.T004 — Execution guards + idempotency ─────────────────────────────

def test_executable_approved_decision():
    d = SimpleNamespace(
        status=AIDecisionStatus.APPROVED.value,
        executed_at=None,
        idempotency_key="key-abc",
    )
    assert assert_executable(d, idempotency_key="key-abc")["ok"] is True


def test_executable_not_approved_blocked():
    d = SimpleNamespace(status=AIDecisionStatus.PENDING_APPROVAL.value, executed_at=None, idempotency_key=None)
    result = assert_executable(d)
    assert result["ok"] is False


def test_executable_already_executed_is_idempotent_safe():
    d = SimpleNamespace(
        status=AIDecisionStatus.APPROVED.value,
        executed_at=NOW,
        idempotency_key="key-abc",
    )
    result = assert_executable(d, "key-abc")
    assert result["ok"] is False
    assert result["reason"] == "already_executed"


def test_executable_rolled_back_decision_blocked():
    d = SimpleNamespace(status=AIDecisionStatus.ROLLED_BACK.value, executed_at=None, idempotency_key=None)
    result = assert_executable(d)
    assert result["ok"] is False


# ── M30.S04.T003 — KPI feedback ───────────────────────────────────────────────

def test_kpi_feedback_computes_error():
    fb = compute_kpi_feedback(
        predicted_kpis={"oee": 0.80, "cost": 500.0},
        actual_kpis={"oee": 0.75, "cost": 490.0},
    )
    assert fb["available"] is True
    assert fb["details"]["oee"]["error"] == pytest.approx(-0.05, abs=1e-6)
    assert fb["details"]["cost"]["error"] == pytest.approx(-10.0, abs=1e-6)


def test_kpi_feedback_no_data_returns_unavailable():
    fb = compute_kpi_feedback(None, None)
    assert fb["available"] is False


# ── M30.S05.T001 — Deterministic fallback ─────────────────────────────────────

def test_fallback_quality_disposition_returns_hold():
    result = deterministic_fallback_recommendation(AIDecisionDomain.QUALITY_DISPOSITION.value, {})
    assert "hold" in result["recommendation"].lower()
    assert result["source"] == "deterministic_fallback"
    assert result["requires_approval"] is True
    assert result["confidence_score"] is None


def test_fallback_every_known_domain_returns_text():
    for domain in AIDecisionDomain:
        result = deterministic_fallback_recommendation(domain.value, {})
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10


def test_fallback_unknown_domain_returns_generic():
    result = deterministic_fallback_recommendation("SPACE_EXPLORATION", {})
    assert "manual review" in result["recommendation"].lower()
