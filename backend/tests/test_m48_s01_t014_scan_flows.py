"""M48.S01.T014 (remediates M37.S04.T008 / M40.S01.T003): barcode scans in goods receipt, stock transfer and cycle count.

The warehouse screens resolve a scanned code with GET /lookup/{kind}?search=<code>&exact=true (the same resolver
as pick/putaway) and then submit the record it returned. Each test drives that real path through the app with a
real session cookie and synthetic POVU data: a correct scan moves stock or records a count; an unknown, partial,
wrong or duplicate scan is refused; rights are enforced. Needs M48_DB=1 and DATABASE_URL on a disposable database.
"""
import os
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
pytestmark = DB


@pytest.fixture(autouse=True)
async def _dispose_engine(monkeypatch):
    from app.core import token_blocklist
    monkeypatch.setattr(token_blocklist, "_get_redis", lambda: None)     # in-memory blocklist: never the dev Redis
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _guard_db():
    from app.db.session import engine
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.port != 5432, "never the dev database"


async def _person(db, *codes):
    """Staff user with exactly these rights; returns a session cookie dict."""
    from app.core.config import settings
    from app.core.security import create_access_token
    from app.models.role import Permission, Role
    from app.models.user import User
    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".", 1)[1], is_active=True)
            db.add(p)
            await db.flush()
        perms.append(p)
    tag = uuid.uuid4().hex
    u = User(username=f"m48scan{tag}", email=f"m48scan-{tag[:12]}@povu-demo.test", full_name="POVU warehouse",
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False,
             roles=[Role(name=f"POVU m48 scan {tag}", is_active=True, permissions=perms)])
    db.add(u)
    await db.flush()
    from app.models.two_factor import TwoFAMethod, User2FASettings   # finance rights need an enrolled authenticator
    db.add(User2FASettings(user_id=u.id, is_enabled=True, method=TwoFAMethod.TOTP, secret_key="JBSWY3DPEHPK3PXP"))
    return {settings.AUTH_COOKIE_NAME: create_access_token(str(u.id), session_version=u.auth_session_version or 0)}, u.id


def _client(cookies=None):
    from app.main import app
    ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 50000)), base_url="http://erp.test",
                             cookies=cookies)


async def _scan(c, kind, code):
    r = await c.get(f"/api/v1/lookup/{kind}", params={"search": code, "exact": "true"})
    assert r.status_code == 200, r.text
    return [x["id"] for x in r.json()]


def _barcode(s):
    return "616" + str(int(s, 16))[:10].rjust(10, "0")      # synthetic 13-digit POVU-style code, never a real GTIN


async def _qty(db, **where):
    from app.models.inventory import Stock
    q = select(func.coalesce(func.sum(Stock.quantity_on_hand), 0)).where(*[getattr(Stock, k) == v for k, v in where.items()])
    return Decimal(str((await db.execute(q)).scalar_one()))


# ── goods receipt ─────────────────────────────────────────────────────────────

async def test_goods_receipt_scan():
    from app.db.session import AsyncSessionLocal
    from app.models.finance import AccountingPeriod, AccountType, ChartOfAccount, InventoryAccountMapping, PeriodStatus
    from app.models.master import Material, MaterialType, Supplier, UnitOfMeasure, Warehouse, WarehouseType
    from app.models.procurement import POLine, POStatus, PurchaseOrder

    _guard_db()
    s = uuid.uuid4().hex[:8]
    today = date.today()
    async with AsyncSessionLocal() as db:
        store, sid = await _person(db, "procurement.view", "procurement.receive", "procurement.post",
                                   "finance.post")   # posting a receipt also values it in the ledger
        viewer, _ = await _person(db, "procurement.view")
        outsider, _ = await _person(db, "sales.view")
        from app.models.company import Company
        co = Company(name=f"POVU Factory {s}", short_code=f"P{s[:6].upper()}", country="Kenya", base_currency="KES")
        sup = Supplier(code=f"M48-SUP-{s}", name=f"POVU surfactant supplier {s}")
        wh = Warehouse(code=f"M48-RAW-{s}", name=f"POVU raw store {s}", warehouse_type=WarehouseType.RAW_MATERIAL)
        labsa = Material(code=f"RM-LABSA-{s}", name=f"LABSA 96% {s}", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG)
        sles = Material(code=f"RM-SLES-{s}", name=f"SLES 70% {s}", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG)
        inv = ChartOfAccount(code=f"M48IN{s}", name="POVU raw inventory", account_type=AccountType.ASSET)
        grni = ChartOfAccount(code=f"M48GR{s}", name="POVU GRNI", account_type=AccountType.LIABILITY)
        db.add_all([co, sup, wh, labsa, sles, inv, grni])
        await db.flush()
        for m in (labsa, sles):
            db.add(InventoryAccountMapping(material_id=m.id, stock_type="MATERIAL", valuation_method="FIFO",
                                           inventory_account_id=inv.id, grni_account_id=grni.id, is_active=True))
        if not await db.scalar(select(AccountingPeriod.id).where(AccountingPeriod.period_ym == today.strftime("%Y-%m"))):
            db.add(AccountingPeriod(period_ym=today.strftime("%Y-%m"), period_start=today.replace(day=1),
                                    period_end=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                                    status=PeriodStatus.OPEN, notes="Synthetic M48 period."))
        po = PurchaseOrder(po_no=f"M48-PO-{s}", supplier_id=sup.id, company_id=co.id, currency="KES", exchange_rate=Decimal("1"),
                           order_date=today, expected_delivery_date=today, status=POStatus.ORDERED, created_by_id=sid)
        db.add(po)
        await db.flush()
        pol = POLine(po_id=po.id, line_no=1, material_id=labsa.id, ordered_quantity=Decimal("100"), unit="KG",
                     unit_price=Decimal("180"))
        db.add(pol)
        await db.commit()
        ids = dict(co=co.id, po=po.id, pol=pol.id, wh=wh.id, labsa=labsa.id, sles=sles.id)

    def grn(no, material, qty="50"):
        return {"grn_no": no, "po_id": str(ids["po"]), "company_id": str(ids["co"]), "received_date": today.isoformat(), "warehouse_id": str(ids["wh"]),
                "lines": [{"po_line_id": str(ids["pol"]), "material_id": str(material), "received_quantity": qty,
                           "accepted_quantity": qty, "unit": "KG", "lot_number": f"LABSA-LOT-{s}"}]}

    async with _client() as anon:
        assert (await anon.get("/api/v1/lookup/material", params={"search": f"RM-LABSA-{s}", "exact": "true"})).status_code == 401
        assert (await anon.post("/api/v1/procurement/grn/", json=grn(f"M48-GRN-A-{s}", ids["labsa"]))).status_code == 401
    async with _client(outsider) as c:
        assert (await c.get("/api/v1/lookup/material", params={"search": f"RM-LABSA-{s}", "exact": "true"})).status_code == 403
    async with _client(viewer) as c:                                       # may look, may not receive
        assert (await c.post("/api/v1/procurement/grn/", json=grn(f"M48-GRN-V-{s}", ids["labsa"]))).status_code == 403

    async with _client(store) as c:
        assert await _scan(c, "material", "UNKNOWN-POVU-CODE") == []                  # unknown barcode
        assert await _scan(c, "material", "RM-LABSA") == []                           # partial code is not a match
        assert await _scan(c, "material", f"rm-labsa-{s}") == [str(ids["labsa"])]     # exact, case-insensitive
        r = await c.post("/api/v1/procurement/grn/", json=grn(f"M48-GRN-{s}", ids["labsa"]))
        assert r.status_code == 201, r.text
        ok_id = r.json()["id"]
        r = await c.post(f"/api/v1/procurement/grn/{ok_id}/post")
        assert r.status_code == 200, r.text
        dup = await c.post(f"/api/v1/procurement/grn/{ok_id}/post")                  # the same receipt twice
        assert dup.status_code == 422, dup.text

        # wrong scan: SLES is a real item but not on this purchase order
        (sles_id,) = await _scan(c, "material", f"RM-SLES-{s}")
        r = await c.post("/api/v1/procurement/grn/", json=grn(f"M48-GRN-W-{s}", sles_id))
        assert r.status_code == 201, r.text                                          # a draft may be keyed in…
        wrong = await c.post(f"/api/v1/procurement/grn/{r.json()['id']}/post")       # …but never becomes stock
        assert wrong.status_code == 422 and "not on this purchase order" in wrong.text, wrong.text

    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["wh"], material_id=ids["labsa"]) == Decimal("50")
        assert await _qty(db, warehouse_id=ids["wh"], material_id=ids["sles"]) == 0
        pol = await db.get(POLine, ids["pol"])
        assert Decimal(str(pol.received_quantity)) == Decimal("50")
        assert (await db.get(PurchaseOrder, ids["po"])).status == POStatus.PARTIALLY_RECEIVED


# ── stock transfer ────────────────────────────────────────────────────────────

async def test_stock_transfer_scan():
    from app.db.session import AsyncSessionLocal
    from app.models.inventory import Stock, StockType
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

    _guard_db()
    s = uuid.uuid4().hex[:8]
    code = _barcode(s)
    async with AsyncSessionLocal() as db:
        clerk, _ = await _person(db, "inventory.view", "inventory.transfer_all")
        viewer, _ = await _person(db, "inventory.view")
        a = Warehouse(code=f"M48-FG-A-{s}", name=f"POVU FG Nairobi {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        b = Warehouse(code=f"M48-FG-B-{s}", name=f"POVU FG Mombasa {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        p = Product(sku=f"POVU-ALC-1L-{s}", barcode=code, name=f"POVU AllClean 1 L {s}", category=ProductCategory.HOUSEHOLD,
                    uom=UnitOfMeasure.PCS)
        db.add_all([a, b, p])
        await db.flush()
        db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=a.id, product_id=p.id, quantity_on_hand=Decimal("40"),
                     quantity_reserved=Decimal("0"), quantity_available=Decimal("40")))
        await db.commit()
        ids = dict(a=a.id, b=b.id, p=p.id)

    def move(pid, qty="30", to=None):
        return {"product_id": str(pid), "from_warehouse_id": str(ids["a"]), "to_warehouse_id": str(to or ids["b"]),
                "quantity": qty, "reference": f"M48-TRF-{s}"}

    async with _client() as anon:
        assert (await anon.post("/api/v1/inventory/stock/transfer", json=move(ids["p"]))).status_code == 401
    async with _client(viewer) as c:
        assert (await c.post("/api/v1/inventory/stock/transfer", json=move(ids["p"]))).status_code == 403

    async with _client(clerk) as c:
        assert await _scan(c, "product", "0000000000000") == []                     # unknown barcode
        assert await _scan(c, "product", code[:-1]) == []                            # truncated read
        (pid,) = await _scan(c, "product", code)
        assert pid == str(ids["p"])
        assert await _scan(c, "product", f"povu-alc-1l-{s}") == [pid]                # SKU label scans too
        r = await c.post("/api/v1/inventory/stock/transfer", json=move(pid))
        assert r.status_code == 201, r.text
        dup = await c.post("/api/v1/inventory/stock/transfer", json=move(pid))      # same scan again: only 10 left
        assert dup.status_code == 422 and "INSUFFICIENT_STOCK" in dup.text, dup.text
        assert (await c.post("/api/v1/inventory/stock/transfer", json=move(pid, to=ids["a"]))).status_code == 422
        assert (await c.post("/api/v1/inventory/stock/transfer", json=move(uuid.uuid4()))).status_code == 404

    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["p"]) == Decimal("10")
        assert await _qty(db, warehouse_id=ids["b"], product_id=ids["p"]) == Decimal("30")


# ── cycle count ───────────────────────────────────────────────────────────────

async def test_cycle_count_scan():
    from app.db.session import AsyncSessionLocal
    from app.models.cycle_count import CountEntry, CycleCountPlan, CycleCountTask, PlanType
    from app.models.inventory import Stock, StockType
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

    _guard_db()
    s = uuid.uuid4().hex[:8]
    code = _barcode(s)
    async with AsyncSessionLocal() as db:
        counter, _ = await _person(db, "inventory.view", "cycle_count.view", "cycle_count.create")
        viewer, _ = await _person(db, "inventory.view", "cycle_count.view")
        a = Warehouse(code=f"M48-CC-A-{s}", name=f"POVU FG Nairobi {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        b = Warehouse(code=f"M48-CC-B-{s}", name=f"POVU FG Kisumu {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        hw = Product(sku=f"POVU-HWP-1KG-{s}", barcode=code, name=f"POVU Hand Wash Powder 1 kg Pouch {s}",
                     category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        other = Product(sku=f"POVU-ALC-1L-{s}", barcode=_barcode(s[::-1]), name=f"POVU AllClean 1 L {s}",
                        category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        db.add_all([a, b, hw, other])
        await db.flush()
        for wh, q in ((a, "100"), (b, "5")):                                          # same item in two warehouses
            db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=wh.id, product_id=hw.id, quantity_on_hand=Decimal(q),
                         quantity_reserved=Decimal("0"), quantity_available=Decimal(q)))
        db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=a.id, product_id=other.id, quantity_on_hand=Decimal("7"),
                     quantity_reserved=Decimal("0"), quantity_available=Decimal("7")))
        plan = CycleCountPlan(plan_code=f"M48-CCP-{s}", name="POVU FG weekly", warehouse_id=a.id, plan_type=PlanType.ITEM,
                              variance_tolerance_pct=Decimal("2.0"), auto_approve_within_tolerance=True)
        db.add(plan)
        await db.flush()
        task = CycleCountTask(task_no=f"M48-CC-{s}", plan_id=plan.id, warehouse_id=a.id, product_id=hw.id,
                              scheduled_date=date.today())
        db.add(task)
        await db.commit()
        ids = dict(a=a.id, b=b.id, hw=hw.id, other=other.id, task=task.id)

    async with _client() as anon:
        assert (await anon.post("/api/v1/cycle-count/entries", json={"task_id": str(ids["task"]), "counted_qty": "99"})).status_code == 401
    async with _client(viewer) as c:
        r = await c.post("/api/v1/cycle-count/entries", json={"task_id": str(ids["task"]), "counted_qty": "99"})
        assert r.status_code == 403, r.text

    async with _client(counter) as c:
        assert await _scan(c, "count_task", f"M48-CC-{s[:4]}") == []                 # partial task label
        (tid,) = await _scan(c, "count_task", f"m48-cc-{s}")
        assert await _scan(c, "product", "9999999999999") == []                     # unknown item barcode
        (pid,) = await _scan(c, "product", code)
        (wrong,) = await _scan(c, "product", _barcode(s[::-1]))
        url = "/api/v1/cycle-count/entries"
        r = await c.post(url, json={"task_id": tid, "product_id": wrong, "counted_qty": "7", "unit": "PCS"})
        assert r.status_code == 400, r.text                                         # item not on this count task
        r = await c.post(url, json={"task_id": tid, "product_id": pid, "counted_qty": "-1", "unit": "PCS"})
        assert r.status_code == 400, r.text
        r = await c.post(url, json={"task_id": tid, "product_id": pid, "counted_qty": "99", "unit": "PCS"})
        assert r.status_code == 201, r.text
        e = r.json()
        assert (Decimal(str(e["system_qty"])), Decimal(str(e["variance_qty"])), e["within_tolerance"]) == \
            (Decimal("100"), Decimal("-1"), True)
        dup = await c.post(url, json={"task_id": tid, "product_id": pid, "counted_qty": "99", "unit": "PCS"})
        assert dup.status_code == 400, dup.text                                     # the same item counted twice

    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["hw"]) == Decimal("99")   # auto-approved, posted
        assert await _qty(db, warehouse_id=ids["b"], product_id=ids["hw"]) == Decimal("5")    # other warehouse untouched
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["other"]) == Decimal("7")
        n = (await db.execute(select(func.count()).select_from(CountEntry).where(CountEntry.task_id == ids["task"]))).scalar_one()
        assert n == 1
