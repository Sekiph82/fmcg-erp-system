"""M36.S03.T005 website live chat with a help-article bot, hand-off to people and CRM lead creation.

- Visitor: starts a chat on the embeddable page (/chat); gets a random token (stored as SHA-256) that is the
  only way to read or write that chat. No login, no cookies.
- Spam controls: honeypot field, message length limits, per keyed-IP-hash limits on new chats and messages.
- Bot: answers from PUBLISHED PUBLIC help articles only (the knowledge base); otherwise, or when the visitor
  asks for a person, the chat is handed off (status WAITING) and appears in the CRM inbox for staff.
- Lead: created only when the visitor gives an e-mail address and ticks consent; deduplicated against open
  leads of the same e-mail (no lead is ever matched across companies).
- Retention: closed chats older than CHAT_RETENTION_DAYS are deleted with their messages.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMChatMessage, CRMChatSession

NEW_CHATS_PER_HOUR = 5          # per connection (keyed IP hash)
ALL_NEW_CHATS_PER_HOUR = 300    # whole site: stops floods from rotating addresses
MESSAGES_PER_MINUTE = 12
MAX_MESSAGES_PER_CHAT = 300     # per visitor chat, ever
RETENTION_DAYS = 365
BOT_IDLE_DAYS = 7               # chats that never reached a person are removed after a week of silence
HANDOFF_WORDS = re.compile(r"\b(human|person|agent|someone|representative|call me|speak to)\b", re.I)


class ChatRefused(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def start(db: AsyncSession, *, ip: Optional[str], name: Optional[str], email: Optional[str], consent: bool,
                page_url: Optional[str], honeypot: Optional[str]) -> tuple[CRMChatSession, str]:
    from app.services.crm_lead_capture_service import ip_hash

    if honeypot:
        raise ChatRefused(400, "Chat could not be started.")
    hashed = ip_hash(ip)
    site = (await db.execute(select(func.count()).select_from(CRMChatSession).where(
        CRMChatSession.created_at >= _now() - timedelta(hours=1)))).scalar_one()
    if site >= ALL_NEW_CHATS_PER_HOUR:
        raise ChatRefused(429, "Chat is busy right now; please try again later or e-mail us.")
    if hashed:
        recent = (await db.execute(select(func.count()).select_from(CRMChatSession).where(
            CRMChatSession.ip_hash == hashed, CRMChatSession.created_at >= _now() - timedelta(hours=1)))).scalar_one()
        if recent >= NEW_CHATS_PER_HOUR:
            raise ChatRefused(429, "Too many chats from your connection; please try again later.")
    token = secrets.token_urlsafe(32)
    now = _now()
    sess = CRMChatSession(token_hash=_digest(token), visitor_name=(name or None), visitor_email=(email or "").lower() or None,
                          consent_given=bool(consent and email), status="BOT", ip_hash=hashed, page_url=page_url,
                          created_at=now, last_message_at=now)
    db.add(sess)
    await db.flush()
    db.add(CRMChatMessage(session_id=sess.id, sender="BOT", created_at=now,
                          body="Hello! I am the POVU assistant. Ask about our products, orders or deliveries, "
                               "or type 'person' to talk to our team."))
    if sess.consent_given:
        await _ensure_lead(db, sess)
    await db.flush()
    return sess, token


async def by_token(db: AsyncSession, session_id, token: str, lock: bool = False) -> CRMChatSession:
    q = select(CRMChatSession).where(CRMChatSession.id == session_id, CRMChatSession.token_hash == _digest(token))
    sess = (await db.execute(q.with_for_update() if lock else q)).scalar_one_or_none()
    if sess is None:
        raise ChatRefused(404, "Chat not found.")
    return sess


async def _kb_answer(db: AsyncSession, text: str) -> Optional[str]:
    from app.models.knowledge_base import KBArticle
    from app.api.v1.endpoints.kb_public import _public

    words = [w for w in re.findall(r"[A-Za-z]{4,}", text.lower()) if w not in {"what", "when", "where", "which", "with", "have", "your", "this", "that", "from", "please", "about"}][:4]
    if not words:
        return None
    conds = [or_(KBArticle.title.ilike(f"%{w}%"), KBArticle.summary.ilike(f"%{w}%")) for w in words]
    rows = (await db.execute(select(KBArticle.slug, KBArticle.title, KBArticle.summary).where(*_public(), or_(*conds))
                             .order_by(KBArticle.is_featured.desc(), KBArticle.title).limit(3))).all()
    if not rows:
        return None
    lines = [f"• {t}: /kb/{slug}" + (f" — {s}" if s else "") for slug, t, s in rows]
    return "These help articles may answer it:\n" + "\n".join(lines) + "\nType 'person' if you still need our team."


async def visitor_says(db: AsyncSession, sess: CRMChatSession, body: str, *, email: Optional[str] = None,
                       consent: bool = False) -> list[CRMChatMessage]:
    if sess.status == "CLOSED":
        raise ChatRefused(409, "This chat is closed. Start a new one if you need help.")
    recent = (await db.execute(select(func.count()).select_from(CRMChatMessage).where(
        CRMChatMessage.session_id == sess.id, CRMChatMessage.sender == "VISITOR",
        CRMChatMessage.created_at >= _now() - timedelta(minutes=1)))).scalar_one()
    if recent >= MESSAGES_PER_MINUTE:
        raise ChatRefused(429, "You are sending messages too fast.")
    total = (await db.execute(select(func.count()).select_from(CRMChatMessage).where(
        CRMChatMessage.session_id == sess.id, CRMChatMessage.sender == "VISITOR"))).scalar_one()
    if total >= MAX_MESSAGES_PER_CHAT:
        raise ChatRefused(429, "This chat is very long; please start a new one or e-mail us.")
    now = _now()
    out = [CRMChatMessage(session_id=sess.id, sender="VISITOR", body=body, created_at=now)]
    if email and consent and not sess.consent_given:
        sess.visitor_email, sess.consent_given = email.lower(), True
        await _ensure_lead(db, sess)
    if sess.status == "BOT":
        answer = None if HANDOFF_WORDS.search(body) else await _kb_answer(db, body)
        if answer is None:
            sess.status = "WAITING"
            answer = ("Thank you, a member of our team will reply here shortly (working hours, Nairobi time)."
                      + ("" if sess.consent_given else " Leave your e-mail if you would like a reply by e-mail too."))
        out.append(CRMChatMessage(session_id=sess.id, sender="BOT", body=answer, created_at=now + timedelta(milliseconds=1)))
    sess.last_message_at = now
    db.add_all(out)
    await db.flush()
    return out


async def agent_says(db: AsyncSession, sess: CRMChatSession, body: str, agent_id) -> CRMChatMessage:
    if sess.status == "CLOSED":
        raise ChatRefused(409, "This chat is closed.")
    now = _now()
    msg = CRMChatMessage(session_id=sess.id, sender="AGENT", body=body, agent_id=agent_id, created_at=now)
    sess.status, sess.last_message_at = "WAITING", now
    sess.assignee_id = sess.assignee_id or agent_id
    db.add(msg)
    await db.flush()
    return msg


async def messages(db: AsyncSession, sess: CRMChatSession, after: Optional[datetime] = None) -> list[dict]:
    q = select(CRMChatMessage).where(CRMChatMessage.session_id == sess.id)
    if after:  # only what is new since the caller's last message
        rows = (await db.execute(q.where(CRMChatMessage.created_at > after)
                                 .order_by(CRMChatMessage.created_at).limit(200))).scalars().all()
    else:      # the newest 200, oldest first
        rows = list(reversed((await db.execute(q.order_by(CRMChatMessage.created_at.desc()).limit(200))).scalars().all()))
    return [{"id": str(m.id), "from": m.sender.lower(), "body": m.body, "at": m.created_at.isoformat()} for m in rows]


async def _ensure_lead(db: AsyncSession, sess: CRMChatSession) -> None:
    """Consent given with an e-mail: link to the open lead of that address in no company, or create one."""
    from app.models.crm import CRMRecord, CRMRecordType, CRMSourceType, CRMStatus
    from app.services.crm_outbound_service import record_consent
    from app.services.crm_pipeline_service import _next_lead_code

    if sess.crm_record_id or not sess.visitor_email:
        return
    await record_consent(db, sess.visitor_email, "SUBSCRIBED", "website chat",
                         "I agree that POVU may contact me about my question and its products.")
    existing = (await db.execute(select(CRMRecord).where(
        CRMRecord.record_type == CRMRecordType.LEAD, CRMRecord.status == CRMStatus.OPEN,
        func.lower(CRMRecord.contact_email) == sess.visitor_email, CRMRecord.company_id.is_(None))
        .order_by(CRMRecord.created_at).limit(1))).scalar_one_or_none()
    if existing is None:
        existing = CRMRecord(record_type=CRMRecordType.LEAD, lead_code=await _next_lead_code(db),
                             company_name=sess.visitor_name or sess.visitor_email, contact_person_name=sess.visitor_name,
                             contact_email=sess.visitor_email, source_type=CRMSourceType.WEBSITE, source_detail="live chat",
                             created_by="website-chat", activities=[], interest_lines=[])
        db.add(existing)
        await db.flush()
    sess.crm_record_id = existing.id


async def purge_old(db: AsyncSession, days: int = RETENTION_DAYS) -> int:
    """Delete closed chats (and their messages) older than the retention period. Caller commits."""
    cutoff = _now() - timedelta(days=days)
    ended = func.coalesce(CRMChatSession.closed_at, CRMChatSession.last_message_at)
    res = await db.execute(delete(CRMChatSession).where(or_(
        ended < cutoff,  # any chat silent or closed for the retention period
        (CRMChatSession.status == "BOT") & (CRMChatSession.last_message_at < _now() - timedelta(days=BOT_IDLE_DAYS)))))
    return res.rowcount or 0


async def run_purge(interval: float = 24 * 3600) -> None:
    """Lifespan task, once a day: expired chats and expired call recordings (retention)."""
    import asyncio
    import logging

    from app.db.session import AsyncSessionLocal

    from app.api.v1.endpoints.voip import purge_expired_recordings

    while True:
        # each purge in its own transaction: one failing never blocks the other
        for name, job in (("chat", purge_old), ("call recording", purge_expired_recordings)):
            try:
                async with AsyncSessionLocal() as db:
                    await job(db)
                    await db.commit()
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.getLogger(__name__).exception("%s retention purge failed", name)
        await asyncio.sleep(interval)
