"""M51.S01.T001/T002 CMS layout editor and shared library — staff API. Prefix /api/v1/cms-layout.

Permissions mirror the M46 CMS: marketing.view reads and previews; marketing.create/edit authors library items;
marketing.approve reviews (a different person than the submitter), publishes, rolls back and assigns the site layout.
Every state change is audited (module "content"). Nothing here stores or renders raw HTML, CSS or script.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import cms as cms_ep
from app.core.access_control import require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.cms import CmsPage, CmsPageVersion, CmsSite
from app.models.m51_cms_layout import CmsComponent, CmsComponentVersion, CmsSiteLayout
from app.services import cms_layout_service as L
from app.services import cms_service as cms

router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view",)))])
EDIT = ("marketing.create", "marketing.edit")
APPROVE = ("marketing.approve",)
_need, _fail, _get = cms_ep._need, cms_ep._fail, cms_ep._get


def _out(c: CmsComponent, with_draft: bool = False) -> dict:
    o = {"id": str(c.id), "site_id": str(c.site_id), "key": c.key, "kind": c.kind, "name": c.name, "status": c.status,
         "live_version_id": str(c.live_version_id) if c.live_version_id else None, "submitted_by": c.submitted_by,
         "approved_by": c.approved_by, "updated_by": c.updated_by, "updated_at": c.updated_at.isoformat() if c.updated_at else None}
    if with_draft:
        o["draft"] = c.draft
    return o


async def _check_assets(db: AsyncSession, content: dict) -> None:
    """A theme's logo must be an approved Brand Vault asset (M48 brand context), not an arbitrary reference."""
    ref = (content.get("tokens") or {}).get("logo_asset_ref")
    if ref:
        from app.services import brand_context_service as bcs
        if ref not in {a["asset_ref"] for a in (await bcs.context(db))["assets"]}:
            raise cms.CmsError("The logo must be an approved brand asset")


async def _validated(db: AsyncSession, kind: str, draft: dict) -> tuple[dict, list[str]]:
    content, warn = L.validate_component(kind, draft)
    await _check_assets(db, content)
    return content, warn


@router.get("/meta")
async def meta():
    """Allow-lists the editor's controls are built from (the server enforces the same lists on save)."""
    return L.meta()


@router.get("/sites/{site_id}/components")
async def components(site_id: uuid.UUID, kind: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(CmsComponent).where(CmsComponent.site_id == site_id)
    if kind:
        q = q.where(CmsComponent.kind == kind)
    return [_out(c) for c in (await db.execute(q.order_by(CmsComponent.kind, CmsComponent.name))).scalars()]


class ComponentIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    key: Optional[str] = Field(None, max_length=40)
    kind: Optional[str] = None
    preset: Optional[str] = Field(None, max_length=40)
    draft: Optional[dict] = None


@router.post("/sites/{site_id}/components", status_code=201)
async def create_component(site_id: uuid.UUID, b: ComponentIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    await _get(db, CmsSite, site_id)
    preset = L.PRESETS.get(b.preset) if b.preset else None
    if b.preset and preset is None:
        raise HTTPException(422, "Unknown preset")
    kind = b.kind or (preset or {}).get("kind")
    if not kind or (preset and kind != preset["kind"]):
        raise HTTPException(422, "A kind is required and must match the preset")
    name = (b.name or (preset or {}).get("name") or "").strip()
    if not name:
        raise HTTPException(422, "A name is required")
    key = cms.slugify(b.key or name)[:40]
    if (await db.execute(select(CmsComponent.id).where(CmsComponent.site_id == site_id, CmsComponent.key == key))).first():
        raise HTTPException(409, "A library item with this key exists")
    try:
        content, warn = await _validated(db, kind, b.draft if b.draft is not None else (preset or {}).get("draft") or {"blocks": []})
    except cms.CmsError as e:
        _fail(e)
    c = CmsComponent(site_id=site_id, key=key, kind=kind, name=name[:150], draft=content, status="DRAFT", created_by=user.username, updated_by=user.username)
    db.add(c)
    await db.flush()
    cms.audit(db, user, "cms.component.created", "cms_component", c.id, {"key": key, "kind": kind, "preset": b.preset})
    await db.commit()
    await db.refresh(c)
    return {**_out(c, True), "warnings": warn}


@router.get("/components/{cid}")
async def component(cid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await _get(db, CmsComponent, cid)
    vs = (await db.execute(select(CmsComponentVersion).where(CmsComponentVersion.component_id == c.id).order_by(CmsComponentVersion.version.desc()))).scalars().all()
    return {**_out(c, True), "versions": [{"version": v.version, "name": v.name, "note": v.note, "approved_by": v.approved_by, "published_by": v.published_by,
                                           "published_at": v.published_at.isoformat(), "live": v.id == c.live_version_id} for v in vs]}


@router.patch("/components/{cid}")
async def update_component(cid: uuid.UUID, b: ComponentIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    c = await _get(db, CmsComponent, cid)
    await db.refresh(c, with_for_update=True)
    warn: list[str] = []
    try:
        if b.draft is not None:
            c.draft, warn = await _validated(db, c.kind, b.draft)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    if b.name:
        c.name = b.name.strip()[:150]
    if c.status in ("IN_REVIEW", "APPROVED"):          # anything reviewed changed: review again
        c.status, c.approved_by = "DRAFT", None
    c.updated_by = user.username
    cms.audit(db, user, "cms.component.edited", "cms_component", c.id, {"fields": sorted(b.model_fields_set)})
    await db.commit()
    await db.refresh(c)
    return {**_out(c, True), "warnings": warn}


class Decision(BaseModel):
    ok: bool = True
    note: str = Field("", max_length=200)
    version: Optional[int] = None


async def _act(db: AsyncSession, cid: uuid.UUID, user, perms, fn):
    _need(user, perms)
    c = await _get(db, CmsComponent, cid)
    await db.refresh(c, with_for_update=True)
    try:
        v = await fn(c)
    except cms.CmsError as e:
        await db.rollback()
        _fail(e)
    await db.commit()
    await db.refresh(c)
    return {**_out(c), **({"version": v.version} if v else {})}


async def _publish(db: AsyncSession, c: CmsComponent, user, note: str, content: Optional[dict] = None, name: Optional[str] = None) -> CmsComponentVersion:
    if content is None:
        if c.status != "APPROVED":
            raise cms.CmsError("A library item must be approved by a second person before publishing")
        content, _ = L.validate_component(c.kind, c.draft or {})
    n = (await db.execute(select(func.coalesce(func.max(CmsComponentVersion.version), 0)).where(CmsComponentVersion.component_id == c.id))).scalar_one()
    v = CmsComponentVersion(component_id=c.id, version=n + 1, name=name or c.name, content=content, note=note[:200] or None,
                            approved_by=c.approved_by or user.username, published_by=user.username)
    db.add(v)
    await db.flush()
    c.live_version_id, c.status = v.id, "PUBLISHED"
    cms.audit(db, user, "cms.component.published", "cms_component", c.id, {"version": v.version, "key": c.key})
    return v


@router.post("/components/{cid}/submit")
async def submit(cid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    async def go(c):
        if c.status not in ("DRAFT", "PUBLISHED", "APPROVED"):
            raise cms.CmsError(f"Cannot submit an item in {c.status}")
        c.status, c.submitted_by, c.approved_by = "IN_REVIEW", user.username, None
        cms.audit(db, user, "cms.component.submitted", "cms_component", c.id, {"key": c.key})
    return await _act(db, cid, user, EDIT, go)


@router.post("/components/{cid}/approve")
async def approve(cid: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    async def go(c):
        if c.status != "IN_REVIEW":
            raise cms.CmsError("Only an item in review can be approved or rejected")
        if c.submitted_by == user.username:
            raise cms.CmsError("A different person must review this item")
        c.status, c.approved_by = ("APPROVED", user.username) if b.ok else ("DRAFT", None)
        cms.audit(db, user, "cms.component.approved" if b.ok else "cms.component.rejected", "cms_component", c.id, {"note": b.note})
    return await _act(db, cid, user, APPROVE, go)


@router.post("/components/{cid}/publish")
async def publish(cid: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await _act(db, cid, user, APPROVE, lambda c: _publish(db, c, user, b.note))


@router.post("/components/{cid}/rollback")
async def rollback(cid: uuid.UUID, b: Decision, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not b.version:
        raise HTTPException(422, "version is required")

    async def go(c):
        old = (await db.execute(select(CmsComponentVersion).where(CmsComponentVersion.component_id == c.id, CmsComponentVersion.version == b.version))).scalar_one_or_none()
        if old is None:
            raise cms.CmsError("Version not found")
        c.draft = old.content
        return await _publish(db, c, user, f"Rollback to v{b.version}", content=old.content, name=old.name)
    return await _act(db, cid, user, APPROVE, go)


@router.get("/components/{cid}/usage")
async def usage(cid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Pages (draft or live) that reference a section/component by key, and the site slots that use a header/footer/nav/theme."""
    c = await _get(db, CmsComponent, cid)
    out = []
    for p in (await db.execute(select(CmsPage).where(CmsPage.site_id == c.site_id).limit(2000))).scalars():
        sources = [("draft", p.draft or {})]
        if p.live_version_id:
            v = await db.get(CmsPageVersion, p.live_version_id)
            sources.append(("live", v.content if v else {}))
        for where, doc in sources:
            if any(b.get("type") == "component" and b.get("key") == c.key for b in cms.flat(doc.get("blocks") or [])) or \
                    c.key in (doc.get("layout") or {}).values():
                out.append({"page_id": str(p.id), "title": p.title, "path": p.path, "locale": p.locale, "where": where})
    lay = await L.site_layout(db, c.site_id)
    slots = [s for s in ("header", "footer", "nav", "theme") if lay and getattr(lay, f"{s}_key") == c.key]
    return {"pages": out, "site_slots": slots}


class LayoutIn(BaseModel):
    header_key: Optional[str] = Field(None, max_length=40)
    footer_key: Optional[str] = Field(None, max_length=40)
    nav_key: Optional[str] = Field(None, max_length=40)
    theme_key: Optional[str] = Field(None, max_length=40)


def _layout_out(lay: Optional[CmsSiteLayout]) -> dict:
    return {s + "_key": getattr(lay, s + "_key", None) if lay else None for s in ("header", "footer", "nav", "theme")}


@router.get("/sites/{site_id}/layout")
async def get_layout(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get(db, CmsSite, site_id)
    return _layout_out(await L.site_layout(db, site_id))


@router.put("/sites/{site_id}/layout")
async def put_layout(site_id: uuid.UUID, b: LayoutIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)                                  # what frames every page is a publishing decision
    await _get(db, CmsSite, site_id)
    kinds = {"header": "HEADER", "footer": "FOOTER", "nav": "NAV", "theme": "THEME"}
    for slot, kind in kinds.items():
        key = getattr(b, f"{slot}_key")
        if key and not await L.live_component(db, site_id, key, (kind,)):
            raise HTTPException(422, f"{slot}: '{key}' is not a published {kind.lower()} of this site")
    lay = await L.site_layout(db, site_id)
    if lay is None:
        lay = CmsSiteLayout(site_id=site_id)
        db.add(lay)
    for slot in kinds:
        setattr(lay, f"{slot}_key", getattr(b, f"{slot}_key") or None)
    lay.updated_by = user.username
    cms.audit(db, user, "cms.site_layout.updated", "cms_site", site_id, b.model_dump())
    await db.commit()
    return _layout_out(lay)


@router.get("/sites/{site_id}/brand")
async def brand(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Approved brand context (M48) the site tokens are checked against, the effective tokens, and the read-only e-mail theme."""
    from app.services import brand_context_service as bcs
    from app.services.email_design_service import DEFAULT_THEME
    s = await _get(db, CmsSite, site_id)
    ctx = await bcs.context(db)
    tokens = await L.effective_tokens(db, s)
    return {"brand": ctx["brand"], "brand_source": ctx["brand_source"], "assets": ctx["assets"], "tokens": tokens,
            "email_theme": L.email_theme(tokens), "email_default_theme": DEFAULT_THEME}


class PreviewIn(BaseModel):
    site_id: uuid.UUID
    doc: dict
    locale: Optional[str] = Field(None, max_length=5)
    kind: Optional[str] = None                      # a library item being edited instead of a page


@router.post("/preview")
async def preview(b: PreviewIn, db: AsyncSession = Depends(get_db)):
    """Canvas preview of an unsaved document: validated, components resolved, css generated; changes nothing."""
    s = await _get(db, CmsSite, b.site_id)
    loc = b.locale if b.locale in cms.LOCALES else s.default_locale
    try:
        if b.kind and b.kind not in ("PAGE", "PAGE_TEMPLATE"):
            content, warn = await _validated(db, b.kind, b.doc)
            tokens = L.validate_tokens(content["tokens"])[0] if b.kind == "THEME" else await L.effective_tokens(db, s)
            blocks, page_layout = ([] if b.kind == "THEME" else L.blocks_for(content, loc)), {}
        else:
            doc, warn = cms.validate_doc(b.doc)
            tokens, blocks, page_layout = await L.effective_tokens(db, s), doc["blocks"], doc.get("layout")
        out = L.attach_css(await cms.expand(db, s, blocks, locale=loc), tokens)
        lay = await L.public_layout(db, s, page_layout, loc, tokens) if not b.kind or b.kind in ("PAGE", "PAGE_TEMPLATE") else {"tokens": tokens}
    except cms.CmsError as e:
        _fail(e)
    return {"blocks": out, "layout": lay, "theme": await L.theme_for(db, s, tokens), "warnings": warn}


class FromTemplate(BaseModel):
    site_id: uuid.UUID
    template_key: str = Field(max_length=40)
    title: str = Field(max_length=200)
    locale: Optional[str] = Field(None, max_length=5)


@router.post("/pages/from-template", status_code=201)
async def page_from_template(b: FromTemplate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    hit = await L.live_component(db, b.site_id, b.template_key, ("PAGE_TEMPLATE",))
    if hit is None:
        raise HTTPException(404, "No published template with this key")
    doc = {k: v for k, v in hit[1].content.items() if k in ("blocks", "seo", "layout")}
    return await cms_ep.create_page(cms_ep.PageIn(site_id=b.site_id, title=b.title, locale=b.locale, draft=doc), db, user)
