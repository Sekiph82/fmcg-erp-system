"""M50.S01.T002 authorized web search + SSRF-safe page fetch + fact extraction/verification.

Official contract used (Brave Search API, Web Search endpoint; docs checked 2026-11-26):
  https://api-dashboard.search.brave.com/app/documentation/web-search/query   (API base /res/v1/)
  GET https://api.search.brave.com/res/v1/web/search   header ``X-Subscription-Token: <key>``  (``Accept: application/json``)
  params: q, country (2 letters), search_lang, count (max 20), offset (0-based page, max 9), safesearch, freshness;
  response: ``web.results[] {title, url, description}``, ``query.more_results_available`` (check before paging).
  Errors: 401/403 bad key or plan, 422 invalid parameter, 429 rate limited (``Retry-After`` / ``X-RateLimit-*`` headers).
Nothing is scraped: pages are fetched only from URLs a search result (or a person) names, one URL per request, with
the controls below. Every outbound request goes through provider_http.provider_client (PROVIDER_EGRESS=local reaches
local simulators only).

Settings read with getattr: BRAVE_SEARCH_API_KEY (str, ""), BRAVE_SEARCH_BASE_URL (str, official URL),
M50_FETCH_MAX_BYTES (int, 1_000_000), M50_FETCH_TIMEOUT (float, 8), M50_FETCH_MAX_REDIRECTS (int, 3).
Search stays NOT_CONFIGURED until a key exists AND the owner enabled it AND confirmed a licence (m50_provider_settings).
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, egress_mode, provider_client
from app.models.m50_prospecting import M50ProviderSetting, M50ResearchDoc, M50ResearchQuery

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
SECRET_PARAMS = re.compile(r"(token|key|secret|sig|signature|auth|password|session|code)", re.I)


class ResearchError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


class FetchBlocked(Exception):
    """The fetch policy refused the URL or the response; nothing was stored from it."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── settings / state ─────────────────────────────────────────────────────────

async def get_setting(db: AsyncSession, kind: str) -> M50ProviderSetting:
    row = await db.get(M50ProviderSetting, kind)
    if row is None:
        row = M50ProviderSetting(kind=kind, provider="", enabled=False, licensed=False, retention_days=30, config={})
        db.add(row)
        await db.flush()
    return row


async def search_state(db: AsyncSession) -> dict:
    row = await get_setting(db, "SEARCH")
    key = bool(getattr(settings, "BRAVE_SEARCH_API_KEY", ""))
    reasons = []
    if not key:
        reasons.append("No search API key is configured (BRAVE_SEARCH_API_KEY).")
    if not row.enabled:
        reasons.append("Search is switched off in settings.")
    if not row.licensed:
        reasons.append("The owner has not confirmed a licence for search results.")
    return {"state": "OK" if not reasons else "NOT_CONFIGURED", "provider": "brave", "reasons": reasons,
            "retention_days": row.retention_days, "license_note": row.license_note, "egress": egress_mode()}


# ── search adapter ───────────────────────────────────────────────────────────

def redact_url(url: str) -> str:
    """Drop credential-looking query values and any user:password part before a URL is stored or shown."""
    p = urlsplit(url)
    q = [(k, "REDACTED" if SECRET_PARAMS.search(k) else v) for k, v in parse_qsl(p.query, keep_blank_values=True)]
    host = p.hostname or ""
    netloc = host + (f":{p.port}" if p.port else "")
    return urlunsplit((p.scheme, netloc, p.path, urlencode(q), ""))[:1000]


async def _brave_get(params: dict) -> dict:
    base = getattr(settings, "BRAVE_SEARCH_BASE_URL", "") or BRAVE_URL
    headers = {"Accept": "application/json", "X-Subscription-Token": getattr(settings, "BRAVE_SEARCH_API_KEY", "")}
    last = "Search provider unavailable."
    async with provider_client(timeout=10.0) as c:
        for attempt in range(3):                       # retry 429 / 5xx with backoff; reads are idempotent
            try:
                r = await c.get(base, params=params, headers=headers)
            except EgressBlocked as e:
                raise ResearchError(503, f"Blocked by egress policy: {e}") from None
            except httpx.HTTPError:
                last = "Search provider unreachable."
            else:
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (401, 403):
                    raise ResearchError(502, "The search provider rejected the API key or plan.")
                if r.status_code == 422:
                    raise ResearchError(422, "The search provider rejected the query parameters.")
                last = "Search provider rate limit reached." if r.status_code == 429 else f"Search provider error {r.status_code}."
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ResearchError(502, last)
                wait = min(float(r.headers.get("Retry-After", 0) or 0), 2.0)
                await asyncio.sleep(max(wait, 0.2 * 2 ** attempt))
                continue
            await asyncio.sleep(0.2 * 2 ** attempt)
    raise ResearchError(502, last)


async def search(db: AsyncSession, q: str, user: str, *, country: Optional[str] = None, lang: Optional[str] = None,
                 page: int = 0, count: int = 10) -> M50ResearchQuery:
    st = await search_state(db)
    if st["state"] != "OK":
        raise ResearchError(409, "Search is not configured: " + " ".join(st["reasons"]))
    q = q.strip()
    if not q or len(q) > 400:
        raise ResearchError(422, "Query must be 1-400 characters.")
    if not 0 <= page <= 9:
        raise ResearchError(422, "Page must be 0-9 (provider limit).")
    row = await get_setting(db, "SEARCH")
    cfg = row.config or {}
    params = {"q": q, "count": max(1, min(count, 20)), "offset": page, "safesearch": "moderate"}
    country = (country or cfg.get("country") or "").upper() or None
    lang = lang or cfg.get("search_lang") or None
    if country:
        params["country"] = country
    if lang:
        params["search_lang"] = lang
    rec = M50ResearchQuery(provider="brave", query=q, country=country, search_lang=lang, page=page, results=[],
                           status="OK", created_by=user, expires_at=_now() + timedelta(days=row.retention_days))
    try:
        data = await _brave_get(params)
        res = (data.get("web") or {}).get("results") or []
        rec.results = [{"rank": page * params["count"] + i + 1, "title": str(x.get("title", ""))[:300],
                        "url": redact_url(str(x.get("url", ""))), "description": re.sub(r"<[^>]+>", "", str(x.get("description", "")))[:500]}
                       for i, x in enumerate(res) if x.get("url")]
        rec.more_available = bool((data.get("query") or {}).get("more_results_available")) and page < 9
    except ResearchError as e:
        rec.status, rec.error = "ERROR", str(e)[:300]
        db.add(rec)
        await db.flush()
        raise
    db.add(rec)
    await db.flush()
    return rec


# ── SSRF-safe fetch ──────────────────────────────────────────────────────────

def _resolve(host: str) -> list[str]:
    return [i[4][0].split("%")[0] for i in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)]


async def check_url(url: str, *, local: bool) -> None:
    """Scheme allow-list, no credentials in the URL, and every resolved address must be public (loopback is allowed
    only when ``local`` = PROVIDER_EGRESS=local, where the egress guard in turn permits loopback hosts only)."""
    p = urlsplit(url)
    if p.scheme not in ("http", "https"):
        raise FetchBlocked(f"Scheme {p.scheme or '(none)'} is not allowed.")
    if p.username or p.password:
        raise FetchBlocked("URLs with credentials are not allowed.")
    if not p.hostname:
        raise FetchBlocked("URL has no host.")
    if not local and p.port not in (None, 80, 443):
        raise FetchBlocked("Only ports 80 and 443 are allowed.")
    try:
        ips = await asyncio.to_thread(_resolve, p.hostname)
    except OSError:
        raise FetchBlocked(f"Cannot resolve {p.hostname}.") from None
    for raw in ips:
        ip = ipaddress.ip_address(raw)
        if local and ip.is_loopback:
            continue
        if not ip.is_global or ip.is_multicast:
            raise FetchBlocked(f"{p.hostname} resolves to a non-public address; refused.")


async def safe_fetch(url: str) -> dict:
    """GET one page. Returns {final_url, content_type, size, text}; raises FetchBlocked on any policy violation.
    Redirects are followed manually and every hop is checked again."""
    max_bytes = int(getattr(settings, "M50_FETCH_MAX_BYTES", 1_000_000))
    timeout = float(getattr(settings, "M50_FETCH_TIMEOUT", 8))
    hops = int(getattr(settings, "M50_FETCH_MAX_REDIRECTS", 3))
    if egress_mode() == "off":
        raise FetchBlocked("Blocked by egress policy: provider traffic is switched off.")
    local = egress_mode() == "local"
    cur = url
    async with provider_client(timeout=timeout) as c:
        for _ in range(hops + 1):
            await check_url(cur, local=local)
            try:
                async with c.stream("GET", cur, headers={"Accept": "text/html,text/plain;q=0.8", "User-Agent": "POVU-ERP-research/1.0"}) as r:
                    if r.status_code in (301, 302, 303, 307, 308):
                        loc = r.headers.get("location")
                        if not loc:
                            raise FetchBlocked("Redirect without a location.")
                        cur = urljoin(cur, loc)
                        continue
                    if r.status_code != 200:
                        raise FetchBlocked(f"Page answered HTTP {r.status_code}.")
                    ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                    if ctype not in ALLOWED_TYPES:
                        raise FetchBlocked(f"Content type {ctype or '(none)'} is not allowed.")
                    if int(r.headers.get("content-length") or 0) > max_bytes:
                        raise FetchBlocked("Page is larger than the size limit.")
                    buf = bytearray()
                    async for chunk in r.aiter_bytes():
                        buf += chunk
                        if len(buf) > max_bytes:
                            raise FetchBlocked("Page is larger than the size limit.")
                    return {"final_url": redact_url(cur), "content_type": ctype, "size": len(buf),
                            "text": bytes(buf).decode(r.encoding or "utf-8", errors="replace")}
            except EgressBlocked as e:
                raise FetchBlocked(f"Blocked by egress policy: {e}") from None
            except httpx.TimeoutException:
                raise FetchBlocked("Page took too long to answer.") from None
            except httpx.HTTPError:
                raise FetchBlocked("Page could not be fetched.") from None
    raise FetchBlocked("Too many redirects.")


# ── extraction and verification ──────────────────────────────────────────────

def extract_facts(html: str, url: str) -> tuple[Optional[str], list[dict]]:
    """(title, facts). Facts come only from schema.org JSON-LD organisation data, tel:/mailto: links and the title;
    nothing is inferred from free text."""
    from app.services.customer_data_service import norm_email, norm_phone
    facts: list[dict] = []

    def add(field, value, snippet):
        if value and not any(f["field"] == field and f["value"] == value for f in facts):
            facts.append({"field": field, "value": str(value)[:300], "snippet": snippet[:200]})
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []):
            if not isinstance(node, dict) or node.get("@type") not in ("Organization", "LocalBusiness", "Store", "Corporation"):
                continue
            add("name", node.get("name"), "JSON-LD name")
            add("phone", norm_phone(str(node.get("telephone") or "")), "JSON-LD telephone")
            add("email", norm_email(str(node.get("email") or "")), "JSON-LD email")
            add("website", node.get("url"), "JSON-LD url")
            a = node.get("address") if isinstance(node.get("address"), dict) else {}
            add("city", a.get("addressLocality"), "JSON-LD addressLocality")
            add("region", a.get("addressRegion"), "JSON-LD addressRegion")
    for m in re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.I):
        add("phone", norm_phone(m), "tel: link")
    for m in re.findall(r'href=["\']mailto:([^"\'?]+)', html, re.I):
        add("email", norm_email(m), "mailto: link")
    t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return (re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t.group(1))).strip()[:300] if t else None), facts


async def fetch_and_store(db: AsyncSession, url: str, user: str, query_id=None) -> M50ResearchDoc:
    row = await get_setting(db, "SEARCH")
    doc = M50ResearchDoc(query_id=query_id, url=redact_url(url), status="FETCHED", facts=[], created_by=user,
                         expires_at=_now() + timedelta(days=row.retention_days))
    if not (row.licensed and row.enabled):
        raise ResearchError(409, "Fetching needs research enabled and the licence confirmed in settings.")
    try:
        got = await safe_fetch(url)
        doc.final_url, doc.content_type, doc.size_bytes = got["final_url"], got["content_type"], got["size"]
        doc.title, doc.facts = extract_facts(got["text"], got["final_url"])
    except FetchBlocked as e:
        doc.status, doc.reason = "BLOCKED", str(e)[:300]
    db.add(doc)
    await db.flush()
    return doc


def reconcile(docs: list[M50ResearchDoc]) -> list[dict]:
    """Per field: values with their sources and a verdict. CORROBORATED = >=2 pages agree; CONFLICT = values differ;
    SINGLE_SOURCE = one page; UNKNOWN fields are listed so the person sees what is missing."""
    out = []
    for field in ("name", "phone", "email", "website", "city", "region"):
        vals: dict[str, set] = {}
        for d in docs:
            if d.status != "FETCHED":
                continue
            for f in d.facts:
                if f["field"] == field:
                    vals.setdefault(f["value"].lower() if field != "name" else f["value"], set()).add(d.final_url or d.url)
        if not vals:
            out.append({"field": field, "verdict": "UNKNOWN", "values": []})
            continue
        verdict = "CONFLICT" if len(vals) > 1 else ("CORROBORATED" if len(next(iter(vals.values()))) > 1 else "SINGLE_SOURCE")
        out.append({"field": field, "verdict": verdict, "values": [{"value": v, "sources": sorted(s)} for v, s in vals.items()]})
    return out


async def purge_expired(db: AsyncSession) -> int:
    n = 0
    for model in (M50ResearchDoc, M50ResearchQuery):
        n += (await db.execute(delete(model).where(model.expires_at < _now()))).rowcount or 0
    return n
