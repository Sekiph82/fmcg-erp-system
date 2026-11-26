"""Shared fixtures for the M48.S01.T001–T004 ad mutation tests (local simulator only, synthetic POVU data)."""
import os
import uuid
from decimal import Decimal

import httpx
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import ads_adapters as ads
from tests.provider_sim.ads_app import ads_sim_settings, create_ads_app

BASE = "http://ads.test"
PW = uuid.uuid4().hex + "Aa1!"
DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the disposable M48 PostgreSQL")

# Synthetic campaign content per provider (POVU home/personal care, example.com / povu-demo.test only).
SPECS = {
    "meta": ("OUTCOME_TRAFFIC", {"page_id": "100200300", "link": "https://povu-demo.test/allclean",
                                 "message": "POVU AllClean 1 L: one bottle for every surface.", "headline": "POVU AllClean",
                                 "country": "KE"}),
    "google": ("SEARCH", {"final_url": "https://povu-demo.test/hand-wash",
                          "headlines": ["POVU Hand Wash Powder", "1 kg Pouch Value Pack", "Gentle On Hands"],
                          "descriptions": ["POVU Hand Wash Powder 1 kg pouch for homes and shops.",
                                           "Order from your POVU distributor today."], "cpc_bid": "12.50"}),
    "linkedin": ("WEBSITE_VISIT", {"share_urn": "urn:li:share:7001", "geo_urn": "urn:li:geo:100710459", "unit_cost": "4.00"}),
    "tiktok": ("TRAFFIC", {"location_ids": ["192950"], "video_id": "v10033g50000povu", "identity_id": "povu-identity-1",
                           "ad_text": "POVU AllClean 1 L cleans kitchen and floor.", "landing_page_url": "https://povu-demo.test/allclean"}),
}
ACCOUNTS = {"meta": ("1001", "KES"), "google": ("444-555-6666", "KES"), "linkedin": ("5001", "USD"), "tiktok": ("7001", "KES")}


@pytest.fixture
def sim(monkeypatch):
    app = create_ads_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in ads_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "LINKEDIN_ADS_ACCESS_TIER", "standard")
    monkeypatch.setattr(settings, "ADS_MAX_DAILY_BUDGET", 1000.0)
    monkeypatch.setattr(ads, "BACKOFF", 0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def control(path: str, body=None):
    async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
        r = await (c.post(path, json=body) if body is not None else c.get(path))
        return r.json()


async def fault(provider: str, kind: str):
    await control("/_control", {"faults": {provider: [kind]}})


async def sim_objects(provider: str) -> dict:
    return {k: o for k, o in (await control("/_control/objects")).items() if o.get("provider") == provider}


def ctx(provider: str, name: str = "POVU AllClean launch (povu-test000001)", tag: str = "povu-test000001",
        budget: str = "60", ids=None) -> dict:
    ext, cur = ACCOUNTS[provider]
    obj, spec = SPECS[provider]
    return {"account": ext, "name": name, "tag": tag, "objective": obj, "budget": Decimal(budget), "currency": cur,
            "spec": spec, "ids": ids or {}}


async def create_chain(provider: str, tag: str = "povu-test000001") -> dict:
    """Create the full tree through the real builders + send(); returns {level: provider id}."""
    b, a, ids = ads.BUILDERS[provider], ads.ADAPTERS[provider], {}
    for lv in ads.LEVELS[provider]:
        x = ctx(provider, name=f"POVU AllClean {lv} ({tag})", tag=tag, ids=ids)
        body, headers = await ads.send(a, b.create(lv, x), safe=False)
        ids[lv] = b.parse_create(lv, body, headers)
    return ids


# ── DB / HTTP helpers ────────────────────────────────────────────────────────

def client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def make_user(db, perms: tuple, tag: str) -> str:
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test",
             full_name=tag.title(), hashed_password=hash_password(PW), is_active=True)
    role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
            await db.flush()
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    return u.username


async def login(c, username: str):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


async def setup_account(provider: str, daily_cap="500", monthly_cap="20000"):
    """Personas + one ad account with caps and members (admin work done directly in the DB)."""
    from app.db.session import AsyncSessionLocal
    from app.models.crm import AdAccount
    from app.models.m48_ads import AdAccountControl
    async with AsyncSessionLocal() as db:
        author = await make_user(db, ("marketing.view", "marketing.edit"), "author")
        approver = await make_user(db, ("marketing.view", "marketing.approve"), "approver")
        intruder = await make_user(db, ("marketing.view", "marketing.edit", "marketing.approve"), "intruder")
        outsider = await make_user(db, ("sales.view",), "outsider")
        cur = ACCOUNTS[provider][1]
        a = AdAccount(provider=provider, external_id=str(uuid.uuid4().int % 10**10), name=f"POVU {provider} sim", currency=cur)
        db.add(a)
        await db.flush()
        db.add(AdAccountControl(account_id=a.id, daily_cap=Decimal(daily_cap), monthly_cap=Decimal(monthly_cap),
                                members=[author, approver]))
        await db.commit()
        return {"account": str(a.id), "author": author, "approver": approver, "intruder": intruder, "outsider": outsider}


def campaign_body(provider: str, account: str, name: str, budget: str = "60") -> dict:
    obj, spec = SPECS[provider]
    return {"account_id": account, "idempotency_key": f"k-{uuid.uuid4().hex[:16]}", "name": name, "objective": obj,
            "daily_budget": budget, "spec": spec}


async def approve(ca, cb, rid: str, action: str) -> dict:
    r = await ca.post(f"/api/v1/ads/campaigns/{rid}/approvals", json={"action": action})
    assert r.status_code == 201, r.text
    ap = [x for x in r.json()["approvals"] if x["action"] == action and x["status"] == "PENDING"][-1]
    r = await cb.post(f"/api/v1/ads/approvals/{ap['id']}/decide", json={"ok": True})
    assert r.status_code == 200, r.text
    return r.json()


async def full_lifecycle(provider: str, sim_app) -> dict:
    """create → validate → approval → paused submit → resume (approved) → pause → budget v2 (approved) → submit.
    Returns the final tree. Also checks unauthorised, cross-account and approval-version refusals."""
    p = await setup_account(provider)
    async with client() as ca, client() as cb, client() as ci, client() as co:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        await login(ci, p["intruder"])
        await login(co, p["outsider"])
        assert (await co.get("/api/v1/ads/campaigns")).status_code == 403                    # no marketing permission
        body = campaign_body(provider, p["account"], f"POVU AllClean {provider} {uuid.uuid4().hex[:4]}")
        assert (await cb.post("/api/v1/ads/campaigns", json=body)).status_code == 403         # approver cannot draft
        assert (await ci.post("/api/v1/ads/campaigns", json=body)).status_code == 403         # not a member: cross-account
        r = await ca.post("/api/v1/ads/campaigns", json=body)
        assert r.status_code == 201, r.text
        t = r.json()
        assert (await ca.post("/api/v1/ads/campaigns", json=body)).json()["id"] == t["id"]    # same key, same tree
        rid = t["id"]
        assert t["status"] == "DRAFT" and t["mode"] == "SIMULATED" and "ADS_LIVE_MUTATIONS is off." in t["live_blockers"]
        assert [n["level"] for n in t["nodes"]] == list(ads.LEVELS[provider])
        assert t["actions"]["submit"] == "Needs an approved submit request."
        assert (await ci.post(f"/api/v1/ads/campaigns/{rid}/submit")).status_code == 403      # intruder: not a member
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/validate")
        assert r.json()["validation"]["ok"], r.json()["validation"]

        # approval: author cannot approve own; stale version refused
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/approvals", json={"action": "SUBMIT"})
        apid = [x for x in r.json()["approvals"] if x["status"] == "PENDING"][0]["id"]
        assert (await ca.post(f"/api/v1/ads/approvals/{apid}/decide", json={"ok": True})).status_code == 403
        assert (await cb.post(f"/api/v1/ads/approvals/{apid}/decide", json={"ok": True})).status_code == 200
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/budget", json={"daily_budget": "70"})   # version 2 after approval
        assert r.json()["budget_version"] == 2
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 409, r.text
        assert not await sim_objects(provider)                                                # nothing sent
        await _tamper_check(ca, cb, rid)

        before = len(await sim_objects(provider))
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["status"] == "PAUSED" and t["mode"] == "SIMULATED" and t["transport"] == "http"
        assert all(n["provider_id"] for n in t["nodes"])
        objs = await sim_objects(provider)
        assert len(objs) - before == len(ads.LEVELS[provider])
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")).status_code == 409    # nothing more to send

        # resume needs its own approval; then read-back confirms ACTIVE
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/resume")).status_code == 409
        await approve(ca, cb, rid, "RESUME")
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/resume")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ACTIVE"
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/pause")
        assert r.status_code == 200 and r.json()["status"] == "PAUSED", r.text

        # budget v3 → approval → push
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/budget", json={"daily_budget": "80"})
        assert r.json()["actions"]["submit"].startswith("Budget version 3 needs approval")
        await approve(ca, cb, rid, "BUDGET")
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["budget_pushed"] == 3

        # cap: 600/day would exceed the daily cap of 500
        await ca.post(f"/api/v1/ads/campaigns/{rid}/budget", json={"daily_budget": "600"})
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/approvals", json={"action": "BUDGET"})
        assert r.status_code in (409, 422) and ("cap" in r.text or "guardrail" in r.text), r.text

        led = (await ca.get(f"/api/v1/ads/campaigns/{rid}/mutations")).json()
        assert all(m["state"] == "SUCCEEDED" and m["mode"] == "SIMULATED" for m in led)
        assert "Authorization" not in str(led) and "Access-Token" not in str(led)          # no credentials stored
        return {"tree": t, "objs": await sim_objects(provider), "people": p, "ledger": led}


async def _tamper_check(ca, cb, rid: str):
    """Approve version 2, change the spec behind the API's back → submit refused (hash-bound approval);
    then restore and the approval works again."""
    import uuid as _u
    from app.db.session import AsyncSessionLocal
    from app.models.m48_ads import AdCampaignNode
    await approve(ca, cb, rid, "SUBMIT")
    async with AsyncSessionLocal() as db:
        root = await db.get(AdCampaignNode, _u.UUID(rid))
        good = dict(root.spec)
        root.spec = {**good, "tampered": "1"}
        await db.commit()
    r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
    assert r.status_code == 409 and "Approval was for" in r.text, r.text
    async with AsyncSessionLocal() as db:
        root = await db.get(AdCampaignNode, _u.UUID(rid))
        root.spec = good
        await db.commit()


async def unknown_then_reconcile(provider: str, level_fault: str = "unknown") -> dict:
    """The provider creates the object but the answer is lost (5xx). Submit stops as UNKNOWN, a second submit is
    refused, reconcile finds the object by read-back, the next submit continues: exactly one object per level."""
    p = await setup_account(provider)
    async with client() as ca, client() as cb:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        r = await ca.post("/api/v1/ads/campaigns", json=campaign_body(provider, p["account"], f"POVU Hand Wash {uuid.uuid4().hex[:4]}"))
        rid = r.json()["id"]
        await approve(ca, cb, rid, "SUBMIT")
        before = len(await sim_objects(provider))
        await fault(provider, level_fault)
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 504 and "UNKNOWN" in r.text, r.text
        t = (await ca.get("/api/v1/ads/campaigns", params={"account_id": p["account"]})).json()
        t = next(x for x in t if x["id"] == rid)
        assert t["status"] == "UNKNOWN" and t["pending_unknown"] == 1
        assert t["actions"]["submit"].startswith("An earlier call has an unknown outcome")
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 409 and "reconcile" in r.text.lower()                      # never re-sent blindly
        assert len(await sim_objects(provider)) - before == 1                              # it was created once
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")
        assert r.status_code == 200, r.text
        assert r.json()["nodes"][0]["provider_id"] and r.json()["pending_unknown"] == 0
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 200 and r.json()["status"] == "PAUSED", r.text
        assert len(await sim_objects(provider)) - before == len(ads.LEVELS[provider])      # no duplicate
        return r.json()


async def lost_then_retry(provider: str) -> None:
    """5xx without creating: reconcile finds nothing → FAILED → a new submit creates it once."""
    p = await setup_account(provider)
    async with client() as ca, client() as cb:
        await login(ca, p["author"])
        await login(cb, p["approver"])
        r = await ca.post("/api/v1/ads/campaigns", json=campaign_body(provider, p["account"], f"POVU Lost {uuid.uuid4().hex[:4]}"))
        rid = r.json()["id"]
        await approve(ca, cb, rid, "SUBMIT")
        before = len(await sim_objects(provider))
        await fault(provider, "lost")
        assert (await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")).status_code == 504
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/reconcile")
        assert r.status_code == 200 and r.json()["status"] == "FAILED", r.text
        r = await ca.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 200 and r.json()["status"] == "PAUSED", r.text
        assert len(await sim_objects(provider)) - before == len(ads.LEVELS[provider])
