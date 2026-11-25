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
            while url:
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
            while url:
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
