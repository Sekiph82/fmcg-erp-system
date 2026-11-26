"""M50.S01.T009 runtime for the common no-code data sync: object adapters, reference resolution, export rows,
transactional proposals (two-person approval, DRAFT documents through the domain's own create functions),
reconciliation (rows, stock vs the movement ledger, invoices vs the general ledger) and conflict resolution.

Nothing here writes stock or posted finance. Stock/invoices are read-only targets; sales and purchase orders are only
ever created as DRAFTs after a different person approves the staged row.
"""
from __future__ import annotations

import importlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m50_data_sso import SyncConflict, SyncOptions, SyncProposal
from app.services import m50_sync_registry as reg

NATURAL = {"customer": ("app.models.sales", "Customer", "code"), "crm_record": ("app.models.crm", "CRMRecord", "opportunity_code"),
           "product": ("app.models.master", "Product", "sku"), "sales_order": ("app.models.sales", "SalesOrder", "order_no"),
           "ticket": ("app.models.helpdesk", "HelpdeskTicket", "ticket_no")}
CONTACT_TO = ("customer", "crm_record", "ticket", "sales_order")
CO_TO = ("customer", "crm_record", "product", "sales_order")
ENUM_MODULES = ("app.models.master", "app.models.helpdesk", "app.models.crm", "app.models.sales", "app.models.procurement")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cls(mod_cls):
    return getattr(importlib.import_module(mod_cls[0]), mod_cls[1])


def enum_class(name: str):
    for m in ENUM_MODULES:
        c = getattr(importlib.import_module(m), name, None)
        if c is not None:
            return c
    raise ValueError(f"unknown enum {name}")


async def options(db: AsyncSession, sync) -> dict:
    o = await db.get(SyncOptions, sync.id)
    return dict(o.options) if o else {}


async def set_options(db: AsyncSession, sync_id: uuid.UUID, opts: dict) -> None:
    o = await db.get(SyncOptions, sync_id)
    if o is None:
        db.add(SyncOptions(sync_id=sync_id, options=opts))
    else:
        o.options = opts


async def custom_type(db: AsyncSession, key: str):
    from app.models.custom_objects import CustomObjectType
    return (await db.execute(select(CustomObjectType).where(CustomObjectType.key == key))).scalar_one_or_none()


_CO_KIND = {"text": "text", "number": "number", "date": "date", "bool": "bool", "select": "text", "email": "email", "phone": "phone"}


async def spec_for(db: AsyncSession, target: str, opts: dict) -> dict:
    """The registry entry; a custom-object sync gets its fields, required fields and key from the object type."""
    from app.services.data_sync_service import TARGETS, SyncError
    if target not in TARGETS:
        raise SyncError(422, f"Target must be one of {', '.join(TARGETS)}.")
    spec = TARGETS[target]
    if spec.get("adapter") == "co":
        t = await custom_type(db, str(opts.get("custom_type") or ""))
        if t is None:
            raise SyncError(422, "A custom-object sync needs options.custom_type naming an existing object type.")
        return {**spec, "key": t.display_field, "type": t,
                "fields": {f["key"]: _CO_KIND[f["type"]] for f in t.fields},
                "required": [f["key"] for f in t.fields if f["required"] or f["key"] == t.display_field]}
    if spec.get("adapter") == "assoc":
        frm = str(opts.get("from") or "")
        if frm != "contact" and not frm.startswith("custom:"):
            raise SyncError(422, "An association sync needs options.from = 'contact' or 'custom:<object type key>'.")
        t = None
        if frm.startswith("custom:"):
            t = await custom_type(db, frm[7:])
            if t is None:
                raise SyncError(422, "That custom object type does not exist.")
        return {**spec, "from": frm, "type": t}
    return spec


# ── reference resolution ─────────────────────────────────────────────────────

async def resolve(db: AsyncSession, spec: dict, vals: dict, cache: dict) -> dict:
    """Replace natural-key reference fields (customer_code ...) by the related record's id; enum names by members."""
    out = dict(vals)
    for fld, (col, tgt) in (spec.get("refs") or {}).items():
        code = out.pop(fld, None)
        if code in (None, ""):
            out[col] = None
            continue
        from app.services.data_sync_service import TARGETS
        ts = TARGETS[tgt]
        ck = (tgt, str(code))
        if ck not in cache:
            M = _cls(ts["model"])
            cache[ck] = (await db.execute(select(M.id).where(getattr(M, ts["key"]) == str(code)))).scalar_one_or_none()
        if cache[ck] is None:
            raise ValueError(f"{fld} {code!r} not found: synchronise {tgt} first")
        out[col] = cache[ck]
    if spec.get("model"):
        M = _cls(spec["model"])
        for k, v in list(out.items()):
            col = M.__table__.c.get(k)
            if col is not None and isinstance(v, str) and getattr(col.type, "enum_class", None) is not None:
                out[k] = col.type.enum_class(v)
    return out


# ── adapters ─────────────────────────────────────────────────────────────────

class ModelAdapter:
    immutable = False

    def __init__(self, db, spec, **_):
        self.db, self.spec = db, spec
        self.M = _cls(spec["model"])
        self.keycol = getattr(self.M, spec["key"])

    async def find(self, key, vals=None):
        return (await self.db.execute(select(self.M).where(self.keycol == key).with_for_update())).scalar_one_or_none()

    async def create(self, vals):
        obj = self.M(**vals)
        self.db.add(obj)
        await self.db.flush()
        return obj

    def get(self, obj, k):
        return getattr(obj, k)

    async def update(self, obj, changes):
        for k, v in changes.items():
            setattr(obj, k, v)

    async def restore(self, obj, values):
        col = self.M.__table__.c
        for k, v in values.items():
            t = col[k].type
            if v is not None and t.__class__.__name__ == "Numeric":
                v = Decimal(v)
            elif v is not None and getattr(t, "enum_class", None) is not None:
                v = t.enum_class(v)
            setattr(obj, k, v)

    async def load(self, ident):
        return await self.db.get(self.M, uuid.UUID(ident))

    async def remove(self, obj):
        await self.db.delete(obj)
        await self.db.flush()

    def ident(self, obj):
        return str(obj.id)

    def deactivate(self, obj) -> Optional[bool]:
        if hasattr(obj, "is_active") and obj.is_active:
            obj.is_active = False
            return True
        return None


class CustomObjectAdapter(ModelAdapter):
    def __init__(self, db, spec, actor=None, **_):
        from app.models.custom_objects import CustomObjectRecord
        self.db, self.spec, self.actor, self.M, self.t = db, spec, actor, CustomObjectRecord, spec["type"]
        if actor is None:
            raise ValueError("A custom-object sync runs as a signed-in user (object-type roles and company scope apply).")

    async def find(self, key, vals=None):
        from app.services import custom_object_service as co
        q = co.visible(select(self.M).where(self.M.type_id == self.t.id, self.M.data[self.t.display_field].astext == str(key)),
                       self.actor).with_for_update()
        return (await self.db.execute(q)).scalars().first()

    async def create(self, vals):
        from app.services import custom_object_service as co
        try:
            return await co.upsert(self.db, self.t, _plain(vals), self.actor)
        except co.COError as e:
            raise ValueError(str(e))

    def get(self, obj, k):
        v = (obj.data or {}).get(k)
        if v is not None and self.spec["fields"].get(k) == "number":
            return Decimal(str(v))
        return v

    async def update(self, obj, changes):
        from app.services import custom_object_service as co
        try:
            await co.upsert(self.db, self.t, {**obj.data, **_plain(changes)}, self.actor, record=obj)
        except co.COError as e:
            raise ValueError(str(e))

    async def restore(self, obj, values):
        obj.data = {**obj.data, **values}
        obj.display = str(obj.data.get(self.t.display_field) or "-")[:255]

    def deactivate(self, obj):
        return None


def _plain(d: dict) -> dict:
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


class AssocAdapter:
    """Links: contact → record, or custom-object record → record. Existing links are never changed, only created/removed."""
    immutable = True

    def __init__(self, db, spec, **_):
        from app.models.crm import CRMContactAssociation
        from app.models.custom_objects import CustomObjectAssociation
        self.db, self.spec = db, spec
        self.contact = spec["from"] == "contact"
        self.M = CRMContactAssociation if self.contact else CustomObjectAssociation

    async def _ids(self, key: str):
        from app.models.crm import CRMContact
        from app.models.custom_objects import CustomObjectRecord
        frm, to_type, to_key, label = key.split("|", 3)
        allowed = CONTACT_TO if self.contact else CO_TO
        if to_type not in allowed:
            raise ValueError(f"to_type must be one of {', '.join(allowed)}")
        if self.contact:
            src = (await self.db.execute(select(CRMContact.id).where(CRMContact.email == frm.lower()))).scalar_one_or_none()
            if src is None:
                raise ValueError(f"contact {frm!r} not found: synchronise crm_contacts first")
        else:
            src = (await self.db.execute(select(CustomObjectRecord.id).where(
                CustomObjectRecord.type_id == self.spec["type"].id,
                CustomObjectRecord.data[self.spec["type"].display_field].astext == frm))).scalars().first()
            if src is None:
                raise ValueError(f"{self.spec['type'].key} record {frm!r} not found: synchronise custom_objects first")
        mod, cls, col = NATURAL[to_type]
        M = getattr(importlib.import_module(mod), cls)
        dst = (await self.db.execute(select(M.id).where(getattr(M, col) == to_key))).scalar_one_or_none()
        if dst is None:
            raise ValueError(f"{to_type} {to_key!r} not found: synchronise it first")
        return src, to_type, dst, (label or ("primary" if self.contact else "related"))[:40 if not self.contact else 20]

    async def find(self, key, vals=None):
        src, to_type, dst, label = await self._ids(key)
        self._pending = (src, to_type, dst, label)
        q = (select(self.M).where(self.M.contact_id == src, self.M.object_type == to_type, self.M.object_id == dst, self.M.label == label)
             if self.contact else
             select(self.M).where(self.M.record_id == src, self.M.target_type == to_type, self.M.target_id == dst, self.M.label == label))
        return (await self.db.execute(q)).scalar_one_or_none()

    async def create(self, vals):
        src, to_type, dst, label = self._pending
        row = (self.M(contact_id=src, object_type=to_type, object_id=dst, label=label, created_at=_now()) if self.contact
               else self.M(record_id=src, target_type=to_type, target_id=dst, label=label))
        self.db.add(row)
        await self.db.flush()
        return row

    def get(self, obj, k):
        return None

    async def update(self, obj, changes):
        return None

    async def restore(self, obj, values):
        return None

    async def load(self, ident):
        return await self.db.get(self.M, uuid.UUID(ident))

    async def remove(self, obj):
        await self.db.delete(obj)
        await self.db.flush()

    def ident(self, obj):
        return str(obj.id)

    def deactivate(self, obj):
        return None


def adapter(db, spec, actor=None):
    kind = spec.get("adapter")
    if kind == "co":
        return CustomObjectAdapter(db, spec, actor=actor)
    if kind == "assoc":
        return AssocAdapter(db, spec)
    return ModelAdapter(db, spec)


def association_key(vals: dict) -> str:
    return "|".join([str(vals["from_key"]), str(vals["to_type"]), str(vals["to_key"]), str(vals.get("label") or "")])


# ── conflicts ────────────────────────────────────────────────────────────────

def record_conflicts(db: AsyncSession, sync_id, run_id, key: str, changes: dict) -> None:
    for f, (erp, src) in changes.items():
        db.add(SyncConflict(sync_id=sync_id, run_id=run_id, key=key, field=f,
                            source_value=None if src is None else str(src), erp_value=None if erp is None else str(erp)))


# ── export (outbound) ────────────────────────────────────────────────────────

async def export_rows(db: AsyncSession, spec: dict, since: Optional[datetime], opts: dict, actor=None, limit: int = 1000) -> list[tuple]:
    """[(updated_at, {field: value})] changed after `since`, with natural keys instead of ids; read-only for the ERP."""
    name = spec.get("export")
    if name:
        return await globals()["_export_" + name](db, since, limit)
    if spec.get("adapter") == "assoc":
        from app.services.data_sync_service import SyncError
        raise SyncError(422, "Associations are synchronised inbound only.")
    ad = adapter(db, spec, actor)
    q = select(ad.M).order_by(ad.M.updated_at)
    if spec.get("adapter") == "co":
        from app.services import custom_object_service as co
        q = co.visible(select(ad.M).where(ad.M.type_id == spec["type"].id).order_by(ad.M.updated_at), actor)
    if since:
        q = q.where(ad.M.updated_at > since)
    out = []
    for o in (await db.execute(q.limit(limit))).scalars():
        row = dict(o.data) if spec.get("adapter") == "co" else {k: getattr(o, k, None) for k in spec["fields"] if k not in (spec.get("refs") or {})}
        for fld, (col, tgt) in (spec.get("refs") or {}).items():
            from app.services.data_sync_service import TARGETS
            ts = TARGETS[tgt]
            rid = getattr(o, col, None)
            row[fld] = (await db.execute(select(getattr(_cls(ts["model"]), ts["key"])).where(_cls(ts["model"]).id == rid))).scalar_one_or_none() if rid else None
        out.append((o.updated_at, row))
    return out


async def _export_sales_orders(db, since, limit):
    from app.models.master import Product
    from app.models.sales import Customer, SalesOrder, SOLine
    q = select(SalesOrder, Customer.code).join(Customer, Customer.id == SalesOrder.customer_id).order_by(SalesOrder.updated_at)
    if since:
        q = q.where(SalesOrder.updated_at > since)
    out = []
    for so, ccode in (await db.execute(q.limit(limit))).all():
        lines = (await db.execute(select(Product.sku, SOLine.ordered_quantity, SOLine.unit_price).join(Product, Product.id == SOLine.product_id)
                                  .where(SOLine.so_id == so.id).order_by(SOLine.line_no))).all()
        out.append((so.updated_at, {"order_no": so.order_no, "customer_code": ccode, "order_date": so.order_date,
                                    "requested_delivery_date": so.requested_delivery_date, "currency": so.currency,
                                    "status": so.status.value, "notes": so.notes,
                                    "lines": [{"sku": s, "quantity": q_, "unit_price": p} for s, q_, p in lines]}))
    return out


async def _export_purchase_orders(db, since, limit):
    from app.models.master import Material, Product, Supplier
    from app.models.procurement import POLine, PurchaseOrder
    q = select(PurchaseOrder, Supplier.code).join(Supplier, Supplier.id == PurchaseOrder.supplier_id).order_by(PurchaseOrder.updated_at)
    if since:
        q = q.where(PurchaseOrder.updated_at > since)
    out = []
    for po, scode in (await db.execute(q.limit(limit))).all():
        lines = (await db.execute(select(Material.code, Product.sku, POLine.ordered_quantity, POLine.unit_price)
                                  .select_from(POLine).outerjoin(Material, Material.id == POLine.material_id)
                                  .outerjoin(Product, Product.id == POLine.product_id).where(POLine.po_id == po.id)
                                  .order_by(POLine.line_no))).all()
        out.append((po.updated_at, {"po_no": po.po_no, "supplier_code": scode, "order_date": po.order_date,
                                    "expected_delivery_date": po.expected_delivery_date, "currency": po.currency,
                                    "payment_terms": po.payment_terms, "status": po.status.value, "notes": po.notes,
                                    "lines": [{"material_code": m, "sku": s, "quantity": q_, "unit_price": p} for m, s, q_, p in lines]}))
    return out


async def _export_invoices(db, since, limit):
    from app.models.sales import Customer, Invoice, SalesOrder
    q = (select(Invoice, SalesOrder.order_no, Customer.code).join(SalesOrder, SalesOrder.id == Invoice.so_id)
         .join(Customer, Customer.id == Invoice.customer_id).order_by(Invoice.updated_at))
    if since:
        q = q.where(Invoice.updated_at > since)
    return [(i.updated_at, {"invoice_no": i.invoice_no, "order_no": o, "customer_code": c, "invoice_date": i.invoice_date,
                            "due_date": i.due_date, "status": i.status.value, "currency": i.currency, "subtotal": i.subtotal,
                            "tax_amount": i.tax_amount, "total_amount": i.total_amount, "paid_amount": i.paid_amount})
            for i, o, c in (await db.execute(q.limit(limit))).all()]


async def _export_stock(db, since, limit):
    from app.models.inventory import Stock
    from app.models.master import Material, Product, Warehouse
    q = (select(Stock, Product.sku, Material.code, Warehouse.code).select_from(Stock)
         .outerjoin(Product, Product.id == Stock.product_id).outerjoin(Material, Material.id == Stock.material_id)
         .join(Warehouse, Warehouse.id == Stock.warehouse_id).order_by(Stock.updated_at))
    if since:
        q = q.where(Stock.updated_at > since)
    return [(s.updated_at, {"stock_key": f"{w}:{sku or mc}:{s.lot_id or ''}", "sku": sku, "material_code": mc, "warehouse_code": w,
                            "quantity_on_hand": s.quantity_on_hand, "quantity_reserved": s.quantity_reserved,
                            "quantity_available": s.quantity_available, "is_blocked": s.is_blocked})
            for s, sku, mc, w in (await db.execute(q.limit(limit))).all()]


# ── transactional proposals ──────────────────────────────────────────────────

def _d(v, what):
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ValueError(f"{what} {v!r} is not a date")


SYSTEM_ACTORS = ("webhook", "scheduler")


async def accountable(db: AsyncSession, sync, user: str) -> str:
    """Who answers for a proposal: the person who ran it, or, for webhook/scheduler runs, the sync's owner (the last
    mapping editor if one is recorded, else its creator) so automation can never launder the two-person rule."""
    if user not in SYSTEM_ACTORS:
        return user
    return (await options(db, sync)).get("mapping_editor") or sync.created_by or user


async def stage(db: AsyncSession, sync, spec: dict, rows: list[dict], *, dry_run: bool, user: str, trigger: str, run,
                proposer: Optional[str] = None) -> dict:
    """Validate and stage inbound order rows (one row per line, grouped by the order number). → counts, diff, errors."""
    user = proposer or await accountable(db, sync, user)
    from app.services.data_sync_service import _jsonable, map_row
    key_f, line_f = spec["key"], set(spec["line_fields"])
    groups: dict[str, dict] = {}
    errors, counts = [], {"propose": 0, "duplicate": 0, "error": 0, "create": 0, "update": 0, "unchanged": 0, "skip": 0, "delete": 0}
    for i, raw in enumerate(rows, start=1):
        try:
            vals = map_row(sync, raw, spec)
            g = groups.setdefault(str(vals[key_f]), {"head": {}, "lines": [], "rows": []})
            head = {k: _jsonable(v) for k, v in vals.items() if k not in line_f}
            for k, v in head.items():
                if k in g["head"] and g["head"][k] != v and v not in (None, ""):
                    raise ValueError(f"{k} differs between lines of the same order")
                g["head"].setdefault(k, v)
            g["lines"].append({k: _jsonable(vals.get(k)) for k in line_f if vals.get(k) is not None})
            g["rows"].append(i)
        except (ValueError, TypeError, InvalidOperation) as e:
            counts["error"] += 1
            errors.append({"row": i, "error": str(e)})
    cache: dict = {}
    diff = []
    existing_model = _cls(spec["model"])
    for key, g in groups.items():
        try:
            await resolve(db, {"refs": spec["refs"]}, g["head"], cache)
            for ln in g["lines"]:
                if Decimal(str(ln.get("quantity", 0))) <= 0:
                    raise ValueError("quantity must be greater than zero")
                if spec["key"] == "order_no":
                    sku = ln.get("sku")
                    if not sku or (await db.execute(select(_cls(("app.models.master", "Product")).id).where(
                            _cls(("app.models.master", "Product")).sku == sku))).scalar_one_or_none() is None:
                        raise ValueError(f"product {sku!r} not found: synchronise products first")
                elif not (ln.get("material_code") or ln.get("sku")):
                    raise ValueError("each line needs a material_code or a sku")
            if (await db.execute(select(existing_model.id).where(getattr(existing_model, key_f) == key))).scalar_one_or_none():
                counts["duplicate"] += 1
                diff.append({"key": key, "action": "skip-exists", "reason": "this document number already exists in the ERP"})
                continue
        except (ValueError, InvalidOperation) as e:
            counts["error"] += 1
            errors.append({"row": g["rows"][0], "key": key, "error": str(e)})
            continue
        existing = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == sync.id, SyncProposal.key == key))).scalar_one_or_none()
        if existing is not None and existing.status in ("APPLIED", "PENDING") and existing.payload == {"head": g["head"], "lines": g["lines"]}:
            counts["duplicate"] += 1
            diff.append({"key": key, "action": "skip-staged", "status": existing.status})
            continue
        counts["propose"] += 1
        diff.append({"key": key, "action": "propose", "lines": len(g["lines"])})
        if not dry_run:
            payload = {"head": g["head"], "lines": g["lines"]}
            if existing is None:
                db.add(SyncProposal(sync_id=sync.id, run_id=run.id, target=sync.target, key=key, payload=payload,
                                    proposed_by=user[:100]))
            elif existing.status != "APPLIED":      # payload changed in place: payload_hash changes, so a stale approval is refused
                existing.payload, existing.status, existing.run_id, existing.error = payload, "PENDING", run.id, None
                existing.proposed_by, existing.decided_by, existing.decided_at = user[:100], None, None
    await db.flush()
    return {"counts": counts, "diff": diff, "errors": errors}


def payload_hash(p: SyncProposal) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(p.payload, sort_keys=True, default=str).encode()).hexdigest()


async def decide(db: AsyncSession, p: SyncProposal, approver, approve: bool, payload_hash_seen: Optional[str] = None) -> SyncProposal:
    """Approve (creates the DRAFT document through the domain) or reject. Nobody who proposed it, owns the sync or last
    edited its mapping approves it, and an approval must quote the hash of the payload the reviewer actually saw."""
    from fastapi import HTTPException
    from app.core.access_control import has_any_permission
    from app.services.data_sync_service import TARGETS
    spec = TARGETS[p.target]
    if p.status != "PENDING":
        raise HTTPException(409, f"This proposal is already {p.status}.")
    from app.models.data_sync import SyncDefinition
    sync = await db.get(SyncDefinition, p.sync_id)
    involved = {p.proposed_by, getattr(sync, "created_by", None), (await options(db, sync)).get("mapping_editor") if sync else None}
    if approver.username in involved - {None, ""}:
        raise HTTPException(403, "A different person must approve: you proposed, own or last edited the mapping of this sync.")
    if approve and payload_hash_seen != payload_hash(p):
        raise HTTPException(409, "The proposal changed after you opened it; reload it and review the new payload.")
    if not (approver.is_superuser or has_any_permission(approver, spec["perm"])):
        raise HTTPException(403, f"You may not create {p.target.replace('_', ' ')}.")
    p.decided_by, p.decided_at = approver.username, _now()
    if not approve:
        p.status = "REJECTED"
        return p
    try:
        async with db.begin_nested():
            p.applied_ref = str(await (_apply_so if p.target == "sales_orders" else _apply_po)(db, p, approver))
        p.status, p.error = "APPLIED", None
    except HTTPException as e:
        p.status, p.error = "FAILED", str(e.detail)[:500]
    except (ValueError, InvalidOperation) as e:
        p.status, p.error = "FAILED", str(e)[:500]
    return p


async def _apply_so(db, p, approver):
    from app.api.v1.endpoints.sales import _require_customer_action
    from app.crud import sales as crud
    from app.models.master import Product
    from app.models.sales import Customer, PaymentMethod, SalesOrder
    from app.services.commercial_access_service import ensure_commercial_action_allowed, inherit_commercial_scope
    h = p.payload["head"]
    customer = (await db.execute(select(Customer).where(Customer.code == h["customer_code"]))).scalar_one_or_none()
    if customer is None:
        raise ValueError(f"customer {h['customer_code']!r} not found")
    _require_customer_action(approver, customer, "create")
    lines = []
    for n, ln in enumerate(p.payload["lines"], start=1):
        prod = (await db.execute(select(Product).where(Product.sku == ln["sku"]))).scalar_one_or_none()
        if prod is None:
            raise ValueError(f"product {ln['sku']!r} not found")
        lines.append({"line_no": n, "product_id": prod.id, "ordered_quantity": Decimal(str(ln["quantity"])),
                      "unit": ln.get("unit") or "PCS",
                      "unit_price": Decimal(str(ln["unit_price"])) if ln.get("unit_price") is not None else (prod.selling_price or Decimal("0")),
                      "discount_pct": Decimal(str(ln.get("discount_pct") or 0)), "tax_rate": Decimal(str(ln.get("tax_rate") or 0))})
    data = {"order_no": h["order_no"], "customer_id": customer.id, "order_date": _d(h["order_date"], "order_date"),
            "requested_delivery_date": _d(h["requested_delivery_date"], "requested_delivery_date"),
            "currency": h.get("currency") or customer.currency or "USD", "notes": h.get("notes"),
            "payment_method": PaymentMethod.CASH}
    for f in ("company_id", "branch_id", "sales_region_id", "sales_team_id", "customer_group_id"):
        data[f] = getattr(customer, f, None)
    target = SalesOrder(**data)
    inherit_commercial_scope(target, customer)
    ensure_commercial_action_allowed(approver, target, "create", "sales")
    so = await crud.create_so(db, {**data, "lines": lines}, created_by_id=approver.id)   # DRAFT; confirming is a domain action
    return so.id


async def _apply_po(db, p, approver):
    from app.crud import procurement as crud
    from app.models.master import Material, Product, Supplier
    from app.models.procurement import PurchaseOrder
    from app.services import procurement_service as svc
    h = p.payload["head"]
    supplier = (await db.execute(select(Supplier).where(Supplier.code == h["supplier_code"]))).scalar_one_or_none()
    if supplier is None:
        raise ValueError(f"supplier {h['supplier_code']!r} not found")
    od, dd = _d(h["order_date"], "order_date"), _d(h["expected_delivery_date"], "expected_delivery_date")
    data = {"po_no": h["po_no"], "supplier_id": supplier.id, "order_date": od, "expected_delivery_date": dd,
            "currency": h.get("currency") or "USD", "payment_terms": h.get("payment_terms"), "notes": h.get("notes")}
    target = PurchaseOrder(**data)
    svc.ensure_procurement_action_allowed(approver, target, "create")
    blocked = svc.supplier_procurement_block_reason(supplier, start_date=od, end_date=dd)
    if blocked:
        raise ValueError(blocked)
    lines = []
    for n, ln in enumerate(p.payload["lines"], start=1):
        mat = (await db.execute(select(Material).where(Material.code == ln["material_code"]))).scalar_one_or_none() if ln.get("material_code") else None
        prod = (await db.execute(select(Product).where(Product.sku == ln["sku"]))).scalar_one_or_none() if ln.get("sku") else None
        if mat is None and prod is None:
            raise ValueError(f"line {n}: material or product not found: synchronise materials/products first")
        lines.append({"line_no": n, "material_id": mat.id if mat else None, "product_id": prod.id if (prod and not mat) else None,
                      "ordered_quantity": Decimal(str(ln["quantity"])), "unit": ln.get("unit") or "KG",
                      "unit_price": Decimal(str(ln.get("unit_price") or 0)), "tax_rate": Decimal(str(ln.get("tax_rate") or 0))})
    po = await crud.create_po(db, {**data, "lines": lines}, approver.id)               # DRAFT; approval/receipt stay domain flows
    return po.id


# ── reconciliation ───────────────────────────────────────────────────────────

async def reconcile_rows(db: AsyncSession, sync, spec: dict, rows: list[dict], actor=None) -> dict:
    """Source rows vs the ERP (no writes): only in source, only in ERP, and field differences."""
    from app.services.data_sync_service import _jsonable, map_row
    if spec.get("mode") == "read_only":
        from app.services.data_sync_service import SyncError
        raise SyncError(409, "Reconcile read-only targets with their own check (stock/GL), not with source rows.")
    if spec.get("mode") == "propose" or spec.get("adapter") == "assoc":
        from app.services.data_sync_service import SyncError
        raise SyncError(422, "Row reconciliation applies to master data and custom objects.")
    ad = adapter(db, spec, actor)
    src: dict[str, dict] = {}
    bad = []
    cache: dict = {}
    for i, raw in enumerate(rows, start=1):
        try:
            v = await resolve(db, spec, map_row(sync, raw, spec), cache)
            src[str(v[spec["key"]])] = v
        except (ValueError, TypeError, InvalidOperation) as e:
            bad.append({"row": i, "error": str(e)})
    missing_in_erp, different = [], []
    for k, v in src.items():
        o = await ad.find(k)
        if o is None:
            missing_in_erp.append(k)
            continue
        d = {f: {"erp": _jsonable(ad.get(o, f)), "source": _jsonable(x)} for f, x in v.items() if _jsonable(ad.get(o, f)) != _jsonable(x)}
        if d:
            different.append({"key": k, "fields": d})
    return {"source_rows": len(src), "invalid_rows": bad[:50], "only_in_source": missing_in_erp[:200], "different": different[:200],
            "matches": len(src) - len(missing_in_erp) - len(different), "balanced": not (missing_in_erp or different or bad)}


async def reconcile_stock(db: AsyncSession) -> dict:
    """On-hand per warehouse/item/lot against the movement ledger (receipts in, issues out). Differences are reported,
    never corrected here: a correction is a counted adjustment document."""
    from app.models.inventory import Stock, StockMovement
    inc = {(r[0], r[1], r[2], r[3]): r[4] for r in (await db.execute(
        select(StockMovement.destination_warehouse_id, StockMovement.product_id, StockMovement.material_id, StockMovement.lot_id,
               func.sum(StockMovement.quantity)).where(StockMovement.destination_warehouse_id.is_not(None))
        .group_by(StockMovement.destination_warehouse_id, StockMovement.product_id, StockMovement.material_id, StockMovement.lot_id))).all()}
    out = {(r[0], r[1], r[2], r[3]): r[4] for r in (await db.execute(
        select(StockMovement.source_warehouse_id, StockMovement.product_id, StockMovement.material_id, StockMovement.lot_id,
               func.sum(StockMovement.quantity)).where(StockMovement.source_warehouse_id.is_not(None))
        .group_by(StockMovement.source_warehouse_id, StockMovement.product_id, StockMovement.material_id, StockMovement.lot_id))).all()}
    diffs, n = [], 0
    for s in (await db.execute(select(Stock))).scalars():
        n += 1
        k = (s.warehouse_id, s.product_id, s.material_id, s.lot_id)
        ledger = (inc.get(k) or Decimal(0)) - (out.get(k) or Decimal(0))
        if Decimal(s.quantity_on_hand) != ledger:
            diffs.append({"stock_id": str(s.id), "on_hand": str(s.quantity_on_hand), "ledger": str(ledger),
                          "difference": str(Decimal(s.quantity_on_hand) - ledger)})
    return {"stock_rows": n, "differences": diffs[:200], "difference_count": len(diffs), "balanced": not diffs}


async def reconcile_invoices(db: AsyncSession) -> dict:
    """Issued invoices against the general ledger: a posted entry for the invoice must balance and match the invoice total."""
    from app.models.finance import JournalEntry, JournalLine, JournalStatus
    from app.models.sales import Invoice, InvoiceStatus
    problems, n = [], 0
    for inv in (await db.execute(select(Invoice).where(Invoice.status != InvoiceStatus.DRAFT, Invoice.status != InvoiceStatus.CANCELLED))).scalars():
        n += 1
        if inv.total_amount != inv.subtotal + inv.tax_amount:
            problems.append({"invoice_no": inv.invoice_no, "issue": "total is not subtotal + tax"})
        je = (await db.execute(select(JournalEntry).where(JournalEntry.source_id == inv.id, JournalEntry.source_module == "sales",
                                                          JournalEntry.status == JournalStatus.POSTED))).scalars().first()
        if je is None:
            problems.append({"invoice_no": inv.invoice_no, "issue": "no posted general-ledger entry"})
            continue
        debit, credit = (await db.execute(select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0))
                                          .where(JournalLine.entry_id == je.id))).one()
        if debit != credit:
            problems.append({"invoice_no": inv.invoice_no, "issue": "journal entry does not balance"})
        elif debit != inv.total_amount:
            problems.append({"invoice_no": inv.invoice_no, "issue": f"journal total {debit} differs from invoice total {inv.total_amount}"})
    return {"invoices_checked": n, "problems": problems[:200], "problem_count": len(problems), "balanced": not problems}


# ── conflict resolution ──────────────────────────────────────────────────────

async def resolve_conflict(db: AsyncSession, c: SyncConflict, sync, spec: dict, choice: str, user) -> dict:
    """SOURCE applies the source's value to the ERP record now; ERP keeps the ERP value. Either way the conflict is closed."""
    from app.services.data_sync_service import SyncError
    if c.resolution:
        raise SyncError(409, "This conflict is already resolved.")
    if choice == "SOURCE":
        ad = adapter(db, spec, user)
        obj = await ad.find(c.key)
        if obj is None:
            raise SyncError(404, "The ERP record no longer exists.")
        from app.services.data_sync_service import check_type
        if c.field not in spec["fields"] or c.field in (spec.get("refs") or {}):
            raise SyncError(422, f"{c.field} is a reference; change it in the ERP record itself.")
        try:
            v = check_type(spec["fields"][c.field], c.source_value)
            v = (await resolve(db, spec, {c.field: v}, {}))[c.field]
        except (ValueError, TypeError, InvalidOperation) as e:
            raise SyncError(422, str(e))
        try:
            await ad.update(obj, {c.field: v})
        except ValueError as e:
            raise SyncError(422, str(e))
    c.resolution, c.resolved_by, c.resolved_at = choice, user.username, _now()
    return {"id": str(c.id), "resolution": choice}
