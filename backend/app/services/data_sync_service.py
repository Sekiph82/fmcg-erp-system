"""M45.S01.T011 no-code data sync and transformation.

A sync maps source fields to ERP fields with typed, whitelisted transformations (no code, no SQL, no regex from
users). IN syncs read an uploaded CSV/JSON, a JSON endpoint (through provider_http egress) or a webhook body; OUT
syncs send changed ERP rows to a JSON endpoint. Every run can be a dry run (diff only). Conflicts follow the sync's
rule (source wins / target wins / skip), unchanged source rows are skipped by hash (incremental), keys that vanished
from a full source are deletes (ignored or deactivated), failed HTTP pulls/pushes are retried, any finished run can be
rolled back from its before-images, and a run's input can be replayed. Mapping changes create a new version.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.data_sync import DataQualitySnapshot, SyncDefinition, SyncRun, SyncState

TARGETS: dict[str, dict] = {
    "customers": {"model": ("app.models.sales", "Customer"), "key": "code", "perm": ("sales.edit", "sales.create"),
                  "fields": {"code": "text", "name": "text", "email": "email", "phone": "phone", "city": "text", "country": "text",
                             "region": "text", "segment": "text", "address": "text", "tax_id": "text", "currency": "text",
                             "payment_terms_days": "integer", "credit_limit": "number", "is_active": "bool"},
                  "required": ["code", "name"], "defaults": {"currency": "KES"}},
    "crm_contacts": {"model": ("app.models.crm", "CRMContact"), "key": "email", "perm": ("crm.edit", "crm.edit_all"),
                     "fields": {"email": "email", "full_name": "text", "phone": "phone", "job_title": "text", "language": "text"},
                     "required": ["email", "full_name"], "defaults": {}},
}
CONTROLLED_FIELDS = {"credit_limit", "payment_terms_days", "tax_id", "is_active"}   # commercial controls: admin-run syncs only
TRANSFORMS = {"trim", "upper", "lower", "title", "phone_ke", "email", "number", "integer", "bool", "date", "default", "map",
              "prefix", "suffix", "concat", "truncate"}
MAX_INPUT_KEEP = 5000


class SyncError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model(target: str):
    import importlib
    mod, cls = TARGETS[target]["model"]
    return getattr(importlib.import_module(mod), cls)


def _cipher():
    from cryptography.fernet import Fernet
    key = hashlib.sha256(b"fmcg-erp:data-sync:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().encrypt(v.encode()).decode() if v else None


def decrypt(v: Optional[str]) -> Optional[str]:
    return _cipher().decrypt(v.encode()).decode() if v else None


# ── mapping validation and transforms ────────────────────────────────────────

def validate_mapping(target: str, key_field: str, mapping: list[dict]) -> list[dict]:
    if target not in TARGETS:
        raise SyncError(422, f"Target must be one of {', '.join(TARGETS)}.")
    spec = TARGETS[target]
    if key_field != spec["key"]:
        raise SyncError(422, f"{target} are matched by {spec['key']}.")
    seen = set()
    for m in mapping:
        t = m.get("target")
        if t not in spec["fields"]:
            raise SyncError(422, f"Unknown target field {t!r}.")
        if t in seen:
            raise SyncError(422, f"{t} is mapped twice.")
        seen.add(t)
        if not m.get("source") and not any(str(x).startswith(("default:", "concat:")) for x in m.get("transforms", [])):
            raise SyncError(422, f"{t}: give a source field or a default.")
        for x in m.get("transforms", []):
            name = str(x).split(":", 1)[0]
            if name not in TRANSFORMS:
                raise SyncError(422, f"{t}: unknown transformation {name!r} (allowed: {', '.join(sorted(TRANSFORMS))}).")
            if name == "map":
                try:
                    json.loads(str(x).split(":", 1)[1])
                except (IndexError, ValueError):
                    raise SyncError(422, f"{t}: map needs JSON, e.g. map:{{\"A\":\"Wholesale\"}}.")
    for r in spec["required"]:
        if r not in seen:
            raise SyncError(422, f"{r} must be mapped.")
    return mapping


def transform(value: Any, ops: list[str], row: dict) -> Any:
    from app.services.customer_data_service import norm_email, norm_phone
    v = value
    for op in ops:
        name, _, arg = str(op).partition(":")
        if name == "default":
            v = v if v not in (None, "") else arg
        elif name == "concat":
            v = " ".join(str(row.get(f.strip()) or "").strip() for f in arg.split(",")).strip()
        elif v in (None, ""):
            continue
        elif name == "trim":
            v = re.sub(r"\s+", " ", str(v)).strip()
        elif name == "upper":
            v = str(v).upper()
        elif name == "lower":
            v = str(v).lower()
        elif name == "title":
            v = str(v).title()
        elif name == "phone_ke":
            v = norm_phone(str(v)) or v
        elif name == "email":
            v = norm_email(str(v)) or v
        elif name == "prefix":
            v = arg + str(v)
        elif name == "suffix":
            v = str(v) + arg
        elif name == "truncate":
            v = str(v)[: int(arg or 255)]
        elif name == "map":
            v = json.loads(arg).get(str(v), v)
        elif name == "number":
            try:
                v = Decimal(str(v).replace(",", ""))
            except InvalidOperation:
                raise ValueError(f"{value!r} is not a number")
        elif name == "integer":
            try:
                v = int(Decimal(str(v).replace(",", "")))
            except InvalidOperation:
                raise ValueError(f"{value!r} is not a whole number")
        elif name == "bool":
            v = str(v).strip().lower() in ("1", "true", "yes", "y", "active")
        elif name == "date":
            v = datetime.strptime(str(v), arg or "%Y-%m-%d").date()
    return v


def check_type(kind: str, v: Any) -> Any:
    from app.services.customer_data_service import norm_email, norm_phone
    if v in (None, ""):
        return None
    if kind == "email":
        e = norm_email(str(v))
        if not e:
            raise ValueError(f"{v!r} is not an e-mail address")
        return e
    if kind == "phone":
        p = norm_phone(str(v))
        if not p:
            raise ValueError(f"{v!r} is not a phone number")
        return p
    if kind == "integer":
        return int(v)
    if kind == "number":
        return Decimal(str(v))
    if kind == "bool":
        return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")
    return str(v)[:255]


def map_row(sync: SyncDefinition, row: dict) -> dict:
    spec = TARGETS[sync.target]
    out = {}
    for m in sync.mapping:
        v = transform(row.get(m.get("source")) if m.get("source") else None, m.get("transforms", []), row)
        out[m["target"]] = check_type(spec["fields"][m["target"]], v)
    for k, v in spec["defaults"].items():
        out.setdefault(k, v)
    for r in spec["required"]:
        if out.get(r) in (None, ""):
            raise ValueError(f"{r} is empty")
    return out


def parse_upload(text: str, fmt: str) -> list[dict]:
    if fmt == "json":
        data = json.loads(text)
        rows = data.get("rows", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise SyncError(422, "JSON must be a list of objects or {\"rows\": [...]}.")
        return [r for r in rows if isinstance(r, dict)]
    return list(csv.DictReader(io.StringIO(text)))


def _jsonable(v):
    if isinstance(v, Decimal):
        return str(v.normalize()) if v == v.to_integral() else str(v.normalize())
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return getattr(v, "value", v)


# ── IN run ───────────────────────────────────────────────────────────────────

async def run_in(db: AsyncSession, sync: SyncDefinition, rows: list[dict], *, dry_run: bool, user: str, trigger: str = "MANUAL",
                 full_snapshot: bool = True) -> SyncRun:
    await db.refresh(sync)                    # callers may hold an expired instance
    M = _model(sync.target)
    spec = TARGETS[sync.target]
    keycol = getattr(M, spec["key"])
    run = SyncRun(sync_id=sync.id, version=sync.version, dry_run=dry_run, trigger=trigger, run_by=user,
                  input=rows[:MAX_INPUT_KEEP])
    db.add(run)
    await db.flush()
    counts = {"create": 0, "update": 0, "unchanged": 0, "skip": 0, "error": 0, "delete": 0}
    diff, errors, before = [], [], []
    states = {s.key: s for s in (await db.execute(select(SyncState).where(SyncState.sync_id == sync.id))).scalars()}
    seen = set()
    for i, raw in enumerate(rows, start=1):
        try:
            vals = map_row(sync, raw)
        except (ValueError, TypeError) as e:
            counts["error"] += 1
            errors.append({"row": i, "error": str(e)})
            continue
        key = str(vals[spec["key"]])
        seen.add(key)
        h = hashlib.sha256(json.dumps(vals, sort_keys=True, default=str).encode()).hexdigest()
        if key in states and states[key].hash == h:
            counts["unchanged"] += 1
            continue
        obj = (await db.execute(select(M).where(keycol == vals[spec["key"]]).with_for_update())).scalar_one_or_none()
        if obj is None:
            counts["create"] += 1
            diff.append({"key": key, "action": "create", "values": {k: _jsonable(v) for k, v in vals.items()}})
            if not dry_run:
                obj = M(**vals)
                db.add(obj)
                await db.flush()
                before.append({"id": str(obj.id), "action": "create"})
        else:
            changes = {k: (_jsonable(getattr(obj, k)), _jsonable(v)) for k, v in vals.items() if _jsonable(getattr(obj, k)) != _jsonable(v)}
            if not changes:
                counts["unchanged"] += 1
            elif sync.conflict_rule == "skip" or (sync.conflict_rule == "target_wins" and key in states):
                counts["skip"] += 1
                diff.append({"key": key, "action": "skip", "changes": changes})
            else:
                if sync.conflict_rule == "target_wins":     # first contact: only fill empty ERP fields
                    changes = {k: c for k, c in changes.items() if c[0] in (None, "")}
                counts["update"] += 1
                diff.append({"key": key, "action": "update", "changes": changes})
                if not dry_run:
                    before.append({"id": str(obj.id), "action": "update", "values": {k: c[0] for k, c in changes.items()},
                                   "after": {k: c[1] for k, c in changes.items()}})
                    for k in changes:
                        setattr(obj, k, vals[k])
        if not dry_run:
            if key in states:
                states[key].hash = h
            else:
                states[key] = SyncState(sync_id=sync.id, key=key, hash=h)
                db.add(states[key])
    if full_snapshot:
        for key in sorted(set(states) - seen):
            counts["delete"] += 1
            diff.append({"key": key, "action": "delete" if sync.delete_mode == "deactivate" else "delete-ignored"})
            if not dry_run and sync.delete_mode == "deactivate" and hasattr(M, "is_active"):
                obj = (await db.execute(select(M).where(keycol == key))).scalar_one_or_none()
                if obj is not None and obj.is_active:
                    before.append({"id": str(obj.id), "action": "update", "values": {"is_active": True}})
                    obj.is_active = False
            if not dry_run:
                await db.delete(states[key])
    run.counts, run.diff, run.errors, run.before = counts, diff[:200], errors[:200], before
    run.status, run.finished_at = "DONE", _now()
    await db.flush()
    return run


async def rollback(db: AsyncSession, run: SyncRun, user: str) -> dict:
    """Undo a run: restore updated values, delete created rows (or deactivate them when other records use them)."""
    from sqlalchemy.exc import IntegrityError
    if run.dry_run or run.status != "DONE":
        raise SyncError(409, "Only a finished, real run can be rolled back.")
    sync = await db.get(SyncDefinition, run.sync_id)
    M = _model(sync.target)
    restored = removed = deactivated = 0
    for b in reversed(run.before):
        obj = await db.get(M, uuid.UUID(b["id"]))
        if obj is None:
            continue
        if b["action"] == "update":
            col = M.__table__.c
            now_vals = b.get("after") or {}
            if any(_jsonable(getattr(obj, k)) != v for k, v in now_vals.items()):
                continue                                   # changed again since this run: leave the newer value
            for k, v in b["values"].items():
                t = col[k].type
                setattr(obj, k, Decimal(v) if v is not None and t.__class__.__name__ == "Numeric" else v)
            restored += 1
        else:
            try:
                async with db.begin_nested():
                    await db.delete(obj)
                    await db.flush()
                removed += 1
            except IntegrityError:
                if hasattr(obj, "is_active"):
                    obj.is_active = False
                    deactivated += 1
    await db.execute(SyncState.__table__.delete().where(SyncState.sync_id == sync.id))   # next run compares afresh
    run.status = "ROLLED_BACK"
    return {"restored": restored, "removed": removed, "deactivated": deactivated}


# ── sources and OUT ──────────────────────────────────────────────────────────

async def pull(sync: SyncDefinition, attempts: int = 3) -> list[dict]:
    from app.core.provider_http import provider_client
    last = None
    for _ in range(attempts):
        try:
            async with provider_client() as c:
                r = await c.get(sync.source_url, headers={"Authorization": f"Bearer {decrypt(sync.secret)}"} if sync.secret else {})
            if r.status_code == 200:
                data = r.json()
                return data.get("rows", data) if isinstance(data, dict) else data
            last = f"HTTP {r.status_code}"
        except Exception as e:          # network errors: retried
            last = f"{type(e).__name__}: {e}"
    raise SyncError(502, f"Source not reachable after {attempts} attempts ({last}).")


async def run_out(db: AsyncSession, sync: SyncDefinition, *, dry_run: bool, user: str, attempts: int = 3) -> SyncRun:
    """Send rows changed since the watermark to the destination; the mapping reads ERP field `target` into `source`."""
    from app.core.provider_http import provider_client
    await db.refresh(sync)
    M = _model(sync.target)
    q = select(M).order_by(M.updated_at)
    if sync.watermark:
        q = q.where(M.updated_at > sync.watermark)
    objs = list((await db.execute(q.limit(1000))).scalars())
    payload = [{m["source"]: _jsonable(transform(getattr(o, m["target"]), m.get("transforms", []), {}))
                for m in sync.mapping if m.get("source")} for o in objs]
    run = SyncRun(sync_id=sync.id, version=sync.version, dry_run=dry_run, trigger="MANUAL", run_by=user, input=payload[:MAX_INPUT_KEEP],
                  counts={"sent": 0 if dry_run else len(payload)}, diff=payload[:200])
    db.add(run)
    if payload and not dry_run:
        last = None
        for n in range(1, attempts + 1):
            run.attempts = n
            try:
                async with provider_client() as c:
                    r = await c.post(sync.source_url, json={"rows": payload},
                                     headers={"Authorization": f"Bearer {decrypt(sync.secret)}"} if sync.secret else {})
                if r.status_code < 300:
                    last = None
                    break
                last = f"HTTP {r.status_code}"
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
        if last:
            run.status, run.errors, run.finished_at = "FAILED", [{"error": last}], _now()
            await db.flush()
            return run
        sync.watermark = objs[-1].updated_at
    run.status, run.finished_at = "DONE", _now()
    await db.flush()
    return run


# ── data quality ─────────────────────────────────────────────────────────────

async def quality(db: AsyncSession) -> dict:
    from app.models.crm import CRMContact
    from app.models.sales import Customer
    from app.services.customer_data_service import norm_email, norm_name, norm_phone
    out = {}
    for name, M, label in (("customers", Customer, "name"), ("crm_contacts", CRMContact, "full_name")):
        rows = (await db.execute(select(M.id, getattr(M, label), M.email, M.phone))).all()
        total = len(rows)
        miss_e = sum(1 for r in rows if not r[2])
        miss_p = sum(1 for r in rows if not r[3])
        bad_e = [str(r[2]) for r in rows if r[2] and not norm_email(r[2])]
        fmt = [{"id": str(r[0]), "field": "phone", "value": r[3], "suggest": norm_phone(r[3])}
               for r in rows if r[3] and norm_phone(r[3]) and norm_phone(r[3]) != r[3]]
        names: dict = {}
        for r in rows:
            names.setdefault(norm_name(r[1]), 0)
            names[norm_name(r[1])] += 1
        dups = sum(c - 1 for c in names.values() if c > 1)
        score = round(100 * (1 - (miss_e + miss_p + len(bad_e) + dups) / (4 * total)), 1) if total else None
        out[name] = {"total": total, "missing_email": miss_e, "missing_phone": miss_p, "invalid_email": len(bad_e),
                     "possible_duplicates": dups, "score": score, "recommendations": fmt[:50]}
    return out


async def snapshot(db: AsyncSession, day: Optional[date] = None) -> None:
    from sqlalchemy.dialects.postgresql import insert
    day = day or date.today()
    q = await quality(db)
    for entity, m in q.items():
        m = {k: v for k, v in m.items() if k != "recommendations"}
        await db.execute(insert(DataQualitySnapshot).values(id=uuid.uuid4(), day=day, entity=entity, metrics=m)
                         .on_conflict_do_update(constraint="uq_dq_snapshot_day", set_={"metrics": m}))


async def tick(db: AsyncSession) -> int:
    n = 0
    for s in (await db.execute(select(SyncDefinition).where(SyncDefinition.active.is_(True), SyncDefinition.every_minutes.is_not(None),
                                                            SyncDefinition.source_kind == "HTTP_JSON",
                                                            (SyncDefinition.next_run_at.is_(None)) | (SyncDefinition.next_run_at <= _now()))
                                 .limit(5))).scalars().all():
        try:
            if s.direction == "IN":
                await run_in(db, s, await pull(s), dry_run=False, user="scheduler", trigger="SCHEDULE")
            else:
                await run_out(db, s, dry_run=False, user="scheduler")
        except SyncError as e:
            db.add(SyncRun(sync_id=s.id, version=s.version, trigger="SCHEDULE", status="FAILED", errors=[{"error": str(e)}],
                           run_by="scheduler", finished_at=_now()))
        s.next_run_at = _now() + timedelta(minutes=s.every_minutes)
        await db.commit()
        n += 1
    return n
