"""M38.S02/S03 field app + collections on disposable PostgreSQL through the real app: rep scoping to own route,
idempotent visits/orders/collections, server prices, open invoices, finance confirmation posting the payment,
driver trips with proof of delivery, outlet audits and supervisor compliance."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.models.delivery import DeliveryTrip, ProofOfDelivery, TripOrder
from app.models.field_ops import CashCollection, FieldAudit
from app.models.field_sales import RouteStop, SalesRep, SalesRoute, VisitLog
from app.models.master import Product, ProductCategory, Warehouse, WarehouseType
from app.models.sales import (Customer, CustomerChannel, Invoice, InvoiceStatus, OrderSource, SalesOrder, Shipment,
                              ShipmentStatus, SOStatus)
from app.models.user import User

TASK_DB_ENV = "M38_S02_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_S02_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_s02_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")
F = "/api/v1/field"
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


@pytest.mark.asyncio
async def test_field_app_end_to_end(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        users = {k: User(email=f"{k}-{s}@example.com", username=f"{k}{s}", full_name=k.title(), hashed_password="x")
                 for k in ("ali", "bea", "drv", "ctl", "sup", "fin")}
        db.add_all(users.values())
        await db.flush()
        rep_a = SalesRep(code=f"RA-{s}", name="Ali Rep", user_id=users["ali"].id)
        rep_b = SalesRep(code=f"RB-{s}", name="Bea Rep", user_id=users["bea"].id)
        db.add_all([rep_a, rep_b])
        await db.flush()
        route_a = SalesRoute(code=f"R-A-{s}", name="Route A", assigned_rep_id=rep_a.id)
        route_b = SalesRoute(code=f"R-B-{s}", name="Route B", assigned_rep_id=rep_b.id)
        db.add_all([route_a, route_b])
        await db.flush()
        cust = {k: Customer(code=f"{k}-{s}", name=f"{k.upper()} Shop {s}", channel=CustomerChannel.RETAIL, currency="KES",
                            phone="0712345678") for k in ("c1", "c2", "c3")}
        db.add_all(cust.values())
        await db.flush()
        for n, (k, route) in enumerate((("c1", route_a), ("c2", route_a), ("c3", route_b)), start=1):
            db.add(RouteStop(route_id=route.id, customer_id=cust[k].id, stop_sequence=n))
        soda = Product(sku=f"SODA-{s}", name=f"Soda {s}", category=ProductCategory.BEVERAGE, selling_price=Decimal("50"))
        wh = Warehouse(code=f"WH-{s}", name="Main", warehouse_type=list(WarehouseType)[0])
        db.add_all([soda, wh])
        await db.flush()
        so = SalesOrder(order_no=f"SO-{s}", customer_id=cust["c1"].id, order_date=date.today(),
                        requested_delivery_date=date.today(), currency="KES", status=SOStatus.CONFIRMED)
        db.add(so)
        await db.flush()
        inv = Invoice(invoice_no=f"INV-{s}", so_id=so.id, customer_id=cust["c1"].id, invoice_date=date.today(),
                      due_date=date.today() + timedelta(days=7), status=InvoiceStatus.ISSUED, currency="KES",
                      total_amount=Decimal("1000"), subtotal=Decimal("1000"))
        ship = Shipment(shipment_no=f"SH-{s}", so_id=so.id, warehouse_id=wh.id, status=ShipmentStatus.DISPATCHED,
                        scheduled_date=date.today())
        db.add_all([inv, ship])
        await db.flush()
        from app.models.finance import AccountingPostingRule, AccountType, ChartOfAccount
        recv = ChartOfAccount(code=f"M38AR{s}", name="Synthetic receivables", account_type=AccountType.ASSET, currency="KES")
        mclr = ChartOfAccount(code=f"M38MP{s}", name="Synthetic M-Pesa clearing", account_type=AccountType.ASSET, currency="KES")
        db.add_all([recv, mclr])
        await db.flush()
        db.add(AccountingPostingRule(source_module="sales", source_event="CUSTOMER_PAYMENT_RECEIVED_MPESA",
                                     rule_name=f"Synthetic M38 M-Pesa receipt {s}", credit_account_id=recv.id,
                                     clearing_account_id=mclr.id, priority=1, is_active=True))
        rev = ChartOfAccount(code=f"M38RV{s}", name="Synthetic revenue", account_type=AccountType.REVENUE, currency="KES")
        db.add(rev)
        await db.flush()
        db.add(AccountingPostingRule(source_module="sales", source_event="SALES_INVOICE_ISSUED", rule_name=f"Synthetic M38 invoice {s}",
                                     debit_account_id=recv.id, credit_account_id=rev.id, priority=1, is_active=True))
        await db.flush()
        from app.services.sales_service import _post_invoice_to_gl
        await _post_invoice_to_gl(db, inv, users["fin"].id)   # the invoice is issued through the real GL path
        trip = DeliveryTrip(trip_no=f"T-{s}", trip_date=date.today(), driver_user_id=users["drv"].id)
        db.add(trip)
        await db.flush()
        stop = TripOrder(trip_id=trip.id, shipment_id=ship.id, delivery_sequence=1)
        db.add(stop)
        await db.commit()
        ids = SimpleNamespace(**{k: c.id for k, c in cust.items()}, soda=soda.id, inv=inv.id, trip=trip.id, stop=stop.id,
                              ship=ship.id, rep_a=rep_a.id)
        U = {k: _as(u) for k, u in users.items()}
        U["ctl"] = _as(users["ctl"], "field.audit")
        U["sup"] = _as(users["sup"], "field.supervise")
        U["fin"] = _as(users["fin"], "finance.edit", "sales.view")

    def who(u):
        app.dependency_overrides[get_current_user] = lambda: u

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            who(U["drv"])
            assert (await c.get(f"{F}/today")).status_code == 403            # not a rep
            who(U["ali"])
            me = (await c.get(f"{F}/me")).json()
            assert me["rep"]["code"] == f"RA-{s}" and not me["can_audit"]
            day = (await c.get(f"{F}/today")).json()
            assert [x["customer_id"] for x in day["stops"]] == [str(ids.c1), str(ids.c2)] and day["stops"][0]["open_balance"] == 1000.0

            v = {"client_ref": f"v-{s}", "customer_id": str(ids.c1), "outcome": "NO_ORDER", "lat": "-1.2921", "lng": "36.8219"}
            first = (await c.post(f"{F}/visits", json=v)).json()
            assert (await c.post(f"{F}/visits", json=v)).json() == {"id": first["id"], "duplicate": True}
            assert (await c.post(f"{F}/visits", json={**v, "client_ref": f"v3-{s}", "customer_id": str(ids.c3)})).status_code == 403
            assert (await c.post(f"{F}/visits/{first['id']}/photo", files={"file": ("shop.png", PNG, "image/png")})).status_code == 200
            assert (await c.post(f"{F}/visits/{first['id']}/photo", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")})).status_code == 415

            cat = (await c.get(f"{F}/catalog", params={"customer_id": str(ids.c1), "search": s})).json()
            assert cat["items"][0]["unit_price"] == 50.0
            order = {"client_ref": f"o-{s}", "customer_id": str(ids.c1), "requested_delivery_date": tomorrow, "visit_id": first["id"],
                     "lines": [{"product_id": str(ids.soda), "quantity": "24", "unit_price": "1"}]}
            o1 = await c.post(f"{F}/orders", json=order)
            assert o1.status_code == 201 and o1.json()["total"] == 1200.0
            assert (await c.post(f"{F}/orders", json=order)).json()["id"] == o1.json()["id"]
            assert (await c.post(f"{F}/orders", json={**order, "client_ref": f"o3-{s}", "customer_id": str(ids.c3)})).status_code == 403

            invs = (await c.get(f"{F}/customers/{ids.c1}/invoices")).json()
            assert invs[0]["outstanding"] == 1000.0
            col = {"client_ref": f"c-{s}", "customer_id": str(ids.c1), "invoice_id": str(ids.inv), "method": "MPESA", "amount": "400"}
            assert (await c.post(f"{F}/collections", json=col)).status_code == 422             # code required
            col["mpesa_code"] = f"QK{s.upper()}"[:10]
            c1 = await c.post(f"{F}/collections", json=col)
            assert c1.status_code == 201 and c1.json()["status"] == "PENDING"
            assert (await c.post(f"{F}/collections", json=col)).json()["duplicate"] is True
            assert (await c.post(f"{F}/collections", json={**col, "client_ref": f"c2-{s}"})).status_code == 409  # same code
            assert (await c.post(f"{F}/collections", json={**col, "client_ref": f"c4-{s}", "mpesa_code": None, "method": "CASH",
                                                           "amount": "5000"})).status_code == 422     # above open balance
            assert len((await c.get(f"{F}/collections")).json()) == 1

            who(U["bea"])
            assert (await c.get(f"{F}/customers/{ids.c1}/invoices")).status_code == 403
            assert (await c.post(f"{F}/orders", json=order)).status_code == 409       # someone else's reference

            # office: only finance confirms; confirming posts the payment to the invoice
            who(U["ali"])
            assert (await c.post(f"/api/v1/collections/{c1.json()['id']}/confirm")).status_code == 403
            who(U["fin"])
            listed = (await c.get("/api/v1/collections/", params={"customer_id": str(ids.c1)})).json()
            assert listed[0]["invoice_no"] == f"INV-{s}" and listed[0]["rep_name"] == "Ali Rep"
            conf = await c.post(f"/api/v1/collections/{c1.json()['id']}/confirm")
            assert conf.status_code == 200 and conf.json()["status"] == "CONFIRMED", conf.text
            assert (await c.post(f"/api/v1/collections/{c1.json()['id']}/cancel")).status_code == 409
            assert (await c.post(f"/api/v1/collections/{c1.json()['id']}/reconcile")).json()["status"] == "RECONCILED"

            # driver
            who(U["ali"])
            assert (await c.get(f"{F}/trips")).json() == []
            who(U["drv"])
            trips = (await c.get(f"{F}/trips")).json()
            assert trips[0]["stops"][0]["customer"] == f"C1 Shop {s}"
            form = {"received_by": "Shop owner", "lat": "-1.29", "lng": "36.82"}
            sig = {"signature": ("sig.png", PNG, "image/png")}
            assert (await c.post(f"{F}/trip-orders/{ids.stop}/deliver", data=form, files=sig)).status_code == 409  # not started
            assert (await c.post(f"{F}/trips/{ids.trip}/finish")).status_code == 409
            assert (await c.post(f"{F}/trips/{ids.trip}/start")).json()["status"] == "IN_TRANSIT"
            d1 = await c.post(f"{F}/trip-orders/{ids.stop}/deliver", data=form, files=sig)
            assert d1.status_code == 201 and d1.json()["status"] == "DELIVERED"
            assert (await c.post(f"{F}/trip-orders/{ids.stop}/deliver", data=form, files=sig)).json()["duplicate"] is True
            assert (await c.post(f"{F}/trips/{ids.trip}/finish")).json()["status"] == "COMPLETED"
            who(U["bea"])
            assert (await c.post(f"{F}/trip-orders/{ids.stop}/fail", json={"reason": "closed"})).status_code == 404

            # controller audits; supervisor compliance
            who(U["ali"])
            assert (await c.get(f"{F}/audit-checklist")).status_code == 403
            who(U["ctl"])
            items = (await c.get(f"{F}/audit-checklist")).json()
            outlets = (await c.get(f"{F}/audit-outlets", params={"search": f"C1 Shop {s}"})).json()
            assert outlets[0]["rep"] == "Ali Rep"
            bad = {"client_ref": f"a-{s}", "customer_id": str(ids.c1), "answers": [{"key": items[0]["key"], "ok": True}]}
            assert (await c.post(f"{F}/audits", json=bad)).status_code == 422
            answers = [{"key": it["key"], "ok": n % 2 == 0, "note": None if n % 2 == 0 else "missing"} for n, it in enumerate(items)]
            a1 = await c.post(f"{F}/audits", json={**bad, "answers": answers, "lat": "-1.29", "lng": "36.82"})
            assert a1.status_code == 201 and a1.json()["score"] == round(100 * 4 / 7, 2)
            assert (await c.post(f"{F}/audits/{a1.json()['id']}/photo", files={"file": ("shelf.png", PNG, "image/png")})).json() == {"photos": 1}
            assert (await c.get(f"{F}/compliance")).status_code == 403
            who(U["sup"])
            rows = {r["code"]: r for r in (await c.get(f"{F}/compliance", params={"days": 1})).json()["reps"]}
            ra = rows[f"RA-{s}"]
            assert (ra["route_stops"], ra["visits"], ra["outlets_visited"], ra["coverage_pct"], ra["visits_with_gps_pct"]) == (2, 1, 1, 50.0, 100.0)
            assert (ra["orders"], ra["order_value"], ra["collections"], ra["audits"]) == (1, 1200.0, 1, 1)
            assert len((await c.get(f"{F}/audits")).json()) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as db:
        so = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == f"field:o-{s}"))).scalar_one()
        assert (so.status, so.source, so.sales_rep_id) == (SOStatus.DRAFT, OrderSource.FIELD_SALES, ids.rep_a)
        visit = (await db.execute(select(VisitLog).where(VisitLog.client_ref == f"v-{s}"))).scalar_one()
        assert visit.order_id == so.id and visit.outcome.value == "ORDERED" and visit.photo_key
        inv = await db.get(Invoice, ids.inv)
        assert inv.paid_amount == Decimal("400") and inv.status == InvoiceStatus.PARTIALLY_PAID
        col = (await db.execute(select(CashCollection).where(CashCollection.client_ref == f"c-{s}"))).scalar_one()
        assert col.payment_id is not None and col.status == "RECONCILED"
        pod = (await db.execute(select(ProofOfDelivery).where(ProofOfDelivery.trip_order_id == ids.stop))).scalar_one()
        assert pod.signature_key and (tmp_path / pod.signature_key).read_bytes() == PNG
        assert (await db.get(Shipment, ids.ship)).status == ShipmentStatus.DELIVERED
        audit = (await db.execute(select(FieldAudit).where(FieldAudit.client_ref == f"a-{s}"))).scalar_one()
        assert audit.rep_id == ids.rep_a and len(audit.photo_keys) == 1
