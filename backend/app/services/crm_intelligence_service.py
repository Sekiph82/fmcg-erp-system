"""M36.S02 sales intelligence on the native CRM: explainable lead scoring, filtered weighted forecasts
with snapshots, and funnel analytics (stage conversion, aging, rep performance, loss reasons)."""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crm import (
    CRMActivityResult, CRMForecastSnapshot, CRMPipelineStage, CRMRecord, CRMRecordType, CRMScoreHistory,
    CRMScoreRule, CRMStageHistory, CRMStatus, CRMTemperature, CRMWinLoss,
)

# ── Lead scoring ──────────────────────────────────────────────────────────────


def _enum(value: Any) -> Optional[str]:
    return getattr(value, "value", value)


def _completed(record: CRMRecord) -> int:
    return sum(1 for a in (record.activities or []) if a.result_status == CRMActivityResult.COMPLETED)


# field -> (value getter, kind). kind: text | number | bool | count
SCORE_FIELDS: dict[str, tuple[Callable[[CRMRecord], Any], str]] = {
    "source_type": (lambda r: _enum(r.source_type), "text"),
    "industry_segment": (lambda r: r.industry_segment, "text"),
    "channel_id": (lambda r: r.channel_id, "text"),
    "region_id": (lambda r: r.region_id, "text"),
    "expected_revenue": (lambda r: Decimal(str(r.expected_revenue or 0)), "number"),
    "qualified_flag": (lambda r: bool(r.qualified_flag), "bool"),
    "has_next_action": (lambda r: r.next_action_date is not None, "bool"),
    "completed_activities": (_completed, "count"),
    "interest_lines": (lambda r: len(r.interest_lines or []), "count"),
}
OPERATORS = {"eq", "in", "gt", "gte", "lte", "true", "per_item"}


@dataclass
class Rule:
    name: str
    category: str
    field: str
    operator: str
    value: Optional[str]
    points: int
    max_points: Optional[int] = None


# Built-in defaults (used until an admin defines rules); same intent as the former fixed formula,
# with its source bonus fixed (it compared str(enum) to raw names and never matched).
DEFAULT_RULES = [
    Rule("Warm source (referral, inbound, field sales)", "FIT", "source_type", "in", "REFERRAL,INBOUND,FIELD_SALES", 20),
    Rule("Qualified", "FIT", "qualified_flag", "true", None, 20),
    Rule("Expected revenue above 100,000", "FIT", "expected_revenue", "gt", "100000", 10),
    Rule("Expected revenue above 500,000", "FIT", "expected_revenue", "gt", "500000", 5),
    Rule("Completed activities", "ENGAGEMENT", "completed_activities", "per_item", None, 5, 30),
    Rule("Next action planned", "ENGAGEMENT", "has_next_action", "true", None, 5),
    Rule("Products of interest", "ENGAGEMENT", "interest_lines", "per_item", None, 3, 10),
]


def validate_rule(field: str, operator: str, value: Optional[str]) -> None:
    if field not in SCORE_FIELDS:
        raise ValueError(f"field must be one of {sorted(SCORE_FIELDS)}")
    if operator not in OPERATORS:
        raise ValueError(f"operator must be one of {sorted(OPERATORS)}")
    kind = SCORE_FIELDS[field][1]
    allowed = {"text": {"eq", "in"}, "number": {"gt", "gte", "lte"}, "bool": {"true"}, "count": {"per_item", "gte"}}[kind]
    if operator not in allowed:
        raise ValueError(f"{field} supports operators {sorted(allowed)}")
    if operator in {"gt", "gte", "lte"}:
        try:
            finite = Decimal(str(value)).is_finite()
        except Exception as exc:
            raise ValueError("value must be a number") from exc
        if not finite:
            raise ValueError("value must be a finite number")
    if operator in {"eq", "in"} and not (value or "").strip():
        raise ValueError("value is required")


def _evaluate(rule: Rule, record: CRMRecord) -> tuple[int, str]:
    actual = SCORE_FIELDS[rule.field][0](record)
    op, value = rule.operator, rule.value
    if op == "per_item":
        pts = int(actual) * rule.points
        if rule.max_points is not None:
            pts = min(pts, rule.max_points)
        return pts, f"{actual} x {rule.points}" + (f" (cap {rule.max_points})" if rule.max_points is not None else "")
    if op == "true":
        hit = bool(actual)
    elif op == "eq":
        hit = actual is not None and str(actual).upper() == str(value).strip().upper()
    elif op == "in":
        hit = actual is not None and str(actual).upper() in {v.strip().upper() for v in str(value).split(",")}
    else:
        if actual is None:
            return 0, "no value"
        limit = Decimal(str(value))
        hit = {"gt": actual > limit, "gte": actual >= limit, "lte": actual <= limit}[op]
    return (rule.points if hit else 0), f"{rule.field}={actual}"


def temperature_for(score: int) -> CRMTemperature:
    return CRMTemperature.HOT if score >= 70 else CRMTemperature.WARM if score >= 40 else CRMTemperature.COLD


def compute_score(record: CRMRecord, rules: Iterable[Rule]) -> tuple[int, CRMTemperature, list[dict]]:
    breakdown, total = [], 0
    for rule in rules:
        pts, reason = _evaluate(rule, record)
        total += pts
        breakdown.append({"rule": rule.name, "category": rule.category, "points": pts, "reason": reason})
    score = max(0, min(100, total))
    return score, temperature_for(score), breakdown


async def active_rules(db: AsyncSession) -> list[Rule]:
    rows = (await db.execute(select(CRMScoreRule).where(CRMScoreRule.active_flag.is_(True))
                             .order_by(CRMScoreRule.sequence_no, CRMScoreRule.name))).scalars().all()
    if not rows:
        return list(DEFAULT_RULES)
    return [Rule(r.name, r.category, r.field, r.operator, r.value, r.points, r.max_points) for r in rows]


async def _records_for_scoring(db: AsyncSession, where) -> list[CRMRecord]:
    return list((await db.execute(select(CRMRecord).where(where).options(
        selectinload(CRMRecord.activities), selectinload(CRMRecord.interest_lines)))).scalars().all())


async def _scored_ids(db: AsyncSession, ids: list) -> set:
    if not ids:
        return set()
    return set((await db.execute(select(CRMScoreHistory.crm_record_id).where(
        CRMScoreHistory.crm_record_id.in_(ids)).distinct())).scalars())


async def rescore(db: AsyncSession, record: CRMRecord, rules: list[Rule], actor: Optional[str],
                  has_history: bool) -> bool:
    """Apply the rules to one loaded record; write history when the score or temperature changes."""
    score, temperature, breakdown = compute_score(record, rules)
    changed = score != (record.lead_score or 0) or temperature != record.temperature
    if changed or not has_history:
        db.add(CRMScoreHistory(crm_record_id=record.id, previous_score=record.lead_score, score=score,
                               temperature=temperature.value, breakdown=json.dumps(breakdown),
                               computed_at=datetime.now(timezone.utc), computed_by=actor))
    record.lead_score, record.temperature = score, temperature
    return changed


async def rescore_record(db: AsyncSession, record_id: str, actor: Optional[str]) -> Optional[CRMRecord]:
    records = await _records_for_scoring(db, CRMRecord.id == uuid.UUID(str(record_id)))
    if not records:
        return None
    await rescore(db, records[0], await active_rules(db), actor, bool(await _scored_ids(db, [records[0].id])))
    await db.commit()
    return records[0]


async def rescore_all(db: AsyncSession, actor: Optional[str]) -> dict:
    rules = await active_rules(db)
    records = await _records_for_scoring(db, CRMRecord.status == CRMStatus.OPEN)
    scored = await _scored_ids(db, [r.id for r in records])
    changed = 0
    for record in records:
        changed += await rescore(db, record, rules, actor, record.id in scored)
    await db.commit()
    return {"scored": len(records), "changed": changed, "rules": len(rules)}


async def score_history(db: AsyncSession, record_id: str, limit: int = 50) -> list[dict]:
    rows = (await db.execute(select(CRMScoreHistory).where(CRMScoreHistory.crm_record_id == uuid.UUID(str(record_id)))
                             .order_by(CRMScoreHistory.computed_at.desc()).limit(limit))).scalars().all()
    return [{"score": r.score, "previous_score": r.previous_score, "temperature": r.temperature,
             "breakdown": json.loads(r.breakdown), "computed_at": r.computed_at.isoformat(),
             "computed_by": r.computed_by} for r in rows]


async def score_queue_candidates(db: AsyncSession, limit: int, offset: int = 0) -> list[tuple[CRMRecord, Optional[list]]]:
    """Open leads, highest score first, each with the breakdown of its latest score."""
    records = (await db.execute(select(CRMRecord).where(
        CRMRecord.status == CRMStatus.OPEN, CRMRecord.record_type == CRMRecordType.LEAD)
        .order_by(CRMRecord.lead_score.desc().nullslast(), CRMRecord.created_at, CRMRecord.id)
        .offset(offset).limit(limit))).scalars().all()
    latest: dict = {}
    if records:
        for h in (await db.execute(select(CRMScoreHistory).where(
                CRMScoreHistory.crm_record_id.in_([r.id for r in records]))
                .order_by(CRMScoreHistory.computed_at))).scalars():
            latest[h.crm_record_id] = json.loads(h.breakdown)
    return [(r, latest.get(r.id)) for r in records]


# ── Forecast ──────────────────────────────────────────────────────────────────

def _month(d: date) -> str:
    return d.strftime("%Y-%m")


def _month_keys(start: date, months: int) -> list[str]:
    keys = []
    for i in range(months):
        m = start.month - 1 + i
        keys.append(f"{start.year + m // 12}-{m % 12 + 1:02d}")
    return keys


async def forecast_detail(db: AsyncSession, months_ahead: int = 6, assigned_rep_id: Optional[str] = None,
                          territory_id: Optional[str] = None, stage_id: Optional[str] = None,
                          start: Optional[date] = None) -> dict:
    """Open opportunities by expected-close month and currency (never summed across currencies)."""
    start = (start or date.today()).replace(day=1)
    months = _month_keys(start, max(1, min(months_ahead, 24)))
    q = select(CRMRecord, CRMPipelineStage.stage_name).outerjoin(
        CRMPipelineStage, CRMPipelineStage.id == CRMRecord.stage_id).where(
        CRMRecord.status == CRMStatus.OPEN, CRMRecord.expected_close_date.isnot(None))
    if assigned_rep_id:
        q = q.where(CRMRecord.assigned_rep_id == assigned_rep_id)
    if territory_id:
        q = q.where(CRMRecord.territory_id == uuid.UUID(territory_id))
    if stage_id:
        q = q.where(CRMRecord.stage_id == uuid.UUID(stage_id))
    cells: dict = defaultdict(lambda: {"expected": Decimal("0"), "weighted": Decimal("0"), "count": 0})
    stages: dict = defaultdict(lambda: {"expected": Decimal("0"), "weighted": Decimal("0"), "count": 0})
    overdue: dict = defaultdict(lambda: {"expected": Decimal("0"), "weighted": Decimal("0"), "count": 0})
    for record, stage_name in (await db.execute(q)).all():
        rev = Decimal(str(record.expected_revenue or 0))
        weighted = rev * Decimal(str(record.probability_pct or 0)) / 100
        currency = (record.currency or "KES").upper()
        month = _month(record.expected_close_date)
        if month < months[0]:
            bucket = overdue[currency]  # close date already passed but still open
        elif month in months:
            bucket = cells[(month, currency)]
            st = stages[(stage_name or "No stage", currency)]
            st["expected"] += rev
            st["weighted"] += weighted
            st["count"] += 1
        else:
            continue
        bucket["expected"] += rev
        bucket["weighted"] += weighted
        bucket["count"] += 1

    def out(v):
        return {"expected_revenue": float(v["expected"]), "weighted_revenue": float(v["weighted"].quantize(Decimal("0.01"))),
                "deal_count": v["count"]}

    currencies = sorted({c for (_, c) in cells} | {c for (_, c) in stages} | set(overdue))
    return {
        "filters": {"months_ahead": len(months), "start": months[0], "assigned_rep_id": assigned_rep_id,
                    "territory_id": territory_id, "stage_id": stage_id},
        "currencies": currencies,
        "rows": [{"month": m, "currency": c, **out(cells[(m, c)])} for m in months for c in currencies],
        "by_stage": [{"stage": s, "currency": c, **out(v)} for (s, c), v in sorted(stages.items())],
        "overdue_open": [{"currency": c, **out(v)} for c, v in sorted(overdue.items())],
    }


async def save_snapshot(db: AsyncSession, detail: dict, label: Optional[str], user_id) -> CRMForecastSnapshot:
    snap = CRMForecastSnapshot(label=(label or None) and label[:150], filters=json.dumps(detail["filters"]),
                               rows=json.dumps({k: detail[k] for k in ("currencies", "rows", "by_stage", "overdue_open")}),
                               taken_at=datetime.now(timezone.utc), taken_by_id=user_id)
    db.add(snap)
    await db.commit()
    return snap


def snapshot_out(s: CRMForecastSnapshot, with_rows: bool = False) -> dict:
    out = {"id": str(s.id), "label": s.label, "filters": json.loads(s.filters), "taken_at": s.taken_at.isoformat()}
    if with_rows:
        out.update(json.loads(s.rows))
    return out


# ── Funnel analytics ─────────────────────────────────────────────────────────

async def funnel(db: AsyncSession, date_from: Optional[date] = None, date_to: Optional[date] = None,
                 assigned_rep_id: Optional[str] = None, territory_id: Optional[str] = None) -> dict:
    """Records created in [date_from, date_to]: how far they got, how long open ones sit, who wins them."""
    q = select(CRMRecord).options(selectinload(CRMRecord.win_loss))
    if date_from:
        q = q.where(CRMRecord.created_at >= datetime.combine(date_from, datetime.min.time(), timezone.utc))
    if date_to:
        q = q.where(CRMRecord.created_at < datetime.combine(date_to, datetime.min.time(), timezone.utc)
                    + _one_day())
    if assigned_rep_id:
        q = q.where(CRMRecord.assigned_rep_id == assigned_rep_id)
    if territory_id:
        q = q.where(CRMRecord.territory_id == uuid.UUID(territory_id))
    records = list((await db.execute(q)).scalars().all())
    stages = list((await db.execute(select(CRMPipelineStage).where(
        CRMPipelineStage.active_flag.is_(True)).order_by(CRMPipelineStage.sequence_no))).scalars().all())
    seq = {s.id: s.sequence_no for s in stages if _enum(s.stage_type) in ("LEAD", "OPPORTUNITY")}
    history: dict = defaultdict(list)
    if records:
        for h in (await db.execute(select(CRMStageHistory).where(
                CRMStageHistory.crm_record_id.in_([r.id for r in records]))
                .order_by(CRMStageHistory.changed_at))).scalars():
            history[h.crm_record_id].append(h)
    now = datetime.now(timezone.utc)

    furthest: dict = {}
    for r in records:
        reached = [seq[h.to_stage_id] for h in history[r.id] if h.to_stage_id in seq]
        if r.stage_id in seq:
            reached.append(seq[r.stage_id])
        furthest[r.id] = max(reached) if reached else None

    funnel_rows, previous = [], None
    for s in stages:
        if _enum(s.stage_type) not in ("LEAD", "OPPORTUNITY"):
            continue  # terminal, on-hold and nurturing stages are not funnel steps
        count = sum(1 for r in records if (furthest[r.id] is not None and furthest[r.id] >= s.sequence_no)
                    or r.status == CRMStatus.WON)
        funnel_rows.append({"stage_id": str(s.id), "stage": s.stage_name, "sequence": s.sequence_no, "reached": count,
                            "conversion_from_previous_pct": round(count * 100 / previous, 1) if previous else None})
        previous = count or None

    aging: dict = defaultdict(list)
    for r in records:
        if r.status != CRMStatus.OPEN or r.stage_id is None:
            continue
        entered = next((h.changed_at for h in reversed(history[r.id]) if h.to_stage_id == r.stage_id), r.created_at)
        aging[r.stage_id].append((now - _aware(entered)).days)
    names = {s.id: s.stage_name for s in stages}
    aging_rows = [{"stage": names.get(sid, "Inactive stage"), "open": len(d), "avg_days": round(sum(d) / len(d), 1),
                   "max_days": max(d), "over_30_days": sum(1 for x in d if x > 30)} for sid, d in aging.items()]

    reps: dict = defaultdict(lambda: {"total": 0, "open": 0, "won": 0, "lost": 0,
                                      "won_revenue": defaultdict(Decimal), "cycle_days": []})
    reasons: dict = defaultdict(int)
    for r in records:
        rep = reps[r.assigned_rep_id or "UNASSIGNED"]
        rep["total"] += 1
        if r.status == CRMStatus.OPEN:
            rep["open"] += 1
        elif r.status in (CRMStatus.WON, CRMStatus.LOST):
            rep["won" if r.status == CRMStatus.WON else "lost"] += 1
            wl: Optional[CRMWinLoss] = r.win_loss
            if r.status == CRMStatus.WON:
                rep["won_revenue"][(r.currency or "KES").upper()] += Decimal(
                    str((wl.final_revenue if wl else None) or r.expected_revenue or 0))
            if wl and wl.close_date and r.created_at:
                rep["cycle_days"].append((wl.close_date - _aware(r.created_at).date()).days)
            if r.status == CRMStatus.LOST:
                reasons[_enum(wl.loss_reason_code) if wl and wl.loss_reason_code else "UNSPECIFIED"] += 1
    rep_rows = [{"assigned_rep_id": k, "total": v["total"], "open": v["open"], "won": v["won"], "lost": v["lost"],
                 "win_rate_pct": round(v["won"] * 100 / (v["won"] + v["lost"]), 1) if v["won"] + v["lost"] else None,
                 "won_revenue_by_currency": {c: float(a) for c, a in sorted(v["won_revenue"].items())},
                 "avg_cycle_days": round(sum(v["cycle_days"]) / len(v["cycle_days"]), 1) if v["cycle_days"] else None}
                for k, v in sorted(reps.items())]
    return {"filters": {"date_from": date_from and date_from.isoformat(), "date_to": date_to and date_to.isoformat(),
                        "assigned_rep_id": assigned_rep_id, "territory_id": territory_id},
            "records": len(records), "funnel": funnel_rows, "aging": aging_rows, "reps": rep_rows,
            "loss_reasons": [{"reason": k, "count": v} for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])]}


def _one_day():
    from datetime import timedelta

    return timedelta(days=1)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
