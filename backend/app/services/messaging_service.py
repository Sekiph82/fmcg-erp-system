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
    """Our queued replies for this channel. Redelivered on every poll until the client acks them (M45.S01.T024)."""
    rows = list((await db.execute(select(CRMChannelMessage).where(
        CRMChannelMessage.channel == "CUSTOM", CRMChannelMessage.account_id == ch.key, CRMChannelMessage.status == "QUEUED")
        .order_by(CRMChannelMessage.created_at).limit(limit))).scalars())
    return [{"id": m.external_id, "thread_id": m.thread_id, "text": m.body, "created_at": m.created_at.isoformat()} for m in rows]


async def outbox_ack(db: AsyncSession, ch: CustomChannel, ids: list[str]) -> int:
    """Mark the acked replies DELIVERED; unknown ids or other channels' ids are ignored."""
    rows = list((await db.execute(select(CRMChannelMessage).where(
        CRMChannelMessage.channel == "CUSTOM", CRMChannelMessage.account_id == ch.key,
        CRMChannelMessage.status == "QUEUED", CRMChannelMessage.external_id.in_(ids)))).scalars())
    for m in rows:
        m.status = "DELIVERED"
    return len(rows)


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
    for rtype, ref in (await db.execute(select(Notification.reference_type, Notification.reference_id).where(
            Notification.reference_type.like("approval:%"), Notification.created_at >= naive)
            .distinct().limit(100))).all():
        # titles can carry customer or amount text: only the kind of item goes to Slack (M44 review)
        kind = rtype.split(":", 1)[1].replace("_", " ")
        out.append(("APPROVAL", str(ref)[:200], f":hourglass: A {kind} is waiting for approval. Open My Approvals in the ERP."))
    if slack_signing_secret():   # M47.S01.T010 interactive notices for the generic approval engine
        from app.models.workflow import ApprovalRequest, ApprovalStatus
        for rid, module, level in (await db.execute(select(ApprovalRequest.id, ApprovalRequest.module, ApprovalRequest.current_level)
                                                    .where(ApprovalRequest.status == ApprovalStatus.PENDING,
                                                           ApprovalRequest.updated_at >= since).limit(100))).all():
            kind = getattr(module, "value", module).replace("_", " ").lower()
            out.append(("APPROVE", f"{rid}:{level}", f":hourglass: A {kind} approval (level {level}) is waiting. Ref {str(rid)[:8]}."))
    return out


# ── M47.S01.T010 Slack app: routing rules and interactive approvals ─────────
SLACK_EVENTS = ("DEAL", "TICKET", "APPROVAL", "APPROVE")
SLACK_WINDOW = 300   # seconds: Slack's replay window for signed requests


def slack_signing_secret() -> str:
    import os
    return getattr(settings, "SLACK_SIGNING_SECRET", "") or os.environ.get("SLACK_SIGNING_SECRET", "")


def valid_webhook(url: str) -> bool:
    """Slack incoming webhooks only (https://hooks.slack.com/services/...); a local simulator host only while egress
    is not live."""
    from urllib.parse import urlsplit
    from app.core import provider_http
    u = urlsplit(url or "")
    if u.scheme == "https" and u.hostname == "hooks.slack.com" and u.path.startswith("/services/"):
        return True
    return provider_http.egress_mode() != "live" and provider_http._is_local_host(u.hostname or "")


def _blocks(d) -> Optional[list]:
    if d.kind != "APPROVE":
        return None
    rid = d.ref.split(":", 1)[0]
    return [{"type": "section", "text": {"type": "mrkdwn", "text": d.text}},
            {"type": "actions", "block_id": "erp_approval", "elements": [
                {"type": "button", "action_id": "approve", "style": "primary", "text": {"type": "plain_text", "text": "Approve"},
                 "value": f"approve:{rid}"},
                {"type": "button", "action_id": "reject", "style": "danger", "text": {"type": "plain_text", "text": "Reject"},
                 "value": f"reject:{rid}"}]}]


def verify_slack(raw: bytes, timestamp: str, signature: str, now: Optional[float] = None) -> bool:
    """Slack v0 signature: HMAC-SHA256(signing secret, "v0:{timestamp}:{body}"), within 5 minutes."""
    import hmac
    import time
    secret = slack_signing_secret()
    if not secret:
        raise MessagingError("NOT_CONFIGURED: SLACK_SIGNING_SECRET is not set.", 503)
    if not str(timestamp or "").isdigit() or abs((now or time.time()) - int(timestamp)) > SLACK_WINDOW:
        return False
    mac = hmac.new(secret.encode(), b"v0:" + timestamp.encode() + b":" + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v0={mac}", signature or "")


async def slack_interaction(db: AsyncSession, payload: dict) -> str:
    """An Approve / Reject click. The Slack user must be linked to an active ERP user (same e-mail as when linked), who
    must hold the step's role and must not be the requester (second person). Returns the text for Slack. No commit."""
    import uuid as _uuid
    from fastapi import HTTPException
    from sqlalchemy.orm import selectinload
    from app.models.m47_platform import SlackUserLink
    from app.models.user import User
    from app.models.workflow import ApprovalRequest, ApprovalStatus
    from app.services import approval_service as aps
    from app.services import pat_service as pats
    action = ((payload.get("actions") or [{}])[0] or {}).get("value") or ""
    verb, _, rid = action.partition(":")
    slack_user = str((payload.get("user") or {}).get("id") or "")[:40]
    if verb not in ("approve", "reject"):
        return "Unknown action."
    link = await db.get(SlackUserLink, slack_user) if slack_user else None
    user = None
    if link is not None:
        user = (await db.execute(select(User).options(selectinload(User.roles)).where(User.id == link.user_id))).scalars().first()
    if user is None or not user.is_active or (user.email or "").lower() != link.email.lower():
        return "Your Slack account is not linked to an ERP user. Link it under Messaging channels in the ERP."
    try:
        req = await db.get(ApprovalRequest, _uuid.UUID(rid), options=[selectinload(ApprovalRequest.steps)], with_for_update=True)
    except ValueError:
        req = None
    if req is None or req.status != ApprovalStatus.PENDING:
        return "This request is no longer waiting for a decision."
    step = next((s for s in req.steps if s.level == req.current_level and s.status == ApprovalStatus.PENDING), None)
    roles = {r.name for r in user.roles if getattr(r, "is_active", True)}
    if step is None or not (user.is_superuser or step.required_role in roles):
        pats.audit(db, user, "SLACK_APPROVAL_REFUSED", "approval_request", rid, {"reason": "role"})
        return "You may not decide this request."
    if req.requested_by_id and req.requested_by_id == user.id:
        pats.audit(db, user, "SLACK_APPROVAL_REFUSED", "approval_request", rid, {"reason": "own request"})
        return "Someone other than the requester must decide."
    try:
        if verb == "approve":
            await aps.approve_request(db, req.id, user.id, notes="Approved in Slack")
        else:
            await aps.reject_request(db, req.id, user.id, reason="Rejected in Slack")
    except HTTPException as e:
        return str(e.detail)
    done = "Approved" if verb == "approve" else "Rejected"
    pats.audit(db, user, f"SLACK_APPROVAL_{done.upper()}", "approval_request", rid, {"slack_user": slack_user})
    return f"{done} by {user.full_name or user.username}."


async def slack_tick(db: AsyncSession, now: Optional[datetime] = None) -> dict:
    """Queue new notices (last 24 h) and post queued / failed ones (≤5 attempts). Without SLACK_WEBHOOK_URL nothing
    is queued or sent."""
    from app.models.m47_platform import SlackRoute
    routes = {} if db is None else {   # db None: configuration check only (unit tests)
        r.event_type: r.webhook_url for r in (await db.execute(select(SlackRoute).where(SlackRoute.active.is_(True)))).scalars()
        if valid_webhook(r.webhook_url)}
    if not settings.SLACK_WEBHOOK_URL and not routes:
        return {"status": "NOT_CONFIGURED", "sent": 0}
    now = now or datetime.now(timezone.utc)
    for kind, ref, text in await _collect(db, now - timedelta(hours=24)):
        if not (routes.get(kind) or settings.SLACK_WEBHOOK_URL):
            continue                       # no destination for this event type
        await db.execute(insert(SlackDelivery).values(kind=kind, ref=ref, text=text[:1000])
                         .on_conflict_do_nothing(constraint="uq_crm_slack_delivery"))
    due = list((await db.execute(select(SlackDelivery).where(SlackDelivery.status != "SENT", SlackDelivery.attempts < 5)
                                 .order_by(SlackDelivery.created_at).limit(50).with_for_update(skip_locked=True))).scalars())
    sent = 0
    async with provider_client(timeout=10.0) as c:
        for d in due:
            url = routes.get(d.kind) or settings.SLACK_WEBHOOK_URL
            if not url:
                continue
            d.attempts += 1
            blocks = _blocks(d)
            try:
                r = await c.post(url, json={"text": d.text, **({"blocks": blocks} if blocks else {})})
                ok = r.status_code == 200
                d.error = None if ok else f"HTTP {r.status_code}: {r.text[:200]}"
            except Exception as e:   # network / egress refusal: keep for retry
                ok, d.error = False, str(e)[:300]
            d.status = "SENT" if ok else "FAILED"
            sent += ok
    await db.commit()
    return {"status": "OK", "sent": sent, "pending": len(due) - sent}
