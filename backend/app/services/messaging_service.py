"""M44.S01.T013 messaging channels into the unified CRM inbox.

Messenger and Instagram DMs arrive on the signed Meta webhook (same app secret as social listening) for channels
registered under Social → Channels; replies go out through the Graph Send API with the page token, only inside
Meta's 24-hour standard messaging window. Custom channels post messages with their own token and fetch our replies
from an outbox. Slack gets deal-won, new-ticket and approval notices through an incoming webhook.
Nothing is sent without configuration: no token / webhook URL → NOT_CONFIGURED.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import provider_client
from app.models.crm import CRMChannelMessage, CustomChannel, SlackDelivery, SocialChannel

logger = logging.getLogger(__name__)
CHANNELS = ("MESSENGER", "INSTAGRAM", "CUSTOM")
WINDOW = timedelta(hours=24)          # Meta standard messaging window after the customer's last message
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")


class MessagingError(Exception):
    def __init__(self, msg: str, status: int = 409):
        super().__init__(msg)
        self.status = status


def _ts(ms: Any) -> Optional[datetime]:
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc) if str(ms or "").isdigit() else None


async def _add(db: AsyncSession, **row) -> bool:
    """Insert once per (channel, external_id); returns whether a new message was stored."""
    res = await db.execute(insert(CRMChannelMessage).values(**row).on_conflict_do_nothing(constraint="uq_crm_channel_message_ext"))
    return bool(res.rowcount)


async def ingest_meta(db: AsyncSession, payload: dict) -> dict:
    """entry[].messaging[] of a Page (Messenger) or Instagram webhook. Only registered channels; echoes of our own
    sends are deduped by message id."""
    channel = {"page": "MESSENGER", "instagram": "INSTAGRAM"}.get(payload.get("object"))
    network = {"MESSENGER": "facebook", "INSTAGRAM": "instagram"}.get(channel or "")
    stored = ignored = 0
    for entry in payload.get("entry", []) if channel else []:
        events = entry.get("messaging") or []
        if not events:
            continue
        acct = str(entry.get("id"))
        known = (await db.execute(select(SocialChannel.id).where(SocialChannel.network == network,
                                                                 SocialChannel.external_id == acct))).first()
        for ev in events:
            msg = ev.get("message") or {}
            if known is None or not msg.get("mid") or msg.get("is_deleted"):
                ignored += 1
                continue
            echo = bool(msg.get("is_echo"))
            peer = (ev.get("recipient") if echo else ev.get("sender")) or {}
            text = msg.get("text") or ("[attachment]" if msg.get("attachments") else "")
            stored += await _add(db, channel=channel, account_id=acct, thread_id=str(peer.get("id"))[:120],
                                 external_id=str(msg["mid"])[:120], direction="OUT" if echo else "IN",
                                 sender=None if echo else f"{channel.title()} user {str(peer.get('id'))[-4:]}",
                                 body=text, status="SENT" if echo else "RECEIVED",
                                 created_at=_ts(ev.get("timestamp")) or datetime.now(timezone.utc))
    return {"stored": stored, "ignored": ignored}


async def thread(db: AsyncSession, channel: str, source_ref: str) -> list[CRMChannelMessage]:
    acct, _, tid = source_ref.partition(":")
    return list((await db.execute(select(CRMChannelMessage).where(
        CRMChannelMessage.channel == channel, CRMChannelMessage.account_id == acct, CRMChannelMessage.thread_id == tid)
        .order_by(CRMChannelMessage.created_at, CRMChannelMessage.id))).scalars())


async def reply(db: AsyncSession, channel: str, source_ref: str, body: str, agent_id) -> CRMChannelMessage:
    acct, _, tid = source_ref.partition(":")
    now = datetime.now(timezone.utc)
    if channel == "CUSTOM":
        ch = (await db.execute(select(CustomChannel).where(CustomChannel.key == acct))).scalar_one_or_none()
        if ch is None or not ch.active:
            raise MessagingError("This custom channel is disabled.")
        msg = CRMChannelMessage(channel=channel, account_id=acct, thread_id=tid, external_id=f"out-{secrets.token_hex(8)}",
                             direction="OUT", body=body, status="QUEUED", agent_id=agent_id, created_at=now)
        db.add(msg)
        return msg
    if not settings.META_PAGE_ACCESS_TOKEN:
        raise MessagingError("NOT_CONFIGURED: Meta page token is not set (activation step in M47).", 503)
    last_in = (await db.execute(select(func.max(CRMChannelMessage.created_at)).where(
        CRMChannelMessage.channel == channel, CRMChannelMessage.account_id == acct, CRMChannelMessage.thread_id == tid,
        CRMChannelMessage.direction == "IN"))).scalar()
    if last_in is None or now - last_in > WINDOW:
        raise MessagingError("Outside Meta's 24-hour window: the customer has to write first.")
    async with provider_client() as c:
        r = await c.post(f"{settings.META_ADS_API_URL.rstrip('/')}/{settings.META_ADS_API_VERSION}/{acct}/messages",
                         json={"recipient": {"id": tid}, "messaging_type": "RESPONSE", "message": {"text": body}},
                         headers={"Authorization": f"Bearer {settings.META_PAGE_ACCESS_TOKEN}"})
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or not data.get("message_id"):
        err = (data.get("error") or {}).get("message") if isinstance(data.get("error"), dict) else None
        raise MessagingError(f"Meta refused the message: {err or f'HTTP {r.status_code}'}", 502)
    msg = CRMChannelMessage(channel=channel, account_id=acct, thread_id=tid, external_id=str(data["message_id"])[:120],
                         direction="OUT", body=body, status="SENT", agent_id=agent_id, created_at=now)
    db.add(msg)
    return msg


# ── custom channels API ─────────────────────────────────────────────────────

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    t = "pcc_" + secrets.token_urlsafe(32)
    return t, token_hash(t)


async def channel_for_token(db: AsyncSession, key: str, token: str) -> Optional[CustomChannel]:
    ch = (await db.execute(select(CustomChannel).where(CustomChannel.key == key))).scalar_one_or_none()
    if ch is None or not ch.active or not secrets.compare_digest(ch.token_hash, token_hash(token or "")):
        return None
    return ch


async def outbox(db: AsyncSession, ch: CustomChannel, limit: int = 100) -> list[dict]:
    """Our queued replies for this channel; handed over once (marked DELIVERED)."""
    rows = list((await db.execute(select(CRMChannelMessage).where(
        CRMChannelMessage.channel == "CUSTOM", CRMChannelMessage.account_id == ch.key, CRMChannelMessage.status == "QUEUED")
        .order_by(CRMChannelMessage.created_at).limit(limit).with_for_update(skip_locked=True))).scalars())
    for m in rows:
        m.status = "DELIVERED"
    return [{"id": m.external_id, "thread_id": m.thread_id, "text": m.body, "created_at": m.created_at.isoformat()} for m in rows]


# ── Slack notices ─────────────────────────────────────────────────────────

async def _collect(db: AsyncSession, since: datetime) -> list[tuple[str, str, str]]:
    from app.models.crm import CRMRecord, CRMStatus
    from app.models.helpdesk import HelpdeskTicket
    from app.models.notifications import Notification
    out = []
    for r in (await db.execute(select(CRMRecord.id, CRMRecord.company_name, CRMRecord.opportunity_code).where(
            CRMRecord.status == CRMStatus.WON, CRMRecord.updated_at >= since).limit(100))).all():
        out.append(("DEAL", str(r.id), f":trophy: Deal won: {r.company_name}" + (f" ({r.opportunity_code})" if r.opportunity_code else "")))
    for t in (await db.execute(select(HelpdeskTicket.id, HelpdeskTicket.ticket_no, HelpdeskTicket.priority).where(
            HelpdeskTicket.created_at >= since).limit(100))).all():
        # subject left out: it may carry customer details; the ticket number is enough to open it
        out.append(("TICKET", str(t.id), f":ticket: New ticket {t.ticket_no} (priority {getattr(t.priority, 'value', t.priority)})"))
    naive = since.replace(tzinfo=None)   # notifications store naive UTC
    for ref, title in (await db.execute(select(Notification.reference_id, func.min(Notification.title)).where(
            Notification.reference_type.like("approval:%"), Notification.created_at >= naive)
            .group_by(Notification.reference_id).limit(100))).all():
        out.append(("APPROVAL", str(ref)[:200], ":hourglass: " + title.replace("Waiting for your approval", "Waiting for approval")))
    return out


async def slack_tick(db: AsyncSession, now: Optional[datetime] = None) -> dict:
    """Queue new notices (last 24 h) and post queued / failed ones (≤5 attempts). Without SLACK_WEBHOOK_URL nothing
    is queued or sent."""
    if not settings.SLACK_WEBHOOK_URL:
        return {"status": "NOT_CONFIGURED", "sent": 0}
    now = now or datetime.now(timezone.utc)
    for kind, ref, text in await _collect(db, now - timedelta(hours=24)):
        await db.execute(insert(SlackDelivery).values(kind=kind, ref=ref, text=text[:1000])
                         .on_conflict_do_nothing(constraint="uq_crm_slack_delivery"))
    due = list((await db.execute(select(SlackDelivery).where(SlackDelivery.status != "SENT", SlackDelivery.attempts < 5)
                                 .order_by(SlackDelivery.created_at).limit(50).with_for_update(skip_locked=True))).scalars())
    sent = 0
    async with provider_client(timeout=10.0) as c:
        for d in due:
            d.attempts += 1
            try:
                r = await c.post(settings.SLACK_WEBHOOK_URL, json={"text": d.text})
                ok = r.status_code == 200
                d.error = None if ok else f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as e:   # network / egress refusal: keep for retry
                ok, d.error = False, str(e)[:300]
            d.status = "SENT" if ok else "FAILED"
            sent += ok
    await db.commit()
    return {"status": "OK", "sent": sent, "pending": len(due) - sent}
