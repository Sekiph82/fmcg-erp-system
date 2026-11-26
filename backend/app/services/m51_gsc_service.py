"""M51.S01.T003 Google Search Console adapter (Search Analytics, sites, sitemaps, URL Inspection).

Official contracts (docs fetched 2026-11-26):
- Search Analytics: POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query
  https://developers.google.com/webmaster-tools/v1/searchanalytics/query   (Search Console API v3)
  body startDate/endDate (YYYY-MM-DD, PT), dimensions (country alpha-3, device, page, query, searchAppearance, date, hour),
  type, dimensionFilterGroups[{groupType: and, filters[{dimension, operator, expression}]}], aggregationType,
  rowLimit 1..25000 (default 1000), startRow (0-based), dataState final|all|hourly_all.
  Response rows[{keys, clicks, impressions, ctr, position}], responseAggregationType, metadata.first_incomplete_date.
- Sites: GET /webmasters/v3/sites → siteEntry[{siteUrl, permissionLevel}]
- Sitemaps: GET /sites/{siteUrl}/sitemaps, GET .../sitemaps/{feedpath}, PUT .../sitemaps/{feedpath} (scope webmasters, empty body)
  https://developers.google.com/webmaster-tools/v1/sitemaps/submit
- URL Inspection: POST https://searchconsole.googleapis.com/v1/urlInspection/index:inspect {inspectionUrl, siteUrl, languageCode}
  https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect   (result field list is on a separate
  reference page that was not fetched: fields are passed through, only a few well-known ones are summarised)
Scopes: webmasters.readonly for reads, webmasters for sitemap submission (OAuth purposes searchconsole / searchconsole_edit).
The docs state no numeric quota for these methods; 429 and 5xx are retried with backoff and, when still failing, the
last stored snapshot for the same query is returned labelled STALE. Nothing is invented: no connection → NOT_CONFIGURED.

Settings (getattr): GSC_API_BASE (str, official), GSC_INSPECT_URL (str, official), M51_BACKOFF_BASE (float, 0.5 s).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, _is_local_host, provider_client
from app.models.m51_seo import M51GscSnapshot, M51GscSubmission
from app.models.oauth_connection import OAuthConnection
from app.services import oauth_service as oauth

API_BASE = "https://www.googleapis.com/webmasters/v3"
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
DIMENSIONS = ("query", "page", "country", "device", "date", "searchAppearance")
DATA_STATES = ("final", "all")
SEARCH_TYPES = ("web", "image", "video", "news", "discover", "googleNews")
OPERATORS = ("contains", "equals", "notContains", "notEquals", "includingRegex", "excludingRegex")
PURPOSES = ("searchconsole_edit", "searchconsole")
MAX_ROWS_PER_CALL = 25_000
MAX_TOTAL_ROWS = 50_000


class GscError(Exception):
    def __init__(self, status: int, message: str, code: str = "gsc_error"):
        super().__init__(message)
        self.status, self.code = status, code


def _base() -> str:
    return (getattr(settings, "GSC_API_BASE", "") or API_BASE).rstrip("/")


def source_label() -> str:
    from urllib.parse import urlsplit
    return "LOCAL_SIMULATOR" if _is_local_host(urlsplit(_base()).hostname or "") else "LIVE"


async def connection(db: AsyncSession, user_id, write: bool = False) -> Optional[OAuthConnection]:
    for purpose in (("searchconsole_edit",) if write else PURPOSES):
        c = (await db.execute(select(OAuthConnection).where(
            OAuthConnection.user_id == user_id, OAuthConnection.provider == "google",
            OAuthConnection.purpose == purpose, OAuthConnection.status == "CONNECTED"))).scalar_one_or_none()
        if c:
            return c
    return None


async def state(db: AsyncSession, user_id) -> dict:
    reasons = []
    ro, rw = await connection(db, user_id), await connection(db, user_id, write=True)
    if ro is None and not oauth.is_configured("google"):
        reasons.append("Google OAuth client id/secret are not configured (GOOGLE_OAUTH_CLIENT_ID / _SECRET).")
    if ro is None:
        reasons.append("No Google account is connected for Search Console (connect it first).")
    return {"state": "OK" if not reasons else "NOT_CONFIGURED", "reasons": reasons, "source": source_label(),
            "can_read": ro is not None, "can_submit_sitemaps": rw is not None,
            "account": ro.account_email if ro else None}


async def _call(db: AsyncSession, conn: OAuthConnection, method: str, url: str, body: Optional[dict] = None) -> dict:
    base = float(getattr(settings, "M51_BACKOFF_BASE", 0.5))
    last = (502, "Search Console is unavailable.")
    for attempt in range(3):
        try:
            token = await oauth.access_token(db, conn)
        except oauth.OAuthError as e:
            raise GscError(409, str(e), e.code) from None
        try:
            async with provider_client(timeout=20.0) as c:
                r = await c.request(method, url, json=body, headers={"Authorization": f"Bearer {token}"})
        except EgressBlocked as e:
            raise GscError(503, f"Blocked by egress policy: {e}", "egress_blocked") from None
        except httpx.HTTPError:
            last = (503, "Search Console could not be reached.")
            await asyncio.sleep(base * 2 ** attempt)
            continue
        if r.status_code in (200, 204):
            try:
                return r.json() if r.content else {}
            except ValueError:
                raise GscError(502, "Unreadable Search Console response.", "bad_response") from None
        if r.status_code == 401:
            raise GscError(409, "Google rejected the stored token; reconnect the account.", "reauth_required")
        if r.status_code == 403:
            raise GscError(403, "This Google account has no permission for that property or action.", "permission_denied")
        if r.status_code in (400, 404):
            msg = ""
            try:
                msg = str((r.json().get("error") or {}).get("message", ""))[:200]
            except ValueError:
                pass
            raise GscError(r.status_code, f"Search Console refused the request: {msg}", "invalid_request")
        if r.status_code in (429, 500, 502, 503, 504):
            last = (429 if r.status_code == 429 else 502, "Search Console quota or service limit reached."
                    if r.status_code == 429 else f"Search Console error {r.status_code}.")
            ra = r.headers.get("Retry-After", "")
            await asyncio.sleep(max(min(float(ra) if ra.replace(".", "", 1).isdigit() else 0, 2.0), base * 2 ** attempt))
            continue
        raise GscError(502, f"Unexpected Search Console status {r.status_code}.")
    raise GscError(last[0], last[1], "quota" if last[0] == 429 else "unavailable")


def _site(site_url: str) -> str:
    if not re.match(r"^(https?://[^\s]+/|sc-domain:[A-Za-z0-9.-]+)$", site_url or ""):
        raise GscError(422, "Property must be a URL-prefix ending in / or sc-domain:example.com.", "bad_site")
    return quote(site_url, safe="")


async def list_sites(db: AsyncSession, conn) -> list[dict]:
    data = await _call(db, conn, "GET", f"{_base()}/sites")
    return [{"site_url": s.get("siteUrl"), "permission": s.get("permissionLevel")} for s in data.get("siteEntry", [])]


def build_query(start: str, end: str, dimensions: list[str], filters: list[dict], row_limit: int, start_row: int,
                data_state: str, search_type: str) -> dict:
    try:
        d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise GscError(422, "Dates must be YYYY-MM-DD.", "bad_dates") from None
    if d0 > d1 or (d1 - d0).days > 500:
        raise GscError(422, "Start must not be after end and the range is at most 500 days.", "bad_dates")
    if len(set(dimensions)) != len(dimensions) or any(x not in DIMENSIONS for x in dimensions) or len(dimensions) > 5:
        raise GscError(422, f"Dimensions must be unique values of {', '.join(DIMENSIONS)}.", "bad_dimensions")
    if data_state not in DATA_STATES or search_type not in SEARCH_TYPES:
        raise GscError(422, "Unsupported dataState or type.", "bad_params")
    if not 1 <= row_limit <= MAX_ROWS_PER_CALL or start_row < 0:
        raise GscError(422, "rowLimit is 1-25000 and startRow is not negative.", "bad_params")
    body: dict = {"startDate": start, "endDate": end, "dimensions": dimensions, "rowLimit": row_limit,
                  "startRow": start_row, "dataState": data_state, "type": search_type}
    if filters:
        fs = []
        for f in filters[:10]:
            if f.get("dimension") not in DIMENSIONS or f.get("operator", "equals") not in OPERATORS \
                    or not str(f.get("expression", ""))[:4096]:
                raise GscError(422, "Invalid dimension filter.", "bad_filter")
            if f["dimension"] == "country" and not re.fullmatch(r"[A-Za-z]{3}", str(f["expression"])):
                raise GscError(422, "country filters use ISO 3166-1 alpha-3 codes (e.g. KEN).", "bad_filter")
            fs.append({"dimension": f["dimension"], "operator": f.get("operator", "equals"), "expression": str(f["expression"])})
        body["dimensionFilterGroups"] = [{"groupType": "and", "filters": fs}]
    return body


async def analytics(db: AsyncSession, conn, user: str, site_url: str, body: dict, paginate: bool = False) -> dict:
    """Run the query (pagination with startRow when ``paginate``), store a snapshot, answer with provenance. On a
    provider quota/availability failure the newest stored snapshot for the same query is returned as STALE."""
    phash = hashlib.sha256(json.dumps({"s": site_url, "b": {k: v for k, v in body.items() if k != "startRow"}},
                                      sort_keys=True).encode()).hexdigest()
    url = f"{_base()}/sites/{_site(site_url)}/searchAnalytics/query"
    rows: list = []
    meta, agg = None, None
    try:
        req = dict(body)
        while True:
            data = await _call(db, conn, "POST", url, req)
            got = data.get("rows") or []
            rows += got
            meta, agg = data.get("metadata") or meta, data.get("responseAggregationType") or agg
            if not paginate or len(got) < req["rowLimit"] or len(rows) >= MAX_TOTAL_ROWS:
                break
            req["startRow"] = req["startRow"] + len(got)
    except GscError as e:
        if e.code in ("quota", "unavailable"):
            prev = (await db.execute(select(M51GscSnapshot).where(
                M51GscSnapshot.params_hash == phash, M51GscSnapshot.source == source_label())
                .order_by(M51GscSnapshot.fetched_at.desc()).limit(1))).scalars().first()
            if prev is not None:
                return {"rows": prev.rows, "row_count": prev.row_count, "stale": True, "stale_reason": str(e),
                        "fetched_at": prev.fetched_at.isoformat(), "source": prev.source, "data_state": prev.data_state,
                        "metadata": prev.metadata_}
        raise
    snap = M51GscSnapshot(site_url=site_url, params_hash=phash, params=body, rows=rows, row_count=len(rows),
                          data_state=body["dataState"], source=source_label(), metadata_=meta, created_by=user)
    db.add(snap)
    await db.flush()
    await db.refresh(snap)
    return {"rows": rows, "row_count": len(rows), "stale": False, "fetched_at": snap.fetched_at.isoformat(),
            "source": snap.source, "data_state": snap.data_state, "metadata": meta, "aggregation": agg,
            "incomplete_from": (meta or {}).get("first_incomplete_date"),
            "note": "Rows are exactly what Search Console returned; nothing is estimated."}


async def sitemaps(db: AsyncSession, conn, site_url: str) -> list[dict]:
    data = await _call(db, conn, "GET", f"{_base()}/sites/{_site(site_url)}/sitemaps")
    return data.get("sitemap", [])


async def sitemap_status(db: AsyncSession, conn, site_url: str, feedpath: str) -> dict:
    return await _call(db, conn, "GET", f"{_base()}/sites/{_site(site_url)}/sitemaps/{quote(feedpath, safe='')}")


def _feedpath(site_url: str, feedpath: str) -> str:
    if not re.match(r"^https?://[^\s]+$", feedpath or "") or len(feedpath) > 1000:
        raise GscError(422, "The sitemap must be a full http(s) URL.", "bad_feedpath")
    return feedpath


async def request_submission(db: AsyncSession, user: str, site_url: str, feedpath: str) -> M51GscSubmission:
    _site(site_url)
    row = M51GscSubmission(site_url=site_url, feedpath=_feedpath(site_url, feedpath), requested_by=user)
    db.add(row)
    await db.flush()
    return row


async def decide_submission(db: AsyncSession, row: M51GscSubmission, approver: str, approve: bool, conn) -> M51GscSubmission:
    if row.status != "PENDING":
        raise GscError(409, "Already decided.", "decided")
    if approver == row.requested_by:
        raise GscError(403, "A second person must approve a sitemap submission.", "two_person")
    row.decided_by, row.decided_at = approver, datetime.now(timezone.utc)
    if not approve:
        row.status = "REJECTED"
        return row
    row.source = source_label()
    try:
        await _call(db, conn, "PUT", f"{_base()}/sites/{_site(row.site_url)}/sitemaps/{quote(row.feedpath, safe='')}")
        row.status, row.result = "SUBMITTED", "Accepted by Search Console (status: read it with Sitemap status)."
    except GscError as e:
        row.status, row.result = "FAILED", str(e)[:480]
    return row


async def inspect_url(db: AsyncSession, conn, site_url: str, url: str, lang: str = "en-US") -> dict:
    _site(site_url)
    if not re.match(r"^https?://[^\s]+$", url or ""):
        raise GscError(422, "Inspection URL must be a full http(s) URL.", "bad_url")
    api = getattr(settings, "GSC_INSPECT_URL", "") or INSPECT_URL
    data = await _call(db, conn, "POST", api, {"inspectionUrl": url, "siteUrl": site_url, "languageCode": lang})
    res = data.get("inspectionResult") or {}
    idx = res.get("indexStatusResult") or {}
    return {"source": source_label(), "inspection_result": res,
            "summary": {k: idx.get(k) for k in ("verdict", "coverageState", "robotsTxtState", "indexingState",
                                                "lastCrawlTime", "pageFetchState", "googleCanonical", "userCanonical")}}
