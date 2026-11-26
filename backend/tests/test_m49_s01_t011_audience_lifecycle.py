"""M49.S01.T011 audience lifecycle on Meta / Google (Data Manager API) / LinkedIn / TikTok against the local simulator
(synthetic POVU data, hashed identifiers only). Needs the disposable PostgreSQL: M49_DB=1."""
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import delete, select

from app.core import provider_http
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.services import ads_adapters as ads
from app.services import audience_sync_adapters as ad
from tests.m48_ads_support import BASE, client, control, login, setup_account
from tests.m49_audience_support import M49, mount
from tests.provider_sim.ads_app import ads_sim_settings
from tests.provider_sim.audience_sync_app import create_audience_sync_app

PROVIDERS = ["meta", "google", "linkedin", "tiktok"]
API = "/api/v1/audience-sync"
mount()


@pytest.fixture
def sim(monkeypatch):
    app = create_audience_sync_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    for k, v in ads_sim_settings(BASE).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "LINKEDIN_ADS_ACCESS_TIER", "standard")
    monkeypatch.setattr(settings, "AUDIENCE_EXPORT_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_DATA_MANAGER_API_URL", f"{BASE}/datamanager")
    monkeypatch.setattr(settings, "GOOGLE_CUSTOMER_MATCH_TOS_ACCEPTED", True)
    monkeypatch.setattr(ads, "BACKOFF", 0)
    monkeypatch.setattr(ad, "LI_WAIT", 0)
    monkeypatch.setitem(ad.MINIMUMS, "tiktok", (3, True, "TikTok test minimum"))     # documented 1,000; small for the simulator
    monkeypatch.setitem(ad.MINIMUMS, "meta", (3, False, "Meta test minimum"))        # documented 100
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


@pytest.fixture(autouse=True)
async def _dispose():
    yield
    await engine.dispose()


async def make_people(tag: str, n_ok: int = 4) -> list[str]:
    """n_ok consented customers and one who unsubscribed, all in one city so a rule finds exactly them."""
    from app.models.crm import CRMContactConsent
    from app.models.sales import Customer
    now, emails = datetime.now(timezone.utc), []
    async with AsyncSessionLocal() as db:
        for i in range(n_ok + 1):
            e = f"duka{i}-{tag}@povu-demo.test"
            db.add(Customer(code=f"M49-{tag}-{i}", name=f"Duka {tag} {i}", email=e, phone=f"0712{(int(tag, 16) * 10 + i) % 10**6:06d}", city=f"City-{tag}"))
            db.add(CRMContactConsent(email=e, status="SUBSCRIBED" if i < n_ok else "UNSUBSCRIBED", updated_at=now))
            emails.append(e)
        await db.commit()
    return emails


async def add_person(tag: str, i: int) -> str:
    from app.models.crm import CRMContactConsent
    from app.models.sales import Customer
    e = f"duka{i}-{tag}@povu-demo.test"
    async with AsyncSessionLocal() as db:
        db.add(Customer(code=f"M49-{tag}-{i}", name=f"Duka {tag} {i}", email=e, city=f"City-{tag}"))
        db.add(CRMContactConsent(email=e, status="SUBSCRIBED", updated_at=datetime.now(timezone.utc)))
        await db.commit()
    return e


async def set_city(email: str, city: str) -> None:
    from app.models.sales import Customer
    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(Customer).where(Customer.email == email))).scalar_one()
        c.city = city
        await db.commit()


async def sim_aud(provider: str, deleted: bool = False) -> dict:
    return {k: v for k, v in (await control("/_control/audiences")).items() if v["provider"] == provider and v["deleted"] == deleted}


def hashes(*emails) -> set:
    return {ads.hash_email(e) for e in emails}


async def approve_and_sync(ca, cb, sid: str) -> dict:
    r = await ca.post(f"{API}/{sid}/approvals")
    assert r.status_code == 200, r.text
    assert (await cb.post(f"{API}/{sid}/decide", json={"ok": True})).status_code == 200
    r = await ca.post(f"{API}/{sid}/sync")
    assert r.status_code == 200, r.text
    return r.json()


@M49
@pytest.mark.parametrize("provider", PROVIDERS)
async def test_t011_full_lifecycle_per_provider(provider, sim):
    tag = uuid.uuid4().hex[:6]
    async with client() as ca, client() as cb, client() as ci, client() as co:
        p0 = await setup_account(provider)          # personas first so we can log in as the author
        await login(ca, p0["author"])
        await login(cb, p0["approver"])
        await login(ci, p0["intruder"])
        await login(co, p0["outsider"])
        await control("/_control", {"tiktok_min": 3})
        emails = await make_people(tag)
        r = await ca.post("/api/v1/audiences", json={"name": f"POVU AllClean buyers {tag}", "require_consent": False,
                                                       "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})
        assert r.status_code == 201 and r.json()["member_count"] == 5, r.text
        aid, acct = r.json()["id"], p0["account"]

        # roles: no marketing permission → refused; not a member of the ad account → refused; both visible
        assert (await co.get(API)).status_code == 403
        assert (await ci.post(API, json={"audience_id": aid, "account_id": acct})).status_code == 403
        listing = (await ci.get(API)).json()
        row = next(a for a in listing["accounts"] if a["id"] == acct)
        assert row["member"] is False and "not a member" in row["refusal"] and not [s for s in listing["syncs"] if s["account_id"] == acct]

        r = await ca.post(API, json={"audience_id": aid, "account_id": acct})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        assert (await ca.post(API, json={"audience_id": aid, "account_id": acct})).status_code == 409      # one list per account
        assert (await ci.get(f"{API}/{sid}/preview")).status_code == 403

        # preview: consented members only (the unsubscribed one is excluded even though the local list holds them)
        pv = (await ca.get(f"{API}/{sid}/preview")).json()
        assert pv["add"] == 4 and pv["remove"] == 0 and not pv["eligibility"]["blocking"] and pv["eligibility"]["minimum"]
        assert all("***@povu-demo.test" in x for x in pv["sample_add"])
        assert not await sim_aud(provider)                                                            # nothing sent by a preview

        # approval gates the upload
        assert (await ca.post(f"{API}/{sid}/sync")).status_code == 409
        assert (await ca.post(f"{API}/{sid}/approvals")).status_code == 200
        assert (await ca.post(f"{API}/{sid}/decide", json={"ok": True})).status_code == 403            # author cannot approve
        assert (await cb.post(f"{API}/{sid}/decide", json={"ok": True})).status_code == 200
        r = await ca.post(f"{API}/{sid}/sync")
        assert r.status_code == 200, r.text
        s = r.json()["sync"]
        assert s["mode"] == "SIMULATED" and s["external_id"] and s["status"] in ("PROCESSING", "READY")
        assert "ADS_LIVE_MUTATIONS is off." in s["gate"]["reasons"] and s["members"] == {"IN_SYNC": 4}
        live = await sim_aud(provider)
        assert len(live) == 1 and set(next(iter(live.values()))["members"]) == hashes(*emails[:4])
        r = await ca.post(f"{API}/{sid}/poll")
        assert r.status_code == 200 and r.json()["sync"]["status"] == "READY", r.text                 # the provider said so
        wire = json.dumps(await control("/_control/calls"))
        for raw in [*emails, "Duka", "0712"]:
            assert raw not in wire                                                                    # no raw PII left the ERP
        assert (await ca.post(f"{API}/{sid}/sync")).status_code == 409                                # approval is single-use

        # membership diff: one leaves the segment, two join; an approval goes stale when the segment changes
        await set_city(emails[0], "elsewhere")
        e5, e6 = await add_person(tag, 5), await add_person(tag, 6)
        assert (await ca.post(f"/api/v1/audiences/{aid}/recompute")).status_code == 200
        pv = (await ca.get(f"{API}/{sid}/preview")).json()
        assert (pv["add"], pv["remove"]) == (2, 1)
        assert (await ca.post(f"{API}/{sid}/approvals")).status_code == 200
        e7 = await add_person(tag, 7)
        await ca.post(f"/api/v1/audiences/{aid}/recompute")
        r = await cb.post(f"{API}/{sid}/decide", json={"ok": True})
        assert r.status_code == 409 and "changed" in r.text, r.text
        s = await approve_and_sync(ca, cb, sid)
        assert s["added"] == 3 and s["removed"] == 1
        assert set(next(iter((await sim_aud(provider)).values()))["members"]) == hashes(*emails[1:4], e5, e6, e7)

        # consent withdrawal: removed from the platform, suppressed, unsubscribed, never sent again
        r = await ca.post(f"{API}/consent-withdrawal", json={"email": emails[1].upper()})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["suppressed"] and out["removed"][0]["result"].startswith("REMOVED"), out
        assert set(next(iter((await sim_aud(provider)).values()))["members"]) == hashes(*emails[2:4], e5, e6, e7)
        from app.models.crm import CRMContactConsent
        from app.models.m49_audiences import AudienceSuppression, AudienceSyncMember
        async with AsyncSessionLocal() as db:
            assert (await db.execute(select(CRMContactConsent.status).where(CRMContactConsent.email == emails[1]))).scalar_one() == "UNSUBSCRIBED"
            assert await db.get(AudienceSuppression, ads.hash_email(emails[1])) is not None
            rows = (await db.execute(select(AudienceSyncMember).where(AudienceSyncMember.sync_id == uuid.UUID(sid)))).scalars().all()
            assert all(len(m.email_sha256) == 64 for m in rows)
            assert next(m for m in rows if m.email_sha256 == ads.hash_email(emails[1])).state == "REMOVED"
        pv = (await ca.get(f"{API}/{sid}/preview")).json()
        assert (pv["add"], pv["remove"]) == (0, 0)
        assert (await ca.get(f"{API}/{sid}")).json()["members"]["REMOVED"] == 2

        if provider == "tiktok":      # TikTok cannot shrink below its minimum: the list is deleted to honour the withdrawal
            await ca.post(f"{API}/consent-withdrawal", json={"email": emails[2]})
            await ca.post(f"{API}/consent-withdrawal", json={"email": emails[3]})
            r = await ca.post(f"{API}/consent-withdrawal", json={"email": e5})
            assert "AUDIENCE DELETED" in json.dumps(r.json()), r.text
            assert (await ca.get(f"{API}/{sid}")).json()["status"] == "DELETED" and not await sim_aud("tiktok")
        else:
            r = await ca.delete(f"{API}/{sid}")
            assert r.status_code == 200 and r.json()["sync"]["status"] == "DELETED", r.text
            assert not await sim_aud(provider) and len(await sim_aud(provider, deleted=True)) == 1
            assert (await ca.delete(f"{API}/{sid}")).status_code == 200                                # idempotent
            assert (await ca.post(f"{API}/{sid}/sync")).status_code == 409


@M49
async def test_t011_unknown_create_outcome_is_reconciled_not_resent(sim):
    tag = uuid.uuid4().hex[:6]
    async with client() as ca, client() as cb:
        p = await setup_account("meta")
        await login(ca, p["author"])
        await login(cb, p["approver"])
        await make_people(tag)
        aid = (await ca.post("/api/v1/audiences", json={"name": f"POVU Hand Wash {tag}", "require_consent": True,
                                                          "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})).json()["id"]
        sid = (await ca.post(API, json={"audience_id": aid, "account_id": p["account"]})).json()["id"]
        assert (await ca.post(f"{API}/{sid}/approvals")).status_code == 200
        assert (await cb.post(f"{API}/{sid}/decide", json={"ok": True})).status_code == 200
        await control("/_control", {"faults": {"meta": ["unknown"]}})
        r = await ca.post(f"{API}/{sid}/sync")
        assert r.status_code == 504 and "UNKNOWN" in r.text, r.text            # created but the answer was lost
        assert len(await sim_aud("meta")) == 1
        assert (await ca.get(f"{API}/{sid}")).json()["status"] == "UNKNOWN"
        r = await ca.post(f"{API}/{sid}/sync")
        assert r.status_code == 409 and "reconcile" in r.text.lower()          # never re-sent blindly
        r = await ca.post(f"{API}/{sid}/reconcile")
        assert r.status_code == 200, r.text
        assert len(await sim_aud("meta")) == 1                                 # found by name, not created twice
        assert set(next(iter((await sim_aud("meta")).values()))["members"]) == hashes(*[f"duka{i}-{tag}@povu-demo.test" for i in range(4)])
        r = await ca.post(f"{API}/{sid}/poll")
        assert r.json()["sync"]["status"] == "READY" and r.json()["sync"]["members"] == {"IN_SYNC": 4}


@M49
async def test_t011_lookalike_only_where_documented_and_local_score_is_labelled(sim):
    tag = uuid.uuid4().hex[:6]
    async with client() as ca, client() as cb:
        p = await setup_account("meta")
        await login(ca, p["author"])
        await login(cb, p["approver"])
        await make_people(tag)
        aid = (await ca.post("/api/v1/audiences", json={"name": f"POVU Personal Care {tag}", "require_consent": True,
                                                          "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})).json()["id"]
        sid = (await ca.post(API, json={"audience_id": aid, "account_id": p["account"]})).json()["id"]
        r = await ca.post(f"{API}/lookalike", json={"origin_sync_id": sid, "ratio": 0.02})      # seed not on the provider yet
        assert r.status_code == 201
        lid = r.json()["id"]
        assert (await ca.post(f"{API}/{lid}/approvals")).status_code == 409                    # simulation never invents a lookalike
        await approve_and_sync(ca, cb, sid)
        await control("/_control", {"meta_lookalike_min": 5})
        assert (await ca.post(f"{API}/{lid}/approvals")).status_code == 200                    # local check uses the documented seed minimum
        assert (await cb.post(f"{API}/{lid}/decide", json={"ok": True})).status_code == 200
        r = await ca.post(f"{API}/{lid}/sync")
        assert r.status_code == 422 and "100 members" in r.text, r.text                        # provider refuses the small seed: surfaced
        await control("/_control", {"meta_lookalike_min": 3})
        r = await ca.post(f"{API}/{lid}/sync")
        assert r.status_code == 200, r.text
        assert [a for a in (await control("/_control/audiences")).values() if a["kind"] == "LOOKALIKE"]
        assert (await ca.post(f"{API}/{lid}/poll")).json()["sync"]["status"] in ("PROCESSING", "READY")
        # the M44 local similarity score keeps its own label
        sim_out = (await ca.get(f"/api/v1/audiences/{aid}/similar")).json()
        assert "local similarity score" in sim_out["label"] and "not an ad-platform lookalike" in sim_out["label"]

    for prov in ("google", "linkedin", "tiktok"):
        async with client() as ca:
            p = await setup_account(prov)
            await login(ca, p["author"])
            sid = (await ca.post(API, json={"audience_id": aid, "account_id": p["account"]})).json()["id"]
            r = await ca.post(f"{API}/lookalike", json={"origin_sync_id": sid, "ratio": 0.01})
            assert r.status_code == 422 and "documents no lookalike API" in r.text, (prov, r.text)
            assert not [a for a in (await sim_aud(prov)).values() if a["kind"] == "LOOKALIKE"]
    caps = {c["provider"]: c for c in (await _caps())["providers"]}
    assert caps["meta"]["operations"]["lookalike"] and not any(caps[x]["operations"]["lookalike"] for x in ("google", "linkedin", "tiktok"))
    assert caps["linkedin"]["operations"]["conversions"] is False and caps["meta"]["operations"]["conversions"] is True


async def _caps():
    async with client() as c:
        p = await setup_account("meta")
        await login(c, p["author"])
        return (await c.get(f"{API}/capabilities")).json()


@M49
async def test_t011_eligibility_blocks_and_export_switch_fails_closed(sim, monkeypatch):
    tag = uuid.uuid4().hex[:6]
    async with client() as ca, client() as cb:
        p = await setup_account("tiktok")
        await login(ca, p["author"])
        await login(cb, p["approver"])
        await make_people(tag)
        aid = (await ca.post("/api/v1/audiences", json={"name": f"POVU Dish Soap {tag}", "require_consent": True,
                                                          "rules": {"all": [{"field": "city", "op": "eq", "value": f"City-{tag}"}]}})).json()["id"]
        sid = (await ca.post(API, json={"audience_id": aid, "account_id": p["account"]})).json()["id"]
        monkeypatch.setitem(ad.MINIMUMS, "tiktok", (1000, True, "TikTok: an audience update fails if the resulting size is below 1,000 (documented)."))
        r = await ca.post(f"{API}/{sid}/approvals")
        assert r.status_code == 422 and "1,000" in r.text, r.text                                # documented minimum blocks, nothing sent
        monkeypatch.setitem(ad.MINIMUMS, "tiktok", (3, True, "test"))
        assert (await ca.post(f"{API}/{sid}/approvals")).status_code == 200
        assert (await cb.post(f"{API}/{sid}/decide", json={"ok": True})).status_code == 200
        monkeypatch.setattr(settings, "AUDIENCE_EXPORT_ENABLED", False)
        r = await ca.post(f"{API}/{sid}/sync")
        assert r.status_code == 409 and "AUDIENCE_EXPORT_ENABLED" in r.text, r.text
        assert not (await control("/_control/calls"))
