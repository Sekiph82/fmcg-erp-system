"""M45.S01.T020 warehouse export (DB part needs M45_DB=1 and M45_DB2_URL as the warehouse PostgreSQL).

Local S3-compatible store and a second PostgreSQL receive incremental loads: first run loads everything, an update
travels alone next time, a deleted row is removed from the warehouse and listed in a _deletes file, a new column is
added (schema change), the classified KRA PIN is masked, a failed run resumes from the last written batch without
duplicates; Snowflake/BigQuery are NOT_CONFIGURED and parquet NOT_AVAILABLE; egress off blocks the S3 target.
"""
import os
import uuid

import pytest

from app.services import warehouse_export_service as wes

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1" or not os.environ.get("M45_DB2_URL"),
                        reason="requires two task-owned disposable PostgreSQL databases")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_serialize_and_unconfigured():
    rows = [{"id": 1, "name": "POVU", "amount": __import__("decimal").Decimal("2.50")}]
    assert wes.serialize(rows, ["id", "name", "amount"], "csv").decode().splitlines() == ["id,name,amount", "1,POVU,2.50"]
    assert b'"amount": "2.50"' in wes.serialize(rows, ["id", "name", "amount"], "jsonl")
    from types import SimpleNamespace
    with pytest.raises(wes.ExportError) as e:
        wes.writer(SimpleNamespace(kind="SNOWFLAKE"))
    assert "NOT_CONFIGURED" in str(e.value)


@DB
@pytest.mark.asyncio
async def test_incremental_s3_and_postgres(monkeypatch):
    import asyncpg
    from sqlalchemy import delete, update
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.sales import Customer
    from app.models.warehouse_export import ExportJob, ExportTarget
    from tests.provider_sim import s3_app
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    monkeypatch.setattr(wes, "BATCH", 2)
    endpoint = s3_app.serve()
    dsn = os.environ["M45_DB2_URL"].replace("postgresql+asyncpg://", "postgresql://")
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Customer).where(Customer.code.like("SYN-T%")))           # keep the dataset to this test's rows
        custs = [Customer(code=f"DW{s}-{i}", name=f"POVU DW {i}", currency="KES", tax_id="P051234567Z") for i in range(5)]
        db.add_all(custs)
        s3 = ExportTarget(name=f"s3-{s}", kind="S3", config={"endpoint_url": endpoint, "bucket": "erp", "prefix": "povu", "access_key": "k"},
                          secret=wes.encrypt("secret"))
        pg = ExportTarget(name=f"pg-{s}", kind="POSTGRES", config={"schema": f"dw_{s}"}, secret=wes.encrypt(dsn))
        db.add_all([s3, pg])
        await db.flush()
        j_s3 = ExportJob(target_id=s3.id, dataset="customers", file_format="csv", known_ids=[], schema_cols=[])
        j_pg = ExportJob(target_id=pg.id, dataset="customers", file_format="csv", known_ids=[], schema_cols=[])
        db.add_all([j_s3, j_pg])
        await db.commit()
        ids = [c.id for c in custs]

        r1 = await wes.run_job(db, j_s3)
        assert r1.status == "DONE" and r1.rows >= 5 and len(r1.files) >= 3
        body = s3_app.STORE[r1.files[0].replace("s3://", "")].decode()
        assert body.startswith("id,code,name") and "P051234567Z" not in body and "•••67Z" in body   # masked KRA PIN
        # failure mid-run resumes without duplicates
        r_fail = await wes.run_job(db, j_pg, fail_after_batches=1)
        assert r_fail.status == "FAILED" and r_fail.rows == 2
        r_ok = await wes.run_job(db, j_pg)
        assert r_ok.status == "DONE"
        conn = await asyncpg.connect(dsn)
        try:
            n = await conn.fetchval(f'SELECT count(*) FROM "dw_{s}".customers WHERE code LIKE $1', f"DW{s}-%")
            assert n == 5 and r_fail.rows + r_ok.rows >= 5
            # incremental: only the changed row travels
            await db.execute(update(Customer).where(Customer.id == ids[0]).values(name="POVU DW renamed"))
            await db.execute(delete(Customer).where(Customer.id == ids[4]))
            await db.commit()
            r2 = await wes.run_job(db, j_pg)
            assert r2.rows == 1 and r2.deleted == 1
            assert await conn.fetchval(f'SELECT name FROM "dw_{s}".customers WHERE id=$1', str(ids[0])) == "POVU DW renamed"
            assert await conn.fetchval(f'SELECT count(*) FROM "dw_{s}".customers WHERE id=$1', str(ids[4])) == 0
            # schema change: a new column appears in the dataset
            monkeypatch.setitem(wes.DATASETS["customers"], "columns", wes.DATASETS["customers"]["columns"] + ["delivery_city"])
            await db.execute(update(Customer).where(Customer.id == ids[1]).values(delivery_city="Thika"))
            await db.commit()
            r3 = await wes.run_job(db, j_pg)
            assert r3.schema_change["added"] == ["delivery_city"]
            assert await conn.fetchval(f'SELECT delivery_city FROM "dw_{s}".customers WHERE id=$1', str(ids[1])) == "Thika"
        finally:
            await conn.close()
        r4 = await wes.run_job(db, j_s3)
        assert r4.deleted == 1 and any(f.endswith("_deletes.json") for f in s3_app.STORE)
        monkeypatch.setattr(settings, "PROVIDER_EGRESS", "off")
        await db.execute(update(Customer).where(Customer.id == ids[2]).values(name="POVU DW blocked"))
        await db.commit()
        blocked = await wes.run_job(db, j_s3)
        assert blocked.status == "FAILED" and "switched off" in blocked.error
