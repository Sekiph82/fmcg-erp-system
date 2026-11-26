"""M48.S01.T007/T008 Snowflake and BigQuery warehouse writers (same Writer interface as LOCAL_DIR/S3/POSTGRES).

Official contracts (checked 2026-11-26):

Snowflake SQL API v2 — https://docs.snowflake.com/en/developer-guide/sql-api/reference
- Key-pair auth: https://docs.snowflake.com/en/developer-guide/sql-api/authenticating — RS256 JWT,
  iss = ACCOUNT.USER.SHA256:<base64 sha256 of the DER SubjectPublicKeyInfo>, sub = ACCOUNT.USER (upper case, account
  without region; JWT valid at most one hour); headers Authorization: Bearer, X-Snowflake-Authorization-Token-Type: KEYPAIR_JWT.
- POST /api/v2/statements?requestId=<uuid>[&retry=true]: a retried requestId is not executed twice
  (https://docs.snowflake.com/en/developer-guide/sql-api/submitting-requests). Bind values are strings typed
  FIXED/REAL/TEXT/BOOLEAN/DATE (ms since epoch)/TIMESTAMP_TZ ("<ns> <offset minutes>")/TIMESTAMP_NTZ (ns).
- 200 ResultSet / 202 QueryStatus (poll GET /api/v2/statements/{handle}) / 422 QueryFailureStatus
  (https://docs.snowflake.com/en/developer-guide/sql-api/handling-responses).
- Multi-statement: parameters.MULTI_STATEMENT_COUNT; "Snowflake does not currently support variable binding in
  multi-statement SQL requests" (https://docs.snowflake.com/en/developer-guide/sql-api/submitting-multiple-statements).
  So rows are bound into a TRANSIENT staging table with single-statement INSERTs, then one multi-statement request
  BEGIN; MERGE; COMMIT applies them atomically (no bound values there), then the staging table is dropped.

BigQuery REST API v2 — https://cloud.google.com/bigquery/docs/reference/rest
- Service account: RS256 JWT (iss=client_email, scope, aud=token endpoint, exp <= 1h) exchanged at
  https://oauth2.googleapis.com/token with grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
  (https://developers.google.com/identity/protocols/oauth2/service-account#httprest).
- datasets.get/insert, tables.get/insert/patch/delete (patch: additive NULLABLE columns only).
- Load: jobs.insert media upload POST /upload/bigquery/v2/projects/{p}/jobs?uploadType=multipart
  (https://cloud.google.com/bigquery/docs/reference/api-uploads) with a client jobId (a retried insert gets 409 and is
  reconciled with jobs.get). Chosen over tabledata.insertAll: batch load jobs use the free shared slot pool, while
  streaming inserts are billed per byte and rows in the streaming buffer cannot be truncated/deleted for a while.
- MERGE/DELETE via jobs.query (POST /bigquery/v2/projects/{p}/queries) with requestId (15-minute idempotency),
  dryRun cost estimate (totalBytesProcessed) checked against the target's cap, and maximumBytesBilled as a hard stop;
  unfinished jobs are polled with jobs.get until status.state == DONE, then status.errorResult is checked.

Both: identifiers pass an allowlist and are quoted; values only travel as bind parameters / query parameters /
load-job JSON, never inside SQL text. Schema drift: missing columns are added, a type change is refused.
Retries with exponential backoff on 429/5xx and network errors re-use the same idempotency key.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import re
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx
import jwt
from cryptography.hazmat.primitives import serialization

from app.core.provider_http import provider_client
from app.services.warehouse_export_service import DATASETS, ExportError, Writer, _cell, decrypt

ATTEMPTS, BACKOFF = 5, 0.5          # tests set BACKOFF = 0
POLL_INTERVAL, POLL_MAX = 1.0, 600.0
MAX_BINDS = 10000                   # bound values per INSERT statement
RETRY_STATUS = {429, 500, 502, 503, 504}
SF_ADMIN_ROLES = {"ACCOUNTADMIN", "SECURITYADMIN", "SYSADMIN", "ORGADMIN", "USERADMIN"}
BQ_SCOPE = "https://www.googleapis.com/auth/bigquery"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
_BQ_PROJECT = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_HANDLE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


# ── shared helpers ───────────────────────────────────────────────────────────

def ident(name: Any, what: str = "identifier") -> str:
    if not isinstance(name, str) or not _IDENT.match(name):
        raise ExportError(f"Refused {what} {str(name)[:60]!r}: only letters, digits and _ (max 128) are allowed.")
    return name


def erp_types(dataset: str, cols: list[str]) -> dict[str, str]:
    """ERP column type per exported column, read from the SQLAlchemy model: string | int | float | bool | date |
    timestamp_tz | timestamp | numeric:<precision>:<scale>."""
    import app.models  # noqa: F401  registers every table on Base.metadata
    from sqlalchemy import types as sa
    from app.db.base import Base
    table = Base.metadata.tables.get(DATASETS[dataset]["table"])
    out = {}
    for c in cols:
        t = table.c[c].type if table is not None and c in table.c else None
        if isinstance(t, sa.Boolean):
            out[c] = "bool"
        elif isinstance(t, sa.Integer):
            out[c] = "int"
        elif isinstance(t, sa.Float):
            out[c] = "float"
        elif isinstance(t, sa.Numeric):
            out[c] = f"numeric:{t.precision or 38}:{t.scale or 0}"
        elif isinstance(t, sa.DateTime):
            out[c] = "timestamp_tz" if t.timezone else "timestamp"
        elif isinstance(t, sa.Date):
            out[c] = "date"
        else:                                   # String, Text, Enum, UUID, JSON
            out[c] = "string"
    return out


async def send(client: httpx.AsyncClient, method: str, url: str, retry_url: Optional[str] = None, **kw) -> httpx.Response:
    """Request with exponential backoff on 429/5xx and network errors. A retry may follow a lost response, so every
    caller passes an idempotency key (Snowflake requestId + retry=true, BigQuery jobId / requestId)."""
    r: Optional[httpx.Response] = None
    for i in range(ATTEMPTS):
        try:
            r = await client.request(method, retry_url if (i and retry_url) else url, **kw)
            if r.status_code not in RETRY_STATUS:
                return r
        except httpx.TransportError as e:
            if i == ATTEMPTS - 1:
                raise ExportError(f"UNKNOWN: network error talking to the warehouse ({type(e).__name__}); the batch "
                                  "was not checkpointed and is replayed next run.") from None
        if i < ATTEMPTS - 1:
            ra = r.headers.get("Retry-After", "") if r is not None else ""
            await asyncio.sleep((min(float(ra), 30.0) if ra.isdigit() else 2 ** i) * BACKOFF)
    return r                                    # last 429/5xx, mapped by the caller


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _live_switch() -> bool:
    from app.core.config import settings
    return bool(getattr(settings, "WAREHOUSE_LIVE_ENABLED", False))


def _live_gate(t) -> str:
    """SIMULATED under PROVIDER_EGRESS=local (only the local simulator is reachable); LIVE needs the runtime switch
    WAREHOUSE_LIVE_ENABLED and a second administrator's approval of this target."""
    from app.core.provider_http import egress_mode
    if egress_mode() != "live":
        return "SIMULATED"
    if not _live_switch():
        raise ExportError("LIVE_DISABLED: live warehouse sync is off until the owner sets WAREHOUSE_LIVE_ENABLED.")
    if not (t.config or {}).get("approved_by"):
        raise ExportError("LIVE_DISABLED: a second report administrator must approve this target first.")
    return "LIVE"


# ── Snowflake ────────────────────────────────────────────────────────────────

def sf_q(name: str) -> str:
    return '"' + ident(name).upper() + '"'


def sf_type(kind: str) -> tuple[str, str]:
    """(DDL type, INFORMATION_SCHEMA.COLUMNS.DATA_TYPE)."""
    if kind.startswith("numeric:"):
        _, p, s = kind.split(":")
        return f"NUMBER({p},{s})", "NUMBER"
    return {"string": ("VARCHAR", "TEXT"), "int": ("NUMBER(38,0)", "NUMBER"), "float": ("FLOAT", "FLOAT"),
            "bool": ("BOOLEAN", "BOOLEAN"), "date": ("DATE", "DATE"), "timestamp_tz": ("TIMESTAMP_TZ", "TIMESTAMP_TZ"),
            "timestamp": ("TIMESTAMP_NTZ", "TIMESTAMP_NTZ")}[kind]


def sf_bind(kind: str, v: Any) -> dict:
    """Typed SQL API binding; the value is always a string (or null)."""
    typ = {"int": "FIXED", "float": "REAL", "bool": "BOOLEAN", "date": "DATE", "timestamp_tz": "TIMESTAMP_TZ",
           "timestamp": "TIMESTAMP_NTZ"}.get(kind, "TEXT")      # decimals travel as TEXT into a NUMBER(p,s) column
    if v is None:
        return {"type": typ, "value": None}
    if kind == "int":
        val = str(int(v))
    elif kind == "float":
        val = repr(float(v))
    elif kind == "bool":
        val = "true" if v else "false"
    elif kind == "date":
        d = v if isinstance(v, date) else date.fromisoformat(str(v))
        val = str(int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()) * 1000)
    elif kind in ("timestamp_tz", "timestamp"):
        ts = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
        aware = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        ns = int(aware.timestamp()) * 1_000_000_000 + aware.microsecond * 1000
        # TIMESTAMP_TZ offset field is minutes + 1440 (the documented example "… 960" is UTC-08:00)
        val = f"{ns} {int(aware.utcoffset().total_seconds() // 60) + 1440}" if kind == "timestamp_tz" else str(ns)
    else:
        val = str(_cell(v))
    return {"type": typ, "value": val}


def sf_account(account: str) -> str:
    """Account identifier for the JWT, per the documented normalisation (no region / cloud / subdomain)."""
    a = account.strip().upper()
    a = a.split("-")[0] if ".GLOBAL" in a else a.split(".")[0]
    return a


def sf_fingerprint(private_key) -> str:
    der = private_key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return "SHA256:" + base64.b64encode(hashlib.sha256(der).digest()).decode()


class SnowflakeWriter(Writer):
    def __init__(self, t):
        super().__init__(t)
        c = t.config or {}
        for k in ("account", "user", "role", "warehouse", "database", "schema"):
            if not c.get(k):
                raise ExportError(f"Snowflake target needs '{k}'.")
        if not re.match(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_.-]+)?$", c["account"]) or not re.match(r"^[A-Za-z0-9_.@-]{1,255}$", c["user"]):
            raise ExportError("Bad Snowflake account or user name.")
        for k in ("role", "warehouse", "database", "schema"):
            ident(c[k], k)
        if c["role"].upper() in SF_ADMIN_ROLES:
            raise ExportError(f"Refused role {c['role'].upper()}: use a least-privilege loader role that owns only the export schema.")
        self.c = c
        self.base = (c.get("base_url") or f"https://{c['account'].lower()}.snowflakecomputing.com").rstrip("/")
        self.allow_deletes = c.get("allow_deletes", True) is not False
        self._tok: Optional[tuple[str, float]] = None
        self._ready: set[str] = set()
        self.dry: Optional[list] = None         # set to [] to record the plan instead of sending

    def jwt_token(self) -> str:
        if self._tok and self._tok[1] > time.monotonic():
            return self._tok[0]
        try:
            sec = json.loads(decrypt(self.t.secret))
            pw = sec.get("passphrase") or None
            key = serialization.load_pem_private_key(sec["private_key"].encode(), password=pw.encode() if pw else None)
        except Exception:
            raise ExportError("The stored Snowflake private key cannot be read (wrong PEM or passphrase).") from None
        acct, user, now = sf_account(self.c["account"]), self.c["user"].upper(), int(time.time())
        tok = jwt.encode({"iss": f"{acct}.{user}.{sf_fingerprint(key)}", "sub": f"{acct}.{user}", "iat": now,
                          "exp": now + 3540}, key, algorithm="RS256")
        self._tok = (tok, time.monotonic() + 3000)
        return tok

    def _tbl(self, name: str) -> str:
        return f"{sf_q(self.c['database'])}.{sf_q(self.c['schema'])}.{sf_q(name)}"

    async def sql(self, statement: str, bindings: Optional[dict] = None, count: int = 1) -> dict:
        if self.dry is not None:
            self.dry.append({"request": "POST /api/v2/statements", "statement": statement,
                             "binding_types": sorted({b["type"] for b in (bindings or {}).values()}),
                             "bound_values": len(bindings or {}), **({"MULTI_STATEMENT_COUNT": count} if count != 1 else {})})
            return {"data": []}
        body: dict = {"statement": statement, "timeout": 600, "database": self.c["database"].upper(),
                      "schema": self.c["schema"].upper(), "warehouse": self.c["warehouse"].upper(), "role": self.c["role"].upper()}
        if bindings:
            body["bindings"] = bindings
        if count != 1:
            body["parameters"] = {"MULTI_STATEMENT_COUNT": str(count)}
        url = f"{self.base}/api/v2/statements?requestId={uuid.uuid4()}"
        headers = {"Authorization": f"Bearer {self.jwt_token()}", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
                   "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "POVU-ERP-warehouse/1.0"}
        async with provider_client(timeout=60) as cl:
            r = await send(cl, "POST", url, retry_url=url + "&retry=true", json=body, headers=headers)
            deadline = time.monotonic() + POLL_MAX
            while r.status_code == 202:
                handle = (r.json() or {}).get("statementHandle", "")
                if not _HANDLE.match(handle):
                    raise ExportError("Snowflake returned a bad statement handle.")
                if time.monotonic() > deadline:
                    raise ExportError(f"UNKNOWN: Snowflake statement {handle} still running; nothing was checkpointed, "
                                      "the batch is replayed next run (MERGE keeps it idempotent).")
                await asyncio.sleep(POLL_INTERVAL)
                r = await send(cl, "GET", f"{self.base}/api/v2/statements/{handle}", headers=headers)
        if r.status_code == 200:
            return r.json()
        try:
            e = r.json()
        except ValueError:
            e = {}
        if r.status_code in (401, 403):
            raise ExportError(f"Snowflake refused the key-pair login ({r.status_code} {e.get('code', '')}): {e.get('message', '')}"[:400])
        raise ExportError(f"Snowflake {r.status_code} {e.get('code', '')} {e.get('sqlState', '')}: {e.get('message', r.text[:200])}"[:400])

    async def test_connection(self) -> dict:
        res = await self.sql("SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
        row = (res.get("data") or [[None, None, None]])[0]
        return {"ok": True, "role": row[0], "warehouse": row[1], "database": row[2]}

    async def _provision(self, dataset: str, cols: list[str], kinds: dict) -> list[str]:
        if dataset in self._ready:
            return []
        tbl = self._tbl(dataset)
        await self.sql(f"CREATE SCHEMA IF NOT EXISTS {sf_q(self.c['database'])}.{sf_q(self.c['schema'])}")
        defs = ", ".join(f"{sf_q(c)} {sf_type(kinds[c])[0]}" for c in cols)
        await self.sql(f'CREATE TABLE IF NOT EXISTS {tbl} ({defs}, "_LOADED_AT" TIMESTAMP_TZ)')
        res = await self.sql(f"SELECT COLUMN_NAME, DATA_TYPE FROM {sf_q(self.c['database'])}.INFORMATION_SCHEMA.COLUMNS "
                             "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
                             {"1": {"type": "TEXT", "value": self.c["schema"].upper()}, "2": {"type": "TEXT", "value": dataset.upper()}})
        have = {row[0]: row[1] for row in res.get("data") or []}
        added, bad = [], []
        for c in cols:
            got = have.get(c.upper())
            if got is None:
                added.append(c)
            elif got != sf_type(kinds[c])[1]:
                bad.append(f"{c} is {got} in Snowflake but the ERP sends {sf_type(kinds[c])[1]}")
        if bad:
            raise ExportError("Schema drift refused (incompatible change): " + "; ".join(bad) +
                              ". Nothing was written; change the warehouse column or point the job at a new table.")
        if self.dry is not None:
            added = []                          # the plan cannot see the live table
        for c in added:
            await self.sql(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {sf_q(c)} {sf_type(kinds[c])[0]}")
        self._ready.add(dataset)
        return [a for a in added if a != "id"]

    async def put(self, key, data):
        return ""                               # the warehouse gets rows, not files

    async def upsert(self, dataset, cols, rows):
        if "id" not in cols:
            raise ExportError("Upsert needs an id column.")
        kinds = erp_types(dataset, cols)
        added = await self._provision(dataset, cols, kinds)
        tbl, stg = self._tbl(dataset), self._tbl(f"{dataset}_stg_{uuid.uuid4().hex[:12]}")
        names = ", ".join(sf_q(c) for c in cols)
        await self.sql(f"CREATE TRANSIENT TABLE {stg} ({', '.join(f'{sf_q(c)} {sf_type(kinds[c])[0]}' for c in cols)}) "
                       "DATA_RETENTION_TIME_IN_DAYS = 0")
        try:
            for part in _chunks(rows, max(1, MAX_BINDS // len(cols))):
                bindings, n = {}, 0
                for r in part:
                    for c in cols:
                        n += 1
                        bindings[str(n)] = sf_bind(kinds[c], r.get(c))
                ph = ", ".join("(" + ", ".join("?" for _ in cols) + ")" for _ in part)
                await self.sql(f"INSERT INTO {stg} ({names}) VALUES {ph}", bindings)
            sets = ", ".join(f"t.{sf_q(c)} = s.{sf_q(c)}" for c in cols if c != "id")
            merge = (f'MERGE INTO {tbl} t USING {stg} s ON t."ID" = s."ID" '
                     f'WHEN MATCHED THEN UPDATE SET {sets}, t."_LOADED_AT" = CURRENT_TIMESTAMP() '
                     f'WHEN NOT MATCHED THEN INSERT ({names}, "_LOADED_AT") '
                     f'VALUES ({", ".join(f"s.{sf_q(c)}" for c in cols)}, CURRENT_TIMESTAMP())')
            await self.sql(f"BEGIN TRANSACTION; {merge}; COMMIT", count=3)
        finally:
            with contextlib.suppress(ExportError):  # ponytail: a leaked transient staging table costs ~nothing; drop next time by hand
                await self.sql(f"DROP TABLE IF EXISTS {stg}")
        return added

    async def delete(self, dataset, ids):
        if not self.allow_deletes or not ids:
            return
        cols = list(DATASETS[dataset]["columns"])
        kinds = erp_types(dataset, cols)
        await self._provision(dataset, cols, kinds)
        for part in _chunks(ids, MAX_BINDS):
            await self.sql(f'DELETE FROM {self._tbl(dataset)} WHERE "ID" IN ({", ".join("?" for _ in part)})',
                           {str(i + 1): sf_bind(kinds["id"], v) for i, v in enumerate(part)})


# ── BigQuery ─────────────────────────────────────────────────────────────────

def bq_type(kind: str) -> str:
    if kind.startswith("numeric:"):
        _, p, s = (int(x) if x.isdigit() else x for x in kind.split(":"))
        return "NUMERIC" if s <= 9 and p - s <= 29 else "BIGNUMERIC"
    return {"string": "STRING", "int": "INTEGER", "float": "FLOAT", "bool": "BOOLEAN", "date": "DATE",
            "timestamp_tz": "TIMESTAMP", "timestamp": "DATETIME"}[kind]


_BQ_ALIAS = {"INT64": "INTEGER", "FLOAT64": "FLOAT", "BOOL": "BOOLEAN", "BIGDECIMAL": "BIGNUMERIC", "DECIMAL": "NUMERIC"}


def bq_json(kind: str, v: Any) -> Any:
    if v is None:
        return None
    if kind == "int":
        return int(v)
    if kind == "float":
        return float(v)
    if kind == "bool":
        return bool(v)
    if kind.startswith("numeric:"):
        return str(v)
    return str(_cell(v)) if kind == "string" else _cell(v)      # dates/timestamps as ISO 8601


class BigQueryWriter(Writer):
    def __init__(self, t):
        super().__init__(t)
        c = t.config or {}
        if not c.get("project") or not _BQ_PROJECT.match(str(c["project"])):
            raise ExportError("BigQuery target needs a valid 'project' id (6-30 lower-case letters, digits, -).")
        ident(c.get("dataset"), "dataset")
        self.c = c
        self.p, self.d, self.loc = c["project"], c["dataset"], c.get("location") or "US"
        if not re.match(r"^[A-Za-z0-9-]{2,30}$", self.loc):
            raise ExportError("Bad BigQuery location.")
        try:
            self.cap = int(c.get("max_bytes_billed") or 1_000_000_000)
        except (TypeError, ValueError):
            raise ExportError("max_bytes_billed must be a whole number of bytes.") from None
        if self.cap <= 0:
            raise ExportError("max_bytes_billed must be positive.")
        self.base = (c.get("base_url") or "https://bigquery.googleapis.com").rstrip("/")
        self.token_url = c.get("token_url") or "https://oauth2.googleapis.com/token"
        self.allow_deletes = c.get("allow_deletes", True) is not False
        self._tok: Optional[tuple[str, float]] = None
        self._ready: set[str] = set()
        self.dry: Optional[list] = None

    def assertion(self) -> str:
        try:
            sa = json.loads(decrypt(self.t.secret))
            key, email = sa["private_key"], sa["client_email"]
        except Exception:
            raise ExportError("The stored service-account key cannot be read.") from None
        now = int(time.time())
        return jwt.encode({"iss": email, "scope": BQ_SCOPE, "aud": self.token_url, "iat": now, "exp": now + 3600},
                          key, algorithm="RS256", headers={"kid": sa.get("private_key_id") or ""})

    async def _token(self, cl) -> str:
        if self._tok and self._tok[1] > time.monotonic():
            return self._tok[0]
        r = await send(cl, "POST", self.token_url, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                                          "assertion": self.assertion()})
        if r.status_code != 200:
            e = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            raise ExportError(f"Google token exchange failed ({r.status_code} {e.get('error', '')}): {e.get('error_description', '')}"[:300])
        b = r.json()
        self._tok = (b["access_token"], time.monotonic() + int(b.get("expires_in", 3600)) - 120)
        return self._tok[0]

    async def call(self, method: str, path: str, ok=(200,), **kw) -> httpx.Response:
        if self.dry is not None:
            body = kw.get("json")
            self.dry.append({"request": f"{method} {path}", **({"body": body} if body is not None else {}),
                             **({"upload": kw["upload_note"]} if "upload_note" in kw else {})})
            return httpx.Response(200, json={"jobComplete": True, "status": {"state": "DONE"}, "schema": {"fields": []},
                                             "totalBytesProcessed": "0"})
        kw.pop("upload_note", None)
        async with provider_client(timeout=60) as cl:
            headers = {"Authorization": f"Bearer {await self._token(cl)}", **kw.pop("headers", {})}
            r = await send(cl, method, self.base + path, headers=headers, **kw)
        if r.status_code in ok:
            return r
        try:
            err = r.json().get("error") or {}
        except ValueError:
            err = {}
        reason = ((err.get("errors") or [{}])[0]).get("reason", "")
        raise ExportError(f"BigQuery {r.status_code} {reason}: {err.get('message', r.text[:200])}"[:400])

    def _fq(self, table: str) -> str:
        return f"`{self.p}.{ident(self.d)}.{ident(table)}`"

    def _tpath(self, table: str = "") -> str:
        base = f"/bigquery/v2/projects/{self.p}/datasets/{self.d}/tables"
        return f"{base}/{ident(table)}" if table else base

    async def wait_job(self, job_id: str) -> dict:
        deadline = time.monotonic() + POLL_MAX
        while True:
            j = (await self.call("GET", f"/bigquery/v2/projects/{self.p}/jobs/{job_id}", params={"location": self.loc})).json()
            st = j.get("status") or {}
            if st.get("state") == "DONE":
                if st.get("errorResult"):
                    er = st["errorResult"]
                    raise ExportError(f"BigQuery job {job_id} failed ({er.get('reason', '')}): {er.get('message', '')}"[:400])
                return j
            if time.monotonic() > deadline:
                raise ExportError(f"UNKNOWN: BigQuery job {job_id} still {st.get('state')}; the batch is replayed next run.")
            await asyncio.sleep(POLL_INTERVAL)

    async def query(self, sql: str, params: Optional[list] = None) -> dict:
        """Cost-guarded DML: dry run first, refuse above the cap, then run with maximumBytesBilled as a hard stop."""
        base = {"query": sql, "useLegacySql": False, "location": self.loc}
        if params:
            base.update(parameterMode="NAMED", queryParameters=params)
        dry = (await self.call("POST", f"/bigquery/v2/projects/{self.p}/queries", json={**base, "dryRun": True})).json()
        est = int(dry.get("totalBytesProcessed") or 0)
        if est > self.cap:
            raise ExportError(f"Cost guard: the statement would process {est} bytes, above this target's cap of {self.cap}; "
                              "nothing was changed. Raise max_bytes_billed or partition the table.")
        r = (await self.call("POST", f"/bigquery/v2/projects/{self.p}/queries",
                             json={**base, "requestId": str(uuid.uuid4()), "maximumBytesBilled": str(self.cap),
                                   "timeoutMs": 10000})).json()
        if not r.get("jobComplete"):
            jid = ((r.get("jobReference") or {}).get("jobId")) or ""
            if not _HANDLE.match(jid):
                raise ExportError("BigQuery returned a bad job id.")
            await self.wait_job(jid)
        return r

    async def test_connection(self) -> dict:
        r = await self.call("GET", f"/bigquery/v2/projects/{self.p}/datasets/{self.d}", ok=(200, 404))
        return {"ok": True, "project": self.p, "dataset": self.d, "dataset_exists": r.status_code == 200}

    def _fields(self, cols, kinds) -> list[dict]:
        return [{"name": ident(c), "type": bq_type(kinds[c]), "mode": "NULLABLE"} for c in cols]

    async def _provision(self, dataset: str, cols: list[str], kinds: dict) -> list[str]:
        if dataset in self._ready:
            return []
        ident(dataset)
        r = await self.call("GET", f"/bigquery/v2/projects/{self.p}/datasets/{self.d}", ok=(200, 404))
        if r.status_code == 404:
            await self.call("POST", f"/bigquery/v2/projects/{self.p}/datasets", ok=(200, 409),
                            json={"datasetReference": {"projectId": self.p, "datasetId": self.d}, "location": self.loc})
        want = self._fields(cols, kinds) + [{"name": "_loaded_at", "type": "TIMESTAMP", "mode": "NULLABLE"}]
        r = await self.call("GET", self._tpath(dataset), ok=(200, 404))
        added: list[str] = []
        if r.status_code == 404 or self.dry is not None:
            await self.call("POST", self._tpath(), ok=(200, 409),
                            json={"tableReference": {"projectId": self.p, "datasetId": self.d, "tableId": dataset},
                                  "schema": {"fields": want}})
        else:
            have = {f["name"]: _BQ_ALIAS.get(f["type"], f["type"]) for f in (r.json().get("schema") or {}).get("fields", [])}
            bad = [f"{f['name']} is {have[f['name']]} in BigQuery but the ERP sends {f['type']}"
                   for f in want if f["name"] in have and have[f["name"]] != f["type"]]
            if bad:
                raise ExportError("Schema drift refused (incompatible change): " + "; ".join(bad) +
                                  ". Nothing was written; change the warehouse column or point the job at a new table.")
            new = [f for f in want if f["name"] not in have]
            if new:
                fields = r.json()["schema"]["fields"] + new          # tables.patch: additive NULLABLE columns only
                await self.call("PATCH", self._tpath(dataset), json={"schema": {"fields": fields}})
                added = [f["name"] for f in new]
        self._ready.add(dataset)
        return [a for a in added if a not in ("id", "_loaded_at")]

    async def put(self, key, data):
        return ""

    async def upsert(self, dataset, cols, rows):
        if "id" not in cols:
            raise ExportError("Upsert needs an id column.")
        kinds = erp_types(dataset, cols)
        added = await self._provision(dataset, cols, kinds)
        stg = f"{dataset}_stg_{uuid.uuid4().hex[:12]}"
        fields = self._fields(cols, kinds)
        await self.call("POST", self._tpath(), json={"tableReference": {"projectId": self.p, "datasetId": self.d, "tableId": stg},
                                                     "schema": {"fields": fields},
                                                     "expirationTime": str(int(time.time() * 1000) + 3_600_000)})
        try:
            ndjson = "".join(json.dumps({c: bq_json(kinds[c], r.get(c)) for c in cols}, ensure_ascii=False) + "\n" for r in rows).encode()
            job_id = f"povu_erp_{uuid.uuid4().hex}"
            meta = {"jobReference": {"projectId": self.p, "jobId": job_id, "location": self.loc},
                    "configuration": {"load": {"destinationTable": {"projectId": self.p, "datasetId": self.d, "tableId": stg},
                                               "sourceFormat": "NEWLINE_DELIMITED_JSON", "writeDisposition": "WRITE_TRUNCATE",
                                               "createDisposition": "CREATE_NEVER", "schema": {"fields": fields}}}}
            boundary = uuid.uuid4().hex
            body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                    f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + ndjson + f"\r\n--{boundary}--\r\n".encode()
            await self.call("POST", f"/upload/bigquery/v2/projects/{self.p}/jobs?uploadType=multipart", ok=(200, 409),
                            content=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"},
                            upload_note={"job": meta, "rows": len(rows), "bytes": len(ndjson)})
            await self.wait_job(job_id)          # 409 = our earlier attempt got through: reconcile through jobs.get
            sets = ", ".join(f"`{c}` = S.`{c}`" for c in cols if c != "id")
            names = ", ".join(f"`{c}`" for c in cols)
            await self.query(f"MERGE {self._fq(dataset)} T USING {self._fq(stg)} S ON T.`id` = S.`id` "
                             f"WHEN MATCHED THEN UPDATE SET {sets}, `_loaded_at` = CURRENT_TIMESTAMP() "
                             f"WHEN NOT MATCHED THEN INSERT ({names}, `_loaded_at`) "
                             f"VALUES ({', '.join(f'S.`{c}`' for c in cols)}, CURRENT_TIMESTAMP())")
        finally:
            with contextlib.suppress(ExportError):  # the staging table also expires by itself after an hour
                await self.call("DELETE", self._tpath(stg), ok=(200, 204, 404))
        return added

    async def delete(self, dataset, ids):
        if not self.allow_deletes or not ids:
            return
        cols = list(DATASETS[dataset]["columns"])
        kinds = erp_types(dataset, cols)
        await self._provision(dataset, cols, kinds)
        typ = bq_type(kinds["id"]).replace("INTEGER", "INT64")
        for part in _chunks(ids, 10000):
            await self.query(f"DELETE FROM {self._fq(dataset)} WHERE `id` IN UNNEST(@ids)",
                             [{"name": "ids", "parameterType": {"type": "ARRAY", "arrayType": {"type": typ}},
                               "parameterValue": {"arrayValues": [{"value": str(v)} for v in part]}}])


async def plan(w, dataset: str, cols: list[str], rows: int) -> list[dict]:
    """The requests/SQL a sync would send for one batch of `rows` rows, recorded without any network call or data."""
    w.dry = []
    fake = [{c: None for c in cols} for _ in range(max(rows, 1))]
    await w.upsert(dataset, cols, fake)
    return w.dry
