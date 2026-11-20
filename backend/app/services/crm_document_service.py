"""M36.S03.T001 sales document engagement: share a quotation by link and see when it is opened.

- Link: 192-bit random token, stored only as SHA-256; expiry (1-90 days) and revocation; the URL is shown once.
- Public view: only what the customer is meant to see (quote number, dates, lines, prices, totals,
  customer-facing notes) — never internal notes, costs, approvals or other customers' data.
- Views: recorded by the page itself after it renders (mail scanners that pre-fetch the link do not run
  it), one event per visitor per 30 minutes. No IP address or user agent is stored, only a keyed hash
  (rotates with SECRET_KEY) used to merge repeat views.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.crm import CRMDocumentLink, CRMDocumentView
from app.models.quotation import Quotation, QuotationLine

DEDUPE = timedelta(minutes=30)
SHAREABLE = {"SENT", "ACCEPTED", "DRAFT"}


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_link(db: AsyncSession, quote: Quotation, user_id: Optional[UUID], days: int,
                      label: Optional[str]) -> tuple[CRMDocumentLink, str]:
    token = secrets.token_urlsafe(24)
    link = CRMDocumentLink(quotation_id=quote.id, token_hash=_digest(token), label=label, created_by_id=user_id,
                           created_at=_now(), expires_at=_now() + timedelta(days=days), view_count=0)
    db.add(link)
    await db.flush()
    return link, token


def link_out(link: CRMDocumentLink) -> dict:
    now = _now()
    state = "REVOKED" if link.revoked_at else ("EXPIRED" if link.expires_at <= now else "ACTIVE")
    iso = lambda v: v.isoformat() if v else None  # noqa: E731
    return {"id": str(link.id), "label": link.label, "state": state, "created_at": iso(link.created_at),
            "expires_at": iso(link.expires_at), "revoked_at": iso(link.revoked_at), "views": link.view_count,
            "first_viewed_at": iso(link.first_viewed_at), "last_viewed_at": iso(link.last_viewed_at)}


class LinkGone(Exception):
    pass


async def resolve(db: AsyncSession, token: str, for_update: bool = False) -> CRMDocumentLink:
    """The live link for a token; LinkGone for unknown, revoked or expired links (same answer for all)."""
    q = select(CRMDocumentLink).where(CRMDocumentLink.token_hash == _digest(token))
    if for_update:
        q = q.with_for_update()
    link = (await db.execute(q)).scalar_one_or_none()
    if link is None or link.revoked_at is not None or link.expires_at <= _now():
        raise LinkGone()
    return link


def _money(v) -> Optional[str]:
    return None if v is None else f"{v:.2f}"


def _num(v) -> str:
    """20.000 -> '20', 12.500 -> '12.5' (no trailing zeros, no exponent)."""
    from decimal import Decimal
    return format(Decimal(v or 0).normalize(), "f")


async def public_document(db: AsyncSession, link: Any, *, any_status: bool = False) -> dict:
    q = (await db.execute(select(Quotation).options(
        selectinload(Quotation.customer), selectinload(Quotation.lines).selectinload(QuotationLine.product))
        .where(Quotation.id == link.quotation_id))).scalar_one_or_none()
    status = getattr(q.status, "value", q.status) if q is not None else None
    if q is None or (status in ("REJECTED", "EXPIRED") and not any_status):  # withdrawn offers are not shown any more
        raise LinkGone()
    lines = []
    for ln in sorted(q.lines, key=lambda x: x.line_no):
        lines.append({"description": (ln.product.name if ln.product else None) or ln.description or "",
                      "sku": ln.product.sku if ln.product else None, "qty": _num(ln.qty), "unit": ln.unit,
                      "unit_price": _money(ln.unit_price), "discount_pct": _num(ln.discount_pct),
                      "tax_rate": _num(ln.tax_rate), "line_total": _money(ln.line_total)})
    doc = {
        "type": "quotation", "number": q.quote_no, "version": q.version, "status": status,
        "customer": q.customer.name if q.customer else None, "quote_date": q.quote_date.isoformat(),
        "valid_until": q.valid_until.isoformat() if q.valid_until else None, "currency": q.currency,
        "discount_pct": _num(q.discount_pct), "total_amount": _money(q.total_amount),
        "tax_amount": _money(q.tax_amount), "grand_total": _money(q.grand_total), "notes": q.notes,
        "lines": lines, "link_expires_at": link.expires_at.isoformat(),
    }
    doc["document_hash"] = document_hash(doc)
    doc["can_decide"] = status == "SENT"
    return doc


def viewer_hash(link_id: UUID, client_ip: str, user_agent: str) -> str:
    key = hashlib.sha256(b"fmcg-erp:document-viewer:v1\0" + settings.SECRET_KEY.encode()).digest()
    return hmac.new(key, f"{link_id}|{client_ip}|{user_agent[:300]}".encode(), hashlib.sha256).hexdigest()


async def record_view(db: AsyncSession, link: CRMDocumentLink, viewer: str) -> bool:
    """Count a visit unless the same visitor was seen on this link in the last 30 minutes. Caller locks the link."""
    now = _now()
    recent = (await db.execute(select(CRMDocumentView).where(
        CRMDocumentView.link_id == link.id, CRMDocumentView.viewer_hash == viewer,
        CRMDocumentView.last_seen_at > now - DEDUPE).order_by(CRMDocumentView.last_seen_at.desc()).limit(1))).scalar_one_or_none()
    if recent is not None:
        recent.last_seen_at = now
        return False
    db.add(CRMDocumentView(link_id=link.id, viewer_hash=viewer, viewed_at=now, last_seen_at=now))
    link.view_count = (link.view_count or 0) + 1
    link.first_viewed_at = link.first_viewed_at or now
    link.last_viewed_at = now
    return True


# ── M36.S04.T003 customer decision (accept / decline) ─────────────────────────

class DecisionRefused(Exception):
    """Shown to the customer as is."""


def document_hash(doc: dict) -> str:
    """SHA-256 of the customer-facing content (status and link expiry excluded: they change by design)."""
    import json
    content = {k: v for k, v in doc.items() if k not in ("status", "link_expires_at", "document_hash", "decision", "can_decide")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


async def decision_for(db: AsyncSession, quotation_id: UUID):
    from app.models.crm import CRMQuoteDecision
    return (await db.execute(select(CRMQuoteDecision).where(CRMQuoteDecision.quotation_id == quotation_id))).scalar_one_or_none()


def decision_out(d, current_hash: Optional[str] = None) -> Optional[dict]:
    if d is None:
        return None
    out = {"decision": d.decision, "signer_name": d.signer_name, "signer_email": d.signer_email, "reason": d.reason,
           "decided_at": d.decided_at.isoformat(), "document_hash": d.document_hash, "evidence_hash": d.evidence_hash,
           "reference": d.evidence_hash[:12].upper()}
    if current_hash is not None:
        out["unchanged_since_signing"] = current_hash == d.document_hash
    return out


async def decide(db: AsyncSession, link: CRMDocumentLink, *, decision: str, signer_name: str, signer_email: str,
                 seen_hash: str, reason: Optional[str], viewer: str):
    """Record the customer's decision. The same rules as the sales team's own accept: only a SENT quote,
    not past its validity date, with any discount approval in place. Conversion to a sales order stays a
    staff step, so pricing and credit checks still run there. Caller holds the link lock and commits."""
    from app.models.crm import CRMQuoteDecision
    from app.models.quotation import QuoteStatus

    q = (await db.execute(select(Quotation).where(Quotation.id == link.quotation_id).with_for_update())).scalar_one_or_none()
    if q is None:
        raise LinkGone()
    if await decision_for(db, q.id) is not None:
        raise DecisionRefused("This quotation has already been answered.")
    if q.status != QuoteStatus.SENT:
        raise DecisionRefused("This quotation can no longer be answered online. Please contact your POVU representative.")
    from zoneinfo import ZoneInfo
    if q.valid_until and q.valid_until < datetime.now(ZoneInfo("Africa/Nairobi")).date():
        raise DecisionRefused("This quotation has expired. Ask your POVU representative for a new one.")
    if decision == "ACCEPTED" and q.discount_approval_required and not q.discount_approved_at:
        raise DecisionRefused("This quotation is still being approved internally. Please try again later.")
    shown = await public_document(db, link)
    current = document_hash(shown)
    if not hmac.compare_digest(current, seen_hash):
        raise DecisionRefused("The quotation changed while you were reading it. Please reload the page and check it again.")
    now = _now()
    evidence = hashlib.sha256(
        f"{current}|{decision}|{signer_name}|{signer_email.lower()}|{now.isoformat()}|{link.id}|{q.id}".encode()).hexdigest()
    rec = CRMQuoteDecision(quotation_id=q.id, link_id=link.id, decision=decision, signer_name=signer_name,
                           signer_email=signer_email.lower(), reason=reason, decided_at=now, document_hash=current,
                           evidence_hash=evidence, viewer_hash=viewer,
                           document_snapshot={k: v for k, v in shown.items() if k not in ("can_decide", "link_expires_at")})
    db.add(rec)
    if decision == "ACCEPTED":
        q.status, q.accepted_at = QuoteStatus.ACCEPTED, now
    else:
        q.status, q.rejected_at = QuoteStatus.REJECTED, now
        q.lost_reason = f"Declined online by {signer_name}" + (f": {reason}" if reason else "")
    await db.flush()
    return rec
