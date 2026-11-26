"""M46 CMS: sites, page tree, block documents, staging → approval → publish, versions and rollback, redirects,
dynamic tables, CTAs, blog, SEO/AEO audits, sitemap/robots, multilingual pages (M46.S01.T001/T002/T005).

Safety model:
- Pages are block documents validated here; no block carries raw HTML. Text allows **bold** and [label](url) links
  only; every URL must be http(s) or a site path. The public page renders blocks as React elements (escaped).
- The public endpoint serves only the live version snapshot of a PUBLISHED page; drafts, reviews and archived
  pages answer 404. Members-only pages need a portal sign-in on the page's access list (cms_media_service).
- A published page's draft can change freely without affecting the live site until the next publish.
- Publishing needs marketing.approve; with site.require_approval a page must be APPROVED by a different person.
- Search Console and answer-engine measurements need an external account: they report NOT_CONFIGURED /
  NOT_AVAILABLE, never a made-up number.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from html import escape
from typing import Any, Optional
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cms import CmsCta, CmsPage, CmsPageVersion, CmsRedirect, CmsSite, CmsTable, CmsTableRow

LOCALES = ("en", "sw", "tr")
BLOCK_TYPES = ("heading", "text", "image", "button", "cta", "columns", "divider", "spacer", "form", "embed", "faq",
               "table", "video", "audio", "product", "hero")
THEME_KEYS = {"brand_color": "#1D4ED8", "text_color": "#111827", "background": "#FFFFFF", "accent": "#F59E0B",
              "font": "Inter, Arial, sans-serif", "radius": "8"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK = re.compile(r"\[([^\]]{1,120})\]\(([^)\s]{1,400})\)")
TOKEN = re.compile(r"\{\{row\.([a-z0-9_]{1,40})\}\}")
MAX_BLOCKS = 120


class CmsError(ValueError):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:120] or "page"


def href(u: Any) -> str:
    """A link: a site path (/x/y) or a full http(s) URL. Anything else (javascript:, data:, //host) is refused."""
    u = str(u or "").strip()
    if u.startswith("/") and not u.startswith("//"):
        if not re.fullmatch(r"/[\w\-./~%#?=&]*", u):
            raise CmsError(f"Bad site path: {u[:80]!r}")
        return u
    p = urlsplit(u)
    if p.scheme not in ("http", "https") or not p.netloc or any(c in u for c in '"<>\\ \n\r\''):
        raise CmsError(f"Link must be a site path or an http(s) address: {u[:80]!r}")
    return u


def https(u: Any) -> str:
    u = href(u)
    if not (u.startswith("https://") or u.startswith("/")):
        raise CmsError("Images and media must be https or served by this site")
    return u


def _text(v: Any, n: int) -> str:
    s = str(v or "")[:n]
    for m in LINK.finditer(s):
        href(m.group(2))                      # every inline link must be safe too
    return s


def _audience(a: dict) -> dict:
    out = {}
    for k in ("lifecycle", "segment", "locale"):
        if a.get(k):
            out[k] = [str(x)[:40] for x in a[k]][:10]
    if a.get("known") in (True, False):
        out["known"] = a["known"]
    return out


def validate_block(b: dict, warnings: list[str], depth: int = 0) -> dict:
    t = b.get("type")
    if t not in BLOCK_TYPES or (depth and t in ("columns", "hero")):
        raise CmsError(f"Unknown or misplaced block: {t!r}")
    o: dict = {"type": t, "id": re.sub(r"[^\w-]", "", str(b.get("id") or uuid.uuid4().hex[:8]))[:20]}
    if b.get("audience"):
        o["audience"] = _audience(b["audience"])
    if b.get("fallback"):
        o["fallback"] = True                    # shown only when no personalized sibling with the same slot shows
    if b.get("slot"):
        o["slot"] = re.sub(r"[^\w-]", "", str(b["slot"]))[:30]
    if b.get("experiment"):
        e = b["experiment"]
        o["experiment"] = {"key": re.sub(r"[^\w-]", "", str(e.get("key")))[:40], "variant": re.sub(r"[^\w-]", "", str(e.get("variant")))[:20]}
    if t in ("heading", "text"):
        o["text"] = _text(b.get("text"), 8000)
        if t == "heading":
            o["level"] = min(3, max(1, int(b.get("level") or 2)))
    elif t == "hero":
        o["title"] = _text(b.get("title"), 200)
        o["subtitle"] = _text(b.get("subtitle"), 400)
        if b.get("image"):
            o["image"] = https(b["image"])
        if b.get("cta_key"):
            o["cta_key"] = str(b["cta_key"])[:40]
    elif t == "image":
        o["url"] = https(b.get("url"))
        o["alt"] = str(b.get("alt") or "").strip()[:200]
        if not o["alt"]:
            warnings.append("An image has no alternative text.")
    elif t == "button":
        o["label"] = str(b.get("label") or "Open")[:80]
        o["href"] = href(b.get("href"))
    elif t == "cta":
        o["cta_key"] = str(b.get("cta_key") or "")[:40]
    elif t == "spacer":
        o["height"] = max(4, min(120, int(b.get("height") or 24)))
    elif t == "form":
        o["form_slug"] = slugify(b.get("form_slug"))
    elif t == "embed":                         # content embed: the live blocks of another page (reusable section)
        o["page_id"] = str(uuid.UUID(str(b.get("page_id"))))
    elif t == "faq":
        items = [{"q": str(x.get("q") or "")[:300], "a": _text(x.get("a"), 2000)} for x in (b.get("items") or [])[:30]]
        o["items"] = [x for x in items if x["q"] and x["a"]]
    elif t == "table":
        o["table_key"] = str(b.get("table_key") or "")[:40]
        o["columns"] = [str(c)[:40] for c in (b.get("columns") or [])][:8]
        o["link_prefix"] = href(b["link_prefix"]) if b.get("link_prefix") else None
    elif t in ("video", "audio"):
        o["media_id"] = str(uuid.UUID(str(b.get("media_id"))))
        o["title"] = str(b.get("title") or "")[:200]
    elif t == "product":
        o.update({k: str(b.get(k) or "")[:120] for k in ("name", "size", "price")})
        if b.get("image"):
            o["image"] = https(b["image"])
    elif t == "columns":
        o["left"] = [validate_block(x, warnings, depth + 1) for x in (b.get("left") or [])[:20]]
        o["right"] = [validate_block(x, warnings, depth + 1) for x in (b.get("right") or [])[:20]]
    return o


def validate_doc(doc: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    blocks = doc.get("blocks") or []
    if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS:
        raise CmsError(f"A page holds at most {MAX_BLOCKS} blocks")
    seo_in = doc.get("seo") or {}
    seo = {"meta_title": str(seo_in.get("meta_title") or "")[:90], "meta_description": str(seo_in.get("meta_description") or "")[:200],
           "noindex": bool(seo_in.get("noindex")), "keywords": [str(k)[:60] for k in (seo_in.get("keywords") or [])][:10]}
    if seo_in.get("canonical"):
        seo["canonical"] = href(seo_in["canonical"])
    if seo_in.get("og_image"):
        seo["og_image"] = https(seo_in["og_image"])
    return {"blocks": [validate_block(b, warnings) for b in blocks], "seo": seo}, warnings


def validate_theme(theme: dict) -> dict:
    t = {**THEME_KEYS, **{k: str(v) for k, v in (theme or {}).items() if k in THEME_KEYS}}
    for k in ("brand_color", "text_color", "background", "accent"):
        if not HEX.match(t[k]):
            raise CmsError(f"{k} must be #RRGGBB")
    t["font"] = re.sub(r"[^A-Za-z0-9 ,\-]", "", t["font"])[:80] or THEME_KEYS["font"]
    t["radius"] = str(max(0, min(24, int(re.sub(r"\D", "", t["radius"]) or 8))))
    return t


def validate_nav(nav: list) -> list:
    return [{"label": str(i.get("label") or "")[:60], "path": href(i.get("path")), **({"locale": i["locale"]} if i.get("locale") in LOCALES else {})}
            for i in (nav or [])[:30] if i.get("label")]


async def build_path(db: AsyncSession, parent_id, slug: str, kind: str) -> str:
    if parent_id:
        parent = await db.get(CmsPage, parent_id)
        if parent is None:
            raise CmsError("Parent page not found")
        base = parent.path.rstrip("/")
    else:
        base = "/blog" if kind == "POST" else ""
    return "/" if slug == "home" and not parent_id and kind == "PAGE" else f"{base}/{slug}"


def audit(db: AsyncSession, user, event: str, target_type: str, target_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="content",
                    target_type=target_type, target_id=str(target_id) if target_id else None, details=details))


# ── workflow ───────────────────────────────────────────────────────────────────

async def submit(db: AsyncSession, page: CmsPage, user) -> None:
    if page.status not in ("DRAFT", "PUBLISHED", "APPROVED"):
        raise CmsError(f"Cannot submit a page in {page.status}")
    page.status, page.submitted_by, page.approved_by = "IN_REVIEW", user.username, None
    audit(db, user, "cms.page.submitted", "cms_page", page.id, {"path": page.path})


async def approve(db: AsyncSession, page: CmsPage, user, ok: bool, note: str = "") -> None:
    if page.status != "IN_REVIEW":
        raise CmsError("Only a page in review can be approved or rejected")
    if page.submitted_by == user.username:
        raise CmsError("A different person must review this page")
    page.status = "APPROVED" if ok else "DRAFT"
    page.approved_by = user.username if ok else None
    audit(db, user, "cms.page.approved" if ok else "cms.page.rejected", "cms_page", page.id, {"note": note[:300]})


async def _live(db: AsyncSession, page: CmsPage) -> Optional[CmsPageVersion]:
    return await db.get(CmsPageVersion, page.live_version_id) if page.live_version_id else None


async def publish(db: AsyncSession, page: CmsPage, user, note: str = "", content: Optional[dict] = None, title: Optional[str] = None) -> CmsPageVersion:
    site = await db.get(CmsSite, page.site_id)
    if content is None:                                   # normal publish: from the reviewed draft
        if site.require_approval and page.status != "APPROVED":
            raise CmsError("This site requires an approved review before publishing")
        content, _ = validate_doc(page.draft or {})
    prev = await _live(db, page)
    n = (await db.execute(select(func.coalesce(func.max(CmsPageVersion.version), 0)).where(CmsPageVersion.page_id == page.id))).scalar_one()
    v = CmsPageVersion(page_id=page.id, version=n + 1, title=title or page.title, content={**content, "path": page.path},
                       note=note[:200] or None, published_by=user.username)
    db.add(v)
    await db.flush()
    old_path = (prev.content or {}).get("path") if prev else None
    if old_path and old_path != page.path:                # slug changed after going live: keep old links working
        await upsert_redirect(db, page.site_id, old_path, page.path, 301, auto=True)
    page.live_version_id, page.status = v.id, "PUBLISHED"
    audit(db, user, "cms.page.published", "cms_page", page.id, {"version": v.version, "path": page.path})
    if page.translation_state == "SOURCE":               # translations of a changed source need a look
        for t in (await db.execute(select(CmsPage).where(CmsPage.translation_group == page.translation_group, CmsPage.id != page.id))).scalars():
            if t.translation_state == "REVIEWED":
                t.translation_state = "STALE"
    return v


async def rollback(db: AsyncSession, page: CmsPage, version: int, user) -> CmsPageVersion:
    old = (await db.execute(select(CmsPageVersion).where(CmsPageVersion.page_id == page.id, CmsPageVersion.version == version))).scalar_one_or_none()
    if old is None:
        raise CmsError("Version not found")
    content = {k: v for k, v in old.content.items() if k != "path"}
    page.draft = content
    return await publish(db, page, user, note=f"Rollback to v{version}", content=content, title=old.title)


async def unpublish(db: AsyncSession, page: CmsPage, user) -> None:
    page.live_version_id, page.status = None, "ARCHIVED"
    audit(db, user, "cms.page.unpublished", "cms_page", page.id, {"path": page.path})


async def upsert_redirect(db: AsyncSession, site_id, src: str, dst: str, code: int = 301, auto: bool = False) -> CmsRedirect:
    src, dst = href(src), href(dst)
    if not src.startswith("/"):
        raise CmsError("A redirect starts from a site path")
    if src == dst:
        raise CmsError("A redirect cannot point to itself")
    if code not in (301, 302):
        raise CmsError("Redirect code must be 301 or 302")
    # never create a loop: follow dst through existing redirects
    seen, cur = {src}, dst
    for _ in range(10):
        nxt = (await db.execute(select(CmsRedirect.to_path).where(CmsRedirect.site_id == site_id, CmsRedirect.from_path == cur))).scalar_one_or_none()
        if nxt is None:
            break
        if nxt in seen:
            raise CmsError("This redirect would create a loop")
        seen.add(cur)
        cur = nxt
    r = (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == site_id, CmsRedirect.from_path == src))).scalar_one_or_none()
    if r is None:
        r = CmsRedirect(site_id=site_id, from_path=src, to_path=dst, code=code, auto=auto, hits=0)
        db.add(r)
    else:
        r.to_path, r.code = dst, code
    # a newer redirect replaces chains: anything pointing at src now points at dst
    for other in (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == site_id, CmsRedirect.to_path == src))).scalars():
        other.to_path = dst
    return r


# ── public rendering ───────────────────────────────────────────────────────────

async def site_by_key(db: AsyncSession, key: str) -> Optional[CmsSite]:
    return (await db.execute(select(CmsSite).where(CmsSite.key == key))).scalar_one_or_none()


async def find_live(db: AsyncSession, site: CmsSite, path: str, locale: str) -> tuple[Optional[CmsPage], Optional[CmsTableRow]]:
    """The live page at a path in a locale (falls back to the default locale); dynamic pages match <prefix>/<row>."""
    for loc in dict.fromkeys([locale, site.default_locale]):
        p = (await db.execute(select(CmsPage).where(CmsPage.site_id == site.id, CmsPage.locale == loc, CmsPage.path == path,
                                                    CmsPage.status == "PUBLISHED", CmsPage.live_version_id.isnot(None)))).scalar_one_or_none()
        if p:
            return p, None
        prefix, _, row_slug = path.rpartition("/")
        if row_slug and prefix:
            d = (await db.execute(select(CmsPage).where(CmsPage.site_id == site.id, CmsPage.locale == loc, CmsPage.path == prefix,
                                                        CmsPage.kind == "DYNAMIC", CmsPage.status == "PUBLISHED"))).scalar_one_or_none()
            if d and d.table_id:
                t = await db.get(CmsTable, d.table_id)
                row = (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == d.table_id, CmsTableRow.slug == row_slug))).scalar_one_or_none()
                if t and t.published and row:
                    return d, row
    return None, None


def _fill_row(blocks: list, row: CmsTableRow) -> list:
    def sub(s: str) -> str:
        return TOKEN.sub(lambda m: str((row.values or {}).get(m.group(1), "")), s)

    def one(b: dict) -> dict:
        b = dict(b)
        for k in ("text", "title", "subtitle", "name", "size", "price", "label"):
            if isinstance(b.get(k), str):
                b[k] = sub(b[k])
        if b["type"] == "columns":
            b["left"], b["right"] = [one(x) for x in b["left"]], [one(x) for x in b["right"]]
        return b
    return [one(b) for b in blocks]


async def expand(db: AsyncSession, site: CmsSite, blocks: list, depth: int = 0) -> list:
    """Resolve CTAs, embeds and table blocks into data the page can render without more calls."""
    out = []
    for b in blocks:
        b = dict(b)
        if b["type"] in ("cta", "hero") and b.get("cta_key"):
            c = (await db.execute(select(CmsCta).where(CmsCta.site_id == site.id, CmsCta.key == b["cta_key"]))).scalar_one_or_none()
            if c:
                b["cta"] = {"key": c.key, "label": c.label, "href": c.href, "style": c.style}
            elif b["type"] == "cta":
                continue
        elif b["type"] == "embed":
            if depth >= 2:
                continue
            src = await db.get(CmsPage, uuid.UUID(b["page_id"]))
            v = await _live(db, src) if src and src.site_id == site.id and src.access == "PUBLIC" else None
            b["blocks"] = await expand(db, site, (v.content or {}).get("blocks", []), depth + 1) if v else []
        elif b["type"] == "table":
            t = (await db.execute(select(CmsTable).where(CmsTable.site_id == site.id, CmsTable.key == b["table_key"]))).scalar_one_or_none()
            rows = [] if not t or not t.published else (await db.execute(
                select(CmsTableRow).where(CmsTableRow.table_id == t.id).order_by(CmsTableRow.position, CmsTableRow.slug).limit(200))).scalars().all()
            cols = b.get("columns") or [c["key"] for c in (t.columns if t else [])][:6]
            b["rows"] = [{"slug": r.slug, **{c: (r.values or {}).get(c) for c in cols}} for r in rows]
            b["columns"] = cols
        elif b["type"] == "columns":
            b["left"], b["right"] = await expand(db, site, b["left"], depth), await expand(db, site, b["right"], depth)
        out.append(b)
    return out


async def alternates(db: AsyncSession, site: CmsSite, page: CmsPage) -> list[dict]:
    rows = (await db.execute(select(CmsPage.locale, CmsPage.path).where(CmsPage.translation_group == page.translation_group,
                                                                        CmsPage.status == "PUBLISHED"))).all()
    return [{"locale": loc, "path": p} for loc, p in sorted(rows)]


def json_ld(site: CmsSite, page: CmsPage, version: CmsPageVersion, blocks: list, base: str, row: Optional[CmsTableRow] = None) -> list[dict]:
    url = f"{base}{page.path}" + (f"/{row.slug}" if row else "")
    out: list[dict] = []
    if page.kind == "POST":
        out.append({"@context": "https://schema.org", "@type": "BlogPosting", "headline": version.title, "inLanguage": page.locale,
                    "author": {"@type": "Person", "name": page.author or site.name}, "datePublished": version.published_at.isoformat() if version.published_at else None,
                    "mainEntityOfPage": url, "publisher": {"@type": "Organization", "name": site.name}})
    else:
        out.append({"@context": "https://schema.org", "@type": "WebPage", "name": version.title, "inLanguage": page.locale, "url": url})
    faqs = [i for b in blocks if b["type"] == "faq" for i in b["items"]]
    if faqs:
        out.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": LINK.sub(r"\1", i["a"]).replace("**", "")}} for i in faqs]})
    return out


def base_url(site: CmsSite) -> str:
    # until a custom domain is activated (M47) the site lives under the local app URL
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/site/{site.key}"


async def sitemap(db: AsyncSession, site: CmsSite) -> str:
    base = base_url(site)
    pages = (await db.execute(select(CmsPage).where(CmsPage.site_id == site.id, CmsPage.status == "PUBLISHED",
                                                    CmsPage.access == "PUBLIC", CmsPage.kind != "DYNAMIC"))).scalars().all()
    groups: dict = {}
    for p in pages:
        v = await _live(db, p)
        if v and not (v.content.get("seo") or {}).get("noindex"):
            groups.setdefault(p.translation_group, []).append((p, v))
    for p in (await db.execute(select(CmsPage).where(CmsPage.site_id == site.id, CmsPage.status == "PUBLISHED", CmsPage.kind == "DYNAMIC",
                                                     CmsPage.access == "PUBLIC"))).scalars().all():
        t = await db.get(CmsTable, p.table_id) if p.table_id else None
        if t and t.published:
            v = await _live(db, p)
            for r in (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == t.id))).scalars():
                groups.setdefault(uuid.uuid4(), []).append((p, v, r))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for items in groups.values():
        for it in items:
            p, v = it[0], it[1]
            path = p.path + (f"/{it[2].slug}" if len(it) > 2 else "")
            loc = f"{base}/{p.locale}{'' if path == '/' else path}"
            lines.append(f"<url><loc>{escape(loc)}</loc><lastmod>{v.published_at.date().isoformat()}</lastmod>")
            if len(it) == 2 and len(items) > 1:
                for q, _ in items:
                    lines.append(f'<xhtml:link rel="alternate" hreflang="{q.locale}" href="{escape(base + "/" + q.locale + ("" if q.path == "/" else q.path))}"/>')
            lines.append("</url>")
    lines.append("</urlset>")
    return "\n".join(lines)


async def robots(db: AsyncSession, site: CmsSite) -> str:
    # members-only pages answer 401/403 and carry noindex, so they need no Disallow rule
    return "\n".join(["User-agent: *", "Allow: /",
                      f"Sitemap: {settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/cms/site/{site.key}/sitemap.xml", ""])


# ── SEO / AEO audits ───────────────────────────────────────────────────────────

def _all_text(blocks: list) -> str:
    parts = []
    for b in blocks:
        for k in ("text", "title", "subtitle", "name"):
            if b.get(k):
                parts.append(b[k])
        if b["type"] == "faq":
            parts += [f'{i["q"]} {i["a"]}' for i in b["items"]]
        if b["type"] == "columns":
            parts.append(_all_text(b["left"] + b["right"]))
    return LINK.sub(r"\1", " ".join(parts)).replace("**", "")


def _links(blocks: list) -> list[str]:
    out = []
    for b in blocks:
        for m in LINK.finditer(b.get("text") or ""):
            out.append(m.group(2))
        if b["type"] == "faq":
            out += [m.group(2) for i in b["items"] for m in LINK.finditer(i["a"])]
        if b.get("href"):
            out.append(b["href"])
        if b["type"] == "columns":
            out += _links(b["left"] + b["right"])
    return out


async def seo_audit(db: AsyncSession, page: CmsPage) -> dict:
    """On-page checks of the draft. Findings are rules over the content; no ranking or traffic is invented."""
    doc, warnings = validate_doc(page.draft or {})
    seo, blocks = doc["seo"], doc["blocks"]
    f: list[dict] = [{"level": "warn", "code": "a11y", "message": w} for w in warnings]
    title = seo["meta_title"] or page.title
    if not 15 <= len(title) <= 65:
        f.append({"level": "warn", "code": "title_length", "message": f"Title is {len(title)} characters (aim for 15–65)."})
    if not seo["meta_description"]:
        f.append({"level": "error", "code": "no_description", "message": "Meta description is missing."})
    elif not 50 <= len(seo["meta_description"]) <= 160:
        f.append({"level": "warn", "code": "description_length", "message": f"Description is {len(seo['meta_description'])} characters (aim for 50–160)."})
    h1 = [b for b in blocks if (b["type"] == "heading" and b["level"] == 1) or b["type"] == "hero"]
    if len(h1) != 1:
        f.append({"level": "warn", "code": "h1", "message": f"The page has {len(h1)} main headings (H1/hero); use exactly one."})
    text = _all_text(blocks)
    words = len(text.split())
    if words < 150 and page.kind == "POST":
        f.append({"level": "warn", "code": "thin", "message": f"Only {words} words; posts under 150 words are thin content."})
    for kw in seo["keywords"]:
        if kw.lower() not in (text + " " + title).lower():
            f.append({"level": "warn", "code": "keyword_missing", "message": f"Target keyword “{kw}” does not appear in the title or text."})
    internal = [u for u in _links(blocks) if u.startswith("/")]
    broken = []
    for u in internal:
        path = u.split("#")[0].split("?")[0] or "/"
        p, _ = await find_live(db, await db.get(CmsSite, page.site_id), path, page.locale)
        redirect = (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == page.site_id, CmsRedirect.from_path == path))).scalar_one_or_none()
        if p is None and redirect is None:
            broken.append(u)
    for u in broken:
        f.append({"level": "error", "code": "broken_link", "message": f"Internal link {u} does not lead to a published page."})
    if not internal and page.kind == "POST":
        f.append({"level": "info", "code": "no_internal_links", "message": "No internal links; link to related pages."})
    score = max(0, 100 - 15 * sum(1 for x in f if x["level"] == "error") - 5 * sum(1 for x in f if x["level"] == "warn"))
    return {"score": score, "words": words, "internal_links": len(internal), "findings": f,
            "search_console": {"status": "NOT_CONFIGURED", "detail": "Connect Google Search Console at activation (M47) to see impressions and clicks."}}


QUESTION = re.compile(r"^(what|how|why|when|where|which|who|can|is|are|does|do|nini|vipi|kwa nini|lini|wapi|nasıl|neden|ne zaman|nerede|hangi|kim|mi|mı)\b|\?$", re.I)


async def aeo_audit(db: AsyncSession, page: CmsPage) -> dict:
    """Answer-engine readiness from the content itself. External answer-engine visibility is NOT_AVAILABLE without a
    measurement provider; it is never estimated."""
    doc, _ = validate_doc(page.draft or {})
    blocks = doc["blocks"]
    faqs = [i for b in blocks if b["type"] == "faq" for i in b["items"]]
    q_heads = [b for b in blocks if b["type"] == "heading" and QUESTION.search(b["text"].strip())]
    long_answers = [i["q"] for i in faqs if len(i["a"].split()) > 80]
    translations = (await db.execute(select(func.count()).select_from(CmsPage).where(CmsPage.translation_group == page.translation_group,
                                                                                    CmsPage.id != page.id))).scalar_one()
    checks = [
        {"code": "faq_schema", "ok": bool(faqs), "message": "FAQ block present (emitted as FAQPage structured data)."},
        {"code": "question_headings", "ok": bool(q_heads) or bool(faqs), "message": "Headings phrased as the questions people ask."},
        {"code": "concise_answers", "ok": bool(faqs) and not long_answers, "message": "FAQ answers under 80 words (answer first)."
         + (f" Too long: {', '.join(long_answers[:3])}" if long_answers else "")},
        {"code": "author", "ok": page.kind != "POST" or bool(page.author), "message": "Posts name an author."},
        {"code": "language", "ok": page.locale in LOCALES, "message": f"Page language declared ({page.locale})."},
        {"code": "translations", "ok": translations > 0, "message": "Available in more than one language (hreflang alternates)."},
        {"code": "indexable", "ok": not doc["seo"]["noindex"], "message": "Page is indexable."},
    ]
    return {"checks": checks, "ready": sum(c["ok"] for c in checks), "total": len(checks),
            "visibility": {"status": "NOT_AVAILABLE", "detail": "No answer-engine measurement provider is connected; no score is shown."}}


def translation_stub(source: CmsPage, locale: str) -> dict:
    """A new translation starts as a copy of the source marked for review (machine translation is never auto-published)."""
    return {"blocks": (source.draft or {}).get("blocks", []), "seo": (source.draft or {}).get("seo", {}),
            "translation_note": f"Copied from {source.locale}; translate and review before publishing."}


def dumps_ld(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")
