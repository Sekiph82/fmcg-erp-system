"""M38.S01 distributor self-service portal on disposable PostgreSQL through the real app: realm sign-in (separate from
staff), legacy hash upgrade, account isolation, server-side prices, idempotent orders → DRAFT sales orders, roles,
unlinked accounts, password change revoking old sessions, staff invite link → activation."""
from __future__ import annotations

import hashlib
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
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory
from app.models.portal import PortalAccount, PortalAccountStatus, PortalAccountType, PortalUser, PortalUserRole
from app.models.sales import Customer, CustomerChannel, OrderSource, SalesOrder, SOLine, SOStatus

TASK_DB_ENV = "M38_S01_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_S01_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_s01_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")
API = "/api/v1/portal-self"
PW = "Distributor-Pass-2026"


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
async def test_distributor_portal_end_to_end():
    from app.main import app

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        cust_a = Customer(code=f"A-{s}", name=f"Alpha Dist {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        cust_b = Customer(code=f"B-{s}", name=f"Beta Dist {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        juice = Product(sku=f"JUICE-{s}", name=f"Mango Juice {s}", category=ProductCategory.BEVERAGE, selling_price=Decimal("120"),
                        standard_cost=Decimal("70"))
        unpriced = Product(sku=f"NOPRICE-{s}", name=f"Unpriced {s}", category=ProductCategory.BEVERAGE)
        db.add_all([cust_a, cust_b, juice, unpriced])
        await db.flush()
        accounts = {}
        for key, cust in (("a", cust_a), ("b", cust_b), ("unlinked", None)):
            acc = PortalAccount(account_code=f"PA-{key}-{s}", account_type=PortalAccountType.DISTRIBUTOR,
                                linked_customer_id=str(cust.id) if cust else None, portal_status=PortalAccountStatus.ACTIVE)
            db.add(acc)
            await db.flush()
            accounts[key] = acc
        users = {
            "a": PortalUser(portal_account_id=accounts["a"].id, full_name="Ann Buyer", email=f"ann-{s}@example.com",
                            password_hash=hashlib.sha256(PW.encode()).hexdigest(),  # legacy unsalted hash
                            role_type=PortalUserRole.BUYER, is_active=True),
            "viewer": PortalUser(portal_account_id=accounts["a"].id, full_name="Vic Viewer", email=f"vic-{s}@example.com",
                                 password_hash=hash_password(PW), role_type=PortalUserRole.VIEWER, is_active=True),
            "b": PortalUser(portal_account_id=accounts["b"].id, full_name="Ben Buyer", email=f"ben-{s}@example.com",
                            password_hash=hash_password(PW), role_type=PortalUserRole.OWNER, is_active=True),
            "unlinked": PortalUser(portal_account_id=accounts["unlinked"].id, full_name="Uma", email=f"uma-{s}@example.com",
                                   password_hash=hash_password(PW), role_type=PortalUserRole.OWNER, is_active=True),
        }
        db.add_all(users.values())
        # an existing order of customer B that A must never see
        other = SalesOrder(order_no=f"SO-B-{s}", customer_id=cust_b.id, order_date=date.today(),
                           requested_delivery_date=date.today(), currency="KES")
        db.add(other)
        await db.commit()
        ids = SimpleNamespace(juice=juice.id, unpriced=unpriced.id, other=other.id, a_user=users["a"].id,
                              b_cust=cust_b.id, a_cust=cust_a.id)

    async def login(c, email, pw=PW):
        return await c.post(f"{API}/auth/login", json={"email": email, "password": pw})

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    async with _client(app) as anon:
        assert (await anon.get(f"{API}/me")).status_code == 401
        assert (await login(anon, f"ann-{s}@example.com", "wrong")).status_code == 401

    async with _client(app) as a:
        r = await login(a, f"ann-{s}@example.com")
        assert r.status_code == 200 and r.json()["can_order"] is True
        assert "erp_portal_token" in a.cookies and "erp_access_token" not in a.cookies
        assert (await a.get("/api/v1/sales/orders/")).status_code == 401           # portal token is not a staff session
        me = (await a.get(f"{API}/me")).json()
        assert me["linked"] and me["customer_name"] == f"Alpha Dist {s}"

        cat = (await a.get(f"{API}/catalog", params={"search": s})).json()
        skus = {i["sku"]: i for i in cat["items"]}
        assert f"JUICE-{s}" in skus and f"NOPRICE-{s}" not in skus and skus[f"JUICE-{s}"]["unit_price"] == 120.0

        order = {"client_ref": f"ref-{s}", "requested_delivery_date": tomorrow, "notes": "Gate 3",
                 "lines": [{"product_id": str(ids.juice), "quantity": "10", "unit_price": "0.01"}]}  # client price ignored
        first = await a.post(f"{API}/orders", json=order)
        assert first.status_code == 201, first.text
        again = await a.post(f"{API}/orders", json=order)                         # retry/double click
        assert again.json()["id"] == first.json()["id"] and again.json()["duplicate"] is True
        assert first.json()["total"] == 1200.0
        bad = dict(order, client_ref=f"ref2-{s}", lines=[{"product_id": str(ids.unpriced), "quantity": "1"}])
        assert (await a.post(f"{API}/orders", json=bad)).status_code == 422
        past = dict(order, client_ref=f"ref3-{s}", requested_delivery_date="2000-01-01")
        assert (await a.post(f"{API}/orders", json=past)).status_code == 422

        listed = (await a.get(f"{API}/orders")).json()
        assert [o["id"] for o in listed] == [first.json()["id"]]                 # B's order never listed
        assert (await a.get(f"{API}/orders/{ids.other}")).status_code == 404
        detail = (await a.get(f"{API}/orders/{first.json()['id']}")).json()
        assert detail["lines"][0]["product_name"] == f"Mango Juice {s}"
        claim = {"claim_type": "SHORTAGE_CLAIM", "reason": "2 missing", "linked_order_id": str(ids.other)}
        r = await a.post(f"{API}/claims", json=claim)
        assert r.status_code == 422 and "not one of your orders" in r.text        # cannot reference B's order
        r = await a.post(f"{API}/claims", json=dict(claim, linked_order_id=first.json()["id"]))
        assert r.status_code == 201, r.text
        assert [c["claim_no"] for c in (await a.get(f"{API}/claims")).json()] == [r.json()["claim_no"]]

        # changing the password ends other sessions
        async with _client(app) as a2:
            assert (await login(a2, f"ann-{s}@example.com")).status_code == 200
            assert (await a.post(f"{API}/password", json={"current_password": PW, "new_password": PW + "-new"})).status_code == 200
            assert (await a2.get(f"{API}/me")).status_code == 401
            assert (await a.get(f"{API}/me")).status_code == 200
        await a.post(f"{API}/auth/logout")
        assert (await a.get(f"{API}/me")).status_code == 401

    async with _client(app) as v:
        assert (await login(v, f"vic-{s}@example.com")).status_code == 200
        r = await v.post(f"{API}/orders", json=dict(order, client_ref=f"vref-{s}"))
        assert r.status_code == 403
    async with _client(app) as u:
        assert (await login(u, f"uma-{s}@example.com")).status_code == 200
        assert (await u.get(f"{API}/catalog")).status_code == 409
        assert (await u.get(f"{API}/dashboard")).status_code == 409
        assert (await u.get(f"{API}/orders")).status_code == 409

    # staff invite → one-time link → activation; staff routes need sales permissions
    staff = SimpleNamespace(id=uuid.uuid4(), username="sales", email="s@example.com", full_name="S", is_superuser=False,
                            is_active=True, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                            permissions=[SimpleNamespace(code=c, module="sales", action=c.split(".")[1], is_active=True)
                                         for c in ("sales.view", "sales.edit")])])
    nobody = SimpleNamespace(**{**staff.__dict__, "roles": []})
    try:
        async with _client(app) as st:
            app.dependency_overrides[get_current_user] = lambda: nobody
            assert (await st.get("/api/v1/portal/accounts")).status_code == 403
            app.dependency_overrides[get_current_user] = lambda: staff
            inv = await st.post(f"/api/v1/portal/accounts/{accounts['b'].id}/users/invite",
                                json={"full_name": "New", "email": f"new-{s}@example.com", "role_type": "BUYER"})
            assert inv.status_code == 201, inv.text
            token = inv.json()["activation_link"].split("token=")[1]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with _client(app) as n:
        assert (await n.post(f"{API}/auth/activate", json={"token": token, "new_password": "short"})).status_code == 422
        assert (await n.post(f"{API}/auth/activate", json={"token": token, "new_password": PW})).status_code == 200
        assert (await n.post(f"{API}/auth/activate", json={"token": token, "new_password": PW})).status_code == 400  # one-time
        assert (await login(n, f"new-{s}@example.com")).status_code == 200

    async with AsyncSessionLocal() as db:
        so = (await db.execute(select(SalesOrder).where(SalesOrder.offline_id == f"portal:{accounts['a'].id}:ref-{s}"))).scalar_one()
        assert (so.status, so.source, so.customer_id, so.currency) == (SOStatus.DRAFT, OrderSource.DISTRIBUTOR, ids.a_cust, "KES")
        line = (await db.execute(select(SOLine).where(SOLine.so_id == so.id))).scalar_one()
        assert (line.unit_price, line.ordered_quantity) == (Decimal("120.0000"), Decimal("10.000"))
        assert (await db.execute(select(func.count()).select_from(SalesOrder).where(
            SalesOrder.offline_id.like(f"portal:{accounts['a'].id}:%")))).scalar_one() == 1
        upgraded = await db.get(PortalUser, ids.a_user)
        assert upgraded.password_hash.startswith("$2")                            # legacy hash replaced by bcrypt
        stored = (await db.execute(select(PortalUser.invitation_token).where(PortalUser.email == f"new-{s}@example.com"))).scalar_one()
        assert stored is None
