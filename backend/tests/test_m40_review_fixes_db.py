"""M40 independent-review fixes on disposable PostgreSQL: approval-level actions need an approval right, customer
payments need finance, approvals/chatter/calendar ownership, appraisal roles, technician id validation."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
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


def _user(*codes, uid=None, username="u", full_name="U"):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid or uuid4(), is_superuser=False, is_active=True, full_name=full_name, username=username,
                           email="t@povu.example", access_scopes=[], company_id=None, branch_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_review_fixes():
    from app.core.deps import get_current_user
    from app.main import app

    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

    who = {"u": None}
    app.dependency_overrides[get_current_user] = lambda: who["u"]
    fake = uuid4()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            async def call(user, method, path, **kw):
                who["u"] = user
                return (await c.request(method, "/api/v1" + path, **kw)).status_code

            pay = {"json": {"amount": 10, "payment_date": "2026-11-21", "method": "cash"}}
            # customer payments are a finance task: a sales write right is not enough
            assert await call(_user("sales.view", "sales.create"), "POST", f"/sales/invoices/{fake}/payments", **pay) == 403
            assert await call(_user("finance.view", "finance.create"), "POST", f"/sales/invoices/{fake}/payments", **pay) == 404
            # approvals need an approval right, not just any write right (segregation of duties)
            assert await call(_user("sales.create"), "POST", f"/commissions/transactions/{fake}/approve") == 403
            assert await call(_user("sales.approve"), "POST", f"/commissions/transactions/{fake}/approve") in (404, 400, 422)
            assert await call(_user("finance.create"), "POST", "/fixed-assets/depreciation/post", json={}) == 403
            # MRP results were left open by an incidental word match before; now they need a planning-type right
            assert await call(_user("crm.view"), "GET", f"/mrp/runs/{fake}/results") == 403
            # custom-field definitions are administration
            assert await call(_user("sales.create"), "POST", "/custom-fields", json={}) == 403
            # appraisals: a payroll clerk (not HR) gets only their own/team rows — none here
            who["u"] = _user("payroll.view")
            r = await c.get("/api/v1/appraisals/")
            assert r.status_code == 200 and r.json() == []
            # calendar: shift approval needs an HR/operations right; the approver is the signed-in user
            assert await call(_user("crm.view"), "PATCH", f"/calendar/shifts/{fake}/approve") == 403
            # technician assignment: a malformed id is a 422, not a crash
            assert await call(_user("maintenance.create", "maintenance.view"), "POST", "/maintenance/breakdowns/",
                              json={"asset_id": str(fake), "start_time": "2026-11-21T08:00:00Z", "reason": "x",
                                    "assigned_to_id": "not-a-uuid"}) in (404, 422)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # approvals: only the requester (or an administrator) cancels; others do not even see it
    from app.api.v1.endpoints import approvals
    from app.models.user import User
    from app.models.workflow import ApprovalModule, ApprovalRequest
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        owner = User(email=f"o-{s}@povu.example", username=f"o{s}", full_name="Owner", hashed_password="x")
        db.add(owner)
        await db.flush()
        req = ApprovalRequest(module=list(ApprovalModule)[0], object_id=uuid4(), object_ref=f"PO-{s}", requested_by_id=owner.id)
        db.add(req)
        await db.commit()
        rid, oid = req.id, owner.id
        stranger = _user("crm.view")
        with pytest.raises(HTTPException) as e:
            await approvals.cancel(rid, db, stranger)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await approvals.get_approval_request(rid, db, stranger)
        assert e.value.status_code == 404
        assert (await approvals.get_approval_request(rid, db, _user(uid=oid)))
        await approvals.cancel(rid, db, _user(uid=oid))

    # chatter: author comes from the session; only the author edits or deletes
    from app.api.v1.endpoints import chatter
    from app.models.chatter import ActivityComment
    async with AsyncSessionLocal() as db:
        from app.models.chatter import Activity
        act = Activity(reference_type="customer", reference_id=str(uuid4()), title="Call notes")
        db.add(act)
        await db.flush()
        com = ActivityComment(activity_id=act.activity_id, user_id=str(oid), user_name="Owner", message="POVU AllClean reorder")
        db.add(com)
        await db.commit()
        with pytest.raises(HTTPException) as e:
            await chatter._own_comment(db, com.comment_id, _user())
        assert e.value.status_code == 403
        await chatter._own_comment(db, com.comment_id, _user(uid=oid))

    # appraisals: employee → own self-review only; manager → team; HR approval right → finalize
    from app.api.v1.endpoints import appraisals as ap
    async with AsyncSessionLocal() as db:
        emp, mgr = str(uuid4()), str(uuid4())
        rec = SimpleNamespace(employee_id=emp, manager_id=mgr)
        me = _user("hr.view_own_scope", uid=uuid4())
        orig = ap._my_employee_ids

        async def ids_for(_db, user):
            return {emp} if user is me else ({mgr} if user.username == "boss" else set())
        ap._my_employee_ids = ids_for
        try:
            assert await ap._may(db, rec, me, "self") and not await ap._may(db, rec, me, "manager")
            boss = _user(username="boss")
            assert await ap._may(db, rec, boss, "manager") and not await ap._may(db, rec, boss, "self")
            assert not await ap._may(db, rec, _user("hr.view"), "view")          # hr.view alone is not HR
            assert not await ap._may(db, rec, _user("hr.edit"), "hr_approve")
            assert await ap._may(db, rec, _user("hr.approve"), "hr_approve")
        finally:
            ap._my_employee_ids = orig
