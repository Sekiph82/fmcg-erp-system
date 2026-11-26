"""M50.S01.T004 third-party buyer-intent feed (DB part needs M50_DB=1).

NOT_CONFIGURED import is refused; schema mapping with scale; company-level identity resolution only (domain, exact
name, ambiguous = unresolved); person fields dropped; duplicates, stale and weak events skipped; decay by half-life;
alert once per cool-down; consent withdrawal stops scoring and removes the open alert; expiry purge; first-party and
third-party scores are returned separately.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tests.m50_s01_common import client_for, ensure_tables, staff

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
API = "/api/v1/prospecting-agent"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


@DB
@pytest.mark.asyncio
async def test_intent_feed_flow():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.m50_prospecting import M50IntentAlert, M50IntentEvent
    from app.models.sales import Customer
    from app.services import m50_intent_service as intent
    await ensure_tables()
    t = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        viewer = await staff(db, "view", ("crm.view",))
        admin = await staff(db, "adm", ("crm.view", "crm.edit_all"))
        a = Customer(code=f"A-{t}", name=f"Duka Moja {t} Supermarket", email=f"info@dukamoja{t}.example.com", currency="KES")
        b = Customer(code=f"B-{t}", name=f"Kibanda {t} Fresh Stores", currency="KES")
        t1 = Customer(code=f"T1-{t}", name=f"Twin One {t}", email=f"a@twin{t}.example.com", currency="KES")
        t2 = Customer(code=f"T2-{t}", name=f"Twin Two {t}", email=f"b@twin{t}.example.com", currency="KES")
        db.add_all([a, b, t1, t2])
        await db.commit()
        aid, bid = str(a.id), str(b.id)
    feed = f"sim-feed-{t}"
    ev = [
        {"company_name": f"Duka Moja {t} Supermarket", "domain": f"www.dukamoja{t}.example.com", "topic": "bulk detergent", "strength": 0.9, "observed_at": _iso(2)},
        {"company_name": f"Duka Moja {t} Supermarket", "domain": f"dukamoja{t}.example.com", "topic": "dish soap", "strength": 0.8, "observed_at": _iso(2)},
        {"company_name": f"Duka Moja {t} Supermarket", "domain": f"dukamoja{t}.example.com", "topic": "bulk detergent", "strength": 0.9, "observed_at": _iso(2)},   # duplicate
        {"company_name": f"Kibanda {t} Fresh Stores", "topic": "hand wash", "strength": 0.8, "observed_at": _iso(1)},
        {"company_name": "Old Co", "topic": "bulk detergent", "strength": 0.9, "observed_at": _iso(120)},                                   # stale
        {"company_name": "Faint Co", "topic": "bulk detergent", "strength": 0.05, "observed_at": _iso(1)},                                  # weak
        {"company_name": "Nobody Ltd", "topic": "bulk detergent", "strength": 0.7, "observed_at": _iso(1),
         "email": "someone@nobody.example.com", "person_name": "A. Person", "ip": "198.51.100.4"},                                          # person fields, unresolved
        {"company_name": "Twin Co", "domain": f"twin{t}.example.com", "topic": "bulk detergent", "strength": 0.7, "observed_at": _iso(1)},  # domain of two customers: not unique
        {"company_name": "No Topic Ltd", "strength": 0.9, "observed_at": _iso(1)},                                                          # invalid
    ]
    async with client_for(viewer) as v, client_for(admin) as ad:
        await ad.put(f"{API}/settings/INTENT", json={"provider": "generic-feed", "enabled": False, "licensed": False, "retention_days": 90, "config": {}})
        r = await ad.post(f"{API}/intent/import", json={"feed": feed, "consent_basis": "vendor licence L-1 (simulated)", "events": ev})
        assert r.status_code == 409 and "not configured" in r.json()["detail"]
        await ad.put(f"{API}/settings/INTENT", json={"provider": "generic-feed", "enabled": True, "licensed": True, "license_note": "vendor licence L-1 (simulated)",
                                                      "retention_days": 90, "config": {}})
        assert (await v.post(f"{API}/intent/import", json={"feed": feed, "consent_basis": "x" * 5, "events": ev})).status_code == 403
        r = (await ad.post(f"{API}/intent/import", json={"feed": feed, "consent_basis": "vendor licence L-1 (simulated)", "events": ev})).json()
        assert r == {"stored": 5, "duplicates": 1, "stale": 1, "weak": 1, "invalid": 1, "unresolved": 2, "person_fields_dropped": 3, "alerts": 1}
        # mapping + scale: a vendor's own column names, strength 0..100
        await ad.put(f"{API}/settings/INTENT", json={"provider": "generic-feed", "enabled": True, "licensed": True, "license_note": "vendor licence L-1 (simulated)",
                                                      "retention_days": 90, "config": {"scale_max": 100}})
        r = (await ad.post(f"{API}/intent/import", json={"feed": feed + "-m", "consent_basis": "vendor licence L-2", "mapping": {
            "company_name": "org", "topic": "interest", "strength": "score", "observed_at": "seen", "domain": "site"},
            "events": [{"org": f"Kibanda {t} Fresh Stores", "interest": "floor cleaner", "score": 70, "seen": _iso(1), "site": ""}]})).json()
        assert r["stored"] == 1
        async with AsyncSessionLocal() as db:
            rows = {e.topic: e for e in (await db.execute(select(M50IntentEvent).where(M50IntentEvent.feed.like(f"{feed}%")))).scalars()}
            assert rows["bulk detergent"].match_method in ("DOMAIN", "NONE") and rows["dish soap"].match_method == "DOMAIN" and rows["dish soap"].match_confidence == 0.9
            assert rows["hand wash"].match_method == "NAME" and rows["hand wash"].match_confidence == 0.6 and rows["floor cleaner"].strength == 0.7
            assert not any(hasattr(M50IntentEvent, f) for f in ("email", "person_name", "ip"))     # no person identity is storable
            # decay: 14 days later the same events score about half
            s0, s14 = await intent.score(db, a.id), await intent.score(db, a.id, datetime.now(timezone.utc) + timedelta(days=14))
            assert 60 < s0["score"] < 70 and abs(s14["score"] - s0["score"] / 2) < 1.5
            assert all(e["match"] == "DOMAIN" and e["consent_basis"] for e in s0["events"])
            assert (await db.execute(select(func.count()).select_from(M50IntentAlert).where(M50IntentAlert.customer_id == a.id))).scalar_one() == 1
            assert await intent.evaluate(db, a.id) == 0                                            # cool-down: no second alert
            await db.rollback()
        alerts = (await ad.get(f"{API}/intent/alerts")).json()
        mine = [x for x in alerts if x["customer_id"] == aid]
        assert len(mine) == 1 and mine[0]["score"] >= 40 and "bulk detergent" in " ".join(mine[0]["reasons"])
        both = (await v.get(f"{API}/intent/customers/{aid}")).json()
        assert set(both) == {"first_party", "third_party"} and both["third_party"]["source"].startswith("third-party") and both["third_party"]["score"] > 60
        assert both["first_party"] != both["third_party"]
        # consent withdrawn: scoring stops at once, the open alert goes
        r = (await ad.post(f"{API}/intent/withdraw", json={"feed": feed})).json()
        assert r["withdrawn"] == 5
        assert r["alerts_removed"] == 2        # Duka Moja, and Kibanda (its remaining feed alone is below the threshold)
        assert (await v.get(f"{API}/intent/customers/{aid}")).json()["third_party"]["score"] == 0
        assert (await v.get(f"{API}/intent/customers/{bid}")).json()["third_party"]["score"] > 0     # the other feed is untouched
        assert (await ad.post(f"{API}/intent/withdraw", json={})).status_code == 422
        # expiry + purge
        async with AsyncSessionLocal() as db:
            for e in (await db.execute(select(M50IntentEvent).where(M50IntentEvent.feed == feed + "-m"))).scalars():
                e.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            await db.commit()
        assert (await v.get(f"{API}/intent/customers/{bid}")).json()["third_party"]["score"] == 0      # expired events do not score even before purge
        assert (await ad.delete(f"{API}/intent/expired")).json()["deleted"] >= 4                        # expired + withdrawn
