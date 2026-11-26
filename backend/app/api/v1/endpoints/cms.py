"""M46 Content hub — staff API. Prefix /api/v1/cms.

Permissions: marketing.view to read; marketing.create/edit to author; marketing.approve to review, publish, roll back,
unpublish and manage access lists. Every state change is audited (module "content").
Sites/pages/versions/redirects/dynamic tables/CTAs/keywords (T001/T002/T005), experiments (T004),
access lists and media (T006). Content studio lives at /content-studio.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.cms import (CmsAccessList, CmsCta, CmsExperiment, CmsKeyword, CmsMedia, CmsMediaView, CmsPage, CmsPageVersion,
                            CmsRedirect, CmsSite, CmsTable, CmsTableRow)
from app.services import cms_media_service as media
from app.services import cms_personalize as pz
from app.services import cms_service as cms

router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view",)))])
EDIT = ("marketing.create", "marketing.edit")
APPROVE = ("marketing.approve",)


def _need(user, perms) -> None:
    if not (user.is_superuser or has_any_permission(user, perms)):
        raise HTTPException(403, "You do not have permission for this content action.")


def _fail(e: Exception):
    raise HTTPException(422, str(e))


async def _get(db, model, oid):
    o = await db.get(model, oid)
    if o is None:
        raise HTTPException(404, "Not found")
    return o


def _site_out(s: CmsSite) -> dict:
    return {"id": str(s.id), "key": s.key, "name": s.name, "default_locale": s.default_locale, "locales": s.locales,
            "domain": s.domain, "domain_status": s.domain_status, "theme": cms.validate_theme(s.theme or {}), "nav": s.nav,
            "require_approval": s.require_approval, "local_url": f"/site/{s.key}"}


def _page_out(p: CmsPage, live: Optional[CmsPageVersion] = None) -> dict:
    return {"id": str(p.id), "site_id": str(p.site_id), "parent_id": str(p.parent_id) if p.parent_id else None, "kind": p.kind,
            "locale": p.locale, "translation_group": str(p.translation_group), "translation_state": p.translation_state,
            "slug": p.slug, "path": p.path, "live_path": p.live_path, "title": p.title, "status": p.status, "access": p.access,
            "access_list_id": str(p.access_list_id) if p.access_list_id else None, "table_id": str(p.table_id) if p.table_id else None,
            "author": p.author, "category": p.category, "tags": p.tags or [], "submitted_by": p.submitted_by, "approved_by": p.approved_by,
            "updated_by": p.updated_by, "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "live_version": live.version if live else None}


# ── sites ────────────────────────────────────────────────────────────────────

class SiteIn(BaseModel):
    key: Optional[str] = Field(None, max_length=40)
    name: Optional[str] = Field(None, max_length=150)
    default_locale: Optional[str] = None
    locales: Optional[list[str]] = None
    domain: Optional[str] = Field(None, max_length=200)
    theme: Optional[dict] = None
    nav: Optional[list[dict]] = None
    require_approval: Optional[bool] = None


def _apply_site(s: CmsSite, b: SiteIn) -> None:
    if b.name is not None:
        s.name = b.name.strip() or s.name
    if b.locales is not None:
        locs = [x for x in dict.fromkeys(b.locales) if x in cms.LOCALES]
        if not locs:
            raise cms.CmsError(f"Locales must be among {cms.LOCALES}")
        s.locales = locs
    if b.default_locale is not None:
        if b.default_locale not in (s.locales or []):
            raise cms.CmsError("The default locale must be one of the site's locales")
        s.default_locale = b.default_locale
    if b.domain is not None:
        d = b.domain.strip().lower()
        if d and not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+", d):
            raise cms.CmsError("Domain must be a host name like www.povu.example.com")
        s.domain = d or None
        s.domain_status = "DNS_PENDING" if d else "LOCAL_ONLY"   # served locally until activation (M47.S02.T001)
    if b.theme is not None:
        s.theme = cms.validate_theme(b.theme)
    if b.nav is not None:
        s.nav = cms.validate_nav(b.nav)
    if b.require_approval is not None:
        s.require_approval = b.require_approval


@router.get("/sites")
async def sites(db: AsyncSession = Depends(get_db)):
    return [_site_out(s) for s in (await db.execute(select(CmsSite).order_by(CmsSite.name))).scalars()]


@router.post("/sites", status_code=201)
async def create_site(b: SiteIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    key = cms.slugify(b.key or b.name or "")[:40]
    if await cms.site_by_key(db, key):
        raise HTTPException(409, "A site with this key exists")
    s = CmsSite(key=key, name=(b.name or key)[:150], locales=["en"], default_locale="en", theme=cms.validate_theme({}), nav=[],
                require_approval=True, domain_status="LOCAL_ONLY", created_by=user.username)
    try:
        _apply_site(s, b)
    except cms.CmsError as e:
        _fail(e)
    db.add(s)
    await db.flush()
    cms.audit(db, user, "cms.site.created", "cms_site", s.id, {"key": key})
    await db.commit()
    await db.refresh(s)
    return _site_out(s)


@router.patch("/sites/{site_id}")
async def update_site(site_id: uuid.UUID, b: SiteIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    s = await _get(db, CmsSite, site_id)
    try:
        _apply_site(s, b)
    except cms.CmsError as e:
        _fail(e)
    cms.audit(db, user, "cms.site.updated", "cms_site", s.id, b.model_dump(exclude_none=True, exclude={"theme", "nav"}))
    await db.commit()
    await db.refresh(s)
    return _site_out(s)


# ── pages ────────────────────────────────────────────────────────────────────

@router.get("/sites/{site_id}/pages")
async def pages(site_id: uuid.UUID, kind: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(CmsPage).where(CmsPage.site_id == site_id)
    if kind:
        q = q.where(CmsPage.kind == kind)
    rows = (await db.execute(q.order_by(CmsPage.path, CmsPage.locale))).scalars().all()
    lives = {v.id: v for v in (await db.execute(select(CmsPageVersion).where(CmsPageVersion.id.in_([p.live_version_id for p in rows if p.live_version_id] or [None])))).scalars()}
    return [_page_out(p, lives.get(p.live_version_id)) for p in rows]


class PageIn(BaseModel):
    site_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    kind: Optional[str] = Field(None, pattern="^(PAGE|POST|DYNAMIC)$")
    locale: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    slug: Optional[str] = Field(None, max_length=120)
    draft: Optional[dict] = None
    access: Optional[str] = Field(None, pattern="^(PUBLIC|MEMBERS)$")
    access_list_id: Optional[uuid.UUID] = None
    table_id: Optional[uuid.UUID] = None
    author: Optional[str] = Field(None, max_length=120)
    category: Optional[str] = Field(None, max_length=80)
    tags: Optional[list[str]] = None


async def _repath(db: AsyncSession, p: CmsPage) -> None:
    p.path = await cms.build_path(db, p.parent_id, p.slug, p.kind)
    clash = (await db.execute(select(CmsPage.id).where(CmsPage.site_id == p.site_id, CmsPage.locale == p.locale, CmsPage.path == p.path,
                                                       CmsPage.id != p.id))).first()
    if clash:
        raise cms.CmsError(f"Another {p.locale} page already uses {p.path}")
    for child in (await db.execute(select(CmsPage).where(CmsPage.parent_id == p.id))).scalars():
        await _repath(db, child)


async def _apply_page(db: AsyncSession, p: CmsPage, b: PageIn, user) -> list[str]:
    warnings: list[str] = []
    content_fields = b.model_fields_set - {"access", "access_list_id"}
    if content_fields and p.status in ("IN_REVIEW", "APPROVED"):      # anything reviewed changed: review again
        p.status, p.approved_by = "DRAFT", None
    if b.title is not None:
        p.title = b.title.strip()[:200] or p.title
    if b.draft is not None:
        doc, warnings = cms.validate_doc(b.draft)
        p.draft = doc
    for k in ("author", "category"):
        if getattr(b, k) is not None:
            setattr(p, k, getattr(b, k).strip() or None)
    if b.tags is not None:
        p.tags = [t.strip()[:40] for t in b.tags if t.strip()][:20]
    if b.access is not None or b.access_list_id is not None:
        _need(user, APPROVE)                              # who may read is a publishing decision
        if b.access is not None:
            p.access = b.access
        if b.access_list_id is not None:
            await _get(db, CmsAccessList, b.access_list_id)
            p.access_list_id = b.access_list_id
        if p.access == "MEMBERS" and not p.access_list_id:
            raise cms.CmsError("A members-only page needs an access list")
    if b.table_id is not None:
        t = await _get(db, CmsTable, b.table_id)
        if t.site_id != p.site_id:
            raise cms.CmsError("The table belongs to another site")
        p.table_id = t.id
    if b.slug is not None or "parent_id" in b.model_fields_set:
        if b.slug is not None:
            p.slug = "home" if b.slug == "home" else cms.slugify(b.slug)
        if "parent_id" in b.model_fields_set:
            if b.parent_id == p.id:
                raise cms.CmsError("A page cannot be its own parent")
            if b.parent_id:
                par = await _get(db, CmsPage, b.parent_id)
                if par.site_id != p.site_id or par.locale != p.locale:
                    raise cms.CmsError("The parent must be a page of the same site and language")
                anc = par
                while anc and anc.parent_id:                  # no cycles in the tree
                    if anc.parent_id == p.id:
                        raise cms.CmsError("That would put the page under itself")
                    anc = await db.get(CmsPage, anc.parent_id)
            p.parent_id = b.parent_id
        await _repath(db, p)
    p.updated_by = user.username
    return warnings


@router.post("/pages", status_code=201)
async def create_page(b: PageIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    if not b.site_id or not b.title:
        raise HTTPException(422, "site_id and title are required")
    s = await _get(db, CmsSite, b.site_id)
    loc = b.locale or s.default_locale
    if loc not in (s.locales or []):
        raise HTTPException(422, f"The site does not use locale {loc}")
    p = CmsPage(id=uuid.uuid4(), site_id=s.id, kind=b.kind or "PAGE", locale=loc, translation_group=uuid.uuid4(), translation_state="SOURCE",
                title=b.title.strip()[:200], slug="", path="", draft={"blocks": [], "seo": {}}, status="DRAFT", access="PUBLIC", tags=[])
    db.add(p)
    try:
        b2 = b.model_copy(update={"slug": b.slug or b.title})
        if "parent_id" not in b.model_fields_set:
            b2 = b2.model_copy(update={"parent_id": None})
        await db.flush()
        warnings = await _apply_page(db, p, b2, user)
        await _repath(db, p)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    cms.audit(db, user, "cms.page.created", "cms_page", p.id, {"path": p.path, "locale": p.locale})
    await db.commit()
    await db.refresh(p)
    return {**_page_out(p), "warnings": warnings}


@router.get("/pages/{page_id}")
async def page(page_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    p = await _get(db, CmsPage, page_id)
    versions = (await db.execute(select(CmsPageVersion).where(CmsPageVersion.page_id == p.id).order_by(CmsPageVersion.version.desc()))).scalars().all()
    live = next((v for v in versions if v.id == p.live_version_id), None)
    siblings = (await db.execute(select(CmsPage).where(CmsPage.translation_group == p.translation_group, CmsPage.id != p.id))).scalars().all()
    return {**_page_out(p, live), "draft": p.draft,
            "versions": [{"version": v.version, "title": v.title, "note": v.note, "published_by": v.published_by,
                          "published_at": v.published_at.isoformat(), "live": v.id == p.live_version_id} for v in versions],
            "translations": [{"id": str(t.id), "locale": t.locale, "path": t.path, "status": t.status, "translation_state": t.translation_state} for t in siblings]}


@router.patch("/pages/{page_id}")
async def update_page(page_id: uuid.UUID, b: PageIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE if b.model_fields_set <= {"access", "access_list_id"} else EDIT)   # access alone is an approver change
    p = await _get(db, CmsPage, page_id)
    try:
        warnings = await _apply_page(db, p, b, user)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    cms.audit(db, user, "cms.page.edited", "cms_page", p.id, {"fields": sorted(b.model_fields_set)})
    await db.commit()
    await db.refresh(p)
    return {**_page_out(p), "warnings": warnings}


class Decision(BaseModel):
    ok: bool = True
    note: str = Field("", max_length=300)
    version: Optional[int] = None


async def _act(db, page_id, user, fn, perms):
    _need(user, perms)
    p = await _get(db, CmsPage, page_id)
    await db.refresh(p, with_for_update=True)       # serialize with concurrent edits (review: approve-vs-edit)
    try:
        out = await fn(p)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    await db.refresh(p)
    return {**_page_out(p), **({"version": out.version} if isinstance(out, CmsPageVersion) else {})}


@router.post("/pages/{page_id}/submit")
async def submit(page_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _act(db, page_id, user, lambda p: cms.submit(db, p, user), EDIT)


@router.post("/pages/{page_id}/approve")
async def approve(page_id: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _act(db, page_id, user, lambda p: cms.approve(db, p, user, b.ok, b.note), APPROVE)


@router.post("/pages/{page_id}/publish")
async def publish(page_id: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _act(db, page_id, user, lambda p: cms.publish(db, p, user, b.note), APPROVE)


@router.post("/pages/{page_id}/rollback")
async def rollback(page_id: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not b.version:
        raise HTTPException(422, "version is required")
    return await _act(db, page_id, user, lambda p: cms.rollback(db, p, b.version, user), APPROVE)


@router.post("/pages/{page_id}/unpublish")
async def unpublish(page_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _act(db, page_id, user, lambda p: cms.unpublish(db, p, user), APPROVE)


@router.get("/pages/{page_id}/preview")
async def preview(page_id: uuid.UUID, version: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """Staff-only preview of the draft (or a past version) rendered exactly as the public page would be, without personalization."""
    p = await _get(db, CmsPage, page_id)
    s = await db.get(CmsSite, p.site_id)
    if version:
        v = (await db.execute(select(CmsPageVersion).where(CmsPageVersion.page_id == p.id, CmsPageVersion.version == version))).scalar_one_or_none()
        if v is None:
            raise HTTPException(404, "Version not found")
        doc = v.content
    else:
        try:
            doc, _ = cms.validate_doc(p.draft or {})
        except cms.CmsError as e:
            _fail(e)
    from app.services import cms_layout_service as L
    tokens = await L.effective_tokens(db, s)
    blocks = L.attach_css(await cms.expand(db, s, doc["blocks"], locale=p.locale), tokens)
    return {"preview": True, "site": {**_site_out(s), "theme": await L.theme_for(db, s, tokens)}, "page": {"title": p.title, "kind": p.kind, "locale": p.locale, "path": p.path,
            "author": p.author, "category": p.category}, "blocks": blocks, "seo": doc.get("seo", {})}


@router.get("/pages/{page_id}/seo-audit")
async def seo_audit(page_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cms.seo_audit(db, await _get(db, CmsPage, page_id))
    except cms.CmsError as e:
        _fail(e)


@router.get("/pages/{page_id}/aeo-audit")
async def aeo_audit(page_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await cms.aeo_audit(db, await _get(db, CmsPage, page_id))
    except cms.CmsError as e:
        _fail(e)


class TranslateIn(BaseModel):
    locale: str
    ai: bool = False                            # machine-translate with a content-studio brand profile's AI budget
    profile_id: Optional[uuid.UUID] = None      # default: the first profile (by name) with a budget


@router.post("/pages/{page_id}/translate", status_code=201)
async def translate(page_id: uuid.UUID, b: TranslateIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Start a translation: a draft in the target locale, linked for hreflang, marked NEEDS_REVIEW. With ai=true the
    texts are machine-translated inside a brand profile's budget, otherwise (or when that is not possible) copied."""
    _need(user, EDIT)
    src = await _get(db, CmsPage, page_id)
    s = await db.get(CmsSite, src.site_id)
    if b.locale not in (s.locales or []) or b.locale == src.locale:
        raise HTTPException(422, "Pick another locale the site uses")
    if (await db.execute(select(CmsPage.id).where(CmsPage.translation_group == src.translation_group, CmsPage.locale == b.locale))).first():
        raise HTTPException(409, "This page already has that translation")
    parent = None
    if src.parent_id:
        par = await db.get(CmsPage, src.parent_id)
        parent = (await db.execute(select(CmsPage.id).where(CmsPage.translation_group == par.translation_group, CmsPage.locale == b.locale))).scalar_one_or_none()
    t = CmsPage(id=uuid.uuid4(), site_id=src.site_id, parent_id=parent, kind=src.kind, locale=b.locale, translation_group=src.translation_group,
                translation_state="NEEDS_REVIEW", slug=src.slug, path="", title=src.title, draft=cms.translation_stub(src, b.locale),
                status="DRAFT", access=src.access, access_list_id=src.access_list_id, table_id=src.table_id, author=src.author,
                category=src.category, tags=src.tags or [], updated_by=user.username)
    db.add(t)
    try:
        await db.flush()
        await _repath(db, t)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    engine, cost = "copy", 0.0
    if b.ai:
        from app.models.cms import CsBrandProfile
        prof = (await db.get(CsBrandProfile, b.profile_id) if b.profile_id else
                (await db.execute(select(CsBrandProfile).where(CsBrandProfile.monthly_budget > 0).order_by(CsBrandProfile.name).limit(1))).scalar_one_or_none())
        if b.profile_id and prof is None:
            await db.rollback()
            raise HTTPException(404, "Brand profile not found")
        t.draft, engine, cost = await cms.ai_translation(db, src, b.locale, prof)
    cms.audit(db, user, "cms.page.translation_started", "cms_page", t.id,
              {"from": src.locale, "to": b.locale, "ai": b.ai, "engine": engine, "cost": round(cost, 4)})
    await db.commit()
    await db.refresh(t)
    return {**_page_out(t), "engine": engine, "cost": round(cost, 4)}


@router.get("/tools")
async def tools():
    """Which optional local engines are installed (narration, ffmpeg poster/trim)."""
    from app.services import tts_adapter as tts
    return {"tts": tts.status(), "ffmpeg": {"status": "AVAILABLE" if media.ffmpeg() else "NOT_AVAILABLE"}}


@router.post("/pages/{page_id}/narrate", status_code=201)
async def narrate(page_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Read the page draft aloud with the local TTS engine into a staff-only AUDIO media item linked to the page.
    An approver makes it public or gated like any other media. 409 NOT_AVAILABLE without an engine."""
    from app.services import tts_adapter as tts
    _need(user, EDIT)
    p = await _get(db, CmsPage, page_id)
    if not tts.engine():
        raise HTTPException(409, tts.status())
    try:
        doc, _ = cms.validate_doc(p.draft or {})
    except cms.CmsError as e:
        _fail(e)
    text = f"{p.title}. {cms._all_text(doc['blocks'])}".strip()
    try:
        wav = await tts.synthesize(text, p.locale)
    except tts.TtsUnavailable as e:
        raise HTTPException(409, {"status": "NOT_AVAILABLE", "detail": str(e)})
    key, size, sha = media.store_bytes(wav, "audio/wav")
    m = CmsMedia(kind="AUDIO", title=f"Narration: {p.title}"[:200], mime="audio/wav", size=size, sha256=sha, storage_path=key, captions={},
                 public=False, access_list_id=None, page_id=p.id, created_by=user.username)
    db.add(m)
    await db.flush()
    cms.audit(db, user, "cms.page.narrated", "cms_page", p.id, {"media_id": str(m.id), "engine": tts.engine(), "chars": len(text)})
    await db.commit()
    await db.refresh(m)
    return _media_out(m)


class TranslationState(BaseModel):
    state: str = Field(pattern="^(NEEDS_REVIEW|REVIEWED)$")


@router.post("/pages/{page_id}/translation-state")
async def translation_state(page_id: uuid.UUID, b: TranslationState, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    p = await _get(db, CmsPage, page_id)
    if p.translation_state == "SOURCE":
        raise HTTPException(422, "This is the source page")
    p.translation_state = b.state
    cms.audit(db, user, "cms.page.translation_state", "cms_page", p.id, {"state": b.state})
    await db.commit()
    return {"ok": True, "translation_state": b.state}


# ── redirects, CTAs, dynamic tables, keywords ─────────────────────────────────

class RedirectIn(BaseModel):
    from_path: str = Field(max_length=400)
    to_path: str = Field(max_length=400)
    code: int = 301


@router.get("/sites/{site_id}/redirects")
async def redirects(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == site_id).order_by(CmsRedirect.from_path))).scalars()
    return [{"id": str(r.id), "from_path": r.from_path, "to_path": r.to_path, "code": r.code, "auto": r.auto, "hits": r.hits} for r in rows]


@router.post("/sites/{site_id}/redirects", status_code=201)
async def add_redirect(site_id: uuid.UUID, b: RedirectIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)                  # changes what live URLs do
    await _get(db, CmsSite, site_id)
    try:
        r = await cms.upsert_redirect(db, site_id, b.from_path, b.to_path, b.code)
    except cms.CmsError as e:
        _fail(e)
    cms.audit(db, user, "cms.redirect.saved", "cms_site", site_id, b.model_dump())
    await db.commit()
    return {"id": str(r.id)}


@router.delete("/redirects/{rid}")
async def delete_redirect(rid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    r = await _get(db, CmsRedirect, rid)
    cms.audit(db, user, "cms.redirect.deleted", "cms_site", r.site_id, {"from": r.from_path})
    await db.delete(r)
    await db.commit()
    return {"ok": True}


class CtaIn(BaseModel):
    key: str = Field(max_length=40)
    label: str = Field(max_length=80)
    href: str = Field(max_length=400)
    style: str = Field("primary", pattern="^(primary|secondary|link)$")


@router.get("/sites/{site_id}/ctas")
async def ctas(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CmsCta).where(CmsCta.site_id == site_id).order_by(CmsCta.key))).scalars()
    return [{"id": str(c.id), "key": c.key, "label": c.label, "href": c.href, "style": c.style, "views": c.views, "clicks": c.clicks,
             "ctr": round(c.clicks / c.views, 4) if c.views else None} for c in rows]


@router.post("/sites/{site_id}/ctas", status_code=201)
async def save_cta(site_id: uuid.UUID, b: CtaIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)                  # CTAs are resolved on live pages at request time
    try:
        href = cms.href(b.href)
    except cms.CmsError as e:
        _fail(e)
    key = cms.slugify(b.key)[:40]
    c = (await db.execute(select(CmsCta).where(CmsCta.site_id == site_id, CmsCta.key == key))).scalar_one_or_none()
    if c is None:
        c = CmsCta(site_id=site_id, key=key, views=0, clicks=0)
        db.add(c)
    c.label, c.href, c.style = b.label.strip(), href, b.style
    cms.audit(db, user, "cms.cta.saved", "cms_site", site_id, {"key": key})
    await db.commit()
    return {"id": str(c.id), "key": key}


class TableIn(BaseModel):
    key: Optional[str] = Field(None, max_length=40)
    name: Optional[str] = Field(None, max_length=150)
    columns: Optional[list[dict]] = None
    published: Optional[bool] = None


def _columns(cols: list[dict]) -> list[dict]:
    out = []
    for c in cols[:20]:
        k = re.sub(r"[^a-z0-9_]", "_", str(c.get("key") or "").lower())[:40]
        if k and c.get("type", "text") in ("text", "number", "url", "image"):
            out.append({"key": k, "label": str(c.get("label") or k)[:60], "type": c.get("type", "text")})
    if not out:
        raise HTTPException(422, "A table needs at least one column (text, number, url or image)")
    return out


@router.get("/sites/{site_id}/tables")
async def tables(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CmsTable).where(CmsTable.site_id == site_id).order_by(CmsTable.name))).scalars().all()
    counts = dict((await db.execute(select(CmsTableRow.table_id, func.count()).where(CmsTableRow.table_id.in_([t.id for t in rows] or [None]))
                                    .group_by(CmsTableRow.table_id))).all())
    return [{"id": str(t.id), "key": t.key, "name": t.name, "columns": t.columns, "published": t.published, "rows": counts.get(t.id, 0)} for t in rows]


@router.post("/sites/{site_id}/tables", status_code=201)
async def create_table(site_id: uuid.UUID, b: TableIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    await _get(db, CmsSite, site_id)
    t = CmsTable(site_id=site_id, key=cms.slugify(b.key or b.name or "table").replace("-", "_")[:40], name=(b.name or b.key or "Table")[:150],
                 columns=_columns(b.columns or []), published=False)
    db.add(t)
    cms.audit(db, user, "cms.table.created", "cms_site", site_id, {"key": t.key})
    await db.commit()
    return {"id": str(t.id), "key": t.key}


@router.patch("/tables/{table_id}")
async def update_table(table_id: uuid.UUID, b: TableIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    t = await _get(db, CmsTable, table_id)
    _need(user, APPROVE if b.published is not None else EDIT)       # publishing a table makes its rows public
    if b.name:
        t.name = b.name[:150]
    if b.columns is not None:
        t.columns = _columns(b.columns)
    if b.published is not None:
        t.published = b.published
    cms.audit(db, user, "cms.table.updated", "cms_table", t.id, b.model_dump(exclude_none=True, exclude={"columns"}))
    await db.commit()
    return {"ok": True}


@router.get("/tables/{table_id}/rows")
async def rows(table_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rs = (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == table_id).order_by(CmsTableRow.position, CmsTableRow.slug))).scalars()
    return [{"id": str(r.id), "slug": r.slug, "values": r.values, "position": r.position} for r in rs]


class RowsIn(BaseModel):
    rows: list[dict] = Field(max_length=2000)


@router.put("/tables/{table_id}/rows")
async def put_rows(table_id: uuid.UUID, b: RowsIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Upsert rows by slug; values are kept only for declared columns, URLs/images checked like page links."""
    t = await _get(db, CmsTable, table_id)
    _need(user, APPROVE if t.published else EDIT)       # rows of a published table are live
    cols = {c["key"]: c["type"] for c in t.columns}
    n, seen = 0, set()
    for i, r in enumerate(b.rows):
        vals = {}
        for k, typ in cols.items():
            v = r.get(k)
            if v in (None, ""):
                continue
            try:
                vals[k] = float(v) if typ == "number" else cms.https(v) if typ == "image" else cms.href(v) if typ == "url" else str(v)[:2000]
            except (ValueError, cms.CmsError) as e:
                raise HTTPException(422, f"Row {i + 1}, {k}: {e}")
        slug = cms.slugify(str(r.get("slug") or next(iter(vals.values()), "")))
        if slug in seen:
            raise HTTPException(422, f"Row {i + 1}: slug {slug} appears twice")
        seen.add(slug)
        try:
            pos = int(r.get("position") or i)
        except (TypeError, ValueError):
            raise HTTPException(422, f"Row {i + 1}: position must be a number")
        row = (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == t.id, CmsTableRow.slug == slug))).scalar_one_or_none()
        if row is None:
            db.add(CmsTableRow(table_id=t.id, slug=slug, values=vals, position=pos))
        else:
            row.values, row.position = vals, pos
        n += 1
    cms.audit(db, user, "cms.table.rows", "cms_table", t.id, {"rows": n})
    await db.commit()
    return {"saved": n}


@router.delete("/rows/{row_id}")
async def delete_row(row_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    row = await _get(db, CmsTableRow, row_id)
    _need(user, APPROVE if (await db.get(CmsTable, row.table_id)).published else EDIT)
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.get("/sites/{site_id}/keywords")
async def keywords(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CmsKeyword).where(CmsKeyword.site_id == site_id).order_by(CmsKeyword.locale, CmsKeyword.keyword))).scalars()
    return [{"id": str(k.id), "keyword": k.keyword, "locale": k.locale, "volume": k.volume, "difficulty": k.difficulty, "source": k.source,
             "target_page": str(k.target_page) if k.target_page else None} for k in rows]


class KeywordImport(BaseModel):
    csv: str = Field(max_length=200_000)
    source: str = Field("import", max_length=60)


@router.post("/sites/{site_id}/keywords/import")
async def import_keywords(site_id: uuid.UUID, b: KeywordImport, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """CSV with keyword[,volume,difficulty,locale]. Volumes/difficulty are stored only as given — blank stays unknown."""
    _need(user, EDIT)
    n, seen = 0, set()
    for row in csv.reader(io.StringIO(b.csv)):
        if not row or not row[0].strip() or row[0].strip().lower() == "keyword":
            continue
        kw = row[0].strip()[:120]

        def num(i):
            try:
                return int(float(row[i])) if len(row) > i and row[i].strip() else None
            except ValueError:
                return None
        loc = row[3].strip() if len(row) > 3 and row[3].strip() in cms.LOCALES else "en"
        if (loc, kw) in seen:
            continue
        seen.add((loc, kw))
        k = (await db.execute(select(CmsKeyword).where(CmsKeyword.site_id == site_id, CmsKeyword.locale == loc, CmsKeyword.keyword == kw))).scalar_one_or_none()
        if k is None:
            k = CmsKeyword(site_id=site_id, locale=loc, keyword=kw)
            db.add(k)
        k.volume, k.difficulty, k.source = num(1), num(2), b.source[:60]
        n += 1
    await db.commit()
    return {"imported": n}


@router.get("/sites/{site_id}/search-console")
async def search_console(site_id: uuid.UUID):
    return {"status": "NOT_CONFIGURED", "detail": "Google Search Console is connected at activation (needs the verified domain, M47)."}


# ── experiments ───────────────────────────────────────────────────────────────

@router.get("/pages/{page_id}/experiments")
async def experiments(page_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return [{"id": str(e.id), **pz.stats(e)} for e in (await db.execute(select(CmsExperiment).where(CmsExperiment.page_id == page_id))).scalars()]


class ExperimentIn(BaseModel):
    mode: Optional[str] = Field(None, pattern="^(AB|BANDIT)$")
    status: Optional[str] = Field(None, pattern="^(RUNNING|STOPPED)$")
    winner: Optional[str] = Field(None, max_length=20)


@router.patch("/experiments/{exp_id}")
async def update_experiment(exp_id: uuid.UUID, b: ExperimentIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    e = await _get(db, CmsExperiment, exp_id)
    if b.mode:
        e.mode = b.mode
    if b.status:
        e.status = b.status
    if b.winner is not None:
        if b.winner and b.winner not in e.variants:
            raise HTTPException(422, "Unknown variant")
        e.counts = {**(e.counts or {}), "winner": b.winner or None}
    cms.audit(db, user, "cms.experiment.updated", "cms_experiment", e.id, b.model_dump(exclude_none=True))
    await db.commit()
    return {"id": str(e.id), **pz.stats(e)}


# ── memberships and media ─────────────────────────────────────────────────────

class AccessListIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    account_ids: Optional[list[str]] = None
    account_types: Optional[list[str]] = None
    revoked_ids: Optional[list[str]] = None


def _acl_out(a: CmsAccessList) -> dict:
    return {"id": str(a.id), "name": a.name, "account_ids": a.account_ids or [], "account_types": a.account_types or [], "revoked_ids": a.revoked_ids or []}


@router.get("/access-lists")
async def access_lists(db: AsyncSession = Depends(get_db)):
    return [_acl_out(a) for a in (await db.execute(select(CmsAccessList).order_by(CmsAccessList.name))).scalars()]


async def _clean_acl(db, b: AccessListIn, a: CmsAccessList) -> None:
    from app.models.portal import PortalAccount, PortalAccountType
    if b.name:
        a.name = b.name.strip()[:150]
    for field in ("account_ids", "revoked_ids"):
        ids = getattr(b, field)
        if ids is not None:
            uu = []
            for x in ids[:5000]:
                try:
                    uu.append(uuid.UUID(str(x)))
                except ValueError:
                    raise HTTPException(422, f"Bad portal account id {x!r}")
            found = set((await db.execute(select(PortalAccount.id).where(PortalAccount.id.in_(uu or [None])))).scalars())
            if len(found) != len(set(uu)):
                raise HTTPException(422, "Some portal accounts do not exist")
            setattr(a, field, [str(x) for x in dict.fromkeys(uu)])
    if b.account_types is not None:
        valid = {t.value for t in PortalAccountType}
        a.account_types = [t for t in b.account_types if t in valid]


@router.post("/access-lists", status_code=201)
async def create_acl(b: AccessListIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    a = CmsAccessList(name=(b.name or "").strip()[:150] or "Members", account_ids=[], account_types=[], revoked_ids=[])
    await _clean_acl(db, b, a)
    db.add(a)
    await db.flush()
    cms.audit(db, user, "cms.access_list.created", "cms_access_list", a.id, _acl_out(a))
    await db.commit()
    return _acl_out(a)


@router.patch("/access-lists/{acl_id}")
async def update_acl(acl_id: uuid.UUID, b: AccessListIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    a = await _get(db, CmsAccessList, acl_id)
    before = _acl_out(a)
    await _clean_acl(db, b, a)
    cms.audit(db, user, "cms.access_list.updated", "cms_access_list", a.id, {"before": before, "after": _acl_out(a)})
    await db.commit()
    return _acl_out(a)


@router.get("/portal-accounts")
async def portal_accounts(db: AsyncSession = Depends(get_db)):
    from app.models.portal import PortalAccount
    rows = (await db.execute(select(PortalAccount).order_by(PortalAccount.account_code).limit(500))).scalars()
    return [{"id": str(a.id), "code": a.account_code, "name": a.primary_contact_name, "type": getattr(a.account_type, "value", a.account_type),
             "status": getattr(a.portal_status, "value", a.portal_status)} for a in rows]


def _media_out(m: CmsMedia, views: int = 0) -> dict:
    return {"id": str(m.id), "kind": m.kind, "title": m.title, "mime": m.mime, "size": m.size, "sha256": m.sha256,
            "captions": sorted((m.captions or {}).keys()), "podcast": m.podcast, "public": m.public,
            "access_list_id": str(m.access_list_id) if m.access_list_id else None, "duration_s": m.duration_s,
            "page_id": str(m.page_id) if m.page_id else None, "poster": bool(m.poster_path),
            "poster_url": f"/api/v1/public/cms/media/{m.id}/poster" if m.poster_path else None,
            "created_at": m.created_at.isoformat() if m.created_at else None, "views": views}


@router.get("/media")
async def media_list(db: AsyncSession = Depends(get_db)):
    counts = dict((await db.execute(select(CmsMediaView.media_id, func.count()).group_by(CmsMediaView.media_id))).all())
    return [_media_out(m, counts.get(m.id, 0)) for m in (await db.execute(select(CmsMedia).order_by(CmsMedia.created_at.desc()))).scalars()]


@router.post("/media", status_code=201)
async def upload_media(request: Request, file: UploadFile = File(...), title: str = Form(..., max_length=200), podcast: Optional[str] = Form(None),
                       access_list_id: Optional[str] = Form(None), public: bool = Form(False),
                       db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE if (public or access_list_id) else EDIT)    # making media public or gated is an approver decision
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > settings.MEDIA_MAX_UPLOAD_BYTES + 65536:            # refuse before reading an oversized body
        raise HTTPException(413, f"Media over {settings.MEDIA_MAX_UPLOAD_BYTES // 1048576} MiB")
    try:
        acl = uuid.UUID(access_list_id) if access_list_id else None
    except ValueError:
        raise HTTPException(422, "Bad access list id")
    if acl:
        await _get(db, CmsAccessList, acl)
    key, mime, size, sha = await media.store(file)
    m = CmsMedia(kind=media.KINDS[mime], title=title.strip()[:200], mime=mime, size=size, sha256=sha, storage_path=key, captions={},
                 podcast=(podcast or "").strip()[:120] or None, access_list_id=acl, public=public, created_by=user.username)
    db.add(m)
    await db.flush()
    cms.audit(db, user, "cms.media.uploaded", "cms_media", m.id, {"title": m.title, "mime": mime, "size": size})
    await db.commit()
    await db.refresh(m)
    return _media_out(m)


class MediaIn(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    access_list_id: Optional[uuid.UUID] = None
    public: Optional[bool] = None
    podcast: Optional[str] = Field(None, max_length=120)
    duration_s: Optional[int] = Field(None, ge=0, le=86400)


@router.patch("/media/{media_id}")
async def update_media(media_id: uuid.UUID, b: MediaIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    m = await _get(db, CmsMedia, media_id)
    _need(user, APPROVE if (b.public is not None or "access_list_id" in b.model_fields_set) else EDIT)
    if b.title:
        m.title = b.title.strip()
    if "access_list_id" in b.model_fields_set:
        if b.access_list_id:
            await _get(db, CmsAccessList, b.access_list_id)
        m.access_list_id = b.access_list_id
    if b.public is not None:
        m.public = b.public
    if b.podcast is not None:
        m.podcast = b.podcast.strip() or None
    if b.duration_s is not None:
        m.duration_s = b.duration_s
    cms.audit(db, user, "cms.media.updated", "cms_media", m.id, b.model_dump(exclude_none=True, mode="json"))
    await db.commit()
    await db.refresh(m)
    return _media_out(m)


class CaptionIn(BaseModel):
    vtt: str = Field(max_length=200_000)


@router.put("/media/{media_id}/captions/{locale}")
async def put_captions(media_id: uuid.UUID, locale: str, b: CaptionIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if locale not in cms.LOCALES:
        raise HTTPException(422, f"Locale must be one of {cms.LOCALES}")
    m = await _get(db, CmsMedia, media_id)
    _need(user, APPROVE if (m.public or m.access_list_id) else EDIT)   # captions of served media are live
    m.captions = {**(m.captions or {}), locale: media.clean_vtt(b.vtt)}
    cms.audit(db, user, "cms.media.captions", "cms_media", m.id, {"locale": locale})
    await db.commit()
    return {"ok": True, "captions": sorted(m.captions)}


@router.get("/media/{media_id}/file")
async def media_file(media_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    m = await _get(db, CmsMedia, media_id)
    return FileResponse(media.file_path(m), media_type=m.mime, headers={"X-Content-Type-Options": "nosniff"})


class PosterIn(BaseModel):
    t: float = Field(0, ge=0, le=86400)


@router.post("/media/{media_id}/poster")
async def make_poster(media_id: uuid.UUID, b: PosterIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Poster frame at t seconds (PNG, ffmpeg). It is served with the same access as the video. 409 without ffmpeg."""
    m = await _get(db, CmsMedia, media_id)
    _need(user, APPROVE if (m.public or m.access_list_id) else EDIT)    # the poster of served media is live
    if m.kind != "VIDEO":
        raise HTTPException(422, "Posters are for videos")
    if not media.ffmpeg():
        raise media.not_available()
    png = await media.poster_frame(m, b.t)
    key, _, _ = media.store_bytes(png, "image/png")
    old, m.poster_path = m.poster_path, key
    cms.audit(db, user, "cms.media.poster", "cms_media", m.id, {"t": b.t})
    await db.commit()
    if old:
        (media.root() / old).unlink(missing_ok=True)
    await db.refresh(m)
    return _media_out(m)


@router.get("/media/{media_id}/poster")
async def poster(media_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    m = await _get(db, CmsMedia, media_id)
    return FileResponse(media.poster_file(m), media_type="image/png", headers={"X-Content-Type-Options": "nosniff"})


class TrimIn(BaseModel):
    start: float = Field(ge=0, le=86400)
    end: float = Field(gt=0, le=86400)
    title: Optional[str] = Field(None, max_length=200)


@router.post("/media/{media_id}/trim", status_code=201)
async def trim_media(media_id: uuid.UUID, b: TrimIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """A NEW staff-only media item holding [start, end) of the original (stream copy); the original is untouched."""
    _need(user, EDIT)
    if b.end <= b.start:
        raise HTTPException(422, "end must be after start")
    m = await _get(db, CmsMedia, media_id)
    if not media.ffmpeg():
        raise media.not_available()
    data = await media.trim(m, b.start, b.end)
    key, size, sha = media.store_bytes(data, m.mime)
    n = CmsMedia(kind=m.kind, title=(b.title or f"{m.title} ({b.start:g}–{b.end:g} s)")[:200], mime=m.mime, size=size, sha256=sha, storage_path=key,
                 captions={}, podcast=None, public=False, access_list_id=None, duration_s=int(b.end - b.start), created_by=user.username)
    db.add(n)
    await db.flush()
    cms.audit(db, user, "cms.media.trimmed", "cms_media", n.id, {"source": str(m.id), "start": b.start, "end": b.end})
    await db.commit()
    await db.refresh(n)
    return _media_out(n)


@router.get("/media/{media_id}/views")
async def media_views(media_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.models.portal import PortalAccount
    rows = (await db.execute(select(CmsMediaView, PortalAccount.account_code).outerjoin(PortalAccount, PortalAccount.id == CmsMediaView.portal_account_id)
                             .where(CmsMediaView.media_id == media_id).order_by(CmsMediaView.created_at.desc()).limit(500))).all()
    return [{"at": v.created_at.isoformat(), "account": code, "seconds": v.seconds, "member": v.portal_user_id is not None} for v, code in rows]
