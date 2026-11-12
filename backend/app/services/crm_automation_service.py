"""M36.S01.T004 CRM workflow automation on the native rule store (`cf_workflow_rules`, entity crm_record).

Events come from `crm_stage_history`, which is written for every CRM record write (created, stage
changed, won, lost, status changed). For each matching active rule a `crm_automation_runs` row is
inserted with ON CONFLICT DO NOTHING on (rule, event), so the same event never runs a rule twice even
with several API workers or restarts. Runs are claimed with FOR UPDATE SKIP LOCKED, executed inside a
savepoint and retried with backoff (5 attempts). Actions never change stage or status, so an action
cannot trigger another rule (no recursion); a per-record hourly cap stops runaway rule sets."""
from __future__ import annotations

import asyncio
import logging
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import (
    CRMActivity, CRMActivityType, CRMAutomationRun, CRMPipelineStage, CRMRecord, CRMStageHistory, CRMTemperature,
)
from app.models.custom_fields import EntityType, WorkflowTriggerRule

logger = logging.getLogger(__name__)

TRIGGERS = ("created", "stage_changed", "won", "lost", "status_changed")
ACTIONS = ("create_task", "assign_owner", "set_field", "notify")
CONDITION_FIELDS = ("to_stage_code", "record_type", "source_type", "temperature", "assigned_rep_id",
                    "industry_segment", "expected_revenue")
SETTABLE = {"temperature": [t.value for t in CRMTemperature], "next_action_days": None, "probability_pct": None}
MAX_ATTEMPTS = 5
LOOKBACK = timedelta(days=7)
PER_RECORD_HOURLY_CAP = 50
WATERMARK_OVERLAP = timedelta(seconds=60)


def validate(trigger: str, condition_field: Optional[str], operator: Optional[str], action_type: str,
             payload: dict) -> None:
    if trigger not in TRIGGERS:
        raise ValueError(f"trigger_event must be one of {TRIGGERS}")
    if condition_field and condition_field not in CONDITION_FIELDS:
        raise ValueError(f"condition_field must be one of {CONDITION_FIELDS}")
    if condition_field and operator not in ("eq", "in", "gte"):
        raise ValueError("condition_operator must be eq, in or gte")
    if action_type not in ACTIONS:
        raise ValueError(f"action_type must be one of {ACTIONS}")
    if action_type == "create_task":
        if not str(payload.get("subject") or "").strip():
            raise ValueError("create_task needs a subject")
        if not 0 <= int(payload.get("due_in_days", 1)) <= 365:
            raise ValueError("due_in_days must be 0..365")
    elif action_type == "assign_owner":
        reps = payload.get("rep_ids")
        if not isinstance(reps, list) or not reps or not all(isinstance(r, str) and r.strip() for r in reps):
            raise ValueError("assign_owner needs rep_ids (non-empty list)")
    elif action_type == "set_field":
        field, value = payload.get("field"), payload.get("value")
        if field not in SETTABLE:
            raise ValueError(f"set_field field must be one of {sorted(SETTABLE)} (stage and status are never set)")
        if field == "temperature" and value not in SETTABLE["temperature"]:
            raise ValueError("temperature must be HOT, WARM or COLD")
        if field == "next_action_days" and not (isinstance(value, int) and 0 <= value <= 365):
            raise ValueError("next_action_days must be 0..365")
        if field == "probability_pct" and not (isinstance(value, (int, float)) and 0 <= value <= 100):
            raise ValueError("probability_pct must be 0..100")
    elif action_type == "notify":
        users = payload.get("usernames")
        if not isinstance(users, list) or not users or not all(isinstance(u, str) for u in users) \
                or not isinstance(payload.get("title"), str) or not payload["title"].strip():
            raise ValueError("notify needs usernames (list of strings) and a title")


async def check_recipients(db: AsyncSession, payload: dict) -> None:
    """Notify only active users who may see CRM records company-wide (the message names the record)."""
    from sqlalchemy.orm import selectinload

    from app.core.access_control import has_any_permission
    from app.models.role import Role
    from app.models.user import User

    names = payload.get("usernames") or []
    users = (await db.execute(select(User).where(User.username.in_(names), User.is_active.is_(True))
                              .options(selectinload(User.roles).selectinload(Role.permissions)))).scalars().all()
    found = {u.username: u for u in users}
    bad = [n for n in names if n not in found or not has_any_permission(found[n], ("crm.view", "crm.view_all"))]
    if bad:
        raise ValueError(f"not active users with company-wide CRM view: {', '.join(bad)}")


def _events(h: CRMStageHistory) -> list[str]:
    if h.from_status is None and h.from_stage_id is None:
        return ["created"]
    out = []
    if h.from_stage_id != h.to_stage_id:
        out.append("stage_changed")
    if h.from_status != h.to_status:
        out.append("status_changed")
        if h.to_status in ("WON", "LOST"):
            out.append(h.to_status.lower())
    return out


def _matches(rule: WorkflowTriggerRule, record: CRMRecord, stage_code: Optional[str]) -> bool:
    if not rule.condition_field:
        return True
    actual = stage_code if rule.condition_field == "to_stage_code" else getattr(record, rule.condition_field, None)
    actual = getattr(actual, "value", actual)
    value = rule.condition_value or ""
    if rule.condition_operator == "in":
        return str(actual).upper() in {v.strip().upper() for v in value.split(",")}
    if rule.condition_operator == "gte":
        try:
            return actual is not None and float(actual) >= float(value)
        except ValueError:
            return False
    return actual is not None and str(actual).upper() == value.strip().upper()


async def enqueue(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Create PENDING runs for new events of active CRM rules. Safe to call concurrently."""
    now = now or datetime.now(timezone.utc)
    rules = (await db.execute(select(WorkflowTriggerRule).where(
        WorkflowTriggerRule.entity_type == EntityType.CRM_RECORD, WorkflowTriggerRule.active_flag.is_(True),
        WorkflowTriggerRule.trigger_event.in_(TRIGGERS)))).scalars().all()
    if not rules:
        return 0
    start = {}  # per rule: never before activation; otherwise from the watermark (overlap covers late commits)
    for r in rules:
        active_from = _aware(r.activated_at or r.created_at)
        mark = _aware(r.enqueued_until) - WATERMARK_OVERLAP if r.enqueued_until else active_from
        start[r.rule_id] = (active_from, max(active_from, mark, now - LOOKBACK))
    rows = (await db.execute(
        select(CRMStageHistory, CRMRecord, CRMPipelineStage.stage_code)
        .join(CRMRecord, CRMRecord.id == CRMStageHistory.crm_record_id)
        .outerjoin(CRMPipelineStage, CRMPipelineStage.id == CRMStageHistory.to_stage_id)
        .where(CRMStageHistory.changed_at >= min(v[1] for v in start.values())))).all()
    created = 0
    for h, record, stage_code in rows:
        for event in _events(h):
            for rule in rules:
                active_from, window = start[rule.rule_id]
                at = _aware(h.changed_at)
                if rule.trigger_event != event or at < active_from or at < window:
                    continue  # paused, edited or new rules do not replay older events
                if not _matches(rule, record, stage_code):
                    continue
                res = await db.execute(insert(CRMAutomationRun).values(
                    rule_id=rule.rule_id, rule_name=rule.rule_name, event_key=f"{event}:{h.id}", event_type=event,
                    crm_record_id=record.id, status="PENDING", attempts=0, next_attempt_at=now, created_at=now,
                ).on_conflict_do_nothing(constraint="uq_crm_automation_rule_event"))
                created += res.rowcount or 0
    for rule in rules:
        rule.enqueued_until = now
    await db.commit()
    return created


async def _act(db: AsyncSession, rule: WorkflowTriggerRule, record: CRMRecord, now: datetime) -> str:
    payload = rule.action_payload or {}
    kind = rule.action_type
    if kind == "create_task":
        due = now + timedelta(days=int(payload.get("due_in_days", 1)))
        db.add(CRMActivity(crm_record_id=record.id, activity_type=CRMActivityType.TASK,
                           subject=str(payload["subject"])[:300], due_datetime=due.replace(tzinfo=None),
                           assigned_to=record.assigned_rep_id, created_by="automation"))
        return f"task '{payload['subject']}' due {due.date()}"
    if kind == "assign_owner":
        if record.assigned_rep_id and not payload.get("overwrite"):
            return f"kept owner {record.assigned_rep_id}"
        reps = payload["rep_ids"]
        record.assigned_rep_id = reps[zlib.crc32(str(record.id).encode()) % len(reps)]  # stable spread over reps
        return f"assigned to {record.assigned_rep_id}"
    if kind == "set_field":
        field, value = payload["field"], payload["value"]
        if field == "temperature":
            record.temperature = CRMTemperature(value)
        elif field == "next_action_days":
            record.next_action_date = (now + timedelta(days=int(value))).date()
        else:
            record.probability_pct = value
            record.probability_override = True
        return f"{field} = {value}"
    if kind == "notify":
        from app.models.notifications import Notification, NotificationType
        from app.models.user import User

        users = (await db.execute(select(User).where(User.username.in_(payload["usernames"]),
                                                     User.is_active.is_(True)))).scalars().all()
        for u in users:
            db.add(Notification(user_id=str(u.id), user_name=u.full_name, title=str(payload["title"])[:300],
                                message=str(payload.get("message") or record.company_name)[:2000],
                                notification_type=NotificationType.REMINDER, reference_type="crm_record",
                                reference_id=str(record.id), module="crm"))
        if not users:
            raise ValueError("none of the usernames is an active user")
        return f"notified {', '.join(u.username for u in users)}"
    raise ValueError(f"unknown action {kind}")


async def process(db: AsyncSession, limit: int = 50, now: Optional[datetime] = None) -> dict:
    """Claim and run due PENDING runs (SKIP LOCKED: concurrent workers take different rows)."""
    now = now or datetime.now(timezone.utc)
    runs = (await db.execute(select(CRMAutomationRun).where(
        CRMAutomationRun.status == "PENDING", CRMAutomationRun.next_attempt_at <= now)
        .order_by(CRMAutomationRun.created_at).limit(limit).with_for_update(skip_locked=True))).scalars().all()
    counts = {"done": 0, "failed": 0, "retry": 0, "skipped": 0}
    for run in runs:
        rule = (await db.execute(select(WorkflowTriggerRule).where(WorkflowTriggerRule.rule_id == run.rule_id))).scalar_one_or_none()
        record = await db.get(CRMRecord, run.crm_record_id)
        recent = (await db.execute(select(func.count()).where(
            CRMAutomationRun.crm_record_id == run.crm_record_id, CRMAutomationRun.status == "DONE",
            CRMAutomationRun.finished_at >= now - timedelta(hours=1)))).scalar()
        if rule is not None and rule.active_flag and record is not None and recent >= PER_RECORD_HOURLY_CAP:
            run.next_attempt_at = now + timedelta(hours=1)  # deferred, not dropped
            run.result = "hourly cap per record reached; deferred"
            counts["retry"] += 1
            continue
        if rule is None or not rule.active_flag or record is None:
            run.status, run.finished_at = "SKIPPED", now
            run.result = "rule inactive or deleted" if record is not None else "record deleted"
            counts["skipped"] += 1
            continue
        run.attempts += 1
        try:
            async with db.begin_nested():
                run.result = await _act(db, rule, record, now)
            run.status, run.finished_at, run.error = "DONE", now, None
            counts["done"] += 1
        except Exception as exc:  # recorded on the run; retried with backoff, then FAILED
            run.error = f"{exc.__class__.__name__}: {exc}"[:1000]
            if run.attempts >= MAX_ATTEMPTS:
                run.status, run.finished_at = "FAILED", now
                counts["failed"] += 1
            else:
                run.next_attempt_at = now + timedelta(minutes=2 ** run.attempts)
                counts["retry"] += 1
    await db.commit()
    return counts


async def run_crm_automation(interval: float = 15.0) -> None:
    """Lifespan task: enqueue and process automation runs; errors are logged, the loop keeps going."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await enqueue(db)
                await process(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("CRM automation tick failed")
        await asyncio.sleep(interval)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
