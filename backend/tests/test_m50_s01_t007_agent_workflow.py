"""M50.S01.T007 Agent Builder advanced workflow (unit; DB part needs M50_DB=1).

Unit: conditionals/branches, bounded loops (hard max), step budget, input/output schemas, exception path, approval park and
resume, validation of every new construct, trigger rules. DB: delegation ceiling and depth, delegation loop refused,
approval gate end to end (second person, denial path), version rollback re-validated, retry does not duplicate proposals,
HTTP route order (validate/gates/budget before /{aid}).
"""
import os
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import agent_service as ags

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
CFG = {**ags.DEFAULT_SETTINGS}


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def D(steps, tools=("kb_search",), **kw):
    return {"trigger": {"type": "manual"}, "tools": list(tools), "steps": steps, **kw}


def llm(sid, template="x", **kw):
    return {"id": sid, "type": "llm", "template": template, **kw}


async def go(defn, inputs=None, **kw):
    agent = SimpleNamespace(id=uuid.uuid4(), name="t")
    return await ags.run(None, agent, defn, None, inputs or {}, simulate=kw.pop("simulate", True), job_ref="t", cfg=CFG,
                         budget_tokens=kw.pop("budget_tokens", 100000), **kw)


def bad(defn, msg):
    with pytest.raises(ags.AgentError) as e:
        ags.validate(defn)
    assert msg in str(e.value), (msg, str(e.value))


# ── validation ───────────────────────────────────────────────────────────────

def test_validation_of_new_constructs():
    ok = D([{"id": "s1", "type": "condition", "if": {"ref": "input.n", "op": "gt", "value": 1}, "then": "s2", "else": "s3"},
            llm("s2"), llm("s3")])
    assert set(ags.validate(ok)["order"]) == {"s1", "s2", "s3"}
    cond = {"id": "s1", "type": "condition", "if": {"ref": "input.n", "op": "gt", "value": 1}, "then": "s2"}
    for defn, msg in [
        (D([{**cond, "if": {"ref": "input.n", "op": "evil", "value": 1}}, llm("s2")]), "operator must be one of"),
        (D([{**cond, "if": {"ref": "input.n", "op": "gt"}}, llm("s2")]), "needs a 'value'"),
        (D([{**cond, "then": None}, llm("s2")]), "needs a 'then'"),
        (D([{**cond, "next": "s2"}, llm("s2")]), "then/else, not next"),
        (D([{"id": "l", "type": "loop", "body": ["b"]}, llm("b")]), "max_iterations between 1 and 10"),
        (D([{"id": "l", "type": "loop", "max_iterations": 11, "body": ["b"]}, llm("b")]), "max_iterations between 1 and 10"),
        (D([{"id": "l", "type": "loop", "max_iterations": 0, "body": ["b"]}, llm("b")]), "max_iterations between 1 and 10"),
        (D([{"id": "l", "type": "loop", "max_iterations": True, "body": ["b"]}, llm("b")]), "max_iterations between 1 and 10"),
        (D([{"id": "l", "type": "loop", "max_iterations": 3, "body": []}]), "body of 1"),
        (D([{"id": "l", "type": "loop", "max_iterations": 3, "body": ["b"]}, llm("b", next="l")]), "without next/on_error"),
        (D([{"id": "l", "type": "loop", "max_iterations": 3, "body": ["l"]}]), "body step"),
        (D([{"id": "s1", "type": "delegate", "agent": str(uuid.uuid4())}]), "delegates list"),
        (D([{"id": "s1", "type": "approval"}]), "needs a message"),
        (D([{"id": "s1", "type": "magic"}]), "type must be one of"),
        (D([llm("s1", next="s2"), llm("s2", next="s3"), llm("s3", next="s2")]), "Cycle"),
        (D([{**cond, "else": "s1"}, llm("s2")]), "Cycle"),
        (D([{**cond, "else": "s3"}, llm("s2"), llm("s3", "{{s2}}")]), "has not run yet"),   # sibling branch output
        (D([llm("s1")], input_schema={"type": "nonsense"}), "not a valid JSON Schema"),
        ({"trigger": {"type": "event"}, "tools": [], "steps": [llm("s1")]}, "event name"),
        (D([llm(f"s{i}") for i in range(31)]), "1–30 steps"),
    ]:
        bad(defn, msg)
    ags.validate({"trigger": {"type": "event", "event": "order.created"}, "tools": [], "steps": [llm("s1")]})


def test_a_loop_body_is_reachable_only_through_its_loop():
    bad(D([llm("s1", next="b"), {"id": "l", "type": "loop", "max_iterations": 2, "body": ["b"]}, llm("b")]), "loop body step")


# ── execution: bounded loops, branches, budget ───────────────────────────────

@pytest.mark.asyncio
async def test_loop_runs_at_most_max_iterations_and_stops_on_until():
    defn = D([{"id": "l", "type": "loop", "max_iterations": 3, "body": ["b"], "until": {"ref": "b", "op": "eq", "value": "never"}, "next": "z"},
              llm("b", "tick"), llm("z", "after {{l.iterations}} {{l.stopped_by}}")])
    out = await go(defn)
    assert out["final"] == "after 3 max_iterations"
    assert [t["step"] for t in out["trace"]].count("b") == 3
    until = D([{"id": "l", "type": "loop", "max_iterations": 10, "body": ["b"], "until": {"ref": "b", "op": "eq", "value": "tick"}}, llm("b", "tick")])
    assert (await go(until))["final"] == {"iterations": 1, "stopped_by": "until"}


@pytest.mark.asyncio
async def test_total_step_executions_are_capped(monkeypatch):
    async def many(db, u, args):
        return [{"title": f"item {i}"} for i in range(50)]
    monkeypatch.setitem(ags.TOOLS["kb_search"], "fn", many)
    steps = [{"id": "s1", "type": "tool", "tool": "kb_search", "args": {}, "next": "s2"}] + [
        llm(f"s{i}", "x", foreach="s1", **({"next": f"s{i + 1}"} if i < 5 else {})) for i in range(2, 6)]
    with pytest.raises(ags.BudgetError) as e:
        await go(D(steps))
    assert "Step execution limit" in str(e.value)


@pytest.mark.asyncio
async def test_token_budget_still_stops_a_loop():
    defn = D([{"id": "l", "type": "loop", "max_iterations": 10, "body": ["b"]}, llm("b", "x" * 400)])
    with pytest.raises(ags.BudgetError):
        await go(defn, budget_tokens=250)


@pytest.mark.asyncio
async def test_condition_branches_and_converges():
    defn = D([{"id": "c", "type": "condition", "if": {"ref": "input.amount", "op": "ge", "value": 100}, "then": "big", "else": "small"},
              llm("big", "large {{input.amount}}", next="end"), llm("small", "small {{input.amount}}", next="end"), llm("end", "done")])
    hi, lo = await go(defn, {"amount": 250}), await go(defn, {"amount": 5})
    assert [t["step"] for t in hi["trace"]] == ["c", "big", "end"] and [t["step"] for t in lo["trace"]] == ["c", "small", "end"]
    cnt = D([{"id": "c", "type": "condition", "if": {"ref": "input.rows", "op": "gt", "value": 1, "agg": "count"}, "then": "a"}, llm("a")])
    assert (await go(cnt, {"rows": [1, 2]}))["final"] == "x"
    assert (await go(cnt, {"rows": [1]}))["final"] == {"result": False}      # no else: the run ends at the condition


def test_condition_operators():
    c = lambda op, v, left: ags.eval_cond({"ref": "input.x", "op": op, "value": v}, {"input": {"x": left}})
    assert c("eq", "5", 5) and c("ne", 4, 5) and c("lt", 10, "9") and c("le", 9, 9) and not c("gt", 9, 9)
    assert c("contains", "clean", "POVU AllClean") and c("not_contains", "x", ["a"]) and c("contains", "a", ["a", "b"])
    assert ags.eval_cond({"ref": "input.x", "op": "exists"}, {"input": {"x": "v"}})
    assert ags.eval_cond({"ref": "input.x", "op": "not_exists"}, {"input": {}})


# ── schemas, exception path, approval ────────────────────────────────────────

@pytest.mark.asyncio
async def test_input_and_output_schema():
    sch_in = {"type": "object", "required": ["goal"], "properties": {"goal": {"type": "string", "maxLength": 20}}}
    defn = D([llm("s1", "Goal {{input.goal}}")], input_schema=sch_in, output_schema={"type": "string", "pattern": "^Goal"})
    assert (await go(defn, {"goal": "grow"}))["final"] == "Goal grow"
    for inputs in ({}, {"goal": 5}, {"goal": "x" * 21}):
        with pytest.raises(ags.AgentError) as e:
            await go(defn, inputs)
        assert "Input does not match its schema" in str(e.value)
    wrong = D([llm("s1", "Nope")], output_schema={"type": "string", "pattern": "^Goal"})
    with pytest.raises(ags.AgentError) as e:
        await go(wrong)
    assert "Output does not match" in str(e.value)


@pytest.mark.asyncio
async def test_exception_path(monkeypatch):
    async def boom(db, u, args):
        raise ags.AgentError("source unavailable")
    monkeypatch.setitem(ags.TOOLS["kb_search"], "fn", boom)
    defn = D([{"id": "s1", "type": "tool", "tool": "kb_search", "args": {}, "on_error": "h", "next": "ok"}, llm("ok", "fine"),
              llm("h", "fallback because {{s1.error}}")])
    out = await go(defn)
    assert out["final"] == "fallback because source unavailable"
    defn["steps"][0].pop("on_error")
    defn["steps"] = defn["steps"][:2]
    with pytest.raises(ags.AgentError):
        await go(defn)
    # a hard limit is never routed to an error path
    loop = D([{"id": "l", "type": "loop", "max_iterations": 10, "body": ["b"], "on_error": "h"}, llm("b", "x" * 400), llm("h", "swallowed")])
    with pytest.raises(ags.BudgetError):
        await go(loop, budget_tokens=250)


@pytest.mark.asyncio
async def test_approval_parks_the_run_and_resumes_on_either_decision():
    defn = D([llm("s1", "draft", next="ap"), {"id": "ap", "type": "approval", "message": "Send {{s1}}?", "next": "go", "on_deny": "no"},
              llm("go", "sent"), llm("no", "stopped")])
    sim = await go(defn)                                           # simulation does not wait
    assert [t["step"] for t in sim["trace"]] == ["s1", "ap", "go"] and "would wait for approval" in sim["trace"][1]["output"]
    parked = (await go(defn, simulate=False))["waiting"]
    assert parked["step"] == "ap" and parked["message"] == "Send draft?"
    yes = await go(defn, simulate=False, resume={**parked["state"], "decision": "APPROVED", "decided_by": "boss"})
    no = await go(defn, simulate=False, resume={**parked["state"], "decision": "DENIED", "decided_by": "boss"})
    assert yes["final"] == "sent" and no["final"] == "stopped"
    only = D([llm("s1", "draft", next="ap"), {"id": "ap", "type": "approval", "message": "ok?", "next": "go"}, llm("go", "sent")])
    p2 = (await go(only, simulate=False))["waiting"]
    denied = await go(only, simulate=False, resume={**p2["state"], "decision": "DENIED"})
    assert denied["denied"] and denied["final"] == {"approved": False, "by": None}


# ── database ─────────────────────────────────────────────────────────────────

async def _user(db, superuser=True, name="own"):
    from app.core.security import hash_password
    from app.models.user import User
    u = User(username=f"{name}-{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=name,
             hashed_password=hash_password(uuid.uuid4().hex), is_active=True, is_superuser=superuser)
    db.add(u)
    await db.flush()
    return u


async def _agent(db, owner, defn, name="A", status="ACTIVE", budgets=None):
    from app.models.ai_hub import AIAgent, AIAgentVersion
    a = AIAgent(name=f"{name}-{uuid.uuid4().hex[:4]}", run_as_id=owner.id, budgets=budgets or dict(ags.DEFAULT_BUDGETS), created_by=owner.username,
                current_version=1, status=status)
    db.add(a)
    await db.flush()
    db.add(AIAgentVersion(agent_id=a.id, version=1, definition=defn, status="PUBLISHED", created_by=owner.username, approved_by="second"))
    await db.flush()
    return a


async def _run_job(db, a, owner, inputs=None, trigger="SIMULATE"):
    from app.models.ai_hub import AIAgentJob
    j = AIAgentJob(agent_id=a.id, version=1, trigger=trigger, idempotency_key=f"t:{uuid.uuid4().hex}", requested_by=owner.id, input=inputs or {})
    db.add(j)
    await db.flush()
    await ags.execute_job(db, j)
    await db.flush()
    return j


@DB
@pytest.mark.asyncio
async def test_delegation_ceiling_depth_and_loop():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        owner = await _user(db)
        child_ok = await _agent(db, owner, D([llm("s1", "child says {{input.q}}")], input_schema={"type": "object", "required": ["q"], "properties": {"q": {"type": "string", "minLength": 1}}}), "child")
        child_more = await _agent(db, owner, {"trigger": {"type": "manual"}, "tools": ["kb_search", "create_task"], "steps": [
            {"id": "s1", "type": "tool", "tool": "create_task", "args": {}}]}, "greedy")
        parent = lambda child: D([{"id": "d", "type": "delegate", "agent": str(child.id), "input": {"q": "{{input.q}}"}}], delegates=[str(child.id)])
        # a child with a subset of the parent's tools runs, as the same user
        p = await _agent(db, owner, parent(child_ok), "parent")
        j = await _run_job(db, p, owner, {"q": "hello"})
        assert j.status == "DONE" and j.trace[0]["type"] == "delegate" and "child says hello" in j.trace[0]["output"]
        # the child's input schema is enforced on what the parent hands over
        j = await _run_job(db, p, owner, {})
        assert j.status == "FAILED" and "Input does not match" in j.error
        # a child with a tool the parent lacks is refused: no escalation through delegation
        p2 = await _agent(db, owner, parent(child_more), "parent2")
        j = await _run_job(db, p2, owner, {"q": "x"})
        assert j.status == "FAILED" and "child never exceeds its parent" in j.error and "create_task" in j.error
        # depth limit: chain of 5 agents
        chain = [await _agent(db, owner, D([llm("s1", "leaf")]), "leaf")]
        for i in range(4):
            chain.append(await _agent(db, owner, parent(chain[-1]), f"lvl{i}"))
        j = await _run_job(db, chain[-1], owner)
        assert j.status == "FAILED" and "Delegation depth limit" in j.error
        j = await _run_job(db, chain[ags.MAX_DELEGATION_DEPTH], owner)      # exactly 3 hops is allowed
        assert j.status == "DONE"
        # delegation loop a -> b -> a
        a1 = await _agent(db, owner, D([llm("s1", "x")]), "ping")
        a2 = await _agent(db, owner, parent(a1), "pong")
        from app.models.ai_hub import AIAgentVersion
        v = (await db.execute(__import__("sqlalchemy").select(AIAgentVersion).where(AIAgentVersion.agent_id == a1.id))).scalar_one()
        v.definition = parent(a2)
        await db.flush()
        j = await _run_job(db, a2, owner)
        assert j.status == "FAILED" and "Delegation loop" in j.error
        # a stopped child is refused
        child_ok.stopped = True
        j = await _run_job(db, p, owner, {"q": "hello"})
        assert j.status == "FAILED" and "stopped" in j.error
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_approval_gate_end_to_end_second_person_and_denial():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.m50_ai_platform import AIAgentGate
    defn = D([llm("s1", "plan", next="ap"), {"id": "ap", "type": "approval", "message": "Go ahead with {{s1}}?", "next": "go", "on_deny": "no"},
              llm("go", "executed"), llm("no", "dropped")])
    async with AsyncSessionLocal() as db:
        owner, boss = await _user(db), await _user(db, name="boss")
        a = await _agent(db, owner, defn)
        j = await _run_job(db, a, owner, trigger="MANUAL")
        assert j.status == "WAITING" and "Go ahead with plan?" in j.error
        g = (await db.execute(select(AIAgentGate).where(AIAgentGate.job_id == j.id))).scalar_one()
        with pytest.raises(PermissionError):
            await ags.decide_gate(db, g, owner, True)               # the owner cannot approve their own agent
        await ags.decide_gate(db, g, boss, True)
        assert j.status == "QUEUED" and g.status == "APPROVED"
        with pytest.raises(ags.AgentError):
            await ags.decide_gate(db, g, boss, True)                # decided once
        await ags.execute_job(db, j)
        assert j.status == "DONE" and j.trace[-1]["step"] == "go" and g.resumed_at is not None
        # denial takes the denial path
        j2 = await _run_job(db, a, owner, trigger="MANUAL")
        g2 = (await db.execute(select(AIAgentGate).where(AIAgentGate.job_id == j2.id))).scalar_one()
        await ags.decide_gate(db, g2, boss, False)
        await ags.execute_job(db, j2)
        assert j2.status == "DONE" and j2.trace[-1]["step"] == "no"
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_rollback_revalidates_and_switches_version():
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.api.v1.endpoints import ai_agents as api
    from app.db.session import AsyncSessionLocal
    from app.models.ai_hub import AIAgentVersion
    async with AsyncSessionLocal() as db:
        owner, boss = await _user(db), await _user(db, name="boss")
        a = await _agent(db, owner, D([llm("s1", "v1")]))
        db.add(AIAgentVersion(agent_id=a.id, version=2, definition=D([llm("s1", "v2")]), status="PUBLISHED", created_by="x", approved_by="y"))
        db.add(AIAgentVersion(agent_id=a.id, version=3, definition=D([llm("s1", "v3")]), status="PUBLISHED", created_by="x", approved_by="y"))
        a.current_version = 3
        await db.flush()
        out = await api.version_action(a.id, 1, "rollback", db=db, current_user=boss)
        assert out["current_version"] == 1
        j = await _run_job(db, a, owner, trigger="MANUAL")
        assert j.status == "DONE"
        # a stored version that breaks today's rules cannot be rolled back to
        v2 = (await db.execute(select(AIAgentVersion).where(AIAgentVersion.agent_id == a.id, AIAgentVersion.version == 2))).scalar_one()
        v2.definition = D([{"id": "l", "type": "loop", "body": ["b"]}, llm("b")])
        await db.flush()
        with pytest.raises(HTTPException) as e:
            await api.version_action(a.id, 2, "rollback", db=db, current_user=boss)
        assert e.value.status_code == 409 and "no longer passes validation" in e.value.detail
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_retry_does_not_duplicate_proposals():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.ai_hub import AIActionRequest
    from app.models.sales import Customer
    async with AsyncSessionLocal() as db:
        owner = await _user(db)
        c = Customer(code=f"SYN-{uuid.uuid4().hex[:6]}", name="POVU Retry Shop", currency="KES", email="retry@povu-demo.test")
        db.add(c)
        await db.flush()
        defn = D([{"id": "s1", "type": "tool", "tool": "create_task", "args": {"customer_id": str(c.id), "subject": "Call back"}}], tools=("create_task",))
        agent = SimpleNamespace(id=uuid.uuid4(), name="t")
        for _ in range(2):          # the same job is run twice (a retry after a crash that lost the result)
            await ags.run(db, agent, defn, owner, {}, simulate=False, job_ref="job-dup", cfg=CFG, budget_tokens=1000)
        n = (await db.execute(select(func.count()).select_from(AIActionRequest).where(AIActionRequest.source_ref == "job-dup"))).scalar_one()
        assert n == 1
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_http_routes_are_not_shadowed_by_agent_id_route():
    import httpx
    from fastapi import FastAPI
    from app.api.v1.endpoints import ai_agents as api
    from app.core.deps import get_current_user
    app = FastAPI()
    app.include_router(api.router, prefix="/ai-agents")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_superuser=True, username="t", id=uuid.uuid4(), permissions=[], roles=[],
                                                                          is_active=True, email="t@povu-demo.test", full_name="t")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/ai-agents/validate", json={"definition": D([{"id": "l", "type": "loop", "body": ["b"]}, llm("b")])})
        assert r.status_code == 200 and r.json()["ok"] is False and "max_iterations" in r.json()["errors"][0]
        assert (await c.post("/ai-agents/validate", json={"definition": D([llm("s1")])})).json()["ok"] is True
        cat = (await c.get("/ai-agents/catalog")).json()
        assert cat["limits"]["max_loop_iterations"] == 10 and "approval" in cat["step_types"]
        assert (await c.get("/ai-agents/gates")).status_code == 200
        assert (await c.get("/ai-agents/budget/usage")).status_code == 200
        assert (await c.get("/ai-agents/evals/corpora")).status_code == 200
