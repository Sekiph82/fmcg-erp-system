"""M45.S01.T010 duplicate detection and merge for customers and CRM contacts.

Detection: fuzzy name similarity (normalized, legal suffixes removed) plus exact phone (+254), KRA PIN, e-mail and
address similarity, with blocking so it scales; dismissed pairs are not suggested again.

Merge (preview first, then execute, both behind crm.edit_all):
- both rows are locked (FOR UPDATE, fixed order); a row already merged is refused;
- every reference to the merged row is moved to the survivor: all foreign keys found in the schema (orders, invoices,
  quotes, tickets, payments, activity, consent-related rows...) plus polymorphic contact associations; nothing is
  copied, so no order or invoice is duplicated or orphaned;
- a referencing row that would duplicate one the survivor already has (e.g. the same group membership) is removed
  and kept in the merge log;
- empty survivor fields are filled from the merged row; e-mail consent: the stricter status wins
  (COMPLAINED > UNSUBSCRIBED > BOUNCED > SUBSCRIBED);
- customers: the merged customer is deactivated (kept for history); contacts: the merged contact is deleted;
- the merge log keeps the snapshot, every moved row and every change, so the merge can be undone.
"""
from __future__ import annotations

import difflib
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Numeric, and_, delete, insert, select, update
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_data import DuplicateDismissal, MergeLog
from app.services.customer_data_service import norm_email, norm_name, norm_phone, norm_tax

RANK = {"COMPLAINED": 4, "UNSUBSCRIBED": 3, "BOUNCED": 2, "SUBSCRIBED": 1}
FILL = {"customer": ("contact_person", "email", "phone", "address", "city", "tax_id", "region", "segment"),
        "contact": ("email", "phone", "job_title", "company_id", "language")}


class MergeError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model(entity: str):
    from app.models.crm import CRMContact
    from app.models.sales import Customer
    return {"customer": Customer, "contact": CRMContact}[entity]


def _ratio(a: Optional[str], b: Optional[str]) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio() if a and b else 0.0


def pair_score(a: dict, b: dict) -> tuple[float, list[str]]:
    reasons, s = [], 0.8 * _ratio(a["n"], b["n"])
    if s >= 0.5:
        reasons.append(f"names {round(s / 0.8 * 100)}% alike")
    for k, w, label in (("phone", 0.3, "same phone"), ("tax", 0.4, "same KRA PIN"), ("email", 0.3, "same e-mail")):
        if a.get(k) and a.get(k) == b.get(k):
            s += w
            reasons.append(label)
    addr = _ratio(a.get("addr"), b.get("addr"))
    if addr > 0.8:
        s += 0.1
        reasons.append("similar address")
    return round(min(1.0, s), 3), reasons


async def candidates(db: AsyncSession, entity: str, threshold: float = 0.7, limit: int = 200) -> list[dict]:
    M = _model(entity)
    if entity == "customer":
        rows = (await db.execute(select(M.id, M.name, M.phone, M.tax_id, M.email, M.address, M.code).where(M.is_active.is_(True)))).all()
        recs = [{"id": r[0], "label": f"{r[1]} ({r[6]})", "n": norm_name(r[1]), "phone": norm_phone(r[2]), "tax": norm_tax(r[3]),
                 "email": norm_email(r[4]), "addr": (r[5] or "").lower()} for r in rows]
    else:
        rows = (await db.execute(select(M.id, M.full_name, M.phone, M.email))).all()
        recs = [{"id": r[0], "label": r[1], "n": norm_name(r[1]), "phone": norm_phone(r[2]), "email": norm_email(r[3])} for r in rows]
    blocks: dict = defaultdict(list)
    for r in recs:
        for key in (r["n"][:4] and "n:" + r["n"][:4], r.get("phone") and "p:" + r["phone"], r.get("tax") and "t:" + r["tax"],
                    r.get("email") and "e:" + r["email"]):
            if key:
                blocks[key].append(r)
    dismissed = {(d.a_id, d.b_id) for d in (await db.execute(select(DuplicateDismissal).where(DuplicateDismissal.entity == entity))).scalars()}
    seen, out = set(), []
    for group in blocks.values():
        for i, a in enumerate(group[:200]):
            for b in group[i + 1:200]:
                k = tuple(sorted((a["id"], b["id"]), key=str))
                if k in seen or k in dismissed or a["id"] == b["id"]:
                    continue
                seen.add(k)
                sc, why = pair_score(a, b)
                if sc >= threshold:
                    out.append({"a_id": str(k[0]), "b_id": str(k[1]), "a": a["label"] if a["id"] == k[0] else b["label"],
                                "b": b["label"] if b["id"] == k[1] else a["label"], "score": sc, "reasons": why})
    return sorted(out, key=lambda x: -x["score"])[:limit]


async def dismiss(db: AsyncSession, entity: str, a_id: uuid.UUID, b_id: uuid.UUID, user: str) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    a, b = sorted((a_id, b_id), key=str)
    await db.execute(pg_insert(DuplicateDismissal).values(id=uuid.uuid4(), entity=entity, a_id=a, b_id=b, dismissed_by=user,
                                                          dismissed_at=_now()).on_conflict_do_nothing(constraint="uq_cd_dup_dismissal"))


# ── references ──────────────────────────────────────────────────────────────

def references(entity: str) -> list[tuple[Any, Any]]:
    """Every (table, column) with a foreign key to the entity's table, from the live schema metadata."""
    import app.models  # noqa: F401
    from app.db.base import Base
    target = _model(entity).__table__.name
    return [(t, fk.parent) for t in Base.metadata.tables.values() for fk in t.foreign_keys
            if fk.column.table.name == target and fk.column.name == "id" and t.name not in ("cd_merges",)]


def _jsonable(v: Any) -> Any:
    if isinstance(v, (uuid.UUID, Decimal)):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _row_json(row) -> dict:
    return {k: _jsonable(v) for k, v in row._mapping.items()}


def _coerce(table, data: dict) -> dict:
    out = {}
    for c in table.columns:
        if c.name not in data:
            continue
        v = data[c.name]
        if v is not None:
            if isinstance(c.type, PGUUID) or getattr(c.type, "as_uuid", False):
                v = uuid.UUID(v) if isinstance(v, str) else v
            elif isinstance(c.type, DateTime):
                v = datetime.fromisoformat(v)
            elif isinstance(c.type, Date):
                v = date.fromisoformat(v)
            elif isinstance(c.type, Numeric):
                v = Decimal(v)
        out[c.name] = v
    return out


async def _polymorphic(db, entity, loser_id) -> list:
    from app.models.crm import CRMContactAssociation
    if entity != "customer":
        return []
    return list((await db.execute(select(CRMContactAssociation.id).where(CRMContactAssociation.object_type == "customer",
                                                                         CRMContactAssociation.object_id == loser_id))).scalars())


async def preview(db: AsyncSession, entity: str, survivor_id: uuid.UUID, loser_id: uuid.UUID) -> dict:
    from sqlalchemy import func
    M = _model(entity)
    s, l = await db.get(M, survivor_id), await db.get(M, loser_id)
    if s is None or l is None or survivor_id == loser_id:
        raise MergeError(404, "Pick two different records.")
    moves = []
    for t, col in references(entity):
        n = (await db.execute(select(func.count()).select_from(t).where(col == loser_id))).scalar_one()
        if n:
            moves.append({"table": t.name, "column": col.name, "rows": n})
    poly = await _polymorphic(db, entity, loser_id)
    if poly:
        moves.append({"table": "crm_contact_associations", "column": "object_id (customer)", "rows": len(poly)})
    fills = {f: getattr(l, f) for f in FILL[entity] if not getattr(s, f, None) and getattr(l, f, None)}
    return {"survivor": _label(s), "merged": _label(l), "moves": moves, "fills": {k: _jsonable(v) for k, v in fills.items()},
            "consent": await _consent_plan(db, s, l), "merged_record": "deactivated" if entity == "customer" else "deleted"}


def _label(o) -> str:
    return getattr(o, "name", None) or getattr(o, "full_name", None) or str(o.id)


async def _consent_plan(db, s, l) -> Optional[dict]:
    from app.models.crm import CRMContactConsent
    es, el = norm_email(getattr(s, "email", None)), norm_email(getattr(l, "email", None))
    target = es or el
    if not target:
        return None
    rows = {c.email: c.status for c in (await db.execute(select(CRMContactConsent).where(
        CRMContactConsent.email.in_([e for e in (es, el) if e])))).scalars()}
    statuses = [rows[e] for e in (es, el) if e in rows]
    if not statuses:
        return None
    strict = max(statuses, key=lambda x: RANK.get(x, 0))
    return {"email": target, "before": rows.get(target), "after": strict}


async def merge(db: AsyncSession, entity: str, survivor_id: uuid.UUID, loser_id: uuid.UUID, user, reason: str = "") -> MergeLog:
    from app.models.crm import CRMContactAssociation, CRMContactConsent
    from app.services import pat_service as pats
    M = _model(entity)
    if survivor_id == loser_id:
        raise MergeError(422, "Pick two different records.")
    for i in sorted((survivor_id, loser_id), key=str):           # fixed lock order: no deadlock between two merges
        await db.execute(select(M.id).where(M.id == i).with_for_update())
    s, l = await db.get(M, survivor_id), await db.get(M, loser_id)
    if s is None or l is None:
        raise MergeError(404, "Record not found.")
    if entity == "customer" and (not s.is_active or not l.is_active):
        raise MergeError(409, "One of these customers is already merged or inactive.")
    snapshot = _row_json((await db.execute(select(M.__table__).where(M.id == loser_id))).one())
    moved, removed = [], []
    for t, col in references(entity):
        pk = list(t.primary_key.columns)
        rows = (await db.execute(select(*pk).where(col == loser_id))).all()
        ids = []
        for r in rows:
            cond = and_(*[c == v for c, v in zip(pk, r)])
            try:
                async with db.begin_nested():
                    await db.execute(update(t).where(cond).values({col.name: survivor_id}))
                ids.append([_jsonable(v) for v in r])
            except IntegrityError:   # the survivor already has the same row → keep one, log the other
                full = (await db.execute(select(t).where(cond))).one()
                removed.append({"table": t.name, "row": _row_json(full)})
                await db.execute(delete(t).where(cond))
        if ids:
            moved.append({"table": t.name, "column": col.name, "pk": [c.name for c in pk], "ids": ids})
    poly = await _polymorphic(db, entity, loser_id)
    if poly:
        await db.execute(update(CRMContactAssociation).where(CRMContactAssociation.id.in_(poly)).values(object_id=survivor_id))
        moved.append({"table": "crm_contact_associations", "column": "object_id", "pk": ["id"], "ids": [[str(i)] for i in poly]})
    changes = {}
    for f in FILL[entity]:
        if not getattr(s, f, None) and getattr(l, f, None):
            changes[f] = {"old": None, "new": _jsonable(getattr(l, f))}
    plan = await _consent_plan(db, s, l)
    if entity == "contact":
        await db.execute(delete(M.__table__).where(M.id == loser_id))      # frees its unique e-mail first
        await db.flush()
    for f, ch in changes.items():
        setattr(s, f, getattr(l, f) if entity == "customer" else _coerce(M.__table__, {f: ch["new"]})[f])
    if plan and plan["after"] != plan["before"]:
        c = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == plan["email"]))).scalar_one_or_none()
        if c is None:
            db.add(CRMContactConsent(email=plan["email"], status=plan["after"], source=f"merge:{user.username}"[:100], updated_at=_now()))
        else:
            c.status, c.source, c.updated_at = plan["after"], f"merge:{user.username}"[:100], _now()
        changes["consent"] = plan
        if plan["after"] in ("UNSUBSCRIBED", "COMPLAINED", "BOUNCED"):
            await db.flush()
            from app.services.audience_sync_service import suppress_now
            await suppress_now(db, plan["email"])
    if entity == "customer":
        l.is_active = False
        l.notes = ((l.notes or "") + f"\nMerged into {s.code} on {_now().date()} by {user.username}.").strip()
    log = MergeLog(entity=entity, survivor_id=survivor_id, merged_id=loser_id, snapshot={"row": snapshot, "removed": removed},
                   moved=moved, field_changes=changes, reason=reason[:300], merged_by=user.username)
    db.add(log)
    await db.flush()
    pats.audit(db, user, f"{entity.upper()}_MERGED", entity, str(survivor_id),
               {"merged": str(loser_id), "moved_tables": [m["table"] for m in moved], "removed": len(removed)})
    return log


async def undo(db: AsyncSession, log_id: uuid.UUID, user) -> MergeLog:
    """Restore the merged record, move every logged reference back and restore removed duplicate rows."""
    import app.models  # noqa: F401
    from app.db.base import Base
    from app.models.crm import CRMContactConsent
    from app.services import pat_service as pats
    log = await db.get(MergeLog, log_id, with_for_update=True)
    if log is None:
        raise MergeError(404, "Merge not found")
    if log.undone_at:
        raise MergeError(409, "Already undone.")
    M = _model(log.entity)
    s = await db.get(M, log.survivor_id)
    if log.entity == "contact":
        await db.execute(insert(M.__table__).values(**_coerce(M.__table__, log.snapshot["row"])))
    else:
        l = await db.get(M, log.merged_id)
        l.is_active, l.notes = True, log.snapshot["row"].get("notes")
    for f, ch in log.field_changes.items():
        if f == "consent":
            c = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == ch["email"]))).scalar_one_or_none()
            if c is not None and ch["before"]:
                c.status = ch["before"]
            elif c is not None:
                await db.delete(c)
        elif s is not None and str(_jsonable(getattr(s, f))) == str(ch["new"]):   # only if nobody changed it since
            setattr(s, f, None)
    await db.flush()
    for m in log.moved:
        t = Base.metadata.tables[m["table"]]
        pk = [t.columns[c] for c in m["pk"]]
        for ids in m["ids"]:
            vals = _coerce(t, dict(zip(m["pk"], ids)))
            await db.execute(update(t).where(and_(*[c == vals[c.name] for c in pk])).values({m["column"]: log.merged_id}))
    for r in log.snapshot.get("removed", []):
        t = Base.metadata.tables[r["table"]]
        await db.execute(insert(t).values(**_coerce(t, r["row"])))
    log.undone_by, log.undone_at = user.username, _now()
    pats.audit(db, user, f"{log.entity.upper()}_MERGE_UNDONE", log.entity, str(log.survivor_id), {"merged": str(log.merged_id)})
    return log
