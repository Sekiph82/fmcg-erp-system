"""M49.S01.T002 calendar change notifications (Google channels, Microsoft Graph subscriptions).

Official contracts (public documentation):
- Google Calendar API v3 push notifications (https://developers.google.com/calendar/api/guides/push):
  POST /calendars/{id}/events/watch {id, type: "web_hook", address, token, expiration(ms)} -> {id, resourceId,
  resourceUri, expiration}. Notifications are POSTs with headers X-Goog-Channel-ID, X-Goog-Channel-Token,
  X-Goog-Resource-ID, X-Goog-Resource-State (sync | exists | not_exists), X-Goog-Message-Number; the body is empty, so
  the changes are fetched with events.list + syncToken. A channel cannot be renewed: a new one is created before the
  old one expires and the old one is stopped with POST /channels/stop {id, resourceId}.
- Microsoft Graph change notifications (https://learn.microsoft.com/graph/api/subscription-post-subscriptions):
  POST /subscriptions {changeType, notificationUrl, lifecycleNotificationUrl, resource: "me/events",
  expirationDateTime, clientState}. Graph first POSTs ``notificationUrl?validationToken=...`` and expects the token
  echoed as text/plain 200 within 10 s; notifications are POSTs {value:[{subscriptionId, clientState, changeType,
  resource, ...}]} answered 202 within 3 s; lifecycle notifications (lifecycleEvent reauthorizationRequired |
  subscriptionRemoved | missed) arrive on the lifecycle URL. Renewal: PATCH /subscriptions/{id} {expirationDateTime}.
  Calendar events subscriptions live at most 4230 minutes.

The notification only says "something changed": the change is read by the existing delta sync (Google syncToken,
Graph calendarView/delta), which is idempotent, so a replayed or duplicated notification cannot corrupt anything; a
receipt table additionally drops exact replays before any work is done. The 5-minute polling loop
(calendar_sync_service.run_calendar_sync) keeps running for every connection, so a lost notification or a failed
renewal degrades to polling instead of silence.

Secrets: the channel token / clientState is random, sent to the provider once and kept only as SHA-256; incoming
values are compared in constant time.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock, provider_http
from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.m49_calendar_mail import CalendarSubscription, CalendarWebhookReceipt
from app.models.oauth_connection import OAuthConnection
from app.services import calendar_sync_service as cal
from app.services import oauth_service as oauth

log = logging.getLogger(__name__)
GOOGLE_TTL = timedelta(days=7)
GRAPH_TTL = timedelta(minutes=4200)            # Graph maximum for calendar events is 4230 minutes
RENEW_BEFORE = {"google": timedelta(hours=24), "microsoft": timedelta(hours=12)}


class WebhookError(Exception):
    pass


def _digest(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def _same(sub: CalendarSubscription, presented: Optional[str]) -> bool:
    return hmac.compare_digest(sub.token_hash, _digest(presented or ""))


def callback_urls(provider: str) -> tuple[str, Optional[str]]:
    base = (getattr(settings, "CALENDAR_WEBHOOK_BASE_URL", "") or settings.PUBLIC_API_URL).rstrip("/") + "/api/v1/public/calendar-hooks"
    if provider == "google":
        return f"{base}/google", None
    return f"{base}/microsoft", f"{base}/microsoft/lifecycle"


def _audit(db: AsyncSession, actor: Any, event: str, sub: CalendarSubscription, details: Optional[dict] = None) -> None:
    db.add(AuditLog(actor_id=getattr(actor, "id", None), actor_email=getattr(actor, "email", None), event_type=event,
                    module="integrations", target_type="calendar_subscription", target_id=str(sub.id),
                    target_name=f"{sub.provider}:{sub.channel_id}"[:200], details=details or {}))


def view(sub: CalendarSubscription) -> dict:
    now = clock.utcnow()
    live = sub.status == "ACTIVE" and sub.expires_at > now
    iso = lambda v: v.isoformat() if v else None  # noqa: E731
    return {"id": str(sub.id), "connection_id": str(sub.connection_id), "provider": sub.provider, "status": sub.status,
            "mode": "webhook" if live else "polling", "environment": sub.environment,
            "expires_at": iso(sub.expires_at), "renew_due": bool(live and sub.expires_at - now <= RENEW_BEFORE[sub.provider]),
            "last_notification_at": iso(sub.last_notification_at), "last_sync_at": iso(sub.last_sync_at),
            "last_error": sub.last_error}


def _env() -> str:
    return "SIMULATED" if provider_http.egress_mode() == "local" else "LIVE"


# ── provider calls ────────────────────────────────────────────────────────────

async def _google_watch(db, conn, address: str, token: str) -> tuple[str, str, datetime]:
    cid = str(uuid.uuid4())
    exp = clock.utcnow() + GOOGLE_TTL
    r = await cal._call(db, conn, "POST", settings.GOOGLE_CALENDAR_API_URL.rstrip("/") + "/calendars/primary/events/watch",
                        json={"id": cid, "type": "web_hook", "address": address, "token": token,
                              "expiration": int(exp.timestamp() * 1000)})
    if r.status_code != 200:
        raise WebhookError(f"Google refused the watch channel ({r.status_code}).")
    b = r.json()
    got = datetime.fromtimestamp(int(b["expiration"]) / 1000, timezone.utc) if b.get("expiration") else exp
    return b.get("id", cid), b["resourceId"], got


async def _graph_subscribe(db, conn, url: str, lifecycle: Optional[str], token: str) -> tuple[str, datetime]:
    exp = clock.utcnow() + GRAPH_TTL
    r = await cal._call(db, conn, "POST", settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + "/subscriptions",
                        json={"changeType": "created,updated,deleted", "notificationUrl": url,
                              "lifecycleNotificationUrl": lifecycle, "resource": "me/events",
                              "expirationDateTime": exp.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"), "clientState": token})
    if r.status_code not in (200, 201):
        raise WebhookError(f"Microsoft refused the subscription ({r.status_code}); it could not reach the callback URL "
                           "or the expiration was not accepted.")
    b = r.json()
    got = datetime.fromisoformat(b["expirationDateTime"].split(".")[0].rstrip("Z")).replace(tzinfo=timezone.utc)
    return b["id"], got


async def _provider_stop(db, conn, sub: CalendarSubscription) -> None:
    if conn.status != "CONNECTED":
        return
    if sub.provider == "google":
        r = await cal._call(db, conn, "POST", settings.GOOGLE_CALENDAR_API_URL.rstrip("/") + "/channels/stop",
                            json={"id": sub.channel_id, "resourceId": sub.resource_id})
    else:
        r = await cal._call(db, conn, "DELETE", settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + f"/subscriptions/{sub.channel_id}")
    if r.status_code not in (200, 204, 404):
        raise WebhookError(f"The provider did not stop the subscription ({r.status_code}).")


# ── lifecycle (staff actions) ─────────────────────────────────────────────────

async def _create(db: AsyncSession, conn: OAuthConnection, actor: Any) -> CalendarSubscription:
    url, lifecycle = callback_urls(conn.provider)
    if provider_http.egress_mode() == "live" and not url.startswith("https://"):
        raise WebhookError("NOT_CONFIGURED: change notifications need a public HTTPS callback address "
                           "(set PUBLIC_API_URL or CALENDAR_WEBHOOK_BASE_URL); polling stays active.")
    token = secrets.token_urlsafe(32)
    try:
        if conn.provider == "google":
            cid, rid, exp = await _google_watch(db, conn, url, token)
        else:
            (cid, exp), rid = await _graph_subscribe(db, conn, url, lifecycle, token), None
    except oauth.OAuthError as e:
        raise WebhookError(str(e)) from None
    except cal.CalendarApiError as e:
        raise WebhookError(str(e)) from None
    sub = CalendarSubscription(connection_id=conn.id, provider=conn.provider, channel_id=cid, resource_id=rid,
                               token_hash=_digest(token), notification_url=url, lifecycle_url=lifecycle, expires_at=exp,
                               status="ACTIVE", environment=_env(), created_by_id=conn.user_id)
    db.add(sub)
    await db.flush()
    return sub


async def _initial_sync(db: AsyncSession, conn: OAuthConnection, sub: CalendarSubscription) -> None:
    try:
        async with db.begin_nested():
            await cal.sync_connection(db, conn)
        sub.last_sync_at, sub.last_error = clock.utcnow(), None
    except (oauth.OAuthError, cal.CalendarApiError) as e:
        sub.last_error = str(e)[:500]


async def subscribe(db: AsyncSession, conn: OAuthConnection, actor: Any) -> CalendarSubscription:
    """Enable change notifications for a connected calendar, then run the initial sync (the notification only says
    that something changed; the sync cursor already holds where we are)."""
    if conn.purpose != "calendar" or conn.status != "CONNECTED":
        raise WebhookError("Connect the calendar first.")
    existing = (await db.execute(select(CalendarSubscription).where(
        CalendarSubscription.connection_id == conn.id, CalendarSubscription.status == "ACTIVE",
        CalendarSubscription.expires_at > clock.utcnow()))).scalars().first()
    if existing is not None:
        return existing
    sub = await _create(db, conn, actor)
    _audit(db, actor, "CALENDAR_SUBSCRIPTION_CREATED", sub, {"provider": sub.provider, "environment": sub.environment,
                                                              "expires_at": sub.expires_at.isoformat()})
    await _initial_sync(db, conn, sub)
    return sub


async def stop(db: AsyncSession, sub: CalendarSubscription, actor: Any, reason: str = "disconnect") -> None:
    conn = await db.get(OAuthConnection, sub.connection_id)
    if sub.status in ("ACTIVE", "FAILED", "EXPIRED") and conn is not None:
        try:
            await _provider_stop(db, conn, sub)
        except (oauth.OAuthError, cal.CalendarApiError, WebhookError) as e:
            sub.last_error = f"Stopped locally; provider stop failed: {e}"[:500]
    sub.status, sub.stopped_at = "STOPPED", clock.utcnow()
    _audit(db, actor, "CALENDAR_SUBSCRIPTION_STOPPED", sub, {"reason": reason})


async def renew(db: AsyncSession, sub: CalendarSubscription, actor: Any = None) -> CalendarSubscription:
    """Google: new channel first, then stop the old one (no gap). Graph: PATCH the expiration, or recreate when the
    provider no longer knows the subscription. An already expired one also gets a catch-up delta sync."""
    conn = await db.get(OAuthConnection, sub.connection_id)
    if conn is None or conn.status != "CONNECTED":
        sub.status, sub.stopped_at = "STOPPED", clock.utcnow()
        return sub
    was_expired = sub.expires_at <= clock.utcnow()
    try:
        if sub.provider == "microsoft" and not was_expired:
            exp = clock.utcnow() + GRAPH_TTL
            r = await cal._call(db, conn, "PATCH", settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + f"/subscriptions/{sub.channel_id}",
                                json={"expirationDateTime": exp.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")})
            if r.status_code == 200:
                sub.expires_at, sub.last_error, sub.status = exp, None, "ACTIVE"
                _audit(db, actor, "CALENDAR_SUBSCRIPTION_RENEWED", sub, {"mode": "patch"})
                return sub
            if r.status_code != 404:
                raise WebhookError(f"Microsoft did not renew the subscription ({r.status_code}).")
        new = await _create(db, conn, actor)
        old_status = sub.status
        sub.status, sub.stopped_at = "EXPIRED" if was_expired else "STOPPED", clock.utcnow()
        if not was_expired and old_status == "ACTIVE" and sub.provider == "google":
            try:
                await _provider_stop(db, conn, sub)
            except (oauth.OAuthError, cal.CalendarApiError, WebhookError) as e:
                sub.last_error = f"Replaced; old channel stop failed: {e}"[:500]
        _audit(db, actor, "CALENDAR_SUBSCRIPTION_RENEWED", new, {"mode": "recreate", "replaced": str(sub.id),
                                                                  "was_expired": was_expired})
        if was_expired:                                  # notifications were missed while it was expired
            await _initial_sync(db, conn, new)
        return new
    except (WebhookError, oauth.OAuthError, cal.CalendarApiError) as e:
        raise WebhookError(str(e)) from None            # status unchanged: the next tick retries, polling covers the gap


async def renew_due(db: AsyncSession) -> dict:
    """Background tick: renew everything expiring soon or already expired; stop those whose calendar was disconnected."""
    now = clock.utcnow()
    done = failed = stopped = 0
    subs = (await db.execute(select(CalendarSubscription).where(CalendarSubscription.status.in_(("ACTIVE", "EXPIRED"))))).scalars().all()
    for sub in subs:
        conn = await db.get(OAuthConnection, sub.connection_id)
        if conn is None or conn.status != "CONNECTED":
            sub.status, sub.stopped_at = "STOPPED", now
            stopped += 1
            continue
        if sub.status == "ACTIVE" and sub.expires_at - now > RENEW_BEFORE[sub.provider]:
            continue
        if sub.status == "EXPIRED":
            continue                                    # already replaced (or failed and surfaced); polling covers it
        try:
            async with db.begin_nested():
                await renew(db, sub, None)
            done += 1
        except WebhookError as e:
            sub.last_error = str(e)[:500]
            failed += 1
    return {"renewed": done, "failed": failed, "stopped": stopped}


# ── public webhooks ───────────────────────────────────────────────────────────

async def _fresh(db: AsyncSession, sub: CalendarSubscription, key: str) -> bool:
    r = await db.execute(pg_insert(CalendarWebhookReceipt).values(
        id=uuid.uuid4(), subscription_id=sub.id, dedupe_key=_digest(key)).on_conflict_do_nothing(
        index_elements=["subscription_id", "dedupe_key"]).returning(CalendarWebhookReceipt.id))
    return r.scalar_one_or_none() is not None


async def _by_channel(db: AsyncSession, channel_id: Optional[str], provider: str) -> Optional[CalendarSubscription]:
    if not channel_id or len(channel_id) > 256:
        return None
    sub = (await db.execute(select(CalendarSubscription).where(CalendarSubscription.channel_id == channel_id))).scalar_one_or_none()
    return sub if sub is not None and sub.provider == provider else None


async def handle_google(db: AsyncSession, headers: dict) -> tuple[int, dict, list]:
    """-> (http status, body, background actions). Verified: channel exists, token and resource id match."""
    sub = await _by_channel(db, headers.get("x-goog-channel-id"), "google")
    if sub is None:
        return 404, {"detail": "unknown channel"}, []
    if not _same(sub, headers.get("x-goog-channel-token")) or headers.get("x-goog-resource-id") != sub.resource_id:
        return 403, {"detail": "channel verification failed"}, []
    if sub.status == "STOPPED":
        return 410, {"detail": "channel stopped"}, []
    try:
        number = int(headers.get("x-goog-message-number") or 0)
    except ValueError:
        return 400, {"detail": "bad message number"}, []
    state = (headers.get("x-goog-resource-state") or "").lower()
    if not await _fresh(db, sub, f"g|{sub.channel_id}|{number}|{state}"):
        return 200, {"ok": True, "duplicate": True}, []
    sub.last_message_number = max(sub.last_message_number or 0, number)
    sub.last_notification_at = clock.utcnow()
    if state == "sync":                                  # channel created: no changes to fetch
        return 200, {"ok": True, "state": "sync"}, []
    return 200, {"ok": True, "state": state}, [("sync", sub.id)]


async def handle_graph(db: AsyncSession, payload: Any) -> tuple[int, dict, list]:
    actions, seen, rejected = [], 0, 0
    items = payload.get("value") if isinstance(payload, dict) else None
    for item in (items if isinstance(items, list) else [])[:100]:
        if not isinstance(item, dict):
            continue
        sub = await _by_channel(db, item.get("subscriptionId"), "microsoft")
        if sub is None or sub.status == "STOPPED":
            continue
        if not _same(sub, item.get("clientState")):      # not from Graph: do nothing with it
            rejected += 1
            continue
        if not await _fresh(db, sub, "m|" + json.dumps(item, sort_keys=True, default=str)):
            continue
        sub.last_notification_at = clock.utcnow()
        seen += 1
        if ("sync", sub.id) not in actions:
            actions.append(("sync", sub.id))
    return 202, {"accepted": seen, "rejected": rejected}, actions


async def handle_lifecycle(db: AsyncSession, payload: Any) -> tuple[int, dict, list]:
    actions = []
    items = payload.get("value") if isinstance(payload, dict) else None
    for item in (items if isinstance(items, list) else [])[:100]:
        if not isinstance(item, dict):
            continue
        sub = await _by_channel(db, item.get("subscriptionId"), "microsoft")
        if sub is None or sub.status == "STOPPED" or not _same(sub, item.get("clientState")):
            continue
        ev = item.get("lifecycleEvent")
        if not await _fresh(db, sub, "l|" + json.dumps(item, sort_keys=True, default=str)):
            continue
        sub.last_notification_at = clock.utcnow()
        if ev == "reauthorizationRequired":
            actions.append(("renew", sub.id))
        elif ev == "subscriptionRemoved":
            sub.status, sub.stopped_at = "EXPIRED", clock.utcnow()
            actions.append(("resubscribe", sub.id))
        elif ev == "missed":
            actions.append(("sync", sub.id))
    return 202, {"accepted": len(actions)}, actions


async def run_actions(actions: list) -> None:
    """Background work after a webhook answered: each action in its own session, one failure never blocks another."""
    from app.db.session import AsyncSessionLocal

    for kind, sub_id in actions:
        async with AsyncSessionLocal() as db:
            try:
                sub = await db.get(CalendarSubscription, sub_id)
                conn = await db.get(OAuthConnection, sub.connection_id) if sub else None
                if sub is None or conn is None or conn.status != "CONNECTED":
                    continue
                from sqlalchemy import text
                await db.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                                 {"k": int(hashlib.sha256(f"calsync:{conn.id}".encode()).hexdigest()[:15], 16)})
                if kind == "renew":
                    await renew(db, sub, None)
                elif kind == "resubscribe":
                    new = await _create(db, conn, None)
                    _audit(db, None, "CALENDAR_SUBSCRIPTION_RENEWED", new, {"mode": "resubscribe", "replaced": str(sub.id)})
                    await _initial_sync(db, conn, new)
                else:
                    await cal.sync_connection(db, conn)
                    sub.last_sync_at, sub.last_error = clock.utcnow(), None
                await db.commit()
            except Exception as e:                      # polling fallback keeps the calendar current
                await db.rollback()
                log.warning("calendar webhook action %s failed for %s", kind, sub_id, exc_info=True)
                try:
                    async with AsyncSessionLocal() as db2:
                        s2 = await db2.get(CalendarSubscription, sub_id)
                        if s2 is not None:
                            s2.last_error = (str(e) if isinstance(e, (WebhookError, oauth.OAuthError, cal.CalendarApiError))
                                             else "Sync after notification failed; polling continues.")[:500]
                            await db2.commit()
                except Exception:
                    pass
