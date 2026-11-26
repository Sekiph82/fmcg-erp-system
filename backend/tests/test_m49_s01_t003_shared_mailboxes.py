"""M49.S01.T003 shared / delegated mailboxes against the local simulators (disposable PostgreSQL, M49_DB=1).

Microsoft: /users/{shared} read, Send As (/users/{shared}/sendMail), Send on Behalf (/me/sendMail from + sender).
Google: sendAs alias (verified only), DWD-only read. Covers authorised registration, membership permissions,
unauthorised access denied, per-mailbox thread scope separate from personal mail, reply threading, attachment metadata,
bounded incremental sync without duplicates, provider access loss, member / mailbox revocation and the audit trail.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.email_integration import EmailAccount, EmailMessage, EmailThread
from app.models.m49_calendar_mail import SharedMailbox
from m49_calmail_helpers import env, mime, new_user, requires_db, _tables_and_dispose  # noqa: F401

SHARED = "povu-sales@example.com"


async def _world(env, provider: str):
    from app.db.session import AsyncSessionLocal
    db = AsyncSessionLocal()
    admin = await new_user(db, "admin", superuser=True)
    a, b, c = await new_user(db, "agent-a"), await new_user(db, "agent-b"), await new_user(db, "outsider")
    for u in (admin, a, b, c):
        await env.connect(db, u, provider, "mail", u.email)
    return SimpleNamespace(env=env, db=db, provider=provider, admin=admin, a=a, b=b, c=c, api=env.api(admin),
                           apis={k: env.api(v) for k, v in dict(a=a, b=b, c=c).items()})


async def _acl(w, **rules):
    await w.env.ctl({"acl": {SHARED: rules}})


async def _register(w, expect=201, **over):
    r = await w.api.post("/api/v1/shared-mailboxes", json={"provider": w.provider, "address": SHARED,
                                                           "display_name": "POVU Sales (shared)", **over})
    assert r.status_code == expect, r.text
    return r.json()


async def _grant(w, mid, user, **kw):
    r = await w.api.put(f"/api/v1/shared-mailboxes/{mid}/members", json={"user_id": str(user.id), **kw})
    assert r.status_code == 200, r.text
    return r.json()


async def _deliver(w, *msgs):
    await w.env.ctl({"deliver": [{"mailbox": SHARED, "raw_b64": m} for m in msgs]})


async def _count(model, *where) -> int:
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def _sent(w):
    return await w.env.cm_get("/_control/sent")


async def _audit(*events):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return set((await db.execute(select(AuditLog.event_type).where(AuditLog.event_type.in_(events)))).scalars())


@requires_db
async def test_microsoft_shared_mailbox_members_send_as_on_behalf_and_threads(env):
    w = await _world(env, "microsoft")
    await _acl(w, read=[w.admin.email, w.a.email, w.b.email], send_as=[w.a.email], on_behalf=[w.b.email])
    mb = await _register(w)
    mid = mb["id"]
    assert mb["status"] == "ACTIVE" and mb["send_modes"] == ["send_as", "on_behalf"]
    await _grant(w, mid, w.a, can_send=True, send_mode="send_as")
    await _grant(w, mid, w.b, can_send=True, send_mode="on_behalf")
    # inbound mail with an attachment arrives; any member's sync imports it into the mailbox's own account
    await _deliver(w, mime("buyer@example.com", SHARED, "Order query POVU AllClean 1 L", "<q1@example.com>", attach=True))
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")
    assert r.status_code == 200 and r.json()["imported"] == 1, r.text
    threads = (await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).json()
    assert len(threads) == 1 and threads[0]["subject"].startswith("Order query")
    detail = (await w.apis["b"].get(f"/api/v1/shared-mailboxes/{mid}/threads/{threads[0]['id']}")).json()
    msg = detail["messages"][0]
    assert msg["has_attachments"] and msg["attachments"][0]["name"] == "prices.pdf" and msg["is_inbound"]
    # personal separation: the shared mail is under its own account, not in anyone's personal accounts
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        shared_acc = await db.get(EmailAccount, (await db.get(SharedMailbox, mid)).account_id)
        assert shared_acc.created_by_id is None and shared_acc.sync_enabled is False and shared_acc.oauth_connection_id is None
        personal = (await db.execute(select(EmailAccount.id).where(EmailAccount.created_by_id.in_([w.a.id, w.b.id, w.admin.id])))).scalars().all()
        assert len(personal) == 3 and shared_acc.id not in personal
        assert (await db.execute(select(func.count()).select_from(EmailThread).where(EmailThread.account_id.in_(personal)))).scalar_one() == 0
    # send as the shared mailbox (member A: Send As)
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={
        "to_emails": ["buyer@example.com"], "subject": "Re: Order query POVU AllClean 1 L", "body_text": "Quote attached.",
        "reply_to_thread_id": threads[0]["id"]})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["id"] == threads[0]["id"] and out["message_count"] == 2           # reply joined the thread
    assert out["messages"][-1]["from_email"] == SHARED
    assert (await _count(EmailMessage, EmailMessage.thread_id == threads[0]["id"], EmailMessage.in_reply_to == "<q1@example.com>")) == 1
    sent = await _sent(w)
    assert sent[-1]["path"] == f"graph:users/{SHARED}/sendMail" and sent[-1]["caller"] == w.a.email and sent[-1]["from"] == SHARED
    # send on behalf (member B): JSON message with from = shared mailbox and sender = B
    r = await w.apis["b"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={
        "to_emails": ["buyer@example.com"], "subject": "Delivery note", "body_text": "On the way."})
    assert r.status_code == 201, r.text
    sent = await _sent(w)
    assert sent[-1]["path"] == "graph:me/sendMail" and sent[-1]["from"] == SHARED and sent[-1]["sender"] == w.b.email
    # unauthorised: the outsider and the administrator (not a member) get nothing; read-only member cannot send
    for who in (w.apis["c"], w.api):
        assert (await who.get(f"/api/v1/shared-mailboxes/{mid}/threads")).status_code == 404
        assert (await who.get(f"/api/v1/shared-mailboxes/{mid}/threads/{threads[0]['id']}")).status_code == 404
        assert (await who.post(f"/api/v1/shared-mailboxes/{mid}/sync")).status_code == 404
        assert (await who.post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["x@example.com"], "subject": "s", "body_text": "b"})).status_code == 404
    assert (await w.apis["c"].get("/api/v1/shared-mailboxes")).json() == []
    assert (await w.apis["a"].post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": "x@example.com"})).status_code == 403
    assert (await w.apis["a"].put(f"/api/v1/shared-mailboxes/{mid}/members", json={"user_id": str(w.c.id)})).status_code == 403
    await _grant(w, mid, w.c, can_send=False)
    r = await w.apis["c"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["x@example.com"], "subject": "s", "body_text": "b"})
    assert r.status_code == 403
    assert (await w.apis["c"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).status_code == 200
    # the provider enforces Send As too: a member without it is refused and nothing is stored
    await _grant(w, mid, w.c, can_send=True, send_mode="send_as")
    before = await _count(EmailMessage)
    r = await w.apis["c"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["x@example.com"], "subject": "s", "body_text": "b"})
    assert r.status_code == 403 and "Send As" in r.json()["detail"] and await _count(EmailMessage) == before
    assert len(await _sent(w)) == 2
    # revocation is immediate
    assert (await w.api.delete(f"/api/v1/shared-mailboxes/{mid}/members/{w.a.id}")).status_code == 204
    assert (await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).status_code == 404
    assert (await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["x@example.com"], "subject": "s", "body_text": "b"})).status_code == 404
    assert (await w.api.delete(f"/api/v1/shared-mailboxes/{mid}/members/{w.a.id}")).status_code == 404
    members = {m["email"]: m for m in (await w.api.get(f"/api/v1/shared-mailboxes/{mid}/members")).json()}
    assert members[w.a.email]["active"] is False and members[w.b.email]["send_mode"] == "on_behalf"
    assert {"SHARED_MAILBOX_REGISTERED", "SHARED_MAILBOX_MEMBER_GRANTED", "SHARED_MAILBOX_MEMBER_REVOKED", "SHARED_MAILBOX_SENT",
            "SHARED_MAILBOX_SYNCED"} <= await _audit("SHARED_MAILBOX_REGISTERED", "SHARED_MAILBOX_MEMBER_GRANTED",
                                                    "SHARED_MAILBOX_MEMBER_REVOKED", "SHARED_MAILBOX_SENT", "SHARED_MAILBOX_SYNCED")
    await w.db.close()


@requires_db
async def test_google_send_as_requires_verified_alias_and_dwd_for_reading(env):
    w = await _world(env, "google")
    mb = await _register(w, expect=403)                               # a delegate's own token cannot open another Gmail user
    await _acl(w, gmail_dwd=[w.admin.email], gmail_send_as=[{"user": w.a.email, "status": "accepted"}, {"user": w.b.email, "status": "pending"}])
    mb = await _register(w)
    mid = mb["id"]
    assert mb["send_modes"] == ["send_as"]
    r = await w.api.put(f"/api/v1/shared-mailboxes/{mid}/members", json={"user_id": str(w.a.id), "can_send": True, "send_mode": "on_behalf"})
    assert r.status_code == 422 and "does not offer" in r.json()["detail"]                       # Gmail has no send-on-behalf API
    await _grant(w, mid, w.a, can_send=True)
    await _grant(w, mid, w.b, can_send=True)
    await _deliver(w, mime("buyer@example.com", SHARED, "Delivery question", "<g1@example.com>"))
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")
    assert r.status_code == 200 and r.json()["imported"] == 1, r.text
    tid = (await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).json()[0]["id"]
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["buyer@example.com"], "subject": "Re: Delivery question",
                                                                              "body_text": "Tomorrow.", "reply_to_thread_id": tid})
    assert r.status_code == 201, r.text
    sent = await _sent(w)
    assert sent[-1]["path"] == "gmail:me/messages/send" and sent[-1]["from"] == SHARED and sent[-1]["caller"] == w.a.email
    n_sent = len(sent)
    r = await w.apis["b"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["buyer@example.com"], "subject": "x", "body_text": "y"})
    assert r.status_code == 403 and "verified send-as" in r.json()["detail"] and len(await _sent(w)) == n_sent   # pending alias: refused
    assert (await w.apis["c"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).status_code == 404
    await w.db.close()


@requires_db
async def test_registration_is_authorised_by_the_provider_and_the_permission(env):
    w = await _world(env, "microsoft")
    assert (await w.apis["a"].post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": SHARED})).status_code == 403
    assert (await w.api.post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": SHARED})).status_code == 403   # Exchange refuses
    assert await _count(SharedMailbox) == 0
    await _acl(w, read=[w.admin.email])
    assert (await w.api.post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": w.admin.email})).status_code == 422
    assert (await w.api.post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": "not an address"})).status_code == 422
    await _register(w)
    await _register(w, expect=409)                                       # already registered
    nobody = await new_user(w.db, "no-connection", superuser=True)
    r = await env.api(nobody).post("/api/v1/shared-mailboxes", json={"provider": "microsoft", "address": "other@example.com"})
    assert r.status_code == 409 and "Connect your own" in r.json()["detail"]
    await w.db.close()


@requires_db
async def test_incremental_sync_is_bounded_deduplicated_and_notices_lost_access(env):
    w = await _world(env, "microsoft")
    await _acl(w, read=[w.admin.email, w.a.email])
    mid = (await _register(w))["id"]
    await _grant(w, mid, w.a, can_send=False)
    await env.ctl({"page_size": 2})
    msgs = [mime("buyer@example.com", SHARED, f"Enquiry {i}", f"<e{i}@example.com>") for i in range(5)]
    await _deliver(w, *msgs)
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")
    assert r.json() == {"imported": 5, "skipped": 0, "failed": 0}
    again = (await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")).json()
    assert again["imported"] == 0                                         # the cursor moved: nothing is fetched twice
    await _deliver(w, msgs[2], mime("buyer@example.com", SHARED, "Enquiry 5", "<e5@example.com>"))     # a re-delivered old one + a new one
    r = (await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")).json()
    assert r["imported"] == 1 and r["skipped"] == 1                      # Message-ID dedupe: no duplicate thread
    threads = (await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads", params={"q": "Enquiry"})).json()
    assert len(threads) == 6
    assert len((await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads", params={"q": "nothing-matches"})).json()) == 0
    # the mailbox owner withdraws the sign-in's access at the provider: the next sync says so and stops
    await _acl(w, read=[w.a.email])
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")
    assert r.status_code == 502
    listing = (await w.api.get("/api/v1/shared-mailboxes")).json()
    assert listing[0]["status"] == "ACCESS_LOST" and listing[0]["last_error"]
    assert (await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")).status_code == 409
    await w.db.close()


@requires_db
async def test_revoking_the_mailbox_closes_it_keeps_history_and_can_be_registered_again(env):
    w = await _world(env, "microsoft")
    await _acl(w, read=[w.admin.email], send_as=[w.a.email])
    mid = (await _register(w))["id"]
    await _grant(w, mid, w.a, can_send=True)
    await _deliver(w, mime("buyer@example.com", SHARED, "History stays", "<h1@example.com>"))
    assert (await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync")).status_code == 200
    r = await w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/revoke")
    assert r.status_code == 403                                           # members cannot close it
    r = await w.api.post(f"/api/v1/shared-mailboxes/{mid}/revoke")
    assert r.status_code == 200 and r.json()["status"] == "REVOKED"
    for call in (w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads"),
                 w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/sync"),
                 w.apis["a"].post(f"/api/v1/shared-mailboxes/{mid}/send", json={"to_emails": ["x@example.com"], "subject": "s", "body_text": "b"})):
        assert (await call).status_code == 404
    assert (await w.apis["a"].get("/api/v1/shared-mailboxes")).json() == []
    assert await _count(EmailThread) >= 1                                  # stored history is kept for the record
    assert "SHARED_MAILBOX_REVOKED" in await _audit("SHARED_MAILBOX_REVOKED")
    again = await _register(w)                                             # re-registered: fresh membership and cursor
    assert again["id"] == mid and again["status"] == "ACTIVE"
    assert (await w.apis["a"].get(f"/api/v1/shared-mailboxes/{mid}/threads")).status_code == 404
    await w.db.close()
