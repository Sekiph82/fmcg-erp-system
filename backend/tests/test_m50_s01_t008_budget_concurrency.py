"""M50.S01.T008 agent budgets and concurrency (unit; DB part needs M50_DB=1). No paid request is ever made:
models are the local ScriptedProvider simulator.

Unit: 429/5xx retry with Retry-After and back-off, non-retryable errors, exhausted retries.
DB: simultaneous reservations never pass a cap (company/user/agent), settlement is idempotent and exact, a crashed worker's
lease is recovered with only measured usage charged, RUNNING jobs are requeued or dead-lettered, contention vs real
exhaustion, rate limits through a real job (usage log rows), dead-letter and requeue, measured usage log.
"""
import asyncio
import os
import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import agent_service as ags
from app.services import ai_provider as aip

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


# ── provider rate limits (no DB) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_429_waits_retry_after_then_succeeds():
    sleeps, seen = [], []

    async def fake_sleep(s):
        sleeps.append(s)

    async def on_attempt(n, status, ra, resp):
        seen.append((n, status, ra, resp is not None))
    p = aip.ScriptedProvider([429, 429, 200], retry_after=2)
    resp = await aip.generate_with_retry(p, "hello", sleep=fake_sleep, on_attempt=on_attempt)
    assert resp.provider == "simulator" and p.calls == 3 and sleeps == [2.0, 2.0]
    assert seen == [(1, 429, 2.0, False), (2, 429, 2.0, False), (3, 200, None, True)]


@pytest.mark.asyncio
async def test_backoff_without_retry_after_and_exhaustion():
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)
    with pytest.raises(aip.RateLimited) as e:
        await aip.generate_with_retry(aip.ScriptedProvider([429, 429, 429, 429]), "x", sleep=fake_sleep, max_attempts=4)
    assert sleeps == [1.0, 2.0, 4.0] and e.value.status == 429 and e.value.attempts == 4 and e.value.retry_after is None
    p = aip.ScriptedProvider([529, 500, 200])           # overloaded and server errors are retried too
    assert (await aip.generate_with_retry(p, "x", sleep=fake_sleep)).text
    with pytest.raises(aip.RateLimited) as e:
        await aip.generate_with_retry(aip.ScriptedProvider([429] * 4, retry_after=3600), "x", sleep=fake_sleep)
    assert e.value.retry_after == 3600 and sleeps[-1] == aip.MAX_RETRY_SLEEP_S      # a huge Retry-After does not stall the worker


@pytest.mark.asyncio
async def test_non_retryable_error_fails_at_once():
    p = aip.ScriptedProvider([401, 200])
    with pytest.raises(aip.ProviderError) as e:
        await aip.generate_with_retry(p, "x", sleep=lambda s: asyncio.sleep(0))
    assert not isinstance(e.value, aip.RateLimited) and p.calls == 1


def test_retry_after_http_date():
    from email.utils import format_datetime
    from datetime import datetime, timezone
    exc = SimpleNamespace(response=SimpleNamespace(headers={"Retry-After": format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)}))
    assert 20 <= aip._retry_after_s(exc) <= 31
    assert aip._retry_after_s(SimpleNamespace(response=SimpleNamespace(headers={"retry-after": "7"}))) == 7.0


# ── helpers ──────────────────────────────────────────────────────────────────

CAPS = {"company": 100, "user": 100, "agent": 100}


async def _clean():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        for t in ("ai_budget_counters", "ai_budget_reservations", "ai_usage_log"):
            await s.execute(text(f"DELETE FROM {t}"))
        await s.commit()


async def _counters():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text("SELECT scope_type, scope_id, cap_cost, reserved_cost, spent_cost FROM ai_budget_counters"))).all()
    return {(r[0], r[1]): (Decimal(r[2]), Decimal(r[3]), Decimal(r[4])) for r in rows}


# ── atomic reservation ───────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_simultaneous_reservations_never_pass_the_cap():
    from app.services import agent_budget as bud
    await _clean()
    agent, users = uuid.uuid4(), [uuid.uuid4() for _ in range(3)]
    caps = {"company": 100, "user": 100, "agent": 1.0}
    got = await asyncio.gather(*[bud.reserve(agent_id=agent, user_id=users[i % 3], est_cost=Decimal("0.3"), est_tokens=100, caps=caps, key=f"k{i}")
                                 for i in range(14)])
    ok = [g for g in got if g.ok]
    assert len(ok) == 3                                                # 0.9 fits, a fourth 0.3 would be 1.2
    assert all(g.denied_scope == "AGENT" and g.contended for g in got if not g.ok)
    c = await _counters()
    cap, reserved, spent = c[("AGENT", str(agent))]
    assert reserved == Decimal("0.9") and spent == 0 and reserved <= cap
    assert c[("COMPANY", "all")][1] == Decimal("0.9")                  # denied attempts rolled every scope back
    # settle with measured usage smaller than the hold: the rest is released, then one more fits
    for g in ok:
        await bud.record_usage(g.id, 50, Decimal("0.1"))
        assert await bud.settle(g.id)
    cap, reserved, spent = (await _counters())[("AGENT", str(agent))]
    assert reserved == 0 and spent == Decimal("0.3")
    again = await asyncio.gather(*[bud.reserve(agent_id=agent, user_id=users[0], est_cost=Decimal("0.3"), est_tokens=100, caps=caps, key=f"n{i}") for i in range(6)])
    assert sum(g.ok for g in again) == 2                               # spent 0.3 + 2 x 0.3 = 0.9 <= 1.0, a third is 1.2


@DB
@pytest.mark.asyncio
async def test_each_scope_is_enforced_and_denial_names_it():
    from app.services import agent_budget as bud
    await _clean()
    a, u = uuid.uuid4(), uuid.uuid4()
    r = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.6"), est_tokens=1, caps={"company": 1.0, "user": 100, "agent": 100}, key="c1")
    assert r.ok
    r2 = await bud.reserve(agent_id=uuid.uuid4(), user_id=uuid.uuid4(), est_cost=Decimal("0.6"), est_tokens=1, caps={"company": 1.0, "user": 100, "agent": 100}, key="c2")
    assert not r2.ok and r2.denied_scope == "COMPANY"
    r3 = await bud.reserve(agent_id=uuid.uuid4(), user_id=u, est_cost=Decimal("0.6"), est_tokens=1, caps={"company": 100, "user": 1.0, "agent": 100}, key="c3")
    assert not r3.ok and r3.denied_scope == "USER"
    # spent (not just reserved) counts: once settled at the full amount, the denial is not "contended"
    await bud.record_usage(r.id, 1, Decimal("0.6"))
    await bud.settle(r.id)
    r4 = await bud.reserve(agent_id=a, user_id=uuid.uuid4(), est_cost=Decimal("0.6"), est_tokens=1, caps={"company": 1.0, "user": 100, "agent": 100}, key="c4")
    assert not r4.ok and r4.denied_scope == "COMPANY" and not r4.contended
    assert not (await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.1"), est_tokens=1, caps={"company": 100, "user": 100, "agent": 100}, key="c1")).id is None
    same = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.6"), est_tokens=1, caps={"company": 1.0, "user": 100, "agent": 100}, key="c1")
    assert same.id == r.id                                             # idempotent per key (a settled one is not ok again)


@DB
@pytest.mark.asyncio
async def test_settlement_is_exact_and_idempotent_and_extend_respects_caps():
    from app.services import agent_budget as bud
    await _clean()
    a, u = uuid.uuid4(), uuid.uuid4()
    caps = {"company": 100, "user": 100, "agent": 1.0}
    r = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.5"), est_tokens=10, caps=caps, key="x")
    assert await bud.extend(r.id, a, u, caps, Decimal("0.4"), 5)       # 0.9 held
    assert not await bud.extend(r.id, a, u, caps, Decimal("0.2"), 5)   # 1.1 would pass the cap, nothing taken
    assert (await _counters())[("AGENT", str(a))][1] == Decimal("0.9")
    await bud.record_usage(r.id, 40, Decimal("0.7"))
    assert await bud.settle(r.id) and not await bud.settle(r.id)
    cap, reserved, spent = (await _counters())[("AGENT", str(a))]
    assert (reserved, spent) == (0, Decimal("0.7"))
    assert not await bud.extend(r.id, a, u, caps, Decimal("0.1"), 1)   # a settled reservation cannot grow
    r2 = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.4"), est_tokens=1, caps=caps, key="y")
    assert not r2.ok                                                   # 0.7 spent + 0.4 > 1.0


# ── crash recovery ───────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_crashed_worker_lease_is_recovered_with_measured_usage_only():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from app.services import agent_budget as bud
    await _clean()
    a, u = uuid.uuid4(), uuid.uuid4()
    caps = {"company": 100, "user": 100, "agent": 1.0}
    r = await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.8"), est_tokens=10, caps=caps, key="crash", job_id=uuid.uuid4())
    await bud.record_usage(r.id, 20, Decimal("0.05"))                  # the worker got this far, then died
    assert await bud.recover_stuck() == []                             # lease still valid: nothing to recover
    assert not (await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.3"), est_tokens=1, caps=caps, key="blocked")).ok
    async with AsyncSessionLocal() as s:
        await s.execute(text("UPDATE ai_budget_reservations SET expires_at = now() - interval '1 minute' WHERE id = :i"), {"i": r.id})
        await s.commit()
    rec = await bud.recover_stuck()
    assert len(rec) == 1 and rec[0]["actual_cost"] == Decimal("0.05")
    cap, reserved, spent = (await _counters())[("AGENT", str(a))]
    assert reserved == 0 and spent == Decimal("0.05")                  # the hold is released; only the measured usage is spent
    assert await bud.recover_stuck() == []                             # idempotent
    assert (await bud.reserve(agent_id=a, user_id=u, est_cost=Decimal("0.3"), est_tokens=1, caps=caps, key="after")).ok
    async with AsyncSessionLocal() as s:
        st = (await s.execute(text("SELECT status, note FROM ai_budget_reservations WHERE id = :i"), {"i": r.id})).one()
    assert st[0] == "EXPIRED" and "lease expired" in st[1]


async def _user_agent(db, defn=None, budgets=None):
    from app.core.security import hash_password
    from app.models.ai_hub import AIAgent, AIAgentVersion
    from app.models.user import User
    u = User(username=f"own-{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:6]}@povu-demo.test", full_name="o",
             hashed_password=hash_password(uuid.uuid4().hex), is_active=True, is_superuser=True)
    db.add(u)
    await db.flush()
    a = AIAgent(name=f"A-{uuid.uuid4().hex[:4]}", run_as_id=u.id, budgets={**ags.DEFAULT_BUDGETS, **(budgets or {})}, created_by=u.username,
                current_version=1, status="ACTIVE")
    db.add(a)
    await db.flush()
    defn = defn or {"trigger": {"type": "manual"}, "tools": [], "steps": [{"id": "s1", "type": "llm", "prompt": "Say hello.", "template": "hello {{input.n}}"}]}
    db.add(AIAgentVersion(agent_id=a.id, version=1, definition=defn, status="PUBLISHED", created_by=u.username, approved_by="b"))
    await db.flush()
    return u, a


async def _job(db, a, u, trigger="MANUAL", inputs=None):
    from app.models.ai_hub import AIAgentJob
    j = AIAgentJob(agent_id=a.id, version=1, trigger=trigger, idempotency_key=f"t:{uuid.uuid4().hex}", requested_by=u.id, input=inputs or {})
    db.add(j)
    await db.flush()
    return j


@DB
@pytest.mark.asyncio
async def test_running_job_of_a_dead_worker_is_requeued_then_dead_lettered():
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from app.services import agent_budget as bud
    await _clean()
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db)
        j = await _job(db, a, u)
        j.status, j.attempts = "RUNNING", 1                            # committed as RUNNING, then the process died
        await db.commit()
        r = await bud.reserve(agent_id=a.id, user_id=u.id, est_cost=Decimal("0.06"), est_tokens=4000, caps=CAPS, key=f"job:{j.id}:1", job_id=j.id)
        await db.execute(text("UPDATE ai_budget_reservations SET expires_at = now() - interval '1 second' WHERE id = :i"), {"i": r.id})
        await db.commit()
        assert await ags.recover(db) == {"requeued": 1, "dead": 0}
        await db.refresh(j)
        assert j.status == "QUEUED" and "queued again" in j.error
        await ags.execute_job(db, j)                                   # the retry runs normally with a new reservation
        assert j.status == "DONE" and j.attempts == 2
        j2 = await _job(db, a, u)
        j2.status, j2.attempts = "RUNNING", ags.MAX_ATTEMPTS
        await db.commit()
        r2 = await bud.reserve(agent_id=a.id, user_id=u.id, est_cost=Decimal("0.06"), est_tokens=1, caps=CAPS, key=f"job:{j2.id}:3", job_id=j2.id)
        await db.execute(text("UPDATE ai_budget_reservations SET expires_at = now() - interval '1 second' WHERE id = :i"), {"i": r2.id})
        await db.commit()
        assert await ags.recover(db) == {"requeued": 0, "dead": 1}
        await db.refresh(j2)
        assert j2.status == "DEAD" and "dead-lettered" in j2.error
        await db.execute(text("DELETE FROM ai_agent_jobs WHERE agent_id = :a"), {"a": a.id})
        await db.commit()


# ── through real jobs ────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_parallel_jobs_are_held_back_not_overspent_and_then_run():
    from app.db.session import AsyncSessionLocal
    from app.services import agent_budget as bud
    await _clean()
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db, budgets={"max_cost_per_day": 0.2, "max_runs_per_day": 100})
        ids = []
        for _ in range(6):
            ids.append((await _job(db, a, u)).id)
        await db.commit()
    holds = [await bud.reserve(agent_id=a.id, user_id=u.id, est_cost=Decimal("0.06"), est_tokens=1, caps={"company": 5, "user": 5, "agent": 0.2}, key=f"hold{i}")
             for i in range(3)]                                        # other workers hold 0.18 of the 0.2 cap
    assert all(h.ok for h in holds)

    async def work(jid):
        from app.models.ai_hub import AIAgentJob
        async with AsyncSessionLocal() as s:
            j = await s.get(AIAgentJob, jid)
            await ags.execute_job(s, j)
            await s.commit()
            return j.status, j.error
    got = await asyncio.gather(*[work(i) for i in ids])
    assert all(st == "QUEUED" and "budget held by runs in progress" in er for st, er in got)     # waiting, not failed, not overspent
    cap, reserved, spent = (await _counters())[("AGENT", str(a.id))]
    assert reserved == Decimal("0.18") and spent == 0
    for h in holds:
        await bud.settle(h.id)                                          # the others finish having used nothing
    async with AsyncSessionLocal() as s:
        from app.models.ai_hub import AIAgentJob
        for jid in ids:
            (await s.get(AIAgentJob, jid)).next_attempt_at = ags._now() - timedelta(seconds=1)
        await s.commit()
    got = await asyncio.gather(*[work(i) for i in ids])
    cap, reserved, spent = (await _counters())[("AGENT", str(a.id))]
    assert reserved == 0 and spent <= cap and spent <= Decimal("0.2")
    assert {st for st, _ in got} <= {"DONE", "QUEUED", "BLOCKED"} and any(st == "DONE" for st, _ in got)


@DB
@pytest.mark.asyncio
async def test_real_exhaustion_blocks_instead_of_waiting():
    from app.db.session import AsyncSessionLocal
    from app.services import agent_budget as bud
    await _clean()
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db, budgets={"max_cost_per_day": 0.05, "max_runs_per_day": 100})
        r = await bud.reserve(agent_id=a.id, user_id=u.id, est_cost=Decimal("0.04"), est_tokens=1, caps={"company": 5, "user": 5, "agent": 0.05}, key="spent")
        await bud.record_usage(r.id, 1, Decimal("0.04"))
        await bud.settle(r.id)
        j = await _job(db, a, u)
        await ags.execute_job(db, j)
        assert j.status == "BLOCKED" and "Agent AI budget" in j.error
        await db.rollback()


PROVIDER_DEF = {"trigger": {"type": "manual"}, "tools": [], "steps": [{"id": "s1", "type": "llm", "prompt": "Say hello to the shop.", "template": "hello {{input.n}}"}]}


@DB
@pytest.mark.asyncio
async def test_rate_limited_provider_job_retries_and_logs_measured_usage(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.m50_ai_platform import AIBudgetReservation, AIUsageLog
    await _clean()
    sim = aip.ScriptedProvider([429, 429, 200], retry_after=0)
    monkeypatch.setattr(ags, "_provider", lambda: sim)
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db, PROVIDER_DEF)
        await ags.settings_put(db, {"use_provider": True}, "t")
        j = await _job(db, a, u)
        await ags.execute_job(db, j)
        await db.commit()
        assert j.status == "DONE" and sim.calls == 3 and j.tokens > 0
        logs = list((await db.execute(select(AIUsageLog).where(AIUsageLog.job_id == j.id).order_by(AIUsageLog.created_at))).scalars())
        assert [(x.outcome, x.attempt) for x in logs] == [("RATE_LIMITED", 1), ("RATE_LIMITED", 2), ("OK", 3)]
        ok = logs[-1]
        assert ok.source == "SIMULATOR" and ok.provider == "simulator" and ok.prompt_tokens > 0 and ok.completion_tokens > 0 and ok.cost > 0
        assert all(x.prompt_tokens == 0 and x.cost == 0 for x in logs[:2]) and logs[0].retry_after_s == 0
        res = (await db.execute(select(AIBudgetReservation).where(AIBudgetReservation.job_id == j.id))).scalar_one()
        assert res.status == "SETTLED" and res.actual_tokens == ok.prompt_tokens + ok.completion_tokens and res.actual_cost == ok.cost == j.cost
        await ags.settings_put(db, {"use_provider": False}, "t")
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_rate_limit_that_does_not_clear_requeues_with_retry_after_then_dead_letters(monkeypatch):
    from sqlalchemy import select
    from app.api.v1.endpoints import ai_agents as api
    from app.db.session import AsyncSessionLocal
    from app.models.m50_ai_platform import AIBudgetReservation
    await _clean()
    sim = aip.ScriptedProvider([429] * 40, retry_after=120)
    monkeypatch.setattr(ags, "_provider", lambda: sim)
    orig = aip.generate_with_retry

    async def no_wait(*a, **k):
        async def nap(_):
            return None
        return await orig(*a, **{**k, "sleep": nap})
    monkeypatch.setattr(aip, "generate_with_retry", no_wait)
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db, PROVIDER_DEF)
        await ags.settings_put(db, {"use_provider": True}, "t")
        j = await _job(db, a, u)
        t0 = ags._now()
        await ags.execute_job(db, j)
        assert j.status == "QUEUED" and j.attempts == 1 and "RateLimited" in j.error
        assert t0 + timedelta(seconds=110) < j.next_attempt_at < t0 + timedelta(seconds=130)       # Retry-After honoured, not 2 minutes of guess
        await ags.execute_job(db, j)
        await ags.execute_job(db, j)
        assert j.status == "DEAD" and j.attempts == ags.MAX_ATTEMPTS and j.finished_at is not None
        res = list((await db.execute(select(AIBudgetReservation).where(AIBudgetReservation.job_id == j.id))).scalars())
        assert len(res) == 3 and all(r.status == "RELEASED" and r.actual_cost == 0 for r in res)    # failed calls cost nothing and release the hold
        assert j.cost == 0
        # manual recovery: requeue the dead job (second person with ai.approve)
        boss = u
        out = await api.job_action(j.id, "requeue", db=db, current_user=boss)
        assert out["status"] == "QUEUED" and out["attempts"] == 0
        out = await api.job_action(j.id, "cancel", db=db, current_user=boss)
        assert out["status"] == "CANCELLED"
        await ags.settings_put(db, {"use_provider": False}, "t")
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_template_run_logs_estimates_and_never_calls_a_provider(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.m50_ai_platform import AIUsageLog
    await _clean()
    monkeypatch.setattr(ags, "_provider", lambda: (_ for _ in ()).throw(AssertionError("no provider call expected")))
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db)
        j = await _job(db, a, u, inputs={"n": "Duka"})
        await ags.execute_job(db, j)
        await db.commit()
        assert j.status == "DONE"
        row = (await db.execute(select(AIUsageLog).where(AIUsageLog.job_id == j.id))).scalar_one()
        assert row.source == "ESTIMATE" and row.provider == "deterministic" and row.prompt_tokens + row.completion_tokens == j.tokens


@DB
@pytest.mark.asyncio
async def test_simulation_reserves_nothing_and_kill_switch_blocks_before_reserving():
    from app.db.session import AsyncSessionLocal
    await _clean()
    async with AsyncSessionLocal() as db:
        u, a = await _user_agent(db)
        sim = await _job(db, a, u, trigger="SIMULATE")
        await ags.execute_job(db, sim)
        assert sim.status == "DONE" and await _counters() == {}
        await ags.settings_put(db, {"kill_switch": True}, "t")
        j = await _job(db, a, u)
        await ags.execute_job(db, j)
        assert j.status == "BLOCKED" and "Emergency stop" in j.error and await _counters() == {}
        await ags.settings_put(db, {"kill_switch": False}, "t")
        await db.commit()
