"""E-mail engagement tracking and sales activity analytics (M43.S01.T006).

Opt-in only: a message is tracked when CRM_EMAIL_TRACKING_ENABLED is on, the sender chose tracking for that
e-mail / campaign / sequence, the purpose is not INVOICE, and the recipient has not opted out of tracking.
Tracked mail is sent as text + an HTML alternative whose http(s) links point at a signed redirect and that
carries a 1×1 open pixel. Redirect targets are only the links stored with that message at send time, so the
endpoint can never be used as an open redirect; an optional domain allow-list narrows them further.

Honesty about opens: privacy proxies (Apple Mail Privacy Protection, Gmail image proxy) and security scanners load
pixels and follow links without a person. Events from known proxy/scanner user agents, or within 10 seconds of
sending, are kept but flagged is_machine and excluded from "human" counts; the dashboard says opens are an
indicator, not proof of reading. No raw IP is stored (keyed hash only, for duplicate suppression).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMContactConsent, CRMEmailEvent, CRMOutboundMessage

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
MACHINE_UA = re.compile(r"googleimageproxy|yahoomailproxy|bot|crawl|spider|scanner|proofpoint|mimecast|barracuda|"
                        r"symantec|forcepoint|microsoft office protection|safelinks|curl|python|wget|headless", re.I)
MACHINE_WINDOW = timedelta(seconds=10)
DUP_WINDOW = timedelta(seconds=60)
PIXEL = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def _sign(payload: str) -> str:
    mac = hmac.new(settings.SECRET_KEY.encode(), b"crm-track:" + payload.encode(), hashlib.sha256).digest()[:12]
    return payload + "." + base64.urlsafe_b64encode(mac).decode().rstrip("=")


def token(message_id: UUID, link: int) -> str:
    return _sign(f"{message_id.hex}-{link}")


def parse_token(tok: str) -> Optional[tuple[UUID, int]]:
    payload, _, _ = (tok or "")[:120].rpartition(".")
    if not payload or not hmac.compare_digest(_sign(payload), tok[:120]):
        return None
    try:
        mid, link = payload.split("-")
        return UUID(hex=mid), int(link)
    except ValueError:
        return None


def _allowed(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    allow = [d.strip().lower() for d in (settings.CRM_TRACKING_LINK_DOMAINS or "").split(",") if d.strip()]
    return not allow or any(host == d or host.endswith("." + d) for d in allow)


async def may_track(db: AsyncSession, msg: CRMOutboundMessage) -> bool:
    if not (settings.CRM_EMAIL_TRACKING_ENABLED and msg.track_engagement and msg.purpose != "INVOICE"):
        return False
    c = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == msg.to_email))).scalar_one_or_none()
    return not (c and c.tracking_opt_out)


def render_html(msg: CRMOutboundMessage, text_body: str) -> tuple[str, list[str]]:
    """HTML alternative of the plain text with tracked links and the open pixel. Returns (html, links)."""
    links: list[str] = []
    base = settings.PUBLIC_API_URL.rstrip("/") + "/api/v1/public/t"

    def sub(m: re.Match) -> str:
        url = m.group(0)
        if not _allowed(url) or "/public/unsubscribe" in url or "/unsubscribe?" in url:
            return f'<a href="{html.escape(url)}">{html.escape(url)}</a>'   # unsubscribe stays untracked
        links.append(url)
        return f'<a href="{base}/c/{token(msg.id, len(links))}">{html.escape(url)}</a>'

    escaped = html.escape(text_body)
    # escape first, then linkify on the escaped text (& in query strings becomes &amp; — unescape for storage)
    body = URL_RE.sub(lambda m: sub(re.match(URL_RE, html.unescape(m.group(0)))), escaped)
    body = body.replace("\n", "<br>\n")
    pixel = f'<img src="{base}/o/{token(msg.id, 0)}.gif" width="1" height="1" alt="" style="display:none">'
    return f"<!doctype html><html><body>{body}{pixel}</body></html>", links


def is_machine(msg: CRMOutboundMessage, user_agent: str, now: datetime) -> bool:
    if MACHINE_UA.search(user_agent or ""):
        return True
    return bool(msg.sent_at and now - msg.sent_at < MACHINE_WINDOW)


async def record(db: AsyncSession, tok: str, kind: str, user_agent: str, ip_hash: Optional[str]) -> Optional[str]:
    """Store an OPEN or CLICK. Returns the redirect target for clicks (None = unknown / not trackable)."""
    parsed = parse_token(tok)
    if parsed is None:
        return None
    mid, link = parsed
    msg = await db.get(CRMOutboundMessage, mid)
    if msg is None or msg.status != "SENT":
        return None
    target = None
    if kind == "CLICK":
        links = msg.tracked_links or []
        if not (1 <= link <= len(links)):
            return None
        target = links[link - 1]
    c = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == msg.to_email))).scalar_one_or_none()
    if c and c.tracking_opt_out:
        return target                                   # still redirect, never record
    now = datetime.now(timezone.utc)
    dup = (await db.execute(select(CRMEmailEvent.id).where(
        CRMEmailEvent.message_id == mid, CRMEmailEvent.kind == kind, CRMEmailEvent.link_index == link,
        CRMEmailEvent.ip_hash == ip_hash, CRMEmailEvent.occurred_at >= now - DUP_WINDOW).limit(1))).first()
    if dup is None:
        db.add(CRMEmailEvent(message_id=mid, kind=kind, link_index=link, url=target, occurred_at=now,
                             is_machine=is_machine(msg, user_agent, now), ip_hash=ip_hash,
                             ua_class=("proxy" if "proxy" in (user_agent or "").lower() else
                                       "machine" if MACHINE_UA.search(user_agent or "") else "client")))
        await db.flush()
    return target


async def opt_out(db: AsyncSession, email: str) -> None:
    from app.services.crm_outbound_service import norm
    c = (await db.execute(select(CRMContactConsent).where(CRMContactConsent.email == norm(email)))).scalar_one_or_none()
    if c is None:
        c = CRMContactConsent(email=norm(email), status="SUBSCRIBED", source="tracking-opt-out",
                              updated_at=datetime.now(timezone.utc))
        db.add(c)
    c.tracking_opt_out = True
    await db.flush()


async def analytics(db: AsyncSession, *, since: datetime, created_by: Optional[str] = None) -> dict:
    """Per-sender and per-message aggregates. Human = not flagged as proxy/scanner/too fast."""
    where = [CRMOutboundMessage.status == "SENT", CRMOutboundMessage.sent_at >= since,
             CRMOutboundMessage.purpose != "INVOICE"]
    if created_by:
        where.append(CRMOutboundMessage.created_by == created_by)
    ev = select(
        CRMEmailEvent.message_id,
        func.count().filter(and_(CRMEmailEvent.kind == "OPEN", CRMEmailEvent.is_machine.is_(False))).label("opens"),
        func.count().filter(CRMEmailEvent.kind == "OPEN").label("opens_all"),
        func.count().filter(and_(CRMEmailEvent.kind == "CLICK", CRMEmailEvent.is_machine.is_(False))).label("clicks"),
        func.min(case((and_(CRMEmailEvent.kind == "OPEN", CRMEmailEvent.is_machine.is_(False)),
                       CRMEmailEvent.occurred_at))).label("first_open"),
    ).group_by(CRMEmailEvent.message_id).subquery()
    rows = (await db.execute(select(CRMOutboundMessage, ev.c.opens, ev.c.opens_all, ev.c.clicks, ev.c.first_open)
                             .outerjoin(ev, ev.c.message_id == CRMOutboundMessage.id).where(*where)
                             .order_by(CRMOutboundMessage.sent_at.desc()).limit(2000))).all()
    reps: dict[str, dict] = {}
    messages = []
    for m, opens, opens_all, clicks, first_open in rows:
        r = reps.setdefault(m.created_by or "system", {"sender": m.created_by or "system", "sent": 0, "tracked": 0,
                                                       "opened": 0, "clicked": 0, "machine_only": 0})
        r["sent"] += 1
        if m.track_engagement:
            r["tracked"] += 1
            r["opened"] += 1 if opens else 0
            r["clicked"] += 1 if clicks else 0
            r["machine_only"] += 1 if (opens_all and not opens) else 0
        messages.append({"id": str(m.id), "to": m.to_email, "subject": m.subject, "purpose": m.purpose,
                         "sent_at": m.sent_at.isoformat(), "tracked": bool(m.track_engagement),
                         "human_opens": opens or 0, "machine_opens": (opens_all or 0) - (opens or 0),
                         "clicks": clicks or 0, "first_open": first_open.isoformat() if first_open else None})
    for r in reps.values():
        t = r["tracked"]
        r["open_rate"] = round(r["opened"] / t, 3) if t else None
        r["click_rate"] = round(r["clicked"] / t, 3) if t else None
    unsub = (await db.execute(select(func.count()).select_from(CRMContactConsent).where(
        CRMContactConsent.status == "UNSUBSCRIBED", CRMContactConsent.updated_at >= since))).scalar_one()
    return {"since": since.isoformat(), "senders": sorted(reps.values(), key=lambda r: -r["sent"]),
            "messages": messages[:200], "unsubscribes": unsub,
            "note": "Opens are an indicator only: privacy proxies and scanners load images; flagged machine "
                    "events are excluded from opened/clicked."}
