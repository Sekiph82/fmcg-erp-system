"""M50.S01.T001 AI Prospecting Agent (DB part needs M50_DB=1).

Synthetic corpus + local search simulator + fake LLM (never a paid call). Covers: deterministic run without any
LLM key, web citations and recency, CRM dedup/association, territory and competitor assessment with citations and
unknowns, LLM path with clipped adjustments and grounding check (ungrounded rationale dropped), LLM failure fallback,
low-confidence web candidates, approval-gated outreach (different approver, suppression), RBAC.
"""
import json
import os
import uuid

import pytest

from tests.m50_s01_common import client_for, ensure_tables, sim_calls, staff, use_sim

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
API = "/api/v1/prospecting-agent"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    from app.core import provider_http
    from app.services import ai_provider
    provider_http.set_test_transport(None)
    ai_provider.reset_provider()
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


class FakeLLM:
    def __init__(self, reply=None, fail=False):
        self.reply, self.fail, self.prompts = reply, fail, []

    async def generate_text(self, prompt, system=None):
        from app.services.ai_provider import AIResponse
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("provider down")
        return AIResponse(text=json.dumps(self.reply(prompt)), provider="fake", model="fake-llm-1")


@DB
@pytest.mark.asyncio
async def test_agent_run_outreach_and_llm(monkeypatch):
    from sqlalchemy import delete, select
    from app.db.session import AsyncSessionLocal
    from app.models.ai_hub import AIActionRequest
    from app.models.crm import CRMOutboundMessage, CRMRecord
    from app.models.customer_data import DataSource
    from app.models.sales import Customer
    from app.services import ai_provider, crm_outbound_service as outbound, customer_data_service as cds
    from app.services import pat_service as pats
    await ensure_tables()
    use_sim(monkeypatch)
    ai_provider.reset_provider()
    monkeypatch.setattr(ai_provider, "_instance", ai_provider.MockProvider())          # no key: deterministic fallback
    t = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        await db.execute(delete(DataSource))
        db.add(CRMRecord(company_name="Kibanda Fresh Stores", contact_email=f"buy{t}@kibanda.example.com", channel_id="RETAIL", lead_code=f"L-{t}"))
        await db.commit()
    async with AsyncSessionLocal() as db:
        viewer = await staff(db, "view", ("crm.view",))
        rep = await staff(db, "rep", ("crm.view", "crm.edit"))
        boss = await staff(db, "boss", ("crm.view", "crm.edit_all"))
        approver = await staff(db, "appr", ("crm.view", "crm.edit_all"))
        db.add(Customer(code=f"SERV-{t}", name=f"Mama Mboga {t}", city="Nakuru", currency="KES", is_active=True))
        await cds.import_source(db, name=f"Fair {t}", license_note="own trade-fair sign-up sheet", retention_days=30, user="rep", rows=[
            {"n": "Kibanda Fresh Stores", "c": "Nakuru", "ch": "RETAIL", "e": f"buy{t}@kibanda.example.com"},       # same company as the CRM lead
            {"n": "Duka Moja Supermarket", "c": "Nakuru", "ch": "RETAIL", "e": f"hello{t}@dukamoja.example.com"},
            {"n": "Mtaani Cleaning Wholesalers", "c": "Eldoret", "ch": "WHOLESALE", "e": ""},
            {"n": f"Mama Mboga {t}", "c": "Nakuru", "ch": "RETAIL", "e": ""}],                                        # an existing customer
            mapping={"company_name": "n", "city": "c", "channel": "ch", "email": "e"})
        await db.commit()
    async with client_for(viewer) as v, client_for(rep) as r, client_for(boss) as b:
        await b.put(f"{API}/settings/SEARCH", json={"provider": "brave", "enabled": True, "licensed": True, "license_note": "Brave plan (simulated)",
                                                      "retention_days": 30, "config": {"country": "KE"}})
        icp = await r.post(f"{API}/icps", json={"name": "Nakuru retail", "city": "Nakuru", "channel": "RETAIL", "competitors": ["Rivalsoap"], "use_search": True})
        assert icp.status_code == 201 and (await v.post(f"{API}/icps", json={"name": "x", "city": "A"})).status_code == 403
        icp_id = icp.json()["id"]
        assert (await r.post(f"{API}/icps", json={"name": "empty"})).status_code == 422
        run = (await r.post(f"{API}/runs", json={"icp_id": icp_id, "discovery_queries": ["Mtaani cleaning wholesalers Eldoret"]})).json()
        assert (await v.post(f"{API}/runs", json={"icp_id": icp_id})).status_code == 403
        assert run["llm_mode"] == "DETERMINISTIC" and run["search_state"] == "OK" and not any(s.get("error") for s in run["steps"])
        by = {c["company_name"]: c for c in run["candidates"]}
        assert f"Mama Mboga {t}" not in by                                                                          # existing customer excluded
        kib, duka, web = by["Kibanda Fresh Stores"], by["Duka Moja Supermarket"], by["Mtaani Cleaning Wholesalers"]
        d = next(s for s in run["steps"] if s["step"] == "discovery")
        assert d["duplicates_merged"] == 1 and kib["kind"] == "lead" and kib["crm_association"] == "EXISTING_LEAD" and kib["crm_record_id"]
        assert [c["company_name"] for c in run["candidates"]].count("Kibanda Fresh Stores") == 1                   # no duplicate of the CRM lead
        assert duka["crm_association"] == "NONE" and duka["score"] > 0.9 and duka["rationale"].startswith("Matches:")
        # citations, recency and unknowns
        assert duka["citations"][0]["url"].startswith("http://127.0.0.1:8765/site/duka-moja") and duka["citations"][0]["retrieved_at"]
        assert any(e["criterion"] == "web_presence" for e in duka["evidence"]) and any("Fair" in e["citation"] for e in duka["evidence"])
        assert duka["unknowns"] == [] and duka["evidence_age_days"] == 0      # unknowns list criteria fields the source lacks
        assert duka["competitor"]["assessment"] == "MENTIONED" and duka["competitor"]["mentions"][0]["competitor"] == "Rivalsoap"
        assert duka["competitor"]["mentions"][0]["citation"].startswith("http://127.0.0.1:8765/site/duka-moja")
        assert kib["competitor"]["assessment"] == "NONE_FOUND" and "not proof" in kib["competitor"]["note"]
        assert duka["territory"]["assessment"] == "SERVED" and duka["territory"]["customers_in_city"] >= 1
        # an unverified web hit is a low-confidence candidate that says what is unknown, never emailable
        assert web["kind"] == "web" and web["confidence"] == 0.2 and web["score"] == 0.2 and not web["can_propose_outreach"]
        assert any("not verified" in u or "identity" in u for u in web["unknowns"]) and web["evidence"][0]["criterion"] == "web_result"
        assert any(c["api"] == "brave" and c["country"] == "KE" for c in await sim_calls())
        # LLM path: adjustments clipped, ungrounded rationale dropped, unknown ids ignored
        def reply(prompt):
            items = json.loads(prompt[prompt.index("\n[") + 1:])
            out = [{"id": "ghost:1", "adjust": 0.1, "rationale": "invented [E1]"}]
            for it in items:
                if it["company"] == "Duka Moja Supermarket":
                    out.append({"id": it["id"], "adjust": -0.9, "rationale": "Retail in Nakuru [E1], no segment known."})
                elif it["company"] == "Kibanda Fresh Stores":
                    out.append({"id": it["id"], "adjust": 0.9, "rationale": "Great fit [E9] with huge sales."})       # cites evidence that does not exist
            return out
        fake = FakeLLM(reply)
        monkeypatch.setattr(ai_provider, "_instance", fake)
        run2 = (await r.post(f"{API}/runs", json={"icp_id": icp_id})).json()
        rk = next(s for s in run2["steps"] if s["step"] == "ranking")
        by2 = {c["company_name"]: c for c in run2["candidates"]}
        assert run2["llm_mode"] == "LLM" and run2["llm_model"] == "fake-llm-1" and rk["ungrounded_rationales_dropped"] == 1
        assert abs(by2["Duka Moja Supermarket"]["score"] - (min(1.0, duka["score"]) - 0.15)) < 0.02                # -0.9 clipped to -0.15
        assert by2["Duka Moja Supermarket"]["rationale"] == "Retail in Nakuru [E1], no segment known."
        assert by2["Kibanda Fresh Stores"]["rationale"].startswith("Matches:") and "huge sales" not in by2["Kibanda Fresh Stores"]["rationale"]
        assert "Use ONLY the evidence given" in fake.prompts[0] and "buy" not in fake.prompts[0].split("\n[", 1)[1]   # prompt holds evidence, no e-mail addresses
        monkeypatch.setattr(ai_provider, "_instance", FakeLLM(fail=True))
        run3 = (await r.post(f"{API}/runs", json={"icp_id": icp_id})).json()
        assert run3["llm_mode"] == "DETERMINISTIC" and "LLM unavailable" in next(s for s in run3["steps"] if s["step"] == "ranking")["error"]
        # outreach: grounded draft, proposal only, a different person approves, suppression applies
        monkeypatch.setattr(ai_provider, "_instance", ai_provider.MockProvider())
        assert (await r.post(f"{API}/candidates/{web['id']}/outreach", json={})).status_code == 409                # no e-mail: call or visit
        dr = (await r.post(f"{API}/candidates/{duka['id']}/draft")).json()
        assert "STOP" in dr["body"] and "Duka Moja Supermarket" in dr["body"] and "Rivalsoap" not in dr["body"] and dr["sources"]
        assert (await v.post(f"{API}/candidates/{duka['id']}/outreach", json={})).status_code == 403
        p = await r.post(f"{API}/candidates/{duka['id']}/outreach", json={})
        assert p.status_code == 201 and p.json()["status"] == "PENDING"
        assert (await r.post(f"{API}/candidates/{duka['id']}/outreach", json={})).status_code == 409               # already proposed
        async with AsyncSessionLocal() as db:
            n0 = len((await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == f"hello{t}@dukamoja.example.com"))).scalars().all())
            req = await db.get(AIActionRequest, uuid.UUID(p.json()["approval_request_id"]))
            assert n0 == 0 and req.status == "PENDING" and req.source == "PROSPECT"                                  # nothing sent or queued
            with pytest.raises(PermissionError):
                await pats.decide(db, req, await _as_user(db, rep), True)                                            # requester cannot approve
            await outbound.record_consent(db, f"hello{t}@dukamoja.example.com", "UNSUBSCRIBED", "test")             # unsubscribes before approval
            await pats.decide(db, req, await _as_user(db, approver), True)
            m = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.to_email == f"hello{t}@dukamoja.example.com"))).scalars().all()
            assert req.status == "DONE" and all(x.status not in ("SENT", "QUEUED") for x in m)                      # the outbox suppression gate wins
            await db.rollback()
        by_k = await r.post(f"{API}/candidates/{kib['id']}/outreach", json={"subject": "POVU range", "body": "Hello, our home care range. Reply STOP."})
        assert by_k.status_code == 201
        async with AsyncSessionLocal() as db:
            await outbound.record_consent(db, "stopped@kibanda.example.com", "UNSUBSCRIBED", "test")
            c = await db.get(__import__("app.models.m50_prospecting", fromlist=["M50Candidate"]).M50Candidate, uuid.UUID(by2["Duka Moja Supermarket"]["id"]))
            c.email = "stopped@kibanda.example.com"
            await db.commit()
        assert (await r.post(f"{API}/candidates/{by2['Duka Moja Supermarket']['id']}/outreach", json={})).status_code == 409   # refused at proposal time
        assert (await r.post(f"{API}/candidates/{web['id']}/dismiss")).status_code == 200


async def _as_user(db, ns):
    from app.models.user import User
    return await db.get(User, ns.id)


@DB
@pytest.mark.asyncio
async def test_agent_without_search_is_honest(monkeypatch):
    """Search not configured: the run still completes from CRM + imports, says so, and makes no provider call."""
    from sqlalchemy import delete
    from app.db.session import AsyncSessionLocal
    from app.models.customer_data import DataSource
    from app.services import ai_provider, customer_data_service as cds
    await ensure_tables()
    use_sim(monkeypatch)
    monkeypatch.setattr(ai_provider, "_instance", ai_provider.MockProvider())
    async with AsyncSessionLocal() as db:
        await db.execute(delete(DataSource))
        rep = await staff(db, "rep", ("crm.view", "crm.edit"))
        boss = await staff(db, "boss", ("crm.view", "crm.edit_all"))
        await cds.import_source(db, name="Fair2", license_note="own list", retention_days=30, user="rep",
                                rows=[{"n": "Kibanda Fresh Stores", "c": "Nakuru"}], mapping={"company_name": "n", "city": "c"})
        await db.commit()
    async with client_for(rep) as r, client_for(boss) as b:
        await b.put(f"{API}/settings/SEARCH", json={"provider": "brave", "enabled": False, "licensed": False, "retention_days": 30, "config": {}})
        icp = (await r.post(f"{API}/icps", json={"name": "n", "city": "Nakuru", "use_search": True})).json()["id"]
        run = (await r.post(f"{API}/runs", json={"icp_id": icp})).json()
        assert run["search_state"] == "NOT_CONFIGURED" and run["candidates"][0]["citations"] == []
        assert "web_presence" not in run["candidates"][0]["unknowns"]                                              # not searched, so nothing claimed either way
        assert await sim_calls() == [] and run["candidates"][0]["territory"]["assessment"] in ("SERVED", "WHITE_SPACE")
        assert run["candidates"][0]["competitor"]["assessment"] == "UNKNOWN"
