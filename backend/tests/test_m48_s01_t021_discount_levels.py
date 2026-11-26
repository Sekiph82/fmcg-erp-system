"""M48.S01.T021 regression: the M41 discount approval and the M45 CPQ approval levels are one approval state.

approve_discount records the next open CPQ level for its approver; the last level (either path) sets DISCOUNT_APPROVED;
each level needs a different person with that level's right; an edit drops every approval. DB part needs M48_DB=1."""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

pytestmark = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the disposable M48 PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    from app.db.session import engine
    await engine.dispose()


async def _actor(db, *codes):
    from app.models.role import Permission, Role
    from app.models.user import User
    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, module=code.split(".")[0], action=code.split(".", 1)[1], name=code, is_active=True)
            db.add(p)
            await db.flush()
        perms.append(p)
    tag = uuid4().hex
    u = User(email=f"t021-{tag}@povu-demo.test", username=f"t021{tag}", full_name="POVU Sales", is_active=True,
             hashed_password="synthetic-test-only-not-a-credential", is_superuser=False,
             roles=[Role(name=f"POVU t021 role {tag}", is_active=True, permissions=perms)])
    db.add(u)
    await db.flush()
    return u.id


async def _load(db, uid):
    from app.models.role import Role
    from app.models.user import User
    return (await db.execute(select(User).where(User.id == uid).options(
        selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.access_scopes),
        selectinload(User.access_scopes)))).scalar_one()


@pytest.mark.asyncio
async def test_discount_approval_drives_cpq_levels_and_back():
    from app.api.v1.endpoints import quotation as api
    from app.db.session import AsyncSessionLocal
    from app.models.cpq import QuoteApproval
    from app.models.master import Product, ProductCategory
    from app.models.quotation import QuoteStatus
    from app.models.sales import Customer, CustomerChannel
    from app.schemas.quotation import QuotationCreate, QuotationLineCreate, QuotationUpdate
    from app.services import approval_inbox_service as inbox
    from app.services import cpq_service as cpq

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        cust = Customer(code=f"T021-{tag}", name="POVU Duka Kilimani", channel=CustomerChannel.RETAIL, currency="KES",
                        email=f"buyer-{tag}@povu-demo.test")
        prod = Product(sku=f"POVU-ALC-1L-{tag}", name="POVU AllClean 1 L", category=ProductCategory.HOUSEHOLD, selling_price=Decimal("210"))
        db.add_all([cust, prod])
        await db.flush()
        rep_id = await _actor(db, "sales.view_all", "sales.create_all", "sales.edit_all")
        mgr_id = await _actor(db, "sales.view_all", "sales.approve_all")
        mgr2_id = await _actor(db, "sales.view_all", "sales.approve_all")
        fin_id = await _actor(db, "sales.view_all", "finance.approve")
        cfo_id = await _actor(db, "sales.view_all", "sales.approve_all", "finance.approve")
        await db.commit()
        cust_id, prod_id = cust.id, prod.id

        async def users():
            return [await _load(db, i) for i in (rep_id, mgr_id, mgr2_id, fin_id, cfo_id)]

        def body(disc):
            return QuotationCreate(customer_id=cust_id, quote_date=date(2026, 11, 26), valid_until=date(2099, 1, 1), currency="KES",
                                   lines=[QuotationLineCreate(line_no=1, product_id=prod_id, qty=Decimal("10"), unit="CTN",
                                                              unit_price=Decimal("200"), discount_pct=disc, tax_rate=Decimal("16"))])

        async def refused(call, status):
            nonlocal rep, mgr, mgr2, fin, cfo
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == status, e.value.detail
            await db.rollback()
            rep, mgr, mgr2, fin, cfo = await users()
            return e.value.detail

        rep, mgr, mgr2, fin, cfo = await users()
        # 30 %: level 1 (sales.approve, over 10 %) and level 2 (finance.approve, over 25 %)
        q = await api.create_quote(body(Decimal("30")), db, rep)
        assert q.approval_status == "PENDING_DISCOUNT" and q.access.can_discount_approve is False
        ok = await api.approve_discount(q.id, api.DiscountDecisionIn(), db, mgr)               # level 1 via the M41 path
        assert ok.approval_status == "PENDING_DISCOUNT" and ok.discount_approved_at is None   # level 2 still open
        st = await cpq.approval_state(db, await cpq._quote(db, q.id))
        assert [l["approved_by"] is not None for l in st["levels"]] == [True, False]
        assert "approval" in await refused(lambda: api.send_quote(q.id, db, rep), 409)
        assert "different approver" in await refused(lambda: api.approve_discount(q.id, api.DiscountDecisionIn(), db, mgr), 403)
        assert "finance.approve" in await refused(lambda: api.approve_discount(q.id, api.DiscountDecisionIn(), db, mgr2), 403)
        await refused(lambda: api.approve_discount(q.id, api.DiscountDecisionIn(), db, fin), 403)   # no sales approve right: M41 path refused
        # UI hints and the inbox follow the levels: level-1 approver is done, a second sales approver cannot do level 2
        assert (await api.get_quote(q.id, db, mgr)).access.can_discount_approve is False
        assert (await api.get_quote(q.id, db, mgr2)).access.can_discount_approve is False
        assert (await api.get_quote(q.id, db, cfo)).access.can_discount_approve is True
        assert all(str(q.id) not in [i["id"] for i in g["items"]] for g in (await inbox.inbox(db, mgr))["groups"])
        # level 2 through the CPQ panel path completes it and sets DISCOUNT_APPROVED (one state)
        st = await cpq.approve_level(db, q.id, fin)
        await db.commit()
        assert st["complete"]
        rep, mgr, mgr2, fin, cfo = await users()
        assert (await api.get_quote(q.id, db, rep)).approval_status == "DISCOUNT_APPROVED"
        # an edit after approval drops both the decision and every level row
        again = await api.update_quote(q.id, QuotationUpdate(lines=body(Decimal("29")).lines), db, rep)
        assert again.approval_status == "PENDING_DISCOUNT" and again.discount_approved_at is None
        assert (await db.execute(select(func.count()).select_from(QuoteApproval).where(QuoteApproval.quote_id == q.id))).scalar_one() == 0
        rep, mgr, mgr2, fin, cfo = await users()
        await api.approve_discount(q.id, api.DiscountDecisionIn(), db, mgr2)                  # level 1
        done = await api.approve_discount(q.id, api.DiscountDecisionIn(), db, cfo)            # level 2, both rights
        assert done.approval_status == "DISCOUNT_APPROVED" and done.discount_approved_at is not None
        assert (await api.send_quote(q.id, db, rep)).status == QuoteStatus.SENT

        # 12 %: one level; approved in the CPQ panel -> the M41 state is approved too, a second M41 approval is refused
        rep, mgr, mgr2, fin, cfo = await users()
        one = await api.create_quote(body(Decimal("12")), db, rep)
        await cpq.approve_level(db, one.id, mgr)
        await db.commit()
        rep, mgr, mgr2, fin, cfo = await users()
        assert (await api.get_quote(one.id, db, rep)).approval_status == "DISCOUNT_APPROVED"
        await refused(lambda: api.approve_discount(one.id, api.DiscountDecisionIn(), db, mgr2), 409)
        assert (await api.send_quote(one.id, db, rep)).status == QuoteStatus.SENT

        # a rejected discount cannot be approved through the CPQ path either
        rep, mgr, mgr2, fin, cfo = await users()
        rej = await api.create_quote(body(Decimal("12")), db, rep)
        await api.reject_discount(rej.id, api.DiscountDecisionIn(reason="Max 10 % for Kilimani"), db, mgr)
        rep, mgr, mgr2, fin, cfo = await users()
        with pytest.raises(cpq.CPQError) as e:
            await cpq.approve_level(db, rej.id, mgr2)
        assert e.value.status == 409
