"""Local Snowflake SQL API v2 + BigQuery REST v2 + Google token endpoint simulator (M48.S01.T007/T008).

Synthetic and in-memory; never a real warehouse. It follows the documented wire contracts the ERP adapter uses
(see app/services/warehouse_cloud_writers.py for the doc URLs):

Snowflake  /snowflake/api/v2/statements[?requestId&retry=true], GET /snowflake/api/v2/statements/{handle}
  - KEYPAIR_JWT verified (RS256 signature against the registered public key, iss fingerprint, sub, <=1h lifetime)
  - 200 ResultSet / 202 QueryStatus while "running" / 422 QueryFailureStatus / 429 / 401
  - requestId + retry=true returns the stored outcome without executing again
  - multi-statement needs MULTI_STATEMENT_COUNT and refuses bindings (documented limitation); BEGIN..COMMIT rolls
    back on a failing statement; typed bindings are decoded and type-checked against the column type
  - SQL: only the statement shapes the adapter emits are understood (anything else is a 422 compilation error);
    the statement splitter is naive because the adapter never puts literals into SQL text.
BigQuery   /bq/bigquery/v2/... datasets/tables get/insert/patch/delete, jobs.get, jobs.query (dryRun,
  maximumBytesBilled, requestId), /bq/upload/bigquery/v2/projects/{p}/jobs?uploadType=multipart (load jobs with a
  client jobId; duplicate -> 409); jobs move PENDING/RUNNING -> DONE across polls; errorResult on failure;
  Google error envelope {"error": {"code", "message", "errors": [{"reason"}], "status"}}.
Token      POST /oauth2/token (jwt-bearer grant, aud must equal this URL, BigQuery scope).

Control: POST /_control {"faults": {"sf"|"bq": [kind | {"kind", "match"}]}, "sf_async": n, "bq_async": n,
"sf_keys": {"ACCOUNT.USER": public_pem}, "bq_keys": {email: public_pem}}; GET /_control/state;
GET /_control/demo-credentials (synthetic key pair for the manual UI walkthrough).
Fault kinds: 429, 503, "lost" (executed, response lost as 503), "fail" (422 / failed job), "jobfail" (BigQuery job errorResult).
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email import message_from_bytes
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

SF_ACCOUNT, SF_USER = "POVU-DEMO", "ERP_LOADER"
BQ_EMAIL, BQ_PROJECT = "erp-loader@povu-demo-erp.iam.povu-demo.test", "povu-demo-erp"


def sf_config(base: str, **kw) -> dict:
    return {"account": SF_ACCOUNT, "user": SF_USER, "role": "ERP_LOADER", "warehouse": "LOAD_WH", "database": "POVU_DW",
            "schema": "ERP", "base_url": base.rstrip("/") + "/snowflake", **kw}


def bq_config(base: str, **kw) -> dict:
    return {"project": BQ_PROJECT, "dataset": "erp_export", "location": "US", "base_url": base.rstrip("/") + "/bq",
            "token_url": base.rstrip("/") + "/oauth2/token", **kw}


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def pem(key) -> str:
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()


def pub_pem(key) -> str:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


class SqlErr(Exception):
    def __init__(self, code: str, msg: str, state: str = "42000"):
        super().__init__(msg)
        self.code, self.msg, self.state = code, msg, state


Q = r'"([A-Za-z0-9_]+)"'
FQ = Q + r"\." + Q + r"\." + Q
TYPE = r"([A-Z_]+(?:\(\d+,\d+\))?)"


def _fam(ddl: str) -> str:
    base = ddl.split("(")[0]
    return {"VARCHAR": "TEXT", "NUMBER": "NUMBER", "FLOAT": "FLOAT", "BOOLEAN": "BOOLEAN", "DATE": "DATE",
            "TIMESTAMP_TZ": "TIMESTAMP_TZ", "TIMESTAMP_NTZ": "TIMESTAMP_NTZ"}.get(base) or _bad_type(ddl)


def _bad_type(ddl):
    raise SqlErr("002040", f"SQL compilation error: unsupported data type '{ddl}'.")


def _decode(b: dict, fam: str, col: str):
    t, v = b.get("type"), b.get("value")
    if v is None:
        return None
    if not isinstance(v, str):
        raise SqlErr("100132", "Bind variable values must be strings.", "22000")
    ok = {"TEXT": {"TEXT"}, "NUMBER": {"FIXED", "TEXT"}, "FLOAT": {"REAL", "FIXED"}, "BOOLEAN": {"BOOLEAN"},
          "DATE": {"DATE"}, "TIMESTAMP_TZ": {"TIMESTAMP_TZ"}, "TIMESTAMP_NTZ": {"TIMESTAMP_NTZ"}}[fam]
    if t not in ok:
        raise SqlErr("002023", f"SQL compilation error: Expression type does not match column data type, expecting {fam} "
                               f"but got {t} for column {col}")
    try:
        if fam == "TEXT":
            return v
        if fam == "NUMBER":
            d = Decimal(v)
            if not d.is_finite() or (t == "FIXED" and d != d.to_integral_value()):
                raise ValueError
            return d
        if fam == "FLOAT":
            return float(v)
        if fam == "BOOLEAN":
            return {"true": True, "1": True, "false": False, "0": False}[v.lower()]
        if fam == "DATE":
            return datetime.fromtimestamp(int(v) / 1000, timezone.utc).date()
        if fam == "TIMESTAMP_TZ":
            ns, off = v.split(" ")
            tz = timezone(timedelta(minutes=int(off) - 1440))
            return datetime.fromtimestamp(int(ns) // 1_000_000_000, tz).replace(microsecond=(int(ns) % 1_000_000_000) // 1000)
        return datetime.fromtimestamp(int(v) // 1_000_000_000, timezone.utc).replace(tzinfo=None, microsecond=(int(v) % 1_000_000_000) // 1000)
    except (ValueError, KeyError, InvalidOperation):
        raise SqlErr("100038", f"Numeric value '{v[:40]}' is not recognized" if fam in ("NUMBER", "FLOAT")
                     else f"Value '{v[:40]}' is not a valid {fam} for column {col}", "22018") from None


def _show(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def _gerr(code: int, status: str, reason: str, msg: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": msg, "errors": [{"message": msg, "domain": "global", "reason": reason}],
                                   "status": status}}, code)


BQ_TYPES = {"STRING", "INTEGER", "FLOAT", "NUMERIC", "BIGNUMERIC", "BOOLEAN", "DATE", "TIMESTAMP", "DATETIME"}


def _bq_value(typ: str, v, name: str):
    if v is None:
        return None
    try:
        if typ == "STRING":
            if not isinstance(v, str):
                raise ValueError
            return v
        if typ == "INTEGER":
            if isinstance(v, bool) or (isinstance(v, float) and not v.is_integer()):
                raise ValueError
            return int(v)
        if typ == "FLOAT":
            return float(v)
        if typ in ("NUMERIC", "BIGNUMERIC"):
            d = Decimal(str(v))
            if not d.is_finite():
                raise ValueError
            return d
        if typ == "BOOLEAN":
            if isinstance(v, bool):
                return v
            return {"true": True, "false": False}[str(v).lower()]
        if typ == "DATE":
            return date.fromisoformat(v)
        if typ == "TIMESTAMP":
            d = datetime.fromisoformat(v)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        if typ == "DATETIME":
            d = datetime.fromisoformat(v)
            if d.tzinfo:
                raise ValueError
            return d
    except (ValueError, KeyError, InvalidOperation, TypeError):
        pass
    raise ValueError(f"Could not convert value '{str(v)[:40]}' to {typ}. Field: {name}")


def create_warehouse_app() -> FastAPI:
    app = FastAPI(title="POVU warehouse simulator (synthetic, local only)")
    demo = new_key()
    st: dict = {}

    def reset():
        st.clear()
        st.update(faults={"sf": [], "bq": []}, sf_async=0, bq_async=0, calls=[],
                  sf_keys={f"{SF_ACCOUNT}.{SF_USER}": pub_pem(demo)}, bq_keys={BQ_EMAIL: pub_pem(demo)},
                  sf_schemas=set(), sf_tables={}, sf_req={}, sf_handles={}, sf_exec=[],
                  bq_tokens=set(), bq_datasets={}, bq_tables={}, bq_jobs={}, bq_req={}, bq_exec=[])
    reset()

    def take_fault(svc: str, text: str):
        for i, f in enumerate(st["faults"][svc]):
            kind, match = (f, "") if not isinstance(f, dict) else (f["kind"], f.get("match", ""))
            if match in text:
                st["faults"][svc].pop(i)
                return kind
        return None

    # ── control ─────────────────────────────────────────────────────────────
    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        for k, v in (b.get("faults") or {}).items():
            st["faults"][k].extend(v)
        for k in ("sf_async", "bq_async"):
            if k in b:
                st[k] = int(b[k])
        st["sf_keys"].update(b.get("sf_keys") or {})
        st["bq_keys"].update(b.get("bq_keys") or {})
        return {"ok": True}

    @app.post("/_control/reset")
    async def control_reset():
        reset()
        return {"ok": True}

    @app.get("/_control/state")
    async def control_state():
        return {"sf_tables": {k: {"cols": t["cols"], "rows": [{c: _show(v) for c, v in r.items()} for r in t["rows"]]}
                              for k, t in st["sf_tables"].items()},
                "bq_tables": {k: {"schema": t["schema"], "rows": [{c: _show(v) for c, v in r.items()} for r in t["rows"]]}
                              for k, t in st["bq_tables"].items()},
                "sf_exec": st["sf_exec"], "bq_exec": st["bq_exec"], "calls": st["calls"], "bq_datasets": sorted(st["bq_datasets"])}

    @app.get("/_control/demo-credentials")
    async def demo_credentials():
        """Synthetic credentials accepted by this simulator only (for the manual connection-wizard walkthrough)."""
        sa = {"type": "service_account", "project_id": BQ_PROJECT, "private_key_id": "sim-key-1", "private_key": pem(demo),
              "client_email": BQ_EMAIL, "token_uri": "http://127.0.0.1/oauth2/token"}
        return {"snowflake": {"account": SF_ACCOUNT, "user": SF_USER, "private_key": pem(demo)}, "bigquery": sa}

    # ── Snowflake ───────────────────────────────────────────────────────────
    def sf_auth(request: Request) -> Optional[JSONResponse]:
        bad = JSONResponse({"code": "390144", "message": "JWT token is invalid."}, 401)
        ttype = request.headers.get("X-Snowflake-Authorization-Token-Type")
        tok = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if ttype not in (None, "KEYPAIR_JWT") or not tok:
            return bad
        try:
            claims = jwt.decode(tok, options={"verify_signature": False})
            acct_user, _, fp = claims["iss"].rpartition(".SHA256:")
            pub = st["sf_keys"].get(acct_user)
            if pub is None:
                return bad
            key = serialization.load_pem_public_key(pub.encode())
            der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            if fp != base64.b64encode(hashlib.sha256(der).digest()).decode() or claims["sub"] != acct_user:
                return bad
            c = jwt.decode(tok, pub, algorithms=["RS256"])
            if c["exp"] - c["iat"] > 3600:
                return bad
        except Exception:
            return bad
        return None

    def sf_ok(rid: str, rows: list, names: list[str], handle: str, extra: Optional[dict] = None) -> dict:
        return {"resultSetMetaData": {"numRows": len(rows), "format": "jsonv2",
                                      "rowType": [{"name": n, "type": "text", "nullable": True} for n in names],
                                      "partitionInfo": [{"rowCount": len(rows)}]},
                "data": rows, "code": "090001", "statementStatusUrl": f"/api/v2/statements/{handle}", "requestId": rid,
                "sqlState": "00000", "statementHandle": handle, "message": "Statement executed successfully.",
                "createdOn": int(time.time() * 1000), **(extra or {})}

    def table(key: str) -> dict:
        t = st["sf_tables"].get(key)
        if t is None:
            raise SqlErr("002003", f"SQL compilation error: Object '{key}' does not exist or not authorized.", "02000")
        return t

    def run_one(sql: str, binds: dict, body: dict) -> tuple[list, list[str], dict]:
        if m := re.fullmatch(r"SELECT CURRENT_ROLE\(\), CURRENT_WAREHOUSE\(\), CURRENT_DATABASE\(\)", sql):
            return [[body.get("role"), body.get("warehouse"), body.get("database")]], ["CURRENT_ROLE()", "CURRENT_WAREHOUSE()", "CURRENT_DATABASE()"], {}
        if m := re.fullmatch(rf"CREATE SCHEMA IF NOT EXISTS {Q}\.{Q}", sql):
            st["sf_schemas"].add(f"{m[1]}.{m[2]}")
            return [["Statement executed successfully."]], ["status"], {}
        if m := re.fullmatch(rf"CREATE (TABLE IF NOT EXISTS|TRANSIENT TABLE) {FQ} \((.*)\)( DATA_RETENTION_TIME_IN_DAYS = 0)?", sql):
            if f"{m[2]}.{m[3]}" not in st["sf_schemas"]:
                raise SqlErr("002003", f"SQL compilation error: Schema '{m[2]}.{m[3]}' does not exist or not authorized.", "02000")
            key = f"{m[2]}.{m[3]}.{m[4]}"
            if key in st["sf_tables"]:
                if m[1] == "TRANSIENT TABLE":
                    raise SqlErr("002002", f"SQL compilation error: Object '{key}' already exists.")
            else:
                defs = re.findall(rf"{Q} {TYPE}", m[5])
                st["sf_tables"][key] = {"cols": {n: _fam(t) for n, t in defs}, "rows": []}
            return [["Table successfully created."]], ["status"], {}
        if m := re.fullmatch(rf"SELECT COLUMN_NAME, DATA_TYPE FROM {Q}\.INFORMATION_SCHEMA\.COLUMNS WHERE TABLE_SCHEMA = \? AND TABLE_NAME = \?", sql):
            t = st["sf_tables"].get(f"{m[1]}.{_decode(binds['1'], 'TEXT', 's')}.{_decode(binds['2'], 'TEXT', 't')}")
            return [[n, f] for n, f in (t["cols"].items() if t else [])], ["COLUMN_NAME", "DATA_TYPE"], {}
        if m := re.fullmatch(rf"ALTER TABLE {FQ} ADD COLUMN IF NOT EXISTS {Q} {TYPE}", sql):
            t = table(f"{m[1]}.{m[2]}.{m[3]}")
            t["cols"].setdefault(m[4], _fam(m[5]))
            return [["Statement executed successfully."]], ["status"], {}
        if m := re.fullmatch(rf"INSERT INTO {FQ} \(([^)]*)\) VALUES ((?:\((?:\?, )*\?\)(?:, )?)+)", sql):
            t = table(f"{m[1]}.{m[2]}.{m[3]}")
            cols = re.findall(Q, m[4])
            n = m[5].count("?")
            if n != len(binds) or n % len(cols):
                raise SqlErr("002049", f"SQL compilation error: wrong number of bind values ({len(binds)} for {n}).")
            for c in cols:
                if c not in t["cols"]:
                    raise SqlErr("000904", f"SQL compilation error: invalid identifier '{c}'")
            new = []
            for i in range(n // len(cols)):
                new.append({c: _decode(binds[str(i * len(cols) + j + 1)], t["cols"][c], c) for j, c in enumerate(cols)})
            t["rows"].extend(new)
            return [[str(len(new))]], ["number of rows inserted"], {"stats": {"numRowsInserted": len(new)}}
        if m := re.fullmatch(rf"MERGE INTO {FQ} t USING {FQ} s ON t\.{Q} = s\.{Q} WHEN MATCHED THEN UPDATE SET (.*) "
                             rf"WHEN NOT MATCHED THEN INSERT \((.*)\) VALUES \((.*)\)", sql):
            tgt, src = table(f"{m[1]}.{m[2]}.{m[3]}"), table(f"{m[4]}.{m[5]}.{m[6]}")
            tk, sk = m[7], m[8]
            sets = re.findall(rf"t\.{Q} = (?:s\.{Q}|(CURRENT_TIMESTAMP\(\)))", m[9])
            icols, ivals = re.findall(Q, m[10]), re.findall(rf"s\.{Q}|(CURRENT_TIMESTAMP\(\))", m[11])
            if len(icols) != len(ivals) or not sets:
                raise SqlErr("001003", "SQL compilation error: MERGE column list mismatch.")
            for c in [s[0] for s in sets] + icols:
                if c not in tgt["cols"]:
                    raise SqlErr("000904", f"SQL compilation error: invalid identifier '{c}'")
            now = datetime.now(timezone.utc)
            index = {r.get(tk): r for r in tgt["rows"]}
            ins = upd = 0
            seen = set()
            for s in src["rows"]:
                if s.get(sk) in seen:
                    raise SqlErr("100090", "Duplicate row detected during DML action", "42P18")
                seen.add(s.get(sk))
                hit = index.get(s.get(sk))
                if hit is not None:
                    for col, scol, ts in sets:
                        hit[col] = now if ts else s.get(scol)
                    upd += 1
                else:
                    row = {c: (now if v[1] else s.get(v[0])) for c, v in zip(icols, ivals)}
                    tgt["rows"].append(row)
                    index[row.get(tk)] = row
                    ins += 1
            return [[str(ins), str(upd)]], ["number of rows inserted", "number of rows updated"], {
                "stats": {"numRowsInserted": ins, "numRowsUpdated": upd}}
        if m := re.fullmatch(rf"DELETE FROM {FQ} WHERE {Q} IN \(((?:\?, )*\?)\)", sql):
            t = table(f"{m[1]}.{m[2]}.{m[3]}")
            if m[5].count("?") != len(binds):
                raise SqlErr("002049", "SQL compilation error: wrong number of bind values.")
            ids = {_decode(b, t["cols"][m[4]], m[4]) for b in binds.values()}
            before = len(t["rows"])
            t["rows"] = [r for r in t["rows"] if r.get(m[4]) not in ids]
            return [[str(before - len(t["rows"]))]], ["number of rows deleted"], {"stats": {"numRowsDeleted": before - len(t["rows"])}}
        if m := re.fullmatch(rf"DROP TABLE IF EXISTS {FQ}", sql):
            st["sf_tables"].pop(f"{m[1]}.{m[2]}.{m[3]}", None)
            return [["successfully dropped."]], ["status"], {}
        raise SqlErr("001003", "SQL compilation error: syntax error (statement shape not understood by the simulator).")

    def sf_execute(body: dict, rid: str, fail: bool = False) -> tuple[int, dict]:
        stmt, binds = body.get("statement") or "", body.get("bindings") or {}
        parts = [s.strip() for s in stmt.split(";") if s.strip()]
        handle = secrets.token_hex(4) + "-0000-0000-0000-" + secrets.token_hex(6)
        want = (body.get("parameters") or {}).get("MULTI_STATEMENT_COUNT")
        try:
            if fail:
                raise SqlErr("100035", "Simulated failure while executing the statement.", "57014")
            if len(parts) > 1 or want not in (None, "1"):
                if want is None or (want != "0" and int(want) != len(parts)):
                    raise SqlErr("000008", f"Actual statement count {len(parts)} did not match the desired statement count {want or 1}.", "0A000")
                if binds:
                    raise SqlErr("000002", "Unsupported feature: variable binding in multi-statement SQL requests.", "0A000")
                snapshot, handles, txn = None, [], False
                try:
                    for p in parts:
                        if p == "BEGIN TRANSACTION":
                            snapshot, txn = copy.deepcopy(st["sf_tables"]), True
                        elif p == "COMMIT":
                            txn = False
                        else:
                            run_one(p, {}, body)
                            st["sf_exec"].append(p)
                        handles.append(secrets.token_hex(8))
                except SqlErr:
                    if txn and snapshot is not None:       # the request's session ends: open transaction rolls back
                        st["sf_tables"] = snapshot
                    raise
                return 200, sf_ok(rid, [["Multiple statements executed successfully."]], ["multiple statement execution"],
                                  handle, {"statementHandles": handles})
            rows, names, extra = run_one(parts[0] if parts else "", binds, body)
            st["sf_exec"].append(parts[0])
            return 200, sf_ok(rid, rows, names, handle, extra)
        except SqlErr as e:
            return 422, {"code": e.code, "message": e.msg, "sqlState": e.state, "statementHandle": handle, "requestId": rid}

    @app.post("/snowflake/api/v2/statements")
    async def sf_submit(request: Request):
        body = await request.json()
        st["calls"].append({"svc": "sf", "method": "POST", "path": request.url.path, "query": dict(request.query_params),
                            "token_type": request.headers.get("X-Snowflake-Authorization-Token-Type"),
                            "auth": request.headers.get("Authorization", "")[:7], "body": body})
        if (bad := sf_auth(request)) is not None:
            return bad
        rid = request.query_params.get("requestId", "")
        if rid and request.query_params.get("retry") == "true" and rid in st["sf_req"]:
            code, out = st["sf_req"][rid]
            return JSONResponse(out, code)                   # already executed: not run twice
        f = take_fault("sf", body.get("statement") or "")
        if f in (429, "429"):
            return JSONResponse({"code": "390505", "message": "Too many requests."}, 429, headers={"Retry-After": "1"})
        if f in (503, "503"):
            return Response(status_code=503)
        code, out = sf_execute(body, rid, fail=f == "fail")
        st["sf_req"][rid] = (code, out)
        if f == "lost":
            return Response(status_code=503)                 # executed, but the client never sees the answer
        if st["sf_async"] and code in (200, 422):
            st["sf_handles"][out["statementHandle"]] = {"polls": st["sf_async"], "code": code, "out": out}
            return JSONResponse({"code": "333334", "sqlState": "01000", "statementHandle": out["statementHandle"],
                                 "statementStatusUrl": f"/api/v2/statements/{out['statementHandle']}",
                                 "message": "Asynchronous execution in progress. Use provided query id to perform query monitoring and management."}, 202)
        return JSONResponse(out, code)

    @app.get("/snowflake/api/v2/statements/{handle}")
    async def sf_status(handle: str, request: Request):
        if (bad := sf_auth(request)) is not None:
            return bad
        h = st["sf_handles"].get(handle)
        if h is None:
            return JSONResponse({"code": "333333", "message": f"Statement handle {handle} not found."}, 404)
        if h["polls"] > 0:
            h["polls"] -= 1
            return JSONResponse({"code": "333334", "statementHandle": handle, "statementStatusUrl": f"/api/v2/statements/{handle}",
                                 "message": "Asynchronous execution in progress."}, 202)
        return JSONResponse(h["out"], h["code"])

    # ── Google token endpoint ───────────────────────────────────────────────
    @app.post("/oauth2/token")
    async def token(request: Request):
        form = dict(await request.form())
        st["calls"].append({"svc": "token", "method": "POST", "path": request.url.path, "form": {k: v for k, v in form.items() if k != "assertion"},
                            "assertion": form.get("assertion", "")})
        if form.get("grant_type") != "urn:ietf:params:oauth:grant-type:jwt-bearer":
            return JSONResponse({"error": "unsupported_grant_type"}, 400)
        try:
            a = form.get("assertion", "")
            iss = jwt.decode(a, options={"verify_signature": False})["iss"]
            c = jwt.decode(a, st["bq_keys"][iss], algorithms=["RS256"], audience=str(request.url).split("?")[0])
            assert c["exp"] - c["iat"] <= 3600 and "https://www.googleapis.com/auth/bigquery" in c["scope"].split()
        except Exception:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid JWT Signature."}, 400)
        tok = "sim-bq-" + secrets.token_urlsafe(16)
        st["bq_tokens"].add(tok)
        return {"access_token": tok, "expires_in": 3599, "token_type": "Bearer"}

    # ── BigQuery ────────────────────────────────────────────────────────────
    async def bq_gate(request: Request) -> Optional[Response]:
        body = (await request.body())[:4000]
        st["calls"].append({"svc": "bq", "method": request.method, "path": request.url.path, "query": dict(request.query_params),
                            "body": body.decode("utf-8", "replace")})
        if request.headers.get("Authorization", "").removeprefix("Bearer ").strip() not in st["bq_tokens"]:
            return _gerr(401, "UNAUTHENTICATED", "authError", "Request had invalid authentication credentials.")
        f = take_fault("bq", f"{request.method} {request.url.path}")
        if f in (429, "429"):
            return _gerr(429, "RESOURCE_EXHAUSTED", "rateLimitExceeded", "Exceeded rate limits.")
        if f in (503, "503"):
            return _gerr(503, "UNAVAILABLE", "backendError", "Backend error. Job aborted.")
        if f is not None:
            st["faults"]["bq"].insert(0, {"kind": f, "match": ""})   # job-level fault: keep for the job
        return None

    def job_resource(p: str, jid: str, loc: str, cfg: dict, err: Optional[dict], stats: dict) -> dict:
        return {"kind": "bigquery#job", "id": f"{p}:{loc}.{jid}", "jobReference": {"projectId": p, "jobId": jid, "location": loc},
                "configuration": cfg, "status": {"state": "DONE", **({"errorResult": err, "errors": [err]} if err else {})},
                "statistics": stats}

    def add_job(p: str, jid: str, res: dict):
        st["bq_jobs"][jid] = {"polls": st["bq_async"], "res": res}

    @app.get("/bq/bigquery/v2/projects/{p}/datasets/{d}")
    async def ds_get(p: str, d: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        ds = st["bq_datasets"].get(f"{p}.{d}")
        return ds if ds else _gerr(404, "NOT_FOUND", "notFound", f"Not found: Dataset {p}:{d}")

    @app.post("/bq/bigquery/v2/projects/{p}/datasets")
    async def ds_insert(p: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        b = await request.json()
        d = b["datasetReference"]["datasetId"]
        if f"{p}.{d}" in st["bq_datasets"]:
            return _gerr(409, "ALREADY_EXISTS", "duplicate", f"Already Exists: Dataset {p}:{d}")
        st["bq_datasets"][f"{p}.{d}"] = {"kind": "bigquery#dataset", "id": f"{p}:{d}", "datasetReference": b["datasetReference"],
                                         "location": b.get("location", "US")}
        return st["bq_datasets"][f"{p}.{d}"]

    def tbl_res(p, d, t):
        x = st["bq_tables"][f"{p}.{d}.{t}"]
        return {"kind": "bigquery#table", "id": f"{p}:{d}.{t}", "tableReference": {"projectId": p, "datasetId": d, "tableId": t},
                "schema": {"fields": x["schema"]}, "numRows": str(len(x["rows"]))}

    @app.get("/bq/bigquery/v2/projects/{p}/datasets/{d}/tables/{t}")
    async def tbl_get(p: str, d: str, t: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        if f"{p}.{d}.{t}" not in st["bq_tables"]:
            return _gerr(404, "NOT_FOUND", "notFound", f"Not found: Table {p}:{d}.{t}")
        return tbl_res(p, d, t)

    def bad_fields(fields) -> Optional[str]:
        for f in fields:
            if f.get("type") not in BQ_TYPES or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,299}", f.get("name", "")):
                return f"Invalid field {f.get('name')!r} of type {f.get('type')!r}"
        return None

    @app.post("/bq/bigquery/v2/projects/{p}/datasets/{d}/tables")
    async def tbl_insert(p: str, d: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        b = await request.json()
        t = b["tableReference"]["tableId"]
        if f"{p}.{d}" not in st["bq_datasets"]:
            return _gerr(404, "NOT_FOUND", "notFound", f"Not found: Dataset {p}:{d}")
        if f"{p}.{d}.{t}" in st["bq_tables"]:
            return _gerr(409, "ALREADY_EXISTS", "duplicate", f"Already Exists: Table {p}:{d}.{t}")
        if (why := bad_fields(b["schema"]["fields"])):
            return _gerr(400, "INVALID_ARGUMENT", "invalid", why)
        st["bq_tables"][f"{p}.{d}.{t}"] = {"schema": b["schema"]["fields"], "rows": [], "expirationTime": b.get("expirationTime")}
        return tbl_res(p, d, t)

    @app.patch("/bq/bigquery/v2/projects/{p}/datasets/{d}/tables/{t}")
    async def tbl_patch(p: str, d: str, t: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        x = st["bq_tables"].get(f"{p}.{d}.{t}")
        if x is None:
            return _gerr(404, "NOT_FOUND", "notFound", f"Not found: Table {p}:{d}.{t}")
        new = {f["name"]: f for f in (await request.json())["schema"]["fields"]}
        for f in x["schema"]:
            n = new.get(f["name"])
            if n is None:
                return _gerr(400, "INVALID_ARGUMENT", "invalid", f"Provided Schema does not match Table {p}:{d}.{t}. Cannot add fields (field: {f['name']} missing)")
            if n["type"] != f["type"]:
                return _gerr(400, "INVALID_ARGUMENT", "invalid", f"Provided Schema does not match Table {p}:{d}.{t}. "
                                                                 f"Field {f['name']} has changed type from {f['type']} to {n['type']}")
        old = {f["name"] for f in x["schema"]}
        if (why := bad_fields(new.values())) or any(new[k].get("mode", "NULLABLE") == "REQUIRED" for k in new if k not in old):
            return _gerr(400, "INVALID_ARGUMENT", "invalid", why or "New fields must be NULLABLE or REPEATED.")
        x["schema"] = list(new.values())
        return tbl_res(p, d, t)

    @app.delete("/bq/bigquery/v2/projects/{p}/datasets/{d}/tables/{t}")
    async def tbl_delete(p: str, d: str, t: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        if st["bq_tables"].pop(f"{p}.{d}.{t}", None) is None:
            return _gerr(404, "NOT_FOUND", "notFound", f"Not found: Table {p}:{d}.{t}")
        return Response(status_code=204)

    @app.post("/bq/upload/bigquery/v2/projects/{p}/jobs")
    async def load_insert(p: str, request: Request):
        if request.query_params.get("uploadType") != "multipart":
            return _gerr(400, "INVALID_ARGUMENT", "invalid", "uploadType must be multipart here.")
        if (g := await bq_gate(request)) is not None:
            return g
        ctype = request.headers.get("content-type", "")
        if not ctype.startswith("multipart/related"):
            return _gerr(400, "INVALID_ARGUMENT", "invalid", "Expected multipart/related.")
        msg = message_from_bytes(f"Content-Type: {ctype}\r\n\r\n".encode() + await request.body())
        parts = msg.get_payload()
        if not isinstance(parts, list) or len(parts) != 2 or not parts[0].get_content_type().startswith("application/json"):
            return _gerr(400, "INVALID_ARGUMENT", "invalid", "Metadata part must come first, media second.")
        meta = json.loads(parts[0].get_payload(decode=True))
        data = parts[1].get_payload(decode=True) or b""
        jid, loc = meta["jobReference"]["jobId"], meta["jobReference"].get("location", "US")
        if jid in st["bq_jobs"]:
            return _gerr(409, "ALREADY_EXISTS", "duplicate", f"Already Exists: Job {p}:{loc}.{jid}")
        load = meta["configuration"]["load"]
        dest = load["destinationTable"]
        key = f"{dest['projectId']}.{dest['datasetId']}.{dest['tableId']}"
        err, n = None, 0
        kind = take_fault("bq", "JOB " + key)
        if kind == "jobfail":
            err = {"reason": "invalid", "message": "Error while reading data, error message: simulated load failure", "location": "data"}
        elif load.get("sourceFormat") != "NEWLINE_DELIMITED_JSON":
            err = {"reason": "invalid", "message": "Unsupported sourceFormat for the simulator."}
        elif key not in st["bq_tables"]:
            err = {"reason": "notFound", "message": f"Not found: Table {key.replace('.', ':', 1)}"}
        else:
            x = st["bq_tables"][key]
            types = {f["name"]: f["type"] for f in x["schema"]}
            try:
                rows = []
                for i, line in enumerate(data.decode().splitlines()):
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    for k in obj:
                        if k not in types:
                            raise ValueError(f"JSON table encountered too many errors. Row {i}: No such field: {k}.")
                    rows.append({k: _bq_value(types[k], obj.get(k), k) for k in types})
                x["rows"] = rows if load.get("writeDisposition") == "WRITE_TRUNCATE" else x["rows"] + rows
                n = len(rows)
                st["bq_exec"].append(f"LOAD {key} {n}")
            except ValueError as e:
                err = {"reason": "invalid", "message": f"Error while reading data, error message: {e}"}
        res = job_resource(p, jid, loc, meta["configuration"], err, {"load": {"outputRows": str(n)}})
        add_job(p, jid, res)
        if kind == "lost":
            return Response(status_code=503)                 # job created, but the client never sees the answer
        return {**res, "status": {"state": "RUNNING"}} if st["bq_async"] else res

    @app.get("/bq/bigquery/v2/projects/{p}/jobs/{jid}")
    async def job_get(p: str, jid: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        j = st["bq_jobs"].get(jid)
        if j is None:
            return _gerr(404, "NOT_FOUND", "notFound", f"Not found: Job {p}:{jid}")
        if j["polls"] > 0:
            j["polls"] -= 1
            return {**j["res"], "status": {"state": "RUNNING"}}
        return j["res"]

    def bq_est(*keys) -> int:
        return sum(len(json.dumps([{c: _show(v) for c, v in r.items()} for r in st["bq_tables"].get(k, {"rows": []})["rows"]]))
                   for k in keys)

    def run_query(q: str, params: list) -> tuple[list, int]:
        if m := re.fullmatch(r"MERGE `([^`]+)` T USING `([^`]+)` S ON T\.`(\w+)` = S\.`(\w+)` WHEN MATCHED THEN UPDATE SET (.*) "
                             r"WHEN NOT MATCHED THEN INSERT \((.*)\) VALUES \((.*)\)", q):
            for k in (m[1], m[2]):
                if k not in st["bq_tables"]:
                    raise SqlErr("notFound", f"Not found: Table {k}")
            tgt, src = st["bq_tables"][m[1]], st["bq_tables"][m[2]]
            names = {f["name"] for f in tgt["schema"]}
            sets = re.findall(r"`(\w+)` = (?:S\.`(\w+)`|(CURRENT_TIMESTAMP\(\)))", m[5])
            icols = re.findall(r"`(\w+)`", m[6])
            ivals = re.findall(r"S\.`(\w+)`|(CURRENT_TIMESTAMP\(\))", m[7])
            if len(icols) != len(ivals) or any(c not in names for c in [s[0] for s in sets] + icols):
                raise SqlErr("invalidQuery", "Unrecognized name in MERGE column list")
            now, idx, hit_once, n = datetime.now(timezone.utc), {r.get(m[3]): r for r in tgt["rows"]}, set(), 0
            for s in src["rows"]:
                r = idx.get(s.get(m[4]))
                if r is not None:
                    if id(r) in hit_once:
                        raise SqlErr("invalidQuery", "UPDATE/MERGE must match at most one source row for each target row")
                    hit_once.add(id(r))
                    for col, scol, ts in sets:
                        r[col] = now if ts else s.get(scol)
                else:
                    row = {c: (now if v[1] else s.get(v[0])) for c, v in zip(icols, ivals)}
                    tgt["rows"].append(row)
                    idx[row.get(m[3])] = row
                n += 1
            return [m[1], m[2]], n
        if m := re.fullmatch(r"DELETE FROM `([^`]+)` WHERE `(\w+)` IN UNNEST\(@(\w+)\)", q):
            if m[1] not in st["bq_tables"]:
                raise SqlErr("notFound", f"Not found: Table {m[1]}")
            x = st["bq_tables"][m[1]]
            par = next((p for p in params if p["name"] == m[3]), None)
            if par is None:
                raise SqlErr("invalidQuery", f"Query parameter '{m[3]}' not found")
            col_t = {f["name"]: f["type"] for f in x["schema"]}[m[2]]
            arr_t = par["parameterType"]["arrayType"]["type"].replace("INT64", "INTEGER")
            if arr_t != col_t:
                raise SqlErr("invalidQuery", f"Cannot execute IN with values of types {col_t} and ARRAY<{arr_t}>")
            vals = {_bq_value(col_t, v["value"], m[2]) for v in par["parameterValue"]["arrayValues"]}
            before = len(x["rows"])
            x["rows"] = [r for r in x["rows"] if r.get(m[2]) not in vals]
            return [m[1]], before - len(x["rows"])
        raise SqlErr("invalidQuery", "Syntax error: statement shape not understood by the simulator")

    @app.post("/bq/bigquery/v2/projects/{p}/queries")
    async def jobs_query(p: str, request: Request):
        if (g := await bq_gate(request)) is not None:
            return g
        b = await request.json()
        if b.get("useLegacySql") is not False:
            return _gerr(400, "INVALID_ARGUMENT", "invalidQuery", "MERGE/DELETE need GoogleSQL: set useLegacySql=false.")
        q, loc = b.get("query", ""), b.get("location", "US")
        keys = re.findall(r"`([^`]+\.[^`]+\.[^`]+)`", q)
        est = bq_est(*keys)
        if b.get("dryRun"):
            return {"kind": "bigquery#queryResponse", "jobReference": {"projectId": p, "location": loc},
                    "totalBytesProcessed": str(est), "jobComplete": True, "cacheHit": False}
        rid = b.get("requestId")
        if rid and rid in st["bq_req"]:
            return st["bq_req"][rid]                          # idempotent duplicate: same job, not run again
        if b.get("maximumBytesBilled") and est > int(b["maximumBytesBilled"]):
            return _gerr(400, "INVALID_ARGUMENT", "bytesBilledLimitExceeded",
                         f"Query exceeded limit for bytes billed: {b['maximumBytesBilled']}. {est} or higher required.")
        jid = "job_" + secrets.token_hex(10)
        err, n = None, 0
        if take_fault("bq", "JOB " + q) in ("jobfail", "fail"):
            err = {"reason": "invalidQuery", "message": "Simulated query failure."}
        else:
            snapshot = copy.deepcopy(st["bq_tables"])
            try:
                _, n = run_query(q, b.get("queryParameters") or [])
                st["bq_exec"].append(q.split(" ")[0] + f" {n}")
            except (SqlErr, ValueError) as e:
                st["bq_tables"] = snapshot                   # a DML statement is atomic
                err = {"reason": getattr(e, "code", "invalidQuery"), "message": str(e)}
        stats = {"query": {"totalBytesProcessed": str(est), "numDmlAffectedRows": str(n)}}
        add_job(p, jid, job_resource(p, jid, loc, {"query": {"query": q}}, err, stats))
        if st["bq_async"]:
            out = {"kind": "bigquery#queryResponse", "jobReference": {"projectId": p, "jobId": jid, "location": loc}, "jobComplete": False}
        elif err:
            return _gerr(400, "INVALID_ARGUMENT", err["reason"], err["message"])
        else:
            out = {"kind": "bigquery#queryResponse", "jobReference": {"projectId": p, "jobId": jid, "location": loc}, "jobComplete": True,
                   "totalBytesProcessed": str(est), "numDmlAffectedRows": str(n), "dmlStats": {"updatedRowCount": str(n)}}
        if rid:
            st["bq_req"][rid] = out
        return out

    return app
