"""M40.S02.T001 on disposable PostgreSQL: every waiting approval reaches its approver — the "My Approvals" inbox shows
only what the user may decide (broad rights see all, own-scope rights only rows in their scope), and each newly
waiting item is sent once to exactly those people's notification bell."""
from __future__ import annotations

import os
import re
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine

TASK_DB_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s02_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _actor(db, *codes, department=None):
    from app.models.role import AccessScope, Permission, Role
    from app.models.user import User

    perms = []
    for code in codes:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, module=code.split(".")[0], action=code.split(".", 1)[1], name=code, is_active=True)
            db.add(p)
        perms.append(p)
    tag = uuid4().hex
    u = User(email=f"m40-inbox-{tag}@example.invalid", username=f"m40inbox{tag}", full_name="POVU Approver",
             hashed_password="synthetic-test-only-not-a-credential", is_active=True, is_superuser=False,
             roles=[Role(name=f"POVU inbox role {tag}", is_active=True, permissions=perms)])
    if department:
        u.access_scopes = [AccessScope(scope_type="department", scope_id=department, can_view=True, can_create=True, can_approve=True)]
    db.add(u)
    await db.flush()
    return u.id


async def _load(db, uid):
    from sqlalchemy.orm import selectinload

    from app.models.role import Role
    from app.models.user import User

    return (await db.execute(select(User).where(User.id == uid).options(
        selectinload(User.roles).selectinload(Role.permissions), selectinload(User.roles).selectinload(Role.access_scopes),
        selectinload(User.access_scopes)))).scalar_one()


@pytest.mark.asyncio
async def test_inbox_and_notifications():
    from app.models.notifications import Notification
    from app.models.procurement import PRStatus, PurchaseRequisition
    from app.services import approval_inbox_service as svc

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

        requester = await _actor(db, "procurement.create_all")
        broad = await _actor(db, "procurement.approve_all")
        scoped = await _actor(db, "procurement.approve_own_scope", "procurement.view_all", department=f"POVU-PACK-{tag}")
        plain_hr = await _actor(db, "hr.approve", "procurement.approve")   # plain procurement.approve cannot decide PRs
        pack = PurchaseRequisition(pr_no=f"PR-POVU-P{tag}", requester_id=requester, required_date=date(2026, 12, 1),
                                   department=f"POVU-PACK-{tag}", status=PRStatus.PENDING_APPROVAL)
        other = PurchaseRequisition(pr_no=f"PR-POVU-O{tag}", requester_id=requester, required_date=date(2026, 12, 1),
                                    department=f"POVU-OTHER-{tag}", status=PRStatus.PENDING_APPROVAL)
        draft = PurchaseRequisition(pr_no=f"PR-POVU-D{tag}", requester_id=requester, required_date=date(2026, 12, 1),
                                    department=f"POVU-PACK-{tag}", status=PRStatus.DRAFT)
        db.add_all([pack, other, draft])
        await db.commit()
        pack_id, other_id = str(pack.id), str(other.id)

    async with AsyncSessionLocal() as db:
        b, s, h, r = [await _load(db, x) for x in (broad, scoped, plain_hr, requester)]

        def refs(box):
            return {i["ref"] for g in box["groups"] if g["key"] == "purchase_request" for i in g["items"]}

        assert {f"PR-POVU-P{tag}", f"PR-POVU-O{tag}"} <= refs(await svc.inbox(db, b))
        assert f"PR-POVU-D{tag}" not in refs(await svc.inbox(db, b))
        assert refs(await svc.inbox(db, s)) == {f"PR-POVU-P{tag}"}          # only the request inside their department
        assert refs(await svc.inbox(db, h)) == set() and refs(await svc.inbox(db, r)) == set()
        assert svc.can_decide_any(b) and svc.can_decide_any(s) and svc.can_decide_any(h) and not svc.can_decide_any(r)
        box = await svc.inbox(db, b)
        assert next(g for g in box["groups"] if g["key"] == "purchase_request")["link"].startswith("/dashboard/procurement")

        await svc.notify_new(db)
        await svc.notify_new(db)   # second tick sends nothing new
        rows = (await db.execute(select(Notification.user_id, Notification.reference_id).where(
            Notification.reference_type == "approval:purchase_request",
            Notification.reference_id.in_([pack_id, other_id])))).all()
        got = sorted((u, ref) for u, ref in rows)
        assert got == sorted([(str(broad), pack_id), (str(broad), other_id), (str(scoped), pack_id)])

        # every registry entry is queryable on the migrated schema (columns and status values exist)
        from app.models.user import User
        su = User(id=uuid4(), is_superuser=True, is_active=True, username="su", email="su@example.invalid")
        assert (await svc.inbox(db, su))["total"] >= 2


@pytest.mark.asyncio
async def test_shelf_life_extension_decision_takes_effect_and_names_the_signed_in_user():
    import httpx

    from app.core.deps import get_current_user
    from app.main import app
    from app.models.inventory import Lot
    from app.models.shelf_life import ExtensionStatus, ShelfLifeExtension

    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        approver_id = await _actor(db, "shelf_life.approve")
        lot = Lot(lot_number=f"POVU-AC5-{uuid4().hex[:6]}", expiry_date=date(2026, 12, 1))
        db.add(lot)
        await db.flush()
        ext = ShelfLifeExtension(lot_id=lot.id, original_expiry=date(2026, 12, 1), proposed_expiry=date(2027, 1, 15),
                                 extension_days=45, justification="POVU AllClean stability retest passed")
        db.add(ext)
        await db.commit()
        lot_id, ext_id = lot.id, ext.id
    async with AsyncSessionLocal() as db:
        approver = await _load(db, approver_id)
    app.dependency_overrides[get_current_user] = lambda: approver
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/shelf-life/extensions/{ext_id}/approve?approved_by=Someone%20Else")
            assert r.status_code == 200, r.text
            assert (await c.post(f"/api/v1/shelf-life/extensions/{ext_id}/reject?reason=late")).status_code == 409
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        ext = await db.get(ShelfLifeExtension, ext_id)
        assert ext.status == ExtensionStatus.APPROVED and ext.approved_by == "POVU Approver"
        assert (await db.get(Lot, lot_id)).expiry_date == date(2027, 1, 15)


@pytest.mark.asyncio
async def test_scoped_manager_turns_an_approved_request_into_a_purchase_order():
    import httpx

    from app.core.deps import get_current_user
    from app.main import app
    from app.models.master import Supplier
    from app.models.procurement import PRLine, PRStatus, PurchaseRequisition

    tag = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        requester = await _actor(db, "procurement.create_all")
        mgr = await _actor(db, "procurement.view_all", "procurement.create_own_scope", "procurement.approve_own_scope",
                           department=f"POVU-PACK-{tag}")
        sup = Supplier(code=f"SUP-POVU-{tag}", name="POVU Caps Ltd")
        prs = {}
        for key, dept in (("in", f"POVU-PACK-{tag}"), ("out", f"POVU-OTHER-{tag}")):
            pr = PurchaseRequisition(pr_no=f"PR-POVU-{key.upper()}{tag}", requester_id=requester, required_date=date(2026, 12, 1),
                                     department=dept, status=PRStatus.APPROVED)
            pr.lines = [PRLine(line_no=1, description="POVU AllClean 5L caps", quantity=2000, unit="PCS", estimated_unit_cost=4)]
            prs[key] = pr
        db.add_all([sup, *prs.values()])
        await db.commit()
        ids = {k: v.id for k, v in prs.items()}
        sup_id = sup.id
    async with AsyncSessionLocal() as db:
        manager = await _load(db, mgr)
    app.dependency_overrides[get_current_user] = lambda: manager
    body = {"supplier_id": str(sup_id), "order_date": "2026-11-21", "expected_delivery_date": "2026-12-05", "currency": "KES"}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            listed = {p["pr_no"]: p["access"] for p in (await c.get("/api/v1/procurement/pr/")).json()}
            assert listed[f"PR-POVU-IN{tag}"]["can_convert"] is True and listed[f"PR-POVU-OUT{tag}"]["can_convert"] is False
            r = await c.post(f"/api/v1/procurement/pr/{ids['in']}/convert", json={**body, "po_no": f"PO-POVU-{tag}"})
            assert r.status_code == 201, r.text
            assert (await c.post(f"/api/v1/procurement/pr/{ids['out']}/convert", json={**body, "po_no": f"PO-POVU-X{tag}"})).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    async with AsyncSessionLocal() as db:
        assert (await db.get(PurchaseRequisition, ids["in"])).status == PRStatus.CONVERTED
