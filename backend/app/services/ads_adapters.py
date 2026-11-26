"""Ad platform adapters (M44.S01.T002–T005): Meta Marketing API, Google Ads API, LinkedIn Marketing API, TikTok API for
Business. Read/report mapping, account discovery, validate-only draft checks where the platform documents one, and
error mapping. Nothing here creates or publishes a live campaign.

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
    """kind: NOT_CONFIGURED | AUTH | RATE_LIMIT | PERMISSION | VALIDATION | VERSION | PROVIDER"""

    def __init__(self, kind: str, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.kind, self.retry_after = kind, retry_after


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
            raise AdsError("PROVIDER", f"Meta returned HTTP {r.status_code} without JSON") from None
        err = body.get("error") if isinstance(body, dict) else None
        if err or r.status_code >= 400:
            err = err or {}
            code, msg = err.get("code"), err.get("message", f"HTTP {r.status_code}")
            kind = ("AUTH" if code in self.AUTH_CODES or r.status_code == 401 else
                    "RATE_LIMIT" if code in self.RATE_CODES or r.status_code == 429 else
                    "PERMISSION" if code in self.PERM_CODES or r.status_code == 403 else
                    "VALIDATION" if code == 100 else "PROVIDER")
            raise AdsError(kind, f"Meta: {msg}", _retry_after(r))
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
            raise AdsError("PROVIDER", f"Google Ads returned HTTP {r.status_code} without JSON") from None
        err = body[0].get("error") if isinstance(body, list) and body and isinstance(body[0], dict) else (
            body.get("error") if isinstance(body, dict) else None)
        if err or r.status_code >= 400:
            err = err or {}
            status = err.get("status", "")
            kind = {"UNAUTHENTICATED": "AUTH", "RESOURCE_EXHAUSTED": "RATE_LIMIT", "PERMISSION_DENIED": "PERMISSION",
                    "INVALID_ARGUMENT": "VALIDATION", "UNIMPLEMENTED": "VERSION"}.get(status, "PROVIDER")
            if r.status_code == 429:
                kind = "RATE_LIMIT"
            raise AdsError(kind, f"Google Ads: {err.get('message', status or r.status_code)}", _retry_after(r))
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
            return r.json()
        try:
            body = r.json()
        except ValueError:
            body = {}
        kind = {401: "AUTH", 403: "PERMISSION", 429: "RATE_LIMIT", 426: "VERSION", 400: "VALIDATION",
                422: "VALIDATION"}.get(r.status_code, "PROVIDER")
        raise AdsError(kind, f"LinkedIn: {body.get('message', r.status_code)}", _retry_after(r))

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
    RATE, AUTH, PERM = {40100, 40133, 51021}, {40104, 40105, 40102}, {40002, 40300}
    MIN_DAILY_BUDGET_USD = Decimal(50)      # documented minimum campaign daily budget

    def configured(self) -> bool:
        return bool(settings.TIKTOK_ADS_ACCESS_TOKEN)

    def _h(self) -> dict:
        return {"Access-Token": settings.TIKTOK_ADS_ACCESS_TOKEN}

    def _check(self, r: httpx.Response) -> dict:
        try:
            body = r.json()
        except ValueError:
            raise AdsError("PROVIDER", f"TikTok returned HTTP {r.status_code} without JSON") from None
        code = body.get("code", r.status_code if r.status_code >= 400 else 0)
        if code != 0:
            kind = ("RATE_LIMIT" if code in self.RATE or r.status_code == 429 else "AUTH" if code in self.AUTH else
                    "PERMISSION" if code in self.PERM else "VALIDATION" if code == 40001 else "PROVIDER")
            raise AdsError(kind, f"TikTok: {body.get('message', code)} (code {code})", _retry_after(r))
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
        problems = []
        if currency.upper() == "USD" and _dec(draft["daily_budget"]) < self.MIN_DAILY_BUDGET_USD:
            problems.append("TikTok's minimum campaign daily budget is USD 50.")
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
