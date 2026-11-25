"""M45.S01.T019 service routing, conditional SLAs and surveys (unit; DB part needs M45_DB=1).

Unit: business-hours arithmetic (evening → next morning, weekend skip, holiday). DB: tickets created through the
real endpoint are routed by skill and round robin with capacity; the tier-1 policy wins for a key account; pause
and resume shift the due time; a tick marks the breach once; closing sends CSAT and CES once each; a survey is
answered once with range checks; the report shows averages and SLA met %.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import service_desk_service as sd

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
CFG = {**sd.DEFAULTS, "weekdays": [0, 1, 2, 3, 4], "holidays": ["2026-12-25"]}


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_business_hours():
    nbo = timezone(timedelta(hours=3))
    thu_4pm = datetime(2026, 11, 26, 16, 0, tzinfo=nbo)
    assert sd.add_business_hours(thu_4pm, 2, CFG) == datetime(2026, 11, 27, 9, 0, tzinfo=nbo).astimezone(timezone.utc)
    fri_4pm = datetime(2026, 11, 27, 16, 0, tzinfo=nbo)
    assert sd.add_business_hours(fri_4pm, 2, CFG) == datetime(2026, 11, 30, 9, 0, tzinfo=nbo).astimezone(timezone.utc)   # weekend
    xmas_eve = datetime(2026, 12, 24, 16, 30, tzinfo=nbo)
    assert sd.add_business_hours(xmas_eve, 1, CFG) == datetime(2026, 12, 28, 8, 30, tzinfo=nbo).astimezone(timezone.utc)  # holiday+weekend
    night = datetime(2026, 11, 26, 22, 0, tzinfo=nbo)
    assert sd.add_business_hours(night, 1, CFG) == datetime(2026, 11, 27, 9, 0, tzinfo=nbo).astimezone(timezone.utc)


async def _staff(db, perms):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    pw = uuid.uuid4().hex + "Aa1!"
    u = User(username=f"sd-{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:6]}@povu-demo.test", full_name="Agent",
             hashed_password=hash_password(pw), is_active=True)
    role = Role(name=f"sd-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    await db.flush()
    return u, pw


@DB
@pytest.mark.asyncio
async def test_routing_sla_surveys():
    from sqlalchemy import func, select, update
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.crm import CRMAccountGroup, CRMAccountGroupMember
    from app.models.helpdesk import HelpdeskTicket
    from app.models.sales import Customer
    from app.models.service_desk import AgentProfile, SLAPolicy, Survey, TicketSLA
    async with AsyncSessionLocal() as db:
        await db.execute(update(AgentProfile).values(presence="OFFLINE"))        # only this test's agents take work
        caller, pw = await _staff(db, ("crm.view", "crm.edit", "crm.edit_all"))
        q1, _ = await _staff(db, ())
        q2, _ = await _staff(db, ())
        gen, _ = await _staff(db, ())
        db.add_all([AgentProfile(user_id=q1.id, skills=["quality"], capacity=1, presence="AVAILABLE"),
                    AgentProfile(user_id=q2.id, skills=["quality"], capacity=5, presence="AVAILABLE"),
                    AgentProfile(user_id=gen.id, skills=["delivery"], capacity=5, presence="AVAILABLE")])
        key = Customer(code=f"KA-{uuid.uuid4().hex[:5]}", name="POVU Key Account", currency="KES", email=f"ka{uuid.uuid4().hex[:4]}@povu-demo.test")
        g = CRMAccountGroup(name=f"Strategic {uuid.uuid4().hex[:4]}")
        db.add_all([key, g])
        await db.flush()
        db.add(CRMAccountGroupMember(group_id=g.id, customer_id=key.id, tier=1))
        db.add_all([SLAPolicy(name="Key accounts", customer_tier=1, first_response_hours=1, resolution_hours=8, business_hours=False, sort=1),
                    SLAPolicy(name="Default", first_response_hours=4, resolution_hours=48, business_hours=True, sort=99)])
        await db.commit()
        ids = {"q1": q1.id, "q2": q2.id, "gen": gen.id, "key": key.id, "user": caller.username}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        assert (await c.post("/api/v1/auth/login", data={"username": ids["user"], "password": pw})).status_code == 200
        made = []
        for cat in ("QUALITY", "QUALITY", "QUALITY", "DELIVERY"):
            r = await c.post("/api/v1/helpdesk/", json={"subject": f"{cat} issue", "category": cat, "priority": "HIGH",
                                                         "source": "PHONE", "customer_id": str(ids["key"])})
            assert r.status_code == 201, r.text
            made.append(r.json()["id"])
    async with AsyncSessionLocal() as db:
        tk = [await db.get(HelpdeskTicket, uuid.UUID(i)) for i in made]
        assert {tk[0].assigned_to_id, tk[1].assigned_to_id} == {ids["q1"], ids["q2"]}       # round robin
        assert tk[2].assigned_to_id == ids["q2"]                                             # q1 at capacity
        assert tk[3].assigned_to_id == ids["gen"]                                            # delivery skill
        s0 = await db.get(TicketSLA, tk[0].id)
        pol = await db.get(SLAPolicy, s0.policy_id)
        assert pol.name == "Key accounts" and abs((s0.first_response_due - tk[0].created_at).total_seconds() - 3600) < 5
        before = s0.resolution_due
        await sd.pause(db, tk[0].id)
        await db.execute(update(TicketSLA).where(TicketSLA.ticket_id == tk[0].id).values(paused_at=datetime.now(timezone.utc) - timedelta(minutes=30)))
        await db.flush()
        await db.refresh(s0)
        await sd.resume(db, tk[0].id)
        await db.flush()
        assert (s0.resolution_due - before) >= timedelta(minutes=29)
        assert await sd.tick(db, now=datetime.now(timezone.utc) + timedelta(hours=2)) >= 1
        await db.refresh(s0)
        assert s0.breached_first and not s0.breached_resolution
        await db.commit()
        before_n = (await db.execute(select(func.count()).select_from(TicketSLA).where(TicketSLA.breached_first.is_(True)))).scalar_one()
        await sd.tick(db, now=datetime.now(timezone.utc) + timedelta(hours=2))
        assert (await db.execute(select(func.count()).select_from(TicketSLA).where(TicketSLA.breached_first.is_(True)))).scalar_one() == before_n
        tokens = await sd.on_closed(db, tk[0])
        assert set(tokens) == {"CSAT", "CES"} and await sd.on_closed(db, tk[0]) == {}         # sent once
        with pytest.raises(ValueError):
            await sd.answer(db, tokens["CES"], 9, None)                                      # out of range 1–7
        await sd.answer(db, tokens["CES"], 6, "easy")
        await sd.answer(db, tokens["CSAT"], 5, None)
        with pytest.raises(ValueError):
            await sd.answer(db, tokens["CSAT"], 4, None)                                     # answered once
        await db.refresh(tk[0])
        assert tk[0].customer_satisfaction == 5
        rep = await sd.report(db)
        assert rep["CES"]["answered"] >= 1 and rep["sla"]["breached"] >= 1
        await db.commit()
