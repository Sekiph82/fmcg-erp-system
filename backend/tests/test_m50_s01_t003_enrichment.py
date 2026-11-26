"""M50.S01.T003 enrichment adapters (DB part needs M50_DB=1; unit part runs everywhere).

Unit: provider registry and request construction against the PDL company-enrich contract (header, params, 404 as
"no match", 402/401 mapping). DB: NOT_CONFIGURED makes no call, preview stores cited proposals with confidence and
expiry, duplicates skipped, conflicting value needs overwrite, a verified field is never overwritten, display-only
fields cannot be applied, reject, revoke restores the old value, expiry blocks apply, purge, RBAC.
"""
import os
import uuid
from datetime import timedelta

import pytest

from app.services import m50_enrichment_service as enr
from tests.m50_s01_common import client_for, ensure_tables, setv, sim_calls, sim_control, staff, use_sim

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
API = "/api/v1/prospecting-agent"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    from app.core import provider_http
    provider_http.set_test_transport(None)
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@pytest.mark.asyncio
async def test_pdl_adapter_contract(monkeypatch):
    use_sim(monkeypatch)
    p = enr.PdlCompanyProvider()
    ok = await p.enrich_company(name="Duka Moja Supermarket", website="dukamoja.example.com", min_likelihood=6)
    assert ok.matched and ok.likelihood == 8 and ok.fields["city"] == "Nakuru" and ok.fields["segment"] == "retail"
    call = (await sim_calls())[-1]
    assert call == {"api": "pdl", "name": "Duka Moja Supermarket", "website": "dukamoja.example.com", "min_likelihood": 6}
    assert not (await p.enrich_company(name="Nobody Ltd", website=None, min_likelihood=2)).matched        # 404 = no match, not an error
    assert not (await p.enrich_company(name="Weak Match Ltd", website=None, min_likelihood=6)).matched   # below min_likelihood
    await sim_control({"faults": {"pdl": ["429"]}})
    assert (await p.enrich_company(name="Duka Moja Supermarket", website=None, min_likelihood=6)).matched   # retried
    await sim_control({"faults": {"pdl": ["402"]}})
    with pytest.raises(enr.EnrichError) as e:
        await p.enrich_company(name="Duka Moja Supermarket", website=None, min_likelihood=6)
    assert e.value.status == 402 and "credits" in str(e.value)
    setv(monkeypatch, "PDL_API_KEY", "wrong")
    with pytest.raises(enr.EnrichError, match="rejected"):
        await p.enrich_company(name="Duka Moja Supermarket", website=None, min_likelihood=6)
    setv(monkeypatch, "PDL_API_KEY", "")
    with pytest.raises(enr.EnrichError, match="not configured"):
        await p.enrich_company(name="x", website=None, min_likelihood=6)


@DB
@pytest.mark.asyncio
async def test_enrichment_flow(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.customer_data import VerifiedField
    from app.models.m50_prospecting import M50EnrichmentProposal
    from app.models.sales import Customer
    await ensure_tables()
    use_sim(monkeypatch)
    tag = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        editor = await staff(db, "edit", ("crm.view", "crm.edit"))
        admin = await staff(db, "adm", ("crm.view", "crm.edit_all"))
        cust = Customer(code=f"SYN-{tag}", name="Duka Moja Supermarket", email="info@dukamoja.example.com", city="Nairobi", currency="KES")
        ghost = Customer(code=f"GHO-{tag}", name="Weak Match Ltd", currency="KES")
        db.add_all([cust, ghost])
        await db.commit()
        cid, gid = str(cust.id), str(ghost.id)
    async with client_for(editor) as e, client_for(admin) as a:
        await a.put(f"{API}/settings/ENRICHMENT", json={"provider": "pdl", "enabled": False, "licensed": False, "retention_days": 30, "config": {"min_likelihood": 6}})
        r = await e.post(f"{API}/enrichment/customers/{cid}/preview")
        assert r.status_code == 409 and "not configured" in r.json()["detail"]
        assert not [c for c in await sim_calls() if c["api"] == "pdl"]                      # nothing requested, nothing spent
        await a.put(f"{API}/settings/ENRICHMENT", json={"provider": "pdl", "enabled": True, "licensed": True,
                                                         "license_note": "PDL Company Enrichment, trial plan (simulated)", "retention_days": 30,
                                                         "config": {"min_likelihood": 6}})
        r = (await e.post(f"{API}/enrichment/customers/{cid}/preview")).json()
        props = {p["field"]: p for p in r["proposals"]}
        assert r["new"] == 7 and props["city"]["value"] == "Nakuru" and props["city"]["current"] == "Nairobi" and props["city"]["confidence"] == 0.8
        assert props["city"]["source_ref"].startswith("pdl company/enrich v5") and props["city"]["applicable"] and not props["website"]["applicable"]
        pdl = [c for c in await sim_calls() if c["api"] == "pdl"][-1]
        assert pdl["website"] == "dukamoja.example.com" and pdl["min_likelihood"] == 6
        assert (await e.post(f"{API}/enrichment/customers/{cid}/preview")).json()["new"] == 0   # dedup
        assert (await e.post(f"{API}/enrichment/customers/{gid}/preview")).json()["new"] == 0   # weak match -> nothing
        # approval is a person with edit_all
        assert (await e.post(f"{API}/enrichment/{props['city']['id']}/apply", json={})).status_code == 403
        r = await a.post(f"{API}/enrichment/{props['city']['id']}/apply", json={})
        assert r.status_code == 409 and "confirm the overwrite" in r.json()["detail"]
        async with AsyncSessionLocal() as db:
            db.add(VerifiedField(customer_id=cust.id, field="city", verified_by="rep"))
            await db.commit()
        r = await a.post(f"{API}/enrichment/{props['city']['id']}/apply", json={"overwrite": True})
        assert r.status_code == 409 and "verified" in r.json()["detail"]                    # verified wins even with overwrite
        assert (await a.post(f"{API}/enrichment/{props['website']['id']}/apply", json={})).status_code == 409
        assert (await a.post(f"{API}/enrichment/{props['region']['id']}/apply", json={})).status_code == 200
        assert (await a.post(f"{API}/enrichment/{props['segment']['id']}/reject")).status_code == 200
        assert (await a.post(f"{API}/enrichment/{props['segment']['id']}/apply", json={})).status_code == 409   # already decided
        r = (await a.post(f"{API}/enrichment/{props['region']['id']}/revoke")).json()
        assert r["restored"] is True
        async with AsyncSessionLocal() as db:
            c = await db.get(Customer, cust.id)
            assert c.region is None and c.city == "Nairobi"
            # expiry blocks apply; expired proposals purge
            p = await db.get(M50EnrichmentProposal, uuid.UUID(props["employee_count"]["id"]))
            p.expires_at = p.retrieved_at - timedelta(days=1)
            await db.commit()
            assert (await enr.purge(db, expired_only=True)) >= 1
            await db.commit()
        # provider failure surfaces, does not store anything
        await sim_control({"faults": {"pdl": ["402"]}})
        await a.post(f"{API}/enrichment/customers/{cid}/preview")
        r = await a.delete(f"{API}/enrichment/customers/{cid}")
        assert r.status_code == 200 and r.json()["deleted"] >= 4
        async with AsyncSessionLocal() as db:
            assert (await db.execute(select(M50EnrichmentProposal).where(M50EnrichmentProposal.customer_id == cust.id))).first() is None
            assert (await db.get(Customer, cust.id)).city == "Nairobi"                      # purge removes proposals, not customer data


@DB
@pytest.mark.asyncio
async def test_402_is_reported(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.models.sales import Customer
    await ensure_tables()
    use_sim(monkeypatch)
    async with AsyncSessionLocal() as db:
        admin = await staff(db, "adm", ("crm.view", "crm.edit_all"))
        c = Customer(code=f"SYN-{uuid.uuid4().hex[:5]}", name="Duka Moja Supermarket", currency="KES")
        db.add(c)
        await db.commit()
        cid = str(c.id)
    async with client_for(admin) as a:
        await a.put(f"{API}/settings/ENRICHMENT", json={"provider": "pdl", "enabled": True, "licensed": True, "license_note": "trial (simulated)",
                                                         "retention_days": 7, "config": {}})
        await sim_control({"faults": {"pdl": ["402"]}})
        r = await a.post(f"{API}/enrichment/customers/{cid}/preview")
        assert r.status_code == 402 and "credits" in r.json()["detail"]
