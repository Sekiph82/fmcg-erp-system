"""Employee digital business cards (M42).

Every employee gets a card automatically (screen, API or Excel/CSV import); the public page is
/kartvizit/<slug>. The slug is issued once from the name and never changes, so printed QR codes keep working.
The card shows the employee's own name, role, work phone and work e-mail (read live from the employee record) and
the profile photo HR uploaded with the employee's consent. Everything else on the page (cover video, logo,
videos, gallery, catalogue) is the shared POVU brand content from CARD_ASSETS_BASE_URL.
A terminated or archived employee's card is closed: the public answer is the same as for an unknown slug.
Never exposed: personal numbers, M-Pesa, bank, salary, employee code, department, manager.
"""
from __future__ import annotations

import base64
import binascii
import io
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.hr import Employee, EmployeeBusinessCard, EmployeeStatus

PUBLISHED, REVOKED = "PUBLISHED", "REVOKED"
PHOTO_MAX = 400 * 1024
_TR = str.maketrans({"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ç": "c", "Ç": "C",
                     "ö": "o", "Ö": "O", "ü": "u", "Ü": "U"})


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", (name or "").translate(_TR)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:100].strip("-")
    return slug or "employee"


async def _free_slug(db: AsyncSession, base: str) -> str:
    taken = set((await db.execute(select(EmployeeBusinessCard.slug).where(
        (EmployeeBusinessCard.slug == base) | EmployeeBusinessCard.slug.like(f"{base}-%")))).scalars())
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def closed(emp: Employee) -> bool:
    return emp.status == EmployeeStatus.TERMINATED or emp.archived_at is not None


def is_live(card: Optional[EmployeeBusinessCard], emp: Optional[Employee]) -> bool:
    return card is not None and emp is not None and card.status == PUBLISHED and not closed(emp)


def _audit(db: AsyncSession, actor_id, event: str, card: EmployeeBusinessCard, details: dict | None = None) -> None:
    from app.models.audit_log import AuditLog

    db.add(AuditLog(actor_id=actor_id, event_type=event, module="hr", target_type="business_card",
                    target_id=str(card.id), target_name=card.slug, details=details or {}))


async def card_for(db: AsyncSession, employee_id) -> Optional[EmployeeBusinessCard]:
    return (await db.execute(select(EmployeeBusinessCard).where(EmployeeBusinessCard.employee_id == employee_id))).scalar_one_or_none()


async def ensure_card(db: AsyncSession, emp: Employee, actor_id=None) -> EmployeeBusinessCard:
    """The employee's card, created (and published unless the employee is closed) when missing."""
    card = await card_for(db, emp.id)
    if card is not None:
        return card
    from sqlalchemy import text

    # serialise card creation (same-name employees at the same moment, two tabs opening a new card)
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('employee_business_card_slug'))"))
    card = await card_for(db, emp.id)
    if card is not None:
        return card
    now = datetime.now(timezone.utc)
    live = not closed(emp)
    card = EmployeeBusinessCard(employee_id=emp.id, slug=await _free_slug(db, slugify(emp.full_name)),
                                status=PUBLISHED if live else REVOKED, published_at=now if live else None,
                                revoked_at=None if live else now, revoked_reason=None if live else "employee closed")
    db.add(card)
    await db.flush()
    _audit(db, actor_id, "BUSINESS_CARD_CREATED", card, {"employee_id": str(emp.id), "status": card.status})
    return card


async def after_employee_change(db: AsyncSession, emp: Employee, actor_id=None) -> EmployeeBusinessCard:
    """Called after an employee is created or changed: card exists; a terminated/archived employee's card closes."""
    card = await ensure_card(db, emp, actor_id)
    if closed(emp) and card.status == PUBLISHED:
        card.status, card.revoked_at = REVOKED, datetime.now(timezone.utc)
        card.revoked_reason = "employee terminated" if emp.status == EmployeeStatus.TERMINATED else "employee archived"
        _audit(db, actor_id, "BUSINESS_CARD_REVOKED", card, {"reason": card.revoked_reason})
    return card


def set_status(db: AsyncSession, card: EmployeeBusinessCard, emp: Employee, publish: bool, actor_id, reason: str | None = None) -> None:
    if publish:
        if closed(emp):
            raise HTTPException(409, "This employee is terminated or archived; make the employee active first.")
        card.status, card.published_at, card.revoked_at, card.revoked_reason = PUBLISHED, datetime.now(timezone.utc), None, None
        _audit(db, actor_id, "BUSINESS_CARD_PUBLISHED", card)
    else:
        card.status, card.revoked_at = REVOKED, datetime.now(timezone.utc)
        card.revoked_reason = (reason or "revoked by HR")[:200]
        _audit(db, actor_id, "BUSINESS_CARD_REVOKED", card, {"reason": card.revoked_reason})


# ── content ──────────────────────────────────────────────────────────────────────────────────────────────────────

def card_url(slug: str) -> str:
    return f"{(settings.PUBLIC_APP_URL or '').rstrip('/')}/kartvizit/{slug}"


def _digits(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")


def _email(value: str | None) -> str | None:
    v = (value or "").strip()
    return v if re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", v) else None


def public_view(card: EmployeeBusinessCard, emp: Employee, company=None) -> dict:
    """Only what the card may show."""
    phone = (emp.phone or "").strip()
    return {
        "slug": card.slug,
        "name": emp.full_name,
        "title": card.title_en or emp.role,
        "company": "POVU",
        "website": "https://www.povu.com",
        "phone": phone if card.show_phone and phone else None,
        "whatsapp": _digits(phone) if card.show_whatsapp and _digits(phone) else None,
        "email": _email(emp.email) if card.show_email else None,
        "has_photo": bool(card.photo and card.photo_consent_at),
        "assets_base": settings.CARD_ASSETS_BASE_URL.rstrip("/"),
        "url": card_url(card.slug),
    }


def image_bytes(data_url: str | None) -> tuple[bytes, str] | None:
    m = re.match(r"^data:(image/(?:jpeg|png));base64,(.+)$", data_url or "", re.S)
    if not m:
        return None
    try:
        return base64.b64decode(m.group(2), validate=True), m.group(1)
    except (binascii.Error, ValueError):
        return None


def _v(text: str) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text or "")   # a bare CR/LF must never end the field
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _fold(line: str) -> str:
    """RFC 2425 folding: 75 octets per line, continuation lines start with a space."""
    out, raw = [], line.encode("utf-8")
    while len(raw) > 75:
        cut = 75
        while cut and (raw[cut] & 0xC0) == 0x80:   # never split a UTF-8 character
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = raw[cut:]
        if raw:
            raw = b" " + raw
    out.append(raw.decode("utf-8"))
    return "\r\n".join(out)


def vcard(card: EmployeeBusinessCard, emp: Employee) -> str:
    view = public_view(card, emp)
    parts = emp.full_name.strip().split()
    last, first = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (emp.full_name.strip(), "")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{_v(last)};{_v(first)};;;", f"FN:{_v(emp.full_name.strip())}",
             f"ORG:{_v(view['company'])}", f"TITLE:{_v(view['title'] or '')}"]
    if view["phone"]:
        lines.append(f"TEL;TYPE=WORK,VOICE:{_v(view['phone'])}")
    if view["email"]:
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{_v(view['email'])}")
    lines += [f"URL:{_v(view['url'])}", f"URL;TYPE=WORK:{_v(view['website'])}"]
    img = image_bytes(card.photo) if view["has_photo"] else None
    if img:
        lines.append(f"PHOTO;ENCODING=b;TYPE={'JPEG' if img[1] == 'image/jpeg' else 'PNG'}:{base64.b64encode(img[0]).decode()}")
    lines.append("END:VCARD")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"


def qr(slug: str, fmt: str) -> tuple[bytes, str]:
    """QR code for the public card URL, error correction M (svg or png)."""
    import qrcode
    import qrcode.image.svg

    base = (settings.PUBLIC_APP_URL or "").strip().lower()
    if settings.ENVIRONMENT == "production" and (not base.startswith("https://") or "localhost" in base or "127.0.0.1" in base):
        raise HTTPException(409, "Set PUBLIC_APP_URL to the public https address (e.g. https://erp.povu.com) before making QR codes; "
                                 "a QR code with a local address cannot be scanned from outside.")
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    code.add_data(card_url(slug))
    code.make(fit=True)
    buf = io.BytesIO()
    if fmt == "svg":
        code.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(buf)
        return buf.getvalue(), "image/svg+xml"
    code.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return buf.getvalue(), "image/png"


async def photo_data_url(file) -> str:
    """Validated JPEG/PNG upload as a data URL (max 400 KB)."""
    from app.core.file_validator import validate_upload

    content = await validate_upload(file, allowed_types={"image/jpeg", "image/png"}, max_bytes=PHOTO_MAX)
    kind = "image/jpeg" if content.startswith(b"\xff\xd8\xff") else "image/png" if content.startswith(b"\x89PNG\r\n\x1a\n") else None
    if kind is None:
        raise HTTPException(415, "The photo must be a JPEG or PNG picture.")
    try:
        from PIL import Image

        Image.open(io.BytesIO(content)).verify()
    except Exception:
        raise HTTPException(415, "The photo file is damaged or not a picture.")
    return f"data:{kind};base64,{base64.b64encode(content).decode()}"
