"""M48.S01.T009 provider e-signature adapters: DocuSign eSignature REST v2.1 and Adobe Acrobat Sign REST v6.

Official contracts used (read 2026-11-26):
- DocuSign JWT Grant: https://developers.docusign.com/platform/auth/jwt/jwt-get-token/
  RS256 assertion {iss: integration key, sub: user GUID, aud: account[-d].docusign.com, iat, exp, scope "signature
  impersonation"} → POST /oauth/token (grant_type urn:ietf:params:oauth:grant-type:jwt-bearer); GET /oauth/userinfo →
  accounts[{account_id, is_default, base_uri}]; error consent_required.
- DocuSign eSignature REST API v2.1 (https://developers.docusign.com/docs/esign-rest-api/reference/envelopes/):
  POST /restapi/v2.1/accounts/{accountId}/envelopes (documents[].documentBase64, recipients.signers[].tabs,
  customFields.textCustomFields, notification.expirations, status "sent"); GET /envelopes/{id}?include=custom_fields;
  GET /envelopes?from_date&custom_field=name=value (listStatusChanges, used to reconcile an unknown create);
  PUT /envelopes/{id} {status: "voided", voidedReason}; GET /envelopes/{id}/documents/combined and
  /documents/certificate. An expired envelope is reported as "voided" with an expiry reason.
- DocuSign Connect HMAC: https://developers.docusign.com/platform/webhooks/connect/hmac/ and /validate/ —
  X-DocuSign-Signature-1..N = base64(HMAC-SHA256(key, raw body)); no timestamp/nonce, so replay protection is ours.
- Acrobat Sign REST v6 (https://secure.adobesign.com/public/docs/restapi/v6, OAuth guide
  https://developer.adobe.com/acrobat-sign/docs/overview/developer_guide/oauth): POST {api_access_point}/oauth/v2/refresh
  (grant_type=refresh_token, client_id, client_secret, refresh_token); POST /api/rest/v6/transientDocuments
  (multipart File, File-Name, Mime-Type) → transientDocumentId; POST /agreements {fileInfos, name,
  participantSetsInfo[{memberInfos[{email}], order, role SIGNER}], signatureType ESIGN, state IN_PROCESS,
  externalId, expirationTime}; GET /agreements/{id}; GET /agreements/{id}/events; GET /agreements (pageSize, cursor);
  PUT /agreements/{id}/state {state: CANCELLED, agreementCancellationInfo}; GET /combinedDocument, /auditTrail.
- Acrobat Sign webhooks (https://helpx.adobe.com/sign/web/developers/webhooks/overview.html): verification of intent
  and every notification carry X-AdobeSign-ClientId; the receiver checks it is our application id and echoes it in the
  X-AdobeSign-ClientId response header (or JSON xAdobeSignClientId). Payloads are not signed.

Rules kept here:
- only an approved quotation (status SENT, discount approvals complete) or an APPROVED/ACTIVE contract is sent; the
  PDF snapshot and a fingerprint of the approved content are stored; any change afterwards invalidates the request;
- the ledger row is committed (CLAIMED) before the provider call; a create without a clear answer becomes UNKNOWN and
  is reconciled by our reference (DocuSign custom field / Adobe agreement name + externalId), never re-sent blindly;
- COMPLETED only from the provider's documented final state AND downloaded signed document + evidence;
  provider_certified only for LIVE completions; webhooks only trigger a status read from the provider API;
- SIMULATED (local simulator hosts) vs LIVE (ESIGN_LIVE_ENABLED setting + owner activation + credentials + official
  hosts). Every request goes through app.core.provider_http.provider_client (egress guard).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, _is_local_host, provider_client
from app.models.m48_esign import ESignEnvelope, ESignProviderConfig, ESignWebhookEvent

PROVIDERS = ("DOCUSIGN", "ADOBE_SIGN")
LABELS = {"DOCUSIGN": "DocuSign eSignature", "ADOBE_SIGN": "Adobe Acrobat Sign"}
FIELDS = {  # (non-secret settings, secrets)
    "DOCUSIGN": (("integration_key", "user_id", "auth_base"), ("private_key_pem", "connect_hmac_key")),
    "ADOBE_SIGN": (("client_id", "api_base"), ("client_secret", "refresh_token")),
}
OPTIONAL = {"DOCUSIGN": ("account_id",), "ADOBE_SIGN": ()}
LIVE_HOSTS = {"DOCUSIGN": (".docusign.com", ".docusign.net"), "ADOBE_SIGN": (".adobesign.com", ".echosign.com")}
OPEN = ("CLAIMED", "SENT", "DELIVERED", "UNKNOWN")
CLAIM_GRACE = timedelta(minutes=2)        # a CLAIMED row younger than this is still in flight
GIVE_UP_AFTER = timedelta(minutes=15)     # an unknown create not found by then was never created
BACKOFF = 0.5
MAX_WAIT = 8.0
WEBHOOK_MAX_AGE = timedelta(days=7)
_TOKENS: dict = {}                        # provider → {"token", "exp", "rest"}


class ESignError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


class ProviderError(Exception):
    """definite=True: the provider refused, nothing was created; False: the outcome is unknown."""

    def __init__(self, msg: str, definite: bool, status: Optional[int] = None):
        super().__init__(msg)
        self.definite, self.status = definite, status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ── configuration, secrets, readiness ────────────────────────────────────────

def _seal(d: dict) -> str:
    from app.services.webhook_service import _store_webhook_secret
    return _store_webhook_secret(json.dumps(d))


def _unseal(v: Optional[str]) -> dict:
    from app.services.webhook_service import _read_webhook_secret
    return json.loads(_read_webhook_secret(v) or "{}") if v else {}


def live_flag() -> bool:
    return bool(getattr(settings, "ESIGN_LIVE_ENABLED", False))


def _readiness(provider: str, row: Optional[ESignProviderConfig]) -> dict:
    cfg = dict(row.settings or {}) if row else {}
    sec = _unseal(row.secrets_sealed) if row else {}
    names, secret_names = FIELDS[provider]
    missing = [n for n in names if not cfg.get(n)] + [n for n in secret_names if not sec.get(n)]
    live = live_flag() and bool(row and row.live_enabled)
    reasons = []
    if missing:
        reasons.append("Missing: " + ", ".join(m.replace("_", " ") for m in missing) + ".")
    base = cfg.get("auth_base" if provider == "DOCUSIGN" else "api_base") or ""
    host = (urlsplit(base).hostname or "").lower()
    if base and live and not (urlsplit(base).scheme == "https" and host.endswith(LIVE_HOSTS[provider])):
        reasons.append(f"LIVE needs the official {LABELS[provider]} https host; {host} is not one.")
    if base and not live and not _is_local_host(host):
        reasons.append(f"Simulated mode only talks to the local simulator; {host} is not local. Live sending needs "
                       "ESIGN_LIVE_ENABLED on the server and the owner's live activation.")
    if row and row.live_enabled and not live_flag():
        reasons.append("Live activation is recorded but ESIGN_LIVE_ENABLED is off on the server.")
    blocking = [r for r in reasons if not r.startswith("Live activation is recorded")]
    return {"provider": provider, "label": LABELS[provider], "mode": "LIVE" if live else "SIMULATED",
            "ready": not blocking, "reasons": reasons, "live_enabled": bool(row and row.live_enabled),
            "settings": {k: cfg.get(k) for k in names + OPTIONAL[provider]},
            "secrets_set": {k: bool(sec.get(k)) for k in secret_names},
            "updated_by": row.updated_by if row else None}


async def readiness(db: AsyncSession) -> list[dict]:
    rows = {r.provider: r for r in (await db.execute(select(ESignProviderConfig))).scalars()}
    local = {"provider": "LOCAL", "label": "Built-in signer code (local evidence, not provider-certified)", "mode": "LOCAL",
             "ready": True, "reasons": [], "live_enabled": False, "settings": {}, "secrets_set": {}, "updated_by": None}
    return [local] + [_readiness(p, rows.get(p)) for p in PROVIDERS]


async def save_config(db: AsyncSession, provider: str, values: dict, secrets: dict, live_enabled: Optional[bool], user) -> dict:
    if provider not in PROVIDERS:
        raise ESignError(404, "Unknown provider")
    names, secret_names = FIELDS[provider]
    row = await db.get(ESignProviderConfig, provider)
    if row is None:
        row = ESignProviderConfig(provider=provider, settings={}, live_enabled=False)
        db.add(row)
    cfg = dict(row.settings or {})
    for k, v in values.items():
        if k in names + OPTIONAL[provider]:
            v = (str(v).strip() if v is not None else "")[:500]
            if k in ("auth_base", "api_base") and v and urlsplit(v).scheme not in ("http", "https"):
                raise ESignError(422, f"{k} must be an http(s) URL.")
            cfg[k] = v.rstrip("/") if k.endswith("_base") else v
    sec = _unseal(row.secrets_sealed)
    for k, v in secrets.items():
        if k in secret_names and v:
            if k == "private_key_pem" and "PRIVATE KEY" not in v:
                raise ESignError(422, "The private key must be a PEM RSA private key.")
            sec[k] = str(v)[:10000]
    row.settings, row.secrets_sealed, row.updated_by = cfg, _seal(sec), user.username
    if live_enabled is not None:
        row.live_enabled = live_enabled
    _TOKENS.pop(provider, None)
    await db.flush()
    return _readiness(provider, row)


# ── HTTP with retries and error mapping ──────────────────────────────────────

def _err_text(r: httpx.Response) -> str:
    try:
        j = r.json()
        code = j.get("errorCode") or j.get("code") or j.get("error")
        msg = " ".join(str(x) for x in (code, j.get("message") or j.get("error_description")) if x)
    except ValueError:
        msg = r.text[:200]
    return f"Provider answered {r.status_code}: {msg}"


async def _call(method: str, url: str, *, retry: bool, **kw) -> httpx.Response:
    """GET/PUT/token calls retry 429/5xx/network errors with backoff; a create (retry=False) retries only 429,
    which the provider answers before processing — anything else unclear is reported as an unknown outcome."""
    attempts = 3
    for i in range(attempts):
        last = i + 1 == attempts
        try:
            async with provider_client(timeout=30.0) as c:
                r = await c.request(method, url, **kw)
        except EgressBlocked as e:
            raise ProviderError(str(e), definite=True) from None
        except httpx.HTTPError as e:
            if retry and not last:
                await asyncio.sleep(min(BACKOFF * 2 ** i, MAX_WAIT))
                continue
            raise ProviderError(f"No answer from the provider ({type(e).__name__}).", definite=False) from None
        if r.status_code == 429 or (r.status_code >= 500 and retry):
            if not last:
                try:
                    wait = float(r.headers.get("Retry-After") or BACKOFF * 2 ** i)
                except ValueError:
                    wait = BACKOFF * 2 ** i
                await asyncio.sleep(min(wait, MAX_WAIT))
                continue
            raise ProviderError(_err_text(r), definite=r.status_code == 429, status=r.status_code)
        if r.status_code >= 500:
            raise ProviderError(_err_text(r), definite=False, status=r.status_code)
        if r.status_code >= 400:
            raise ProviderError(_err_text(r), definite=True, status=r.status_code)
        return r
    raise AssertionError("unreachable")


def _pdf_ok(b: bytes) -> bool:
    return isinstance(b, bytes) and b.startswith(b"%PDF-") and len(b) < 50 * 1024 * 1024


# ── DocuSign eSignature REST v2.1 ────────────────────────────────────────────

class DocuSign:
    name = "DOCUSIGN"
    JWT_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"

    def __init__(self, cfg: dict, sec: dict, mode: str):
        self.cfg, self.sec, self.mode = cfg, sec, mode

    def assertion(self, now: Optional[int] = None) -> str:
        import jwt
        now = int(time.time()) if now is None else now
        claims = {"iss": self.cfg["integration_key"], "sub": self.cfg["user_id"],
                  "aud": urlsplit(self.cfg["auth_base"]).netloc, "iat": now, "exp": now + 3600,
                  "scope": "signature impersonation"}
        return jwt.encode(claims, self.sec["private_key_pem"], algorithm="RS256", headers={"typ": "JWT"})

    async def _auth(self) -> tuple[dict, str]:
        c = _TOKENS.get(self.name)
        if not c or c["exp"] < time.time() + 60:
            auth = self.cfg["auth_base"]
            r = await _call("POST", f"{auth}/oauth/token", retry=True,
                            data={"grant_type": self.JWT_GRANT, "assertion": self.assertion()})
            tok = r.json()
            h = {"Authorization": f"Bearer {tok['access_token']}"}
            info = (await _call("GET", f"{auth}/oauth/userinfo", retry=True, headers=h)).json()
            accounts = info.get("accounts") or []
            want = self.cfg.get("account_id")
            acct = next((a for a in accounts if want and a.get("account_id") == want), None) or \
                next((a for a in accounts if a.get("is_default") and not want), None)
            if acct is None:
                raise ProviderError("The DocuSign user has no matching account.", definite=True)
            base = acct["base_uri"].rstrip("/")
            host = (urlsplit(base).hostname or "").lower()
            if self.mode == "LIVE" and not (base.startswith("https://") and host.endswith(LIVE_HOSTS[self.name])):
                raise ProviderError(f"Refused account base URI {host}.", definite=True)
            c = {"token": tok["access_token"], "exp": time.time() + int(tok.get("expires_in") or 3600),
                 "rest": f"{base}/restapi/v2.1/accounts/{acct['account_id']}"}
            _TOKENS[self.name] = c
        return {"Authorization": f"Bearer {c['token']}"}, c["rest"]

    @staticmethod
    def envelope_body(env: ESignEnvelope) -> dict:
        return {
            "emailSubject": f"Please sign: {env.source_ref}"[:100],
            "documents": [{"documentBase64": base64.b64encode(env.snapshot_pdf).decode(), "name": f"{env.source_ref}.pdf",
                           "fileExtension": "pdf", "documentId": "1"}],
            "recipients": {"signers": [{
                "email": env.signer_email, "name": env.signer_name, "recipientId": "1", "routingOrder": "1",
                "tabs": {"signHereTabs": [{"anchorString": "/sig1/", "anchorUnits": "pixels", "anchorXOffset": "0", "anchorYOffset": "0"}],
                         "dateSignedTabs": [{"anchorString": "/date1/", "anchorUnits": "pixels", "anchorXOffset": "0", "anchorYOffset": "0"}]}}]},
            "customFields": {"textCustomFields": [{"name": "povu_ref", "value": env.idempotency_key, "show": "false", "required": "false"}]},
            "notification": {"useAccountDefaults": "false",
                             "expirations": {"expireEnabled": "true", "expireAfter": str(env.expire_days), "expireWarn": "0"}},
            "status": "sent",
        }

    async def create(self, env: ESignEnvelope) -> str:
        h, rest = await self._auth()
        r = await _call("POST", f"{rest}/envelopes", retry=False, headers=h, json=self.envelope_body(env))
        return r.json()["envelopeId"]

    async def find(self, env: ESignEnvelope) -> Optional[str]:
        h, rest = await self._auth()
        since = (env.created_at - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = await _call("GET", f"{rest}/envelopes", retry=True, headers=h,
                        params={"from_date": since, "custom_field": f"povu_ref={env.idempotency_key}"})
        envs = r.json().get("envelopes") or []
        return envs[0]["envelopeId"] if envs else None

    async def status(self, env: ESignEnvelope) -> tuple[str, str, bool]:
        h, rest = await self._auth()
        j = (await _call("GET", f"{rest}/envelopes/{env.provider_ref}", retry=True, headers=h,
                         params={"include": "custom_fields"})).json()
        fields = (j.get("customFields") or {}).get("textCustomFields") or []
        ours = any(f.get("name") == "povu_ref" and f.get("value") == env.idempotency_key for f in fields)
        raw = str(j.get("status") or "").lower()
        mapped = {"sent": "SENT", "created": "SENT", "delivered": "DELIVERED", "signed": "DELIVERED",
                  "completed": "COMPLETED", "declined": "DECLINED"}.get(raw)
        if raw == "voided":
            mapped = "EXPIRED" if "expir" in str(j.get("voidedReason") or "").lower() else "VOIDED"
        return raw, mapped or "UNKNOWN", ours

    async def cancel(self, env: ESignEnvelope, reason: str) -> None:
        h, rest = await self._auth()
        await _call("PUT", f"{rest}/envelopes/{env.provider_ref}", retry=True, headers=h,
                    json={"status": "voided", "voidedReason": reason[:200]})

    async def documents(self, env: ESignEnvelope) -> tuple[bytes, bytes]:
        h, rest = await self._auth()
        base = f"{rest}/envelopes/{env.provider_ref}/documents"
        signed = (await _call("GET", f"{base}/combined", retry=True, headers=h)).content
        cert = (await _call("GET", f"{base}/certificate", retry=True, headers=h)).content
        return signed, cert


def docusign_hmac(key: str, body: bytes) -> str:
    return base64.b64encode(hmac.new(key.replace('"', "").encode(), body, hashlib.sha256).digest()).decode()


# ── Adobe Acrobat Sign REST v6 ───────────────────────────────────────────────

class AdobeSign:
    name = "ADOBE_SIGN"

    def __init__(self, cfg: dict, sec: dict, mode: str):
        self.cfg, self.sec, self.mode = cfg, sec, mode

    async def _auth(self) -> tuple[dict, str]:
        c = _TOKENS.get(self.name)
        if not c or c["exp"] < time.time() + 60:
            base = self.cfg["api_base"]
            r = await _call("POST", f"{base}/oauth/v2/refresh", retry=True, data={
                "grant_type": "refresh_token", "client_id": self.cfg["client_id"],
                "client_secret": self.sec["client_secret"], "refresh_token": self.sec["refresh_token"]})
            tok = r.json()
            c = {"token": tok["access_token"], "exp": time.time() + int(tok.get("expires_in") or 3600),
                 "rest": f"{base}/api/rest/v6"}
            _TOKENS[self.name] = c
        return {"Authorization": f"Bearer {c['token']}"}, c["rest"]

    @staticmethod
    def agreement_body(env: ESignEnvelope, transient_id: str) -> dict:
        exp = (env.created_at + timedelta(days=env.expire_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"fileInfos": [{"transientDocumentId": transient_id}],
                "name": f"{env.source_ref} [{env.idempotency_key}]"[:255],
                "participantSetsInfo": [{"memberInfos": [{"email": env.signer_email}], "order": 1, "role": "SIGNER"}],
                "signatureType": "ESIGN", "state": "IN_PROCESS", "externalId": {"id": env.idempotency_key},
                "expirationTime": exp}

    async def create(self, env: ESignEnvelope) -> str:
        h, rest = await self._auth()
        name = f"{env.source_ref}.pdf"
        t = await _call("POST", f"{rest}/transientDocuments", retry=True, headers=h,
                        files={"File": (name, env.snapshot_pdf, "application/pdf")},
                        data={"File-Name": name, "Mime-Type": "application/pdf"})
        r = await _call("POST", f"{rest}/agreements", retry=False, headers=h,
                        json=self.agreement_body(env, t.json()["transientDocumentId"]))
        return r.json()["id"]

    async def find(self, env: ESignEnvelope) -> Optional[str]:
        h, rest = await self._auth()
        cursor = None
        for _ in range(20):                       # ponytail: linear page scan, a search query if volumes grow
            params = {"pageSize": 100, **({"cursor": cursor} if cursor else {})}
            j = (await _call("GET", f"{rest}/agreements", retry=True, headers=h, params=params)).json()
            for a in j.get("userAgreementList") or []:
                if str(a.get("name", "")).endswith(f"[{env.idempotency_key}]"):
                    return a["id"]
            cursor = (j.get("page") or {}).get("nextCursor")
            if not cursor:
                return None
        return None

    async def status(self, env: ESignEnvelope) -> tuple[str, str, bool]:
        h, rest = await self._auth()
        j = (await _call("GET", f"{rest}/agreements/{env.provider_ref}", retry=True, headers=h)).json()
        ours = (j.get("externalId") or {}).get("id") == env.idempotency_key
        raw = str(j.get("status") or "").upper()
        if raw in ("SIGNED", "APPROVED", "ACCEPTED", "FORM_FILLED", "DELIVERED"):
            mapped = "COMPLETED"
        elif raw.startswith(("OUT_FOR_", "WAITING_FOR_")) or raw in ("DOCUMENTS_NOT_YET_PROCESSED", "IN_PROCESS"):
            mapped = "SENT"
        elif raw == "EXPIRED":
            mapped = "EXPIRED"
        elif raw == "CANCELLED":                  # recalled by the sender or rejected by a signer: the events tell
            ev = (await _call("GET", f"{rest}/agreements/{env.provider_ref}/events", retry=True, headers=h)).json()
            mapped = "DECLINED" if any(e.get("type") == "REJECTED" for e in ev.get("events") or []) else "CANCELLED"
        else:
            mapped = "UNKNOWN"
        return raw, mapped, ours

    async def cancel(self, env: ESignEnvelope, reason: str) -> None:
        h, rest = await self._auth()
        await _call("PUT", f"{rest}/agreements/{env.provider_ref}/state", retry=True, headers=h,
                    json={"state": "CANCELLED", "agreementCancellationInfo": {"comment": reason[:200], "notifyOthers": True}})

    async def documents(self, env: ESignEnvelope) -> tuple[bytes, bytes]:
        h, rest = await self._auth()
        base = f"{rest}/agreements/{env.provider_ref}"
        signed = (await _call("GET", f"{base}/combinedDocument", retry=True, headers=h)).content
        audit = (await _call("GET", f"{base}/auditTrail", retry=True, headers=h)).content
        return signed, audit


async def _adapter(db: AsyncSession, provider: str, mode: Optional[str] = None):
    row = await db.get(ESignProviderConfig, provider)
    rd = _readiness(provider, row)
    if not rd["ready"]:
        raise ESignError(409, f"{LABELS[provider]} is not ready: " + " ".join(rd["reasons"]))
    if mode and rd["mode"] != mode:
        raise ESignError(409, f"This request was sent in {mode} mode; the provider is now {rd['mode']}. Reconcile is refused.")
    cls = DocuSign if provider == "DOCUSIGN" else AdobeSign
    return cls(dict(row.settings), _unseal(row.secrets_sealed), rd["mode"])


# ── immutable snapshot of the approved source ────────────────────────────────

def _pdf(lines: list[str]) -> bytes:
    """Deterministic plain-text PDF (Helvetica, A4), 50 lines per page."""
    def esc(s: str) -> str:
        return s.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    pages = [lines[i:i + 50] for i in range(0, max(len(lines), 1), 50)]
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for pg in pages:
        stream = "BT /F1 10 Tf 14 TL 50 800 Td " + " ".join(f"({esc(l)}) '" for l in pg) + " ET"
        objs.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objs)} 0 R >>")
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _fp(content: dict) -> str:
    return _sha(json.dumps(content, sort_keys=True, default=str, separators=(",", ":")).encode())


async def _quote_content(db: AsyncSession, q) -> tuple[dict, list[str]]:
    from app.models.master import Product
    from app.models.sales import Customer
    cust = await db.get(Customer, q.customer_id)
    names = {}
    for ln in q.lines:
        if ln.product_id and ln.product_id not in names:
            p = await db.get(Product, ln.product_id)
            names[ln.product_id] = getattr(p, "name", str(ln.product_id))
    d = lambda v: str(Decimal(v or 0).quantize(Decimal("0.0001")))     # noqa: E731
    content = {"type": "QUOTATION", "quote_no": q.quote_no, "version": q.version, "customer_id": str(q.customer_id),
               "currency": q.currency, "discount_pct": d(q.discount_pct), "total": d(q.total_amount), "tax": d(q.tax_amount),
               "grand_total": d(q.grand_total), "valid_until": str(q.valid_until), "notes": q.notes or "",
               "lines": [{"no": ln.line_no, "product_id": str(ln.product_id), "description": ln.description or "",
                          "qty": str(Decimal(ln.qty).quantize(Decimal("0.001"))), "unit": ln.unit, "unit_price": d(ln.unit_price),
                          "discount_pct": d(ln.discount_pct), "tax_rate": d(ln.tax_rate), "line_total": d(ln.line_total)}
                         for ln in sorted(q.lines, key=lambda x: x.line_no)]}
    text = [f"POVU quotation {q.quote_no} version {q.version}", f"Customer: {getattr(cust, 'name', '')}",
            f"Date: {q.quote_date}   Valid until: {q.valid_until}   Currency: {q.currency}", ""]
    for ln in content["lines"]:
        name = names.get(uuid.UUID(ln["product_id"])) if ln["product_id"] != "None" else ln["description"]
        text.append(f"{ln['no']}. {name or ln['description']} | {ln['qty']} {ln['unit']} x {ln['unit_price']} | "
                    f"disc {ln['discount_pct']}% | tax {ln['tax_rate']}% | {ln['line_total']}")
    text += ["", f"Discount {content['discount_pct']}%  Net {content['total']}  Tax {content['tax']}  Total {content['grand_total']}",
             (q.notes or "")[:300]]
    return content, text


async def _contract_content(c) -> tuple[dict, list[str]]:
    content = {"type": "CONTRACT", "code": c.contract_code, "name": c.contract_name, "contract_type": c.contract_type,
               "party_type": c.party_type, "party_id": str(c.party_id), "start": str(c.start_date), "end": str(c.end_date),
               "currency": c.currency, "auto_renew": bool(c.auto_renew), "notes": c.notes or "", "version": c.current_version}
    text = [f"POVU contract {c.contract_code} version {c.current_version}", c.contract_name,
            f"Type {c.contract_type}  Party {c.party_type}  From {c.start_date} to {c.end_date}  Currency {c.currency}", ""]
    for para in (c.notes or "").splitlines():
        text += [para[i:i + 100] for i in range(0, len(para), 100)] or [""]
    return content, text


async def _load_source(db: AsyncSession, source_type: str, source_id, lock: bool = False):
    from sqlalchemy.orm import selectinload
    from app.models.contracts import Contract
    from app.models.quotation import Quotation
    if source_type == "QUOTATION":
        stmt = select(Quotation).options(selectinload(Quotation.lines)).where(Quotation.id == source_id)
    elif source_type == "CONTRACT":
        stmt = select(Contract).where(Contract.id == source_id)
    else:
        raise ESignError(422, "source_type must be QUOTATION or CONTRACT")
    if lock:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt.execution_options(populate_existing=True))).scalar_one_or_none()


async def fingerprint(db: AsyncSession, source_type: str, obj) -> str:
    content, _ = await (_quote_content(db, obj) if source_type == "QUOTATION" else _contract_content(obj))
    return _fp(content)


async def snapshot(db: AsyncSession, source_type: str, source_id, user) -> tuple[object, str, str, bytes]:
    """Validates that the source is approved, then returns (obj, ref, content fingerprint, PDF)."""
    from fastapi import HTTPException
    from app.core.access_control import has_any_permission
    obj = await _load_source(db, source_type, source_id, lock=True)
    if obj is None:
        raise ESignError(404, "Source document not found")
    if source_type == "QUOTATION":
        from app.services import cpq_service as cpq
        from app.services import discount_approval_service as disc
        from app.services.commercial_access_service import ensure_commercial_action_allowed
        ensure_commercial_action_allowed(user, obj, "view", "sales")     # record scope; the route checks the send right
        if getattr(obj.status, "value", obj.status) != "SENT":
            raise ESignError(409, "Only a sent (approved) quotation can go out for signature; a draft needs its approvals and "
                                  "must be sent first, an accepted or closed one is final.")
        try:
            disc.ensure_approved(obj, "send it for signature")
            await cpq.ensure_levels(db, obj, "send it for signature")
        except cpq.CPQError as e:
            raise ESignError(e.status, str(e)) from None
        except HTTPException as e:
            raise ESignError(e.status_code, str(e.detail)) from None
        content, text = await _quote_content(db, obj)
        ref = f"{obj.quote_no} v{obj.version}"
    else:
        if not (user.is_superuser or has_any_permission(user, ("sales.edit", "procurement.edit", "finance.edit"))):
            raise ESignError(403, "You may not send contracts for signature.")
        if obj.status not in ("APPROVED", "ACTIVE"):
            raise ESignError(409, "Only an approved or active contract can go out for signature.")
        content, text = await _contract_content(obj)
        ref = f"{obj.contract_code} v{obj.current_version}"
    fp = _fp(content)
    text += ["", f"Content fingerprint (SHA-256): {fp}", "", "Signature: /sig1/        Date: /date1/"]
    return obj, ref, fp, _pdf(text)


# ── ledger state machine ─────────────────────────────────────────────────────

async def _set(db: AsyncSession, env: ESignEnvelope, status: str, note: Optional[str], via: str, actor=None) -> None:
    from app.crud import audit as audit_crud
    changed = status != env.status
    env.timeline = [*(env.timeline or []), {"at": _now().isoformat(), "status": status, "via": via, "note": note,
                                            "provider_status": env.provider_status}]
    env.error = note if status in ("FAILED", "UNKNOWN", "INVALIDATED") else env.error if not changed else None
    env.status, env.updated_at = status, _now()
    await audit_crud.log_event(db, event_type=f"ESIGN_PROVIDER_{status}", actor_id=getattr(actor, "id", None),
                               actor_email=getattr(actor, "email", None), module="esign", target_type="esign_envelope",
                               target_id=str(env.id), target_name=env.source_ref,
                               details={"provider": env.provider, "mode": env.mode, "via": via, "provider_ref": env.provider_ref,
                                        "note": note})


async def send(db: AsyncSession, *, provider: str, source_type: str, source_id, signer_name: str, signer_email: str,
               expire_days: int, idempotency_key: Optional[str], user) -> ESignEnvelope:
    if provider not in PROVIDERS:
        raise ESignError(422, "provider must be DOCUSIGN or ADOBE_SIGN")
    if idempotency_key:
        old = (await db.execute(select(ESignEnvelope).where(ESignEnvelope.idempotency_key == idempotency_key))).scalar_one_or_none()
        if old is not None:
            if (old.source_type, old.source_id, old.provider) != (source_type, source_id, provider):
                raise ESignError(409, "This idempotency key was used for another request.")
            return old
    adapter = await _adapter(db, provider)
    obj, ref, fp, pdf = await snapshot(db, source_type, source_id, user)
    busy = (await db.execute(select(ESignEnvelope.id).where(ESignEnvelope.source_type == source_type,
                                                             ESignEnvelope.source_id == source_id,
                                                             ESignEnvelope.status.in_(OPEN)))).first()
    if busy:
        raise ESignError(409, "This document is already out for signature; cancel or reconcile that request first.")
    now = _now()
    env = ESignEnvelope(provider=provider, mode=adapter.mode, idempotency_key=idempotency_key or f"povu-{uuid.uuid4().hex}",
                        source_type=source_type, source_id=source_id, source_ref=ref, source_fingerprint=fp,
                        snapshot_pdf=pdf, snapshot_sha256=_sha(pdf), signer_name=signer_name, signer_email=signer_email,
                        expire_days=expire_days, status="CLAIMED", timeline=[], provider_certified=False,
                        created_by_id=user.id, created_at=now, updated_at=now)
    db.add(env)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ESignError(409, "This document is already out for signature.") from None
    await _set(db, env, "CLAIMED", "Ledger claim before the provider call", "send", user)
    await db.commit()                                        # the claim survives a crash during the call
    try:
        env.provider_ref = await adapter.create(env)
    except ProviderError as e:
        await _set(db, env, "FAILED" if e.definite else "UNKNOWN",
                   str(e) if e.definite else f"{e} The request may or may not exist at the provider; reconcile before sending again.",
                   "send", user)
        await db.commit()
        return env
    env.provider_status = "sent"
    await _set(db, env, "SENT", f"{LABELS[provider]} {'envelope' if provider == 'DOCUSIGN' else 'agreement'} {env.provider_ref}", "send", user)
    await db.commit()
    return env


async def _apply_completion(db: AsyncSession, env: ESignEnvelope) -> str:
    """ERP update after a verified completion. Financial approval rules are checked again."""
    if env.source_type != "QUOTATION":
        return "Signed contract and evidence stored with the contract's signature request."
    from fastapi import HTTPException
    from app.models.quotation import QuoteStatus
    from app.services import cpq_service as cpq
    from app.services import discount_approval_service as disc
    q = await _load_source(db, "QUOTATION", env.source_id, lock=True)
    if q is None:
        return "Quotation no longer exists; evidence stored."
    st = getattr(q.status, "value", q.status)
    if st != "SENT":
        return f"Quotation is {st}; evidence stored, status unchanged."
    try:
        disc.ensure_approved(q, "accept it")
        await cpq.ensure_levels(db, q, "accept it")
    except (HTTPException, cpq.CPQError) as e:
        return f"Not accepted: {getattr(e, 'detail', None) or e}"
    q.status, q.accepted_at = QuoteStatus.ACCEPTED, _now()
    return f"Quotation accepted from the signed {'simulated ' if env.mode == 'SIMULATED' else ''}{LABELS[env.provider]} copy."


async def reconcile(db: AsyncSession, env_id, via: str, actor=None) -> ESignEnvelope:
    env = (await db.execute(select(ESignEnvelope).where(ESignEnvelope.id == env_id).with_for_update()
                            .execution_options(populate_existing=True))).scalar_one_or_none()
    if env is None:
        raise ESignError(404, "Signature request not found")
    if env.status not in OPEN:
        return env
    adapter = await _adapter(db, env.provider, env.mode)
    now = _now()
    env.last_checked_at = now
    try:
        if env.provider_ref is None:
            if env.status == "CLAIMED" and now - env.created_at < CLAIM_GRACE:
                return env
            found = await adapter.find(env)
            if found is None:
                if now - env.created_at > GIVE_UP_AFTER:
                    await _set(db, env, "FAILED", "Not found at the provider: nothing was sent. You can send again.", via, actor)
                elif env.status != "UNKNOWN":
                    await _set(db, env, "UNKNOWN", "Not found at the provider yet; reconcile again later.", via, actor)
                return env
            env.provider_ref = found
        raw, mapped, ours = await adapter.status(env)
    except ProviderError as e:
        env.error = str(e)
        return env
    env.provider_status = raw
    if not ours:
        await _set(db, env, "UNKNOWN", "The provider record does not carry this request's reference; not trusted.", via, actor)
        return env
    obj = await _load_source(db, env.source_type, env.source_id)
    if obj is None or await fingerprint(db, env.source_type, obj) != env.source_fingerprint:
        note = "The document changed after it was sent; this signature request is void."
        if mapped in OPEN:
            try:
                await adapter.cancel(env, "Document changed after sending")
            except ProviderError as e:
                note += f" Cancelling at the provider failed ({e}); cancel it there."
        await _set(db, env, "INVALIDATED", note, via, actor)
        return env
    if mapped == "COMPLETED":
        try:
            signed, evidence = await adapter.documents(env)
        except ProviderError as e:
            env.error = f"The provider reports completion; the signed document could not be downloaded yet ({e})."
            return env
        if not (_pdf_ok(signed) and _pdf_ok(evidence)):
            env.error = "The provider reports completion but the downloaded files are not PDFs; not marked completed."
            return env
        env.signed_pdf, env.signed_sha256 = signed, _sha(signed)
        env.evidence_pdf, env.evidence_sha256 = evidence, _sha(evidence)
        env.provider_certified = env.mode == "LIVE"
        env.completed_at = now
        env.erp_applied = (await _apply_completion(db, env))[:200]
        await _set(db, env, "COMPLETED", f"Signed document {env.signed_sha256[:12]}…, evidence {env.evidence_sha256[:12]}…. "
                   + env.erp_applied, via, actor)
    elif mapped != env.status:
        await _set(db, env, mapped, None if mapped != "UNKNOWN" else f"Unmapped provider status {raw!r}", via, actor)
    return env


async def cancel(db: AsyncSession, env_id, reason: str, user) -> ESignEnvelope:
    env = (await db.execute(select(ESignEnvelope).where(ESignEnvelope.id == env_id).with_for_update()
                            .execution_options(populate_existing=True))).scalar_one_or_none()
    if env is None:
        raise ESignError(404, "Signature request not found")
    if env.status not in ("SENT", "DELIVERED"):
        raise ESignError(409, f"A {env.status} request cannot be cancelled; reconcile it first.")
    adapter = await _adapter(db, env.provider, env.mode)
    try:
        await adapter.cancel(env, reason)
    except ProviderError as e:
        raise ESignError(502 if not e.definite else 409, f"The provider refused the cancellation: {e}") from None
    env.provider_status = "voided" if env.provider == "DOCUSIGN" else "CANCELLED"
    await _set(db, env, "VOIDED" if env.provider == "DOCUSIGN" else "CANCELLED", reason, "user", user)
    return env


# ── webhooks (triggers only: the status is always read back from the provider API) ──

async def _remember(db: AsyncSession, provider: str, key: str, ref: Optional[str], event: Optional[str]) -> bool:
    """False when this notification was already received (replay)."""
    db.add(ESignWebhookEvent(provider=provider, event_key=_sha(key.encode()), provider_ref=ref, event=(event or "")[:80]))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False
    return True


def _too_old(stamp: Optional[str]) -> bool:
    try:
        t = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return True
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return not (_now() - WEBHOOK_MAX_AGE <= t <= _now() + timedelta(minutes=5))


async def _trigger(db: AsyncSession, provider: str, ref: Optional[str], via: str) -> Optional[str]:
    env_id = (await db.execute(select(ESignEnvelope.id).where(ESignEnvelope.provider == provider,
                                                              ESignEnvelope.provider_ref == ref))).scalar_one_or_none() if ref else None
    await db.commit()                                         # keep the replay record even if the reconcile fails
    if env_id is None:
        return None
    try:
        env = await reconcile(db, env_id, via)
    except ESignError:
        await db.rollback()
        return None
    await db.commit()
    return env.status


async def docusign_connect(db: AsyncSession, body: bytes, headers) -> tuple[int, dict]:
    row = await db.get(ESignProviderConfig, "DOCUSIGN")
    key = _unseal(row.secrets_sealed).get("connect_hmac_key") if row else None
    if not key:
        return 503, {"detail": "DocuSign Connect is not configured."}
    sigs = [v for k, v in headers.items() if k.lower().startswith("x-docusign-signature-")]
    want = docusign_hmac(key, body)
    if not any(hmac.compare_digest(want.encode(), s.strip().encode()) for s in sigs):
        return 401, {"detail": "Invalid signature."}
    try:
        msg = json.loads(body)
        data = msg.get("data") or {}
        ref, event, stamp = data.get("envelopeId"), msg.get("event"), msg.get("generatedDateTime")
    except (ValueError, AttributeError):
        return 400, {"detail": "Not a DocuSign Connect JSON message."}
    if _too_old(stamp):
        return 200, {"ignored": "stale or future-dated message"}
    if not await _remember(db, "DOCUSIGN", f"{ref}|{event}|{stamp}", ref, event):
        return 200, {"duplicate": True}
    return 200, {"status": await _trigger(db, "DOCUSIGN", ref, "webhook")}


async def adobe_client_id(db: AsyncSession) -> Optional[str]:
    row = await db.get(ESignProviderConfig, "ADOBE_SIGN")
    return (row.settings or {}).get("client_id") if row else None


async def adobe_webhook(db: AsyncSession, body: bytes, client_id_header: Optional[str]) -> tuple[int, dict]:
    ours = await adobe_client_id(db)
    if not ours:
        return 503, {"detail": "Acrobat Sign is not configured."}
    if not client_id_header or not hmac.compare_digest(ours.encode(), client_id_header.encode()):
        return 401, {"detail": "Unknown client id."}
    try:
        msg = json.loads(body)
        ref, event = (msg.get("agreement") or {}).get("id"), msg.get("event")
        note_id, stamp = msg.get("webhookNotificationId"), msg.get("eventDate")
    except (ValueError, AttributeError):
        return 400, {"detail": "Not an Acrobat Sign notification."}
    if not note_id or _too_old(stamp):
        return 200, {"ignored": "missing id, stale or future-dated notification"}
    if not await _remember(db, "ADOBE_SIGN", str(note_id), ref, event):
        return 200, {"duplicate": True}
    return 200, {"status": await _trigger(db, "ADOBE_SIGN", ref, "webhook")}


def envelope_out(env: ESignEnvelope) -> dict:
    return {"id": str(env.id), "provider": env.provider, "provider_label": LABELS[env.provider], "mode": env.mode,
            "source_type": env.source_type, "source_id": str(env.source_id), "source_ref": env.source_ref,
            "status": env.status, "provider_ref": env.provider_ref, "provider_status": env.provider_status,
            "signer_name": env.signer_name, "signer_email": env.signer_email, "expire_days": env.expire_days,
            "snapshot_sha256": env.snapshot_sha256, "source_fingerprint": env.source_fingerprint,
            "signed_sha256": env.signed_sha256, "evidence_sha256": env.evidence_sha256,
            "provider_certified": env.provider_certified,
            "evidence_label": ("Provider-certified (live)" if env.provider_certified else
                               "Simulated provider evidence — not certified" if env.status == "COMPLETED" else None),
            "erp_applied": env.erp_applied, "error": env.error, "timeline": env.timeline or [],
            "completed_at": env.completed_at.isoformat() if env.completed_at else None,
            "created_at": env.created_at.isoformat() if env.created_at else None,
            "last_checked_at": env.last_checked_at.isoformat() if env.last_checked_at else None,
            "can_cancel": env.status in ("SENT", "DELIVERED"), "can_reconcile": env.status in OPEN}
