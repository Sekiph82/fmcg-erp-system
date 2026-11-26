"""M48.S01.T024 (T015 M38 review remediation) on disposable PostgreSQL through the real app:

* a cash collector who is NOT linked as a SalesRep gets the collector screen: only customers of open dunning cases
  assigned to them (not resolved cases, not other collectors' cases), their open invoices and collections;
* van-sales check-in stores GPS + accuracy, validates coordinates, and only checks in a PLANNED visit;
* van visit photo upload (checked-in visits only, images only), photo-URL validation and the own rep day log;
* van actions only for the van's driver / route rep or a supervisor / logistics manager; day log for another rep only
  with field.supervise; offline sync resend after a lost response books no second sale or payment.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine

pytestmark = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the disposable M48 PostgreSQL")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(user, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=user.id, username=user.username, email=user.email, full_name=user.full_name, is_superuser=False,
                           is_active=True, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms,
                                                                                    access_scopes=[])])


PERMS = {"drv": ("field.edit",), "nobody": ("field.view",), "other": ("field.edit",), "rep": ("field.edit",),
         "sup": ("field.supervise",), "log": ("logistics.edit",)}  # van-sales routes sit behind the sales/field/logistics guard


async def _setup():
    from app.models.dunning import DunningCase, DunningCaseStatus
    from app.models.sales import Customer, CustomerChannel, Invoice, InvoiceStatus, SalesOrder, SOStatus
    from app.models.user import User
    from app.models.van_sales import Van, VanVisit

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.port != 5432
        # migration 0078 adds this column; idempotent here so the test also runs on a pre-0078 template
        await db.execute(text("ALTER TABLE van_visits ADD COLUMN IF NOT EXISTS gps_accuracy_m NUMERIC(8,1)"))
        await db.execute(text("ALTER TABLE van_payments ADD COLUMN IF NOT EXISTS offline_id VARCHAR(100) UNIQUE"))
        users = {k: User(email=f"{k}-{s}@example.com", username=f"{k}{s}", full_name=k.title(), hashed_password="x")
                 for k in ("col", "col2", "nobody", "drv", "other", "rep", "sup", "log")}
        db.add_all(users.values())
        cust = {k: Customer(code=f"{k}-{s}", name=f"POVU Outlet {k.upper()} {s}", channel=CustomerChannel.RETAIL,
                            currency="KES", phone="0712345678") for k in ("c1", "c2", "c3")}
        db.add_all(cust.values())
        await db.flush()
        invs = {}
        for k in ("c1", "c3"):
            so = SalesOrder(order_no=f"SO-{k}-{s}", customer_id=cust[k].id, order_date=date.today(),
                            requested_delivery_date=date.today(), currency="KES", status=SOStatus.CONFIRMED)
            db.add(so)
            await db.flush()
            invs[k] = Invoice(invoice_no=f"INV-{k}-{s}", so_id=so.id, customer_id=cust[k].id, invoice_date=date.today(),
                              due_date=date.today() - timedelta(days=10), status=InvoiceStatus.OVERDUE, currency="KES",
                              total_amount=Decimal("1000"), subtotal=Decimal("1000"))
            db.add(invs[k])
        db.add_all([
            DunningCase(case_no=f"DC1-{s}", customer_id=cust["c1"].id, assigned_collector_id=users["col"].id,
                        case_status=DunningCaseStatus.OPEN, total_overdue_amount=Decimal("1000")),
            DunningCase(case_no=f"DC2-{s}", customer_id=cust["c2"].id, assigned_collector_id=users["col"].id,
                        case_status=DunningCaseStatus.RESOLVED),
            DunningCase(case_no=f"DC3-{s}", customer_id=cust["c3"].id, assigned_collector_id=users["col2"].id,
                        case_status=DunningCaseStatus.PROMISE_TO_PAY),
        ])
        from app.models.field_sales import SalesRep, SalesRoute
        from app.models.master import Product, ProductCategory
        rep = SalesRep(code=f"VR-{s}", name="Van Rep", user_id=users["rep"].id)
        product = Product(sku=f"POVU-ALC-1L-{s}", name=f"POVU AllClean 1 L {s}", category=ProductCategory.HOUSEHOLD,
                          selling_price=Decimal("150"))
        db.add_all([rep, product])
        await db.flush()
        route = SalesRoute(code=f"VRT-{s}", name="Van route", assigned_rep_id=rep.id)
        db.add(route)
        await db.flush()
        van = Van(van_code=f"VAN-{s}", driver_id=users["drv"].id, route_id=route.id)
        db.add(van)
        await db.flush()
        visits = [VanVisit(van_id=van.id, customer_id=cust["c1"].id, route_date=date.today(), sequence_no=n) for n in (1, 2, 3, 4)]
        db.add_all(visits)
        await db.commit()
        return SimpleNamespace(U={k: _as(u, *PERMS.get(k, ())) for k, u in users.items()}, c={k: v.id for k, v in cust.items()},
                               inv={k: v.id for k, v in invs.items()}, van=van.id, v1=visits[0].id, v2=visits[1].id,
                               v3=visits[2].id, v4=visits[3].id, product=product.id)


@pytest.mark.asyncio
async def test_collector_without_rep_link_sees_only_own_assignments():
    from app.main import app
    from app.models.field_ops import CashCollection

    d = await _setup()
    F = "/api/v1/field"
    who = lambda u: app.dependency_overrides.__setitem__(get_current_user, lambda: u)  # noqa: E731
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            who(d.U["col"])
            me = (await c.get(f"{F}/me")).json()
            assert me["rep"] is None and me["is_collector"] is True
            assert (await c.get(f"{F}/today")).status_code == 403          # collector is not a rep: no route screen
            accts = (await c.get(f"{F}/collector/accounts")).json()
            assert [a["customer_id"] for a in accts] == [str(d.c["c1"])]   # not the RESOLVED case, not col2's case
            assert accts[0]["open_balance"] == 1000.0
            r = await c.get(f"{F}/customers/{d.c['c1']}/invoices")
            assert r.status_code == 200 and [i["id"] for i in r.json()] == [str(d.inv["c1"])]
            assert (await c.get(f"{F}/customers/{d.c['c2']}/invoices")).status_code == 403   # resolved case
            assert (await c.get(f"{F}/customers/{d.c['c3']}/invoices")).status_code == 403   # other collector's
            body = {"client_ref": f"col-{uuid.uuid4().hex[:12]}", "customer_id": str(d.c["c1"]), "invoice_id": str(d.inv["c1"]),
                    "method": "CASH", "amount": "400.00", "lat": -1.2921, "lng": 36.8219}
            r = await c.post(f"{F}/collections", json=body)
            assert r.status_code == 201, r.text
            again = await c.post(f"{F}/collections", json=body)
            assert again.status_code == 201 and again.json()["duplicate"] is True
            assert (await c.post(f"{F}/collections", json={**body, "client_ref": f"col-{uuid.uuid4().hex[:12]}",
                                                           "customer_id": str(d.c["c3"]), "invoice_id": str(d.inv["c3"])})).status_code == 403
            assert (await c.post(f"{F}/collections", json={**body, "client_ref": f"col-{uuid.uuid4().hex[:12]}",
                                                           "amount": "700.00"})).status_code == 422  # over open balance
            assert (await c.post(f"{F}/invoices/{d.inv['c3']}/stk", json={"phone": "0712345678", "amount": "10"})).status_code == 403
            mine = (await c.get(f"{F}/collections")).json()
            assert len(mine) == 1 and mine[0]["customer"].startswith("POVU Outlet C1") and mine[0]["amount"] == 400.0

            who(d.U["col2"])
            assert [a["customer_id"] for a in (await c.get(f"{F}/collector/accounts")).json()] == [str(d.c["c3"])]
            assert (await c.get(f"{F}/customers/{d.c['c1']}/invoices")).status_code == 403

            who(d.U["nobody"])
            me = (await c.get(f"{F}/me")).json()
            assert me["rep"] is None and me["is_collector"] is False
            assert (await c.get(f"{F}/collector/accounts")).status_code == 403
            r = await c.get(f"{F}/customers/{d.c['c1']}/invoices")
            assert r.status_code == 403 and "not set up" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(CashCollection).where(CashCollection.customer_id == d.c["c1"]))).scalars().all()
        assert len(rows) == 1 and rows[0].rep_id is None and rows[0].collected_by_id == d.U["col"].id
        assert rows[0].status == "PENDING" and rows[0].amount == Decimal("400.00") and rows[0].gps_lat is not None


@pytest.mark.asyncio
async def test_van_check_in_stores_gps_and_validates(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app
    from app.models.van_sales import VanRepDayLog, VanVisit

    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    d = await _setup()
    V = "/api/v1/van-sales"
    app.dependency_overrides[get_current_user] = lambda: d.U["drv"]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            ci = f"{V}/visits/{d.v1}/check-in"
            for bad in ({"gps_lat": 91, "gps_lng": 36.8}, {"gps_lat": -1.29, "gps_lng": 181}, {"gps_lat": -1.29},
                        {"gps_accuracy_m": 12}, {"gps_lat": -1.29, "gps_lng": 36.8, "gps_accuracy_m": -1}):
                assert (await c.post(ci, json=bad)).status_code == 422, bad
            # photo before check-in is refused
            assert (await c.post(f"{V}/visits/{d.v1}/photo-upload", files={"file": ("o.png", PNG, "image/png")})).status_code == 409
            r = await c.post(ci, json={"gps_lat": -1.2920659, "gps_lng": 36.8219462, "gps_accuracy_m": 14.5})
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "CHECKED_IN" and float(r.json()["gps_accuracy_m"]) == 14.5
            assert (await c.post(ci, json={"gps_lat": -1.3, "gps_lng": 36.8})).status_code == 409   # not PLANNED any more
            # no fix (permission denied) -> explicit check-in without location stays possible, stored as NULL
            assert (await c.post(f"{V}/visits/{d.v2}/check-in", json={})).status_code == 200

            up = f"{V}/visits/{d.v1}/photo-upload"
            assert (await c.post(up, files={"file": ("o.txt", b"hello", "text/plain")})).status_code == 415
            r = await c.post(up, files={"file": ("outlet.png", PNG, "image/png")})
            assert r.status_code == 200 and r.json()["has_photo"] is True
            assert (await c.post(f"{V}/visits/{d.v1}/photo", json={"photo_url": "javascript:alert(1)"})).status_code == 422

            today = date.today().isoformat()
            assert (await c.post(f"{V}/rep-day-log", json={"log_date": today, "start_gps_lat": 95})).status_code == 422
            r = await c.post(f"{V}/rep-day-log", json={"log_date": today, "start_time": "2026-11-26T05:30:00.000Z",
                                                        "start_gps_lat": -1.29, "start_gps_lng": 36.82})
            assert r.status_code == 201 and r.json()["action"] == "created", r.text
            r = await c.post(f"{V}/rep-day-log", json={"log_date": today, "end_time": "2026-11-26T15:00:00.000Z",
                                                        "end_gps_lat": -1.3, "end_gps_lng": 36.8, "total_visits": 2})
            assert r.json()["action"] == "updated"
            mine = (await c.get(f"{V}/rep-day-log", params={"mine": "true", "log_date": today})).json()
            assert len(mine) == 1 and mine[0]["rep_user_id"] == str(d.U["drv"].id) and mine[0]["total_visits"] == 2
            assert mine[0]["start_time"] == "2026-11-26T05:30:00" and mine[0]["end_gps_lat"] == -1.3
            app.dependency_overrides[get_current_user] = lambda: d.U["nobody"]
            assert (await c.get(f"{V}/rep-day-log", params={"mine": "true", "log_date": today})).json() == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        v1, v2 = await db.get(VanVisit, d.v1), await db.get(VanVisit, d.v2)
        assert v1.gps_lat == Decimal("-1.2920659") and v1.gps_lng == Decimal("36.8219462") and v1.gps_accuracy_m == Decimal("14.5")
        assert v1.outlet_photo_url.startswith("doc:")
        assert v2.status == "CHECKED_IN" and v2.gps_lat is None and v2.gps_accuracy_m is None
        assert (await db.execute(select(VanRepDayLog).where(VanRepDayLog.rep_user_id == d.U["drv"].id))).scalar_one().start_gps_lat is not None


def _sale(d, ref: str, when: str = "2026-11-26T09:00:00.000Z", qty: str = "2") -> dict:
    return {"customer_id": str(d.c["c1"]), "txn_type": "SALE", "txn_datetime": when, "offline_id": ref,
            "lines": [{"item_id": str(d.product), "quantity": qty, "unit_price": "150"}]}


@pytest.mark.asyncio
async def test_van_actions_limited_to_assigned_users_and_day_log_owner():
    from app.main import app

    d = await _setup()
    V = "/api/v1/van-sales"

    def as_(k):
        app.dependency_overrides[get_current_user] = lambda: d.U[k]

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            as_("other")   # has a field write right, but is not this van's driver/rep and not a supervisor
            assert (await c.post(f"{V}/visits/{d.v1}/check-in", json={})).status_code == 403
            assert (await c.post(f"{V}/visits/{d.v1}/photo-upload", files={"file": ("o.png", PNG, "image/png")})).status_code == 403
            assert (await c.post(f"{V}/visits/{d.v1}/check-out")).status_code == 403
            assert (await c.post(f"{V}/vans/{d.van}/transactions", json=_sale(d, f"pos-{uuid.uuid4()}"))).status_code == 403
            assert (await c.post(f"{V}/vans/{d.van}/sync", json={"transactions": [_sale(d, f"pos-{uuid.uuid4()}")]})).status_code == 403
            as_("drv")
            r = await c.post(f"{V}/vans/{d.van}/transactions", json=_sale(d, f"pos-{uuid.uuid4()}"))
            assert r.status_code == 201, r.text
            txn_id = r.json()["id"]
            as_("other")
            assert (await c.post(f"{V}/transactions/{txn_id}/payments",
                                 json={"method": "CASH", "amount": "10", "collected_at": "2026-11-26T09:05:00Z"})).status_code == 403
            for k, visit in (("drv", d.v1), ("rep", d.v2), ("sup", d.v3), ("log", d.v4)):   # driver, route rep, supervisors
                as_(k)
                assert (await c.post(f"{V}/visits/{visit}/check-in", json={})).status_code == 200, k

            # an online payment is idempotent on its offline_id too
            as_("drv")
            pay = {"method": "CASH", "amount": "100", "collected_at": "2026-11-26T09:05:00Z", "offline_id": f"pay-{uuid.uuid4()}"}
            p1 = await c.post(f"{V}/transactions/{txn_id}/payments", json=pay)
            p2 = await c.post(f"{V}/transactions/{txn_id}/payments", json=pay)
            assert p1.status_code == p2.status_code == 201 and p1.json()["id"] == p2.json()["id"], (p1.text, p2.text)

            # day log: own only, unless field.supervise
            today = date.today().isoformat()
            assert (await c.post(f"{V}/rep-day-log", json={"log_date": today, "rep_user_id": str(d.U["rep"].id)})).status_code == 403
            assert (await c.post(f"{V}/rep-day-log", json={"log_date": today, "rep_user_id": str(d.U["drv"].id)})).status_code == 201
            as_("sup")
            assert (await c.post(f"{V}/rep-day-log", json={"log_date": today, "rep_user_id": str(d.U["rep"].id)})).status_code == 201
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_offline_sync_resend_after_lost_response_books_nothing_twice():
    from app.main import app
    from app.models.van_sales import VanPayment, VanSalesTxn

    d = await _setup()
    V = "/api/v1/van-sales"
    sale_ref, pay_ref = f"pos-{uuid.uuid4()}", f"pay-{uuid.uuid4()}"
    outbox = {"transactions": [_sale(d, sale_ref, "2026-11-26T10:00:00.000Z", "1")],
              "payments": [{"offline_id": pay_ref, "offline_txn_id": sale_ref, "method": "CASH", "amount": 150,
                            "collected_at": "2026-11-26T10:01:00.000Z"}], "device_id": "t024-device"}
    app.dependency_overrides[get_current_user] = lambda: d.U["drv"]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            first = (await c.post(f"{V}/vans/{d.van}/sync", json=outbox)).json()
            assert first["txns_created"] == 1 and first["payments_created"] == 1 and first["errors"] == [], first
            # the response was "lost": the device resends the same outbox
            again = (await c.post(f"{V}/vans/{d.van}/sync", json=outbox)).json()
            assert again == {"visits_created": 0, "txns_created": 0, "payments_created": 0, "errors": [], "duplicates_skipped": 2}
            # a payment-only resend (its sale already on the server, not in this batch) is matched too
            third = (await c.post(f"{V}/vans/{d.van}/sync", json={"payments": outbox["payments"]})).json()
            assert third["payments_created"] == 0 and third["duplicates_skipped"] == 1 and third["errors"] == [], third
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        txns = (await db.execute(select(VanSalesTxn).where(VanSalesTxn.offline_id == sale_ref))).scalars().all()
        assert len(txns) == 1 and txns[0].paid_amount == Decimal("150") and txns[0].payment_status == "PAID"
        pays = (await db.execute(select(VanPayment).where(VanPayment.txn_id == txns[0].id))).scalars().all()
        assert len(pays) == 1 and pays[0].offline_id == pay_ref and pays[0].collected_by == d.U["drv"].id
