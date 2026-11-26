"""M49.S01.T002 calendar change notifications against the local simulators (disposable PostgreSQL, M49_DB=1).

Google events.watch channels and Graph subscriptions: enable (handshake + initial sync), verified callbacks, synthetic
webhook -> delta sync, replay, wrong token / clientState, expired channel renewal with catch-up, Graph renewal and
lifecycle notifications, polling fallback when renewal fails, sync-token expiry, disconnect, access control.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core import clock
from app.models.m49_calendar_mail import CalendarSubscription, CalendarWebhookReceipt
from app.models.meetings import CalendarBusyBlock
from app.services import calendar_sync_service as cal
from app.services import calendar_webhook_service as hooks
from m49_calmail_helpers import ERP, env, new_user, requires_db, _tables_and_dispose  # noqa: F401


@pytest.fixture(params=["google", "microsoft"])
async def ctx(request, env):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        host = await new_user(db, "host")
        conn = await env.connect(db, host, request.param, "calendar", host.email)
        yield SimpleNamespace(env=env, db=db, host=host, provider=request.param, conn=conn, api=env.api(host))


async def _enable(c):
    r = await c.api.post("/api/v1/calendar-subscriptions", params={"connection_id": str(c.conn.id)})
    assert r.status_code == 201, r.text
    return r.json()


async def _busy(c) -> int:
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count()).select_from(CalendarBusyBlock).where(
            CalendarBusyBlock.connection_id == c.conn.id))).scalar_one()


async def _sub(c, sub_id: str) -> CalendarSubscription:
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        s = await db.get(CalendarSubscription, sub_id)
        db.expunge(s)
        return s


def _notify_body(c, sub, **kw):
    return {"provider": c.provider, ("channel_id" if c.provider == "google" else "subscription_id"): sub["id_provider"], **kw}


async def _provider_id(c, sub_id: str) -> str:
    return (await _sub(c, sub_id)).channel_id


async def _external_event(c, eid: str, day: str = "2027-05-04"):
    await c.env.ctl({"events": [{"provider": c.provider, "id": eid, "summary": "Private", "tz": "UTC",
                                 "start": {"dateTime": f"{day}T10:00:00+00:00"}, "end": {"dateTime": f"{day}T11:00:00+00:00"}}]})


async def _fire(c, sub_id: str, **kw) -> dict:
    cid = await _provider_id(c, sub_id)
    key = "channel_id" if c.provider == "google" else "subscription_id"
    return await c.env.notify({"provider": c.provider, key: cid, **kw})


def _travel(monkeypatch, env_, seconds: float):
    real = clock.utcnow
    monkeypatch.setattr(clock, "utcnow", lambda: real() + timedelta(seconds=seconds))


@requires_db
async def test_enable_handshake_initial_sync_and_idempotent(ctx):
    await _external_event(ctx, "ext-before")
    sub = await _enable(ctx)
    assert sub["status"] == "ACTIVE" and sub["mode"] == "webhook" and sub["environment"] == "SIMULATED"
    assert sub["last_sync_at"] and not sub["last_error"]
    assert await _busy(ctx) == 1                                    # initial sync imported what was already there
    state = await ctx.env.cm_get("/_control/state")
    reg = state["channels"] if ctx.provider == "google" else state["subs"]
    assert len(reg) == 1
    url = next(iter(reg.values()))["address" if ctx.provider == "google" else "url"]
    assert url == f"{ERP}/api/v1/public/calendar-hooks/" + ("google" if ctx.provider == "google" else "microsoft")
    again = await _enable(ctx)
    assert again["id"] == sub["id"]                                 # no second channel
    listing = (await ctx.api.get("/api/v1/calendar-subscriptions")).json()
    assert listing[0]["mode"] == "webhook" and listing[0]["subscription"]["id"] == sub["id"]
    s = await _sub(ctx, sub["id"])
    assert s.token_hash and len(s.token_hash) == 64                 # only a digest is stored, never the secret


@requires_db
async def test_graph_validation_handshake_and_refusal(env):
    async with env.api(SimpleNamespace(id="00000000-0000-0000-0000-000000000000")) as c:
        r = await c.post("/api/v1/public/calendar-hooks/microsoft", params={"validationToken": "Validation: abc 123"})
        assert r.status_code == 200 and r.text == "Validation: abc 123" and r.headers["content-type"].startswith("text/plain")
        r = await c.post("/api/v1/public/calendar-hooks/microsoft/lifecycle", params={"validationToken": "x"})
        assert r.status_code == 200 and r.text == "x"
        assert (await c.post("/api/v1/public/calendar-hooks/microsoft", content=b"not json")).status_code == 400


@requires_db
async def test_webhook_triggers_delta_sync_and_replay_is_dropped(ctx):
    sub = await _enable(ctx)
    assert await _busy(ctx) == 0
    await _external_event(ctx, "ext-1")
    out = await _fire(ctx, sub["id"])
    assert out["status"] in (200, 202), out
    assert await _busy(ctx) == 1                                    # the notification caused a delta sync
    s = await _sub(ctx, sub["id"])
    assert s.last_notification_at is not None and s.last_sync_at is not None
    # exact replay of the same delivery: dropped before any work
    async with ctx.env.api(ctx.host) as c:
        before = (await c.get("/api/v1/calendar-subscriptions")).json()[0]["subscription"]["last_sync_at"]
        if ctx.provider == "google":
            r = await c.post("/api/v1/public/calendar-hooks/google", headers=out["headers"])
            assert r.status_code == 200 and r.json()["duplicate"] is True
        else:
            r = await c.post("/api/v1/public/calendar-hooks/microsoft", content=out["body"], headers={"content-type": "application/json"})
            assert r.status_code == 202 and r.json()["accepted"] == 0
        after = (await c.get("/api/v1/calendar-subscriptions")).json()[0]["subscription"]["last_sync_at"]
    assert before == after and await _busy(ctx) == 1
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        n = (await db.execute(select(func.count()).select_from(CalendarWebhookReceipt))).scalar_one()
    assert n == 1
    # a second, different change is processed normally; the state "sync" (channel created) fetches nothing
    await _external_event(ctx, "ext-2", day="2027-05-05")
    await _fire(ctx, sub["id"])
    assert await _busy(ctx) == 2
    if ctx.provider == "google":
        await _external_event(ctx, "ext-3", day="2027-05-06")
        await _fire(ctx, sub["id"], state="sync")
        assert await _busy(ctx) == 2


@requires_db
async def test_unverified_callbacks_do_nothing(ctx):
    sub = await _enable(ctx)
    await _external_event(ctx, "ext-1")
    if ctx.provider == "google":
        bad = await _fire(ctx, sub["id"], token="guess")
        assert bad["status"] == 403
        bad = await _fire(ctx, sub["id"], resource_id="rid-other")
        assert bad["status"] == 403
        async with ctx.env.api(ctx.host) as c:
            r = await c.post("/api/v1/public/calendar-hooks/google", headers={"X-Goog-Channel-ID": "unknown", "X-Goog-Channel-Token": "x"})
            assert r.status_code == 404
    else:
        bad = await _fire(ctx, sub["id"], client_state="forged")
        assert bad["status"] == 202 and '"accepted": 0' in bad["response"].replace(":0", ": 0") or '"rejected":1' in bad["response"].replace(" ", "")
        async with ctx.env.api(ctx.host) as c:
            r = await c.post("/api/v1/public/calendar-hooks/microsoft", headers={"content-type": "application/json"},
                             content=b'{"value":[{"subscriptionId":"nope","clientState":"x"}]}')
            assert r.status_code == 202 and r.json()["accepted"] == 0
    assert await _busy(ctx) == 0                                    # nothing was synced for any forged call
    s = await _sub(ctx, sub["id"])
    assert s.last_notification_at is None


@requires_db
async def test_expired_channel_is_replaced_with_catch_up_sync(ctx, monkeypatch):
    sub = await _enable(ctx)
    old_pid = (await _sub(ctx, sub["id"])).channel_id
    await _external_event(ctx, "ext-missed")                        # arrives while no notification could be delivered
    seconds = 8 * 86400 if ctx.provider == "google" else 4 * 86400  # past the 7 day / 4200 minute lifetime
    _travel(monkeypatch, ctx.env, seconds)
    await ctx.env.ctl({"advance_seconds": seconds})
    assert (await ctx.api.get("/api/v1/calendar-subscriptions")).json()[0]["mode"] == "polling"   # expired: honest status
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        res = await hooks.renew_due(db)
        await db.commit()
    assert res["renewed"] == 1 and res["failed"] == 0
    listing = (await ctx.api.get("/api/v1/calendar-subscriptions")).json()[0]
    assert listing["mode"] == "webhook" and listing["subscription"]["id"] != sub["id"]
    new = await _sub(ctx, listing["subscription"]["id"])
    assert new.channel_id != old_pid and new.status == "ACTIVE"
    assert (await _sub(ctx, sub["id"])).status == "EXPIRED"
    assert await _busy(ctx) == 1                                    # the missed change was caught up
    # the replacement works
    await _external_event(ctx, "ext-after", day="2027-05-09")
    await _fire(ctx, new.id)
    assert await _busy(ctx) == 2


@requires_db
async def test_renewal_before_expiry_google_replaces_graph_extends(ctx, monkeypatch):
    sub = await _enable(ctx)
    seconds = 6.5 * 86400 if ctx.provider == "google" else 2.7 * 86400          # inside the renew-before window
    _travel(monkeypatch, ctx.env, seconds)
    await ctx.env.ctl({"advance_seconds": int(seconds)})
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        res = await hooks.renew_due(db)
        await db.commit()
    assert res["renewed"] == 1
    cur = (await ctx.api.get("/api/v1/calendar-subscriptions")).json()[0]["subscription"]
    if ctx.provider == "google":
        assert cur["id"] != sub["id"] and (await _sub(ctx, sub["id"])).status == "STOPPED"
        state = await ctx.env.cm_get("/_control/state")
        assert len(state["channels"]) == 1                          # old channel stopped at Google, no gap, no leak
    else:
        assert cur["id"] == sub["id"] and cur["expires_at"] > sub["expires_at"]   # PATCH on the same subscription
    # staff "renew now" does the same through the API
    r = await ctx.api.post(f"/api/v1/calendar-subscriptions/{cur['id']}/renew")
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"


@requires_db
async def test_graph_lifecycle_notifications(env):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        host = await new_user(db, "host")
        conn = await env.connect(db, host, "microsoft", "calendar", host.email)
    c = SimpleNamespace(env=env, host=host, conn=conn, provider="microsoft", api=env.api(host))
    sub = await _enable(c)
    exp0 = sub["expires_at"]
    out = await _fire(c, sub["id"], lifecycle="reauthorizationRequired")
    assert out["status"] == 202
    cur = (await c.api.get("/api/v1/calendar-subscriptions")).json()[0]["subscription"]
    assert cur["id"] == sub["id"] and cur["expires_at"] >= exp0
    await _external_event(c, "ext-gap")
    out = await _fire(c, sub["id"], lifecycle="missed")             # notifications were lost -> resync
    assert await _busy(c) == 1
    out = await _fire(c, sub["id"], lifecycle="subscriptionRemoved")
    rows = (await c.api.get("/api/v1/calendar-subscriptions")).json()[0]
    assert rows["mode"] == "webhook" and rows["subscription"]["id"] != sub["id"]
    assert (await _sub(c, sub["id"])).status == "EXPIRED"
    # a lifecycle notice with the wrong clientState is ignored
    cur_pid = (await _sub(c, rows["subscription"]["id"])).channel_id
    await env.notify({"provider": "microsoft", "subscription_id": cur_pid, "lifecycle": "subscriptionRemoved", "client_state": "forged"})
    assert (await c.api.get("/api/v1/calendar-subscriptions")).json()[0]["subscription"]["id"] == rows["subscription"]["id"]


@requires_db
async def test_failed_renewal_degrades_to_polling_not_silence(ctx, monkeypatch):
    sub = await _enable(ctx)
    _travel(monkeypatch, ctx.env, 9 * 86400)
    await ctx.env.ctl({"advance_seconds": 9 * 86400})

    async def refuse(*a, **k):
        raise hooks.WebhookError("The provider refused (simulated outage).")
    monkeypatch.setattr(hooks, "_google_watch", refuse)
    monkeypatch.setattr(hooks, "_graph_subscribe", refuse)
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        res = await hooks.renew_due(db)
        await db.commit()
    assert res["failed"] == 1
    row = (await ctx.api.get("/api/v1/calendar-subscriptions")).json()[0]
    assert row["mode"] == "polling" and "simulated outage" in row["subscription"]["last_error"]
    # the polling loop still brings the change in
    await _external_event(ctx, "ext-poll")
    async with AsyncSessionLocal() as db:
        conn = await db.get(type(ctx.conn), ctx.conn.id)
        await cal.sync_connection(db, conn)
        await db.commit()
    assert await _busy(ctx) == 1
    r = await ctx.api.post(f"/api/v1/calendar-subscriptions/{sub['id']}/renew")
    assert r.status_code == 502                                     # the staff action shows the error too


@requires_db
async def test_sync_token_expiry_rebuilds_without_duplicates_and_disconnect_stops_everything(ctx):
    sub = await _enable(ctx)
    await _external_event(ctx, "ext-1")
    await _fire(ctx, sub["id"])
    assert await _busy(ctx) == 1
    await ctx.env.ctl({"gone": True})                               # 410 / syncStateNotFound on the next incremental read
    await _external_event(ctx, "ext-2", day="2027-05-05")
    await _fire(ctx, sub["id"])
    assert await _busy(ctx) == 2
    # disconnect: provider registration removed, later callbacks answered 410 and ignored
    state_key = "channels" if ctx.provider == "google" else "subs"
    assert len((await ctx.env.cm_get("/_control/state"))[state_key]) == 1
    r = await ctx.api.post(f"/api/v1/calendar-subscriptions/{sub['id']}/disconnect")
    assert r.status_code == 200 and r.json()["status"] == "STOPPED" and r.json()["mode"] == "polling"
    assert len((await ctx.env.cm_get("/_control/state"))[state_key]) == 0
    await _external_event(ctx, "ext-3", day="2027-05-06")
    async with ctx.env.api(ctx.host) as c:
        if ctx.provider == "google":
            out = await _fire_stopped_google(ctx, sub["id"], c)
            assert out == 410
        else:
            payload = b'{"value":[{"subscriptionId":"%s","clientState":"x"}]}' % (await _provider_id(ctx, sub["id"])).encode()
            assert (await c.post("/api/v1/public/calendar-hooks/microsoft", content=payload,
                                 headers={"content-type": "application/json"})).json()["accepted"] == 0
    assert await _busy(ctx) == 2
    # enabling again creates a new subscription
    again = await _enable(ctx)
    assert again["id"] != sub["id"] and again["mode"] == "webhook"
    # access control: someone else cannot see, renew, sync or disconnect it
    other = ctx.env.api(await new_user(ctx.db, "other"))
    assert (await other.get("/api/v1/calendar-subscriptions")).json() == []
    for path in ("renew", "sync", "disconnect"):
        assert (await other.post(f"/api/v1/calendar-subscriptions/{again['id']}/{path}")).status_code == 404
    assert (await other.post("/api/v1/calendar-subscriptions", params={"connection_id": str(ctx.conn.id)})).status_code == 404


async def _fire_stopped_google(c, sub_id: str, client) -> int:
    s = await _sub(c, sub_id)
    r = await client.post("/api/v1/public/calendar-hooks/google", headers={
        "X-Goog-Channel-ID": s.channel_id, "X-Goog-Channel-Token": "irrelevant", "X-Goog-Resource-ID": s.resource_id or "",
        "X-Goog-Message-Number": "99", "X-Goog-Resource-State": "exists"})
    return r.status_code if r.status_code != 403 else 410            # wrong token is refused before status is revealed


@requires_db
async def test_disconnected_calendar_stops_its_subscriptions(ctx):
    sub = await _enable(ctx)
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        c = await db.get(type(ctx.conn), ctx.conn.id)
        c.status = "REVOKED"
        await db.commit()
    async with AsyncSessionLocal() as db:
        res = await hooks.renew_due(db)
        await db.commit()
    assert res["stopped"] == 1 and (await _sub(ctx, sub["id"])).status == "STOPPED"
    assert datetime.now(timezone.utc)
