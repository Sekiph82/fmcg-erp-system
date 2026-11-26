"""M45.S01.T015 custom objects: admin-defined types with typed fields, records, associations, CSV import/export,
grouped reports and agent triggers ("custom_object.<key>.created|updated").

Values are validated against the type's fields (text, number, date, bool, select, email, phone); required and
unique are enforced (unique under a per-type advisory lock). No SQL is ever built from user input: records are JSONB.
Access: the module rights below plus, per type, optional role lists; company isolation through the user's company
scopes (records of other companies are invisible). Deleting a record removes its associations.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import Float, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_objects import CustomObjectAssociation, CustomObjectRecord, CustomObjectType

VIEW = ("crm.view", "crm.view_all", "sales.view")
EDIT = ("crm.edit", "crm.edit_all", "sales.edit")
ADMIN = ("crm.edit_all",)
TYPES = ("text", "number", "date", "bool", "select", "email", "phone")
TARGETS = {"customer": ("app.models.sales", "Customer"), "crm_record": ("app.models.crm", "CRMRecord"),
           "product": ("app.models.master", "Product"), "sales_order": ("app.models.sales", "SalesOrder"),
           "co_record": ("app.models.custom_objects", "CustomObjectRecord")}


class COError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def validate_type(body: dict) -> dict:
    key = str(body.get("key") or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,39}", key):
        raise COError(422, "Key: 2–40 characters, lower-case letters, digits and _ (starting with a letter).")
    fields = body.get("fields") or []
    if not 1 <= len(fields) <= 50:
        raise COError(422, "Define 1–50 fields.")
    seen = set()
    for f in fields:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", str(f.get("key") or "")) or f["key"] in seen:
            raise COError(422, f"Field key {f.get('key')!r} is invalid or repeated.")
        seen.add(f["key"])
        if f.get("type") not in TYPES:
            raise COError(422, f"Field {f['key']}: type must be one of {', '.join(TYPES)}.")
        if f["type"] == "select" and not f.get("options"):
            raise COError(422, f"Field {f['key']}: a select needs options.")
        f["label"] = str(f.get("label") or f["key"])[:80]
        f["required"], f["unique"] = bool(f.get("required")), bool(f.get("unique"))
    display = body.get("display_field") or fields[0]["key"]
    if display not in seen:
        raise COError(422, "display_field must be one of the fields.")
    return {"key": key, "label": str(body.get("label") or key)[:80], "label_plural": str(body.get("label_plural") or body.get("label") or key)[:80],
            "fields": fields, "display_field": display, "view_roles": list(body.get("view_roles") or []),
            "edit_roles": list(body.get("edit_roles") or [])}


def coerce(field: dict, value: Any) -> Any:
    if value is None or value == "":
        return None
    t = field["type"]
    try:
        if t == "number":
            return float(value)
        if t == "bool":
            return value if isinstance(value, bool) else str(value).strip().lower() in ("1", "true", "yes", "y")
        if t == "date":
            return date.fromisoformat(str(value)[:10]).isoformat()
        if t == "select":
            if str(value) not in field["options"]:
                raise ValueError
            return str(value)
        if t == "email":
            v = str(value).strip().lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
                raise ValueError
            return v
        if t == "phone":
            from app.services.customer_data_service import norm_phone
            v = norm_phone(str(value))
            if not v:
                raise ValueError
            return v
        return str(value)[:2000]
    except (ValueError, TypeError):
        raise COError(422, f"{field['label']}: {value!r} is not a valid {t}.")


def _roles(user) -> set[str]:
    return {r.name for r in getattr(user, "roles", []) or [] if getattr(r, "is_active", True)}


def can(user, t: CustomObjectType, write: bool) -> bool:
    from app.core.access_control import has_any_permission
    if user.is_superuser:
        return True
    if not has_any_permission(user, EDIT if write else VIEW):
        return False
    allowed = t.edit_roles if write else (t.view_roles or t.edit_roles)
    return not allowed or bool(_roles(user) & set(allowed))


def companies(user) -> Optional[set]:
    """None = all companies; otherwise the company ids in the user's scopes (records without a company are shared)."""
    from app.core.access_control import get_effective_scopes
    if user.is_superuser:
        return None
    ids = {str(s["scope_id"]) for s in get_effective_scopes(user, "company")}
    return None if not ids or "ALL" in ids else ids


def visible(stmt, user):
    from sqlalchemy import or_
    comp = companies(user)
    if comp is None:
        return stmt
    return stmt.where(or_(CustomObjectRecord.company_id.is_(None), CustomObjectRecord.company_id.in_([uuid.UUID(c) for c in comp])))


async def get_type(db: AsyncSession, key: str, user, write: bool = False) -> CustomObjectType:
    t = (await db.execute(select(CustomObjectType).where(CustomObjectType.key == key))).scalar_one_or_none()
    if t is None or not can(user, t, False):
        raise COError(404, "Object type not found")
    if write and not can(user, t, True):
        raise COError(403, f"You may not change {t.label_plural}.")
    return t


async def clean(db: AsyncSession, t: CustomObjectType, data: dict, record_id: Optional[uuid.UUID] = None) -> dict:
    unknown = set(data) - {f["key"] for f in t.fields}
    if unknown:
        raise COError(422, f"Unknown fields: {', '.join(sorted(unknown))}.")
    out = {}
    for f in t.fields:
        v = coerce(f, data.get(f["key"]))
        if v is None and f["required"]:
            raise COError(422, f"{f['label']} is required.")
        out[f["key"]] = v
    for f in t.fields:
        if f["unique"] and out[f["key"]] is not None:
            await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"co:{t.id}:{f['key']}"})
            q = select(func.count()).select_from(CustomObjectRecord).where(
                CustomObjectRecord.type_id == t.id, CustomObjectRecord.data[f["key"]].astext == str(out[f["key"]]))
            if record_id:
                q = q.where(CustomObjectRecord.id != record_id)
            if (await db.execute(q)).scalar_one():
                raise COError(409, f"{f['label']} {out[f['key']]!r} is already used.")
    return out


async def upsert(db: AsyncSession, t: CustomObjectType, data: dict, user, record: Optional[CustomObjectRecord] = None,
                 company_id: Optional[uuid.UUID] = None) -> CustomObjectRecord:
    from app.services import agent_service as ags
    vals = await clean(db, t, data, record.id if record else None)
    display = str(vals.get(t.display_field) or "—")[:255]
    if record is None:
        comp = companies(user)
        if comp is not None and (company_id is None or str(company_id) not in comp):
            company_id = uuid.UUID(sorted(comp)[0])          # scoped users always write into their own company
        record = CustomObjectRecord(type_id=t.id, data=vals, display=display, company_id=company_id, created_by=user.username)
        db.add(record)
        event = "created"
    else:
        record.data, record.display, record.updated_at = vals, display, datetime.now(timezone.utc)
        event = "updated"
    await db.flush()
    await ags.fire(db, f"custom_object.{t.key}.{event}", {"event_id": f"{record.id}:{record.updated_at.isoformat()}",
                                                         "record_id": str(record.id), "data": vals}, getattr(user, "id", None))
    return record


async def get_record(db: AsyncSession, t: CustomObjectType, rid: uuid.UUID, user) -> CustomObjectRecord:
    r = (await db.execute(visible(select(CustomObjectRecord).where(CustomObjectRecord.id == rid,
                                                                  CustomObjectRecord.type_id == t.id), user))).scalar_one_or_none()
    if r is None:
        raise COError(404, "Record not found")
    return r


async def associate(db: AsyncSession, r: CustomObjectRecord, target_type: str, target_id: uuid.UUID, label: str) -> None:
    import importlib
    from sqlalchemy.dialects.postgresql import insert
    if target_type not in TARGETS:
        raise COError(422, f"Target must be one of {', '.join(TARGETS)}.")
    mod, cls = TARGETS[target_type]
    if await db.get(getattr(importlib.import_module(mod), cls), target_id) is None:
        raise COError(404, f"{target_type} not found")
    await db.execute(insert(CustomObjectAssociation).values(id=uuid.uuid4(), record_id=r.id, target_type=target_type, target_id=target_id,
                                                            label=label[:40] or "related", created_at=datetime.now(timezone.utc))
                     .on_conflict_do_nothing(constraint="uq_co_association"))


async def records_for(db: AsyncSession, target_type: str, target_id: uuid.UUID, user) -> list[dict]:
    """Custom records associated with an ERP record (e.g. freezers placed at a customer)."""
    rows = (await db.execute(visible(select(CustomObjectRecord, CustomObjectType, CustomObjectAssociation.label)
                                     .join(CustomObjectAssociation, CustomObjectAssociation.record_id == CustomObjectRecord.id)
                                     .join(CustomObjectType, CustomObjectType.id == CustomObjectRecord.type_id)
                                     .where(CustomObjectAssociation.target_type == target_type,
                                            CustomObjectAssociation.target_id == target_id), user))).all()
    return [{"type": t.key, "label": t.label, "record_id": str(r.id), "display": r.display, "association": lab}
            for r, t, lab in rows if can(user, t, False)]


def export_csv(t: CustomObjectType, rows: list[CustomObjectRecord]) -> str:
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=["id"] + [f["key"] for f in t.fields])
    w.writeheader()
    for r in rows:
        w.writerow({"id": str(r.id), **{k: ("" if v is None else v) for k, v in r.data.items()}})
    return out.getvalue()


async def import_csv(db: AsyncSession, t: CustomObjectType, text_: str, user) -> dict:
    created, errors = 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(text_)), start=2):
        data = {k: v for k, v in row.items() if k and k != "id" and k in {f["key"] for f in t.fields}}
        try:
            async with db.begin_nested():
                await upsert(db, t, data, user)
            created += 1
        except COError as e:
            errors.append({"line": i, "error": str(e)})
    return {"created": created, "errors": errors[:200]}


async def catalog(db: AsyncSession, user) -> dict:
    """Custom object types this user may read, as report-builder data sources "co:<key>" (M46.S01.T008)."""
    out = {}
    for t in (await db.execute(select(CustomObjectType).order_by(CustomObjectType.label))).scalars():
        if can(user, t, False):
            fields = [{"path": "display", "label": t.label, "type": "string"}] + [
                {"path": f["key"], "label": f["label"], "type": "number" if f["type"] == "number" else "string"} for f in t.fields]
            out[f"co:{t.key}"] = {"label": f"{t.label_plural} (custom)", "module": "custom_objects", "table": None, "fields": fields}
    return out


async def report_rows(db: AsyncSession, key: str, user, paths: list[str], filters: list[dict], limit: int, offset: int) -> dict:
    """Rows for the report builder, through the same access rules as the object screens (roles + company scope)."""
    from app.services.report_builder_service import _apply_filter_python
    t = (await db.execute(select(CustomObjectType).where(CustomObjectType.key == key))).scalar_one_or_none()
    if t is None or not can(user, t, False):
        return {"columns": [], "rows": [], "total": 0, "error": "Not found"}
    allowed = ["display"] + [f["key"] for f in t.fields]
    cols = [p for p in paths if p in allowed] or allowed[:6]
    stmt = visible(select(CustomObjectRecord).where(CustomObjectRecord.type_id == t.id), user).order_by(CustomObjectRecord.display)
    recs = list((await db.execute(stmt.limit(5000))).scalars())
    rows = [{c: (r.display if c == "display" else r.data.get(c)) for c in cols} for r in recs]
    for f in filters:
        if f.get("field_path") in allowed:
            rows = _apply_filter_python(rows, f["field_path"], f["operator"], f.get("value", ""), f.get("value_to"))
    total = len(rows)
    rows = [{k: (None if v is None else str(v)) for k, v in r.items()} for r in rows[offset: offset + limit]]
    return {"columns": [{"path": c, "label": c, "type": "string"} for c in cols], "rows": rows, "total": total}


async def report(db: AsyncSession, t: CustomObjectType, user, group_by: str, metric: Optional[str]) -> list[dict]:
    """Count (and sum of a number field) per value of a field, over the records this user may see."""
    keys = {f["key"]: f for f in t.fields}
    if group_by not in keys or (metric and keys.get(metric, {}).get("type") != "number"):
        raise COError(422, "group_by must be a field; metric a number field.")
    g = CustomObjectRecord.data[group_by].astext
    cols = [g.label("value"), func.count().label("count")]
    if metric:
        cols.append(func.sum(CustomObjectRecord.data[metric].astext.cast(Float)).label("sum"))
    rows = (await db.execute(visible(select(*cols).where(CustomObjectRecord.type_id == t.id), user).group_by(g).order_by(g))).all()
    return [{"value": r.value, "count": r.count, **({"sum": float(r.sum or 0)} if metric else {})} for r in rows]
