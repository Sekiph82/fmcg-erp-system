"""M46.S01.T008 M45 carry-overs (unit; DB part needs M46_DB=1).

Unit: workflow graphs exported in config bundles lose user ids and e-mail addresses. DB: the daily ledger runs each
step once per day, a failing step is retried while the others are not skipped; an STK push with no callback stops
reserving the balance after the TTL and a late success still settles.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_strip_people_from_graphs():
    from app.services.config_bundle_service import strip_people
    g = {"nodes": [{"id": "a", "config": {"action": "assign_owner", "user_id": "42", "to": "boss@povu.example.com", "subject": "Hi"}},
                   {"id": "b", "config": {"owner_user_ids": ["1", "2"], "event": "won"}}]}
    out = strip_people(g)
    assert out["nodes"][0]["config"] == {"action": "assign_owner", "user_id": None, "to": "<set after import>", "subject": "Hi"}
    assert out["nodes"][1]["config"] == {"owner_user_ids": None, "event": "won"}


@DB
@pytest.mark.asyncio
async def test_daily_ledger_isolates_steps(monkeypatch):
    from app.db.session import AsyncSessionLocal
    from app.services import hub_tick
    calls = {"a": 0, "b": 0}

    async def ok(db):
        calls["a"] += 1

    async def boom(db):
        calls["b"] += 1
        raise RuntimeError("provider down")
    monkeypatch.setattr(hub_tick, "DAILY", {"a": ok, "b": boom})
    async with AsyncSessionLocal() as db:
        first = await hub_tick.run_daily_steps(db, date(2026, 11, 27))
        again = await hub_tick.run_daily_steps(db, date(2026, 11, 27))
    assert first == {"a": "ran", "b": "failed"} and again == {"a": "done", "b": "failed"}
    assert calls == {"a": 1, "b": 2}                              # a ran once; b retried; neither blocked the other


@DB
@pytest.mark.asyncio
async def test_pending_push_expires_and_late_success_settles(monkeypatch):
    from sqlalchemy import update
    from app.db.session import AsyncSessionLocal
    from app.models.integrations import MpesaTxStatus
    from app.models.payments_hub import PaymentLinkAttempt
    from app.models.sales import Customer, Invoice, InvoiceStatus, SalesOrder, SOStatus
    from app.services import mpesa_daraja_service as daraja
    from app.services import payment_link_service as pls

    async def push(phone, amount, reference, description="Payment"):
        cid = f"ws_CO_LIVE_{uuid.uuid4().hex[:10]}"
        return cid, "MR", {"ResponseCode": "0", "CheckoutRequestID": cid}
    monkeypatch.setattr(daraja, "_stk_push_request", push)
    async with AsyncSessionLocal() as db:
        c = Customer(code=f"PT-{uuid.uuid4().hex[:5]}", name="POVU Pending Outlet", currency="KES")
        db.add(c)
        await db.flush()
        so = SalesOrder(order_no=f"SO-{uuid.uuid4().hex[:8]}", customer_id=c.id, order_date=date.today(), requested_delivery_date=date.today(),
                        status=SOStatus.INVOICED, currency="KES")
        db.add(so)
        await db.flush()
        inv = Invoice(invoice_no=f"INV-{uuid.uuid4().hex[:8]}", so_id=so.id, customer_id=c.id, invoice_date=date.today(),
                      due_date=date.today(), status=InvoiceStatus.ISSUED, currency="KES", total_amount=Decimal("300"), paid_amount=Decimal("0"))
        db.add(inv)
        await db.flush()
        link, token = await pls.create(db, inv.id, None, 7, True)
        a = await pls.pay_mpesa(db, token, "0712345678", Decimal("300"))
        assert await pls.open_balance(db, inv) == Decimal("0.00")                  # reserved while pending
        await db.execute(update(PaymentLinkAttempt).where(PaymentLinkAttempt.id == a.id)
                         .values(created_at=datetime.now(timezone.utc) - timedelta(minutes=20)))
        assert await pls.open_balance(db, inv) == Decimal("300.00")                # TTL passed: released
        assert await pls.expire_stale(db) == 1
        await db.refresh(a)
        assert a.status == "EXPIRED"
        from app.models.integrations import IntegrationMpesaTransaction
        tx = await db.get(IntegrationMpesaTransaction, a.mpesa_tx_id)
        tx.status, tx.mpesa_receipt_number = MpesaTxStatus.SUCCESS, "QLATE001"
        settled = await pls.on_mpesa_callback(db, tx)
        assert settled.status == "SETTLED"                                         # the money moved: still recorded
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_custom_objects_in_report_builder():
    from types import SimpleNamespace
    from app.db.session import AsyncSessionLocal
    from app.models.custom_objects import CustomObjectType
    from app.services import custom_object_service as cos
    from app.services import report_builder_service as rbs
    admin = SimpleNamespace(id=None, username="admin", is_superuser=True, roles=[], access_scopes=[])
    rep = SimpleNamespace(id=None, username="rep", is_superuser=False, access_scopes=[],
                          roles=[SimpleNamespace(name="Sales rep", is_active=True, access_scopes=[],
                                                 permissions=[SimpleNamespace(code="crm.view", is_active=True)])])
    key = f"cool{uuid.uuid4().hex[:5]}"
    async with AsyncSessionLocal() as db:
        t = CustomObjectType(**cos.validate_type({"key": key, "label": "Cooler", "fields": [
            {"key": "serial", "label": "Serial", "type": "text", "required": True},
            {"key": "litres", "label": "Litres", "type": "number"}]}), created_by="admin")
        db.add(t)
        await db.flush()
        for i in range(3):
            await cos.upsert(db, t, {"serial": f"C-{i}", "litres": str(100 + i)}, admin)
        assert f"co:{key}" in await cos.catalog(db, rep)
        out = await rbs._execute_query(db, f"co:{key}", [{"path": "serial"}, {"path": "litres"}],
                                       [{"field_path": "serial", "operator": "eq", "value": "C-1"}], 10, 0, user=rep)
        assert out["rows"] == [{"serial": "C-1", "litres": "101.0"}]
        none = await rbs._execute_query(db, f"co:{key}", [{"path": "serial"}], [], 10, 0, user=None)
        assert none["rows"] == [] and "signed-in" in none["error"]
        t.view_roles = ["Freezer team"]                      # per-type roles also apply in the report builder
        await db.flush()
        assert f"co:{key}" not in await cos.catalog(db, rep)
        assert (await rbs._execute_query(db, f"co:{key}", [{"path": "serial"}], [], 10, 0, user=rep))["rows"] == []
        await db.rollback()
