"""M48.S01.T007 Snowflake writer against the local SQL API v2 simulator (unit; the DB part needs M48_DB=1).

Request shapes and KEYPAIR_JWT claims, typed bindings, MERGE upsert with no duplicate rows on replay, async 202
polling, retry/backoff with requestId+retry=true (lost response not executed twice), transactional failure and
restore, deletes, schema drift (additive vs refused), SQL injection in identifiers and values, NOT_CONFIGURED only
without a credential, LIVE gate, dry-run plan without network. Synthetic POVU data only.
"""
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import jwt
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import warehouse_cloud_writers as cw
from app.services import warehouse_export_service as wes
from tests.provider_sim.warehouse_app import create_warehouse_app, new_key, pem, sf_config

BASE = "http://wh.test"
COLS = ["id", "code", "name", "channel", "payment_terms_days", "credit_limit", "tax_id", "is_active", "created_at", "updated_at"]
TBL = "POVU_DW.ERP.CUSTOMERS"


@pytest.fixture
def sim(monkeypatch):
    app = create_warehouse_app()
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(cw, "BACKOFF", 0)
    monkeypatch.setattr(cw, "POLL_INTERVAL", 0)
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def _c(method, path, **kw):
    async with httpx.AsyncClient(transport=provider_http._test_transport, base_url=BASE) as c:
        return (await c.request(method, path, **kw)).json()


async def _target(**cfg):
    creds = await _c("GET", "/_control/demo-credentials")
    return SimpleNamespace(kind="SNOWFLAKE", config=sf_config(BASE, **cfg),
                           secret=wes.encrypt(json.dumps({"private_key": creds["snowflake"]["private_key"]})))


def _rows(n=3, **over):
    t0 = datetime(2026, 11, 20, 8, 30, tzinfo=timezone(timedelta(hours=3)))
    return [{"id": uuid.UUID(int=i + 1), "code": f"POVU-C{i}", "name": f"POVU Duka {i}", "channel": "GENERAL_TRADE",
             "payment_terms_days": 30, "credit_limit": Decimal("15000.50"), "tax_id": "P05•••67Z", "is_active": i % 2 == 0,
             "created_at": t0, "updated_at": t0 + timedelta(minutes=i), **over} for i in range(n)]


@pytest.mark.asyncio
async def test_jwt_claims_and_request_shape(sim):
    assert cw.sf_account("xy12345.us-east-2.aws") == "XY12345"
    assert cw.sf_account("povu-demo") == "POVU-DEMO"
    assert cw.sf_account("xy12345-acct.global") == "XY12345"
    w = cw.SnowflakeWriter(await _target())
    tok = w.jwt_token()
    assert jwt.get_unverified_header(tok)["alg"] == "RS256"
    c = jwt.decode(tok, options={"verify_signature": False})
    assert c["iss"].startswith("POVU-DEMO.ERP_LOADER.SHA256:") and c["sub"] == "POVU-DEMO.ERP_LOADER"
    assert 0 < c["exp"] - c["iat"] <= 3600
    assert (await w.test_connection()) == {"ok": True, "role": "ERP_LOADER", "warehouse": "LOAD_WH", "database": "POVU_DW"}
    call = (await _c("GET", "/_control/state"))["calls"][0]
    assert call["path"] == "/snowflake/api/v2/statements" and uuid.UUID(call["query"]["requestId"])
    assert call["token_type"] == "KEYPAIR_JWT" and call["auth"] == "Bearer "
    assert {k: call["body"][k] for k in ("role", "warehouse", "database", "schema")} == \
        {"role": "ERP_LOADER", "warehouse": "LOAD_WH", "database": "POVU_DW", "schema": "ERP"}


@pytest.mark.asyncio
async def test_wrong_key_is_refused(sim):
    t = await _target()
    t.secret = wes.encrypt(json.dumps({"private_key": pem(new_key())}))
    with pytest.raises(wes.ExportError, match="refused the key-pair login"):
        await cw.SnowflakeWriter(t).test_connection()


@pytest.mark.asyncio
async def test_merge_upsert_types_and_replay_idempotent(sim):
    w = cw.SnowflakeWriter(await _target())
    rows = _rows(3)
    assert await w.upsert("customers", COLS, rows) == []
    assert await w.upsert("customers", COLS, rows) == []            # replay of the same window
    rows[1]["name"] = "POVU Duka renamed"
    await w.upsert("customers", COLS, rows[1:2])
    state = await _c("GET", "/_control/state")
    assert list(state["sf_tables"]) == [TBL]                          # staging tables were dropped
    t = state["sf_tables"][TBL]
    assert len(t["rows"]) == 3 and sorted(r["NAME"] for r in t["rows"])[2] == "POVU Duka renamed"
    assert t["cols"]["CREDIT_LIMIT"] == "NUMBER" and t["cols"]["IS_ACTIVE"] == "BOOLEAN" and t["cols"]["CREATED_AT"] == "TIMESTAMP_TZ"
    r0 = next(r for r in t["rows"] if r["CODE"] == "POVU-C0")
    assert r0["CREDIT_LIMIT"] == "15000.50" and r0["IS_ACTIVE"] == "true" and r0["CREATED_AT"] == "2026-11-20T08:30:00+03:00"
    assert r0["ID"] == str(uuid.UUID(int=1)) and r0["_LOADED_AT"]
    calls = [c["body"] for c in state["calls"]]
    ins = next(b for b in calls if b["statement"].startswith("INSERT INTO"))
    by_col = {c: ins["bindings"][str(i + 1)]["type"] for i, c in enumerate(COLS)}
    assert by_col == {"id": "TEXT", "code": "TEXT", "name": "TEXT", "channel": "TEXT", "payment_terms_days": "FIXED",
                      "credit_limit": "TEXT", "tax_id": "TEXT", "is_active": "BOOLEAN", "created_at": "TIMESTAMP_TZ",
                      "updated_at": "TIMESTAMP_TZ"}
    assert all(isinstance(b["value"], str) for b in ins["bindings"].values())
    merge = next(b for b in calls if "MERGE INTO" in b["statement"])
    assert merge["statement"].startswith("BEGIN TRANSACTION; MERGE INTO") and merge["statement"].endswith("; COMMIT")
    assert merge["parameters"] == {"MULTI_STATEMENT_COUNT": "3"} and "bindings" not in merge
    assert sum(1 for s in state["sf_exec"] if s.startswith("MERGE")) == 3


def test_bind_formats():
    assert cw.sf_bind("date", date(1970, 1, 2)) == {"type": "DATE", "value": "86400000"}
    assert cw.sf_bind("timestamp_tz", datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone(timedelta(hours=-8)))) == \
        {"type": "TIMESTAMP_TZ", "value": "28801000000000 960"}                        # documented example offset 960
    assert cw.sf_bind("int", 7) == {"type": "FIXED", "value": "7"} and cw.sf_bind("bool", None) == {"type": "BOOLEAN", "value": None}


@pytest.mark.asyncio
async def test_sql_injection_identifiers_and_values(sim):
    evil = "x'); DROP TABLE CUSTOMERS; --\""
    w = cw.SnowflakeWriter(await _target())
    await w.upsert("customers", COLS, _rows(1, name=evil))
    t = (await _c("GET", "/_control/state"))["sf_tables"][TBL]
    assert t["rows"][0]["NAME"] == evil                               # stored verbatim as a bound value
    for bad in ({"schema": 'ERP"; DROP SCHEMA X; --'}, {"database": "DW.X"}, {"role": "ACCOUNTADMIN"}, {"warehouse": ""}):
        with pytest.raises(wes.ExportError):
            cw.SnowflakeWriter(await _target(**bad))
    with pytest.raises(wes.ExportError, match="Refused"):
        await w.upsert("customers", ["id", 'name" = 1; --'], [{"id": 1}])
    assert all(evil not in c["body"]["statement"] for c in (await _c("GET", "/_control/state"))["calls"])


@pytest.mark.asyncio
async def test_schema_drift_additive_and_refused(sim):
    w = cw.SnowflakeWriter(await _target())
    await w.upsert("customers", COLS, _rows(2))
    w2 = cw.SnowflakeWriter(await _target())                          # next run: dataset gained a column
    assert await w2.upsert("customers", COLS + ["delivery_city"], _rows(1, delivery_city="Thika")) == ["delivery_city"]
    t = (await _c("GET", "/_control/state"))["sf_tables"][TBL]
    assert t["cols"]["DELIVERY_CITY"] == "TEXT" and next(r for r in t["rows"] if r["CODE"] == "POVU-C0")["DELIVERY_CITY"] == "Thika"
    # incompatible: an existing warehouse column has another type
    w3 = cw.SnowflakeWriter(await _target(schema="OTHER"))
    await w3.sql('CREATE SCHEMA IF NOT EXISTS "POVU_DW"."OTHER"')
    await w3.sql('CREATE TABLE IF NOT EXISTS "POVU_DW"."OTHER"."CUSTOMERS" ("ID" VARCHAR, "PAYMENT_TERMS_DAYS" VARCHAR)')
    with pytest.raises(wes.ExportError, match="payment_terms_days is TEXT in Snowflake but the ERP sends NUMBER"):
        await w3.upsert("customers", COLS, _rows(1))
    assert (await _c("GET", "/_control/state"))["sf_tables"]["POVU_DW.OTHER.CUSTOMERS"]["rows"] == []


@pytest.mark.asyncio
async def test_async_polling_retries_and_lost_response(sim):
    w = cw.SnowflakeWriter(await _target())
    await _c("POST", "/_control", json={"sf_async": 2, "faults": {"sf": [429, 503, {"kind": "lost", "match": "MERGE"}]}})
    await w.upsert("customers", COLS, _rows(2))
    state = await _c("GET", "/_control/state")
    assert len(state["sf_tables"][TBL]["rows"]) == 2
    assert sum(1 for s in state["sf_exec"] if s.startswith("MERGE")) == 1     # lost answer → retry=true, not executed twice
    merges = [c for c in state["calls"] if "MERGE" in c["body"]["statement"]]
    assert len(merges) == 2 and merges[1]["query"]["retry"] == "true" and merges[0]["query"]["requestId"] == merges[1]["query"]["requestId"]


@pytest.mark.asyncio
async def test_failure_rolls_back_and_restore(sim):
    w = cw.SnowflakeWriter(await _target())
    await w.upsert("customers", COLS, _rows(2))
    await _c("POST", "/_control", json={"faults": {"sf": [{"kind": "fail", "match": "MERGE"}]}})
    changed = _rows(3, name="POVU changed")
    with pytest.raises(wes.ExportError, match="422 100035"):
        await w.upsert("customers", COLS, changed)
    state = await _c("GET", "/_control/state")
    assert list(state["sf_tables"]) == [TBL] and len(state["sf_tables"][TBL]["rows"]) == 2     # nothing half-applied
    await w.upsert("customers", COLS, changed)                                                   # restore: replay succeeds
    rows = (await _c("GET", "/_control/state"))["sf_tables"][TBL]["rows"]
    assert len(rows) == 3 and {r["NAME"] for r in rows} == {"POVU changed"}


@pytest.mark.asyncio
async def test_deletes_where_allowed(sim):
    w = cw.SnowflakeWriter(await _target())
    await w.upsert("customers", COLS, _rows(3))
    await w.delete("customers", [str(uuid.UUID(int=2)), "x' OR '1'='1"])
    assert len((await _c("GET", "/_control/state"))["sf_tables"][TBL]["rows"]) == 2
    keep = cw.SnowflakeWriter(await _target(allow_deletes=False))
    await keep.delete("customers", [str(uuid.UUID(int=1))])
    assert len((await _c("GET", "/_control/state"))["sf_tables"][TBL]["rows"]) == 2


@pytest.mark.asyncio
async def test_not_configured_live_gate_and_dry_plan(sim, monkeypatch):
    t = await _target()
    with pytest.raises(wes.ExportError, match="NOT_CONFIGURED"):
        wes.writer(SimpleNamespace(kind="SNOWFLAKE", config=t.config, secret=None))
    assert wes.writer(t).mode == "SIMULATED"
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "live")
    with pytest.raises(wes.ExportError, match="LIVE_DISABLED: live warehouse sync is off"):
        wes.writer(t)
    monkeypatch.setattr(cw, "_live_switch", lambda: True)
    with pytest.raises(wes.ExportError, match="independent report administrator"):
        wes.writer(t)
    # live: the simulator override is refused even after an approval (endpoint pinning)
    t.config = {**t.config, "approved_by": "admin2", "approved_hosts": [f"{BASE}/snowflake"]}
    with pytest.raises(wes.ExportError, match="only allowed against the local simulator"):
        wes.writer(t)
    official = {k: v for k, v in t.config.items() if k != "base_url"}
    live = SimpleNamespace(kind="SNOWFLAKE", config={**official, "approved_hosts": ["https://povu-demo.snowflakecomputing.com"]},
                           secret=t.secret, created_by="admin1", secret_set_by="admin1")
    assert wes.writer(live).mode == "LIVE" and wes.writer(live).base == "https://povu-demo.snowflakecomputing.com"
    for who in ("created_by", "secret_set_by"):                       # approver must be independent of both
        setattr(live, who, "admin2")
        with pytest.raises(wes.ExportError, match="independent approval"):
            wes.writer(live)
        setattr(live, who, "admin1")
    live.config = {**live.config, "approved_hosts": ["https://other.snowflakecomputing.com"]}
    with pytest.raises(wes.ExportError, match="endpoints changed since approval"):
        wes.writer(live)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    steps = await cw.plan(cw.SnowflakeWriter(SimpleNamespace(config=t.config, secret=None)), "customers", COLS, 5)
    assert (await _c("GET", "/_control/state"))["calls"] == []        # nothing sent
    sql = [s["statement"] for s in steps]
    assert any(s.startswith("CREATE TABLE IF NOT EXISTS") for s in sql) and any("MERGE INTO" in s for s in sql)
    ins = next(s for s in steps if s["statement"].startswith("INSERT"))
    assert ins["bound_values"] == 5 * len(COLS) and "\"value\":" not in json.dumps(ins)


# ── DB: the real incremental job + staff API ─────────────────────────────────

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"


@pytest.fixture
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _user(db, perms, tag):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password=hash_password(PW), is_active=True)
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


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


@DB
@pytest.mark.asyncio
async def test_job_checkpoint_failure_restore_and_replay(sim, monkeypatch, _dispose_engine):
    from sqlalchemy import delete, func, select, update
    from app.db.session import AsyncSessionLocal
    from app.models.sales import Customer
    from app.models.warehouse_export import ExportJob, ExportTarget
    monkeypatch.setattr(wes, "BATCH", 2)
    s = uuid.uuid4().hex[:5]
    t = await _target()
    async with AsyncSessionLocal() as db:
        custs = [Customer(code=f"SF{s}-{i}", name=f"POVU SF {i}", currency="KES") for i in range(5)]
        db.add_all(custs)
        tgt = ExportTarget(name=f"sf-{s}", kind="SNOWFLAKE", config=t.config, secret=t.secret)
        db.add(tgt)
        await db.flush()
        job = ExportJob(target_id=tgt.id, dataset="customers", file_format="csv", known_ids=[], schema_cols=[])
        db.add(job)
        await db.commit()
        total = (await db.execute(select(func.count()).select_from(Customer))).scalar()
        ids = [c.id for c in custs]
        r_fail = await wes.run_job(db, job, fail_after_batches=1)
        assert r_fail.status == "FAILED" and r_fail.rows == 2 and r_fail.mode == "SIMULATED"
        await db.refresh(job)
        mark = job.watermark_id
        await _c("POST", "/_control", json={"faults": {"sf": [{"kind": "fail", "match": "MERGE"}]}})
        r_merge = await wes.run_job(db, job)
        assert r_merge.status == "FAILED" and "100035" in r_merge.error
        await db.refresh(job)
        assert job.watermark_id == mark                              # not advanced past an uncommitted batch
        r_ok = await wes.run_job(db, job)
        assert r_ok.status == "DONE" and r_ok.rows == total - 2
        rows = (await _c("GET", "/_control/state"))["sf_tables"][TBL]["rows"]
        assert len(rows) == total and sum(r["CODE"].startswith(f"SF{s}-") for r in rows) == 5
        await db.execute(update(Customer).where(Customer.id == ids[0]).values(name="POVU SF renamed"))
        await db.execute(delete(Customer).where(Customer.id == ids[4]))
        await db.commit()
        r2 = await wes.run_job(db, job)
        assert r2.rows == 1 and r2.deleted == 1
        job.watermark, job.watermark_id = None, None                 # replay the whole window
        await db.commit()
        r3 = await wes.run_job(db, job)
        assert r3.status == "DONE" and r3.rows == total - 1
        rows = (await _c("GET", "/_control/state"))["sf_tables"][TBL]["rows"]
        assert len(rows) == total - 1 and "POVU SF renamed" in {r["NAME"] for r in rows}


@DB
@pytest.mark.asyncio
async def test_staff_api_wizard_rbac_dry_run_and_approval(sim, _dispose_engine):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        a1 = await _user(db, ("reports.admin",), "dwadmin")
        a2 = await _user(db, ("reports.admin",), "dwadmin2")
        a3 = await _user(db, ("reports.admin",), "dwadmin3")
        out = await _user(db, ("sales.view",), "outsider")
        await db.commit()
    creds = await _c("GET", "/_control/demo-credentials")
    name = f"POVU Snowflake {uuid.uuid4().hex[:5]}"
    async with _client() as c, _client() as c2, _client() as c3, _client() as co:
        await _login(c, a1)
        await _login(c2, a2)
        await _login(c3, a3)
        await _login(co, out)
        assert (await co.get("/api/v1/warehouse-exports")).status_code == 403
        assert (await co.post("/api/v1/warehouse-exports/targets", json={"name": "x", "kind": "SNOWFLAKE", "config": {}})).status_code == 403
        bad = await c.post("/api/v1/warehouse-exports/targets", json={"name": name, "kind": "SNOWFLAKE", "config": sf_config(BASE, role="SYSADMIN")})
        assert bad.status_code == 422 and "least-privilege" in bad.json()["detail"]
        r = await c.post("/api/v1/warehouse-exports/targets", json={"name": name, "kind": "SNOWFLAKE", "config": sf_config(BASE)})
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        ov = (await c.get("/api/v1/warehouse-exports")).json()
        assert ov["kinds"]["SNOWFLAKE"] == "available"
        assert next(x for x in ov["targets"] if x["id"] == tid)["status"] == "NOT_CONFIGURED"
        res = (await c.post(f"/api/v1/warehouse-exports/targets/{tid}/test")).json()
        assert res["ok"] is False and "NOT_CONFIGURED" in res["error"]
        # admin 2 (not the creator) stores the credential: from now on admin 2 is not independent either
        r = await c2.put(f"/api/v1/warehouse-exports/targets/{tid}/secret", json={"secret": creds["snowflake"]["private_key"]})
        assert r.status_code == 200 and r.json()["public_key_fp"].startswith("SHA256:")
        ov_text = (await c.get("/api/v1/warehouse-exports")).text
        assert "PRIVATE KEY" not in ov_text and "secret" not in json.loads(ov_text)["targets"][0]
        assert (await c.post(f"/api/v1/warehouse-exports/targets/{tid}/test")).json() == \
            {"ok": True, "role": "ERP_LOADER", "warehouse": "LOAD_WH", "database": "POVU_DW", "mode": "SIMULATED"}
        assert (await c.post(f"/api/v1/warehouse-exports/targets/{tid}/approve")).status_code == 403    # creator
        assert (await c2.post(f"/api/v1/warehouse-exports/targets/{tid}/approve")).status_code == 403   # set the secret
        tv = next(x for x in (await c.get("/api/v1/warehouse-exports")).json()["targets"] if x["id"] == tid)
        assert tv["hosts"] == [f"{BASE}/snowflake"] and tv["secret_set_by"] == a2
        ok = (await c3.post(f"/api/v1/warehouse-exports/targets/{tid}/approve")).json()
        assert ok == {"status": "APPROVED", "hosts": [f"{BASE}/snowflake"]}
        # replacing the credential after approval withdraws it; the replacer cannot re-approve
        assert (await c3.put(f"/api/v1/warehouse-exports/targets/{tid}/secret", json={"secret": creds["snowflake"]["private_key"]})).status_code == 200
        tv = next(x for x in (await c.get("/api/v1/warehouse-exports")).json()["targets"] if x["id"] == tid)
        assert tv["status"] == "CONFIGURED" and "approved_by" not in tv["config"] and "approved_hosts" not in tv["config"]
        assert (await c3.post(f"/api/v1/warehouse-exports/targets/{tid}/approve")).status_code == 403
        assert (await c2.post(f"/api/v1/warehouse-exports/targets/{tid}/approve")).json()["status"] == "APPROVED"
        j = await c.post("/api/v1/warehouse-exports/jobs", json={"target_id": tid, "dataset": "products"})
        jid = j.json()["id"]
        dry = (await c.post(f"/api/v1/warehouse-exports/jobs/{jid}/dry-run")).json()
        assert dry["column_types"]["is_active"] == "BOOLEAN" and any("MERGE INTO" in p["statement"] for p in dry["plan"])
        assert (await co.post(f"/api/v1/warehouse-exports/jobs/{jid}/dry-run")).status_code == 403
        run = (await c.post(f"/api/v1/warehouse-exports/jobs/{jid}/run")).json()
        assert run["status"] == "DONE" and run["mode"] == "SIMULATED"
        assert (await co.post(f"/api/v1/warehouse-exports/jobs/{jid}/run")).status_code == 403
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.models.audit_log import AuditLog
        ev = set((await db.execute(select(AuditLog.event_type).where(AuditLog.event_type.like("DW_%")))).scalars())
        assert {"DW_TARGET_ADDED", "DW_TARGET_SECRET_SET", "DW_TARGET_TESTED", "DW_TARGET_APPROVED", "DW_JOB_ADDED", "DW_JOB_RUN"} <= ev
