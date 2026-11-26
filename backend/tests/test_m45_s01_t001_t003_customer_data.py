"""M45.S01.T001 prospecting, T002 research, T003 enrichment and business cards (unit; DB part needs M45_DB=1).

Unit: normalization (Kenyan phones, KRA PIN, names), scoring with evidence and unknowns, outreach drafts built only
from evidence, business-card parsing. DB: import with licence note and retention; ranked prospects exclude existing
customers and cite rows; outreach only creates an approval request; research collects cited facts, shows conflicts
and unknowns, never overwrites a verified field or a different value without overwrite; expired sources purge.
"""
import os
import uuid
from datetime import timedelta

import pytest

from app.services import customer_data_service as cds

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_normalization_and_scoring():
    assert cds.norm_phone("0712 345 678") == "+254712345678" and cds.norm_phone("+254 712 345678") == "+254712345678"
    assert cds.norm_tax("p051234567z") == "P051234567Z" and cds.norm_tax("123") is None
    assert cds.norm_name("Duka Moja Enterprises Ltd") == cds.norm_name("duka moja") == "duka moja"
    p = {"company_name": "Kibanda Fresh", "city": "Nakuru", "channel": None, "segment": "kiosk", "size_band": "S",
         "notes": "near bus stage", "citation": "Fair 2026, row 3"}
    s, ev, conf, unknown = cds.score(p, {"city": "nakuru", "channel": "RETAIL", "keywords": ["bus"]})
    assert 0 < s < 1 and unknown == ["channel"] and conf == round(2 / 3, 2)
    assert {e["criterion"] for e in ev} == {"city", "keywords"} and all("Fair 2026, row 3" in e["citation"] for e in ev)
    empty = {"brand": "POVU", "lines": [], "assets": [], "claims": [], "target": None}
    d = cds.compose({"company_name": "Kibanda Fresh", "evidence": ev}, "Rep", empty)
    assert "Kibanda Fresh" in d["body"] and "city Nakuru" in d["body"] and "STOP" in d["body"]


def test_business_card():
    out = cds.parse_card("Amina Wanjiru\nProcurement Manager\nDuka Moja Supermarket Ltd\n0712 345 678\namina@dukamoja.example.com")
    f = out["fields"]
    assert f["full_name"]["value"] == "Amina Wanjiru" and f["phone"]["value"] == "+254712345678"
    assert f["email"]["value"] == "amina@dukamoja.example.com" and f["company"]["value"].startswith("Duka Moja")
    assert out["ocr_engine"] == "NOT_CONFIGURED"


@DB
@pytest.mark.asyncio
async def test_prospect_research_enrich():
    from types import SimpleNamespace
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.ai_hub import AIActionRequest
    from app.models.customer_data import DataSource, ProspectRecord
    from app.models.sales import Customer
    from app.services import pat_service as pats
    s = uuid.uuid4().hex[:5]
    user = SimpleNamespace(id=None, username="analyst", email=None, full_name="Analyst")
    async with AsyncSessionLocal() as db:
        cust = Customer(code=f"SYN-{s}", name=f"Mama Mboga {s} Ltd", currency="KES", phone="0711000111", city="Nairobi")
        db.add(cust)
        await db.flush()
        with pytest.raises(cds.DataError):
            await cds.import_source(db, name="x", license_note=" ", rows=[{"n": "a"}], mapping={"company_name": "n"},
                                    retention_days=30, user="analyst")
        rows = [{"n": f"Mama Mboga {s}", "c": "Nairobi", "ch": "RETAIL", "p": "0711 000 111", "e": "", "w": "mamamboga.example.com"},
                {"n": f"Kibanda {s} Fresh", "c": "Nakuru", "ch": "RETAIL", "p": "0722000222", "e": f"buy{s}@kibanda.example.com"},
                {"n": f"Kibanda {s} Fresh", "c": "Nakuru", "ch": "RETAIL", "p": "0722000222", "e": ""},          # duplicate
                {"n": f"Shop {s} North", "c": "Nakuru", "ch": "WHOLESALE", "p": "bad", "e": ""}]
        out = await cds.import_source(db, name=f"Fair {s}", license_note="own trade-fair sign-up sheet", rows=rows,
                                      mapping={"company_name": "n", "city": "c", "channel": "ch", "phone": "p", "email": "e", "website": "w"},
                                      retention_days=30, user="analyst")
        assert out["stored"] == 3 and any("duplicate" in e["error"] for e in out["errors"]) and any("phone" in e["error"] for e in out["errors"])
        run = await cds.prospect(db, {"city": "Nakuru", "channel": "RETAIL"}, "analyst")
        names = [r["company_name"] for r in run.results]
        assert names[0] == f"Kibanda {s} Fresh" and f"Mama Mboga {s}" not in names       # existing customer excluded
        top = run.results[0]
        assert top["score"] == 1.0 and top["can_email"] and all(f"Fair {s}, row 2" in e["citation"] for e in top["evidence"])
        req = await pats.propose(db, source="PROSPECT", source_ref="t", user=user, action="send_email",
                                 arguments={"to_email": top["email"], **{k: v for k, v in (await cds.draft(db, top, "Rep")).items() if k in ("subject", "body")}}, summary="x")
        assert req.status == "PENDING"
        # research: cited facts, then a second source disagreeing → conflict
        view = await cds.research(db, cust.id)
        ph = next(f for f in view["fields"] if f["field"] == "phone")
        assert not ph["unknown"] and ph["candidates"][0]["citation"].startswith(f"Fair {s}, row 1") and ph["candidates"][0]["confidence"] == 0.8
        assert next(f for f in view["fields"] if f["field"] == "tax_id")["unknown"]
        await cds.import_source(db, name=f"List B {s}", license_note="distributor list shared under contract",
                                rows=[{"n": f"Mama Mboga {s}", "c": "Thika"}], mapping={"company_name": "n", "city": "c"},
                                retention_days=30, user="analyst")
        view = await cds.research(db, cust.id)
        city = next(f for f in view["fields"] if f["field"] == "city")
        assert city["conflict"] and {c["value"] for c in city["candidates"]} == {"Nairobi", "Thika"}
        thika = next(c for c in city["candidates"] if c["value"] == "Thika")
        with pytest.raises(cds.DataError) as e:
            await cds.apply_fact(db, uuid.UUID(thika["id"]), user)                   # different value, no overwrite
        assert "confirm the overwrite" in str(e.value)
        await cds.set_verified(db, cust.id, "city", user, True)
        with pytest.raises(cds.DataError) as e:
            await cds.apply_fact(db, uuid.UUID(thika["id"]), user, overwrite=True)   # verified wins
        assert "verified" in str(e.value)
        web = next(f for f in view["fields"] if f["field"] == "website")
        assert not web["applicable"]
        # retention: expired sources and their rows go
        for src in (await db.execute(select(DataSource).where(DataSource.name.in_([f"Fair {s}", f"List B {s}"])))).scalars():
            src.expires_at = src.imported_at - timedelta(days=1)
        await db.flush()
        assert await cds.purge_expired(db) >= 2
        assert (await db.execute(select(func.count()).select_from(ProspectRecord).where(ProspectRecord.company_name.like(f"%{s}%")))).scalar_one() == 0
        await db.rollback()
