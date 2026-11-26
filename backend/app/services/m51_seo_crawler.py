"""M51.S01.T004 technical SEO crawler, vitals (lab vs field), keyword import and authorised competitor comparison.

Safety: only origins on the owner's allow-list (m51_seo_sites) are fetched; robots.txt is honoured (user agent
"POVUSeoBot"); every request goes through provider_http.provider_client and the M50 SSRF check (check_url: scheme,
no credentials, public addresses only, loopback only in PROVIDER_EGRESS=local); redirects are followed by hand and
never leave the allowed origin; page count, depth, bytes and time are bounded. External links are NOT fetched (that
would be crawling sites nobody authorised), so broken-link checks cover internal links only.

Vitals: LAB = a local headless browser run (Lighthouse CLI or Playwright, whichever is installed) → UNAVAILABLE when
neither is; FIELD = Chrome UX Report API
  POST https://chromeuxreport.googleapis.com/v1/records:queryRecord?key=<API key>   body {origin|url, formFactor, metrics}
  https://developer.chrome.com/docs/crux/api  (150 queries/min/project; 28-day collection window; p75 + histogram).
  The doc does not state the no-data response; HTTP 404 is mapped to NO_DATA (UNVERIFIED against the docs).
Lab and field results are returned under separate keys and never merged.

Keyword research: CSV import (schema in KEYWORD_COLUMNS). A paid provider API (e.g. DataForSEO) is UNVERIFIED: its docs
were not confirmed, so none is wired.

Settings (getattr): SEO_CRAWL_MAX_PAGES (int, 50, hard cap 200), SEO_CRAWL_MAX_DEPTH (int, 4), SEO_CRAWL_DELAY (float, 0),
SEO_CRAWL_MAX_BYTES (int, 1_000_000), CRUX_API_KEY (str, ""), CRUX_API_URL (str, official), SEO_LAB_TIMEOUT (int, 90).
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import re
import shutil
import socket
import uuid
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, egress_mode, provider_client
from app.models.m51_seo import M51Keyword, M51SeoCrawl, M51SeoIssue, M51SeoPage, M51SeoSite
from app.services.m50_research_service import FetchBlocked, check_url

UA = "POVUSeoBot/1.0 (+own-site audit)"
CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
KEYWORD_COLUMNS = ("keyword", "volume", "difficulty", "cpc", "locale", "intent")   # keyword required, rest optional
HREFLANG_RE = re.compile(r"^(x-default|[a-z]{2,3}(-[A-Za-z0-9]{2,8})*)$")
LD_REQUIRED = {"Organization": ["name"], "LocalBusiness": ["name", "address"], "Product": ["name"],
               "Article": ["headline"], "BlogPosting": ["headline"], "FAQPage": ["mainEntity"],
               "BreadcrumbList": ["itemListElement"], "WebSite": ["name"]}


class CrawlError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def origin_of(url: str) -> str:
    p = urlsplit(url.strip())
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise CrawlError(422, "Give an origin like https://www.example.com (no path or credentials).")
    return f"{p.scheme}://{p.hostname.lower()}" + (f":{p.port}" if p.port else "")


# ── allow-list ───────────────────────────────────────────────────────────────────────────────────

async def add_site(db: AsyncSession, origin: str, kind: str, note: str, user: str) -> M51SeoSite:
    origin = origin_of(origin)
    if kind not in ("OWN", "AUTHORIZED_SOURCE"):
        raise CrawlError(422, "Kind must be OWN or AUTHORIZED_SOURCE.")
    if kind == "AUTHORIZED_SOURCE" and len((note or "").strip()) < 10:
        raise CrawlError(422, "Say who authorised this source (at least 10 characters).")
    if (await db.execute(select(M51SeoSite).where(M51SeoSite.origin == origin))).scalar_one_or_none():
        raise CrawlError(409, "Already on the allow-list.")
    row = M51SeoSite(origin=origin, kind=kind, note=(note or "")[:500] or None, created_by=user)
    db.add(row)
    await db.flush()
    return row


async def allowed(db: AsyncSession, url: str, kinds=("OWN", "AUTHORIZED_SOURCE")) -> M51SeoSite:
    row = (await db.execute(select(M51SeoSite).where(M51SeoSite.origin == origin_of(url)))).scalar_one_or_none()
    if row is None or row.kind not in kinds:
        raise CrawlError(403, "This site is not on the authorised allow-list; nothing was fetched.")
    return row


# ── HTML parsing ─────────────────────────────────────────────────────────────────────────────────

class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.links, self.imgs = "", {}, [], []
        self.canonical, self.hreflang, self.jsonld, self.h1 = None, [], [], 0
        self.lang, self.text, self._in, self._ld, self._a = None, [], None, None, None
        self.empty_links, self.heads = 0, []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang") or None
        elif tag == "title":
            self._in = "title"
        elif tag == "meta" and a.get("name"):
            self.meta[a["name"].lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.canonical = a.get("href")
        elif tag == "link" and a.get("rel", "").lower() == "alternate" and a.get("hreflang"):
            self.hreflang.append((a["hreflang"], a.get("href", "")))
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._ld = []
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
            self._a = {"text": "", "aria": bool(a.get("aria-label"))}
        elif tag == "img":
            self.imgs.append({"src": a.get("src", ""), "alt": a.get("alt")})
        elif tag in ("h1", "h2", "h3"):
            self._in = tag
            self.h1 += tag == "h1"

    def handle_endtag(self, tag):
        if tag == "title" or tag in ("h1", "h2", "h3"):
            self._in = None
        elif tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None
        elif tag == "a" and self._a is not None:
            self.empty_links += not self._a["text"].strip() and not self._a["aria"]
            self._a = None

    def handle_data(self, d):
        if self._ld is not None:
            self._ld.append(d)
            return
        if self._in == "title":
            self.title += d
        elif self._in in ("h1", "h2", "h3"):
            self.heads.append(d.strip())
        if self._a is not None:
            self._a["text"] += d
        self.text.append(d)


def parse_html(html: str) -> dict:
    p = _Page()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001  malformed markup: keep what was parsed
        pass
    ld, ld_errors = [], []
    for blob in p.jsonld:
        try:
            ld.append(json.loads(blob))
        except ValueError:
            ld_errors.append(blob[:80])
    words = re.findall(r"\w+", " ".join(p.text).lower())
    return {"title": re.sub(r"\s+", " ", p.title).strip(), "description": p.meta.get("description", "").strip(),
            "robots_meta": p.meta.get("robots", "").lower(), "viewport": "viewport" in p.meta, "canonical": p.canonical,
            "hreflang": p.hreflang, "lang": p.lang, "h1": p.h1, "headings": [h for h in p.heads if h][:20],
            "links": p.links, "imgs": p.imgs, "empty_links": p.empty_links, "jsonld": ld, "jsonld_errors": ld_errors,
            "words": len(words), "terms": Counter(w for w in words if len(w) > 3).most_common(40)}


def validate_jsonld(nodes) -> list[str]:
    out = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            if "@graph" in n:
                walk(n["@graph"])
            t = n.get("@type")
            for typ in (t if isinstance(t, list) else [t]):
                miss = [f for f in LD_REQUIRED.get(typ, []) if not n.get(f)]
                if miss:
                    out.append(f"{typ} is missing {', '.join(miss)}")
            if "@context" in n and "schema.org" not in str(n["@context"]):
                out.append("@context is not schema.org")
    walk(nodes)
    return out


# ── fetching ─────────────────────────────────────────────────────────────────────────────────────

async def _get(c: httpx.AsyncClient, url: str, base_origin: str, local: bool, max_bytes: int, hops: int = 5, allow=None) -> dict:
    """allow(url) -> bool (robots.txt) is re-checked for every redirect target BEFORE it is fetched. A redirect to a non-http(s) URL
    raises CrawlError (the crawler records it as a page issue)."""
    chain, cur = [], url
    for _ in range(hops + 1):
        await check_url(cur, local=local)
        async with c.stream("GET", cur, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5"}) as r:
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                nxt = urldefrag(urljoin(cur, r.headers["location"]))[0]
                chain.append({"url": cur, "status": r.status_code})
                if nxt in [x["url"] for x in chain] or nxt == cur:
                    return {"status": r.status_code, "chain": chain, "final": cur, "loop": True, "text": ""}
                if origin_of(nxt) != base_origin:
                    return {"status": r.status_code, "chain": chain, "final": nxt, "external": True, "text": ""}
                if allow is not None and not allow(nxt):
                    return {"status": r.status_code, "chain": chain, "final": nxt, "robots_blocked": True, "text": ""}
                cur = nxt
                continue
            ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
            buf = bytearray()
            if ctype in ("text/html", "application/xhtml+xml", "text/plain", "application/xml", "text/xml"):
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > max_bytes:
                        break
            return {"status": r.status_code, "chain": chain, "final": cur, "ctype": ctype,
                    "text": bytes(buf).decode(r.encoding or "utf-8", errors="replace"),
                    "x_robots": r.headers.get("x-robots-tag", "").lower()}
    return {"status": 310, "chain": chain, "final": cur, "loop": True, "text": ""}


def _sitemap_urls(xml: str) -> tuple[list[str], list[str]]:
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    if "<sitemapindex" in xml:
        return [], locs
    return locs, []


async def crawl(db: AsyncSession, origin: str, user: str, max_pages: Optional[int] = None) -> M51SeoCrawl:
    site = await allowed(db, origin, kinds=("OWN",))
    origin = site.origin
    cap = min(int(max_pages or getattr(settings, "SEO_CRAWL_MAX_PAGES", 50)), 200)
    depth_max = int(getattr(settings, "SEO_CRAWL_MAX_DEPTH", 4))
    delay = float(getattr(settings, "SEO_CRAWL_DELAY", 0))
    max_bytes = int(getattr(settings, "SEO_CRAWL_MAX_BYTES", 1_000_000))
    if egress_mode() == "off":
        raise CrawlError(503, "Provider traffic is switched off (PROVIDER_EGRESS=off).")
    local = egress_mode() == "local"
    run = M51SeoCrawl(origin=origin, status="RUNNING", config={"max_pages": cap, "max_depth": depth_max}, created_by=user)
    db.add(run)
    await db.flush()
    pages: dict[str, dict] = {}
    issues: list[tuple] = []
    robots = RobotFileParser()
    sitemap_locs: list[str] = []
    try:
        async with provider_client(timeout=float(getattr(settings, "M50_FETCH_TIMEOUT", 8))) as c:
            try:
                rb = await _get(c, origin + "/robots.txt", origin, local, max_bytes)
            except (CrawlError, httpx.HTTPError):
                rb = {"status": 599, "text": ""}                  # unreachable
            if rb["status"] == 200:
                robots.parse(rb["text"].splitlines())
                sitemap_locs = re.findall(r"(?im)^sitemap:\s*(\S+)", rb["text"])
            elif 400 <= rb["status"] < 500:
                robots.parse([])          # RFC 9309 2.3.1.3: unavailable (4xx) = everything allowed
            else:                         # RFC 9309 2.3.1.4: 5xx / unreachable / unresolved redirect = assume complete disallow
                robots.parse(["User-agent: *", "Disallow: /"])
                issues.append((origin + "/robots.txt", "ROBOTS_UNREACHABLE", "WARN",
                               f"robots.txt answered HTTP {rb['status']} (unreachable): treated as disallow-all, so nothing was crawled."))
            if rb["status"] == 200 or 400 <= rb["status"] < 500:
                sm_found, sm_urls = await _read_sitemaps(c, origin, local, max_bytes, sitemap_locs)
            else:
                sm_found, sm_urls = True, []        # robots.txt unreachable = disallow-all: nothing else is fetched, no sitemap verdict
            queue = [(origin + "/", 0)]
            seen = {origin + "/"}
            for u in sm_urls[:cap]:                      # sitemap URLs are legitimate crawl seeds of the same site
                try:
                    same = origin_of(u) == origin
                except CrawlError:
                    continue
                if same and u not in seen:
                    seen.add(u)
                    queue.append((u, 1))
            statuses: dict[str, int] = {}
            while queue and len(pages) < cap:
                url, depth = queue.pop(0)
                if not robots.can_fetch("POVUSeoBot", url):
                    issues.append((url, "ROBOTS_BLOCKED", "INFO", "Disallowed for crawlers by robots.txt; not fetched."))
                    continue
                try:
                    got = await _get(c, url, origin, local, max_bytes, allow=lambda u: robots.can_fetch("POVUSeoBot", u))
                except (FetchBlocked, EgressBlocked) as e:
                    pages[url] = {"status": None, "error": str(e)[:200]}
                    continue
                except CrawlError as e:                        # e.g. a redirect to ftp:// or javascript: : a finding, not an abort
                    pages[url] = {"status": None, "error": str(e)[:200]}
                    issues.append((url, "REDIRECT_INVALID", "WARN", "Redirects to a URL that is not http(s); not followed."))
                    continue
                except httpx.HTTPError:
                    pages[url] = {"status": None, "error": "unreachable"}
                    continue
                statuses[url] = got["status"]
                d = {"status": got["status"], "final_url": got["final"], "chain": got["chain"], "depth": depth}
                if got.get("loop"):
                    issues.append((url, "REDIRECT_LOOP", "ERROR", "Redirects loop."))
                if got.get("robots_blocked"):
                    issues.append((url, "ROBOTS_BLOCKED", "INFO", f"Redirects to {got['final'][:150]} which robots.txt disallows; not fetched."))
                if got.get("external"):
                    issues.append((url, "REDIRECT_EXTERNAL", "WARN", f"Redirects off-site to {got['final'][:150]} (not followed)."))
                if len(got["chain"]) > 1:
                    issues.append((url, "REDIRECT_CHAIN", "WARN", f"{len(got['chain'])} redirects before the final page."))
                if got["status"] >= 400:
                    d["links_from"] = []
                elif got.get("ctype", "").startswith(("text/html", "application/xhtml")):
                    info = parse_html(got["text"])
                    d.update({k: info[k] for k in ("title", "description", "robots_meta", "canonical", "lang", "h1", "headings",
                                                  "words", "terms", "viewport")})
                    d["hreflang"] = info["hreflang"]
                    d["noindex"] = "noindex" in info["robots_meta"] or "noindex" in got.get("x_robots", "")
                    d["jsonld_types"] = [n.get("@type") for n in info["jsonld"] if isinstance(n, dict)]
                    _page_issues(url, got, info, d, issues)
                    if depth < depth_max:
                        for h in info["links"]:
                            nxt = urldefrag(urljoin(got["final"], h))[0]
                            if urlsplit(nxt).scheme in ("http", "https") and nxt not in seen:
                                try:
                                    same = origin_of(nxt) == origin
                                except CrawlError:
                                    continue
                                if same:
                                    seen.add(nxt)
                                    queue.append((nxt, depth + 1))
                    d["out_links"] = [urldefrag(urljoin(got["final"], h))[0] for h in info["links"]][:200]
                pages[url] = d
                if delay:
                    await asyncio.sleep(delay)
            _sitemap_checks(origin, pages, issues, sm_found, sm_urls, robots, statuses)
        for url, d in pages.items():                       # broken internal links (only among pages actually fetched)
            for tgt in d.get("out_links", []):
                if statuses.get(tgt, 200) >= 400:
                    issues.append((url, "BROKEN_LINK", "ERROR", f"Links to {tgt[:200]} which answers HTTP {statuses[tgt]}."))
        _duplicates(pages, issues)
        for url, d in pages.items():
            d.pop("out_links", None)
            db.add(M51SeoPage(crawl_id=run.id, url=url[:1000], status=d.get("status"), data=_plain(d)))
        for url, code, sev, detail in issues:
            db.add(M51SeoIssue(crawl_id=run.id, url=url[:1000], code=code, severity=sev, detail=detail[:500]))
        by = Counter(i[2] for i in issues)
        run.summary = {"pages": len(pages), "issues": len(issues), "errors": by["ERROR"], "warnings": by["WARN"],
                       "info": by["INFO"], "by_code": dict(Counter(i[1] for i in issues)),
                       "capped": bool(queue), "robots_txt": rb["status"] == 200}
        run.status = "DONE"
    except (FetchBlocked, EgressBlocked) as e:
        run.status, run.error = "FAILED", str(e)[:480]
    run.finished_at = datetime.now(timezone.utc)
    await db.flush()
    return run


def _plain(d: dict) -> dict:
    return json.loads(json.dumps(d, default=str))


def _page_issues(url, got, info, d, issues):
    def add(code, sev, detail):
        issues.append((url, code, sev, detail))
    if d["status"] == 200:
        if not info["title"]:
            add("TITLE_MISSING", "ERROR", "No <title>.")
        elif len(info["title"]) > 60:
            add("TITLE_LONG", "WARN", f"Title is {len(info['title'])} characters.")
        if not info["description"]:
            add("META_MISSING", "WARN", "No meta description.")
        if not info["canonical"]:
            add("CANONICAL_MISSING", "WARN", "No canonical link.")
        elif urldefrag(urljoin(got["final"], info["canonical"]))[0].rstrip("/") != got["final"].rstrip("/"):
            add("CANONICAL_OTHER", "INFO", f"Canonical points to {info['canonical'][:150]}.")
        if d["noindex"]:
            add("NOINDEX", "INFO", "Page is noindex (meta robots or X-Robots-Tag).")
        if info["h1"] == 0:
            add("H1_MISSING", "WARN", "No <h1>.")
        elif info["h1"] > 1:
            add("H1_MULTIPLE", "INFO", f"{info['h1']} <h1> elements.")
        if not info["lang"]:
            add("HTML_LANG_MISSING", "WARN", "<html> has no lang attribute (accessibility).")
        if not info["viewport"]:
            add("VIEWPORT_MISSING", "WARN", "No viewport meta (mobile rendering).")
        no_alt = [i["src"] for i in info["imgs"] if i["alt"] is None]
        if no_alt:
            add("IMG_ALT_MISSING", "WARN", f"{len(no_alt)} image(s) without alt, e.g. {no_alt[0][:100]}.")
        if info["empty_links"]:
            add("LINK_TEXT_EMPTY", "WARN", f"{info['empty_links']} link(s) with no text or aria-label.")
        for bad in info["jsonld_errors"]:
            add("JSONLD_INVALID", "ERROR", f"Structured data is not valid JSON: {bad}")
        for msg in validate_jsonld(info["jsonld"]):
            add("JSONLD_FIELDS", "WARN", msg)
        for code, _ in info["hreflang"]:
            if not HREFLANG_RE.match(code):
                add("HREFLANG_INVALID", "ERROR", f"hreflang '{code[:20]}' is not a valid language code.")


def _duplicates(pages: dict, issues: list) -> None:
    for field, code in (("title", "DUPLICATE_TITLE"), ("description", "DUPLICATE_META")):
        seen: dict[str, list] = {}
        for url, d in pages.items():
            if d.get("status") == 200 and d.get(field) and not d.get("noindex"):
                seen.setdefault(d[field].strip().lower(), []).append(url)
        for text, urls in seen.items():
            if len(urls) > 1:
                for u in urls:
                    issues.append((u, code, "WARN", f"Same {field} on {len(urls)} pages: {text[:80]}"))
    for url, d in pages.items():                          # hreflang needs a return link
        for code, href in d.get("hreflang", []):
            tgt = pages.get(urldefrag(urljoin(url, href))[0])
            if tgt and tgt.get("status") == 200 and url not in [urldefrag(urljoin(url, h))[0] for _, h in tgt.get("hreflang", [])]:
                issues.append((url, "HREFLANG_NO_RETURN", "WARN", f"{href[:150]} does not link back."))


async def _read_sitemaps(c, origin, local, max_bytes, sitemap_locs):
    urls: list[str] = []
    found = False
    todo = list((sitemap_locs or [origin + "/sitemap.xml"])[:5])
    while todo:
        sm = todo.pop(0)
        try:
            if origin_of(sm) != origin:
                continue
            got = await _get(c, sm, origin, local, max_bytes)
        except (CrawlError, FetchBlocked, EgressBlocked, httpx.HTTPError):
            continue
        if got["status"] != 200:
            continue
        found = True
        locs, children = _sitemap_urls(got["text"])
        urls += locs
        todo += children[:5 - len(todo)]
    return found, urls[:200]


def _sitemap_checks(origin, pages, issues, found, urls, robots, statuses):
    if not found:
        issues.append((origin + "/", "SITEMAP_MISSING", "WARN", "No readable sitemap (robots.txt Sitemap: line or /sitemap.xml)."))
        return
    for u in urls:
        d = pages.get(u)
        if d is None:
            if robots.can_fetch("POVUSeoBot", u) and u not in statuses:
                issues.append((u, "SITEMAP_URL_NOT_CRAWLED", "INFO", "Listed in the sitemap but not reached by the crawl (page cap)."))
        elif d.get("status") and d["status"] >= 400:
            issues.append((u, "SITEMAP_URL_BROKEN", "ERROR", f"Listed in the sitemap but answers HTTP {d['status']}."))
        elif d.get("noindex"):
            issues.append((u, "SITEMAP_URL_NOINDEX", "WARN", "Listed in the sitemap but marked noindex."))


def compare(a: list, b: list) -> dict:
    """Issue sets of two crawls keyed by (code, url): resolved, new and unchanged."""
    ka = {(i.code, i.url): i for i in a}
    kb = {(i.code, i.url): i for i in b}
    row = lambda i: {"code": i.code, "url": i.url, "severity": i.severity}   # noqa: E731
    return {"resolved": [row(ka[k]) for k in ka if k not in kb], "new": [row(kb[k]) for k in kb if k not in ka],
            "unchanged": len(set(ka) & set(kb))}


# ── vitals ───────────────────────────────────────────────────────────────────────────────────────

def lab_tool() -> Optional[str]:
    if shutil.which("lighthouse"):
        return "lighthouse"
    try:
        import playwright  # noqa: F401
        return "playwright"
    except ImportError:
        return None


def parse_lighthouse(report: dict) -> dict:
    a = report.get("audits", {})
    g = lambda k: (a.get(k) or {}).get("numericValue")   # noqa: E731
    return {"lcp_ms": g("largest-contentful-paint"), "cls": g("cumulative-layout-shift"),
            "tbt_ms": g("total-blocking-time"), "fcp_ms": g("first-contentful-paint"),
            "performance_score": (report.get("categories", {}).get("performance") or {}).get("score")}


async def _public_ips(url: str, local: bool) -> list[str]:
    """check_url, then the addresses the lab browser is pinned to (it must not re-resolve the name later)."""
    await check_url(url, local=local)
    host = urlsplit(url).hostname
    try:
        return sorted({i[4][0].split("%")[0] for i in await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)})
    except OSError:
        raise FetchBlocked(f"Cannot resolve {host}.") from None


def chrome_lockdown_flags(host: str, ips: list[str]) -> list[str]:
    """Chrome flags that confine a lab browser to the ONE own host: the name is pinned to the addresses checked above (no
    DNS rebinding), every other name does not resolve, and every other address (IP literals, loopback) goes to a dead proxy.
    The host-resolver rule contains spaces, which Lighthouse's single --chrome-flags string cannot carry, so Lighthouse gets only
    the space-free proxy flags (every non-own address -> dead proxy); Playwright passes the full list as separate arguments."""
    ip = ips[0] if ips else "0.0.0.0"
    return ["--headless", "--no-sandbox", f"--host-resolver-rules=MAP {host} {ip}, MAP * ~NOTFOUND",
            "--proxy-server=http://127.0.0.1:9", f"--proxy-bypass-list=<-loopback>;{host}"]


async def _lab_request_guard(route, local: bool, host: str) -> None:
    """Playwright route handler: only requests to the own host (and inline data:/blob: URLs) that pass check_url proceed."""
    u = route.request.url
    try:
        if urlsplit(u).scheme in ("data", "blob", "about"):
            return await route.continue_()
        if (urlsplit(u).hostname or "").lower() != host:
            raise FetchBlocked("off-origin lab request")
        await check_url(u, local=local)
    except (FetchBlocked, EgressBlocked, ValueError):
        return await route.abort("blockedbyclient")
    await route.continue_()


async def lab_vitals(db: AsyncSession, url: str) -> dict:
    """Lab run in a local headless Chrome. OWN origins only (an AUTHORIZED_SOURCE is someone else's site: a browser would run its
    scripts and fetch whatever they ask for). The browser is confined to the checked own host (see chrome_lockdown_flags for
    Lighthouse; a page.route guard that re-runs check_url on every request and redirect for Playwright). The subprocess/browser is
    always killed/closed, also on timeout. Residual: Lighthouse trusts Chrome's own flag handling, Playwright additionally filters
    each request."""
    await allowed(db, url, kinds=("OWN",))
    tool = lab_tool()
    base = {"kind": "LAB", "url": url, "measured_at": datetime.now(timezone.utc).isoformat(), "tool": tool}
    if tool is None:
        return {**base, "state": "UNAVAILABLE", "metrics": None,
                "reason": "Neither Lighthouse nor Playwright is installed on this server; no numbers are shown."}
    if egress_mode() == "off":
        return {**base, "state": "BLOCKED", "metrics": None, "reason": "Provider traffic is switched off (PROVIDER_EGRESS=off)."}
    local = egress_mode() == "local"
    host = (urlsplit(url).hostname or "").lower()
    try:
        ips = await _public_ips(url, local)
    except (FetchBlocked, EgressBlocked) as e:
        return {**base, "state": "BLOCKED", "metrics": None, "reason": str(e)[:200]}
    timeout = int(getattr(settings, "SEO_LAB_TIMEOUT", 90))
    proc = br = None
    try:
        if tool == "lighthouse":
            proc = await asyncio.create_subprocess_exec(
                shutil.which("lighthouse"), url, "--output=json", "--quiet", "--only-categories=performance",
                "--chrome-flags=" + " ".join(f for f in chrome_lockdown_flags(host, ips) if " " not in f), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
            return {**base, "state": "OK", "metrics": parse_lighthouse(json.loads(out))}

        async def run_playwright() -> dict:
            nonlocal br
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                br = await p.chromium.launch(args=chrome_lockdown_flags(host, ips)[2:])
                pg = await br.new_page()
                await pg.route("**", lambda route: _lab_request_guard(route, local, host))
                await pg.add_init_script("""window.__v={lcp:0,cls:0};
                  new PerformanceObserver(l=>{for(const e of l.getEntries())window.__v.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});
                  new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__v.cls+=e.value}).observe({type:'layout-shift',buffered:true});""")
                await pg.goto(url, wait_until="load", timeout=timeout * 1000)
                await pg.wait_for_timeout(1000)
                return await pg.evaluate("window.__v")
        v = await asyncio.wait_for(run_playwright(), timeout + 10)
        return {**base, "state": "OK", "metrics": {"lcp_ms": v["lcp"], "cls": v["cls"]}}
    except (asyncio.TimeoutError, OSError, ValueError, Exception) as e:  # noqa: BLE001  tool failure is reported, not hidden
        return {**base, "state": "ERROR", "metrics": None, "reason": f"Lab run failed: {type(e).__name__}"}
    finally:
        if proc is not None and getattr(proc, "returncode", 0) is None:
            proc.kill()
            await proc.wait()
        if br is not None:
            try:
                await br.close()
            except Exception:  # noqa: BLE001  already gone
                pass


async def field_vitals(db: AsyncSession, url_or_origin: str, form_factor: Optional[str] = None, page: bool = False) -> dict:
    await allowed(db, url_or_origin)
    base = {"kind": "FIELD", "source": "Chrome UX Report"}
    key = getattr(settings, "CRUX_API_KEY", "")
    if not key:
        return {**base, "state": "NOT_CONFIGURED", "metrics": None, "reason": "No CRUX_API_KEY is configured."}
    body: dict = {"url": url_or_origin} if page else {"origin": origin_of(url_or_origin)}
    if form_factor:
        if form_factor not in ("DESKTOP", "PHONE", "TABLET"):
            raise CrawlError(422, "formFactor is DESKTOP, PHONE or TABLET.")
        body["formFactor"] = form_factor
    api = getattr(settings, "CRUX_API_URL", "") or CRUX_URL
    try:
        async with provider_client(timeout=15.0) as c:
            r = await c.post(api, params={"key": key}, json=body)
    except EgressBlocked as e:
        return {**base, "state": "BLOCKED", "metrics": None, "reason": str(e)}
    except httpx.HTTPError:
        return {**base, "state": "ERROR", "metrics": None, "reason": "CrUX could not be reached."}
    if r.status_code == 404:
        return {**base, "state": "NO_DATA", "metrics": None, "reason": "CrUX has no data for this site (too little traffic)."}
    if r.status_code == 429:
        return {**base, "state": "RATE_LIMITED", "metrics": None, "reason": "CrUX quota (150/min per project) reached."}
    if r.status_code != 200:
        return {**base, "state": "ERROR", "metrics": None, "reason": f"CrUX answered HTTP {r.status_code}."}
    rec = r.json().get("record", {})
    metrics = {k: {"p75": (v.get("percentiles") or {}).get("p75"),
                   "histogram": v.get("histogram")} for k, v in (rec.get("metrics") or {}).items()}
    return {**base, "state": "OK", "metrics": metrics, "collection_period": rec.get("collectionPeriod"),
            "key": rec.get("key"), "measured_at": datetime.now(timezone.utc).isoformat()}


# ── keyword import ───────────────────────────────────────────────────────────────────────────────

def _clean(s: str) -> str:
    return re.sub(r"^[=+\-@\t\r]+", "", s.strip())[:200]     # no spreadsheet formula injection on later export


async def import_keywords(db: AsyncSession, raw: str, source: str, user: str) -> dict:
    if len(raw) > 1_000_000:
        raise CrawlError(413, "CSV larger than 1 MB.")
    if not 2 <= len((source or "").strip()) <= 60:
        raise CrawlError(422, "Name the supplier of this CSV (2-60 characters).")
    rd = csv.DictReader(io.StringIO(raw))
    cols = [h.strip().lower() for h in (rd.fieldnames or [])]
    if "keyword" not in cols or any(h not in KEYWORD_COLUMNS for h in cols):
        raise CrawlError(422, f"Header must contain 'keyword' and only these columns: {', '.join(KEYWORD_COLUMNS)}.")
    batch, ok, bad = uuid.uuid4(), 0, []
    seen = set()
    for n, row in enumerate(rd, start=2):
        if n > 5001:
            raise CrawlError(422, "At most 5000 rows per import.")
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        kw, loc = _clean(row.get("keyword", "")), (row.get("locale") or "en").lower()[:8]
        try:
            vol = int(row["volume"]) if row.get("volume") else None
            diff = float(row["difficulty"]) if row.get("difficulty") else None
            cpc = float(row["cpc"]) if row.get("cpc") else None
            if not kw or (diff is not None and not 0 <= diff <= 100) or (vol is not None and vol < 0) or (cpc is not None and cpc < 0):
                raise ValueError
        except ValueError:
            bad.append({"line": n, "reason": "invalid keyword or number"})
            continue
        if (kw.lower(), loc) in seen:
            continue
        seen.add((kw.lower(), loc))
        await db.execute(delete(M51Keyword).where(M51Keyword.keyword == kw.lower(), M51Keyword.locale == loc, M51Keyword.source == source))
        db.add(M51Keyword(keyword=kw.lower(), locale=loc, volume=vol, difficulty=diff, cpc=cpc,
                          intent=(row.get("intent") or None), source=source.strip(), batch_id=batch, imported_by=user))
        ok += 1
    await db.flush()
    return {"batch_id": str(batch), "imported": ok, "rejected": bad[:50], "rejected_count": len(bad)}


async def keyword_coverage(db: AsyncSession, crawl_id) -> list[dict]:
    """Which imported keywords appear in a crawl's titles, descriptions and headings (nothing is ranked)."""
    pages = (await db.execute(select(M51SeoPage).where(M51SeoPage.crawl_id == crawl_id))).scalars().all()
    kws = (await db.execute(select(M51Keyword).order_by(M51Keyword.volume.desc().nullslast()).limit(500))).scalars().all()
    out = []
    for k in kws:
        hit = [p.url for p in pages if k.keyword in " ".join([p.data.get("title", ""), p.data.get("description", ""),
                                                              " ".join(p.data.get("headings", []))]).lower()]
        out.append({"keyword": k.keyword, "locale": k.locale, "volume": k.volume, "pages": hit[:5], "covered": bool(hit)})
    return out


# ── competitor comparison (authorised sources or pasted text only) ───────────────────────────────

async def compare_content(db: AsyncSession, own_url: str, other_text: Optional[str], other_url: Optional[str]) -> dict:
    await allowed(db, own_url, kinds=("OWN",))
    if bool(other_text) == bool(other_url):
        raise CrawlError(422, "Give either competitor_text (pasted, from a source you may use) or competitor_url (an authorised source).")
    local = egress_mode() == "local"
    max_bytes = int(getattr(settings, "SEO_CRAWL_MAX_BYTES", 1_000_000))

    async def load(u):
        o = origin_of(u)
        async with provider_client(timeout=8.0) as c:
            try:
                got = await _get(c, u, o, local, max_bytes)
            except (FetchBlocked, EgressBlocked, httpx.HTTPError) as e:
                raise CrawlError(502, f"Could not fetch {u[:100]}: {str(e)[:100]}") from None
        if got["status"] != 200:
            raise CrawlError(502, f"{u[:100]} answered HTTP {got['status']}.")
        return parse_html(got["text"])
    mine = await load(own_url)
    if other_url:
        await allowed(db, other_url, kinds=("AUTHORIZED_SOURCE",))
        theirs = await load(other_url)
    else:
        theirs = parse_html(f"<html><body><p>{other_text[:200_000]}</p></body></html>")
    mt, tt = dict(mine["terms"]), dict(theirs["terms"])
    return {"own": {"words": mine["words"], "headings": mine["headings"]},
            "other": {"words": theirs["words"], "headings": theirs["headings"]},
            "terms_only_in_other": [t for t, _ in theirs["terms"] if t not in mt][:20],
            "terms_only_in_own": [t for t, _ in mine["terms"] if t not in tt][:20],
            "shared_terms": [t for t, _ in mine["terms"] if t in tt][:20],
            "note": "Compared only content you own or an authorised source; no ranking claims."}
