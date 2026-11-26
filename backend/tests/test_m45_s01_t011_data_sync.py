"""M45.S01.T011 no-code data sync (unit; DB part needs M45_DB=1).

Unit: typed transforms, invalid mappings refused, no code execution. DB with a local two-way fixture: dry run writes
nothing; run creates/updates; unchanged rows skipped (incremental); conflict rules; vanished keys deactivated;
rollback restores; replay; pull from a JSON endpoint retried after a failure; OUT pushes changed rows with retry;
webhook needs its token; data-quality overview and recommendations.
"""
import os
import uuid
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core import provider_http
from app.services import data_sync_service as dss

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
MAP = [{"target": "code", "source": "Code", "transforms": ["trim", "upper"]},
       {"target": "name", "source": "Name", "transforms": ["trim", "title"]},
       {"target": "phone", "source": "Tel", "transforms": ["phone_ke"]},
       {"target": "credit_limit", "source": "Limit", "transforms": ["number"]},
       {"target": "segment", "source": "Type", "transforms": ['map:{"W":"Wholesale","R":"Retail"}', "default:Retail"]}]


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_transforms_and_validation():
    row = {"First": "amina", "Last": "wanjiru"}
    assert dss.transform(" mama  mboga ", ["trim", "title"], row) == "Mama Mboga"
    assert dss.transform("0712 345 678", ["phone_ke"], row) == "+254712345678"
    assert dss.transform(None, ["concat:First,Last", "title"], row) == "Amina Wanjiru"
    assert dss.transform("1,250.50", ["number"], row) == Decimal("1250.50")
    assert dss.transform("W", ['map:{"W":"Wholesale"}'], row) == "Wholesale"
    with pytest.raises(ValueError):
        dss.transform("abc", ["integer"], row)
    dss.validate_mapping("customers", "code", MAP)
    for bad, msg in (([{"target": "code", "source": "c", "transforms": ["eval:__import__('os')"]}], "unknown transformation"),
                     ([{"target": "nope", "source": "x"}], "Unknown target"),
                     ([{"target": "code", "source": "c"}], "name must be mapped")):
        with pytest.raises(dss.SyncError) as e:
            dss.validate_mapping("customers", "code", bad)
        assert msg in str(e.value)


def _fixture_app():
    """A two-way local source: GET returns rows (fails first time), POST receives the ERP's changes (fails once)."""
    app = FastAPI()
    st = {"get_calls": 0, "post_calls": 0, "received": []}

    @app.get("/rows")
    async def rows():
        st["get_calls"] += 1
        if st["get_calls"] == 1:
            return JSONResponse({"error": "busy"}, status_code=503)
        return {"rows": [{"Code": "dsx-9", "Name": "pulled outlet", "Tel": "0700000009"}]}

    @app.post("/inbox")
    async def inbox(request: Request):
        st["post_calls"] += 1
        if st["post_calls"] == 1:
            return JSONResponse({"error": "busy"}, status_code=500)
        st["received"].append(await request.json())
        return {"ok": True}
    app.state.st = st
    return app


@DB
@pytest.mark.asyncio
async def test_sync_end_to_end(monkeypatch):
    from sqlalchemy import select
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.data_sync import SyncDefinition, SyncRun
    from app.models.sales import Customer
    s = uuid.uuid4().hex[:4].upper()
    csv1 = f"Code,Name,Tel,Limit,Type\nds{s}-1, duka moja ,0711 000 001,1000,W\nds{s}-2,kibanda,0711000002,500,\nds{s}-3,bad,,notanumber,R\n"
    async with AsyncSessionLocal() as db:
        sync = SyncDefinition(name=f"Distributor list {s}", source_kind="UPLOAD", target="customers", key_field="code",
                              mapping=MAP, conflict_rule="source_wins", delete_mode="deactivate", history=[])
        db.add(sync)
        await db.commit()
        dry = await dss.run_in(db, sync, dss.parse_upload(csv1, "csv"), dry_run=True, user="t")
        assert dry.counts["create"] == 2 and dry.counts["error"] == 1 and "not a number" in dry.errors[0]["error"]
        await db.rollback()
        assert (await db.execute(select(Customer).where(Customer.code == f"DS{s}-1"))).first() is None     # nothing written
        r1 = await dss.run_in(db, sync, dss.parse_upload(csv1, "csv"), dry_run=False, user="t")
        await db.commit()
        c1 = (await db.execute(select(Customer).where(Customer.code == f"DS{s}-1"))).scalar_one()
        assert (c1.name, c1.phone, c1.segment, c1.credit_limit) == ("Duka Moja", "+254711000001", "Wholesale", Decimal("1000"))
        r2 = await dss.run_in(db, sync, dss.parse_upload(csv1, "csv"), dry_run=False, user="t")
        assert r2.counts["unchanged"] == 2 and r2.counts["create"] == 0                         # incremental
        csv2 = f"Code,Name,Tel,Limit,Type\nds{s}-1,duka moja,0711 000 001,2000,W\n"
        r3 = await dss.run_in(db, sync, dss.parse_upload(csv2, "csv"), dry_run=False, user="t")
        await db.commit()
        assert r3.counts["update"] == 1 and r3.counts["delete"] == 1
        await db.refresh(c1)
        c2 = (await db.execute(select(Customer).where(Customer.code == f"DS{s}-2"))).scalar_one()
        assert c1.credit_limit == Decimal("2000") and c2.is_active is False                      # vanished → deactivated
        out = await dss.rollback(db, r3, "t")
        await db.commit()
        await db.refresh(c1), await db.refresh(c2)
        assert out["restored"] >= 2 and c1.credit_limit == Decimal("1000") and c2.is_active is True
        rp = await dss.run_in(db, sync, r1.input, dry_run=False, user="t", trigger="REPLAY", full_snapshot=False)
        assert rp.counts["error"] == 1                                                            # same input, same verdicts
        # ERP wins: first contact only fills empty fields
        sync.conflict_rule = "target_wins"
        c1.city = "Nairobi"
        await db.commit()
        # two-way local fixture: pull (retry after 503) and push (retry after 500)
        app = _fixture_app()
        monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
        provider_http.set_test_transport(httpx.ASGITransport(app=app))
        try:
            pull = SyncDefinition(name=f"Pull {s}", source_kind="HTTP_JSON", source_url="http://fixture.test/rows", target="customers",
                                  key_field="code", mapping=MAP[:3], history=[])
            push = SyncDefinition(name=f"Push {s}", direction="OUT", source_kind="HTTP_JSON", source_url="http://fixture.test/inbox",
                                  target="customers", key_field="code", mapping=[{"target": "code", "source": "id"}, {"target": "name", "source": "title"}],
                                  history=[])
            db.add_all([pull, push])
            await db.commit()
            rows = await dss.pull(pull)
            assert app.state.st["get_calls"] == 2 and rows[0]["Code"] == "dsx-9"
            ro = await dss.run_out(db, push, dry_run=False, user="t")
            assert ro.status == "DONE" and ro.attempts == 2 and app.state.st["received"][0]["rows"]
            ro2 = await dss.run_out(db, push, dry_run=False, user="t")
            assert ro2.counts["sent"] == 0                                                       # watermark: nothing new
        finally:
            provider_http.set_test_transport(None)
        q = await dss.quality(db)
        assert q["customers"]["total"] >= 2 and "score" in q["customers"]
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_webhook_needs_token():
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.data_sync import SyncDefinition
    async with AsyncSessionLocal() as db:
        sync = SyncDefinition(name=f"Hook {uuid.uuid4().hex[:4]}", source_kind="WEBHOOK", target="crm_contacts", key_field="email",
                              mapping=[{"target": "email", "source": "mail", "transforms": ["email"]}, {"target": "full_name", "source": "who"}],
                              secret=dss.encrypt("hook-token-123"), history=[])
        db.add(sync)
        await db.commit()
        sid = sync.id
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        body = {"rows": [{"mail": f"Hook{uuid.uuid4().hex[:4]}@POVU-demo.test", "who": "Webhook Person"}]}
        assert (await c.post(f"/api/v1/public/data-sync/{sid}", json=body, headers={"Authorization": "Bearer wrong"})).status_code == 401
        r = await c.post(f"/api/v1/public/data-sync/{sid}", json=body, headers={"Authorization": "Bearer hook-token-123"})
        assert r.status_code == 200 and r.json()["counts"]["create"] == 1
