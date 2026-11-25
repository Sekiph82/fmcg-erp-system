"""M45.S01.T023 audited impersonation and notification defaults (DB, M45_DB=1), through real login sessions.

Refused without the right, without a reason, for a superuser target and for oneself; with the right: /status shows
both people, requests run as the target, password/token endpoints are refused, audit rows carry both names, the
target is notified; the session ends on request and on expiry; mandatory notifications override a user's opt-out
and company defaults apply when the user has no preference.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _user(db, perms=(), superuser=False):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    pw = uuid.uuid4().hex + "Aa1!"
    u = User(username=f"syn-{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@povu-demo.test", full_name="Synthetic person",
             hashed_password=hash_password(pw), is_active=True, is_superuser=superuser)
    if perms:
        role = Role(name=f"syn-{uuid.uuid4().hex[:6]}", is_active=True)
        for code in perms:
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if p is None:
                mod, act = code.split(".", 1)
                p = Permission(code=code, name=code, module=mod, action=act, is_active=True)
                db.add(p)
            role.permissions.append(p)
        u.roles.append(role)
        db.add(role)
    db.add(u)
    await db.flush()
    return u, pw


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


@DB
@pytest.mark.asyncio
async def test_impersonation_flow():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.identity import ImpersonationSession
    from app.models.notifications import Notification
    async with AsyncSessionLocal() as db:
        support, spw = await _user(db, ("users.impersonate", "users.view"))
        plain, ppw = await _user(db, ("users.view",))
        target, _ = await _user(db, ("crm.view", "crm.create", "crm.edit"))
        boss, _ = await _user(db, superuser=True)
        await db.commit()
        ids = {k: (u.id, u.username) for k, u in (("support", support), ("plain", plain), ("target", target), ("boss", boss))}
    async with _client() as c, _client() as p:
        assert (await c.post("/api/v1/auth/login", data={"username": ids["support"][1], "password": spw})).status_code == 200
        assert (await p.post("/api/v1/auth/login", data={"username": ids["plain"][1], "password": ppw})).status_code == 200
        body = {"user_id": str(ids["target"][0]), "reason": "Ticket TKT-1: cannot see her contacts", "minutes": 15}
        assert (await p.post("/api/v1/impersonation/start", json=body)).status_code == 403          # no right
        assert (await c.post("/api/v1/impersonation/start", json={**body, "reason": "short"})).status_code == 422
        assert (await c.post("/api/v1/impersonation/start", json={**body, "user_id": str(ids["boss"][0])})).status_code == 403
        assert (await c.post("/api/v1/impersonation/start", json={**body, "user_id": str(ids["support"][0])})).status_code == 422
        r = await c.post("/api/v1/impersonation/start", json=body)
        assert r.status_code == 200
        sid = r.json()["session_id"]
        st = (await c.get("/api/v1/impersonation/status")).json()
        assert st["active"] and st["actor"] == ids["support"][1] and st["target"] == ids["target"][1]
        made = await c.post("/api/v1/crm-contacts", json={"full_name": "Created during support"})
        assert made.status_code == 201                                                              # target's CRM rights
        assert (await c.post("/api/v1/access-tokens", json={"name": "x", "scopes": ["crm.addin"]})).status_code == 403
        assert (await c.post("/api/v1/users/me/change-password", json={"current_password": "x", "new_password": "y"})).status_code == 403
        assert (await c.post("/api/v1/impersonation/start", json=body)).status_code == 403          # no nesting
        # the support person's own status is visible after ending
        assert (await c.post("/api/v1/impersonation/end")).json() == {"ended": True}
        assert (await c.get("/api/v1/impersonation/status")).json()["active"] is False
    async with AsyncSessionLocal() as db:
        s = await db.get(ImpersonationSession, uuid.UUID(sid))
        assert s.ended_reason == "ENDED"
        started = (await db.execute(select(AuditLog).where(AuditLog.event_type == "IMPERSONATION_STARTED",
                                                           AuditLog.target_id == str(ids["target"][0])))).scalars().first()
        assert started is not None and started.actor_id == ids["support"][0]
        during = (await db.execute(select(AuditLog).where(AuditLog.event_type == "IMPERSONATION_ENDED",
                                                          AuditLog.target_id == str(ids["target"][0])))).scalars().first()
        assert during.details["impersonated_by"] == ids["support"][1] and during.actor_id == ids["target"][0]
        assert (await db.execute(select(Notification).where(Notification.user_id == str(ids["target"][0]),
                                                            Notification.reference_type == "impersonation"))).scalars().first()
        # expiry: a session past its end time no longer switches identity
        s2 = ImpersonationSession(actor_id=ids["support"][0], target_id=ids["target"][0], reason="expired check here",
                                  expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        db.add(s2)
        await db.commit()
        from app.services import impersonation_service as imp
        token = imp.token_for(s2.__class__(id=s2.id, actor_id=s2.actor_id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
    async with _client() as c:
        await c.post("/api/v1/auth/login", data={"username": ids["support"][1], "password": spw})
        c.cookies.set(imp.COOKIE, token)
        assert (await c.get("/api/v1/impersonation/status")).json()["active"] is False
    async with AsyncSessionLocal() as db:
        assert (await db.get(ImpersonationSession, s2.id)).ended_reason == "EXPIRED"


@DB
@pytest.mark.asyncio
async def test_notification_defaults_and_mandatory():
    from app.db.session import AsyncSessionLocal
    from app.models.notifications import NotificationChannel, NotificationPreference, NotificationType
    from app.services import notification_policy_service as nps
    async with AsyncSessionLocal() as db:
        uid = str(uuid.uuid4())
        assert await nps.should_notify(db, uid, NotificationType.REMINDER, NotificationChannel.IN_APP)       # nothing set → on
        await nps.set_policy(db, "reminder", "in_app", False, False, "admin")
        assert not await nps.should_notify(db, uid, NotificationType.REMINDER, NotificationChannel.IN_APP)   # company default off
        db.add(NotificationPreference(user_id=uid, notification_type=NotificationType.REMINDER, channel=NotificationChannel.IN_APP, enabled_flag=True))
        await db.flush()
        assert await nps.should_notify(db, uid, NotificationType.REMINDER, NotificationChannel.IN_APP)       # user's own choice wins
        db.add(NotificationPreference(user_id=uid, notification_type=NotificationType.SYSTEM_ALERT, channel=NotificationChannel.IN_APP, enabled_flag=False))
        await db.flush()
        assert not await nps.should_notify(db, uid, NotificationType.SYSTEM_ALERT, NotificationChannel.IN_APP)
        await nps.set_policy(db, "system_alert", "in_app", True, True, "admin")
        assert await nps.should_notify(db, uid, NotificationType.SYSTEM_ALERT, NotificationChannel.IN_APP)   # mandatory overrides
        await db.rollback()
