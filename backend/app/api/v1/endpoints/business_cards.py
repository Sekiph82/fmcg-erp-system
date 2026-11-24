"""M42 employee business cards — HR management (hr.cards_manage) and the employee's own card (My business card).
Mounted under /hr. The public card is in business_cards_public.py."""
from __future__ import annotations

import io
import uuid
import zipfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models.hr import Employee, EmployeeBusinessCard
from app.services import business_card_service as cards

router = APIRouter()
MANAGE = Depends(require_permission("hr", "cards_manage"))
ZIP_MAX = 500


def _row(card: EmployeeBusinessCard, emp: Employee, with_photo: bool = False) -> dict:
    out = {"employee_id": str(emp.id), "employee_code": emp.employee_code, "name": emp.full_name, "role": emp.role,
           "department": emp.department, "employee_status": getattr(emp.status, "value", emp.status),
           "card_id": str(card.id), "slug": card.slug, "status": card.status, "live": cards.is_live(card, emp),
           "url": cards.card_url(card.slug), "show_phone": card.show_phone, "show_whatsapp": card.show_whatsapp,
           "show_email": card.show_email, "title_en": card.title_en, "has_photo": bool(card.photo),
           "photo_consent_at": card.photo_consent_at.isoformat() if card.photo_consent_at else None,
           "revoked_reason": card.revoked_reason, "phone": emp.phone if card.show_phone else None,
           "email": emp.email if card.show_email else None, "assets_base": cards.settings.CARD_ASSETS_BASE_URL.rstrip("/")}
    if with_photo:
        out["photo"] = card.photo
        out["public"] = cards.public_view(card, emp)
    return out


async def _employee_card(db: AsyncSession, employee_id: uuid.UUID, actor_id=None) -> tuple[Employee, EmployeeBusinessCard]:
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(404, "Employee not found")
    return emp, await cards.ensure_card(db, emp, actor_id)


async def _filtered(db: AsyncSession, company_id, branch_id, department, status, search):
    q = select(EmployeeBusinessCard, Employee).join(Employee, Employee.id == EmployeeBusinessCard.employee_id)
    if company_id:
        q = q.where(Employee.company_id == company_id)
    if branch_id:
        q = q.where(Employee.branch_id == branch_id)
    if department:
        q = q.where(Employee.department == department)
    if status:
        q = q.where(EmployeeBusinessCard.status == status)
    if search:
        q = q.where(Employee.full_name.ilike(f"%{search}%") | Employee.employee_code.ilike(f"%{search}%"))
    return (await db.execute(q.order_by(Employee.full_name))).all()


@router.get("/cards", dependencies=[MANAGE])
async def list_cards(company_id: Optional[uuid.UUID] = None, branch_id: Optional[uuid.UUID] = None,
                     department: Optional[str] = None, status: Optional[str] = Query(None, pattern="^(PUBLISHED|REVOKED)$"),
                     search: Optional[str] = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    """Every employee's card (cards are created automatically; this list is for printing and checking)."""
    return [_row(c, e) for c, e in await _filtered(db, company_id, branch_id, department, status, search)]


@router.get("/cards/qr.zip", dependencies=[MANAGE])
async def qr_zip(company_id: Optional[uuid.UUID] = None, branch_id: Optional[uuid.UUID] = None,
                 department: Optional[str] = None, search: Optional[str] = Query(None, max_length=100),
                 db: AsyncSession = Depends(get_db)):
    """PNG QR codes of the live cards in the filter, one file per employee (slug.png)."""
    rows = [(c, e) for c, e in await _filtered(db, company_id, branch_id, department, "PUBLISHED", search) if cards.is_live(c, e)]
    if not rows:
        raise HTTPException(404, "No live cards in this selection.")
    if len(rows) > ZIP_MAX:
        raise HTTPException(422, f"{len(rows)} cards selected; choose a department or search so at most {ZIP_MAX} are in one file.")
    slugs = [c.slug for c, _e in rows]

    def build() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for slug in slugs:
                z.writestr(f"{slug}.png", cards.qr(slug, "png")[0])
        return buf.getvalue()

    from starlette.concurrency import run_in_threadpool

    return Response(await run_in_threadpool(build), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="business-card-qr-codes.zip"'})


@router.get("/employees/{employee_id}/card", dependencies=[MANAGE])
async def get_card(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    emp, card = await _employee_card(db, employee_id, current_user.id)
    await db.commit()
    return _row(card, emp, with_photo=True)


class CardUpdate(BaseModel):
    show_phone: Optional[bool] = None
    show_whatsapp: Optional[bool] = None
    show_email: Optional[bool] = None
    title_en: Optional[str] = Field(default=None, max_length=150, pattern=r"^[^\r\n<>]*$")


@router.patch("/employees/{employee_id}/card", dependencies=[MANAGE])
async def update_card(employee_id: uuid.UUID, body: CardUpdate, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    emp, card = await _employee_card(db, employee_id, current_user.id)
    changes = body.model_dump(exclude_unset=True)
    if "title_en" in changes:
        changes["title_en"] = (changes["title_en"] or "").strip() or None
    before = {k: getattr(card, k) for k in changes}
    for k, v in changes.items():
        setattr(card, k, v)
    cards._audit(db, current_user.id, "BUSINESS_CARD_UPDATED", card, {"before": before, "after": changes})
    await db.commit()
    return _row(card, emp, with_photo=True)


@router.post("/employees/{employee_id}/card/photo", dependencies=[MANAGE])
async def upload_photo(employee_id: uuid.UUID, file: UploadFile = File(...), consent: bool = Form(False),
                       db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Profile photo (JPEG/PNG, max 400 KB). Published only with the employee's consent, recorded here."""
    from datetime import datetime, timezone

    if not consent:
        raise HTTPException(422, "Confirm that the employee agreed to their photo being published on the card.")
    emp, card = await _employee_card(db, employee_id, current_user.id)
    card.photo = await cards.photo_data_url(file)
    card.photo_consent_by_id, card.photo_consent_at = current_user.id, datetime.now(timezone.utc)
    cards._audit(db, current_user.id, "BUSINESS_CARD_PHOTO_SET", card, {"consent_recorded_by": str(current_user.id)})
    await db.commit()
    return _row(card, emp, with_photo=True)


@router.delete("/employees/{employee_id}/card/photo", dependencies=[MANAGE])
async def remove_photo(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    emp, card = await _employee_card(db, employee_id, current_user.id)
    card.photo, card.photo_consent_by_id, card.photo_consent_at = None, None, None
    cards._audit(db, current_user.id, "BUSINESS_CARD_PHOTO_REMOVED", card)
    await db.commit()
    return _row(card, emp, with_photo=True)


class RevokeIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=200)


@router.post("/employees/{employee_id}/card/revoke", dependencies=[MANAGE])
async def revoke_card(employee_id: uuid.UUID, body: RevokeIn = RevokeIn(), db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    emp, card = await _employee_card(db, employee_id, current_user.id)
    cards.set_status(db, card, emp, False, current_user.id, body.reason)
    await db.commit()
    return _row(card, emp, with_photo=True)


@router.post("/employees/{employee_id}/card/republish", dependencies=[MANAGE])
async def republish_card(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Same slug as before, so QR codes printed earlier work again (e.g. after a rehire)."""
    emp, card = await _employee_card(db, employee_id, current_user.id)
    cards.set_status(db, card, emp, True, current_user.id)
    await db.commit()
    return _row(card, emp, with_photo=True)


def _qr_response(slug: str, fmt: str) -> Response:
    data, media = cards.qr(slug, fmt)
    return Response(data, media_type=media, headers={"Content-Disposition": f'inline; filename="{slug}.{fmt}"'})


@router.get("/employees/{employee_id}/card/qr.{fmt}", dependencies=[MANAGE])
async def card_qr(employee_id: uuid.UUID, fmt: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if fmt not in ("svg", "png"):
        raise HTTPException(404, "Use qr.svg or qr.png")
    _emp, card = await _employee_card(db, employee_id, current_user.id)
    await db.commit()
    return _qr_response(card.slug, fmt)


# ── the employee's own card (any signed-in employee) ──────────────────────────────────────────────────────────────

async def _my_card(db: AsyncSession, user) -> tuple[Employee, EmployeeBusinessCard]:
    from app.models.hr import EmployeeStatus

    # one login linked to several records (e.g. rehired): the current one — not terminated/archived, newest hire first
    emp = (await db.execute(select(Employee).where(Employee.user_id == user.id).order_by(
        (Employee.status == EmployeeStatus.TERMINATED), Employee.archived_at.isnot(None), Employee.hire_date.desc(),
        Employee.created_at.desc()))).scalars().first()
    if emp is None:
        from app.models.ess import ESSAccount

        hr_id = (await db.execute(select(ESSAccount.hr_employee_id).where(ESSAccount.user_id == user.id))).scalars().first()
        emp = await db.get(Employee, hr_id) if hr_id else None
    if emp is None:
        raise HTTPException(404, "Your login is not linked to an employee record yet. Ask HR to link it.")
    return emp, await cards.ensure_card(db, emp, user.id)


@router.get("/my-card")
async def my_card(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """The signed-in employee's own card: view and share; changes are made by HR."""
    emp, card = await _my_card(db, current_user)
    await db.commit()
    return {**_row(card, emp, with_photo=True), "employee_code": None}


@router.get("/my-card/qr.{fmt}")
async def my_card_qr(fmt: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if fmt not in ("svg", "png"):
        raise HTTPException(404, "Use qr.svg or qr.png")
    _emp, card = await _my_card(db, current_user)
    await db.commit()
    return _qr_response(card.slug, fmt)
