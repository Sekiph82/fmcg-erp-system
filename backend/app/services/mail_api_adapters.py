"""Gmail API and Microsoft Graph mail adapters (M43.S01.T001 / T002).

Both fetch messages as raw RFC 822 and hand them to the existing mailbox pipeline (email_mailbox_service.parse /
store), so threading, Message-ID dedupe, customer linking, bounce and unsubscribe handling are shared with IMAP.

Gmail (public REST v1): users.getProfile → historyId; users.history.list(startHistoryId, historyTypes=messageAdded)
for increments (404 = history expired → bounded full resync); users.messages.get(format=raw); users.messages.send
({raw, threadId}).
Microsoft Graph v1.0: GET /me/mailFolders/inbox/messages/delta (+ @odata.nextLink / @odata.deltaLink; 410 or
syncStateNotFound → reset); GET /me/messages/{id}/$value (MIME); POST /me/sendMail with a base64 MIME body.

A 401 refreshes the token once; 429/5xx surface as temporary errors with Retry-After so the 5-minute loop retries.
Cursors live on oauth_connections.sync_cursor and only advance after the messages are stored.
"""
from __future__ import annotations

import base64
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.email_integration import EmailAccount, EmailProvider
from app.models.oauth_connection import OAuthConnection
from app.services import oauth_service as oauth

FULL_SYNC_LIMIT = 200
PAGE_LIMIT = 20          # pages per run; the rest follows on the next run (cursor not advanced past them)


class MailApiError(Exception):
    pass


async def _call(db: AsyncSession, conn: OAuthConnection, method: str, url: str, **kw) -> httpx.Response:
    extra = kw.pop("headers", {}) or {}
    for attempt in (1, 2):
        token = await oauth.access_token(db, conn)
        try:
            async with provider_client() as c:
                resp = await c.request(method, url, headers={"Authorization": f"Bearer {token}", **extra}, **kw)
        except EgressBlocked as e:
            raise MailApiError(str(e)) from None
        except httpx.HTTPError:
            raise oauth.OAuthTemporaryError("The mail provider could not be reached.") from None
        if resp.status_code == 401 and attempt == 1:
            conn.expires_at = clock.utcnow()      # force a refresh, then retry once
            continue
        if resp.status_code == 401:
            conn.status, conn.last_error = "ERROR", "The provider rejected the token; reconnect."
            raise oauth.OAuthReauthRequired()
        if resp.status_code == 429 or resp.status_code >= 500:
            ra = resp.headers.get("Retry-After")
            raise oauth.OAuthTemporaryError(f"Mail provider busy ({resp.status_code}).",
                                            int(ra) if ra and ra.isdigit() else None)
        return resp
    raise AssertionError("unreachable")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


# ── Gmail ─────────────────────────────────────────────────────────────────────

def _gmail(mailbox: Optional[str] = None) -> str:
    """users/me, or (M49.S01.T003, shared / delegated mailbox) users/{address}: Gmail only honours another user id
    for a service account with domain-wide delegation; the provider decides, a refusal surfaces as MailApiError."""
    return settings.GOOGLE_GMAIL_API_URL.rstrip("/") + "/users/" + (quote(mailbox, safe="@") if mailbox else "me")


async def _gmail_raw(db, conn, msg_id: str, mailbox: Optional[str] = None) -> Optional[bytes]:
    r = await _call(db, conn, "GET", f"{_gmail(mailbox)}/messages/{msg_id}", params={"format": "raw"})
    if r.status_code == 404:          # deleted between listing and fetching
        return None
    if r.status_code != 200:
        raise MailApiError(f"Gmail message fetch failed ({r.status_code}).")
    return _b64url_decode(r.json()["raw"])


async def gmail_fetch(db: AsyncSession, conn: OAuthConnection, mailbox: Optional[str] = None,
                      cursor: Optional[dict] = None) -> tuple[list[bytes], dict]:
    """mailbox / cursor: a shared mailbox is read with its own cursor, never the connection's personal one."""
    cursor = dict(conn.sync_cursor or {} if cursor is None else cursor)
    ids: list[str] = []
    if cursor.get("history_id"):
        params = {"startHistoryId": cursor["history_id"], "historyTypes": "messageAdded"}
        new_history = cursor["history_id"]
        for _ in range(PAGE_LIMIT):
            r = await _call(db, conn, "GET", f"{_gmail(mailbox)}/history", params=params)
            if r.status_code == 404:          # history too old: bounded resync, dedupe by Message-ID
                cursor = {}
                break
            if r.status_code != 200:
                raise MailApiError(f"Gmail history failed ({r.status_code}).")
            body = r.json()
            for h in body.get("history", []):
                ids += [m["message"]["id"] for m in h.get("messagesAdded", []) if "message" in m]
            new_history = body.get("historyId", new_history)
            if not body.get("nextPageToken"):
                cursor["history_id"] = new_history
                break
            params["pageToken"] = body["nextPageToken"]
    if not cursor.get("history_id"):
        prof = await _call(db, conn, "GET", f"{_gmail(mailbox)}/profile")
        if prof.status_code != 200:
            raise MailApiError(f"Gmail profile failed ({prof.status_code}).")
        r = await _call(db, conn, "GET", f"{_gmail(mailbox)}/messages", params={"maxResults": FULL_SYNC_LIMIT,
                                                                         "labelIds": "INBOX"})
        if r.status_code != 200:
            raise MailApiError(f"Gmail list failed ({r.status_code}).")
        ids = [m["id"] for m in r.json().get("messages", [])]
        cursor = {"history_id": prof.json()["historyId"]}
    raws = []
    for mid in dict.fromkeys(ids):                 # keep order, drop repeats
        raw = await _gmail_raw(db, conn, mid, mailbox)
        if raw:
            raws.append(raw)
    return raws, cursor


async def gmail_send(db: AsyncSession, conn: OAuthConnection, mime_bytes: bytes) -> None:
    raw = base64.urlsafe_b64encode(mime_bytes).decode().rstrip("=")
    r = await _call(db, conn, "POST", f"{_gmail()}/messages/send", json={"raw": raw})
    if r.status_code not in (200, 202):
        raise MailApiError(f"Gmail refused the message ({r.status_code}); nothing was sent.")


# ── Microsoft Graph ───────────────────────────────────────────────────────────

def _graph(mailbox: Optional[str] = None) -> str:
    """/me, or (M49.S01.T003) /users/{address} for a shared mailbox (Mail.Read.Shared + Exchange permission)."""
    return settings.MICROSOFT_GRAPH_BASE_URL.rstrip("/") + ("/users/" + quote(mailbox, safe="@") if mailbox else "/me")


async def graph_fetch(db: AsyncSession, conn: OAuthConnection, mailbox: Optional[str] = None,
                      cursor: Optional[dict] = None) -> tuple[list[bytes], dict]:
    cursor = dict(conn.sync_cursor or {} if cursor is None else cursor)
    base_cursor = dict(cursor)
    url = cursor.get("delta_link") or f"{_graph(mailbox)}/mailFolders/inbox/messages/delta?$select=id"
    ids: list[str] = []
    for _ in range(PAGE_LIMIT):
        r = await _call(db, conn, "GET", url, headers={"Prefer": "odata.maxpagesize=50"})
        if r.status_code == 410 or (r.status_code == 400 and "syncStateNotFound" in r.text):
            cursor, url, ids = {}, f"{_graph(mailbox)}/mailFolders/inbox/messages/delta?$select=id", []
            continue
        if r.status_code != 200:
            raise MailApiError(f"Graph delta failed ({r.status_code}).")
        body = r.json()
        ids += [m["id"] for m in body.get("value", []) if "@removed" not in m]
        if body.get("@odata.deltaLink"):
            cursor = {"delta_link": body["@odata.deltaLink"]}
            break
        url = body.get("@odata.nextLink")
        if not url:
            break
    else:
        cursor = base_cursor                        # page limit hit: keep old cursor, next run continues
    raws = []
    for mid in dict.fromkeys(ids[-FULL_SYNC_LIMIT:]):
        r = await _call(db, conn, "GET", f"{_graph(mailbox)}/messages/{mid}/$value")
        if r.status_code == 404:
            continue
        if r.status_code != 200:
            raise MailApiError(f"Graph message fetch failed ({r.status_code}).")
        raws.append(r.content)
    return raws, cursor


async def graph_send(db: AsyncSession, conn: OAuthConnection, mime_bytes: bytes) -> None:
    r = await _call(db, conn, "POST", f"{_graph()}/sendMail", content=base64.b64encode(mime_bytes),
                    headers={"Content-Type": "text/plain"})
    if r.status_code not in (200, 202):
        raise MailApiError(f"Microsoft refused the message ({r.status_code}); nothing was sent.")


# ── glue ──────────────────────────────────────────────────────────────────────

async def ensure_mail_account(db: AsyncSession, conn: OAuthConnection) -> EmailAccount:
    """After a mail OAuth connect: the user's mailbox row (created once, re-linked on reconnect)."""
    provider = EmailProvider.GMAIL if conn.provider == "google" else EmailProvider.OUTLOOK
    acc = (await db.execute(select(EmailAccount).where(EmailAccount.oauth_connection_id == conn.id))).scalar_one_or_none()
    if acc is None and conn.account_email:
        acc = (await db.execute(select(EmailAccount).where(
            EmailAccount.created_by_id == conn.user_id, EmailAccount.provider == provider,
            EmailAccount.email_address == conn.account_email))).scalars().first()
    if acc is None:
        acc = EmailAccount(provider=provider, email_address=conn.account_email or f"{conn.provider}-mailbox",
                           created_by_id=conn.user_id, is_active=True, sync_enabled=True)
        db.add(acc)
    acc.oauth_connection_id, acc.sync_error = conn.id, None
    await db.flush()
    return acc


async def fetch(db: AsyncSession, conn: OAuthConnection) -> tuple[list[bytes], dict]:
    return await (gmail_fetch if conn.provider == "google" else graph_fetch)(db, conn)


async def send_raw(db: AsyncSession, conn: OAuthConnection, mime_bytes: bytes) -> None:
    await (gmail_send if conn.provider == "google" else graph_send)(db, conn, mime_bytes)
