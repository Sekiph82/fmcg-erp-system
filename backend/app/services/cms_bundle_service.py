"""M47.S01.T007 content sync: the CMS part of configuration bundles (config_bundle_service).

Exported by natural key: sites (key), PUBLIC pages' LIVE versions + metadata (site key + locale + path), dynamic tables
with rows (site key + table key), redirects (site key + from path) and CTAs (site key + key). Domains, members-only
pages (their access lists name portal accounts), counters and media files stay behind; media travel by reference only
(a block keeps its media id and the dry run warns when the target does not have it).
Import never publishes: pages arrive as DRAFT (an existing page gets its draft replaced, its live version untouched),
new tables arrive unpublished and rows of a table that is published on the target are not changed. Sites, redirects
and CTAs are configuration and are applied as shown in the dry run (administrators only).
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import CmsCta, CmsMedia, CmsPage, CmsPageVersion, CmsRedirect, CmsSite, CmsTable, CmsTableRow
from app.services import cms_service as cms

SITE_FIELDS = ("name", "default_locale", "locales", "theme", "nav", "require_approval")


def _media_refs(blocks: list) -> list[str]:
    out = []
    for b in blocks:
        if b.get("media_id"):
            out.append(b["media_id"])
        if b.get("type") == "columns":
            out += _media_refs(b.get("left", []) + b.get("right", []))
    return out


async def export(db: AsyncSession) -> dict:
    sites = {s.id: s for s in (await db.execute(select(CmsSite).order_by(CmsSite.key))).scalars()}
    tables = {t.id: t for t in (await db.execute(select(CmsTable))).scalars()}
    out: dict = {"sites": [{"key": s.key, **{f: getattr(s, f) for f in SITE_FIELDS}} for s in sites.values()],
                 "tables": [], "pages": [], "redirects": [], "ctas": []}
    for t in sorted(tables.values(), key=lambda t: (sites[t.site_id].key, t.key)):
        rows = (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == t.id).order_by(CmsTableRow.slug))).scalars()
        out["tables"].append({"site": sites[t.site_id].key, "key": t.key, "name": t.name, "columns": t.columns,
                              "rows": [{"slug": r.slug, "values": r.values, "position": r.position} for r in rows]})
    pages = (await db.execute(select(CmsPage).where(CmsPage.live_version_id.isnot(None), CmsPage.access == "PUBLIC"))).scalars().all()
    versions = {v.id: v for v in (await db.execute(select(CmsPageVersion).where(CmsPageVersion.id.in_([p.live_version_id for p in pages] or [None])))).scalars()}
    by_id = {p.id: p for p in (await db.execute(select(CmsPage))).scalars()} if pages else {}
    for p in pages:
        v = versions[p.live_version_id]
        content = {"blocks": v.content.get("blocks", []), "seo": v.content.get("seo", {})}
        path = v.content.get("path") or p.live_path
        parent = by_id.get(p.parent_id)
        out["pages"].append({"site": sites[p.site_id].key, "locale": p.locale, "path": path, "kind": p.kind, "title": v.title,
                             "content": content, "meta": v.content.get("meta") or {}, "group": str(p.translation_group),
                             "source": p.translation_state == "SOURCE", "parent_path": parent.live_path or parent.path if parent else None,
                             "table_key": tables[p.table_id].key if p.table_id in tables else None, "media_refs": _media_refs(content["blocks"])})
    out["pages"].sort(key=lambda x: (x["site"], len(x["path"]), x["path"], x["locale"]))     # parents before children
    for r in (await db.execute(select(CmsRedirect))).scalars():
        out["redirects"].append({"site": sites[r.site_id].key, "from_path": r.from_path, "to_path": r.to_path, "code": r.code})
    for c in (await db.execute(select(CmsCta))).scalars():
        out["ctas"].append({"site": sites[c.site_id].key, "key": c.key, "label": c.label, "href": c.href, "style": c.style})
    for k in ("redirects", "ctas"):
        out[k].sort(key=lambda x: json.dumps(x, sort_keys=True))
    return out


def _j(v) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def _step(table: str, key: str, existing, row: dict, changed: list[str], mode: str, **extra) -> dict:
    if existing is None:
        return {"table": table, "key": key, "action": "create", "row": row, **extra}
    if not changed:
        return {"table": table, "key": key, "action": "unchanged", **extra}
    if mode == "skip_existing":
        return {"table": table, "key": key, "action": "skip", "changed": changed, **extra}
    return {"table": table, "key": key, "action": "update", "changed": changed, "row": row, "id": existing.id, **extra}


async def plan(db: AsyncSession, items: dict, mode: str, site_keys: Optional[dict] = None) -> list[dict]:
    """Dry-run steps for the CMS part. site_keys maps a bundle site key to a target site key (e.g. clone a site)."""
    sk = site_keys or {}
    key_of = lambda k: sk.get(k, k)                                  # noqa: E731
    steps: list[dict] = []
    targets: dict[str, Optional[CmsSite]] = {}
    for s in items.get("sites", []):
        k = key_of(s["key"])
        ex = targets[k] = await cms.site_by_key(db, k)
        row = {**s, "key": k}
        try:
            row["theme"], row["nav"] = cms.validate_theme(s.get("theme") or {}), cms.validate_nav(s.get("nav") or [])
            # M47 review: name / locales / default locale go through the CMS API's own validators
            from pydantic import ValidationError
            from app.api.v1.endpoints.cms import SiteIn, _apply_site
            probe = CmsSite(key=k, name=ex.name if ex else k, locales=["en"], default_locale="en")
            try:
                _apply_site(probe, SiteIn(name=s.get("name"), locales=s.get("locales"), default_locale=s.get("default_locale")))
            except ValidationError as ve:
                raise cms.CmsError(f"Invalid site settings: {ve.errors()[0].get('msg')}") from None
            if probe.default_locale not in probe.locales:
                raise cms.CmsError("The default locale must be one of the site's locales")
            row["name"], row["locales"], row["default_locale"] = probe.name, probe.locales, probe.default_locale
            if ex is not None and ex.require_approval:   # an import never switches the approval step off
                row["require_approval"] = True
            row["require_approval"] = bool(row.get("require_approval", True))
        except cms.CmsError as e:
            steps.append({"table": "cms_sites", "key": k, "action": "error", "detail": str(e)})
            continue
        changed = [f for f in SITE_FIELDS if ex is not None and _j(getattr(ex, f)) != _j(row.get(f))]
        steps.append(_step("cms_sites", k, ex, row, changed, mode))

    async def site(k: str) -> Optional[CmsSite]:
        if k not in targets:
            targets[k] = await cms.site_by_key(db, k)
        return targets[k]

    def missing_site(table: str, label: str, k: str) -> bool:
        if targets.get(k) is None and not any(st["table"] == "cms_sites" and st["key"] == k and st["action"] == "create" for st in steps):
            steps.append({"table": table, "key": label, "action": "error", "detail": f"site {k} is neither on the target nor in the bundle"})
            return True
        return False

    for t in items.get("tables", []):
        k = key_of(t["site"])
        label = f"{k} / {t['key']}"
        s = await site(k)
        if missing_site("cms_tables", label, k):
            continue
        ex = (await db.execute(select(CmsTable).where(CmsTable.site_id == s.id, CmsTable.key == t["key"]))).scalar_one_or_none() if s else None
        changed: list[str] = []
        if ex is not None:
            changed = [f for f in ("name", "columns") if _j(getattr(ex, f)) != _j(t[f])]
            cur = [{"slug": r.slug, "values": r.values, "position": r.position} for r in
                   (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == ex.id).order_by(CmsTableRow.slug))).scalars()]
            if _j(cur) != _j(sorted(t["rows"], key=lambda r: r["slug"])):
                if ex.published:
                    steps.append({"table": "cms_tables", "key": label, "action": "skip", "changed": ["rows"],
                                  "detail": "the table is published on the target; its rows are live and are not changed by an import"})
                    continue
                changed.append("rows")
        steps.append(_step("cms_tables", label, ex, {**t, "site": k}, changed, mode))

    for p in items.get("pages", []):
        k = key_of(p["site"])
        label = f"{k} / {p['locale']} / {p['path']}"
        s = await site(k)
        if missing_site("cms_pages", label, k):
            continue
        try:
            content, _ = cms.validate_doc(p["content"])
        except cms.CmsError as e:
            steps.append({"table": "cms_pages", "key": label, "action": "error", "detail": str(e)})
            continue
        ex = (await db.execute(select(CmsPage).where(CmsPage.site_id == s.id, CmsPage.locale == p["locale"], CmsPage.path == p["path"]))).scalar_one_or_none() if s else None
        changed = []
        if ex is not None:
            cur = {"blocks": (ex.draft or {}).get("blocks", []), "seo": (ex.draft or {}).get("seo", {})}
            changed = (["title"] if ex.title != p["title"] else []) + (["draft"] if _j(cur) != _j(content) else [])
        refs = p.get("media_refs") or []
        have = {str(i) for i in (await db.execute(select(CmsMedia.id).where(CmsMedia.id.in_([uuid.UUID(r) for r in refs] or [None])))).scalars()}
        miss = [r for r in refs if r not in have]
        extra = {"detail": f"media not on the target (reference only, upload it there): {', '.join(miss)}"} if miss else {}
        extra.update(_group=p.get("group"), _pid=ex.id if ex else None)
        steps.append(_step("cms_pages", label, ex, {**p, "site": k, "content": content}, changed, mode, **extra))

    for r in items.get("redirects", []):
        k = key_of(r["site"])
        label = f"{k} / {r['from_path']}"
        s = await site(k)
        if missing_site("cms_redirects", label, k):
            continue
        ex = (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == s.id, CmsRedirect.from_path == r["from_path"]))).scalar_one_or_none() if s else None
        changed = [f for f in ("to_path", "code") if ex is not None and getattr(ex, f) != r[f]]
        steps.append(_step("cms_redirects", label, ex, {**r, "site": k}, changed, mode))

    for c in items.get("ctas", []):
        k = key_of(c["site"])
        label = f"{k} / {c['key']}"
        s = await site(k)
        if missing_site("cms_ctas", label, k):
            continue
        try:
            cms.href(c["href"])
        except cms.CmsError as e:
            steps.append({"table": "cms_ctas", "key": label, "action": "error", "detail": str(e)})
            continue
        ex = (await db.execute(select(CmsCta).where(CmsCta.site_id == s.id, CmsCta.key == c["key"]))).scalar_one_or_none() if s else None
        changed = [f for f in ("label", "href", "style") if ex is not None and getattr(ex, f) != c[f]]
        steps.append(_step("cms_ctas", label, ex, {**c, "site": k}, changed, mode))
    return steps


async def apply(db: AsyncSession, steps: list[dict], user: str) -> dict:
    done = {"create": 0, "update": 0}
    by = f"bundle:{user}"[:100]

    async def site_id(k: str):
        s = await cms.site_by_key(db, k)
        return s.id

    groups: dict[str, uuid.UUID] = {}            # bundle translation group → target group (from pages already on the target)
    for s in steps:
        if s["table"] == "cms_pages" and s.get("_pid") and s.get("_group"):
            ex = await db.get(CmsPage, s["_pid"])
            if ex:
                groups.setdefault(s["_group"], ex.translation_group)
    for s in steps:
        a, row = s["action"], s.get("row")
        if a not in ("create", "update"):
            continue
        t = s["table"]
        if t == "cms_sites":
            site = CmsSite(key=row["key"], domain_status="LOCAL_ONLY", created_by=by) if a == "create" else await db.get(CmsSite, s["id"])
            for f in SITE_FIELDS:
                setattr(site, f, row[f])
            db.add(site)
            await db.flush()
        elif t == "cms_tables":
            sid = await site_id(row["site"])
            tb = CmsTable(site_id=sid, key=row["key"], published=False) if a == "create" else await db.get(CmsTable, s["id"])
            tb.name, tb.columns = row["name"], row["columns"]
            db.add(tb)
            await db.flush()
            existing = {r.slug: r for r in (await db.execute(select(CmsTableRow).where(CmsTableRow.table_id == tb.id))).scalars()}
            for r in row["rows"]:
                cur = existing.get(r["slug"])
                if cur is None:
                    db.add(CmsTableRow(table_id=tb.id, slug=r["slug"], values=r["values"], position=r.get("position") or 0))
                else:
                    cur.values, cur.position = r["values"], r.get("position") or 0
        elif t == "cms_pages":
            sid = await site_id(row["site"])
            if a == "create":
                parent = (await db.execute(select(CmsPage.id).where(CmsPage.site_id == sid, CmsPage.locale == row["locale"],
                                                                    CmsPage.path == row["parent_path"]))).scalar_one_or_none() if row.get("parent_path") else None
                table = (await db.execute(select(CmsTable.id).where(CmsTable.site_id == sid, CmsTable.key == row["table_key"]))).scalar_one_or_none() if row.get("table_key") else None
                meta = row.get("meta") or {}
                group = groups.setdefault(row.get("group") or uuid.uuid4().hex, uuid.uuid4())
                p = CmsPage(id=uuid.uuid4(), site_id=sid, parent_id=parent, kind=row["kind"], locale=row["locale"], translation_group=group,
                            translation_state="SOURCE" if row.get("source", True) else "NEEDS_REVIEW",
                            slug=row["path"].rstrip("/").rsplit("/", 1)[-1] or "home", path=row["path"], title=row["title"], draft=row["content"],
                            status="DRAFT", access="PUBLIC", table_id=table, author=meta.get("author"), category=meta.get("category"),
                            tags=meta.get("tags") or [], updated_by=by)
                db.add(p)
                await db.flush()
            else:
                p = await db.get(CmsPage, s["id"])
                p.title, p.draft, p.updated_by = row["title"], row["content"], by
                if p.status in ("IN_REVIEW", "APPROVED"):            # reviewed content changed: review again
                    p.status, p.approved_by = "DRAFT", None
        elif t == "cms_redirects":
            await cms.upsert_redirect(db, await site_id(row["site"]), row["from_path"], row["to_path"], row["code"])
        elif t == "cms_ctas":
            c = CmsCta(site_id=await site_id(row["site"]), key=row["key"], views=0, clicks=0) if a == "create" else await db.get(CmsCta, s["id"])
            c.label, c.href, c.style = row["label"], cms.href(row["href"]), row["style"]
            db.add(c)
        done[a] += 1
    return done
