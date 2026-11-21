"""Visual workflow designer engine (M36.S03.T004).

A workflow is a versioned graph: one trigger node (a CRM event), then condition (yes/no branches), delay, approval
(a manager approves or rejects → branch) and action nodes (the same safe actions as CRM automation), ending in end
nodes. Only PUBLISHED versions run; publishing archives the previous one and an older version can be re-published
(rollback). Validation refuses cycles, unreachable nodes, missing branches and invalid action settings. Simulation
walks the graph against a real record without changing anything.

Runs start from new CRM events (stage history after the version was published), advance node by node, wait on
delays (resume time) and approvals, and record every step in the run log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMPipelineStage, CRMRecord, CRMStageHistory, CRMWorkflow, CRMWorkflowRun, CRMWorkflowVersion
from app.services import crm_automation_service as auto

NODE_TYPES = ("trigger", "condition", "delay", "approval", "action", "end")
MAX_NODES = 60
MAX_STEPS_PER_TICK = 25


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
    ids = [n.get("id") for n in nodes]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
        errs.append("Every step needs a unique id.")
    by = {n.get("id"): n for n in nodes}
    triggers = [n for n in nodes if n.get("type") == "trigger"]
    if len(triggers) != 1:
        errs.append("Exactly one trigger step is required.")
    for n in nodes:
        t, cfg = n.get("type"), n.get("config") or {}
        if t not in NODE_TYPES:
            errs.append(f"{n.get('id')}: unknown step type {t}.")
            continue
        if t == "trigger" and cfg.get("event") not in auto.TRIGGERS:
            errs.append(f"{n['id']}: trigger event must be one of {', '.join(auto.TRIGGERS)}.")
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
            except ValueError as e:
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
            steps.append({"node": node["id"], "type": t, "note": f"on {cfg['event']}"})
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


async def publish(db: AsyncSession, version: CRMWorkflowVersion, user) -> None:
    problems = validate(version.graph)
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
        since = max(auto._aware(ver.published_at), auto._aware(wf.enqueued_until) - auto.WATERMARK_OVERLAP) if wf.enqueued_until else auto._aware(ver.published_at)
        since = max(since, auto._aware(ver.published_at))
        hist = (await db.execute(select(CRMStageHistory).where(CRMStageHistory.changed_at >= since))).scalars().all()
        trig = next(n for n in ver.graph["nodes"] if n["type"] == "trigger")
        for h in hist:
            if wf.trigger_event not in auto._events(h):
                continue
            res = await db.execute(insert(CRMWorkflowRun).values(
                id=uuid.uuid4(), version_id=ver.id, crm_record_id=h.crm_record_id, event_key=f"{wf.trigger_event}:{h.id}",
                current_node=_next(ver.graph, trig["id"]), status="RUNNING", resume_at=now, log=[], created_at=now
            ).on_conflict_do_nothing(constraint="uq_crm_workflow_run_event"))
            created += res.rowcount or 0
        wf.enqueued_until = now
    await db.commit()
    return created


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
