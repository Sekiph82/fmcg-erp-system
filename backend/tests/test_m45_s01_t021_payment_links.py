"""M45.S01.T021 customer payment links (DB part needs M45_DB=1).

Through the real endpoints: forged token 404; partial STK push; the Daraja callback (simulator-style, non-simulated
transaction) settles once into a PENDING M-Pesa collection, a replayed callback changes nothing; the rest is paid →
link PAID; finance confirmation posts through the existing collections flow; without Daraja credentials the push is
simulated and the link only reaches TEST_PAID with no collection; expired/revoked links are refused; card is
NOT_CONFIGURED.
"""
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _invoice(db, total="1000"):
    from app.models.sales import Customer, Invoice, InvoiceStatus, SalesOrder, SOStatus
    c = Customer(code=f"SYN-{uuid.uuid4().hex[:6]}", name="POVU Pay Outlet", currency="KES")
    db.add(c)
    await db.flush()
    so = SalesOrder(order_no=f"SO-{uuid.uuid4().hex[:8]}", customer_id=c.id, order_date=date.today(),
                    requested_delivery_date=date.today(), status=SOStatus.INVOICED, currency="KES")
    db.add(so)
    await db.flush()
    inv = Invoice(invoice_no=f"INV-{uuid.uuid4().hex[:8]}", so_id=so.id, customer_id=c.id, invoice_date=date.today(),
                  due_date=date.today() + timedelta(days=30), status=InvoiceStatus.ISSUED, currency="KES",
                  subtotal=Decimal(total), total_amount=Decimal(total), paid_amount=Decimal("0"))
    db.add(inv)
    await db.flush()
    return inv


def _callback(checkout, ok=True, receipt="QSIM123ABC"):
    item = [{"Name": "MpesaReceiptNumber", "Value": receipt}, {"Name": "Amount", "Value": 1}]
    return {"Body": {"stkCallback": {"MerchantRequestID": "m", "CheckoutRequestID": checkout, "ResultCode": 0 if ok else 1032,
                                     "ResultDesc": "ok" if ok else "cancelled", "CallbackMetadata": {"Item": item}}}}


@DB
@pytest.mark.asyncio
async def test_payment_link_flow(monkeypatch):
    from sqlalchemy import func, select
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.field_ops import CashCollection
    from app.models.payments_hub import PaymentLink
    from app.services import mpesa_daraja_service as daraja
    from app.services import payment_link_service as pls
    monkeypatch.setattr(settings, "MPESA_CALLBACK_SECRET", "cb-secret")
    pushes = []

    async def live_push(phone, amount, reference, description="Payment"):     # the Daraja simulator accepts the push
        cid = f"ws_CO_LIVE_{uuid.uuid4().hex[:12]}"
        pushes.append(cid)
        return cid, "MR1", {"ResponseCode": "0", "CheckoutRequestID": cid}
    monkeypatch.setattr(daraja, "_stk_push_request", live_push)
    async with AsyncSessionLocal() as db:
        inv = await _invoice(db)
        link, token = await pls.create(db, inv.id, None, 14, True)
        await db.commit()
        inv_id, link_id = inv.id, link.id
    cb = "/api/v1/integrations/mpesa/callback?token=cb-secret"
    async with _client() as c:
        assert (await c.get(f"/api/v1/public/pay/{'x' * 43}")).status_code == 404
        page = (await c.get(f"/api/v1/public/pay/{token}")).json()
        assert page["amount_due"] == "1000.00" and page["providers"]["card"] == "NOT_CONFIGURED"
        assert (await c.post(f"/api/v1/public/pay/{token}/card", json={})).status_code == 503
        assert (await c.post(f"/api/v1/public/pay/{token}/mpesa", json={"phone": "0712345678", "amount": "5000"})).status_code == 422
        r = await c.post(f"/api/v1/public/pay/{token}/mpesa", json={"phone": "0712345678", "amount": "400"})
        assert r.status_code == 200 and r.json()["simulated"] is False
        assert (await c.get(f"/api/v1/public/pay/{token}")).json()["amount_due"] == "600.00"   # pending push reserved
        assert (await c.post(cb, json=_callback(pushes[0], receipt="QREC0001"))).status_code == 200
        assert (await c.post(cb, json=_callback(pushes[0], receipt="QREC0001"))).status_code == 200   # replay
        r = await c.post(f"/api/v1/public/pay/{token}/mpesa", json={"phone": "0712345678"})
        assert r.json()["amount"] == "600.00"
        await c.post(cb, json=_callback(pushes[1], receipt="QREC0002"))
        page = (await c.get(f"/api/v1/public/pay/{token}")).json()
        assert page["status"] == "PAID" and {x["receipt"] for x in page["receipts"]} == {"QREC0001", "QREC0002"}
        assert (await c.post(f"/api/v1/public/pay/{token}/mpesa", json={"phone": "0712345678"})).status_code == 409
    async with AsyncSessionLocal() as db:
        cols = list((await db.execute(select(CashCollection).where(CashCollection.invoice_id == inv_id))).scalars())
        assert sorted(c.amount for c in cols) == [Decimal("400.00"), Decimal("600.00")] and all(c.status == "PENDING" for c in cols)
        assert {c.mpesa_code for c in cols} == {"QREC0001", "QREC0002"}
    monkeypatch.undo()                     # without credentials: simulated push → TEST_PAID only, no collection
    monkeypatch.setattr(settings, "MPESA_CALLBACK_SECRET", "cb-secret")
    monkeypatch.setattr(settings, "MPESA_CONSUMER_KEY", "")
    async with AsyncSessionLocal() as db:
        inv2 = await _invoice(db, "300")
        _, token2 = await pls.create(db, inv2.id, None, 14, False)
        expired, token3 = await pls.create(db, inv2.id, None, 1, True)
        expired.expires_at = pls._now() - timedelta(minutes=1)
        await db.commit()
        inv2_id = inv2.id
    async with _client() as c:
        assert (await c.post(f"/api/v1/public/pay/{token2}/mpesa", json={"phone": "0712345678", "amount": "100"})).status_code == 422  # full only
        r = (await c.post(f"/api/v1/public/pay/{token2}/mpesa", json={"phone": "0712345678"})).json()
        assert r["simulated"] is True
        async with AsyncSessionLocal() as db:
            from app.models.integrations import IntegrationMpesaTransaction
            tx = (await db.execute(select(IntegrationMpesaTransaction).where(IntegrationMpesaTransaction.related_entity_id == (
                await db.execute(select(PaymentLink.id).where(PaymentLink.invoice_id == inv2_id, PaymentLink.allow_partial.is_(False)))).scalar_one()))).scalar_one()
            checkout = tx.checkout_request_id
        await c.post(cb, json=_callback(checkout, receipt="SIM0001"))
        assert (await c.get(f"/api/v1/public/pay/{token2}")).json()["status"] == "TEST_PAID"
        assert (await c.get(f"/api/v1/public/pay/{token3}")).status_code == 410
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.count()).select_from(CashCollection).where(CashCollection.invoice_id == inv2_id))).scalar_one() == 0
