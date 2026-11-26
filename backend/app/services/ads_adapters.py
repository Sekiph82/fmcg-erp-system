"""Ad platform adapters (M44.S01.T002–T005): Meta Marketing API, Google Ads API, LinkedIn Marketing API, TikTok API for
Business. Read/report mapping, account discovery, validate-only draft checks where the platform documents one, and
error mapping. M48.S01.T001–T004 (end of file): documented campaign-tree mutation requests (create / budget update /
pause-resume / read-back / reconcile search) per provider; whether they run LIVE or SIMULATED is decided fail-closed
in ads_service, never here.

Every adapter is NOT_CONFIGURED until its token settings are filled (owner activation, M47). All traffic goes through
the provider egress guard (`provider_http`), so tests and local runs reach only the local simulator.

Normalised report row: (campaign id, name, day, impressions, clicks, spend in account currency, conversions).
Money: Meta spend is a decimal string in account currency; Google cost is micros; LinkedIn costInLocalCurrency is a
decimal string; TikTok spend is a decimal string. Drafts carry the daily budget in account currency and are converted
to each platform's unit (Meta minor units, Google micros).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings
from app.core.provider_http import provider_client

ZERO_DECIMAL = {"JPY", "KRW", "VND", "CLP", "ISK", "UGX", "RWF", "XOF", "XAF"}   # currencies without minor units


def minor_units(amount: Decimal, currency: str) -> int:
    return int(amount) if currency.upper() in ZERO_DECIMAL else int((amount * 100).to_integral_value())


MAX_PAGES = 50  # Meta paging cap per sync (M45.S01.T024)


@dataclass
class ReportRow:
    campaign_id: str
    campaign_name: str
    day: date
    impressions: int
    clicks: int
    spend: Decimal
    conversions: Decimal


class AdsError(Exception):
    """kind: NOT_CONFIGURED | AUTH | RATE_LIMIT | PERMISSION | VALIDATION | VERSION | PROVIDER | UNKNOWN.
    UNKNOWN (M48): a mutation was sent but its outcome is not known (timeout / 5xx) → reconcile by read-back."""

    def __init__(self, kind: str, message: str, retry_after: Optional[int] = None, http_status: Optional[int] = None):
        super().__init__(message)
        self.kind, self.retry_after, self.http_status = kind, retry_after, http_status


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v if v not in (None, "") else 0))
    except Exception:
        return Decimal(0)


def _retry_after(r: httpx.Response) -> Optional[int]:
    try:
        return int(r.headers.get("Retry-After", ""))
    except ValueError:
        return None


class Adapter:
    provider = ""
    supports_validate_only = False

    def configured(self) -> bool:
        raise NotImplementedError

    def _need(self) -> None:
        if not self.configured():
            raise AdsError("NOT_CONFIGURED", f"{self.provider} ads connection is not configured.")


# ── Meta Marketing API ───────────────────────────────────────────────────────

class MetaAds(Adapter):
    provider, supports_validate_only = "meta", True
    RATE_CODES, AUTH_CODES, PERM_CODES = {4, 17, 32, 613, 80000, 80004}, {190, 102}, {10, 200, 294}

    def configured(self) -> bool:
        return bool(settings.META_ADS_ACCESS_TOKEN)

    def _url(self, path: str) -> str:
        return f"{settings.META_ADS_API_URL.rstrip('/')}/{settings.META_ADS_API_VERSION}/{path.lstrip('/')}"

    def _check(self, r: httpx.Response) -> dict:
        try:
            body = r.json()
        except ValueError:
            raise AdsError("PROVIDER", f"Meta returned HTTP {r.status_code} without JSON", None, r.status_code) from None
        err = body.get("error") if isinstance(body, dict) else None
        if err or r.status_code >= 400:
            err = err or {}
            code, msg = err.get("code"), err.get("message", f"HTTP {r.status_code}")
            kind = ("AUTH" if code in self.AUTH_CODES or r.status_code == 401 else
                    "RATE_LIMIT" if code in self.RATE_CODES or r.status_code == 429 else
                    "PERMISSION" if code in self.PERM_CODES or r.status_code == 403 else
                    "VALIDATION" if code == 100 else "PROVIDER")
            raise AdsError(kind, f"Meta: {msg}", _retry_after(r), r.status_code)
        return body

    async def accounts(self) -> list[dict]:
        self._need()
        out, url = [], self._url("me/adaccounts")
        params = {"fields": "account_id,name,currency,timezone_name", "limit": 50}
        async with provider_client() as c:
            for _ in range(MAX_PAGES):          # ponytail: hard cap so a looping 'next' cannot run forever
                if not url:
                    break
                body = self._check(await c.get(url, params=params, headers=self._h()))
                out += [{"external_id": a["account_id"], "name": a.get("name"), "currency": a.get("currency"),
                         "time_zone": a.get("timezone_name")} for a in body.get("data", [])]
                url, params = body.get("paging", {}).get("next"), None
        return out

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {settings.META_ADS_ACCESS_TOKEN}"}

    async def report(self, account_id: str, since: date, until: date) -> list[ReportRow]:
        self._need()
        rows: list[ReportRow] = []
        url = self._url(f"act_{account_id}/insights")
        params = {"level": "campaign", "time_increment": 1, "limit": 500,
                  "fields": "campaign_id,campaign_name,impressions,clicks,spend,actions,date_start",
                  "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()})}
        async with provider_client() as c:
            for _ in range(MAX_PAGES):          # ponytail: hard cap so a looping 'next' cannot run forever
                if not url:
                    break
                body = self._check(await c.get(url, params=params, headers=self._h()))
                for d in body.get("data", []):
                    conv = sum((_dec(a.get("value")) for a in d.get("actions") or []
                                if a.get("action_type") in ("purchase", "lead", "offsite_conversion.fb_pixel_purchase")), Decimal(0))
                    rows.append(ReportRow(d["campaign_id"], d.get("campaign_name") or d["campaign_id"],
                                          date.fromisoformat(d["date_start"]), int(d.get("impressions") or 0),
                                          int(d.get("clicks") or 0), _dec(d.get("spend")), conv))
                url, params = body.get("paging", {}).get("next"), None
        return rows

    async def validate(self, account_id: str, draft: dict, currency: str) -> dict:
        """Meta documents execution_options=["validate_only"]: the request is checked, nothing is created."""
        self._need()
        data = {"name": draft["name"], "objective": draft["objective"], "status": "PAUSED",
                "special_ad_categories": json.dumps([]), "daily_budget": minor_units(_dec(draft["daily_budget"]), currency),
                "execution_options": json.dumps(["validate_only"])}
        async with provider_client() as c:
            body = self._check(await c.post(self._url(f"act_{account_id}/campaigns"), data=data, headers=self._h()))
        return {"provider_checked": True, "result": body}


# ── Google Ads API ──────────────────────────────────────────────────────────

class GoogleAds(Adapter):
    provider, supports_validate_only = "google", True

    def configured(self) -> bool:
        return bool(settings.GOOGLE_ADS_DEVELOPER_TOKEN and settings.GOOGLE_ADS_ACCESS_TOKEN)

    def _h(self) -> dict:
        h = {"Authorization": f"Bearer {settings.GOOGLE_ADS_ACCESS_TOKEN}",
             "developer-token": settings.GOOGLE_ADS_DEVELOPER_TOKEN}
        if settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID:
            h["login-customer-id"] = settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID.replace("-", "")
        return h

    def _url(self, path: str) -> str:
        return f"{settings.GOOGLE_ADS_API_URL.rstrip('/')}/{settings.GOOGLE_ADS_API_VERSION}/{path}"

    def _check(self, r: httpx.Response):
        try:
            body = r.json()
        except ValueError:
            raise AdsError("PROVIDER", f"Google Ads returned HTTP {r.status_code} without JSON", None, r.status_code) from None
        err = body[0].get("error") if isinstance(body, list) and body and isinstance(body[0], dict) else (
            body.get("error") if isinstance(body, dict) else None)
        if err or r.status_code >= 400:
            err = err or {}
            status = err.get("status", "")
            kind = {"UNAUTHENTICATED": "AUTH", "RESOURCE_EXHAUSTED": "RATE_LIMIT", "PERMISSION_DENIED": "PERMISSION",
                    "INVALID_ARGUMENT": "VALIDATION", "UNIMPLEMENTED": "VERSION"}.get(status, "PROVIDER")
            if r.status_code == 429:
                kind = "RATE_LIMIT"
            raise AdsError(kind, f"Google Ads: {err.get('message', status or r.status_code)}", _retry_after(r), r.status_code)
        return body

    async def _search(self, customer_id: str, query: str) -> list[dict]:
        self._need()
        async with provider_client() as c:
            body = self._check(await c.post(self._url(f"customers/{customer_id.replace('-', '')}/googleAds:searchStream"),
                                            json={"query": query}, headers=self._h()))
        return [row for batch in body for row in batch.get("results", [])]

    async def accounts(self) -> list[dict]:
        root = settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID
        if not root:
            raise AdsError("VALIDATION", "Set GOOGLE_ADS_LOGIN_CUSTOMER_ID (manager account) to list the account hierarchy.")
        rows = await self._search(root, "SELECT customer_client.id, customer_client.descriptive_name, "
                                        "customer_client.currency_code, customer_client.time_zone, customer_client.manager "
                                        "FROM customer_client")
        return [{"external_id": str(r["customerClient"]["id"]), "name": r["customerClient"].get("descriptiveName"),
                 "currency": r["customerClient"].get("currencyCode"), "time_zone": r["customerClient"].get("timeZone"),
                 "manager": bool(r["customerClient"].get("manager"))} for r in rows]

    async def report(self, account_id: str, since: date, until: date) -> list[ReportRow]:
        q = ("SELECT campaign.id, campaign.name, segments.date, metrics.impressions, metrics.clicks, "
             "metrics.cost_micros, metrics.conversions FROM campaign "
             f"WHERE segments.date BETWEEN '{since.isoformat()}' AND '{until.isoformat()}'")
        return [ReportRow(str(r["campaign"]["id"]), r["campaign"].get("name") or str(r["campaign"]["id"]),
                          date.fromisoformat(r["segments"]["date"]), int(r["metrics"].get("impressions") or 0),
                          int(r["metrics"].get("clicks") or 0), _dec(r["metrics"].get("costMicros")) / Decimal(1_000_000),
                          _dec(r["metrics"].get("conversions"))) for r in await self._search(account_id, q)]

    async def validate(self, account_id: str, draft: dict, currency: str) -> dict:
        """Google Ads mutate with validateOnly=true and partialFailure: errors come back, nothing is created."""
        self._need()
        micros = int((_dec(draft["daily_budget"]) * 1_000_000).to_integral_value())
        body = {"operations": [{"create": {"name": f"{draft['name']} budget", "amountMicros": str(micros),
                                           "deliveryMethod": "STANDARD"}}], "validateOnly": True, "partialFailure": True}
        async with provider_client() as c:
            res = self._check(await c.post(self._url(f"customers/{account_id.replace('-', '')}/campaignBudgets:mutate"),
                                           json=body, headers=self._h()))
        pf = res.get("partialFailureError") if isinstance(res, dict) else None
        return {"provider_checked": True, "ok": not pf, "partial_failure": pf}


# ── LinkedIn Marketing API ─────────────────────────────────────────────────

class LinkedInAds(Adapter):
    provider = "linkedin"
    MIN_DAILY_BUDGET_USD = Decimal(10)      # documented LinkedIn minimum daily budget

    def configured(self) -> bool:
        return bool(settings.LINKEDIN_ADS_ACCESS_TOKEN)

    def _h(self) -> dict:
        return {"Authorization": f"Bearer {settings.LINKEDIN_ADS_ACCESS_TOKEN}",
                "LinkedIn-Version": settings.LINKEDIN_ADS_VERSION, "X-Restli-Protocol-Version": "2.0.0"}

    def _check(self, r: httpx.Response) -> dict:
        if r.status_code < 400:
            return r.json() if r.content else {}          # 201 create / 204 update carry no body
        try:
            body = r.json()
        except ValueError:
            body = {}
        kind = {401: "AUTH", 403: "PERMISSION", 429: "RATE_LIMIT", 426: "VERSION", 400: "VALIDATION",
                422: "VALIDATION"}.get(r.status_code, "PROVIDER")
        raise AdsError(kind, f"LinkedIn: {body.get('message', r.status_code)}", _retry_after(r), r.status_code)

    async def accounts(self) -> list[dict]:
        self._need()
        out, start = [], 0
        async with provider_client() as c:
            while True:
                body = self._check(await c.get(f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/adAccounts",
                                               params={"q": "search", "start": start, "count": 100}, headers=self._h()))
                els = body.get("elements", [])
                out += [{"external_id": str(a["id"]), "name": a.get("name"), "currency": a.get("currency"),
                         "time_zone": None} for a in els]
                total = body.get("paging", {}).get("total", 0)
                start += len(els)
                if not els or start >= total:
                    return out

    async def report(self, account_id: str, since: date, until: date) -> list[ReportRow]:
        self._need()
        base = settings.LINKEDIN_ADS_API_URL.rstrip("/")
        acct = f"urn:li:sponsoredAccount:{account_id}"
        dr = (f"(start:(year:{since.year},month:{since.month},day:{since.day}),"
              f"end:(year:{until.year},month:{until.month},day:{until.day}))")
        async with provider_client() as c:
            names = {}
            camps = self._check(await c.get(f"{base}/rest/adAccounts/{account_id}/adCampaigns",
                                            params={"q": "search"}, headers=self._h()))
            for x in camps.get("elements", []):
                names[f"urn:li:sponsoredCampaign:{x['id']}"] = x.get("name")
            # Rest.li query parameters must not be percent-encoded twice: built by hand
            url = (f"{base}/rest/adAnalytics?q=analytics&pivot=CAMPAIGN&timeGranularity=DAILY&dateRange={dr}"
                   f"&accounts=List({acct.replace(':', '%3A')})"
                   "&fields=impressions,clicks,costInLocalCurrency,externalWebsiteConversions,dateRange,pivotValues")
            body = self._check(await c.get(url, headers=self._h()))
        rows = []
        for e in body.get("elements", []):
            s = e["dateRange"]["start"]
            urn = (e.get("pivotValues") or [""])[0]
            rows.append(ReportRow(urn.rsplit(":", 1)[-1], names.get(urn) or urn, date(s["year"], s["month"], s["day"]),
                                  int(e.get("impressions") or 0), int(e.get("clicks") or 0),
                                  _dec(e.get("costInLocalCurrency")), _dec(e.get("externalWebsiteConversions"))))
        return rows

    async def validate(self, account_id: str, draft: dict, currency: str) -> dict:
        """LinkedIn documents no validate-only call: local checks only, plus access-tier gating."""
        problems = []
        if settings.LINKEDIN_ADS_ACCESS_TIER != "standard":
            problems.append("Development access tier: campaign writes are not available until LinkedIn grants Standard tier.")
        if currency.upper() == "USD" and _dec(draft["daily_budget"]) < self.MIN_DAILY_BUDGET_USD:
            problems.append("LinkedIn's minimum daily budget is USD 10.")
        return {"provider_checked": False, "ok": not problems, "problems": problems}


# ── TikTok API for Business ────────────────────────────────────────────────

class TikTokAds(Adapter):
    provider = "tiktok"
    RATE, AUTH, PERM = {40100, 40133, 51021}, {40104, 40105, 40102}, {40001, 40300}   # M48: 40001 no permission, 40002 parameter error
    MIN_DAILY_BUDGET_USD = Decimal(50)      # documented minimum campaign daily budget

    def configured(self) -> bool:
        return bool(settings.TIKTOK_ADS_ACCESS_TOKEN)

    def _h(self) -> dict:
        return {"Access-Token": settings.TIKTOK_ADS_ACCESS_TOKEN}

    def _check(self, r: httpx.Response) -> dict:
        try:
            body = r.json()
        except ValueError:
            raise AdsError("PROVIDER", f"TikTok returned HTTP {r.status_code} without JSON", None, r.status_code) from None
        code = body.get("code", r.status_code if r.status_code >= 400 else 0)
        if code != 0:
            kind = ("RATE_LIMIT" if code in self.RATE or r.status_code == 429 else "AUTH" if code in self.AUTH else
                    "PERMISSION" if code in self.PERM else "VALIDATION" if code == 40002 else "PROVIDER")
            # TikTok answers HTTP 200 with a code; 5xxxx codes are server-side errors (outcome of a write unknown)
            raise AdsError(kind, f"TikTok: {body.get('message', code)} (code {code})", _retry_after(r),
                           500 if code >= 50000 else r.status_code)
        return body.get("data") or {}

    async def accounts(self) -> list[dict]:
        raise AdsError("VALIDATION", "TikTok advertiser ids come from the authorised app; add the account by id.")

    async def report(self, account_id: str, since: date, until: date) -> list[ReportRow]:
        self._need()
        rows, page = [], 1
        url = f"{settings.TIKTOK_ADS_API_URL.rstrip('/')}/open_api/v1.3/report/integrated/get/"
        async with provider_client() as c:
            while True:
                data = self._check(await c.get(url, headers=self._h(), params={
                    "advertiser_id": account_id, "report_type": "BASIC", "data_level": "AUCTION_CAMPAIGN",
                    "dimensions": json.dumps(["campaign_id", "stat_time_day"]),
                    "metrics": json.dumps(["campaign_name", "spend", "impressions", "clicks", "conversion"]),
                    "start_date": since.isoformat(), "end_date": until.isoformat(), "page": page, "page_size": 200}))
                for x in data.get("list", []):
                    d, m = x["dimensions"], x["metrics"]
                    rows.append(ReportRow(str(d["campaign_id"]), m.get("campaign_name") or str(d["campaign_id"]),
                                          datetime.strptime(d["stat_time_day"][:10], "%Y-%m-%d").date(),
                                          int(_dec(m.get("impressions"))), int(_dec(m.get("clicks"))),
                                          _dec(m.get("spend")), _dec(m.get("conversion"))))
                info = data.get("page_info") or {}
                if page >= int(info.get("total_page") or 1):
                    return rows
                page += 1

    async def validate(self, account_id: str, draft: dict, currency: str) -> dict:
        """No documented validate-only call: local checks only."""
        problems = budget_problems("tiktok", _dec(draft["daily_budget"]), currency)
        return {"provider_checked": False, "ok": not problems, "problems": problems}


def verify_tiktok_callback(raw: bytes, signature_header: str, now: Optional[float] = None) -> bool:
    """TikTok-Signature: t=<unix>,s=<hex HMAC-SHA256 of 't.body' with the app secret>; 5-minute window."""
    secret = settings.TIKTOK_ADS_APP_SECRET
    if not secret:
        return False
    parts = dict(p.split("=", 1) for p in (signature_header or "").split(",") if "=" in p)
    try:
        ts = int(parts.get("t", ""))
    except ValueError:
        return False
    if abs((now or time.time()) - ts) > 300:
        return False
    want = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, parts.get("s", ""))


ADAPTERS: dict[str, Adapter] = {a.provider: a for a in (MetaAds(), GoogleAds(), LinkedInAds(), TikTokAds())}


# ── M47.S01.T010 customer lists and offline conversions ─────────────────────
# Only SHA-256 hashes of normalised identifiers leave the ERP: e-mail trimmed + lower-cased; phone in E.164 (Google:
# "+254712345678") or digits with country code (Meta: "254712345678"), as each platform documents. Only people with
# marketing consent on record (SUBSCRIBED) are ever sent, checked at upload time, for audiences and conversions alike.
# Meta: Custom Audience (act_<id>/customaudiences + <audience>/users), Conversions API (<pixel>/events).
# Google: Customer Match (userLists:mutate, offlineUserDataJobs create / addOperations / run), offline conversions
# (customers/<id>:uploadClickConversions with hashed user identifiers). Extra settings: META_PIXEL_ID,
# GOOGLE_ADS_CONVERSION_ACTION (resource name); missing → NOT_CONFIGURED.
CHUNK = 5000


def _setting(name: str) -> str:
    import os
    return getattr(settings, name, "") or os.environ.get(name, "")


def sha256_hex(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def hash_email(email: Optional[str]) -> Optional[str]:
    e = (email or "").strip().lower()
    return sha256_hex(e) if "@" in e else None


def hash_phone(phone: Optional[str], plus: bool) -> Optional[str]:
    from app.services.customer_data_service import norm_phone
    p = norm_phone(phone)
    if not p:
        return None
    return sha256_hex(p if plus else p.lstrip("+"))


def _google_ids(email: Optional[str], phone: Optional[str]) -> list[dict]:
    out = []
    if hash_email(email):
        out.append({"hashedEmail": hash_email(email)})
    if hash_phone(phone, plus=True):
        out.append({"hashedPhoneNumber": hash_phone(phone, plus=True)})
    return out


async def meta_audience_upload(account_id: str, name: str, people: list[tuple[Optional[str], Optional[str]]]) -> dict:
    """people: (email, phone) in the clear → hashed here, before anything is sent."""
    a = ADAPTERS["meta"]
    a._need()
    rows = [[hash_email(e) or "", hash_phone(p, plus=False) or ""] for e, p in people]
    rows = [r for r in rows if r[0] or r[1]]
    async with provider_client() as c:
        body = a._check(await c.post(a._url(f"act_{account_id}/customaudiences"), headers=a._h(),
                                     json={"name": name[:200], "subtype": "CUSTOM", "customer_file_source": "USER_PROVIDED_ONLY",
                                           "description": "POVU ERP consented audience"}))
        aud = str(body.get("id") or "")
        if not aud:
            raise AdsError("PROVIDER", "Meta did not return an audience id.")
        for i in range(0, len(rows), CHUNK):
            a._check(await c.post(a._url(f"{aud}/users"), headers=a._h(),
                                  json={"payload": {"schema": ["EMAIL", "PHONE"], "data": rows[i:i + CHUNK]}}))
    return {"external_id": aud, "sent": len(rows)}


async def google_audience_upload(customer_id: str, name: str, people: list[tuple[Optional[str], Optional[str]]]) -> dict:
    g = ADAPTERS["google"]
    g._need()
    cid = customer_id.replace("-", "")
    ops = [{"create": {"userIdentifiers": ids}} for ids in (_google_ids(e, p) for e, p in people) if ids]
    async with provider_client() as c:
        body = g._check(await c.post(g._url(f"customers/{cid}/userLists:mutate"), headers=g._h(), json={"operations": [
            {"create": {"name": name[:200], "membershipLifeSpan": 10000, "crmBasedUserList": {"uploadKeyType": "CONTACT_INFO"}}}]}))
        lst = ((body.get("results") or [{}])[0]).get("resourceName")
        if not lst:
            raise AdsError("PROVIDER", "Google Ads did not return a user list.")
        job = g._check(await c.post(g._url(f"customers/{cid}/offlineUserDataJobs:create"), headers=g._h(), json={
            "job": {"type": "CUSTOMER_MATCH_USER_LIST", "customerMatchUserListMetadata": {"userList": lst}}})).get("resourceName")
        if not job:
            raise AdsError("PROVIDER", "Google Ads did not return an upload job.")
        for i in range(0, len(ops), CHUNK):
            g._check(await c.post(g._url(f"{job}:addOperations"), headers=g._h(), json={"operations": ops[i:i + CHUNK]}))
        g._check(await c.post(g._url(f"{job}:run"), headers=g._h(), json={}))
    return {"external_id": lst, "sent": len(ops)}


async def meta_conversions(events: list[dict]) -> int:
    """events: {id, email, phone, value, currency, at}. Purchase events; event_id lets Meta deduplicate."""
    a = ADAPTERS["meta"]
    a._need()
    pixel = _setting("META_PIXEL_ID")
    if not pixel:
        raise AdsError("NOT_CONFIGURED", "META_PIXEL_ID is not set.")
    data = []
    for ev in events:
        ud = {}
        if hash_email(ev.get("email")):
            ud["em"] = [hash_email(ev.get("email"))]
        if hash_phone(ev.get("phone"), plus=False):
            ud["ph"] = [hash_phone(ev.get("phone"), plus=False)]
        data.append({"event_name": "Purchase", "event_time": int(ev["at"].timestamp()), "action_source": "system_generated",
                     "event_id": ev["id"], "user_data": ud, "custom_data": {"currency": ev["currency"], "value": float(ev["value"])}})
    sent = 0
    async with provider_client() as c:
        for i in range(0, len(data), 1000):        # Meta: at most 1000 events per request
            body = a._check(await c.post(a._url(f"{pixel}/events"), headers=a._h(), json={"data": data[i:i + 1000]}))
            sent += int(body.get("events_received") or 0)
    return sent


async def google_conversions(customer_id: str, events: list[dict]) -> int:
    g = ADAPTERS["google"]
    g._need()
    action = _setting("GOOGLE_ADS_CONVERSION_ACTION")
    if not action:
        raise AdsError("NOT_CONFIGURED", "GOOGLE_ADS_CONVERSION_ACTION is not set.")
    convs = [{"conversionAction": action, "conversionDateTime": ev["at"].strftime("%Y-%m-%d %H:%M:%S+00:00"),
              "conversionValue": float(ev["value"]), "currencyCode": ev["currency"], "orderId": ev["id"],
              "userIdentifiers": _google_ids(ev.get("email"), ev.get("phone"))} for ev in events]
    ok = 0
    async with provider_client() as c:
        for i in range(0, len(convs), 2000):
            body = g._check(await c.post(g._url(f"customers/{customer_id.replace('-', '')}:uploadClickConversions"),
                                         headers=g._h(), json={"conversions": convs[i:i + 2000], "partialFailure": True}))
            if body.get("partialFailureError"):
                raise AdsError("VALIDATION", f"Google Ads: {body['partialFailureError'].get('message', 'partial failure')}")
            ok += len(body.get("results") or [])
    return ok


async def _account(db, provider: str):
    from sqlalchemy import select
    from app.models.crm import AdAccount
    if provider not in ("meta", "google"):
        raise AdsError("VALIDATION", "Customer lists and conversions support meta and google.")
    acct = (await db.execute(select(AdAccount).where(AdAccount.provider == provider, AdAccount.status == "ACTIVE")
                             .order_by(AdAccount.created_at))).scalars().first()
    if acct is None or not ADAPTERS[provider].configured():
        raise AdsError("NOT_CONFIGURED", f"No active {provider} ad account is connected.")
    return acct


async def upload_audience(db, audience, provider: str, user) -> dict:
    """Upload the audience's consented members (hashed) and record the upload. Does not commit."""
    from sqlalchemy import select
    from app.models.crm import MarketingAudienceMember
    from app.models.m47_platform import AdsAudienceUpload
    from app.models.sales import Customer
    from app.services import audience_service as aus
    acct = await _account(db, provider)
    rows = (await db.execute(select(MarketingAudienceMember.email, Customer.phone).join(
        Customer, Customer.id == MarketingAudienceMember.customer_id).where(MarketingAudienceMember.audience_id == audience.id))).all()
    # ad uploads always need marketing consent (SUBSCRIBED), whatever the audience's require_consent says:
    # unsubscribed, bounced, complained and never-consented people are never sent (T003 audit)
    ok = await aus._consented(db)
    people = [(e, p) for e, p in rows if (e or "").strip().lower() in ok]
    rec = AdsAudienceUpload(audience_id=audience.id, provider=provider, account_id=acct.id, status="FAILED",
                            created_by_id=getattr(user, "id", None))
    db.add(rec)
    try:
        fn = meta_audience_upload if provider == "meta" else google_audience_upload
        out = await fn(acct.external_id, f"POVU {audience.name}", people)
    except AdsError as e:
        rec.error = str(e)[:500]
        raise
    rec.status, rec.external_audience_id, rec.sent_count = "UPLOADED", out["external_id"], out["sent"]
    return {"status": "UPLOADED", "provider": provider, "external_audience_id": out["external_id"], "sent": out["sent"]}


async def conversion_events(db, since) -> list[tuple[str, dict]]:
    """Won deals and paid invoices changed since `since` whose e-mail has marketing consent: (source_type, event)."""
    from sqlalchemy import select
    from app.models.crm import CRMRecord, CRMStatus
    from app.models.sales import Customer, Invoice, InvoiceStatus
    from app.services import audience_service as aus
    ok = await aus._consented(db)
    out: list[tuple[str, dict]] = []
    for r in (await db.execute(select(CRMRecord).where(CRMRecord.status == CRMStatus.WON, CRMRecord.updated_at >= since)
                               .limit(2000))).scalars():
        if (r.contact_email or "").lower() in ok:
            out.append(("DEAL", {"id": str(r.id), "email": r.contact_email, "phone": r.contact_phone,
                                 "value": r.expected_revenue or 0, "currency": r.currency or "KES", "at": r.updated_at}))
    for i, c in (await db.execute(select(Invoice, Customer).join(Customer, Customer.id == Invoice.customer_id).where(
            Invoice.status == InvoiceStatus.PAID, Invoice.updated_at >= since).limit(2000))).all():
        if (c.email or "").lower() in ok:
            out.append(("INVOICE", {"id": str(i.id), "email": c.email, "phone": c.phone, "value": i.total_amount or 0,
                                    "currency": i.currency or "KES", "at": i.updated_at}))
    return out


async def upload_conversions(db, provider: str, since) -> dict:
    """Upload conversions not yet uploaded to this provider (one row per source in ads_conversion_uploads). No commit."""
    from datetime import timezone
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert
    from app.models.m47_platform import AdsConversionUpload
    acct = await _account(db, provider)
    done = {(t, str(i)) for t, i in (await db.execute(select(AdsConversionUpload.source_type, AdsConversionUpload.source_id)
                                                      .where(AdsConversionUpload.provider == provider,
                                                             AdsConversionUpload.status == "UPLOADED"))).all()}
    todo = [(t, ev) for t, ev in await conversion_events(db, since) if (t, ev["id"]) not in done]
    if not todo:
        return {"status": "OK", "uploaded": 0}
    for _, ev in todo:
        ev["at"] = ev["at"] if ev["at"].tzinfo else ev["at"].replace(tzinfo=timezone.utc)
    events = [e for _, e in todo]
    try:
        n = await (meta_conversions(events) if provider == "meta" else google_conversions(acct.external_id, events))
        status, err = "UPLOADED", None
    except AdsError as e:
        if e.kind == "NOT_CONFIGURED":
            raise
        n, status, err = 0, "FAILED", str(e)[:500]
    for t, ev in todo:
        await db.execute(insert(AdsConversionUpload).values(provider=provider, source_type=t, source_id=ev["id"], status=status,
                                                            error=err).on_conflict_do_update(
            constraint="uq_ads_conversion_upload", set_={"status": status, "error": err}))
    return {"status": "OK" if status == "UPLOADED" else "FAILED", "uploaded": n, "error": err}


# ── M48.S01.T001–T004 campaign mutations ────────────────────────────────────
# Request construction follows the official public contracts (checked 2026-11-26):
#  Meta Marketing API (Graph version = META_ADS_API_VERSION):
#    https://developers.facebook.com/docs/marketing-api/reference/ad-account/campaigns/
#    https://developers.facebook.com/docs/marketing-api/reference/ad-account/adsets/
#    https://developers.facebook.com/docs/marketing-api/reference/ad-account/adcreatives/
#    https://developers.facebook.com/docs/marketing-api/reference/ad-account/ads/
#    Create on act_<id>/{campaigns,adsets,adcreatives,ads}; update/read on /<object id>; status PAUSED|ACTIVE;
#    special_ad_categories required; budgets in the account currency's minor unit; execution_options validate_only.
#  Google Ads API REST (version = GOOGLE_ADS_API_VERSION):
#    https://developers.google.com/google-ads/api/rest/reference/rest  (campaignBudgets / campaigns / adGroups /
#    adGroupAds :mutate, googleAds:mutate with temporary ids, googleAds:search GAQL), validateOnly, partialFailure,
#    resource names customers/<id>/<collection>/<id>, money in micros, updates carry an updateMask.
#  LinkedIn Marketing API, versioned REST (LinkedIn-Version = LINKEDIN_ADS_VERSION; docs view li-lms-2026-11):
#    https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaign-groups
#    https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns
#    https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-creatives
#    X-Restli-Protocol-Version 2.0.0; create → 201 + x-restli-id; update = POST + X-RestLi-Method PARTIAL_UPDATE
#    {"patch":{"$set":{...}}} → 204; groups/campaigns DRAFT|PAUSED|ACTIVE, creatives intendedStatus. No validate-only
#    call is documented → local checks. Writes need the rw_ads scope and Standard access tier (refused otherwise).
#  TikTok API for Business v1.3: https://business-api.tiktok.com/portal/docs (campaign|adgroup|ad /create/,
#    /update/, /status/update/ with operation_status ENABLE|DISABLE, /get/ with filtering + page/page_size);
#    Access-Token header, advertiser_id in every call, budget in account currency, code != 0 = error.
#    Ads need uploaded assets first (video_id, identity_id); organic Content Posting is a different API (social).
# Nothing here decides LIVE vs SIMULATED: ads_service does (fail-closed). Every call goes through provider_client().

LEVELS = {"meta": ("CAMPAIGN", "ADSET", "CREATIVE", "AD"), "google": ("BUDGET", "CAMPAIGN", "ADSET", "AD"),
          "linkedin": ("CAMPAIGN", "ADSET", "AD"), "tiktok": ("CAMPAIGN", "ADSET", "AD")}
STATUS_LEVELS = ("CAMPAIGN", "ADSET", "AD")              # every provider: these carry a pause/active status
BUDGET_LEVEL = {"meta": "CAMPAIGN", "google": "BUDGET", "linkedin": "ADSET", "tiktok": "CAMPAIGN"}
# Only objectives whose full tree can be built from documented fields without pixels, apps or lead forms.
OBJECTIVES = {"meta": ("OUTCOME_AWARENESS", "OUTCOME_TRAFFIC"), "google": ("SEARCH",),
              "linkedin": ("BRAND_AWARENESS", "WEBSITE_VISIT"), "tiktok": ("REACH", "TRAFFIC")}
LEVEL_LABEL = {"meta": {"CAMPAIGN": "Campaign", "ADSET": "Ad set", "CREATIVE": "Ad creative", "AD": "Ad"},
               "google": {"BUDGET": "Campaign budget", "CAMPAIGN": "Search campaign", "ADSET": "Ad group",
                          "AD": "Responsive search ad"},
               "linkedin": {"CAMPAIGN": "Campaign group", "ADSET": "Campaign", "AD": "Creative"},
               "tiktok": {"CAMPAIGN": "Campaign", "ADSET": "Ad group", "AD": "Ad"}}
MAX_TRIES, BACKOFF = 3, 0.5          # tests set BACKOFF = 0


@dataclass
class Req:
    method: str
    url: str
    json: Optional[dict] = None
    data: Optional[dict] = None
    params: Optional[dict] = None
    headers: Optional[dict] = None

    def log(self) -> dict:
        """What the ledger stores. Credentials live only in adapter headers and are never stored."""
        return {"method": self.method, "url": self.url, "body": self.json if self.json is not None else self.data,
                "params": self.params, "headers": self.headers}


def _https(v) -> bool:
    return isinstance(v, str) and v.startswith("https://") and len(v) <= 1000


# Documented minimum DAILY budgets (M48.S01.T020). (amount, currency it is verified for; None = account currency units)
#  TikTok: campaign daily and lifetime budgets must exceed 50 USD, ad group daily 20 USD (lifetime = 20 × days):
#    https://ads.tiktok.com/help/article/budget . TikTok localises these per currency and we cannot verify the local
#    table, so the 50 is applied in ACCOUNT CURRENCY UNITS (as the simulator does). Our trees use campaign budget
#    optimisation with BUDGET_MODE_DAY, so only the campaign daily minimum applies (ad groups carry no budget).
#  LinkedIn: minimum daily budget USD 10 (documented for USD accounts only; other currencies not verified → not applied).
#  Meta: minimum depends on currency and billing event (no single figure) → the provider's validate_only checks it.
#  Google Ads: no fixed documented minimum daily budget → not applied.
MIN_DAILY = {"tiktok": (Decimal(50), None), "linkedin": (Decimal(10), "USD")}


def min_daily_budget(provider: str, currency: str) -> Optional[Decimal]:
    m = MIN_DAILY.get(provider)
    if not m or (m[1] and m[1] != currency.upper()):
        return None
    return m[0]


def budget_note(provider: str, currency: str) -> Optional[str]:
    m = MIN_DAILY.get(provider)
    if not m or (m[1] and m[1] != currency.upper()):
        return None
    if provider == "tiktok":
        return (f"TikTok minimum campaign daily budget: 50 (TikTok documents USD 50; applied as 50 {currency.upper()} "
                "because the local-currency minimum is not verified here).")
    return f"{ {'linkedin': 'LinkedIn'}.get(provider, provider)} minimum daily budget: {m[1]} {m[0]}."


def budget_problems(provider: str, budget: Decimal, currency: str) -> list[str]:
    """Below the documented minimum → refused locally, before approval. Also flags a minimum above the global
    guardrail ADS_MAX_DAILY_BUDGET (then no valid budget exists until the owner raises the guardrail)."""
    low = min_daily_budget(provider, currency)
    if low is None:
        return []
    out = []
    guard = Decimal(str(settings.ADS_MAX_DAILY_BUDGET))
    if low > guard:
        out.append(f"{budget_note(provider, currency)} This is above the global guardrail ADS_MAX_DAILY_BUDGET "
                   f"({guard}): the owner must raise the guardrail before any {provider} campaign can be valid.")
    if Decimal(budget) < low:
        out.append(f"Daily budget {budget} {currency.upper()} is below the minimum. {budget_note(provider, currency)}")
    return out


def check_spec(provider: str, objective: str, spec: dict, budget: Decimal, currency: str) -> list[str]:
    """Local checks of documented limits before anything is sent (the only check where no validate-only exists)."""
    import re
    p: list[str] = []
    if objective not in OBJECTIVES[provider]:
        p.append(f"Objective {objective} is not offered for {provider}; supported: {', '.join(OBJECTIVES[provider])}.")
    if provider == "meta":
        if not str(spec.get("page_id", "")).isdigit():
            p.append("Meta needs the Facebook Page id the ad runs from.")
        if not _https(spec.get("link")):
            p.append("Meta link must be an https URL.")
        if not str(spec.get("message") or "").strip():
            p.append("Meta ad text (message) is required.")
        if not re.fullmatch(r"[A-Za-z]{2}", str(spec.get("country", ""))):
            p.append("Meta targeting needs a 2-letter country code.")
    elif provider == "google":
        hs, ds = spec.get("headlines") or [], spec.get("descriptions") or []
        if not 3 <= len(hs) <= 15 or any(not h or len(h) > 30 for h in hs):
            p.append("Responsive search ads need 3–15 headlines of at most 30 characters.")
        if not 2 <= len(ds) <= 4 or any(not d or len(d) > 90 for d in ds):
            p.append("Responsive search ads need 2–4 descriptions of at most 90 characters.")
        if not _https(spec.get("final_url")):
            p.append("Google final URL must be an https URL.")
        if _dec(spec.get("cpc_bid")) <= 0:
            p.append("Google manual CPC bid must be positive.")
    elif provider == "linkedin":
        if not re.fullmatch(r"urn:li:(share|ugcPost):\d+", str(spec.get("share_urn", ""))):
            p.append("LinkedIn creative needs an existing post URN (urn:li:share:… or urn:li:ugcPost:…).")
        if not re.fullmatch(r"urn:li:geo:\d+", str(spec.get("geo_urn", ""))):
            p.append("LinkedIn targeting needs a location URN (urn:li:geo:…).")
        if _dec(spec.get("unit_cost")) <= 0:
            p.append("LinkedIn bid (unit cost) must be positive.")
    elif provider == "tiktok":
        locs = spec.get("location_ids") or []
        if not locs or any(not str(x).isdigit() for x in locs):
            p.append("TikTok ad group needs location ids.")
        if not str(spec.get("video_id") or "").strip() or not str(spec.get("identity_id") or "").strip():
            p.append("TikTok ads need an uploaded video_id and an identity_id (asset prerequisites).")
        if not str(spec.get("ad_text") or "").strip() or len(str(spec.get("ad_text") or "")) > 100:
            p.append("TikTok ad text is required (at most 100 characters).")
        if not _https(spec.get("landing_page_url")):
            p.append("TikTok landing page must be an https URL.")
    return p + budget_problems(provider, Decimal(budget), currency)


async def send(adapter: Adapter, req: Req, safe: bool) -> tuple[dict, httpx.Headers]:
    """One provider call with the retry policy.

    safe (read): retried with backoff on RATE_LIMIT, 5xx and timeouts.
    write: retried only on RATE_LIMIT (the provider refused it, nothing happened) or when the connection never
    opened. A 5xx or a timeout after sending → AdsError("UNKNOWN"): the caller marks the ledger UNKNOWN and
    reconciles by read-back; it never re-sends blindly."""
    import asyncio
    adapter._need()
    if not safe and adapter.provider == "linkedin" and settings.LINKEDIN_ADS_ACCESS_TIER != "standard":
        raise AdsError("PERMISSION", "LinkedIn Development tier: campaign writes need Standard tier access.")
    headers = {**adapter._h(), **(req.headers or {})}
    async with provider_client() as c:
        for attempt in range(MAX_TRIES):
            last = attempt == MAX_TRIES - 1
            wait = BACKOFF * 2 ** attempt
            try:
                r = await c.request(req.method, req.url, json=req.json, data=req.data, params=req.params, headers=headers)
            except httpx.ConnectError as e:              # never reached the provider: certainly not executed
                if not last:
                    await asyncio.sleep(wait)
                    continue
                raise AdsError("PROVIDER", f"{adapter.provider}: cannot connect ({e.__class__.__name__})") from None
            except httpx.TransportError as e:            # timeout / dropped after sending
                if safe and not last:
                    await asyncio.sleep(wait)
                    continue
                raise AdsError("PROVIDER" if safe else "UNKNOWN",
                               f"{adapter.provider}: no answer ({e.__class__.__name__})") from None
            try:
                return adapter._check(r), r.headers
            except AdsError as e:
                server = (e.http_status or 0) >= 500
                if not last and (e.kind == "RATE_LIMIT" or (safe and server)):
                    await asyncio.sleep(min(e.retry_after or wait, 30) if BACKOFF else 0)
                    continue
                if server and not safe:
                    e.kind = "UNKNOWN"
                raise
    raise AdsError("PROVIDER", "unreachable")


def _ms(d: Optional[str]) -> int:
    day = date.fromisoformat(d) if d else date.today()
    return int(datetime(day.year, day.month, day.day).timestamp() * 1000)


def _num(v: str) -> str:
    return str(v).rsplit(":", 1)[-1]


# Builders per provider. create(level, x) / status(level, pid, active, x) / budget(pid, x) / read(level, pid, x) /
# find(level, x) → Req;  parse_create / parse_read / parse_find → plain values.
# x: {"account": external id, "name": tagged name, "tag": name tag, "objective", "budget": Decimal, "currency",
#     "spec": dict, "ids": {level: provider id of the already created ancestors}}

class MetaBuild:
    EDGE = {"CAMPAIGN": "campaigns", "ADSET": "adsets", "CREATIVE": "adcreatives", "AD": "ads"}
    GOAL = {"OUTCOME_AWARENESS": "REACH", "OUTCOME_TRAFFIC": "LINK_CLICKS"}
    a = ADAPTERS["meta"]

    def create(self, level: str, x: dict, validate_only: bool = False) -> Req:
        s, acct = x["spec"], x["account"]
        if level == "CAMPAIGN":
            data = {"name": x["name"], "objective": x["objective"], "status": "PAUSED",
                    "special_ad_categories": json.dumps(s.get("special_ad_categories") or []),
                    "daily_budget": minor_units(x["budget"], x["currency"]), "bid_strategy": "LOWEST_COST_WITHOUT_CAP"}
        elif level == "ADSET":
            data = {"name": x["name"], "campaign_id": x["ids"]["CAMPAIGN"], "status": "PAUSED", "billing_event": "IMPRESSIONS",
                    "optimization_goal": self.GOAL.get(x["objective"], "REACH"),
                    "targeting": json.dumps({"geo_locations": {"countries": [str(s.get("country", "")).upper()]}}),
                    "start_time": f"{s.get('start_date') or date.today().isoformat()}T00:00:00+0300"}
        elif level == "CREATIVE":
            data = {"name": x["name"], "object_story_spec": json.dumps({"page_id": str(s.get("page_id")), "link_data": {
                "link": s.get("link"), "message": s.get("message"), "name": s.get("headline") or ""}})}
        else:
            data = {"name": x["name"], "adset_id": x["ids"]["ADSET"], "status": "PAUSED",
                    "creative": json.dumps({"creative_id": x["ids"]["CREATIVE"]})}
        if validate_only:
            data["execution_options"] = json.dumps(["validate_only"])
        return Req("POST", self.a._url(f"act_{acct}/{self.EDGE[level]}"), data=data)

    def parse_create(self, level: str, body: dict, headers) -> str:
        if not body.get("id"):
            raise AdsError("PROVIDER", "Meta did not return an object id.")
        return str(body["id"])

    def status(self, level: str, pid: str, active: bool, x: dict) -> Req:
        return Req("POST", self.a._url(pid), data={"status": "ACTIVE" if active else "PAUSED"})

    def budget(self, pid: str, x: dict) -> Req:
        return Req("POST", self.a._url(pid), data={"daily_budget": minor_units(x["budget"], x["currency"])})

    def read(self, level: str, pid: str, x: dict) -> Req:
        f = "id,name,status" if level == "CREATIVE" else "id,name,status,effective_status" + (
            ",daily_budget" if level == "CAMPAIGN" else "")
        return Req("GET", self.a._url(pid), params={"fields": f})

    def parse_read(self, level: str, body: dict, x: dict) -> dict:
        b = body.get("daily_budget")
        return {"status": body.get("effective_status") or body.get("status"), "configured": body.get("status"),
                "budget_ok": None if b in (None, "") else int(b) == minor_units(x["budget"], x["currency"])}

    def find(self, level: str, x: dict) -> Req:
        return Req("GET", self.a._url(f"act_{x['account']}/{self.EDGE[level]}"), params={
            "fields": "id,name,status", "filtering": json.dumps([{"field": "name", "operator": "CONTAIN", "value": x["tag"]}])})

    def parse_find(self, level: str, body: dict, x: dict) -> Optional[str]:
        hit = [d for d in body.get("data", []) if x["tag"] in (d.get("name") or "")]
        return str(hit[0]["id"]) if hit else None


class GoogleBuild:
    SVC = {"BUDGET": "campaignBudgets", "CAMPAIGN": "campaigns", "ADSET": "adGroups", "AD": "adGroupAds"}
    GAQL = {"BUDGET": "campaign_budget", "CAMPAIGN": "campaign", "ADSET": "ad_group", "AD": "ad_group_ad"}
    KEY = {"BUDGET": "campaignBudget", "CAMPAIGN": "campaign", "ADSET": "adGroup", "AD": "adGroupAd"}
    OP = {"BUDGET": "campaignBudgetOperation", "CAMPAIGN": "campaignOperation", "ADSET": "adGroupOperation",
          "AD": "adGroupAdOperation"}
    a = ADAPTERS["google"]

    @staticmethod
    def _cid(x: dict) -> str:
        return x["account"].replace("-", "")

    @staticmethod
    def _version() -> int:
        try:
            return int(str(settings.GOOGLE_ADS_API_VERSION).lstrip("v").split(".")[0])
        except ValueError:
            return 0

    @staticmethod
    def _micros(v) -> str:
        return str(int((_dec(v) * 1_000_000).to_integral_value()))

    def resource(self, level: str, x: dict) -> dict:
        s, ids = x["spec"], x["ids"]
        if level == "BUDGET":
            return {"name": x["name"], "amountMicros": self._micros(x["budget"]), "deliveryMethod": "STANDARD",
                    "explicitlyShared": False}
        if level == "CAMPAIGN":
            c = {"name": x["name"], "status": "PAUSED", "advertisingChannelType": "SEARCH", "campaignBudget": ids["BUDGET"],
                 "manualCpc": {}, "networkSettings": {"targetGoogleSearch": True, "targetSearchNetwork": False,
                                                       "targetContentNetwork": False, "targetPartnerSearchNetwork": False}}
            if self._version() >= 20:     # EU political-advertising declaration required for new campaigns (v20+)
                c["containsEuPoliticalAdvertising"] = "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING"
            return c
        if level == "ADSET":
            return {"name": x["name"], "campaign": ids["CAMPAIGN"], "status": "PAUSED", "type": "SEARCH_STANDARD",
                    "cpcBidMicros": self._micros(s.get("cpc_bid"))}
        return {"adGroup": ids["ADSET"], "status": "PAUSED", "ad": {
            "finalUrls": [s.get("final_url")], "responsiveSearchAd": {
                "headlines": [{"text": h} for h in s.get("headlines") or []],
                "descriptions": [{"text": d} for d in s.get("descriptions") or []]}}}

    def create(self, level: str, x: dict) -> Req:
        return Req("POST", self.a._url(f"customers/{self._cid(x)}/{self.SVC[level]}:mutate"),
                   json={"operations": [{"create": self.resource(level, x)}], "partialFailure": True})

    def validate_tree(self, x: dict, names: dict) -> Req:
        """googleAds:mutate with validateOnly and temporary (negative) resource ids chaining the creates.
        Google checks the whole tree; nothing is created."""
        cid = self._cid(x)
        ids = {lv: f"customers/{cid}/{self.SVC[lv]}/-{i + 1}" for i, lv in enumerate(("BUDGET", "CAMPAIGN", "ADSET"))}
        ops = []
        for lv in LEVELS["google"]:
            res = self.resource(lv, {**x, "ids": ids, "name": names[lv]})
            if lv in ids:
                res["resourceName"] = ids[lv]
            ops.append({self.OP[lv]: {"create": res}})
        return Req("POST", self.a._url(f"customers/{cid}/googleAds:mutate"), json={"mutateOperations": ops, "validateOnly": True})

    def parse_create(self, level: str, body: dict, headers) -> str:
        pf = body.get("partialFailureError")
        if pf:   # one operation per request: a partial failure means that operation failed and nothing was created
            raise AdsError("VALIDATION", f"Google Ads: {pf.get('message', 'operation failed')}")
        rn = ((body.get("results") or [{}])[0]).get("resourceName")
        if not rn:
            raise AdsError("PROVIDER", "Google Ads did not return a resource name.")
        return rn

    def status(self, level: str, pid: str, active: bool, x: dict) -> Req:
        return Req("POST", self.a._url(f"customers/{self._cid(x)}/{self.SVC[level]}:mutate"), json={"operations": [
            {"update": {"resourceName": pid, "status": "ENABLED" if active else "PAUSED"}, "updateMask": "status"}],
            "partialFailure": True})

    def budget(self, pid: str, x: dict) -> Req:
        return Req("POST", self.a._url(f"customers/{self._cid(x)}/campaignBudgets:mutate"), json={"operations": [
            {"update": {"resourceName": pid, "amountMicros": self._micros(x["budget"])}, "updateMask": "amountMicros"}],
            "partialFailure": True})

    def _search(self, x: dict, q: str) -> Req:
        return Req("POST", self.a._url(f"customers/{self._cid(x)}/googleAds:search"), json={"query": q})

    def read(self, level: str, pid: str, x: dict) -> Req:
        r = self.GAQL[level]
        extra = ", campaign_budget.amount_micros" if level == "BUDGET" else ""
        return self._search(x, f"SELECT {r}.resource_name, {r}.status{extra} FROM {r} WHERE {r}.resource_name = '{pid}'")

    def parse_read(self, level: str, body: dict, x: dict) -> dict:
        row = ((body.get("results") or [{}])[0]).get(self.KEY[level]) or {}
        m = row.get("amountMicros")
        return {"status": row.get("status"), "configured": row.get("status"),
                "budget_ok": None if not m else str(m) == self._micros(x["budget"])}

    def find(self, level: str, x: dict) -> Req:
        r = self.GAQL[level]
        if level == "AD":     # responsive search ads carry no name: it is the only ad in our ad group
            return self._search(x, f"SELECT {r}.resource_name, {r}.status FROM {r} WHERE {r}.ad_group = '{x['ids']['ADSET']}'")
        return self._search(x, f"SELECT {r}.resource_name, {r}.name FROM {r} WHERE {r}.name LIKE '%{x['tag']}%'")

    def parse_find(self, level: str, body: dict, x: dict) -> Optional[str]:
        rows = [(row.get(self.KEY[level]) or {}).get("resourceName") for row in body.get("results") or []]
        return next((r for r in rows if r), None)


class LinkedInBuild:
    COLL = {"CAMPAIGN": "adCampaignGroups", "ADSET": "adCampaigns", "AD": "creatives"}
    COST = {"BRAND_AWARENESS": "CPM", "WEBSITE_VISIT": "CPC"}
    PATCH = {"X-RestLi-Method": "PARTIAL_UPDATE"}

    @staticmethod
    def _base(acct: str) -> str:
        return f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/adAccounts/{acct}"

    def _path(self, level: str, pid: str, x: dict) -> str:
        from urllib.parse import quote
        return f"{self._base(x['account'])}/{self.COLL[level]}/{quote(pid, safe='')}"

    def create(self, level: str, x: dict) -> Req:
        s, acct, cur = x["spec"], x["account"], x["currency"].upper()
        start = {"start": _ms(s.get("start_date"))}
        if level == "CAMPAIGN":
            body = {"account": f"urn:li:sponsoredAccount:{acct}", "name": x["name"], "status": "DRAFT", "runSchedule": start}
        elif level == "ADSET":
            body = {"account": f"urn:li:sponsoredAccount:{acct}", "name": x["name"], "status": "DRAFT",
                    "campaignGroup": f"urn:li:sponsoredCampaignGroup:{_num(x['ids']['CAMPAIGN'])}",
                    "type": "SPONSORED_UPDATES", "costType": self.COST.get(x["objective"], "CPM"),
                    "objectiveType": x["objective"], "politicalIntent": "NOT_POLITICAL",
                    "dailyBudget": {"amount": str(x["budget"]), "currencyCode": cur},
                    "unitCost": {"amount": str(_dec(s.get("unit_cost"))), "currencyCode": cur},
                    "locale": {"country": "US", "language": "en"}, "offsiteDeliveryEnabled": False,
                    "audienceExpansionEnabled": False, "runSchedule": start,
                    "targetingCriteria": {"include": {"and": [{"or": {"urn:li:adTargetingFacet:locations": [s.get("geo_urn")]}}]}}}
        else:
            body = {"campaign": f"urn:li:sponsoredCampaign:{_num(x['ids']['ADSET'])}",
                    "content": {"reference": s.get("share_urn")}, "intendedStatus": "DRAFT"}
        return Req("POST", f"{self._base(acct)}/{self.COLL[level]}", json=body)

    def parse_create(self, level: str, body: dict, headers) -> str:
        rid = headers.get("x-restli-id") or headers.get("x-linkedin-id")
        if not rid:
            raise AdsError("PROVIDER", "LinkedIn did not return x-restli-id.")
        return rid

    def status(self, level: str, pid: str, active: bool, x: dict) -> Req:
        field = "intendedStatus" if level == "AD" else "status"
        return Req("POST", self._path(level, pid, x), headers=self.PATCH,
                   json={"patch": {"$set": {field: "ACTIVE" if active else "PAUSED"}}})

    def budget(self, pid: str, x: dict) -> Req:
        return Req("POST", self._path("ADSET", pid, x), headers=self.PATCH, json={"patch": {"$set": {
            "dailyBudget": {"amount": str(x["budget"]), "currencyCode": x["currency"].upper()}}}})

    def read(self, level: str, pid: str, x: dict) -> Req:
        return Req("GET", self._path(level, pid, x))

    def parse_read(self, level: str, body: dict, x: dict) -> dict:
        st = body.get("intendedStatus") if level == "AD" else body.get("status")
        serving = body.get("servingStatuses") or ([] if level != "AD" else (["SERVING"] if body.get("isServing") else []))
        amt = (body.get("dailyBudget") or {}).get("amount")
        status = f"{st} ({', '.join(serving)})" if serving else st
        return {"status": status, "configured": st, "budget_ok": None if amt is None else _dec(amt) == x["budget"]}

    def find(self, level: str, x: dict) -> Req:
        from urllib.parse import quote
        base = self._base(x["account"])
        if level == "CAMPAIGN":       # Rest.li query syntax: built by hand so it is not encoded twice
            url = f"{base}/adCampaignGroups?q=search&search=(name:(values:List({quote(x['name'], safe='')})))"
        elif level == "ADSET":
            g = quote(f"urn:li:sponsoredCampaignGroup:{_num(x['ids']['CAMPAIGN'])}", safe="")
            url = f"{base}/adCampaigns?q=search&search=(campaignGroup:(values:List({g})))"
        else:
            cm = quote(f"urn:li:sponsoredCampaign:{_num(x['ids']['ADSET'])}", safe="")
            url = f"{base}/creatives?q=criteria&campaigns=List({cm})"
        return Req("GET", url)

    def parse_find(self, level: str, body: dict, x: dict) -> Optional[str]:
        els = [e for e in body.get("elements", []) if level == "AD" or x["tag"] in (e.get("name") or "")]
        return str(els[0]["id"]) if els else None


class TikTokBuild:
    KIND = {"CAMPAIGN": "campaign", "ADSET": "adgroup", "AD": "ad"}
    GOAL = {"REACH": ("REACH", "CPM"), "TRAFFIC": ("CLICK", "CPC")}

    @staticmethod
    def _url(path: str) -> str:
        return f"{settings.TIKTOK_ADS_API_URL.rstrip('/')}/open_api/v1.3/{path}"

    def create(self, level: str, x: dict) -> Req:
        s, adv = x["spec"], x["account"]
        if level == "CAMPAIGN":
            body = {"advertiser_id": adv, "campaign_name": x["name"], "objective_type": x["objective"],
                    "budget_optimize_on": True, "budget_mode": "BUDGET_MODE_DAY", "budget": float(x["budget"]),
                    "operation_status": "DISABLE"}
        elif level == "ADSET":
            goal, billing = self.GOAL.get(x["objective"], ("REACH", "CPM"))
            body = {"advertiser_id": adv, "campaign_id": x["ids"]["CAMPAIGN"], "adgroup_name": x["name"],
                    "placement_type": "PLACEMENT_TYPE_AUTOMATIC", "location_ids": [str(v) for v in s.get("location_ids") or []],
                    "schedule_type": "SCHEDULE_FROM_NOW",
                    "schedule_start_time": f"{s.get('start_date') or date.today().isoformat()} 00:00:00",
                    "optimization_goal": goal, "billing_event": billing, "bid_type": "BID_TYPE_NO_BID",
                    "pacing": "PACING_MODE_SMOOTH", "operation_status": "DISABLE"}
            if x["objective"] == "TRAFFIC":
                body["promotion_type"] = "WEBSITE"
        else:
            body = {"advertiser_id": adv, "adgroup_id": x["ids"]["ADSET"], "operation_status": "DISABLE", "creatives": [{
                "ad_name": x["name"], "ad_format": "SINGLE_VIDEO", "video_id": s.get("video_id"),
                "identity_type": "CUSTOMIZED_USER", "identity_id": s.get("identity_id"), "ad_text": s.get("ad_text"),
                "call_to_action": "LEARN_MORE", "landing_page_url": s.get("landing_page_url")}]}
        return Req("POST", self._url(f"{self.KIND[level]}/create/"), json=body)

    def parse_create(self, level: str, data: dict, headers) -> str:
        pid = (data.get("ad_ids") or [None])[0] if level == "AD" else data.get(f"{self.KIND[level]}_id")
        if not pid:
            raise AdsError("PROVIDER", "TikTok did not return an id.")
        return str(pid)

    def status(self, level: str, pid: str, active: bool, x: dict) -> Req:
        k = self.KIND[level]
        return Req("POST", self._url(f"{k}/status/update/"), json={
            "advertiser_id": x["account"], f"{k}_ids": [pid], "operation_status": "ENABLE" if active else "DISABLE"})

    def budget(self, pid: str, x: dict) -> Req:
        return Req("POST", self._url("campaign/update/"), json={"advertiser_id": x["account"], "campaign_id": pid,
                                                                  "budget": float(x["budget"])})

    def read(self, level: str, pid: str, x: dict) -> Req:
        k = self.KIND[level]
        return Req("GET", self._url(f"{k}/get/"), params={"advertiser_id": x["account"],
                                                         "filtering": json.dumps({f"{k}_ids": [pid]})})

    def parse_read(self, level: str, data: dict, x: dict) -> dict:
        row = (data.get("list") or [{}])[0]
        st = row.get("operation_status")
        sec = row.get("secondary_status")
        return {"status": f"{st} ({sec})" if sec else st, "configured": st,
                "budget_ok": None if row.get("budget") is None else _dec(row["budget"]) == x["budget"]}

    def find(self, level: str, x: dict, page: int = 1) -> Req:
        k = self.KIND[level]
        flt = {} if level == "CAMPAIGN" else ({"campaign_ids": [x["ids"]["CAMPAIGN"]]} if level == "ADSET"
                                              else {"adgroup_ids": [x["ids"]["ADSET"]]})
        return Req("GET", self._url(f"{k}/get/"), params={"advertiser_id": x["account"], "filtering": json.dumps(flt),
                                                         "page": page, "page_size": 100})

    def parse_find(self, level: str, data: dict, x: dict) -> Optional[str]:
        k = self.KIND[level]
        for row in data.get("list") or []:
            if level != "CAMPAIGN" or x["tag"] in (row.get("campaign_name") or ""):
                return str(row.get(f"{k}_id"))
        return None


BUILDERS = {"meta": MetaBuild(), "google": GoogleBuild(), "linkedin": LinkedInBuild(), "tiktok": TikTokBuild()}


async def find_created(provider: str, level: str, x: dict) -> Optional[str]:
    """Read-back used to reconcile an UNKNOWN create. TikTok campaign lists are paged (page_info.total_page)."""
    a, b = ADAPTERS[provider], BUILDERS[provider]
    if provider == "tiktok" and level == "CAMPAIGN":
        for page in range(1, MAX_PAGES + 1):
            data, _ = await send(a, b.find(level, x, page), safe=True)
            hit = b.parse_find(level, data, x)
            if hit or page >= int((data.get("page_info") or {}).get("total_page") or 1):
                return hit
        return None
    body, _ = await send(a, b.find(level, x), safe=True)
    return b.parse_find(level, body, x)
