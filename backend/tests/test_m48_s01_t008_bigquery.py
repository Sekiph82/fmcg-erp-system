"""M48.S01.T008 BigQuery writer against the local REST v2 + Google token simulator (unit; the DB part needs M48_DB=1).

Service-account JWT claims and token exchange, dataset/table provisioning, multipart load job with a client jobId
(lost response reconciled through 409 + jobs.get), jobs.get polling, MERGE through jobs.query with dry-run cost guard
and maximumBytesBilled, replay without duplicate rows, typed schema evolution (additive PATCH, incompatible refused),
job failure and restore, deletes with array query parameters, injection, NOT_CONFIGURED, dry-run plan. Synthetic data.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import jwt
import pytest

from app.core import provider_http
from app.core.config import settings
from app.services import warehouse_cloud_writers as cw
from app.services import warehouse_export_service as wes
from tests.provider_sim.warehouse_app import bq_config, create_warehouse_app, new_key, pem

BASE = "http://wh.test"
COLS = ["id", "invoice_no", "customer_id", "invoice_date", "status", "currency", "total_amount", "created_at", "updated_at"]
TBL = "povu-demo-erp.erp_export.invoices"


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
    sa = (await _c("GET", "/_control/demo-credentials"))["bigquery"]
    return SimpleNamespace(kind="BIGQUERY", config=bq_config(BASE, **cfg), secret=wes.encrypt(json.dumps(sa)))


def _rows(n=3, **over):
    t0 = datetime(2026, 11, 21, 9, 0, tzinfo=timezone.utc)
    return [{"id": uuid.UUID(int=i + 1), "invoice_no": f"INV-POVU-{i}", "customer_id": uuid.UUID(int=100), "invoice_date": t0.date(),
             "status": "ISSUED", "currency": "KES", "total_amount": Decimal("2320.0000"), "created_at": t0,
             "updated_at": t0 + timedelta(minutes=i), **over} for i in range(n)]


async def _state():
    return await _c("GET", "/_control/state")


@pytest.mark.asyncio
async def test_token_exchange_claims_and_request_shapes(sim):
    w = cw.BigQueryWriter(await _target())
    assert await w.test_connection() == {"ok": True, "project": "povu-demo-erp", "dataset": "erp_export", "dataset_exists": False}
    calls = (await _state())["calls"]
    tok = calls[0]
    assert tok["path"] == "/oauth2/token" and tok["form"] == {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer"}
    assert jwt.get_unverified_header(tok["assertion"]) == {"alg": "RS256", "kid": "sim-key-1", "typ": "JWT"}
    c = jwt.decode(tok["assertion"], options={"verify_signature": False})
    assert c["iss"] == "erp-loader@povu-demo-erp.iam.povu-demo.test" and c["aud"] == f"{BASE}/oauth2/token"
    assert c["scope"] == "https://www.googleapis.com/auth/bigquery" and c["exp"] - c["iat"] == 3600
    assert calls[1]["method"] == "GET" and calls[1]["path"] == "/bq/bigquery/v2/projects/povu-demo-erp/datasets/erp_export"
    bad = await _target()
    sa = json.loads(wes.decrypt(bad.secret))
    bad.secret = wes.encrypt(json.dumps({**sa, "private_key": pem(new_key())}))
    with pytest.raises(wes.ExportError, match="token exchange failed .400 invalid_grant"):
        await cw.BigQueryWriter(bad).test_connection()


@pytest.mark.asyncio
async def test_load_merge_types_replay_and_cost_guard_order(sim):
    w = cw.BigQueryWriter(await _target())
    rows = _rows(3)
    assert await w.upsert("invoices", COLS, rows) == []
    assert await w.upsert("invoices", COLS, rows) == []                 # replay of the same window
    rows[0]["status"] = "PAID"
    await w.upsert("invoices", COLS, rows[:1])
    st = await _state()
    assert sorted(st["bq_tables"]) == [TBL] and st["bq_datasets"] == ["povu-demo-erp.erp_export"]   # staging deleted
    t = st["bq_tables"][TBL]
    assert len(t["rows"]) == 3 and sum(r["status"] == "PAID" for r in t["rows"]) == 1
    types = {f["name"]: f["type"] for f in t["schema"]}
    assert types == {"id": "STRING", "invoice_no": "STRING", "customer_id": "STRING", "invoice_date": "DATE", "status": "STRING",
                     "currency": "STRING", "total_amount": "NUMERIC", "created_at": "TIMESTAMP", "updated_at": "TIMESTAMP",
                     "_loaded_at": "TIMESTAMP"}
    r0 = next(r for r in t["rows"] if r["invoice_no"] == "INV-POVU-0")
    assert r0["total_amount"] == "2320.0000" and r0["invoice_date"] == "2026-11-21" and r0["created_at"] == "2026-11-21T09:00:00+00:00"
    up = next(c for c in st["calls"] if c["path"].startswith("/bq/upload/"))
    assert up["path"] == "/bq/upload/bigquery/v2/projects/povu-demo-erp/jobs" and up["query"] == {"uploadType": "multipart"}
    assert '"sourceFormat": "NEWLINE_DELIMITED_JSON"' in up["body"] and '"writeDisposition": "WRITE_TRUNCATE"' in up["body"]
    queries = [json.loads(c["body"]) for c in st["calls"] if c["path"].endswith("/queries")]
    assert [q.get("dryRun", False) for q in queries[:2]] == [True, False]        # cost estimate before every DML
    real = queries[1]
    assert real["useLegacySql"] is False and real["maximumBytesBilled"] == "1000000000" and uuid.UUID(real["requestId"])
    assert real["query"].startswith(f"MERGE `{TBL}` T USING `povu-demo-erp.erp_export.invoices_stg_")
    assert [e.split(" ")[0] for e in st["bq_exec"]].count("MERGE") == 3


@pytest.mark.asyncio
async def test_cost_cap_refuses_before_running(sim):
    w = cw.BigQueryWriter(await _target(max_bytes_billed=50))
    with pytest.raises(wes.ExportError, match="Cost guard: the statement would process"):
        await w.upsert("invoices", COLS, _rows(2))
    st = await _state()
    assert not any(e.startswith("MERGE") for e in st["bq_exec"]) and st["bq_tables"][TBL]["rows"] == []


@pytest.mark.asyncio
async def test_async_polling_retries_and_lost_load_response(sim):
    w = cw.BigQueryWriter(await _target())
    await _c("POST", "/_control", json={"bq_async": 2, "faults": {"bq": [429, {"kind": 503, "match": "/queries"}, "lost"]}})
    await w.upsert("invoices", COLS, _rows(2))
    st = await _state()
    assert len(st["bq_tables"][TBL]["rows"]) == 2
    loads = [c for c in st["calls"] if c["path"].startswith("/bq/upload/")]
    assert len(loads) == 2 and sum(e.startswith("LOAD") for e in st["bq_exec"]) == 1    # 409 duplicate reconciled, loaded once
    assert any(c["path"].endswith("/jobs/" + json.loads(loads[0]["body"].split("\r\n\r\n")[1].split("\r\n")[0])["jobReference"]["jobId"])
               for c in st["calls"])


@pytest.mark.asyncio
async def test_job_failure_and_restore(sim):
    w = cw.BigQueryWriter(await _target())
    await w.upsert("invoices", COLS, _rows(2))
    await _c("POST", "/_control", json={"faults": {"bq": [{"kind": "jobfail", "match": "JOB povu-demo-erp.erp_export.invoices_stg_"}]}})
    with pytest.raises(wes.ExportError, match=r"BigQuery job povu_erp_\w+ failed \(invalid\)"):
        await w.upsert("invoices", COLS, _rows(3, status="PAID"))
    st = await _state()
    assert sorted(st["bq_tables"]) == [TBL] and len(st["bq_tables"][TBL]["rows"]) == 2
    await w.upsert("invoices", COLS, _rows(3, status="PAID"))
    rows = (await _state())["bq_tables"][TBL]["rows"]
    assert len(rows) == 3 and {r["status"] for r in rows} == {"PAID"}


@pytest.mark.asyncio
async def test_schema_evolution_additive_and_refused(sim):
    w = cw.BigQueryWriter(await _target())
    await w.upsert("invoices", COLS[:-2] + ["updated_at"], _rows(1))
    w2 = cw.BigQueryWriter(await _target())
    assert await w2.upsert("invoices", COLS, _rows(1)) == ["created_at"]
    assert any(c["method"] == "PATCH" for c in (await _state())["calls"])
    w3 = cw.BigQueryWriter(await _target(dataset="erp_other"))
    await w3._provision("invoices", ["id"], {"id": "string"})
    await w3.call("PATCH", w3._tpath("invoices"), json={"schema": {"fields": [
        {"name": "id", "type": "STRING", "mode": "NULLABLE"}, {"name": "_loaded_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "total_amount", "type": "STRING", "mode": "NULLABLE"}]}})
    w4 = cw.BigQueryWriter(await _target(dataset="erp_other"))
    with pytest.raises(wes.ExportError, match="total_amount is STRING in BigQuery but the ERP sends NUMERIC"):
        await w4.upsert("invoices", COLS, _rows(1))
    with pytest.raises(wes.ExportError, match="changed type from STRING to NUMERIC"):    # the API itself also refuses
        await w4.call("PATCH", w4._tpath("invoices"), json={"schema": {"fields": [
            {"name": "id", "type": "STRING"}, {"name": "_loaded_at", "type": "TIMESTAMP"}, {"name": "total_amount", "type": "NUMERIC"}]}})


@pytest.mark.asyncio
async def test_deletes_injection_and_identifiers(sim):
    w = cw.BigQueryWriter(await _target())
    evil = "x' OR 1=1; DROP TABLE `povu-demo-erp.erp_export.invoices`; --"
    await w.upsert("invoices", COLS, _rows(3, invoice_no=evil))
    await w.delete("invoices", [str(uuid.UUID(int=2)), "' OR '1'='1"])
    st = await _state()
    rows = st["bq_tables"][TBL]["rows"]
    assert len(rows) == 2 and all(r["invoice_no"] == evil for r in rows)
    dq = [json.loads(c["body"]) for c in st["calls"] if c["path"].endswith("/queries") and "DELETE" in c["body"]][-1]
    assert dq["query"] == f"DELETE FROM `{TBL}` WHERE `id` IN UNNEST(@ids)" and dq["parameterMode"] == "NAMED"
    assert dq["queryParameters"][0]["parameterType"] == {"type": "ARRAY", "arrayType": {"type": "STRING"}}
    assert all(evil not in json.loads(c["body"]).get("query", "") for c in st["calls"] if c["path"].endswith("/queries"))
    for bad in ({"dataset": "erp`; DROP"}, {"project": "Bad Project"}, {"location": "us/../x"}):
        with pytest.raises(wes.ExportError):
            cw.BigQueryWriter(await _target(**bad))


@pytest.mark.asyncio
async def test_not_configured_and_dry_plan(sim):
    t = await _target()
    with pytest.raises(wes.ExportError, match="NOT_CONFIGURED: BigQuery needs a service-account key"):
        wes.writer(SimpleNamespace(kind="BIGQUERY", config=t.config, secret=None))
    steps = await cw.plan(cw.BigQueryWriter(SimpleNamespace(config=t.config, secret=None)), "invoices", COLS, 4)
    assert (await _state())["calls"] == []
    reqs = [s["request"] for s in steps]
    assert "POST /upload/bigquery/v2/projects/povu-demo-erp/jobs?uploadType=multipart" in reqs
    up = next(s for s in steps if "upload" in s)
    assert up["upload"]["rows"] == 4 and "INV-POVU" not in json.dumps(steps)
    assert any("MERGE" in (s.get("body") or {}).get("query", "") for s in steps)


# ── DB: the real incremental job ────────────────────────────────────────────

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@DB
@pytest.mark.asyncio
async def test_job_watermark_failure_restore_and_replay(sim, monkeypatch):
    from sqlalchemy import delete, func, select, update
    from app.db.session import AsyncSessionLocal, engine
    from app.models.sales import Customer
    from app.models.warehouse_export import ExportJob, ExportTarget
    monkeypatch.setattr(wes, "BATCH", 2)
    s = uuid.uuid4().hex[:5]
    t = await _target()
    try:
        async with AsyncSessionLocal() as db:
            custs = [Customer(code=f"BQ{s}-{i}", name=f"POVU BQ {i}", currency="KES", credit_limit=Decimal("100.25")) for i in range(5)]
            db.add_all(custs)
            tgt = ExportTarget(name=f"bq-{s}", kind="BIGQUERY", config=t.config, secret=t.secret)
            db.add(tgt)
            await db.flush()
            job = ExportJob(target_id=tgt.id, dataset="customers", file_format="csv", known_ids=[], schema_cols=[])
            db.add(job)
            await db.commit()
            total = (await db.execute(select(func.count()).select_from(Customer))).scalar()
            ids = [c.id for c in custs]
            key = "povu-demo-erp.erp_export.customers"
            await _c("POST", "/_control", json={"faults": {"bq": [{"kind": "jobfail", "match": "JOB povu-demo-erp.erp_export.customers_stg_"}]}})
            r_fail = await wes.run_job(db, job)
            assert r_fail.status == "FAILED" and r_fail.rows == 0 and "failed (invalid)" in r_fail.error
            await db.refresh(job)
            assert job.watermark is None                                   # nothing checkpointed
            r_ok = await wes.run_job(db, job)
            assert r_ok.status == "DONE" and r_ok.rows == total and r_ok.mode == "SIMULATED"
            assert len((await _state())["bq_tables"][key]["rows"]) == total
            await db.execute(update(Customer).where(Customer.id == ids[0]).values(name="POVU BQ renamed"))
            await db.execute(delete(Customer).where(Customer.id == ids[4]))
            await db.commit()
            r2 = await wes.run_job(db, job)
            assert r2.rows == 1 and r2.deleted == 1
            job.watermark, job.watermark_id = None, None
            await db.commit()
            r3 = await wes.run_job(db, job)
            rows = (await _state())["bq_tables"][key]["rows"]
            assert r3.status == "DONE" and len(rows) == total - 1 and "POVU BQ renamed" in {r["name"] for r in rows}
            assert next(r for r in rows if r["code"] == f"BQ{s}-1")["credit_limit"] == "100.25"
    finally:
        await engine.dispose()
