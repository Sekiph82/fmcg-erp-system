"""M30: AI Decision Governance Service — observe, decide, simulate, approve, execute, learn.

All public functions accept in-memory objects (SimpleNamespace or model instances)
and return plain dicts so they can be tested without a database.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.models.ai import AIDecisionDomain, AIRiskTier, AIDecisionStatus

# ── Risk tier helpers ─────────────────────────────────────────────────────────

_DEFAULT_RISK: dict[str, AIRiskTier] = {
    AIDecisionDomain.PRODUCTION_SCHEDULE: AIRiskTier.MEDIUM,
    AIDecisionDomain.PROCUREMENT_ORDER:   AIRiskTier.MEDIUM,
    AIDecisionDomain.MAINTENANCE_ACTION:  AIRiskTier.HIGH,
    AIDecisionDomain.PRICING_ADJUSTMENT:  AIRiskTier.HIGH,
    AIDecisionDomain.INVENTORY_REORDER:   AIRiskTier.LOW,
    AIDecisionDomain.QUALITY_DISPOSITION: AIRiskTier.CRITICAL,
    AIDecisionDomain.RESOURCE_ALLOCATION: AIRiskTier.MEDIUM,
    AIDecisionDomain.GENERAL:             AIRiskTier.MEDIUM,
}

_AUTO_APPROVE_THRESHOLD: dict[str, Decimal | None] = {
    AIRiskTier.LOW:      Decimal("0.70"),
    AIRiskTier.MEDIUM:   Decimal("0.85"),
    AIRiskTier.HIGH:     None,   # always requires human
    AIRiskTier.CRITICAL: None,   # always requires human
}


def classify_risk_tier(domain: str, registry_override: str | None = None) -> str:
    """Return the effective risk tier for a decision domain.

    registry_override — if set, must be a valid AIRiskTier value.
    """
    if registry_override is not None:
        try:
            return AIRiskTier(registry_override).value
        except ValueError:
            pass
    try:
        d = AIDecisionDomain(domain)
    except ValueError:
        return AIRiskTier.MEDIUM.value
    return _DEFAULT_RISK.get(d, AIRiskTier.MEDIUM).value


def evaluate_approval_requirement(
    risk_tier: str,
    confidence_score: float | Decimal | None,
    policy: Any | None = None,
) -> dict[str, Any]:
    """M30.S01.T002 — Determine whether human approval is required.

    policy — optional AIApprovalPolicy-like object with
              .requires_human_approval and .auto_approve_min_confidence.
    Returns dict with keys: requires_approval, auto_approved, reason.
    """
    try:
        tier = AIRiskTier(risk_tier)
    except ValueError:
        return {"requires_approval": True, "auto_approved": False, "reason": "unknown_risk_tier"}

    if policy is not None:
        if not policy.requires_human_approval:
            return {"requires_approval": False, "auto_approved": True, "reason": "policy_no_approval"}
        threshold = policy.auto_approve_min_confidence
    else:
        threshold = _AUTO_APPROVE_THRESHOLD.get(tier)

    if threshold is None:
        return {"requires_approval": True, "auto_approved": False, "reason": "tier_always_requires_approval"}

    if confidence_score is None:
        return {"requires_approval": True, "auto_approved": False, "reason": "confidence_unknown"}

    score = Decimal(str(confidence_score))
    if score >= threshold:
        return {"requires_approval": False, "auto_approved": True, "reason": "confidence_above_threshold"}
    return {"requires_approval": True, "auto_approved": False, "reason": "confidence_below_threshold"}


# ── Observation payload contract ──────────────────────────────────────────────

def build_observation_payload(
    domain: str,
    subject_id: str | None,
    context_data: dict[str, Any],
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """M30.S02.T001 — Canonical observation payload structure."""
    return {
        "domain": domain,
        "subject_id": subject_id,
        "as_of": (as_of or datetime.now(timezone.utc)).isoformat(),
        "context": context_data,
    }


def validate_constraints(
    recommendation: str,
    constraints: list[dict[str, Any]],
) -> dict[str, Any]:
    """M30.S02.T003 — Check recommendation against constraint list.

    Each constraint dict: {name, rule, value, operator}.
    Returns {passed, violations}.
    """
    violations = []
    for c in constraints:
        rule = c.get("rule", "")
        name = c.get("name", "unnamed")
        # Simple rule engine: "max_value", "min_value", "forbidden_keyword"
        if rule == "forbidden_keyword":
            kw = str(c.get("value", ""))
            if kw and kw.lower() in recommendation.lower():
                violations.append({"constraint": name, "rule": rule, "detail": f"keyword '{kw}' found"})
        # Other rule types deferred to domain-specific validators
    return {"passed": len(violations) == 0, "violations": violations}


# ── Scenario simulation ───────────────────────────────────────────────────────

def compare_kpi_impact(
    baseline_kpis: dict[str, float],
    predicted_kpis: dict[str, float],
) -> dict[str, Any]:
    """M30.S03.T002 — Compute delta between baseline and predicted KPI values."""
    result: dict[str, Any] = {}
    all_keys = set(baseline_kpis) | set(predicted_kpis)
    for k in sorted(all_keys):
        b = baseline_kpis.get(k)
        p = predicted_kpis.get(k)
        if b is not None and p is not None:
            delta = p - b
            pct = (delta / b * 100) if b != 0 else None
            result[k] = {"baseline": b, "predicted": p, "delta": delta, "delta_pct": pct}
        else:
            result[k] = {"baseline": b, "predicted": p, "delta": None, "delta_pct": None}
    return result


# ── Approval / execution guards ───────────────────────────────────────────────

def assert_approvable(decision: Any, as_of: datetime | None = None) -> dict[str, Any]:
    """M30.S03.T003 — Validate a decision can be approved right now.

    decision — object with .status, .expires_at, .requires_approval.
    Returns {ok, reason}.
    """
    now = as_of or datetime.now(timezone.utc)
    status = getattr(decision, "status", None)
    if status not in (AIDecisionStatus.PENDING_APPROVAL.value, AIDecisionStatus.AUTO_APPROVED.value,
                      AIDecisionStatus.PENDING_APPROVAL, AIDecisionStatus.AUTO_APPROVED):
        return {"ok": False, "reason": f"decision_in_terminal_state:{status}"}
    expires_at = getattr(decision, "expires_at", None)
    if expires_at is not None:
        exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if now > exp:
            return {"ok": False, "reason": "approval_window_expired"}
    return {"ok": True, "reason": "approvable"}


def assert_executable(decision: Any, idempotency_key: str | None = None) -> dict[str, Any]:
    """M30.S03.T004 — Validate decision can be executed (approved, not yet executed, key unique).

    Returns {ok, reason}.
    """
    status = getattr(decision, "status", None)
    approved_statuses = {AIDecisionStatus.APPROVED.value, AIDecisionStatus.AUTO_APPROVED.value,
                         AIDecisionStatus.APPROVED, AIDecisionStatus.AUTO_APPROVED}
    if status not in approved_statuses:
        return {"ok": False, "reason": f"not_approved:{status}"}
    executed_at = getattr(decision, "executed_at", None)
    if executed_at is not None:
        return {"ok": False, "reason": "already_executed"}
    if idempotency_key is not None:
        stored_key = getattr(decision, "idempotency_key", None)
        if stored_key and stored_key != idempotency_key:
            return {"ok": False, "reason": "idempotency_key_mismatch"}
    return {"ok": True, "reason": "executable"}


# ── Learning / outcome ────────────────────────────────────────────────────────

def compute_kpi_feedback(
    predicted_kpis: dict[str, float] | None,
    actual_kpis: dict[str, float] | None,
) -> dict[str, Any]:
    """M30.S04.T003 — Predicted-vs-actual KPI feedback."""
    if not predicted_kpis or not actual_kpis:
        return {"available": False, "details": {}}
    details: dict[str, Any] = {}
    for k in sorted(set(predicted_kpis) | set(actual_kpis)):
        p = predicted_kpis.get(k)
        a = actual_kpis.get(k)
        if p is not None and a is not None:
            error = a - p
            pct_err = (error / p * 100) if p != 0 else None
            details[k] = {"predicted": p, "actual": a, "error": error, "pct_error": pct_err}
        else:
            details[k] = {"predicted": p, "actual": a, "error": None, "pct_error": None}
    return {"available": True, "details": details}


def deterministic_fallback_recommendation(domain: str, observation: dict[str, Any]) -> dict[str, Any]:
    """M30.S05.T001 — Deterministic rule-based fallback when AI provider unavailable.

    Returns a minimal safe recommendation that does not rely on any AI provider.
    """
    rules: dict[str, str] = {
        AIDecisionDomain.PRODUCTION_SCHEDULE.value:  "Hold current schedule; escalate to production manager.",
        AIDecisionDomain.PROCUREMENT_ORDER.value:    "Do not issue new orders; alert procurement team.",
        AIDecisionDomain.MAINTENANCE_ACTION.value:   "Defer non-critical maintenance; escalate critical alerts.",
        AIDecisionDomain.PRICING_ADJUSTMENT.value:   "Maintain current prices; flag for manual review.",
        AIDecisionDomain.INVENTORY_REORDER.value:    "Apply standard reorder point from master data.",
        AIDecisionDomain.QUALITY_DISPOSITION.value:  "Place batch on hold pending manual QA review.",
        AIDecisionDomain.RESOURCE_ALLOCATION.value:  "Use last-known allocation; flag for planner review.",
        AIDecisionDomain.GENERAL.value:              "No AI recommendation available; manual review required.",
    }
    recommendation = rules.get(domain, rules[AIDecisionDomain.GENERAL.value])
    return {
        "domain": domain,
        "recommendation": recommendation,
        "confidence_score": None,
        "source": "deterministic_fallback",
        "requires_approval": True,
    }
