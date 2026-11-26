"""M45.S01.T020 incremental export of CRM/ERP datasets to object storage and a PostgreSQL warehouse.

Targets: LOCAL_DIR (files), S3 (any S3-compatible store, e.g. MinIO, through boto3), POSTGRES (upsert into a
warehouse schema), SNOWFLAKE (SQL API v2) and BIGQUERY (REST v2) through warehouse_cloud_writers (M48.S01.T007/T008);
those two are NOT_CONFIGURED only while their credential is missing.
Formats: CSV, JSON Lines and typed Parquet (pyarrow, M50.S01.T010; see parquet_service).

- Incremental: rows with (updated_at, id) after the job's watermark, in batches; the watermark moves after every
  successfully written batch, so a failed run resumes where it stopped without gaps or duplicates.
- Deletes: ids seen last run but gone now are written as a `_deletes` file / deleted from the warehouse table.
- Schema: each file carries a manifest with the column list; a new column is added to the warehouse table
  (ALTER TABLE ADD COLUMN IF NOT EXISTS) and reported as a schema change.
- Privacy: only allow-listed columns per dataset; fields classified sensitive (T017) are always masked in exports.
- Egress: PROVIDER_EGRESS=off blocks everything; =local allows only local hosts (e.g. MinIO on localhost).
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.warehouse_export import ExportJob, ExportRun, ExportTarget

DATASETS: dict[str, dict] = {
    "customers": {"table": "customers", "entity": "customer",
                  "columns": ["id", "code", "name", "channel", "city", "country", "region", "segment", "currency",
                              "payment_terms_days", "credit_limit", "tax_id", "is_active", "created_at", "updated_at"]},
    "sales_orders": {"table": "sales_orders", "columns": ["id", "order_no", "customer_id", "order_date", "status", "currency",
                                                          "payment_status", "source", "created_at", "updated_at"]},
    "invoices": {"table": "invoices", "columns": ["id", "invoice_no", "so_id", "customer_id", "invoice_date", "due_date", "status",
                                                  "currency", "subtotal", "tax_amount", "total_amount", "paid_amount", "created_at", "updated_at"]},
    "products": {"table": "products", "columns": ["id", "sku", "name", "category", "uom", "is_active", "created_at", "updated_at"]},
    "crm_records": {"table": "crm_records", "columns": ["id", "record_type", "company_name", "status", "stage_id", "expected_revenue",
                                                        "probability_pct", "expected_close_date", "assigned_customer_id", "created_at", "updated_at"]},
}
BATCH = 1000
CLOUD_KINDS = {"SNOWFLAKE": "Snowflake needs the loader user's key-pair private key (PEM).",
               "BIGQUERY": "BigQuery needs a service-account key (JSON)."}


class ExportError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cipher():
    from cryptography.fernet import Fernet
    key = hashlib.sha256(b"fmcg-erp:dw-target:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().encrypt(v.encode()).decode() if v else None


def decrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().decrypt(v.encode()).decode() if v else None


def check_host(url: str) -> None:
    from app.core.provider_http import EgressBlocked, _is_local_host, egress_mode
    mode, host = egress_mode(), urlsplit(url).hostname or ""
    if mode == "off":
        raise EgressBlocked("Exports to external systems are switched off (PROVIDER_EGRESS=off).")
    if mode == "local" and not _is_local_host(host):
        raise EgressBlocked(f"Only local targets are allowed here; refused {host}.")


def _cell(v: Any) -> Any:
    if isinstance(v, (datetime,)):
        return v.isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (Decimal, uuid.UUID)):
        return str(v)
    if hasattr(v, "value"):
        return v.value
    return v


def serialize(rows: list[dict], cols: list[str], fmt: str, table: Optional[str] = None, masked: tuple = ()) -> bytes:
    if fmt == "parquet":
        from app.services import parquet_service as pqs
        return pqs.write(rows, pqs.dataset_types(table, cols, masked), {"dataset": table, "exported_at": _now().isoformat(),
                                                                          "masked": ",".join(sorted(masked))})
    if fmt == "jsonl":
        return "".join(json.dumps({c: _cell(r.get(c)) for c in cols}, ensure_ascii=False) + "\n" for r in rows).encode()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: _cell(r.get(c)) for c in cols})
    return buf.getvalue().encode()


# ── target writers ───────────────────────────────────────────────────────────

class Writer:
    def __init__(self, target: ExportTarget):
        self.t = target

    async def put(self, key: str, data: bytes) -> str: ...
    async def upsert(self, dataset: str, cols: list[str], rows: list[dict]) -> list[str]: return []
    async def delete(self, dataset: str, ids: list[str]) -> None: ...


class LocalDirWriter(Writer):
    async def put(self, key, data):
        root = Path(self.t.config["dir"]).resolve()
        p = (root / key).resolve()
        if root not in p.parents:
            raise ExportError("Bad file key.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return str(p)


class S3Writer(Writer):
    def _client(self):
        import boto3
        check_host(self.t.config["endpoint_url"])
        from botocore.config import Config
        return boto3.client("s3", endpoint_url=self.t.config["endpoint_url"], region_name=self.t.config.get("region") or "us-east-1",
                            aws_access_key_id=self.t.config.get("access_key"), aws_secret_access_key=decrypt(self.t.secret),
                            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 2}))

    async def put(self, key, data):
        import asyncio
        prefix = (self.t.config.get("prefix") or "").strip("/")
        full = f"{prefix}/{key}" if prefix else key
        await asyncio.to_thread(self._client().put_object, Bucket=self.t.config["bucket"], Key=full, Body=data)
        return f"s3://{self.t.config['bucket']}/{full}"


class PostgresWriter(Writer):
    async def _conn(self):
        import asyncpg
        dsn = decrypt(self.t.secret) or ""
        if "?" in dsn:
            raise ExportError("Connection URLs with query parameters are not accepted (they can redirect the host).")
        check_host(dsn.replace("postgresql+asyncpg://", "postgresql://"))
        return await asyncpg.connect(dsn.replace("postgresql+asyncpg://", "postgresql://"))

    def _schema(self) -> str:
        s = self.t.config.get("schema") or "erp_export"
        if not s.replace("_", "").isalnum():
            raise ExportError("Bad schema name.")
        return s

    async def put(self, key, data):
        return ""            # the warehouse gets rows, not files

    async def upsert(self, dataset, cols, rows):
        conn = await self._conn()
        s, added = self._schema(), []
        try:
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}"')
            await conn.execute(f'CREATE TABLE IF NOT EXISTS "{s}"."{dataset}" (id text PRIMARY KEY, _loaded_at timestamptz)')
            have = {r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=$1 AND table_name=$2", s, dataset)}
            for c in cols:
                if c not in have:
                    await conn.execute(f'ALTER TABLE "{s}"."{dataset}" ADD COLUMN IF NOT EXISTS "{c}" text')
                    added.append(c)
            names = ", ".join(f'"{c}"' for c in cols)
            ph = ", ".join(f"${i + 1}" for i in range(len(cols)))
            upd = ", ".join(f'"{c}"=EXCLUDED."{c}"' for c in cols if c != "id")
            sql = (f'INSERT INTO "{s}"."{dataset}" ({names}, _loaded_at) VALUES ({ph}, now()) '
                   f'ON CONFLICT (id) DO UPDATE SET {upd}, _loaded_at=now()')
            await conn.executemany(sql, [[None if r.get(c) is None else str(_cell(r.get(c))) for c in cols] for r in rows])
        finally:
            await conn.close()
        return [a for a in added if a != "id"]

    async def delete(self, dataset, ids):
        conn = await self._conn()
        try:
            await conn.execute(f'DELETE FROM "{self._schema()}"."{dataset}" WHERE id = ANY($1::text[])', ids)
        finally:
            await conn.close()


def writer(t: ExportTarget) -> Writer:
    if t.kind in CLOUD_KINDS:
        if not getattr(t, "secret", None):
            raise ExportError(f"NOT_CONFIGURED: {CLOUD_KINDS[t.kind]}")
        from app.services import warehouse_cloud_writers as cw
        mode = cw._live_gate(t)
        w = (cw.SnowflakeWriter if t.kind == "SNOWFLAKE" else cw.BigQueryWriter)(t)
        w.mode = mode
        return w
    return {"LOCAL_DIR": LocalDirWriter, "S3": S3Writer, "POSTGRES": PostgresWriter}[t.kind](t)


# ── run ──────────────────────────────────────────────────────────────────────

async def run_job(db: AsyncSession, job: ExportJob, fail_after_batches: Optional[int] = None) -> ExportRun:
    """One incremental run. `fail_after_batches` simulates an outage (tests)."""
    from app.services import sensitive_service as sens
    await db.refresh(job)                     # callers may hold an expired instance
    got = (await db.execute(text("SELECT pg_try_advisory_lock(hashtext(:k))"), {"k": f"dw:{job.id}"})).scalar()
    if not got:                               # another worker is exporting this job right now
        return ExportRun(job_id=job.id, status="SKIPPED", error="Another run of this job is in progress.")
    try:
        return await _run_job_locked(db, job, fail_after_batches)
    finally:
        await db.execute(text("SELECT pg_advisory_unlock(hashtext(:k))"), {"k": f"dw:{job.id}"})


async def _run_job_locked(db: AsyncSession, job: ExportJob, fail_after_batches: Optional[int]) -> ExportRun:
    from app.services import sensitive_service as sens
    spec = DATASETS[job.dataset]
    target = await db.get(ExportTarget, job.target_id)
    run = ExportRun(job_id=job.id)
    db.add(run)
    await db.commit()                         # the run is recorded even if the target fails at once
    run_id, job_id = run.id, job.id
    try:
        w = writer(target)
        run.mode = getattr(w, "mode", None)      # SIMULATED (local simulator) or LIVE, cloud targets only
        if job.file_format not in ("csv", "jsonl", "parquet"):
            raise ExportError(f"Unknown file format {job.file_format!r}.")
        cols = list(spec["columns"])
        masked = (await sens.policy(db)).get(spec.get("entity", ""), set()) if spec.get("entity") else set()
        change = {"added": [c for c in cols if job.schema_cols and c not in job.schema_cols],
                  "removed": [c for c in (job.schema_cols or []) if c not in cols]}
        stamp = _now().strftime("%Y%m%dT%H%M%S")
        batches = 0
        while True:
            where = ""
            params: dict = {"lim": BATCH}
            if job.watermark is not None:
                where = "WHERE (updated_at > :wm OR (updated_at = :wm AND id::text > :wid))"
                params.update(wm=job.watermark, wid=job.watermark_id or "")
            rows = [dict(r) for r in (await db.execute(text(
                f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{spec["table"]}" {where} '
                f'ORDER BY updated_at, id::text LIMIT :lim'), params)).mappings()]
            if not rows:
                break
            if fail_after_batches is not None and batches >= fail_after_batches:
                raise ExportError("Simulated target outage.")
            for r in rows:
                for f in masked:
                    if f in r:
                        r[f] = sens.mask(r[f] if isinstance(r[f], str) else None)
            key = f"{job.dataset}/{stamp}-{run.id.hex[:8]}-part{batches:04d}.{job.file_format}"
            loc = await w.put(key, serialize(rows, cols, job.file_format, spec["table"], tuple(masked)))
            added = await w.upsert(job.dataset, cols, rows)
            if added and job.schema_cols:
                change["added"] = sorted(set(change["added"]) | set(added))
            if loc:
                await w.put(key + ".manifest.json", json.dumps({"dataset": job.dataset, "columns": cols, "rows": len(rows),
                                                                 "masked": sorted(masked)}).encode())
                run.files = [*run.files, loc]
            job.watermark, job.watermark_id = rows[-1]["updated_at"], str(rows[-1]["id"])
            run.rows += len(rows)
            batches += 1
            await db.commit()                 # watermark after each written batch: resume without gaps
        current = {str(i) for i in (await db.execute(text(f'SELECT id::text FROM "{spec["table"]}"'))).scalars()}
        gone = sorted(set(job.known_ids or []) - current)
        if gone:
            await w.put(f"{job.dataset}/{stamp}-{run.id.hex[:8]}-_deletes.json", json.dumps({"deleted_ids": gone}).encode())
            await w.delete(job.dataset, gone)
            run.deleted = len(gone)
        job.known_ids = sorted(current)[:200000]   # ponytail: id set kept in the job row; move to a table past ~200k rows
        job.schema_cols = cols
        run.schema_change = change if (change["added"] or change["removed"]) else None
        run.status, run.finished_at = "DONE", _now()
    except Exception as e:
        await db.rollback()                   # earlier batches stay committed together with their watermark
        run, job = await db.get(ExportRun, run_id), await db.get(ExportJob, job_id)
        run.status, run.error, run.finished_at = "FAILED", f"{type(e).__name__}: {e}"[:500], _now()
    if job.every_minutes:
        from datetime import timedelta
        job.next_run_at = _now() + timedelta(minutes=job.every_minutes)
    await db.commit()
    await db.refresh(run)                     # after a rollback some attributes were expired: load them for callers
    return run


async def tick(db: AsyncSession) -> int:
    n = 0
    for job in (await db.execute(select(ExportJob).where(ExportJob.active.is_(True), ExportJob.every_minutes.is_not(None),
                                                         or_(ExportJob.next_run_at.is_(None), ExportJob.next_run_at <= _now()))
                                 .limit(5))).scalars().all():
        await run_job(db, job)
        n += 1
    return n
