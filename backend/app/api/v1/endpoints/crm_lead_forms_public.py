"""Public website lead forms (no login). Allow-listed in module_registry.PUBLIC_ROUTES."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.crm import CRMLeadForm
from app.services import crm_lead_capture_service as capture

router = APIRouter()


async def _active_form(db: AsyncSession, slug: str) -> CRMLeadForm:
    if len(slug) > 80:
        raise HTTPException(404, "Form not found")
    form = (await db.execute(select(CRMLeadForm).where(CRMLeadForm.slug == slug))).scalar_one_or_none()
    if form is None or not form.active_flag:
        raise HTTPException(404, "Form not found")
    return form


@router.get("/{slug}")
async def get_public_form(slug: str, db: AsyncSession = Depends(get_db)):
    form = await _active_form(db, slug)
    return {"slug": form.slug, "title": form.title, "intro": form.intro, "consent_text": form.consent_text,
            "require_consent": form.require_consent}


@router.post("/{slug}/submit", status_code=202)
async def submit_public_form(slug: str, body: capture.LeadSubmission, request: Request,
                             db: AsyncSession = Depends(get_db)):
    """Same 202 answer for new, repeat and trapped submissions, so the form reveals nothing about existing leads.
    The per-IP limit uses the connection address: behind a reverse proxy run the API with
    FORWARDED_ALLOW_IPS set to that proxy only, so X-Forwarded-For is trusted from it and nobody else."""
    form = await _active_form(db, slug)
    try:
        await capture.submit(db, form, body, request.client.host if request.client else None)
    except capture.RateLimited:
        raise HTTPException(429, "Too many submissions; please try again later.")
    except capture.ConsentRequired:
        raise HTTPException(422, "Please accept the consent statement to send the form.")
    return {"status": "received", "message": form.success_message or "Thank you — we will be in touch."}
