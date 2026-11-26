"""M46.S01.T003 AI brand voice and content studio. Prefix /api/v1/content-studio.

marketing.view reads; marketing.create/edit writes drafts; marketing.approve manages brand profiles and decides
reviews. Drafts are never published from here (see content_studio_service).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.cms import CmsPage, CsBrandProfile, CsDraft, CsUsage
from app.services import cms_service as cms
from app.services import content_studio_service as cs

router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view",)))])
EDIT = ("marketing.create", "marketing.edit")
APPROVE = ("marketing.approve",)


def _need(user, perms) -> None:
    if not (user.is_superuser or has_any_permission(user, perms)):
        raise HTTPException(403, "You do not have permission for this content action.")


def _profile_out(p: CsBrandProfile, usage: Optional[CsUsage] = None) -> dict:
    return {"id": str(p.id), "key": p.key, "name": p.name, "voice": p.voice, "banned_terms": p.banned_terms or [],
            "terminology": p.terminology or {}, "claim_terms": p.claim_terms or [], "evidence": p.evidence or [],
            "asset_ids": p.asset_ids or [], "monthly_budget": float(p.monthly_budget or 0),
            "spent_this_month": round(usage.spent, 4) if usage else 0.0, "calls_this_month": usage.calls if usage else 0}


def _draft_out(d: CsDraft) -> dict:
    return {"id": str(d.id), "profile_id": str(d.profile_id), "channel": d.channel, "template": d.template, "brief": d.brief, "body": d.body,
            "engine": d.engine, "cost": float(d.cost or 0), "findings": d.findings or [], "history": d.history or [], "status": d.status,
            "source_id": str(d.source_id) if d.source_id else None, "created_by": d.created_by, "approved_by": d.approved_by,
            "created_at": d.created_at.isoformat() if d.created_at else None}


@router.get("/options")
async def options():
    return {"channels": cs.CHANNELS, "templates": cs.TEMPLATES}


@router.get("/profiles")
async def profiles(db: AsyncSession = Depends(get_db)):
    month = cs._month()
    usage = {u.profile_id: u for u in (await db.execute(select(CsUsage).where(CsUsage.month == month))).scalars()}
    return [_profile_out(p, usage.get(p.id)) for p in (await db.execute(select(CsBrandProfile).order_by(CsBrandProfile.name))).scalars()]


class ProfileIn(BaseModel):
    key: Optional[str] = Field(None, max_length=40)
    name: Optional[str] = Field(None, max_length=150)
    voice: Optional[str] = Field(None, max_length=4000)
    banned_terms: Optional[list[str]] = None
    terminology: Optional[dict[str, str]] = None
    claim_terms: Optional[list[str]] = None
    evidence: Optional[list[dict]] = None
    asset_ids: Optional[list[uuid.UUID]] = None
    monthly_budget: Optional[float] = Field(None, ge=0, le=10000)


async def _apply(db, p: CsBrandProfile, b: ProfileIn) -> None:
    if b.name:
        p.name = b.name.strip()
    if b.voice is not None:
        p.voice = b.voice.strip()
    if b.banned_terms is not None:
        p.banned_terms = [t.strip()[:60] for t in b.banned_terms if t.strip()][:200]
    if b.terminology is not None:
        p.terminology = {k.strip()[:60]: v.strip()[:60] for k, v in b.terminology.items() if k.strip() and v.strip()}
    if b.claim_terms is not None:
        p.claim_terms = [t.strip()[:40] for t in b.claim_terms if t.strip()][:100]
    if b.evidence is not None:
        ev = []
        for i, e in enumerate(b.evidence[:200]):
            text, src = str(e.get("text") or "").strip()[:500], str(e.get("source") or "").strip()[:300]
            if not text or not src:
                raise HTTPException(422, "Each evidence item needs the fact text and its source")
            ev.append({"id": str(e.get("id") or f"e{i + 1}")[:40], "text": text, "source": src})
        p.evidence = ev
    if b.asset_ids is not None:                         # only APPROVED / PRINT_READY brand assets may guide content
        from app.models.brand_assets import AssetStatus, BrandAsset
        ok = set((await db.execute(select(BrandAsset.id).where(BrandAsset.id.in_(b.asset_ids or [None]),
                                                               BrandAsset.status.in_([AssetStatus.APPROVED, AssetStatus.PRINT_READY])))).scalars())
        bad = [str(a) for a in b.asset_ids if a not in ok]
        if bad:
            raise HTTPException(422, f"Only approved brand assets can be used: {', '.join(bad[:3])}")
        p.asset_ids = [str(a) for a in b.asset_ids]
    if b.monthly_budget is not None:
        p.monthly_budget = Decimal(str(b.monthly_budget))


@router.post("/profiles", status_code=201)
async def create_profile(b: ProfileIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    key = cms.slugify(b.key or b.name or "brand")[:40]
    if (await db.execute(select(CsBrandProfile.id).where(CsBrandProfile.key == key))).first():
        raise HTTPException(409, "A profile with this key exists")
    p = CsBrandProfile(key=key, name=(b.name or key)[:150], voice="", banned_terms=[], terminology={}, claim_terms=[], evidence=[],
                       asset_ids=[], monthly_budget=Decimal("0"))
    await _apply(db, p, b)
    db.add(p)
    await db.flush()
    cms.audit(db, user, "studio.profile.created", "cs_profile", p.id, {"key": key})
    await db.commit()
    await db.refresh(p)
    return _profile_out(p)


@router.patch("/profiles/{pid}")
async def update_profile(pid: uuid.UUID, b: ProfileIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    p = await db.get(CsBrandProfile, pid)
    if p is None:
        raise HTTPException(404, "Not found")
    await _apply(db, p, b)
    cms.audit(db, user, "studio.profile.updated", "cs_profile", p.id, {"fields": sorted(b.model_fields_set)})
    await db.commit()
    await db.refresh(p)
    return _profile_out(p)


@router.get("/drafts")
async def drafts(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(CsDraft).order_by(CsDraft.created_at.desc()).limit(200)
    if status:
        q = q.where(CsDraft.status == status)
    return [_draft_out(d) for d in (await db.execute(q)).scalars()]


class GenerateIn(BaseModel):
    profile_id: uuid.UUID
    channel: str
    template: str
    brief: str = Field(max_length=2000)
    evidence_ids: list[str] = []
    source_id: Optional[uuid.UUID] = None


@router.post("/drafts", status_code=201)
async def generate(b: GenerateIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    p = await db.get(CsBrandProfile, b.profile_id)
    if p is None:
        raise HTTPException(404, "Profile not found")
    src = await db.get(CsDraft, b.source_id) if b.source_id else None
    brief = b.brief if not src else (b.brief or src.body)
    try:
        d = await cs.generate(db, p, b.channel, b.template, brief, b.evidence_ids, user, src)
    except cs.StudioError as e:
        raise HTTPException(422, str(e))
    await db.flush()
    cms.audit(db, user, "studio.draft.generated", "cs_draft", d.id, {"engine": d.engine, "cost": float(d.cost), "channel": d.channel})
    await db.commit()
    await db.refresh(d)
    return _draft_out(d)


class EditIn(BaseModel):
    body: str = Field(max_length=20000)


class DecideIn(BaseModel):
    ok: bool
    note: str = Field("", max_length=300)


async def _draft(db, did):
    d = await db.get(CsDraft, did)
    if d is None:
        raise HTTPException(404, "Not found")
    return d


@router.patch("/drafts/{did}")
async def edit(did: uuid.UUID, b: EditIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    d = await _draft(db, did)
    try:
        cs.edit(await db.get(CsBrandProfile, d.profile_id), d, b.body, user)
    except cs.StudioError as e:
        raise HTTPException(422, str(e))
    await db.commit()
    await db.refresh(d)
    return _draft_out(d)


@router.post("/drafts/{did}/submit")
async def submit(did: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    d = await _draft(db, did)
    try:
        cs.submit(d, user)
    except cs.StudioError as e:
        raise HTTPException(422, str(e))
    await db.commit()
    await db.refresh(d)
    return _draft_out(d)


@router.post("/drafts/{did}/decide")
async def decide(did: uuid.UUID, b: DecideIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    d = await _draft(db, did)
    try:
        cs.decide(d, user, b.ok, b.note, await db.get(CsBrandProfile, d.profile_id))
    except cs.StudioError as e:
        raise HTTPException(422, str(e))
    cms.audit(db, user, "studio.draft.approved" if b.ok else "studio.draft.rejected", "cs_draft", d.id, {"note": b.note})
    await db.commit()
    await db.refresh(d)
    return _draft_out(d)


class RemixIn(BaseModel):
    channels: list[str] = Field(min_length=1, max_length=6)


@router.post("/drafts/{did}/remix", status_code=201)
async def remix(did: uuid.UUID, b: RemixIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """One draft per channel from this draft (repurpose path: budget gate, brand review; each needs its own approval)."""
    _need(user, EDIT)
    src = await _draft(db, did)
    try:
        out = await cs.remix(db, await db.get(CsBrandProfile, src.profile_id), src, b.channels, user)
    except cs.StudioError as e:
        raise HTTPException(422, str(e))
    await db.flush()
    cms.audit(db, user, "studio.draft.remixed", "cs_draft", src.id, {"drafts": [str(d.id) for d in out], "engines": [d.engine for d in out]})
    await db.commit()
    for d in out:
        await db.refresh(d)
    return [_draft_out(d) for d in out]


@router.get("/images/status")
async def image_status():
    from app.services import image_gen_adapter as ig
    return ig.status()


class ImageIn(BaseModel):
    prompt: str = Field(min_length=10, max_length=1000)
    title: str = Field(min_length=1, max_length=200)


@router.post("/images", status_code=201)
async def generate_image(b: ImageIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """AI image → DRAFT MARKETING_CREATIVE document in the asset library. It is not usable in e-mail, social or the
    website until approved (and scanned clean) in the DAM. 409 NOT_CONFIGURED without an image provider."""
    import io

    from fastapi import UploadFile
    from starlette.datastructures import Headers

    from app.models.documents import Document, DocumentCategory, DocumentStatus
    from app.services import image_gen_adapter as ig
    from app.services.document_storage_service import get_document_storage, scan_document
    _need(user, EDIT)
    gen = ig.get_generator()
    if gen is None:
        raise HTTPException(409, ig.status())
    try:
        png = await gen.generate(b.prompt)
    except Exception as e:                 # provider failure is reported, never replaced by a stock image
        raise HTTPException(502, f"The image provider failed: {type(e).__name__}")
    storage = get_document_storage()      # same validation as a manual upload: PNG magic bytes, size limit
    stored = await storage.store_upload(UploadFile(io.BytesIO(png), filename="generated.png", headers=Headers({"content-type": "image/png"})))
    scan = await scan_document(storage.path_for(stored.storage_key))
    doc = Document(title=b.title.strip(), category=DocumentCategory.MARKETING_CREATIVE, status=DocumentStatus.DRAFT,
                   description=f"AI generated ({getattr(gen, 'name', 'provider')}). Prompt: {b.prompt.strip()}",
                   document_type="AI_IMAGE", file_name=stored.file_name, file_size_bytes=stored.file_size_bytes, mime_type=stored.mime_type,
                   storage_provider="local", storage_key=stored.storage_key, file_checksum_sha256=stored.sha256,
                   file_scan_status=scan.status, file_scan_result=scan.result, owner_user_id=user.id, created_by_id=user.id, updated_by_id=user.id)
    db.add(doc)
    await db.flush()
    cms.audit(db, user, "studio.image.generated", "document", doc.id, {"engine": getattr(gen, "name", "provider"), "scan": scan.status})
    await db.commit()
    return {"document_id": str(doc.id), "status": doc.status.value, "scan": scan.status, "engine": getattr(gen, "name", "provider"),
            "detail": "Draft creative: approve it in the asset library before use."}


class UseIn(BaseModel):
    page_id: uuid.UUID


@router.post("/drafts/{did}/to-page")
async def to_page(did: uuid.UUID, b: UseIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Append an APPROVED draft to a CMS page draft as text blocks. The page still needs its own review and publish."""
    _need(user, EDIT)
    d = await _draft(db, did)
    if d.status != "APPROVED":
        raise HTTPException(422, "Only approved drafts can be used")
    p = await db.get(CmsPage, b.page_id)
    if p is None:
        raise HTTPException(404, "Page not found")
    text = cs.CITE.sub("", d.body).strip()
    doc = dict(p.draft or {"blocks": [], "seo": {}})
    doc["blocks"] = [*(doc.get("blocks") or []), *({"type": "text", "text": para.strip()} for para in text.split("\n") if para.strip())]
    try:
        p.draft, _ = cms.validate_doc(doc)
    except cms.CmsError as e:
        raise HTTPException(422, str(e))
    if p.status in ("IN_REVIEW", "APPROVED"):
        p.status, p.approved_by = "DRAFT", None
    p.updated_by = user.username
    cms.audit(db, user, "studio.draft.used", "cms_page", p.id, {"draft": str(d.id)})
    await db.commit()
    return {"ok": True, "page_id": str(p.id)}
