"""Audience (customer list) lifecycle requests per ad platform (M49.S01.T011): create, add / remove members, status poll,
delete and (Meta only) lookalike. Only SHA-256 hashes ever reach this module; the retry / idempotency / error mapping is
`ads_adapters.send` (writes are never re-sent after an unknown outcome; add / remove are idempotent at the provider).

Official contracts (checked 2026-11-26):
 Meta Marketing API v27.0 custom audiences: https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences
   POST act_<id>/customaudiences, POST|DELETE <audience>/users (<=10,000 per request, session batching), DELETE <audience>,
   GET <audience>?fields=operation_status,delivery_status,approximate_count_*;
   lookalike: https://developers.facebook.com/docs/marketing-api/audiences/guides/lookalike-audiences  (seed >= 100 members,
   lookalike_spec.ratio 0.01-0.20; country / location_spec are not accepted from v27.0).
 Google Data Manager API v1 (Customer Match is closed to new Ads API projects since 2026-04-01):
   https://developers.google.com/data-manager/api/reference/rest/v1/audienceMembers/ingest  (POST
   https://datamanager.googleapis.com/v1/audienceMembers:ingest, <=10,000 members, encoding HEX, termsOfService ACCEPTED).
   UNVERIFIED (reference pages not readable here): the :remove body, requestStatus:retrieve response names and closing a
   user list with membershipStatus CLOSED. The user list itself is created with Google Ads API userLists:mutate.
 LinkedIn Matched Audiences (docs view li-lms-2026-11, Linkedin-Version 202611):
   https://learn.microsoft.com/en-us/linkedin/marketing/matched-audiences/create-and-manage-segments
   https://learn.microsoft.com/en-us/linkedin/marketing/matched-audiences/create-and-manage-segment-users
   POST /rest/dmpSegments, POST /rest/dmpSegments/<id>/users (X-RestLi-Method BATCH_CREATE, <=5,000, ADD|REMOVE,
   SHA256_EMAIL), wait 5 s after creation, GET / DELETE /rest/dmpSegments/<id>. No lookalike API is documented.
 TikTok API for Business v1.3: https://business-api.tiktok.com/portal/docs/upload-an-audience-file/v1.3 and update-an-audience/v1.3
   file upload (SHA256 CSV, header email_SHA256 / phone_SHA256) -> /dmp/custom_audience/create/ and /update/ (APPEND |
   REMOVE | REPLACE; resulting size < 1,000 fails; 24 updates per audience per rolling 24 h). UNVERIFIED: exact field names of
   /dmp/custom_audience/get/ and /delete/ (page bodies not readable here) and any lookalike API (none used).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
from typing import Optional
from urllib.parse import quote

from app.core.config import settings
from app.core.provider_http import provider_client
from app.services.ads_adapters import ADAPTERS, AdsError, Req, _setting, send

META_BATCH, GOOGLE_BATCH, LI_BATCH = 10_000, 10_000, 5_000
LI_WAIT = 5            # seconds the docs ask to wait after a segment is created (tests set 0)
# Documented minimum list sizes. blocking = the provider refuses / cannot serve below it (documented);
# non-blocking figures are informational only.
MINIMUMS = {"meta": (100, False, "Meta needs a lookalike seed of at least 100 members; ads delivery on small lists is not guaranteed."),
            "google": (1000, False, "Google Ads commonly needs 1,000 matched users to serve on Search/Display (UNVERIFIED in the capability matrix)."),
            "linkedin": (300, False, "LinkedIn: a campaign needs a target audience of at least 300 members (documented)."),
            "tiktok": (1000, True, "TikTok: an audience update fails if the resulting size is below 1,000 (documented).")}
CAPS = {  # what each provider's public API allows (T011)
    "meta": {"create": True, "add": True, "remove": True, "delete": True, "status": True, "lookalike": True, "conversions": True},
    "google": {"create": True, "add": True, "remove": True, "delete": True, "status": True, "lookalike": False, "conversions": True},
    "linkedin": {"create": True, "add": True, "remove": True, "delete": True, "status": True, "lookalike": False, "conversions": False},
    "tiktok": {"create": True, "add": True, "remove": True, "delete": True, "status": True, "lookalike": False, "conversions": False}}
NOTES = {"google": "Lookalike / similar segments are not offered through the Data Manager API; delete closes the list (UNVERIFIED).",
         "linkedin": "No lookalike or conversion upload is implemented (conversions API details UNVERIFIED).",
         "tiktok": "No lookalike is implemented (API UNVERIFIED); conversion events (/event/track/) are not implemented here.",
         "meta": "Conversion upload is the M47 Conversions API path."}


def _adapter(provider: str):
    a = ADAPTERS[provider]
    a._need()
    return a


def _li(path: str) -> str:
    return f"{settings.LINKEDIN_ADS_API_URL.rstrip('/')}/rest/{path}"


def _tt(path: str) -> str:
    return f"{settings.TIKTOK_ADS_API_URL.rstrip('/')}/open_api/v1.3/{path}"


def _dm(path: str) -> str:
    return f"{(_setting('GOOGLE_DATA_MANAGER_API_URL') or 'https://datamanager.googleapis.com').rstrip('/')}/v1/{path}"


def _gdest(acct: str, list_id: str) -> dict:
    d = {"operatingAccount": {"accountType": "GOOGLE_ADS", "accountId": acct.replace("-", "")}, "productDestinationId": list_id}
    login = (settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID or "").replace("-", "")
    if login:
        d["loginAccount"] = {"accountType": "GOOGLE_ADS", "accountId": login}
    return d


def _chunks(rows: list, n: int):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


async def create(provider: str, acct: str, name: str) -> tuple[str, Optional[str]]:
    """Create the empty list on the platform; returns (external id, request id)."""
    a = _adapter(provider)
    if provider == "meta":
        body, _ = await send(a, Req("POST", a._url(f"act_{acct}/customaudiences"), json={
            "name": name[:200], "subtype": "CUSTOM", "customer_file_source": "USER_PROVIDED_ONLY",
            "description": "POVU ERP consented audience"}), safe=False)
        ext = str(body.get("id") or "")
    elif provider == "google":
        body, _ = await send(a, Req("POST", a._url(f"customers/{acct.replace('-', '')}/userLists:mutate"), json={"operations": [
            {"create": {"name": name[:200], "membershipLifeSpan": 10000, "crmBasedUserList": {"uploadKeyType": "CONTACT_INFO"}}}]}),
            safe=False)
        ext = ((body.get("results") or [{}])[0]).get("resourceName") or ""
    elif provider == "linkedin":
        _, headers = await send(a, Req("POST", _li("dmpSegments"), json={
            "name": name[:200], "sourcePlatform": "DIRECT_API", "account": f"urn:li:sponsoredAccount:{acct}", "type": "USER",
            "destinations": [{"destination": "LINKEDIN"}]}), safe=False)
        ext = headers.get("x-restli-id") or ""
        if LI_WAIT:
            await asyncio.sleep(LI_WAIT)
    else:   # tiktok: a list exists only once a file is uploaded, so it is created with its first members
        return "", None
    if not ext:
        raise AdsError("UNKNOWN", f"{provider} did not return an audience id: reconcile before sending again.")
    return ext, None


async def add(provider: str, acct: str, ext: str, members: list[dict], name: str = "") -> tuple[str, Optional[str]]:
    """members: [{"e": email hash, "p": phone hash (+E.164), "pn": phone hash (digits)}]. Returns (external id, request id)."""
    return await _members(provider, acct, ext, members, "ADD", name)


async def remove(provider: str, acct: str, ext: str, members: list[dict]) -> tuple[str, Optional[str]]:
    return await _members(provider, acct, ext, members, "REMOVE", "")


async def _members(provider: str, acct: str, ext: str, members: list[dict], action: str, name: str) -> tuple[str, Optional[str]]:
    a, job = _adapter(provider), None
    if not members:
        return ext, None
    if provider == "meta":
        session = random.randint(1, 2**31)
        parts = list(_chunks(members, META_BATCH))
        for i, part in enumerate(parts):
            payload = {"schema": ["EMAIL", "PHONE"], "data": [[m["e"] or "", m.get("pn") or ""] for m in part]}
            body = {"payload": payload}
            if len(parts) > 1:
                body["session"] = {"session_id": session, "batch_seq": i + 1, "last_batch_flag": i == len(parts) - 1,
                                   "estimated_num_total": len(members)}
            await send(a, Req("POST" if action == "ADD" else "DELETE", a._url(f"{ext}/users"), json=body), safe=False)
    elif provider == "google":
        if action == "ADD" and str(_setting("GOOGLE_CUSTOMER_MATCH_TOS_ACCEPTED")).strip().lower() not in ("1", "true", "yes", "on"):
            raise AdsError("PERMISSION", "Google Customer Match terms are not accepted (GOOGLE_CUSTOMER_MATCH_TOS_ACCEPTED): "
                                         "an owner must accept them in Google Ads first. Nothing was sent.")
        dest = _gdest(acct, ext.rsplit("/", 1)[-1])
        for part in _chunks(members, GOOGLE_BATCH):
            ams = []
            for m in part:
                ids = [{"emailAddress": m["e"]}] + ([{"phoneNumber": m["p"]}] if m.get("p") else [])
                am = {"userData": {"userIdentifiers": ids}}
                if action == "ADD":
                    am["consent"] = {"adUserData": "CONSENT_GRANTED", "adPersonalization": "CONSENT_GRANTED"}
                ams.append(am)
            body = {"destinations": [dest], "audienceMembers": ams, "encoding": "HEX"}
            if action == "ADD":
                body["termsOfService"] = {"customerMatchTermsOfServiceStatus": "ACCEPTED"}
            out, _ = await send(a, Req("POST", _dm("audienceMembers:ingest" if action == "ADD" else "audienceMembers:remove"),
                                       json=body), safe=False)
            job = out.get("requestId") or job
    elif provider == "linkedin":
        for part in _chunks(members, LI_BATCH):
            out, _ = await send(a, Req("POST", _li(f"dmpSegments/{ext}/users"), headers={"X-RestLi-Method": "BATCH_CREATE"},
                                       json={"elements": [{"action": action, "userIds": [{"idType": "SHA256_EMAIL", "idValue": m["e"]}]}
                                                          for m in part]}), safe=False)
            bad = [i for i, el in enumerate(out.get("elements") or []) if int(el.get("status") or 201) >= 400]
            if bad:
                raise AdsError("VALIDATION", f"LinkedIn rejected {len(bad)} element(s) (batchIndex {bad[:5]}).")
    else:   # tiktok: upload a hashed CSV, then create (first time) or update (APPEND | REMOVE)
        path = await _tt_upload(a, acct, members)
        if action == "ADD" and not ext:
            out, _ = await send(a, Req("POST", _tt("dmp/custom_audience/create/"), json={
                "advertiser_id": acct, "custom_audience_name": name[:100], "file_paths": [path]}), safe=False)
            ext = str(out.get("custom_audience_id") or "")
            if not ext:
                raise AdsError("UNKNOWN", "TikTok did not return a custom audience id: reconcile before sending again.")
        else:
            await send(a, Req("POST", _tt("dmp/custom_audience/update/"), json={
                "advertiser_id": acct, "custom_audience_id": ext, "file_paths": [path],
                "action": "APPEND" if action == "ADD" else "REMOVE"}), safe=False)
    return ext, job


async def _tt_upload(a, acct: str, members: list[dict]) -> str:
    csv = "email_SHA256,phone_SHA256\n" + "".join(f"{m['e']},{m.get('p') or ''}\n" for m in members)
    raw = csv.encode()
    try:
        async with provider_client() as c:
            r = await c.post(_tt("dmp/custom_audience/file/upload/"), headers=a._h(), data={
                "advertiser_id": acct, "file_signature": hashlib.md5(raw).hexdigest()},
                files={"file": ("povu-audience.csv", raw, "text/csv")})
    except Exception as e:                      # upload creates nothing durable: a failure is a plain failure
        if isinstance(e, AdsError):
            raise
        raise AdsError("PROVIDER", f"TikTok file upload failed ({e.__class__.__name__}).") from None
    path = a._check(r).get("file_path")
    if not path:
        raise AdsError("PROVIDER", "TikTok did not return a file_path.")
    return path


async def delete(provider: str, acct: str, ext: str) -> None:
    a = _adapter(provider)
    if provider == "meta":
        await send(a, Req("DELETE", a._url(ext)), safe=False)
    elif provider == "google":    # UNVERIFIED: a user list is closed, not removed
        await send(a, Req("POST", a._url(f"customers/{acct.replace('-', '')}/userLists:mutate"), json={"operations": [
            {"update": {"resourceName": ext, "membershipStatus": "CLOSED"}, "updateMask": "membershipStatus"}]}), safe=False)
    elif provider == "linkedin":
        await send(a, Req("DELETE", _li(f"dmpSegments/{ext}")), safe=False)
    else:
        await send(a, Req("POST", _tt("dmp/custom_audience/delete/"), json={"advertiser_id": acct, "custom_audience_ids": [ext]}),
                   safe=False)


async def status(provider: str, acct: str, ext: str, job: Optional[str]) -> dict:
    """Provider read-back → {"state": READY | PROCESSING | FAILED, "size": int | None, "detail": str}."""
    a = _adapter(provider)
    if provider == "meta":
        b, _ = await send(a, Req("GET", a._url(ext), params={
            "fields": "operation_status,delivery_status,approximate_count_lower_bound"}), safe=True)
        op, dl = (b.get("operation_status") or {}), (b.get("delivery_status") or {})
        size = b.get("approximate_count_lower_bound")
        state = "FAILED" if op.get("code") == 471 else "READY" if dl.get("code") == 200 else "PROCESSING"
        return {"state": state, "size": size if isinstance(size, int) and size >= 0 else None,
                "detail": f"operation {op.get('code')} {op.get('description', '')}; delivery {dl.get('code')} {dl.get('description', '')}".strip()}
    if provider == "google":
        if not job:
            return {"state": "PROCESSING", "size": None, "detail": "No ingest request sent yet."}
        b, _ = await send(a, Req("GET", _dm("requestStatus:retrieve"), params={"requestId": job}), safe=True)
        sts = [str(x.get("requestStatus") or "") for x in b.get("requestStatusPerDestination") or []]
        state = ("FAILED" if any(s in ("FAILED", "CLIENT_ERROR", "CANCELLED") for s in sts) else
                 "READY" if sts and all(s in ("SUCCESS", "PARTIAL_SUCCESS") for s in sts) else "PROCESSING")
        return {"state": state, "size": None, "detail": f"request {job}: {', '.join(sts) or 'no status yet'}"
                                                         " (list matching can take hours; size is not reported here)"}
    if provider == "linkedin":
        b, _ = await send(a, Req("GET", _li(f"dmpSegments/{quote(ext, safe='')}")), safe=True)
        st = str(((b.get("destinations") or [{}])[0]).get("status") or "")
        state = "FAILED" if st in ("FAILED", "ERROR") else "READY" if st == "READY" else "PROCESSING"
        return {"state": state, "size": None, "detail": f"destination {st or 'unknown'}, inputCount {b.get('inputCount')}"}
    b, _ = await send(a, Req("GET", _tt("dmp/custom_audience/get/"), params={
        "advertiser_id": acct, "custom_audience_ids": json.dumps([ext])}), safe=True)
    row = (b.get("list") or [{}])[0]
    ok = bool(row.get("is_valid"))
    return {"state": "READY" if ok else "PROCESSING", "size": row.get("cover_num"),
            "detail": f"is_valid={row.get('is_valid')} cover_num={row.get('cover_num')} (processing takes 30-60 min)"}


async def lookalike(provider: str, acct: str, name: str, origin_ext: str, ratio: float) -> str:
    """Meta only (documented). Other providers have no lookalike API we may call."""
    if not CAPS[provider]["lookalike"]:
        raise AdsError("VALIDATION", f"{provider} has no documented lookalike API: nothing is created. {NOTES.get(provider, '')}")
    a = _adapter(provider)
    body, _ = await send(a, Req("POST", a._url(f"act_{acct}/customaudiences"), json={
        "name": name[:200], "subtype": "LOOKALIKE", "origin_audience_id": origin_ext,
        "lookalike_spec": {"ratio": ratio}}), safe=False)
    if not body.get("id"):
        raise AdsError("UNKNOWN", "Meta did not return the lookalike audience id: reconcile before sending again.")
    return str(body["id"])


async def find(provider: str, acct: str, name: str) -> Optional[str]:
    """Read-back for an UNKNOWN create: the audience with our exact name (Meta, LinkedIn). Google / TikTok: no lookup here."""
    a = _adapter(provider)
    if provider == "meta":
        b, _ = await send(a, Req("GET", a._url(f"act_{acct}/customaudiences"), params={"fields": "id,name", "limit": 200}), safe=True)
        return next((str(x["id"]) for x in b.get("data") or [] if x.get("name") == name), None)
    if provider == "linkedin":
        b, _ = await send(a, Req("GET", _li(f"dmpSegments?q=account&account={quote(f'urn:li:sponsoredAccount:{acct}', safe='')}")), safe=True)
        return next((str(x["id"]) for x in b.get("elements") or [] if x.get("name") == name), None)
    return None
