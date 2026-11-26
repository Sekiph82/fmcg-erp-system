"""M45.S01.T018 configuration sandbox: versioned configuration bundles with diff and dry run.

A bundle holds configuration only (pipelines and stages, custom fields and options, custom object types, e-mail
templates, sequences and steps, lead forms, lead-score and routing rules, workflows with their published graph). Rows
are identified by natural keys, never by database ids, so a bundle exported from a staging copy applies cleanly to
production even though ids differ; references between rows travel as the referenced row's natural key.
Environment-specific or personal columns (users, territories, companies, routing members/state) are left out, and no
customer, contact or transaction table is ever part of a bundle.
Import: diff → create / update / unchanged / skip, dry run writes nothing; apply runs in one transaction; workflows
arrive as a new DRAFT version that must be published again. A bundle from another schema revision is refused.
Optional CMS part (M47.S01.T007, items["cms"]): see cms_bundle_service — pages arrive as drafts, never published.
"""
from __future__ import annotations

import enum
import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import String, and_, func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

FORMAT = "fmcg-erp-config"
FORMAT_VERSION = 1
SPEC: list[dict] = [
    {"table": "crm_pipelines", "key": ["name"], "drop": ["company_id"]},
    {"table": "crm_pipeline_stages", "key": ["stage_code"], "fks": {"pipeline_id": ("crm_pipelines", ["name"])}},
    {"table": "cf_definitions", "key": ["entity_type", "field_code"], "pk": "custom_field_id", "drop": ["created_by"]},
    {"table": "cf_options", "key": ["custom_field_id", "option_value"], "pk": "option_id",
     "fks": {"custom_field_id": ("cf_definitions", ["entity_type", "field_code"])}},
    {"table": "co_types", "key": ["key"], "drop": ["created_by"]},
    {"table": "email_templates", "key": ["name"], "drop": ["created_by_id"]},
    {"table": "crm_sequences", "key": ["name"]},
    {"table": "crm_sequence_steps", "key": ["sequence_id", "step_no"], "fks": {"sequence_id": ("crm_sequences", ["name"])}},
    {"table": "crm_lead_forms", "key": ["slug"],
     "drop": ["assigned_rep_id", "territory_id", "company_id", "branch_id", "sales_region_id", "sales_team_id"]},
    {"table": "crm_score_rules", "key": ["name", "field"]},
    {"table": "crm_routing_rules", "key": ["name"], "drop": ["user_ids", "weights", "state"]},
    {"table": "crm_workflows", "key": ["name"], "drop": ["published_version_id", "enqueued_until", "created_by"], "workflow": True},
]
ALWAYS_DROP = {"id", "created_at", "updated_at"}


class BundleError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _tables():
    import app.models  # noqa: F401
    from app.db.base import Base
    return Base.metadata.tables


PEOPLE_KEY = re.compile(r"(^|_)(user|owner|assignee|rep|approver|agent)(_?(ids?|names?)|s)?$", re.I)   # incl. notify "usernames"
EMAIL = re.compile(r"[^@\s\"']+@[^@\s\"']+\.[a-z]{2,}", re.I)


def strip_people(value: Any) -> Any:
    """Workflow graphs travel between environments: people (user ids, e-mail addresses) do not (M46.S01.T008).
    Such values become null / "<set after import>" and must be filled in on the target before publishing."""
    if isinstance(value, dict):
        return {k: (None if PEOPLE_KEY.search(str(k)) and v not in (None, "", []) else strip_people(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_people(v) for v in value]
    if isinstance(value, str) and EMAIL.search(value):
        return EMAIL.sub("<set after import>", value)
    return value


def _j(v: Any) -> Any:
    if isinstance(v, enum.Enum):
        return v.name
    if isinstance(v, (uuid.UUID, Decimal)):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


async def _revision(db: AsyncSession) -> Optional[str]:
    try:
        return (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
    except Exception:
        return None


async def _key_of(db: AsyncSession, table: str, pk_value, key: list[str], pk: str = "id") -> Any:
    t = _tables()[table]
    row = (await db.execute(select(*[t.c[k] for k in key]).where(t.c[pk] == pk_value))).one_or_none()
    if row is None:
        return None
    vals = [_j(v) for v in row]
    return vals[0] if len(vals) == 1 else vals


async def export(db: AsyncSession, include_cms: bool = False) -> dict:
    tables = _tables()
    out: dict[str, list] = {}
    for spec in SPEC:
        t = tables[spec["table"]]
        pk = spec.get("pk", "id")
        drop = ALWAYS_DROP | set(spec.get("drop", [])) | {pk}
        rows = []
        for r in (await db.execute(select(t))).mappings():
            item = {c: _j(v) for c, v in r.items() if c not in drop}
            for col, (ref_table, ref_key) in spec.get("fks", {}).items():
                ref_spec = next(s for s in SPEC if s["table"] == ref_table)
                item[col] = await _key_of(db, ref_table, r[col], ref_key, ref_spec.get("pk", "id")) if r[col] is not None else None
            if spec.get("workflow"):
                v = tables["crm_workflow_versions"]
                pub = (await db.execute(select(v.c.graph).where(v.c.id == r["published_version_id"]))).scalar() if r["published_version_id"] else None
                latest = (await db.execute(select(v.c.graph).where(v.c.workflow_id == r["id"]).order_by(v.c.version_no.desc()).limit(1))).scalar()
                item["graph"] = strip_people(pub if pub is not None else latest)
            rows.append(item)
        out[spec["table"]] = sorted(rows, key=lambda x: json.dumps([x.get(k) for k in spec["key"]], default=str))
    if include_cms:
        from app.services import cms_bundle_service
        out["cms"] = await cms_bundle_service.export(db)
    body = {"format": FORMAT, "format_version": FORMAT_VERSION, "schema_revision": await _revision(db),
            "exported_at": datetime.now(timezone.utc).isoformat(), "items": out}
    body["sha256"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    return body


def _coerce(t, data: dict) -> dict:
    from app.services.dedupe_service import _coerce as base
    out = base(t, data)
    for c in t.columns:          # enum columns: the bundle carries member names
        if c.name in out and out[c.name] is not None and hasattr(c.type, "enum_class") and c.type.enum_class is not None:
            out[c.name] = c.type.enum_class[out[c.name]]
    return out


async def _resolve_fk(db: AsyncSession, ref_table: str, ref_key: list[str], value) -> Any:
    t = _tables()[ref_table]
    ref_spec = next(s for s in SPEC if s["table"] == ref_table)
    vals = value if isinstance(value, list) else [value]
    cond = and_(*[t.c[k] == _coerce(t, {k: v})[k] for k, v in zip(ref_key, vals)])
    return (await db.execute(select(t.c[ref_spec.get("pk", "id")]).where(cond).limit(1))).scalar()


async def plan(db: AsyncSession, bundle: dict, mode: str = "overwrite", site_keys: Optional[dict] = None) -> list[dict]:
    """Per row: create | update (with changed fields) | unchanged | skip | error. Writes nothing."""
    if bundle.get("format") != FORMAT or bundle.get("format_version") != FORMAT_VERSION:
        raise BundleError(422, "This is not a configuration bundle of a supported version.")
    if hashlib.sha256(json.dumps(bundle.get("items", {}), sort_keys=True, default=str).encode()).hexdigest() != bundle.get("sha256"):
        raise BundleError(422, "The bundle was changed after export (checksum mismatch).")
    rev = await _revision(db)
    if bundle.get("schema_revision") and rev and bundle["schema_revision"] != rev:
        raise BundleError(409, f"The bundle is from schema {bundle['schema_revision']}; this database is at {rev}. Upgrade first.")
    tables = _tables()
    steps = []
    for spec in SPEC:
        t = tables[spec["table"]]
        pk = spec.get("pk", "id")
        for item in bundle["items"].get(spec["table"], []):
            row = dict(item)
            graph = row.pop("graph", None) if spec.get("workflow") else None
            err = None
            for col, (ref_table, ref_key) in spec.get("fks", {}).items():
                if row.get(col) is not None:
                    rid = await _resolve_fk(db, ref_table, ref_key, row[col])
                    if rid is None and not any(s["table"] == ref_table and any(_same(x, row[col], s["key"]) for x in bundle["items"].get(ref_table, []))
                                               for s in SPEC):
                        err = f"{col}: referenced {ref_table} {row[col]} not found"
                    row[col] = rid
            keyvals = {k: row[k] for k in spec["key"]}
            existing = None
            if all(v is not None for v in keyvals.values()):
                c = _coerce(t, keyvals)
                existing = (await db.execute(select(t).where(and_(*[t.c[k] == c[k] for k in spec["key"]])))).mappings().first()
            label = " / ".join(str(item[k]) for k in spec["key"])
            if err:
                steps.append({"table": spec["table"], "key": label, "action": "error", "detail": err})
            elif existing is None:
                steps.append({"table": spec["table"], "key": label, "action": "create", "row": row, "graph": graph})
            else:
                changed = [c for c, v in row.items() if c in t.c and _j(existing[c]) != v and c not in spec.get("fks", {})]
                if graph is not None:
                    changed.append("graph")
                if not changed:
                    steps.append({"table": spec["table"], "key": label, "action": "unchanged"})
                elif mode == "skip_existing":
                    steps.append({"table": spec["table"], "key": label, "action": "skip", "changed": changed})
                else:
                    steps.append({"table": spec["table"], "key": label, "action": "update", "changed": changed, "row": row,
                                  "id": existing[pk], "graph": graph})
    if isinstance(bundle["items"].get("cms"), dict):
        from app.services import cms_bundle_service
        steps += await cms_bundle_service.plan(db, bundle["items"]["cms"], mode, site_keys)
    return steps


def _same(x: dict, value, key: list[str]) -> bool:
    vals = value if isinstance(value, list) else [value]
    return [x.get(k) for k in key] == vals


async def apply(db: AsyncSession, bundle: dict, user: str, mode: str = "overwrite", site_keys: Optional[dict] = None) -> dict:
    steps = await plan(db, bundle, mode, site_keys)
    if any(s["action"] == "error" for s in steps):
        raise BundleError(422, "The bundle has unresolved references; see the dry run.")
    tables = _tables()
    done = {"create": 0, "update": 0}
    for s in steps:
        if s["action"] not in ("create", "update") or s["table"].startswith("cms_"):
            continue
        spec = next(x for x in SPEC if x["table"] == s["table"])
        t, pk = tables[s["table"]], spec.get("pk", "id")
        row = dict(s["row"])
        for col, (ref_table, ref_key) in spec.get("fks", {}).items():   # parents created earlier in this same apply
            if row.get(col) is None:
                orig = next((i for i in bundle["items"][s["table"]] if " / ".join(str(i[k]) for k in spec["key"]) == s["key"]), {})
                if orig.get(col) is not None:
                    row[col] = await _resolve_fk(db, ref_table, ref_key, orig[col])
        vals = _coerce(t, row)
        if s["action"] == "create":
            new_id = str(uuid.uuid4()) if isinstance(t.c[pk].type, String) else uuid.uuid4()
            await db.execute(insert(t).values(**{pk: new_id}, **vals))
            rid = new_id
        else:
            await db.execute(update(t).where(t.c[pk] == s["id"]).values(**vals))
            rid = s["id"]
        if spec.get("workflow") and s.get("graph") is not None:
            v = tables["crm_workflow_versions"]
            n = (await db.execute(select(func.coalesce(func.max(v.c.version_no), 0)).where(v.c.workflow_id == rid))).scalar_one()
            await db.execute(insert(v).values(id=uuid.uuid4(), workflow_id=rid, version_no=n + 1, graph=s["graph"], status="DRAFT",
                                              created_by=f"bundle:{user}"[:100], created_at=datetime.now(timezone.utc)))
        done[s["action"]] += 1
    cms_steps = [s for s in steps if s["table"].startswith("cms_")]
    if cms_steps:
        from app.services import cms_bundle_service
        from app.services.cms_service import CmsError
        try:
            for k, n in (await cms_bundle_service.apply(db, cms_steps, user)).items():
                done[k] += n
        except CmsError as e:
            raise BundleError(422, f"Content import refused: {e}")
    return {"created": done["create"], "updated": done["update"],
            "unchanged": sum(1 for s in steps if s["action"] == "unchanged"), "skipped": sum(1 for s in steps if s["action"] == "skip")}
