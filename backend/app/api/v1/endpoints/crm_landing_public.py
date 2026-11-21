"""Public landing pages (no login): GET shows the visitor's variant and records one view; POST submits the lead
form and records one conversion for that variant. The visitor id is a random id kept by the browser."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.crm import CRMLeadForm
from app.services import crm_landing_service as lp
from app.services import crm_lead_capture_service as capture

router = APIRouter()
VISITOR = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class ConvertIn(BaseModel):
    visitor: str = VISITOR
    lead: capture.LeadSubmission


async def _resolve(db: AsyncSession, slug: str, visitor: str):
    page = await lp.page_by_slug(db, slug)
    if page is None:
        raise HTTPException(404, "Page not found")
    try:
        variant = lp.assign(page.id, visitor, await lp.variants(db, page.id))
    except ValueError:
        raise HTTPException(404, "Page not found")
    return page, variant


@router.get("/{slug}")
async def show(slug: str, visitor: str = Query(..., min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$"),
               db: AsyncSession = Depends(get_db)):
    page, v = await _resolve(db, slug, visitor)
    await lp.record(db, page, v, visitor, "VIEW")
    await db.commit()
    form = await db.get(CRMLeadForm, page.lead_form_id)
    return {"slug": page.slug, "variant": v.key, "headline": v.headline, "body": v.body, "cta_label": v.cta_label,
            "consent_text": form.consent_text, "require_consent": form.require_consent}


@router.post("/{slug}/convert", status_code=202)
async def convert(slug: str, body: ConvertIn, request: Request, db: AsyncSession = Depends(get_db)):
    page, v = await _resolve(db, slug, body.visitor)
    form = await db.get(CRMLeadForm, page.lead_form_id)
    if form is None or not form.active_flag:
        raise HTTPException(404, "Page not found")
    lead = body.lead.model_copy(update={"landing_page": f"lp:{page.slug}:{v.key}", "utm_content": body.lead.utm_content or f"variant-{v.key}"})
    try:
        sub = await capture.submit(db, form, lead, request.client.host if request.client else None)
    except capture.RateLimited:
        raise HTTPException(429, "Too many submissions; please try again later.")
    except capture.ConsentRequired:
        raise HTTPException(422, "Please accept the consent statement to send the form.")
    if getattr(sub, "status", None) != "SPAM":        # bots never count as conversions
        await lp.record(db, page, v, body.visitor, "CONVERT")
    await db.commit()
    return {"status": "received", "message": form.success_message or "Thank you — we will be in touch."}
