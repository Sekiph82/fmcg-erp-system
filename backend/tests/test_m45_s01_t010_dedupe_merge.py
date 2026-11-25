"""M45.S01.T010 duplicate detection and merge (unit; DB part needs M45_DB=1).

Unit: fuzzy pair score. DB: synthetic duplicate customers with orders, invoices, tickets, a shared group membership
and a contact association → candidates found; preview counts; merge moves every reference (no orphan, no duplicate
order), drops the duplicate membership, fills empty fields, the stricter unsubscribe wins, the loser is deactivated;
a second merge of the same loser is refused; undo restores everything; concurrent merges of one pair → one wins;
contacts merge with associations; dismissed pairs are not suggested again.
"""
import asyncio
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import dedupe_service as dd

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
ADMIN = SimpleNamespace(id=None, username="steward", email=None, full_name="Data steward")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_pair_score():
    a = {"n": "mama mboga", "phone": "+254711000111", "tax": None, "email": None, "addr": "moi avenue 12"}
    b = {"n": "mama mbogaa", "phone": "+254711000111", "tax": None, "email": None, "addr": "moi avenue 12"}
    s, why = dd.pair_score(a, b)
    assert s >= 0.9 and "same phone" in why and "similar address" in why
    s2, _ = dd.pair_score(a, {"n": "kibanda fresh", "phone": None, "tax": None, "email": None, "addr": ""})
    assert s2 < 0.5


async def _pair(db, s):
    from app.models.crm import (CRMAccountGroup, CRMAccountGroupMember, CRMContact, CRMContactAssociation,
                                CRMContactConsent)
    from app.models.helpdesk import HelpdeskTicket
    from app.models.sales import Customer, Invoice, InvoiceStatus, SalesOrder, SOStatus
    keep = Customer(code=f"K-{s}", name=f"Mama Mboga {s} Ltd", currency="KES", phone="0711000111", email=f"keep{s}@povu-demo.test")
    dup = Customer(code=f"D-{s}", name=f"Mama Mboga {s}", currency="KES", phone="+254 711 000 111", city="Nairobi",
                   tax_id="P051234567Z", email=f"dup{s}@povu-demo.test")
    db.add_all([keep, dup])
    await db.flush()
    sos = []
    for c in (keep, dup, dup):
        so = SalesOrder(order_no=f"SO-{uuid.uuid4().hex[:8]}", customer_id=c.id, order_date=date.today(),
                        requested_delivery_date=date.today(), status=SOStatus.INVOICED, currency="KES")
        db.add(so)
        sos.append(so)
    await db.flush()
    db.add(Invoice(invoice_no=f"INV-{uuid.uuid4().hex[:8]}", so_id=sos[1].id, customer_id=dup.id, invoice_date=date.today(),
                   due_date=date.today(), status=InvoiceStatus.ISSUED, currency="KES", total_amount=Decimal("10")))
    db.add(HelpdeskTicket(ticket_no=f"TKT-{uuid.uuid4().hex[:6]}", customer_id=dup.id, subject="late"))
    g = CRMAccountGroup(name=f"Key {s}")
    db.add(g)
    await db.flush()
    db.add_all([CRMAccountGroupMember(group_id=g.id, customer_id=keep.id), CRMAccountGroupMember(group_id=g.id, customer_id=dup.id)])
    ct = CRMContact(full_name="Buyer", email=f"buyer{s}@povu-demo.test")
    db.add(ct)
    await db.flush()
    db.add(CRMContactAssociation(contact_id=ct.id, object_type="customer", object_id=dup.id, label="primary", created_at=datetime.now(timezone.utc)))
    db.add_all([CRMContactConsent(email=f"keep{s}@povu-demo.test", status="SUBSCRIBED", updated_at=datetime.now(timezone.utc)),
                CRMContactConsent(email=f"dup{s}@povu-demo.test", status="UNSUBSCRIBED", updated_at=datetime.now(timezone.utc))])
    await db.flush()
    return keep, dup, g


@DB
@pytest.mark.asyncio
async def test_customer_merge_and_undo():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMAccountGroupMember, CRMContactAssociation, CRMContactConsent
    from app.models.helpdesk import HelpdeskTicket
    from app.models.sales import Customer, Invoice, SalesOrder
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        keep, dup, g = await _pair(db, s)
        await db.commit()
        kid, did, gid = keep.id, dup.id, g.id
    async with AsyncSessionLocal() as db:
        pairs = await dd.candidates(db, "customer")
        assert any({p["a_id"], p["b_id"]} == {str(kid), str(did)} for p in pairs)
        pv = await dd.preview(db, "customer", kid, did)
        moves = {m["table"]: m["rows"] for m in pv["moves"]}
        assert moves["sales_orders"] == 2 and moves["invoices"] == 1 and moves["helpdesk_tickets"] == 1
        assert pv["fills"]["city"] == "Nairobi" and pv["consent"]["after"] == "UNSUBSCRIBED"
        count = lambda M, col: select(func.count()).select_from(M).where(col == kid)
        before = (await db.execute(select(func.count()).select_from(SalesOrder))).scalar_one()
        lid = (await dd.merge(db, "customer", kid, did, ADMIN, "same outlet")).id
        await db.commit()
        assert (await db.execute(count(SalesOrder, SalesOrder.customer_id))).scalar_one() == 3
        assert (await db.execute(select(func.count()).select_from(SalesOrder))).scalar_one() == before      # nothing copied
        assert (await db.execute(select(func.count()).select_from(SalesOrder).where(SalesOrder.customer_id == did))).scalar_one() == 0
        assert (await db.execute(count(Invoice, Invoice.customer_id))).scalar_one() == 1
        assert (await db.execute(count(HelpdeskTicket, HelpdeskTicket.customer_id))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(CRMAccountGroupMember).where(CRMAccountGroupMember.group_id == gid))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(CRMContactAssociation).where(CRMContactAssociation.object_id == kid))).scalar_one() == 1
        k, d = await db.get(Customer, kid), await db.get(Customer, did)
        await db.refresh(k); await db.refresh(d)
        assert k.city == "Nairobi" and k.tax_id == "P051234567Z" and not d.is_active and f"Merged into K-{s}" in d.notes
        assert (await db.execute(select(CRMContactConsent.status).where(CRMContactConsent.email == f"keep{s}@povu-demo.test"))).scalar_one() == "UNSUBSCRIBED"
        with pytest.raises(dd.MergeError):
            await dd.merge(db, "customer", kid, did, ADMIN)                                  # already merged
        await db.rollback()
        await dd.undo(db, lid, ADMIN)
        await db.commit()
        assert (await db.execute(select(func.count()).select_from(SalesOrder).where(SalesOrder.customer_id == did))).scalar_one() == 2
        assert (await db.execute(select(func.count()).select_from(CRMAccountGroupMember).where(CRMAccountGroupMember.group_id == gid))).scalar_one() == 2
        d = await db.get(Customer, did)
        await db.refresh(d)
        assert d.is_active
        assert (await db.execute(select(CRMContactConsent.status).where(CRMContactConsent.email == f"keep{s}@povu-demo.test"))).scalar_one() == "SUBSCRIBED"
        with pytest.raises(dd.MergeError):
            await dd.undo(db, lid, ADMIN)


@DB
@pytest.mark.asyncio
async def test_concurrent_merge_one_wins_and_contacts_and_dismiss():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMContactAssociation
    from app.models.sales import Customer
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        keep, dup, _ = await _pair(db, s)
        await db.commit()
        kid, did = keep.id, dup.id

    async def attempt(a, b):
        async with AsyncSessionLocal() as db:
            try:
                await dd.merge(db, "customer", a, b, ADMIN)
                await db.commit()
                return "ok"
            except dd.MergeError:
                await db.rollback()
                return "refused"
    res = await asyncio.gather(attempt(kid, did), attempt(did, kid))
    assert sorted(res) == ["ok", "refused"]
    async with AsyncSessionLocal() as db:
        active = (await db.execute(select(func.count()).select_from(Customer).where(Customer.id.in_([kid, did]), Customer.is_active.is_(True)))).scalar_one()
        assert active == 1
        a = CRMContact(full_name="Peter Otieno", email=f"po{s}@povu-demo.test")
        b = CRMContact(full_name="Peter Otieno", phone="0722111222")
        db.add_all([a, b])
        await db.flush()
        db.add(CRMContactAssociation(contact_id=b.id, object_type="customer", object_id=kid, label="primary", created_at=datetime.now(timezone.utc)))
        await db.flush()
        log = await dd.merge(db, "contact", a.id, b.id, ADMIN)
        await db.flush()
        assert (await db.execute(select(func.count()).select_from(CRMContact).where(CRMContact.id == b.id))).scalar_one() == 0
        assert (await db.execute(select(func.count()).select_from(CRMContactAssociation).where(CRMContactAssociation.contact_id == a.id))).scalar_one() == 1
        await dd.undo(db, log.id, ADMIN)
        await db.flush()
        assert (await db.execute(select(func.count()).select_from(CRMContact).where(CRMContact.id == b.id))).scalar_one() == 1
        x = Customer(code=f"X-{s}", name=f"Zebra Wholesale {s}", currency="KES")
        y = Customer(code=f"Y-{s}", name=f"Zebra Wholesalers {s}", currency="KES")
        db.add_all([x, y])
        await db.flush()
        assert any({p["a_id"], p["b_id"]} == {str(x.id), str(y.id)} for p in await dd.candidates(db, "customer"))
        await dd.dismiss(db, "customer", x.id, y.id, "steward")
        assert not any({p["a_id"], p["b_id"]} == {str(x.id), str(y.id)} for p in await dd.candidates(db, "customer"))
        await db.rollback()
