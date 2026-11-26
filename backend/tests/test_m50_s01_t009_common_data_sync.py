"""M50.S01.T009 common no-code data sync across ERP objects (unit; DB part needs M50_DB=1).

Unit: the registry covers the listed objects, dependency order, stock/invoices are read-only (inbound refused at definition),
typed enum/date fields. DB: master data synced in dependency order (suppliers -> materials -> products -> customers ->
tickets/deals) with typed references, dry run writes nothing, rollback and replay; conflicts recorded and resolved;
custom objects and associations; sales/purchase orders only staged, approved by a different person with the create right
and created as DRAFTs through the domain; stock and invoices exported read-only and reconciled; refusals are audited.
"""
import os
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import data_sync_service as dss
from app.services import m50_sync_registry as reg

DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
LISTED = {"customers", "crm_contacts", "suppliers", "products", "materials", "sales_orders", "purchase_orders", "invoices", "stock",
          "deals", "tickets", "custom_objects", "associations"}


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_registry_covers_every_listed_object_in_dependency_order():
    assert LISTED <= set(dss.TARGETS)
    order = reg.order(list(dss.TARGETS))
    for t, deps in reg.DEPENDS.items():
        for d in deps:
            assert order.index(d) < order.index(t), (d, t)
    assert order.index("suppliers") < order.index("materials") < order.index("purchase_orders")
    assert order.index("customers") < order.index("sales_orders") < order.index("invoices")
    # only dependencies the caller asked about are returned, still dependency-first
    assert reg.order(["invoices", "customers", "sales_orders"]) == ["customers", "sales_orders", "invoices"]


def test_stock_and_invoices_are_read_only_and_orders_are_proposals():
    assert dss.TARGETS["stock"]["mode"] == dss.TARGETS["invoices"]["mode"] == "read_only"
    assert dss.TARGETS["sales_orders"]["mode"] == dss.TARGETS["purchase_orders"]["mode"] == "propose"
    for t in ("stock", "invoices"):
        with pytest.raises(dss.SyncError) as e:
            dss.validate_mapping(t, dss.TARGETS[t]["key"], [{"target": dss.TARGETS[t]["key"], "source": "k"}], direction="IN")
        assert e.value.status == 409 and "read-only" in str(e.value)
    # reading (OUT) is fine, including the joined natural keys
    dss.validate_mapping("stock", "stock_key", [{"target": "sku", "source": "sku"}, {"target": "quantity_on_hand", "source": "qty"}],
                         direction="OUT")
    dss.validate_mapping("sales_orders", "order_no", [{"target": "order_no", "source": "no"}, {"target": "lines", "source": "lines"}],
                         direction="OUT")
    with pytest.raises(dss.SyncError):
        dss.validate_mapping("sales_orders", "order_no", [{"target": "order_no", "source": "no"}, {"target": "lines", "source": "l"}],
                             direction="IN")                       # `lines` is an export-only field
    with pytest.raises(dss.SyncError):
        dss.validate_mapping("products", "sku", [{"target": "sku", "source": "s"}, {"target": "hacked", "source": "x"},
                                                 {"target": "name", "source": "n"}, {"target": "category", "source": "c"}])


def test_typed_fields_enum_and_date():
    assert dss.check_type("enum:ProductCategory", "household") == "HOUSEHOLD"
    assert dss.check_type("enum:TicketPriority", "high") == "HIGH"
    with pytest.raises(ValueError):
        dss.check_type("enum:ProductCategory", "slime")
    import datetime
    assert dss.check_type("date", "2026-11-30") == datetime.date(2026, 11, 30)
    with pytest.raises(ValueError):
        dss.check_type("date", "30/11/2026")


def test_read_only_refusal_for_a_person_defining_or_running_inbound():
    from app.api.v1.endpoints.data_sync import _may_run
    admin = SimpleNamespace(is_superuser=True, roles=[], access_scopes=[])
    with pytest.raises(HTTPException) as e:
        _may_run(admin, SimpleNamespace(target="stock", direction="IN", mapping=[]))
    assert e.value.status_code == 409                                 # even a superuser cannot write stock through a sync
    clerk = SimpleNamespace(is_superuser=False, access_scopes=[], roles=[SimpleNamespace(
        name="r", is_active=True, access_scopes=[], permissions=[SimpleNamespace(code="sales.view", is_active=True)])])
    with pytest.raises(HTTPException) as e:
        _may_run(clerk, SimpleNamespace(target="stock", direction="OUT", mapping=[]))
    assert e.value.status_code == 403                                 # exporting stock needs the inventory view right


# ── DB ───────────────────────────────────────────────────────────────────────

async def _user(db, tag, perms=(), superuser=False):
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password="x", is_active=True, is_superuser=superuser)
    db.add(u)
    await db.flush()
    plist = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in perms]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=superuser,
                           access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=plist, access_scopes=[])])


def _S():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db.session import engine
    return async_sessionmaker(engine, expire_on_commit=False)()


def _sync(name, target, key, mapping, **kw):
    from app.models.data_sync import SyncDefinition
    return SyncDefinition(name=name, **{"source_kind": "UPLOAD", **kw}, target=target, key_field=key, mapping=mapping, history=[])


def _m(*pairs, **tf):
    return [{"target": t, "source": t if s is None else s, "transforms": tf.get(t, [])} for t, s in pairs]


@DB
@pytest.mark.asyncio
async def test_master_data_chain_in_dependency_order_with_refs_dry_run_rollback_replay():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.helpdesk import HelpdeskTicket
    from app.models.master import Material, Product, Supplier
    from app.models.sales import Customer
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        sup = _sync(f"sup {s}", "suppliers", "code", _m(("code", None), ("name", None), ("email", None)))
        mat = _sync(f"mat {s}", "materials", "code", _m(("code", None), ("name", None), ("material_type", None), ("uom", None), ("supplier_code", None)))
        prd = _sync(f"prd {s}", "products", "sku", _m(("sku", None), ("name", None), ("category", None), ("uom", None), ("selling_price", None)))
        cus = _sync(f"cus {s}", "customers", "code", _m(("code", None), ("name", None)))
        tix = _sync(f"tix {s}", "tickets", "ticket_no", _m(("ticket_no", None), ("subject", None), ("priority", None), ("customer_code", None)))
        db.add_all([sup, mat, prd, cus, tix])
        await db.commit()
        # a material before its supplier: refused row that names the missing dependency, nothing written
        mrows = [{"code": f"MAT-{s}", "name": "Povu surfactant base", "material_type": "raw", "uom": "kg", "supplier_code": f"SUP-{s}"}]
        r0 = await dss.run_in(db, mat, mrows, dry_run=False, user="t")
        assert r0.counts["error"] == 1 and "synchronise suppliers first" in r0.errors[0]["error"]
        await db.commit()
        # suppliers
        r = await dss.run_in(db, sup, [{"code": f"SUP-{s}", "name": "Chem Supplies Ltd", "email": "orders@povu-demo.test"}], dry_run=True, user="t")
        assert r.counts["create"] == 1
        await db.rollback()
        assert (await db.execute(select(Supplier).where(Supplier.code == f"SUP-{s}"))).first() is None      # dry run wrote nothing
        sup = (await db.execute(select(type(sup)).where(type(sup).name == f"sup {s}"))).scalar_one()
        r = await dss.run_in(db, sup, [{"code": f"SUP-{s}", "name": "Chem Supplies Ltd", "email": "orders@povu-demo.test"}], dry_run=False, user="t")
        await db.commit()
        supplier = (await db.execute(select(Supplier).where(Supplier.code == f"SUP-{s}"))).scalar_one()
        # materials now resolve the supplier by code
        mat = (await db.execute(select(type(mat)).where(type(mat).name == f"mat {s}"))).scalar_one()
        r = await dss.run_in(db, mat, mrows, dry_run=False, user="t")
        await db.commit()
        m = (await db.execute(select(Material).where(Material.code == f"MAT-{s}"))).scalar_one()
        assert r.counts["create"] == 1 and m.supplier_id == supplier.id and m.material_type.value == "RAW" and m.uom.value == "KG"
        # products with typed enum/number
        prd = (await db.execute(select(type(prd)).where(type(prd).name == f"prd {s}"))).scalar_one()
        prows = [{"sku": f"POVU-ALC-{s}", "name": "POVU AllClean 1 L", "category": "household", "uom": "pcs", "selling_price": "350.00"},
                 {"sku": f"POVU-HWP-{s}", "name": "POVU Hand Wash Powder 1 kg Pouch", "category": "nonsense", "uom": "pcs", "selling_price": "1"}]
        r = await dss.run_in(db, prd, prows, dry_run=False, user="t")
        await db.commit()
        assert r.counts["create"] == 1 and r.counts["error"] == 1 and "not one of" in r.errors[0]["error"]
        p = (await db.execute(select(Product).where(Product.sku == f"POVU-ALC-{s}"))).scalar_one()
        assert p.category.value == "HOUSEHOLD" and p.selling_price == Decimal("350.00")
        # rollback removes the created product; replay recreates it from the stored input
        out = await dss.rollback(db, r, "t")
        await db.commit()
        assert out["removed"] == 1
        assert (await db.execute(select(Product).where(Product.sku == f"POVU-ALC-{s}"))).first() is None
        rp = await dss.run_in(db, prd, r.input, dry_run=False, user="t", trigger="REPLAY", full_snapshot=False)
        await db.commit()
        assert rp.counts["create"] == 1
        # customers then tickets with the customer reference
        cus = (await db.execute(select(type(cus)).where(type(cus).name == f"cus {s}"))).scalar_one()
        await dss.run_in(db, cus, [{"code": f"DUKA-{s}", "name": "Duka Moja"}], dry_run=False, user="t")
        tix = (await db.execute(select(type(tix)).where(type(tix).name == f"tix {s}"))).scalar_one()
        r = await dss.run_in(db, tix, [{"ticket_no": f"TK-{s}", "subject": "Late delivery", "priority": "high", "customer_code": f"DUKA-{s}"}],
                             dry_run=False, user="t")
        await db.commit()
        t = (await db.execute(select(HelpdeskTicket).where(HelpdeskTicket.ticket_no == f"TK-{s}"))).scalar_one()
        c = (await db.execute(select(Customer).where(Customer.code == f"DUKA-{s}"))).scalar_one()
        assert t.customer_id == c.id and t.priority.value == "HIGH"


@DB
@pytest.mark.asyncio
async def test_conflicts_are_recorded_and_resolved_and_deals_are_synced():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord
    from app.models.m50_data_sso import SyncConflict
    from app.models.sales import Customer
    from app.services import m50_sync as m50
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        admin = await _user(db, "adm", ("crm.edit_all",), superuser=True)
        cus = _sync(f"cus {s}", "customers", "code", _m(("code", None), ("name", None), ("city", None)), conflict_rule="skip")
        db.add(cus)
        await db.commit()
        await dss.run_in(db, cus, [{"code": f"C-{s}", "name": "Kibanda", "city": "Nairobi"}], dry_run=False, user="t")
        r = await dss.run_in(db, cus, [{"code": f"C-{s}", "name": "Kibanda", "city": "Mombasa"}], dry_run=False, user="t")
        await db.commit()
        assert r.counts["skip"] == 1
        c = (await db.execute(select(SyncConflict).where(SyncConflict.run_id == r.id))).scalar_one()
        assert (c.field, c.erp_value, c.source_value) == ("city", "Nairobi", "Mombasa")
        spec = await m50.spec_for(db, "customers", {})
        await m50.resolve_conflict(db, c, cus, spec, "SOURCE", admin)
        await db.commit()
        cust = (await db.execute(select(Customer).where(Customer.code == f"C-{s}"))).scalar_one()
        assert cust.city == "Mombasa" and c.resolution == "SOURCE"
        # deals: typed date/number, record type defaulted
        deals = _sync(f"deals {s}", "deals", "opportunity_code", _m(("opportunity_code", None), ("company_name", None), ("expected_revenue", None),
                                                                     ("expected_close_date", None)))
        db.add(deals)
        await db.commit()
        r = await dss.run_in(db, deals, [{"opportunity_code": f"OPP-{s}", "company_name": "Duka Kubwa", "expected_revenue": "12,500.00",
                                           "expected_close_date": "2026-12-15"}], dry_run=False, user="t")
        await db.commit()
        d = (await db.execute(select(CRMRecord).where(CRMRecord.opportunity_code == f"OPP-{s}"))).scalar_one()
        assert r.counts["create"] == 1 and d.record_type.value == "OPPORTUNITY" and d.expected_revenue == Decimal("12500.00")


@DB
@pytest.mark.asyncio
async def test_custom_objects_and_associations():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMContactAssociation
    from app.models.custom_objects import CustomObjectAssociation, CustomObjectRecord, CustomObjectType
    from app.models.sales import Customer
    s = uuid.uuid4().hex[:5].lower()
    async with _S() as db:
        admin = await _user(db, "adm", ("crm.edit_all",), superuser=True)
        t = CustomObjectType(key=f"shelf_{s}", label="Shelf", label_plural="Shelves", display_field="tag", created_by="t",
                             fields=[{"key": "tag", "label": "Tag", "type": "text", "required": True, "unique": True},
                                     {"key": "bays", "label": "Bays", "type": "number", "required": False, "unique": False}])
        db.add(t)
        db.add(Customer(code=f"K-{s}", name="Kibanda Kuu"))
        await db.flush()
        from app.services import m50_sync as m50
        co_sync = _sync(f"co {s}", "custom_objects", "tag", _m(("tag", None), ("bays", None)))
        db.add(co_sync)
        await db.flush()
        await m50.set_options(db, co_sync.id, {"custom_type": f"shelf_{s}"})
        await db.commit()
        r = await dss.run_in(db, co_sync, [{"tag": f"SH-{s}", "bays": "4"}], dry_run=False, user="t", actor=admin)
        await db.commit()
        assert r.counts["create"] == 1
        rec = (await db.execute(select(CustomObjectRecord).where(CustomObjectRecord.type_id == t.id))).scalar_one()
        assert rec.data["tag"] == f"SH-{s}" and rec.data["bays"] == 4
        rec_id = rec.id
        r = await dss.run_in(db, co_sync, [{"tag": f"SH-{s}", "bays": "6"}], dry_run=False, user="t", actor=admin)
        assert r.counts["update"] == 1
        await db.commit()
        await db.refresh(rec)
        assert rec.data["bays"] == 6
        # a custom-object sync with no signed-in user is refused (object-type roles must apply)
        with pytest.raises(dss.SyncError) as e:
            await dss.run_in(db, co_sync, [{"tag": "X", "bays": "1"}], dry_run=True, user="webhook")
        assert e.value.status == 403
        await db.rollback()
        # associations: shelf -> customer, contact -> customer
        link = _sync(f"link {s}", "associations", "link", _m(("from_key", None), ("to_type", None), ("to_key", None), ("label", None)))
        db.add(link)
        await db.flush()
        await m50.set_options(db, link.id, {"from": f"custom:shelf_{s}"})
        con = CRMContact(full_name="Wanjiru Duka", email=f"wanjiru-{s}@povu-demo.test")
        db.add(con)
        await db.flush()
        con_id = con.id
        clink = _sync(f"clink {s}", "associations", "link", _m(("from_key", None), ("to_type", None), ("to_key", None), ("label", None)))
        db.add(clink)
        await db.flush()
        await m50.set_options(db, clink.id, {"from": "contact"})
        await db.commit()
        rows = [{"from_key": f"SH-{s}", "to_type": "customer", "to_key": f"K-{s}", "label": "placed_at"}]
        r = await dss.run_in(db, link, rows, dry_run=False, user="t", actor=admin)
        await db.commit()
        assert r.counts["create"] == 1
        assert (await db.execute(select(CustomObjectAssociation).where(CustomObjectAssociation.record_id == rec_id))).scalar_one().label == "placed_at"
        bad = await dss.run_in(db, link, [{"from_key": f"SH-{s}", "to_type": "customer", "to_key": "NOPE", "label": "x"}], dry_run=False, user="t", actor=admin)
        assert bad.counts["error"] == 1 and "synchronise it first" in bad.errors[0]["error"]
        r = await dss.run_in(db, clink, [{"from_key": f"wanjiru-{s}@povu-demo.test", "to_type": "customer", "to_key": f"K-{s}", "label": "primary"}],
                             dry_run=False, user="t", actor=admin)
        await db.commit()
        assert (await db.execute(select(CRMContactAssociation).where(CRMContactAssociation.contact_id == con_id))).scalar_one().object_type == "customer"
        out = await dss.rollback(db, r, "t", actor=admin)
        await db.commit()
        assert out["removed"] == 1
        assert (await db.execute(select(CRMContactAssociation).where(CRMContactAssociation.contact_id == con_id))).first() is None


@DB
@pytest.mark.asyncio
async def test_orders_are_staged_two_person_approved_and_created_as_drafts_through_the_domain():
    from fastapi import HTTPException as HE
    from sqlalchemy import select
    from app.api.v1.endpoints import data_sync as api
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.master import Material, Product, Supplier
    from app.models.m50_data_sso import SyncProposal
    from app.models.procurement import PurchaseOrder
    from app.models.sales import Customer, SalesOrder, SOStatus
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        db.add_all([Customer(code=f"OC-{s}", name="Duka Order"), Product(sku=f"POVU-ALC-{s}", name="POVU AllClean 1 L", category="HOUSEHOLD", selling_price=Decimal("350")),
                    Supplier(code=f"OS-{s}", name="Pack Supplies"), Material(code=f"OM-{s}", name="Pouch film", material_type="PACKAGING")])
        so_sync = _sync(f"so {s}", "sales_orders", "order_no", _m(("order_no", None), ("customer_code", None), ("order_date", None),
                                                                  ("requested_delivery_date", None), ("sku", None), ("quantity", None), ("unit_price", None)))
        po_sync = _sync(f"po {s}", "purchase_orders", "po_no", _m(("po_no", None), ("supplier_code", None), ("order_date", None),
                                                                  ("expected_delivery_date", None), ("material_code", None), ("quantity", None), ("unit_price", None)))
        proposer = await _user(db, "prop", ("sales.create", "sales.create_all", "procurement.create"))
        approver = await _user(db, "appr", ("sales.create", "sales.create_all", "procurement.create"))
        nobody = await _user(db, "none", ("sales.view",))
        db.add_all([so_sync, po_sync])
        await db.commit()
        so_id, po_id = so_sync.id, po_sync.id
        rows = [{"order_no": f"SO-{s}", "customer_code": f"OC-{s}", "order_date": "2026-11-30", "requested_delivery_date": "2026-12-05",
                 "sku": f"POVU-ALC-{s}", "quantity": "10", "unit_price": "340"},
                {"order_no": f"SO-{s}", "customer_code": f"OC-{s}", "order_date": "2026-11-30", "requested_delivery_date": "2026-12-05",
                 "sku": f"POVU-ALC-{s}", "quantity": "5", "unit_price": "340"},
                {"order_no": f"SO-BAD-{s}", "customer_code": "NOPE", "order_date": "2026-11-30", "requested_delivery_date": "2026-12-05",
                 "sku": f"POVU-ALC-{s}", "quantity": "1"}]
        dry = await dss.run_in(db, so_sync, rows, dry_run=True, user=proposer.username)
        assert dry.counts["propose"] == 1 and dry.counts["error"] == 1
        await db.rollback()
        assert (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == so_id))).first() is None
        r = await dss.run_in(db, so_sync, rows, dry_run=False, user=proposer.username)
        await db.commit()
        assert r.counts["propose"] == 1 and r.counts["create"] == 0
        assert (await db.execute(select(SalesOrder).where(SalesOrder.order_no == f"SO-{s}"))).first() is None   # nothing written yet
        prop = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == so_id))).scalar_one()
        assert prop.status == "PENDING" and len(prop.payload["lines"]) == 2
        prop_id = prop.id
        # the proposer may not approve; someone without the create right may not either
        with pytest.raises(HE) as e:
            await api.approve_proposal(prop_id, db, proposer)
        assert e.value.status_code == 403 and "different person" in e.value.detail
        await db.rollback()
        with pytest.raises(HE) as e:
            await api.approve_proposal(prop_id, db, nobody)
        assert e.value.status_code == 403
        await db.rollback()
        out = await api.approve_proposal(prop_id, db, approver)
        assert out["status"] == "APPLIED"
        so = (await db.execute(select(SalesOrder).where(SalesOrder.order_no == f"SO-{s}"))).scalar_one()
        assert so.status == SOStatus.DRAFT and so.created_by_id == approver.id
        from app.models.sales import SOLine
        assert len((await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalars().all()) == 2
        # replaying the same rows neither duplicates nor re-proposes
        again = await dss.run_in(db, so_sync, rows, dry_run=False, user=proposer.username, full_snapshot=False)
        assert again.counts["propose"] == 0 and again.counts["duplicate"] == 1
        # a staged run cannot be "rolled back" as if it wrote data
        await db.refresh(r)
        with pytest.raises(dss.SyncError) as e:
            await dss.rollback(db, r, "t")
        assert e.value.status == 409
        ev = (await db.execute(select(AuditLog).where(AuditLog.event_type == "DATA_SYNC_PROPOSAL_APPROVED",
                                                      AuditLog.target_id == str(prop_id)))).scalar_one()
        assert ev.details["applied_ref"] == str(so.id)
        # purchase order: reject path then approve path
        prow = [{"po_no": f"PO-{s}", "supplier_code": f"OS-{s}", "order_date": "2026-11-30", "expected_delivery_date": "2026-12-10",
                 "material_code": f"OM-{s}", "quantity": "200", "unit_price": "12.5"}]
        await dss.run_in(db, po_sync, prow, dry_run=False, user=proposer.username)
        await db.commit()
        pp = (await db.execute(select(SyncProposal).where(SyncProposal.sync_id == po_id))).scalar_one()
        pp_id = pp.id
        assert (await api.reject_proposal(pp_id, db, approver))["status"] == "REJECTED"
        await dss.run_in(db, po_sync, prow, dry_run=False, user=proposer.username)      # re-staging a rejected one is allowed
        await db.commit()
        await db.refresh(pp)
        assert pp.status == "PENDING"
        assert (await api.approve_proposal(pp_id, db, approver))["status"] == "APPLIED"
        po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.po_no == f"PO-{s}"))).scalar_one()
        assert po.status.value == "DRAFT"


@DB
@pytest.mark.asyncio
async def test_stock_and_invoices_read_only_export_and_reconciliation():
    import httpx
    from fastapi import FastAPI, Request
    from sqlalchemy import select
    from app.api.v1.endpoints import data_sync as api
    from app.core import provider_http
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.inventory import Stock, StockType
    from app.models.master import Product, Warehouse
    s = uuid.uuid4().hex[:5].upper()
    async with _S() as db:
        wh = Warehouse(code=f"WH-{s}", name="Main", warehouse_type="FINISHED_GOODS")
        p = Product(sku=f"POVU-ALC-{s}", name="POVU AllClean 1 L", category="HOUSEHOLD")
        db.add_all([wh, p])
        await db.flush()
        db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=wh.id, product_id=p.id, quantity_on_hand=Decimal("40"),
                     quantity_available=Decimal("40")))
        stock_out = _sync(f"stock {s}", "stock", "stock_key", _m(("sku", "item"), ("warehouse_code", "wh"), ("quantity_on_hand", "qty")),
                          direction="OUT", source_kind="HTTP_JSON", source_url="http://fixture.test/inbox")
        stock_in = _sync(f"stock-in {s}", "stock", "stock_key", _m(("sku", "item"), ("quantity_on_hand", "qty")))   # direct DB, as a stored legacy row
        reader = await _user(db, "rd", ("inventory.view",))
        sales_only = await _user(db, "so", ("sales.view",))
        db.add_all([stock_out, stock_in])
        await db.commit()
        p_id, out_id = p.id, stock_out.id
        # defining an inbound stock sync through the API is refused
        body = api.SyncIn(name=f"x {s}", source_kind="UPLOAD", target="stock", key_field="stock_key", mapping=[{"target": "sku", "source": "a"}])
        admin = await _user(db, "adm", ("crm.edit_all",), superuser=True)
        with pytest.raises(HE := HTTPException) as e:
            await api.create(body, db, admin)
        assert e.value.status_code == 409 and "read-only" in e.value.detail
        await db.rollback()
        # a stored inbound definition still cannot write stock when run
        with pytest.raises(dss.SyncError) as e:
            await dss.run_in(db, stock_in, [{"item": "x", "qty": "9"}], dry_run=False, user="t")
        assert e.value.status == 409
        await db.rollback()
        assert (await db.execute(select(Stock.quantity_on_hand).where(Stock.product_id == p_id))).scalar_one() == Decimal("40")
        # outbound read is allowed for the inventory viewer, refused for a sales-only user
        got = []
        fx = FastAPI()

        @fx.post("/inbox")
        async def inbox(request: Request):
            got.append(await request.json())
            return {"ok": True}
        monkey = settings.PROVIDER_EGRESS
        settings.PROVIDER_EGRESS = "local"
        provider_http.set_test_transport(httpx.ASGITransport(app=fx))
        try:
            with pytest.raises(HTTPException) as e:
                await api.run(out_id, api.RunIn(dry_run=False), db, sales_only)
            assert e.value.status_code == 403
            await db.rollback()
            out = await api.run(out_id, api.RunIn(dry_run=False), db, reader)
        finally:
            provider_http.set_test_transport(None)
            settings.PROVIDER_EGRESS = monkey
        assert out["status"] == "DONE"
        mine = [r for r in got[0]["rows"] if r["item"] == f"POVU-ALC-{s}"]
        assert mine == [{"item": f"POVU-ALC-{s}", "wh": f"WH-{s}", "qty": "40"}]
        assert (await db.execute(select(AuditLog).where(AuditLog.event_type == "DATA_SYNC_RUN"))).first() is not None
        # reconciliation reports the on-hand that has no movement ledger behind it, and never corrects it
        rec = await api.reconcile_stock(db, reader)
        assert rec["balanced"] is False and any(d["on_hand"] == "40.000" and d["ledger"] == "0" for d in rec["differences"])
        inv = await api.reconcile_invoices(db, await _user(db, "fin", ("finance.view",)))
        assert "problems" in inv and "invoices_checked" in inv
        with pytest.raises(HTTPException) as e:
            await api.reconcile_invoices(db, sales_only)
        assert e.value.status_code == 403
        await db.rollback()
