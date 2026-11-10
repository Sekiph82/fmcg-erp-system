"""M35 QC/QA enterprise rules.

Pure functions take plain objects (ORM rows or SimpleNamespace) so the rules
can be verified without a database; the few async helpers do the lookups.
"""
from __future__ import annotations

import math
import statistics
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _v(value: Any) -> Any:
    """Enum → value, everything else unchanged."""
    return getattr(value, "value", value)


def _today() -> date:
    return date.today()


# ── S01 Specifications ───────────────────────────────────────────────────────

def effective_spec(specs: Iterable[Any], as_of: date) -> Optional[Any]:
    """Approved (or since-superseded) version whose effective window covers `as_of`."""
    candidates = [
        s for s in specs
        if _v(s.status) in {"APPROVED", "SUPERSEDED"}
        and s.effective_from <= as_of
        and (s.effective_to is None or s.effective_to >= as_of)
    ]
    return max(candidates, key=lambda s: s.version, default=None)


def spec_approval_errors(spec: Any, actor_id: Any, change_request: Any = None,
                         today: Optional[date] = None) -> list[str]:
    today = today or _today()
    errors = []
    if _v(spec.status) != "DRAFT":
        errors.append("Only a DRAFT specification can be approved.")
    if actor_id == spec.created_by_id:
        errors.append("The specification author cannot approve it.")
    if spec.effective_from < today:
        errors.append("A specification cannot become effective in the past.")
    if spec.version > 1:
        if change_request is None:
            errors.append("A new specification version requires an approved change request.")
        else:
            if _v(change_request.status) not in {"APPROVED", "IMPLEMENTED"}:
                errors.append("The linked change request is not approved.")
            if change_request.target_reference != spec.spec_code:
                errors.append("The linked change request targets a different specification.")
    return errors


def supersede_previous(existing: Iterable[Any], new_spec: Any) -> list[Any]:
    """End-date earlier live versions of the same spec at the new effective date."""
    changed = []
    cutoff = new_spec.effective_from - timedelta(days=1)
    for s in existing:
        if s is new_spec or s.spec_code != new_spec.spec_code or s.version >= new_spec.version:
            continue
        if _v(s.status) != "APPROVED":
            continue
        if s.effective_to is None or s.effective_to > cutoff:
            s.effective_to = max(cutoff, s.effective_from)
        s.status = "SUPERSEDED"
        changed.append(s)
    return changed


def plan_coverage(steps: Iterable[Any], inspections: Iterable[Any]) -> dict:
    """Compare a QC plan's steps with the inspections recorded for one order/lot."""
    inspections = list(inspections)
    rows, missing, failed = [], [], []
    for step in sorted(steps, key=lambda s: s.sequence):
        matching = [
            i for i in inspections
            if _v(i.qc_type) == _v(step.qc_type)
            and (not step.qc_sub_type or (i.qc_sub_type or "") == step.qc_sub_type)
        ]
        statuses = {_v(i.status) for i in matching}
        if statuses & {"PASSED", "CONDITIONAL_RELEASE"}:
            state = "SATISFIED"
        elif "FAILED" in statuses:
            state = "FAILED"
        elif matching:
            state = "IN_PROGRESS"
        else:
            state = "NOT_STARTED"
        if step.is_mandatory and state != "SATISFIED":
            (failed if state == "FAILED" else missing).append(step.sequence)
        rows.append({"sequence": step.sequence, "qc_type": _v(step.qc_type),
                     "qc_sub_type": step.qc_sub_type, "is_mandatory": step.is_mandatory, "state": state})
    return {"complete": not missing and not failed, "missing_steps": missing,
            "failed_steps": failed, "steps": rows}


# ── S02 AQL ───────────────────────────────────────────────────────────────────

def aql_plan_errors(values: dict) -> list[str]:
    errors = []
    sample, ac, re_ = values.get("sample_size"), values.get("acceptance_number"), values.get("rejection_number")
    lo, hi = values.get("lot_size_min"), values.get("lot_size_max")
    if sample is None or sample <= 0:
        errors.append("sample_size must be positive.")
    if ac is None or ac < 0:
        errors.append("acceptance_number must be zero or more.")
    if ac is not None and re_ is not None and re_ <= ac:
        errors.append("rejection_number must be greater than acceptance_number.")
    if lo is None or lo < 1:
        errors.append("lot_size_min must be at least 1.")
    if hi is not None and lo is not None and hi < lo:
        errors.append("lot_size_max must not be below lot_size_min.")
    if hi is not None and sample is not None and sample > hi:
        errors.append("sample_size cannot exceed lot_size_max.")
    return errors


def select_aql_plan(plans: Iterable[Any], lot_size: int, applies_to: str,
                    product_id: Any = None, material_id: Any = None) -> Optional[Any]:
    """Active plan for the lot size; item-specific plans win, then the narrowest range."""
    def fits(p):
        return (p.is_active and p.applies_to_type == applies_to and p.lot_size_min <= lot_size
                and (p.lot_size_max is None or lot_size <= p.lot_size_max)
                and (p.product_id is None or p.product_id == product_id)
                and (p.material_id is None or p.material_id == material_id))

    def rank(p):
        specific = (p.product_id is not None and p.product_id == product_id) or (
            p.material_id is not None and p.material_id == material_id)
        width = (p.lot_size_max - p.lot_size_min) if p.lot_size_max is not None else math.inf
        return (0 if specific else 1, width)

    return min((p for p in plans if fits(p)), key=rank, default=None)


def evaluate_aql(plan: Any, sample_inspected: int, defects_found: int) -> dict:
    if sample_inspected < plan.sample_size:
        return {"decision": "INCOMPLETE", "reason": f"{plan.sample_size} units must be inspected; {sample_inspected} were."}
    if defects_found < 0:
        raise ValueError("defects_found cannot be negative")
    if defects_found <= plan.acceptance_number:
        decision = "ACCEPT"
    elif defects_found >= plan.rejection_number:
        decision = "REJECT"
    else:
        decision = "SECOND_SAMPLE"
    return {"decision": decision, "acceptance_number": plan.acceptance_number,
            "rejection_number": plan.rejection_number, "defects_found": defects_found}


# ── S02 SPC ───────────────────────────────────────────────────────────────────

_D2_N2 = 1.128
# n: (A2, D3, D4)
_XBAR_R = {2: (1.880, 0, 3.267), 3: (1.023, 0, 2.574), 4: (0.729, 0, 2.282), 5: (0.577, 0, 2.114),
           6: (0.483, 0, 2.004), 7: (0.419, 0.076, 1.924), 8: (0.373, 0.136, 1.864),
           9: (0.337, 0.184, 1.816), 10: (0.308, 0.223, 1.777)}


def individuals_limits(values: Sequence[float]) -> dict:
    if len(values) < 2:
        raise ValueError("At least two values are needed for an individuals chart.")
    mean = statistics.fmean(values)
    mr_bar = statistics.fmean(abs(b - a) for a, b in zip(values, values[1:]))
    sigma = mr_bar / _D2_N2
    return {"center": mean, "sigma": sigma, "ucl": mean + 3 * sigma, "lcl": mean - 3 * sigma,
            "mr_bar": mr_bar, "mr_ucl": 3.267 * mr_bar}


def xbar_r_limits(subgroups: Sequence[Sequence[float]]) -> dict:
    sizes = {len(g) for g in subgroups}
    if len(subgroups) < 2 or len(sizes) != 1 or next(iter(sizes)) not in _XBAR_R:
        raise ValueError("Need two or more equal subgroups of size 2-10.")
    a2, d3, d4 = _XBAR_R[next(iter(sizes))]
    xbar = statistics.fmean(statistics.fmean(g) for g in subgroups)
    rbar = statistics.fmean(max(g) - min(g) for g in subgroups)
    return {"center": xbar, "ucl": xbar + a2 * rbar, "lcl": xbar - a2 * rbar,
            "r_bar": rbar, "r_ucl": d4 * rbar, "r_lcl": d3 * rbar}


def capability(values: Sequence[float], lsl: Optional[float], usl: Optional[float]) -> dict:
    """Overall-sigma performance indices (Pp/Ppk); within-subgroup Cp/Cpk would use MR-bar/d2."""
    if len(values) < 2 or (lsl is None and usl is None):
        return {"pp": None, "ppk": None}
    mean, sd = statistics.fmean(values), statistics.stdev(values)
    if sd == 0:
        return {"pp": None, "ppk": None, "mean": mean, "stdev": 0.0}
    pp = (usl - lsl) / (6 * sd) if lsl is not None and usl is not None else None
    sides = [x for x in ((usl - mean) / (3 * sd) if usl is not None else None,
                         (mean - lsl) / (3 * sd) if lsl is not None else None) if x is not None]
    return {"pp": pp, "ppk": min(sides), "mean": mean, "stdev": sd}


def western_electric_violations(values: Sequence[float], center: float, sigma: float) -> list[tuple[int, str]]:
    """(index, rule) for each point that completes a rule violation."""
    if sigma <= 0:
        return []
    z = [(v - center) / sigma for v in values]
    out: list[tuple[int, str]] = []
    for i, zi in enumerate(z):
        if abs(zi) > 3:
            out.append((i, "WE1_BEYOND_3_SIGMA"))
        for side in (1, -1):
            w3 = z[max(0, i - 2): i + 1]
            if len(w3) == 3 and side * zi > 2 and sum(side * x > 2 for x in w3) >= 2:
                out.append((i, "WE2_2_OF_3_BEYOND_2_SIGMA"))
            w5 = z[max(0, i - 4): i + 1]
            if len(w5) == 5 and side * zi > 1 and sum(side * x > 1 for x in w5) >= 4:
                out.append((i, "WE3_4_OF_5_BEYOND_1_SIGMA"))
            w8 = z[max(0, i - 7): i + 1]
            if len(w8) == 8 and all(side * x > 0 for x in w8):
                out.append((i, "WE4_8_SAME_SIDE"))
    return out


def spc_signal_severity(rule: str) -> str:
    return "HIGH" if rule.startswith("WE1") else "MEDIUM"


async def load_spc_series(db: AsyncSession, product_id: Any, parameter_name: str, limit: int = 200,
                          qc_type: Any = None) -> list:
    """Most recent `limit` numeric results for a product parameter, oldest first (by recording time)."""
    from app.models.quality import QCInspection, QCTestResult

    q = (
        select(QCTestResult)
        .join(QCInspection, QCInspection.id == QCTestResult.inspection_id)
        .where(QCInspection.product_id == product_id, QCTestResult.parameter_name == parameter_name,
               QCTestResult.numeric_value.is_not(None))
    )
    if qc_type is not None:
        q = q.where(QCInspection.qc_type == qc_type)
    rows = await db.execute(q.order_by(QCTestResult.created_at.desc(), QCTestResult.id.desc()).limit(limit))
    return list(reversed(rows.scalars().all()))


def analyse_spc(results: Sequence[Any]) -> dict:
    values = [float(r.numeric_value) for r in results]
    limits = individuals_limits(values)
    lsl = next((float(r.min_spec) for r in reversed(results) if r.min_spec is not None), None)
    usl = next((float(r.max_spec) for r in reversed(results) if r.max_spec is not None), None)
    violations = western_electric_violations(values, limits["center"], limits["sigma"])
    return {
        "n": len(values), "limits": limits, "capability": capability(values, lsl, usl),
        "lsl": lsl, "usl": usl,
        "violations": [{"index": i, "rule": rule, "test_result_id": str(results[i].id), "value": values[i]}
                       for i, rule in violations],
    }


async def record_spc_signals(db: AsyncSession, product_id: Any, parameter_name: str,
                             actor_id: Any, limit: int = 200, qc_type: Any = None) -> dict:
    """Persist new rule hits once and raise one deviation per evaluation that found any."""
    from app.models.quality import QCInspection, RiskLevel, SPCSignal
    from app.services.qms_service import create_deviation

    results = await load_spc_series(db, product_id, parameter_name, limit, qc_type)
    analysis = analyse_spc(results)
    lim = analysis["limits"]
    existing = await db.execute(
        select(SPCSignal.test_result_id, SPCSignal.rule)
        .where(SPCSignal.test_result_id.in_([r.id for r in results]))
    )
    seen = {(row[0], row[1]) for row in existing.all()}
    new_signals = []
    for v in analysis["violations"]:
        result = results[v["index"]]
        if (result.id, v["rule"]) in seen:
            continue
        seen.add((result.id, v["rule"]))
        signal = SPCSignal(
            product_id=product_id, parameter_name=parameter_name, test_result_id=result.id, rule=v["rule"],
            value=Decimal(str(v["value"])), center_line=Decimal(str(round(lim["center"], 4))),
            ucl=Decimal(str(round(lim["ucl"], 4))), lcl=Decimal(str(round(lim["lcl"], 4))),
            detected_by_id=actor_id,
        )
        db.add(signal)
        new_signals.append(signal)

    deviation = None
    if new_signals:
        severity = RiskLevel.HIGH if any(spc_signal_severity(s.rule) == "HIGH" for s in new_signals) else RiskLevel.MEDIUM
        await db.flush()
        # Scope the deviation to the latest offending inspection so it can be approved and closed.
        signal_ids = {s.test_result_id for s in new_signals}
        latest = next(r for r in reversed(results) if r.id in signal_ids)
        source = await db.get(QCInspection, latest.inspection_id)
        deviation = await create_deviation(db, {
            "inspection_id": latest.inspection_id,
            "lot_id": source.lot_id if source else None,
            "production_order_id": source.production_order_id if source else None,
            "product_id": product_id, "deviation_type": "SPC_OUT_OF_CONTROL", "severity": severity,
            "description": f"SPC out-of-control on {parameter_name}: "
                           + ", ".join(sorted({s.rule for s in new_signals})),
        }, actor_id)
        for s in new_signals:
            s.deviation_id = deviation.id
    await db.flush()
    return {"analysis": analysis, "new_signals": len(new_signals),
            "deviation_id": str(deviation.id) if deviation else None}


# ── S03 NCR / CAPA / concessions / cost ──────────────────────────────────────

DEVIATION_TRANSITIONS = {
    "OPEN": {"UNDER_REVIEW", "RESOLVED"},
    "UNDER_REVIEW": {"RESOLVED"},
    "RESOLVED": {"CLOSED", "UNDER_REVIEW"},
    "CLOSED": set(),
}


def deviation_transition_error(current: Any, target: Any) -> Optional[str]:
    cur, tgt = _v(current), _v(target)
    if cur == tgt:
        return None
    if tgt not in DEVIATION_TRANSITIONS.get(cur, set()):
        return f"A deviation cannot move from {cur} to {tgt}."
    return None


CAPA_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "COMPLETED", "OVERDUE"},
    "IN_PROGRESS": {"COMPLETED", "OVERDUE"},
    "OVERDUE": {"IN_PROGRESS", "COMPLETED"},
    "COMPLETED": {"IN_PROGRESS"},
    "VERIFIED": set(),
}


def capa_transition_errors(ca: Any, target: Any) -> list[str]:
    cur, tgt = _v(ca.status), _v(target)
    if cur == tgt:
        return []
    if tgt == "VERIFIED":
        return ["Use the verification action to verify a CAPA."]
    if tgt not in CAPA_TRANSITIONS.get(cur, set()):
        return [f"A CAPA cannot move from {cur} to {tgt}."]
    if tgt == "COMPLETED":
        return capa_completion_errors(ca)
    return []


def capa_completion_errors(ca: Any) -> list[str]:
    errors = []
    if not (ca.root_cause_analysis or "").strip():
        errors.append("A documented root cause is required to complete a CAPA.")
    open_steps = [s.step_no for s in (ca.steps or []) if not s.is_completed]
    if open_steps:
        errors.append(f"CAPA steps {open_steps} are not completed.")
    return errors


def capa_verification_errors(ca: Any, verifier_id: Any, effectiveness_check: str) -> list[str]:
    errors = []
    if _v(ca.status) != "COMPLETED":
        errors.append("Only a COMPLETED CAPA can be verified.")
    if verifier_id is not None and verifier_id == ca.assigned_to_id:
        errors.append("The CAPA owner cannot verify its effectiveness.")
    if not (effectiveness_check or "").strip():
        errors.append("Effectiveness evidence is required.")
    return errors


def capa_is_overdue(ca: Any, today: Optional[date] = None) -> bool:
    today = today or _today()
    return _v(ca.status) in {"OPEN", "IN_PROGRESS"} and ca.due_date is not None and ca.due_date < today


def concession_decision_errors(concession: Any, actor_id: Any, approve: bool,
                               now: Optional[datetime] = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    errors = []
    if _v(concession.status) != "PENDING":
        errors.append("Only a PENDING concession can be decided.")
    if actor_id == concession.requested_by_id:
        errors.append("The requester cannot decide their own concession.")
    if approve:
        if not (concession.conditions or "").strip():
            errors.append("An approved concession must state its conditions.")
        valid_until = concession.valid_until
        if valid_until is not None and valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)
        if valid_until is None or valid_until <= now:
            errors.append("An approved concession needs a future expiry.")
    return errors


def concession_is_active(concession: Any, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    valid_until = concession.valid_until
    if valid_until is not None and valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    return _v(concession.status) == "APPROVED" and valid_until is not None and valid_until > now


QUALITY_COST_CATEGORIES = ("PREVENTION", "APPRAISAL", "INTERNAL_FAILURE", "EXTERNAL_FAILURE")


def summarize_quality_costs(entries: Iterable[Any]) -> dict:
    by_cat = {c: Decimal("0") for c in QUALITY_COST_CATEGORIES}
    by_risk: dict[str, Decimal] = {}
    currencies = set()
    for e in entries:
        amount = Decimal(str(e.amount))
        by_cat[_v(e.category)] += amount
        if e.risk_level is not None:
            key = _v(e.risk_level)
            by_risk[key] = by_risk.get(key, Decimal("0")) + amount
        currencies.add(e.currency)
    total = sum(by_cat.values(), Decimal("0"))
    copq = by_cat["INTERNAL_FAILURE"] + by_cat["EXTERNAL_FAILURE"]

    def money(v: Decimal) -> str:
        return str(v.quantize(Decimal("0.01")))

    return {
        "by_category": {k: money(v) for k, v in by_cat.items()},
        "by_risk_level": {k: money(v) for k, v in by_risk.items()},
        "cost_of_good_quality": money(by_cat["PREVENTION"] + by_cat["APPRAISAL"]),
        "cost_of_poor_quality": money(copq),
        "total": money(total),
        "copq_share_pct": str(round(copq / total * 100, 2)) if total else None,
        "currencies": sorted(currencies),
        "mixed_currency": len(currencies) > 1,
    }


# ── S04 CoA / retain samples / instruments / training ────────────────────────

def coa_issue_errors(coa: Any, actor_id: Any, inspection: Any = None, lot_status: Any = None) -> list[str]:
    errors = []
    if coa.status != "DRAFT":
        errors.append("Only a DRAFT CoA can be issued.")
    if actor_id == coa.issued_by_id:
        errors.append("The CoA preparer cannot approve its issue.")
    if (coa.overall_result or "").upper() != "PASS":
        errors.append("A CoA can only be issued for a passing result.")
    if inspection is None:
        errors.append("A CoA must reference a QC inspection.")
    else:
        if _v(inspection.status) != "PASSED":
            errors.append("The referenced inspection has not passed.")
        if inspection.lot_id != coa.lot_id:
            errors.append("The referenced inspection is not an inspection of this lot.")
    if lot_status is None:
        errors.append("The lot has no quality release status.")
    elif lot_status.hold_flag or lot_status.quarantine_flag:
        errors.append("The lot is on hold or quarantined.")
    if coa.valid_until is not None and coa.valid_until < coa.issue_date:
        errors.append("valid_until is before the issue date.")
    return errors


def retain_withdraw_errors(sample: Any, quantity: Decimal) -> list[str]:
    errors = []
    if _v(sample.status) != "STORED":
        errors.append("Only a STORED retain sample can be withdrawn from.")
    if quantity <= 0:
        errors.append("Withdrawal quantity must be positive.")
    elif quantity > sample.quantity_remaining:
        errors.append("Withdrawal exceeds the remaining retain quantity.")
    return errors


def retain_dispose_errors(sample: Any, reason: Optional[str], early_authorized: bool,
                          today: Optional[date] = None) -> list[str]:
    today = today or _today()
    errors = []
    if _v(sample.status) == "DISPOSED":
        errors.append("The retain sample is already disposed.")
    if today < sample.retain_until:
        if not early_authorized:
            errors.append("Disposal before the retention date requires quality approval.")
        if not (reason or "").strip():
            errors.append("Early disposal requires a reason.")
    return errors


def retain_samples_due(samples: Iterable[Any], today: Optional[date] = None) -> list[Any]:
    today = today or _today()
    return [s for s in samples if _v(s.status) != "DISPOSED" and s.retain_until < today]


def instrument_usage_errors(instrument: Any, method: Any = None, today: Optional[date] = None) -> list[str]:
    today = today or _today()
    if instrument is None:
        if method is not None and method.requires_instrument:
            return [f"Test method {method.method_code} requires a calibrated instrument."]
        return []
    errors = []
    if not instrument.is_active:
        errors.append(f"Instrument {instrument.instrument_id} is inactive.")
    if instrument.status in {"OVERDUE", "OUT_OF_SERVICE", "NOT_VERIFIED"}:
        errors.append(f"Instrument {instrument.instrument_id} calibration status is {instrument.status}.")
    elif instrument.next_calibration_due is None or instrument.next_calibration_due < today:
        errors.append(f"Instrument {instrument.instrument_id} calibration is past due.")
    if method is not None and method.instrument_type and (
            (instrument.instrument_type or "").strip().lower() != method.instrument_type.strip().lower()):
        errors.append(f"Test method {method.method_code} needs a {method.instrument_type} instrument.")
    return errors


async def tester_skill_errors(db: AsyncSession, user_id: Any, skill_id: Any) -> list[str]:
    """User → employee → operator profile → approved, current skill certificate."""
    if skill_id is None:
        return []
    from app.models.hr import Employee
    from app.models.machine_operator import CertStatus, OperatorProfile, OperatorSkillCert
    from app.services.machine_operator_service import _compute_cert_status

    employee_ids = (await db.execute(select(Employee.id).where(Employee.user_id == user_id))).scalars().all()
    operator_ids = (await db.execute(
        select(OperatorProfile.id).where(OperatorProfile.employee_id.in_(employee_ids),
                                         OperatorProfile.active_flag.is_(True))
    )).scalars().all() if employee_ids else []
    certs = (await db.execute(
        select(OperatorSkillCert).where(OperatorSkillCert.operator_id.in_(operator_ids),
                                        OperatorSkillCert.skill_id == skill_id,
                                        OperatorSkillCert.approved_flag.is_(True))
    )).scalars().all() if operator_ids else []
    for cert in certs:
        status = _compute_cert_status(cert.certification_expiry, cert.certification_required)
        if status in {CertStatus.VALID, CertStatus.EXPIRING_SOON} and _v(cert.cert_status) != "BLOCKED":
            return []
    return ["The tester has no approved, current qualification for this test method."]


# ── S05 audits / change control ──────────────────────────────────────────────

def audit_close_errors(checklist: Any) -> list[str]:
    errors = []
    if checklist.closed_at is not None:
        errors.append("The audit is already closed.")
    pending = [i for i, item in enumerate(checklist.items or []) if item.get("result") not in {"pass", "fail", "na"}]
    if pending:
        errors.append(f"Checklist items {pending} have no result.")
    if not checklist.items:
        errors.append("An audit without checklist items cannot be closed.")
    return errors


def audit_failed_items(checklist: Any) -> list[dict]:
    return [item for item in (checklist.items or []) if item.get("result") == "fail"]


CHANGE_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"IMPLEMENTED"},
    "IMPLEMENTED": {"CLOSED"},
    "REJECTED": set(), "CANCELLED": set(), "CLOSED": set(),
}


def change_request_transition_errors(cr: Any, target: str, actor_id: Any, notes: Optional[str] = None) -> list[str]:
    cur = _v(cr.status)
    if target not in CHANGE_TRANSITIONS.get(cur, set()):
        return [f"A change request cannot move from {cur} to {target}."]
    errors = []
    if target == "SUBMITTED" and not (cr.risk_assessment or "").strip():
        errors.append("A risk assessment is required before submission.")
    if target in {"APPROVED", "REJECTED"} and actor_id == cr.requested_by_id:
        errors.append("The requester cannot decide their own change request.")
    if target == "CLOSED" and not (notes or cr.verification_notes or "").strip():
        errors.append("Closing a change request requires verification notes.")
    return errors


def new_reference(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
