"""Visual workflow designer engine (M36.S03.T004).

A workflow is a versioned graph: one trigger node (a CRM event), then condition (yes/no branches), delay, approval
(a manager approves or rejects → branch) and action nodes (the same safe actions as CRM automation), ending in end
nodes. Only PUBLISHED versions run; publishing archives the previous one and an older version can be re-published
(rollback). Validation refuses cycles, unreachable nodes, missing branches and invalid action settings. Simulation
walks the graph against a real record without changing anything.

Runs start from new CRM events (stage history after the version was published), advance node by node, wait on
delays (resume time) and approvals, and record every step in the run log.

M47.S01.T008 adds three trigger kinds besides CRM events:
- "scheduled": daily / weekly at a local time, or relative to a date property of the record (N days before/after,
  e.g. expected close date). Each tick enrols the open records matching the optional filter once per occurrence:
  the run's event key names the occurrence and the record, and (version, event key) is unique (the idempotent ledger).
  Only the latest occurrence is considered (a server down for several days does not replay every missed one).
- "inbound_webhook": a random token (shown once, stored as SHA-256) lets a system POST {event_id, record_id|email};
  the event id is the event key, so a replayed call enrols once.
- "web_event": a defined custom website event of an identified visitor (marketing consent) enrols the CRM record
  whose contact e-mail is the visitor's.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMPipelineStage, CRMRecord, CRMStageHistory, CRMWorkflow, CRMWorkflowRun, CRMWorkflowVersion
from app.services import crm_automation_service as auto

NODE_TYPES = ("trigger", "condition", "delay", "approval", "action", "end")
MAX_NODES = 60
MAX_STEPS_PER_TICK = 25
MAX_RUNS_PER_RECORD_HOUR = 10   # runaway protection: a record flipping stages does not fire endlessly
EXTRA_TRIGGERS = ("scheduled", "inbound_webhook", "web_event")   # M47.S01.T008 (designer only, not the rule store)
WORKFLOW_TRIGGERS = (*auto.TRIGGERS, *EXTRA_TRIGGERS)
SCHEDULE_KINDS = ("daily", "weekly", "relative")
DATE_PROPERTIES = ("expected_close_date", "next_action_date", "qualified_date", "converted_date")
DEFAULT_TZ = "Africa/Nairobi"
MAX_SCHEDULED_PER_OCCURRENCE = 500
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
EVENT_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


class WorkflowError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(str(detail))
        self.status, self.detail = status, detail


def validate(graph: dict) -> list[str]:
    """Problems with the graph (empty list = valid)."""
    errs: list[str] = []
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    edges = graph.get("edges") if isinstance(graph, dict) else None
    if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes:
        return ["The workflow needs nodes and connections."]
    if len(nodes) > MAX_NODES:
        return [f"At most {MAX_NODES} steps."]
    if not all(isinstance(n, dict) and isinstance(n.get("config", {}) or {}, dict) for n in nodes) or not all(isinstance(e, dict) for e in edges):
        return ["Steps and connections must be objects."]
    ids = [n.get("id") for n in nodes]
    if not all(isinstance(i, str) and 0 < len(i) <= 40 for i in ids) or len(set(ids)) != len(ids):
        return ["Every step needs a unique id of at most 40 characters."]
    by = {n.get("id"): n for n in nodes}
    triggers = [n for n in nodes if n.get("type") == "trigger"]
    if len(triggers) != 1:
        errs.append("Exactly one trigger step is required.")
    for n in nodes:
        t, cfg = n.get("type"), n.get("config") or {}
        if t not in NODE_TYPES:
            errs.append(f"{n.get('id')}: unknown step type {t}.")
            continue
        if t == "trigger":
            if cfg.get("event") not in WORKFLOW_TRIGGERS:
                errs.append(f"{n['id']}: trigger event must be one of {', '.join(WORKFLOW_TRIGGERS)}.")
            elif cfg["event"] == "scheduled":
                errs += [f"{n['id']}: {p}" for p in schedule_problems(cfg.get("schedule"))]
            elif cfg["event"] == "web_event" and not EVENT_NAME_RE.fullmatch(str(cfg.get("name") or "")):
                errs.append(f"{n['id']}: a web event trigger needs the name of a defined event.")
        if t == "condition":
            if cfg.get("field") not in auto.CONDITION_FIELDS or cfg.get("operator") not in ("eq", "in", "gte"):
                errs.append(f"{n['id']}: condition needs a field ({', '.join(auto.CONDITION_FIELDS)}) and operator eq/in/gte.")
        if t == "delay":
            if not isinstance(cfg.get("days"), int) or not 0 <= cfg["days"] <= 365:
                errs.append(f"{n['id']}: delay days must be 0..365.")
        if t == "approval" and not str(cfg.get("title") or "").strip():
            errs.append(f"{n['id']}: approval needs a title.")
        if t == "action":
            try:
                auto.validate("created", None, None, cfg.get("action_type", ""), cfg.get("payload") or {})
            except (ValueError, TypeError) as e:
                errs.append(f"{n['id']}: {e}")
    out: dict[str, list[tuple[str, Optional[str]]]] = {i: [] for i in by}
    for e in edges:
        a, b, br = e.get("from"), e.get("to"), e.get("branch")
        if a not in by or b not in by:
            errs.append(f"Connection {a} → {b} points to a missing step.")
            continue
        out[a].append((b, br))
    for i, n in by.items():
        t = n.get("type")
        branches = {br for _, br in out.get(i, [])}
        if t in ("condition", "approval"):
            if branches != {"yes", "no"} or len(out[i]) != 2:
                errs.append(f"{i}: needs exactly one 'yes' and one 'no' connection.")
        elif t == "end":
            if out.get(i):
                errs.append(f"{i}: an end step has no outgoing connection.")
        elif t in NODE_TYPES and len(out.get(i, [])) != 1:
            errs.append(f"{i}: needs exactly one outgoing connection.")
    if errs or not triggers:
        return errs
    # cycles and reachability (DFS with colours)
    colour: dict[str, int] = {}

    def dfs(u: str) -> bool:
        colour[u] = 1
        for v, _ in out.get(u, []):
            if colour.get(v) == 1 or (colour.get(v) is None and dfs(v)):
                return True
        colour[u] = 2
        return False
    if dfs(triggers[0]["id"]):
        errs.append("The workflow loops back on itself; loops are not allowed.")
    unreachable = [i for i in by if i not in colour]
    if unreachable:
        errs.append(f"Not reachable from the trigger: {', '.join(sorted(unreachable))}.")
    return errs


def schedule_problems(sch) -> list[str]:
    if not isinstance(sch, dict) or sch.get("kind") not in SCHEDULE_KINDS:
        return [f"schedule kind must be one of {', '.join(SCHEDULE_KINDS)}."]
    errs = []
    if not TIME_RE.fullmatch(str(sch.get("time") or "")):
        errs.append("schedule time must be HH:MM (24 h).")
    try:
        ZoneInfo(str(sch.get("tz") or DEFAULT_TZ))
    except (ZoneInfoNotFoundError, ValueError):
        errs.append("unknown time zone.")
    if sch["kind"] == "weekly" and not (isinstance(sch.get("weekday"), int) and 0 <= sch["weekday"] <= 6):
        errs.append("weekly schedule needs weekday 0 (Monday) .. 6 (Sunday).")
    if sch["kind"] == "relative":
        if sch.get("property") not in DATE_PROPERTIES:
            errs.append(f"relative schedule needs a date property: {', '.join(DATE_PROPERTIES)}.")
        if not (isinstance(sch.get("offset_days"), int) and -365 <= sch["offset_days"] <= 365):
            errs.append("offset_days must be -365..365 (negative = before the date).")
    m = sch.get("match")
    if m and (not isinstance(m, dict) or m.get("field") not in auto.CONDITION_FIELDS or m.get("operator") not in ("eq", "in", "gte")):
        errs.append(f"schedule filter needs a field ({', '.join(auto.CONDITION_FIELDS)}) and operator eq/in/gte.")
    return errs


def occurrence(sch: dict, now: datetime) -> datetime:
    """The latest scheduled instant at or before `now` (UTC)."""
    tz = ZoneInfo(str(sch.get("tz") or DEFAULT_TZ))
    local = now.astimezone(tz)
    hh, mm = (int(x) for x in sch["time"].split(":"))
    at = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if sch["kind"] == "weekly":
        at -= timedelta(days=(at.weekday() - sch["weekday"]) % 7)
        if at > local:
            at -= timedelta(days=7)
    elif at > local:
        at -= timedelta(days=1)
    return at.astimezone(timezone.utc)


def _next(graph: dict, node_id: str, branch: Optional[str] = None) -> Optional[str]:
    for e in graph["edges"]:
        if e["from"] == node_id and (branch is None or e.get("branch") == branch):
            return e["to"]
    return None


def _node(graph: dict, node_id: str) -> dict:
    return next(n for n in graph["nodes"] if n["id"] == node_id)


def _condition(cfg: dict, record: CRMRecord, stage_code: Optional[str]) -> bool:
    rule = SimpleNamespace(condition_field=cfg["field"], condition_operator=cfg["operator"], condition_value=str(cfg.get("value", "")))
    return auto._matches(rule, record, stage_code)


async def _stage_code(db: AsyncSession, record: CRMRecord) -> Optional[str]:
    if not record.stage_id:
        return None
    st = await db.get(CRMPipelineStage, record.stage_id)
    return st.stage_code if st else None


async def simulate(db: AsyncSession, graph: dict, record: CRMRecord, approvals: str = "yes") -> list[dict]:
    """Walk the graph for this record without side effects; approvals are assumed `approvals` (yes/no)."""
    problems = validate(graph)
    if problems:
        raise WorkflowError(422, problems)
    stage = await _stage_code(db, record)
    node = next(n for n in graph["nodes"] if n["type"] == "trigger")
    steps = []
    while node:
        t, cfg = node["type"], node.get("config") or {}
        if t == "trigger":
            steps.append({"node": node["id"], "type": t, "note": f"on {cfg['event']}" + (f" {cfg['name']}" if cfg.get("name") else "")})
            nid = _next(graph, node["id"])
        elif t == "condition":
            ok = _condition(cfg, record, stage)
            steps.append({"node": node["id"], "type": t, "note": f"{cfg['field']} {cfg['operator']} {cfg.get('value')} → {'yes' if ok else 'no'}"})
            nid = _next(graph, node["id"], "yes" if ok else "no")
        elif t == "delay":
            steps.append({"node": node["id"], "type": t, "note": f"wait {cfg['days']} day(s)"})
            nid = _next(graph, node["id"])
        elif t == "approval":
            steps.append({"node": node["id"], "type": t, "note": f"approval '{cfg['title']}' → {approvals} (simulated)"})
            nid = _next(graph, node["id"], approvals)
        elif t == "action":
            steps.append({"node": node["id"], "type": t, "note": f"would {cfg['action_type'].replace('_', ' ')}"})
            nid = _next(graph, node["id"])
        else:
            steps.append({"node": node["id"], "type": "end", "note": "end"})
            nid = None
        node = _node(graph, nid) if nid else None
    return steps


async def recipient_problems(db: AsyncSession, graph: dict) -> list[str]:
    """Notify steps may only name active users with company-wide CRM view (the message names the record)."""
    out = []
    for n in graph.get("nodes", []) if isinstance(graph, dict) else []:
        cfg = n.get("config") or {} if isinstance(n, dict) else {}
        if n.get("type") == "action" and cfg.get("action_type") == "notify":
            try:
                await auto.check_recipients(db, cfg.get("payload") or {})
            except ValueError as e:
                out.append(f"{n['id']}: {e}")
    return out


async def trigger_problems(db: AsyncSession, graph: dict) -> list[str]:
    """A web-event trigger must name an active event definition."""
    trig = next((n for n in graph.get("nodes", []) if isinstance(n, dict) and n.get("type") == "trigger"), None)
    cfg = (trig or {}).get("config") or {}
    if cfg.get("event") == "web_event":
        from app.services.web_analytics_service import definitions
        if cfg.get("name") not in await definitions(db):
            return [f"{trig['id']}: '{cfg.get('name')}' is not an active web event definition."]
    return []


async def publish(db: AsyncSession, version: CRMWorkflowVersion, user) -> None:
    problems = validate(version.graph) or await recipient_problems(db, version.graph) or await trigger_problems(db, version.graph)
    if problems:
        raise WorkflowError(422, problems)
    wf = await db.get(CRMWorkflow, version.workflow_id)
    trig = next(n for n in version.graph["nodes"] if n["type"] == "trigger")
    from sqlalchemy import update
    await db.execute(update(CRMWorkflowVersion).where(  # archive first: at most one published version (unique index)
        CRMWorkflowVersion.workflow_id == wf.id, CRMWorkflowVersion.status == "PUBLISHED",
        CRMWorkflowVersion.id != version.id).values(status="ARCHIVED").execution_options(synchronize_session="fetch"))
    now = datetime.now(timezone.utc)
    version.status, version.published_by_id, version.published_at = "PUBLISHED", user.id, now
    wf.trigger_event, wf.published_version_id, wf.enqueued_until = trig["config"]["event"], version.id, now
    await db.flush()


# ── execution ───────────────────────────────────────────────────────────────────

async def enqueue(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Start runs for CRM events after each published version went live (never replays older events)."""
    now = now or datetime.now(timezone.utc)
    rows = (await db.execute(select(CRMWorkflow, CRMWorkflowVersion).join(
        CRMWorkflowVersion, CRMWorkflowVersion.id == CRMWorkflow.published_version_id))).all()
    created = 0
    for wf, ver in rows:
        try:
            async with db.begin_nested():   # one broken workflow never stops the others
                created += await _enqueue_one(db, wf, ver, now)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("workflow %s enqueue failed", wf.id)
    await db.commit()
    return created


async def start_run(db: AsyncSession, ver: CRMWorkflowVersion, record_id: uuid.UUID, event_key: str,
                    now: datetime) -> Optional[uuid.UUID]:
    """Insert a run unless this (version, event key) already ran or the record hit the hourly cap. Returns the new id."""
    recent = (await db.execute(select(func.count()).select_from(CRMWorkflowRun).where(
        CRMWorkflowRun.version_id == ver.id, CRMWorkflowRun.crm_record_id == record_id,
        CRMWorkflowRun.created_at >= now - timedelta(hours=1)))).scalar_one()
    if recent >= MAX_RUNS_PER_RECORD_HOUR:
        return None
    trig = next(n for n in ver.graph["nodes"] if n["type"] == "trigger")
    res = await db.execute(insert(CRMWorkflowRun).values(
        id=uuid.uuid4(), version_id=ver.id, crm_record_id=record_id, event_key=event_key[:120],
        current_node=_next(ver.graph, trig["id"]), status="RUNNING", resume_at=now, log=[], created_at=now
    ).on_conflict_do_nothing(constraint="uq_crm_workflow_run_event").returning(CRMWorkflowRun.id))
    return res.scalar_one_or_none()


async def _enqueue_one(db: AsyncSession, wf, ver, now: datetime) -> int:
    made = 0
    since = max(auto._aware(ver.published_at), auto._aware(wf.enqueued_until) - auto.WATERMARK_OVERLAP) if wf.enqueued_until else auto._aware(ver.published_at)
    since = max(since, auto._aware(ver.published_at))
    cfg = next(n for n in ver.graph["nodes"] if n["type"] == "trigger").get("config") or {}
    if wf.trigger_event == "scheduled":
        made = await _enqueue_scheduled(db, ver, cfg["schedule"], now)
    elif wf.trigger_event == "web_event":
        made = await _enqueue_web(db, ver, cfg["name"], since, now)
    elif wf.trigger_event in auto.TRIGGERS:   # inbound_webhook runs start from the public endpoint instead
        hist = (await db.execute(select(CRMStageHistory).where(CRMStageHistory.changed_at >= since))).scalars().all()
        for h in hist:
            if wf.trigger_event in auto._events(h):
                made += 1 if await start_run(db, ver, h.crm_record_id, f"{wf.trigger_event}:{h.id}", now) else 0
    wf.enqueued_until = now
    return made


async def _enqueue_scheduled(db: AsyncSession, ver, sch: dict, now: datetime) -> int:
    from app.models.crm import CRMStatus
    occ = occurrence(sch, now)
    if occ < auto._aware(ver.published_at):          # never fire an occurrence from before the version went live
        return 0
    q = select(CRMRecord).where(CRMRecord.status == CRMStatus.OPEN)
    if sch["kind"] == "relative":
        target = occ.astimezone(ZoneInfo(str(sch.get("tz") or DEFAULT_TZ))).date() - timedelta(days=sch["offset_days"])
        q = q.where(getattr(CRMRecord, sch["property"]) == target)
    made, m, last = 0, sch.get("match"), None
    # M47 review: page through every matching record (keyset by id) instead of silently stopping at the first batch;
    # runs are keyed per occurrence + record, so a page that is processed twice enrols nobody twice.
    while True:
        page_q = q.where(CRMRecord.id > last) if last is not None else q
        page = (await db.execute(page_q.order_by(CRMRecord.id).limit(MAX_SCHEDULED_PER_OCCURRENCE))).scalars().all()
        for record in page:
            if m and not _condition(m, record, await _stage_code(db, record)):
                continue
            if sch["kind"] == "relative":
                key = f"rel:{sch['property']}:{getattr(record, sch['property']).isoformat()}:{record.id}"
            else:
                key = f"sched:{occ:%Y%m%dT%H%M}:{record.id}"
            made += 1 if await start_run(db, ver, record.id, key, now) else 0
        if len(page) < MAX_SCHEDULED_PER_OCCURRENCE:
            return made
        last = page[-1].id


async def record_for_email(db: AsyncSession, email: str) -> Optional[uuid.UUID]:
    """The CRM record whose contact e-mail this is (open records first, then the most recently updated)."""
    from app.models.crm import CRMStatus
    if not email or not email.strip():
        return None
    return (await db.execute(select(CRMRecord.id).where(func.lower(CRMRecord.contact_email) == email.strip().lower())
                             .order_by((CRMRecord.status == CRMStatus.OPEN).desc(), CRMRecord.updated_at.desc().nulls_last())
                             .limit(1))).scalar_one_or_none()


async def _enqueue_web(db: AsyncSession, ver, name: str, since: datetime, now: datetime) -> int:
    """Defined custom events of identified visitors (an identity exists only with marketing consent) whose e-mail is
    verified: an unverified link is just a typed address and must not enrol somebody else's record (M47 review)."""
    from app.models.crm import WebEvent, WebIdentity
    from app.services.web_analytics_service import definitions
    if name not in await definitions(db):            # definition deactivated: the trigger pauses
        return 0
    base = select(WebEvent.id, WebIdentity.email).join(
        WebIdentity, WebIdentity.visitor_hash == WebEvent.visitor_hash).where(
        WebEvent.kind == "CUSTOM", WebEvent.name == name, WebEvent.occurred_at >= since,
        WebIdentity.verified_at.is_not(None))
    made, last = 0, None
    while True:   # M47 review: page through all events (keyset by id) — nothing is dropped before the watermark moves
        rows = (await db.execute((base.where(WebEvent.id > last) if last is not None else base).order_by(WebEvent.id).limit(2000))).all()
        for eid, email in rows:
            rid = await record_for_email(db, email)
            if rid:
                made += 1 if await start_run(db, ver, rid, f"web:{eid}", now) else 0
        if len(rows) < 2000:
            return made
        last = rows[-1][0]


# ── inbound webhook (M47.S01.T008) ──────────────────────────────────────────────

def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _audit(db: AsyncSession, user, event: str, workflow_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="crm",
                    target_type="crm_workflow", target_id=str(workflow_id), details=details))


async def issue_hook_token(db: AsyncSession, wf: CRMWorkflow, user) -> str:
    """Create or rotate the workflow's inbound token. The plain token is returned once and never stored."""
    from app.models.m47_automation import CRMWorkflowHook
    token = "wfh_" + secrets.token_urlsafe(32)
    hook = await db.get(CRMWorkflowHook, wf.id)
    rotated = hook is not None
    if hook is None:
        hook = CRMWorkflowHook(workflow_id=wf.id)
        db.add(hook)
    hook.token_digest, hook.token_hint, hook.created_by = _digest(token), token[-4:], user.username
    hook.rotated_at = datetime.now(timezone.utc)
    _audit(db, user, "crm_workflow.hook_rotated" if rotated else "crm_workflow.hook_created", wf.id, {"hint": token[-4:]})
    await db.flush()
    return token


async def revoke_hook(db: AsyncSession, wf: CRMWorkflow, user) -> bool:
    from app.models.m47_automation import CRMWorkflowHook
    hook = await db.get(CRMWorkflowHook, wf.id)
    if hook is None:
        return False
    await db.delete(hook)
    _audit(db, user, "crm_workflow.hook_revoked", wf.id, {})
    await db.flush()
    return True


async def hook_token_ok(db: AsyncSession, workflow_id: uuid.UUID, token: str):
    """The workflow's hook when the bearer token matches its stored digest, else None."""
    from app.models.m47_automation import CRMWorkflowHook
    hook = await db.get(CRMWorkflowHook, workflow_id)
    if hook is None or not token or not hmac.compare_digest(_digest(token), hook.token_digest):
        return None
    return hook


async def hook_enrol(db: AsyncSession, workflow_id: uuid.UUID, token: str, event_id: str,
                     record_id: Optional[uuid.UUID], email: Optional[str], now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    hook = await hook_token_ok(db, workflow_id, token)
    if hook is None:
        raise WorkflowError(401, "Invalid workflow or token.")
    wf = await db.get(CRMWorkflow, workflow_id)
    ver = await db.get(CRMWorkflowVersion, wf.published_version_id) if wf and wf.published_version_id else None
    if ver is None or ver.status != "PUBLISHED" or wf.trigger_event != "inbound_webhook":
        raise WorkflowError(409, "This workflow has no published version with an inbound webhook trigger.")
    if record_id is not None:
        rid = record_id if await db.get(CRMRecord, record_id) else None
    else:
        rid = await record_for_email(db, email or "")
    if rid is None:
        raise WorkflowError(404, "No CRM record matches this id or e-mail.")
    hook.last_used_at = now
    key = f"hook:{event_id}"
    run_id = await start_run(db, ver, rid, key, now)
    if run_id is None:
        existing = (await db.execute(select(CRMWorkflowRun.id).where(CRMWorkflowRun.version_id == ver.id,
                                                                    CRMWorkflowRun.event_key == key))).scalar_one_or_none()
        if existing is None:
            raise WorkflowError(429, "This record was enrolled too often in the last hour.")
        return {"enrolled": False, "duplicate": True, "run_id": str(existing)}
    return {"enrolled": True, "duplicate": False, "run_id": str(run_id)}


async def advance(db: AsyncSession, run: CRMWorkflowRun, now: datetime, approval: Optional[str] = None) -> None:
    ver = await db.get(CRMWorkflowVersion, run.version_id)
    record = await db.get(CRMRecord, run.crm_record_id)
    if record is None:
        run.status, run.log = "FAILED", [*(run.log or []), {"at": now.isoformat(), "note": "record deleted"}]
        return
    stage = await _stage_code(db, record)
    log = list(run.log or [])
    for _ in range(MAX_STEPS_PER_TICK):
        if not run.current_node:
            run.status = "DONE"
            break
        node = _node(ver.graph, run.current_node)
        t, cfg = node["type"], node.get("config") or {}
        if t == "condition":
            ok = _condition(cfg, record, stage)
            log.append({"at": now.isoformat(), "node": node["id"], "note": "yes" if ok else "no"})
            run.current_node = _next(ver.graph, node["id"], "yes" if ok else "no")
        elif t == "delay":
            if run.resume_at and auto._aware(run.resume_at) > now and run.waiting_node == node["id"]:
                break
            if run.waiting_node != node["id"]:
                run.waiting_node, run.resume_at, run.status = node["id"], now + timedelta(days=cfg["days"]), "WAITING"
                log.append({"at": now.isoformat(), "node": node["id"], "note": f"waiting until {run.resume_at.date()}"})
                if cfg["days"] > 0:
                    break
            run.waiting_node, run.status = None, "RUNNING"
            run.current_node = _next(ver.graph, node["id"])
        elif t == "approval":
            if approval is None:
                run.status, run.waiting_node = "WAITING_APPROVAL", node["id"]
                log.append({"at": now.isoformat(), "node": node["id"], "note": f"waiting for approval: {cfg['title']}"})
                break
            log.append({"at": now.isoformat(), "node": node["id"], "note": f"approval {approval}"})
            run.status, run.waiting_node = "RUNNING", None
            run.current_node = _next(ver.graph, node["id"], approval)
            approval = None
        elif t == "action":
            rule = SimpleNamespace(action_type=cfg["action_type"], action_payload=cfg.get("payload") or {})
            async with db.begin_nested():
                result = await auto._act(db, rule, record, now)
            log.append({"at": now.isoformat(), "node": node["id"], "note": result})
            run.current_node = _next(ver.graph, node["id"])
        elif t == "end":
            run.current_node, run.status = None, "DONE"
            log.append({"at": now.isoformat(), "node": node["id"], "note": "end"})
            break
        else:
            run.current_node = _next(ver.graph, node["id"])
    run.log = log
    if run.status == "DONE":
        run.finished_at = now


async def process(db: AsyncSession, limit: int = 50, now: Optional[datetime] = None) -> int:
    now = now or datetime.now(timezone.utc)
    runs = (await db.execute(select(CRMWorkflowRun).where(
        CRMWorkflowRun.status.in_(("RUNNING", "WAITING")), CRMWorkflowRun.resume_at <= now)
        .order_by(CRMWorkflowRun.created_at).limit(limit).with_for_update(skip_locked=True))).scalars().all()
    for run in runs:
        ver = await db.get(CRMWorkflowVersion, run.version_id)
        if ver is None or ver.status != "PUBLISHED":      # rolled back / replaced: the old version stops here
            run.status, run.finished_at = "CANCELLED", now
            run.log = [*(run.log or []), {"at": now.isoformat(), "note": "version no longer published; stopped"}]
            continue
        try:
            await advance(db, run, now)
        except Exception as exc:  # recorded; the run stops instead of looping
            run.status = "FAILED"
            run.log = [*(run.log or []), {"at": now.isoformat(), "note": f"{exc.__class__.__name__}: {exc}"[:300]}]
    await db.commit()
    return len(runs)


async def decide(db: AsyncSession, run_id: uuid.UUID, user, approve: bool) -> CRMWorkflowRun:
    run = (await db.execute(select(CRMWorkflowRun).where(CRMWorkflowRun.id == run_id).with_for_update())).scalar_one_or_none()
    if run is None or run.status != "WAITING_APPROVAL":
        raise WorkflowError(409, "This run is not waiting for an approval.")
    now = datetime.now(timezone.utc)
    run.log = [*(run.log or []), {"at": now.isoformat(), "note": f"{'approved' if approve else 'rejected'} by {user.username}"}]
    await advance(db, run, now, approval="yes" if approve else "no")
    await db.flush()
    return run
