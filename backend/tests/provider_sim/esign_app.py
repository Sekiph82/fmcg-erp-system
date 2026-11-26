"""Local DocuSign eSignature + Adobe Acrobat Sign simulator (M48.S01.T009). Synthetic, local only — no real signing.

Contracts followed (see app/services/esign_provider_service.py for the doc URLs):
- DocuSign: POST /docusign/oauth/token (JWT bearer grant, RS256 assertion checked against the registered public key,
  aud = this host, consent_required), GET /docusign/oauth/userinfo (accounts[].base_uri), REST v2.1 under
  /docusign/restapi/v2.1/accounts/{accountId}: envelopes create / get (include=custom_fields) / list (from_date,
  custom_field) / void (PUT status voided, only sent|delivered), documents/combined, documents/certificate.
  Connect messages are JSON with X-DocuSign-Signature-1 = base64(HMAC-SHA256(key, body)).
- Acrobat Sign REST v6 under /adobe: POST /oauth/v2/refresh, POST /api/rest/v6/transientDocuments (multipart),
  POST/GET /agreements (pageSize + cursor paging), GET /agreements/{id}, /events, PUT /agreements/{id}/state,
  GET /combinedDocument, /auditTrail. Notifications carry X-AdobeSign-ClientId (no payload signature).

Behaviour: after sending, an envelope/agreement turns "delivered" at half of the configured delay and reaches the
configured outcome (complete | decline | expire) after the delay. Each transition queues a provider callback
(GET /_control/outbox), and POSTs it to deliver_to[provider] when set (browser walkthrough). Faults per operation:
429 / 500 / 400 / "lost" (create succeeds but the answer is lost: 504) / "nopdf" (documents are not PDFs).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

ACCOUNT = "a1b2c3d4-0000-4000-8000-00000000acc1"


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _mini_pdf(text: str) -> bytes:
    return b"%PDF-1.4\n% " + text.encode() + b"\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def sim_esign_settings(base: str) -> dict:
    """Provider config (settings, secrets) that points the ERP adapters at a simulator served at ``base``."""
    base = base.rstrip("/")
    return {"DOCUSIGN": {"integration_key": "sim-integration-key", "user_id": "5f1e2d3c-0000-4000-8000-0000000000u1",
                         "auth_base": f"{base}/docusign"},
            "ADOBE_SIGN": {"client_id": "sim-adobe-client", "api_base": f"{base}/adobe"}}


def create_esign_app() -> FastAPI:
    app = FastAPI(title="POVU e-signature simulator (synthetic, local only)")
    st: dict = {}

    def reset() -> None:
        st.clear()
        st.update(ds_public_key=None, ds_ik="sim-integration-key", ds_user="5f1e2d3c-0000-4000-8000-0000000000u1",
                  consent=True, hmac_key="sim-connect-hmac-key", adobe_client="sim-adobe-client",
                  adobe_secret="sim-adobe-secret", adobe_refresh="sim-adobe-refresh", tokens={},
                  envelopes={}, agreements={}, transient={}, outbox=[], faults={}, delay=0.0, outcome="complete",
                  deliver_to={}, strip_ref=False, page_size=2, requests=[], assertions=[])
    reset()

    def fault(op: str):
        q = st["faults"].get(op) or []
        return q.pop(0) if q else None

    def err(code, provider):
        if code == 429:
            return JSONResponse({"errorCode": "HOURLY_APIINVOCATION_LIMIT_EXCEEDED", "message": "rate limited"} if provider == "ds"
                                else {"code": "THROTTLING_TOO_MANY_REQUESTS", "message": "rate limited"}, 429, headers={"Retry-After": "1"})
        if code == 500:
            return JSONResponse({"errorCode": "UNSPECIFIED_ERROR", "message": "simulated"} if provider == "ds"
                                else {"code": "MISC_SERVER_ERROR", "message": "simulated"}, 500)
        return JSONResponse({"errorCode": "INVALID_REQUEST_PARAMETER", "message": "simulated"} if provider == "ds"
                            else {"code": "INVALID_ARGUMENTS", "message": "simulated"}, 400)

    def bearer(provider: str, authorization: Optional[str]) -> bool:
        return st["tokens"].get((authorization or "").removeprefix("Bearer ").strip()) == provider

    async def deliver(provider: str, body: bytes, headers: dict) -> None:
        url = st["deliver_to"].get(provider)
        if not url:
            return
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(url, content=body, headers=headers)
        except httpx.HTTPError:
            pass

    def callback(provider: str, item: dict, event: str) -> None:
        if provider == "DOCUSIGN":
            body = json.dumps({"event": event, "apiVersion": "v2.1",
                               "uri": f"/restapi/v2.1/accounts/{ACCOUNT}/envelopes/{item['id']}", "retryCount": 0,
                               "configurationId": "10001", "generatedDateTime": _iso(),
                               "data": {"accountId": ACCOUNT, "userId": st["ds_user"], "envelopeId": item["id"]}}).encode()
            sig = base64.b64encode(hmac.new(st["hmac_key"].encode(), body, hashlib.sha256).digest()).decode()
            headers = {"Content-Type": "application/json", "X-DocuSign-Signature-1": sig}
        else:
            body = json.dumps({"webhookId": "sim-webhook-1", "webhookName": "POVU ERP", "webhookNotificationId": str(uuid.uuid4()),
                               "event": event, "eventDate": _iso(),
                               "agreement": {"id": item["id"], "name": item["name"], "status": item["status"]}}).encode()
            headers = {"Content-Type": "application/json", "X-AdobeSign-ClientId": st["adobe_client"]}
        st["outbox"].append({"provider": provider, "body_b64": base64.b64encode(body).decode(), "headers": headers})
        try:
            asyncio.get_running_loop().create_task(deliver(provider, body, headers))
        except RuntimeError:
            pass

    def tick(force: bool = False) -> None:
        now = time.time()
        for e in st["envelopes"].values():
            if e["status"] in ("sent",) and (force or now >= e["sent_at"] + e["delay"] / 2):
                e["status"] = "delivered"
                callback("DOCUSIGN", e, "envelope-delivered")
            if e["status"] == "delivered" and (force or now >= e["sent_at"] + e["delay"]):
                if e["outcome"] == "complete":
                    e["status"] = "completed"
                elif e["outcome"] == "decline":
                    e["status"] = "declined"
                else:
                    e["status"], e["voidedReason"] = "voided", "Envelope has expired."
                callback("DOCUSIGN", e, {"completed": "envelope-completed", "declined": "envelope-declined"}.get(e["status"], "envelope-voided"))
        for a in st["agreements"].values():
            if a["status"] == "OUT_FOR_SIGNATURE" and (force or now >= a["sent_at"] + a["delay"]):
                if a["outcome"] == "complete":
                    a["status"], ev, typ = "SIGNED", "AGREEMENT_WORKFLOW_COMPLETED", "ESIGNED"
                elif a["outcome"] == "decline":
                    a["status"], ev, typ = "CANCELLED", "AGREEMENT_REJECTED", "REJECTED"
                else:
                    a["status"], ev, typ = "EXPIRED", "AGREEMENT_EXPIRED", "EXPIRED"
                a["events"].append({"type": typ, "date": _iso()})
                callback("ADOBE_SIGN", a, ev)

    # ── control plane ───────────────────────────────────────────────────────
    @app.post("/_control")
    async def control(request: Request):
        body = await request.json()
        for k in ("ds_public_key", "consent", "delay", "outcome", "strip_ref", "page_size", "hmac_key"):
            if k in body:
                st[k] = body[k]
        st["deliver_to"].update(body.get("deliver_to") or {})
        for k, v in (body.get("faults") or {}).items():
            st["faults"].setdefault(k, []).extend(v)
        return {"ok": True}

    @app.post("/_control/reset")
    async def control_reset():
        reset()
        return {"ok": True}

    @app.post("/_control/tick")
    async def control_tick(force: bool = True):
        tick(force)
        return {"ok": True}

    @app.get("/_control/outbox")
    async def control_outbox():
        out, st["outbox"] = st["outbox"], []
        return {"callbacks": out}

    @app.get("/_control/state")
    async def control_state():
        return {"envelopes": {k: {x: y for x, y in v.items() if x != "pdf"} for k, v in st["envelopes"].items()},
                "agreements": {k: {x: y for x, y in v.items() if x != "pdf"} for k, v in st["agreements"].items()},
                "requests": st["requests"], "assertions": st["assertions"]}

    # ── DocuSign OAuth (JWT Grant) ──────────────────────────────────────────
    @app.post("/docusign/oauth/token")
    async def ds_token(request: Request):
        if (f := fault("ds_token")) is not None:
            return err(f, "ds")
        import jwt
        form = dict(await request.form())
        if form.get("grant_type") != "urn:ietf:params:oauth:grant-type:jwt-bearer":
            return JSONResponse({"error": "unsupported_grant_type"}, 400)
        try:
            header = jwt.get_unverified_header(form.get("assertion", ""))
            claims = jwt.decode(form.get("assertion", ""), st["ds_public_key"], algorithms=["RS256"],
                                audience=request.url.netloc, options={"require": ["iss", "sub", "aud", "iat", "exp"]})
        except Exception:   # noqa: BLE001 — any invalid assertion is invalid_grant, as DocuSign answers
            return JSONResponse({"error": "invalid_grant"}, 400)
        st["assertions"].append({"header": header, "claims": claims})
        if claims["iss"] != st["ds_ik"] or claims["sub"] != st["ds_user"] or "signature" not in str(claims.get("scope", "")).split():
            return JSONResponse({"error": "invalid_grant", "error_description": "issuer_not_found"}, 400)
        if not st["consent"]:
            return JSONResponse({"error": "consent_required"}, 400)
        tok = "sim-ds-" + secrets.token_urlsafe(16)
        st["tokens"][tok] = "ds"
        return {"access_token": tok, "token_type": "Bearer", "expires_in": 3600}

    @app.get("/docusign/oauth/userinfo")
    async def ds_userinfo(request: Request, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization):
            return JSONResponse({"error": "invalid_request"}, 401)
        return {"sub": st["ds_user"], "name": "POVU Sales Ops", "email": "sales-ops@povu-demo.test",
                "accounts": [{"account_id": ACCOUNT, "is_default": True, "account_name": "POVU Demo",
                              "base_uri": str(request.base_url).rstrip("/") + "/docusign"}]}

    # ── DocuSign eSignature REST v2.1 ───────────────────────────────────────
    def ds_env_out(e: dict) -> dict:
        out = {"envelopeId": e["id"], "status": e["status"], "emailSubject": e["subject"], "statusChangedDateTime": _iso(),
               "customFields": {"textCustomFields": [] if st["strip_ref"] else e["custom"]}}
        if e.get("voidedReason"):
            out["voidedReason"] = e["voidedReason"]
        return out

    @app.post("/docusign/restapi/v2.1/accounts/{acct}/envelopes")
    async def ds_create(acct: str, request: Request, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization) or acct != ACCOUNT:
            return JSONResponse({"errorCode": "USER_AUTHENTICATION_FAILED"}, 401)
        f = fault("ds_create")
        if f not in (None, "lost"):
            return err(f, "ds")
        b = await request.json()
        st["requests"].append({"op": "ds_create", "body": {**b, "documents": [{**d, "documentBase64": "<%d chars>" % len(d.get("documentBase64", ""))} for d in b.get("documents", [])]}})
        try:
            pdf = base64.b64decode(b["documents"][0]["documentBase64"], validate=True)
            signer = b["recipients"]["signers"][0]
            ok = (b.get("status") == "sent" and b.get("emailSubject") and pdf.startswith(b"%PDF-")
                  and b["documents"][0].get("fileExtension") == "pdf" and b["documents"][0].get("documentId")
                  and signer.get("email") and signer.get("name") and signer.get("recipientId")
                  and signer.get("tabs", {}).get("signHereTabs"))
        except (KeyError, IndexError, ValueError, TypeError):
            ok = False
        if not ok:
            return JSONResponse({"errorCode": "INVALID_REQUEST_BODY", "message": "The request body is missing or improperly formatted."}, 400)
        eid = str(uuid.uuid4())
        st["envelopes"][eid] = {"id": eid, "status": "sent", "subject": b["emailSubject"], "pdf": pdf,
                                "custom": (b.get("customFields") or {}).get("textCustomFields") or [],
                                "sent_at": time.time(), "delay": float(st["delay"]), "outcome": st["outcome"]}
        if f == "lost":
            return JSONResponse({"errorCode": "GATEWAY_TIMEOUT"}, 504)
        return JSONResponse({"envelopeId": eid, "status": "sent", "statusDateTime": _iso(),
                             "uri": f"/envelopes/{eid}"}, 201)

    @app.get("/docusign/restapi/v2.1/accounts/{acct}/envelopes")
    async def ds_list(acct: str, request: Request, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization):
            return JSONResponse({"errorCode": "USER_AUTHENTICATION_FAILED"}, 401)
        q = request.query_params
        if not q.get("from_date"):
            return JSONResponse({"errorCode": "INVALID_REQUEST_PARAMETER", "message": "from_date is required"}, 400)
        tick()
        name, _, value = (q.get("custom_field") or "").partition("=")
        hits = [ds_env_out(e) for e in st["envelopes"].values()
                if not name or any(c.get("name") == name and c.get("value") == value for c in e["custom"])]
        return {"envelopes": hits, "resultSetSize": str(len(hits)), "totalSetSize": str(len(hits))}

    @app.get("/docusign/restapi/v2.1/accounts/{acct}/envelopes/{eid}")
    async def ds_get(acct: str, eid: str, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization):
            return JSONResponse({"errorCode": "USER_AUTHENTICATION_FAILED"}, 401)
        if (f := fault("ds_status")) is not None:
            return err(f, "ds")
        tick()
        e = st["envelopes"].get(eid)
        if e is None:
            return JSONResponse({"errorCode": "ENVELOPE_DOES_NOT_EXIST"}, 404)
        return ds_env_out(e)

    @app.put("/docusign/restapi/v2.1/accounts/{acct}/envelopes/{eid}")
    async def ds_void(acct: str, eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization):
            return JSONResponse({"errorCode": "USER_AUTHENTICATION_FAILED"}, 401)
        tick()
        b = await request.json()
        e = st["envelopes"].get(eid)
        if e is None:
            return JSONResponse({"errorCode": "ENVELOPE_DOES_NOT_EXIST"}, 404)
        if b.get("status") != "voided" or not b.get("voidedReason"):
            return JSONResponse({"errorCode": "INVALID_REQUEST_PARAMETER", "message": "voidedReason is required"}, 400)
        if e["status"] not in ("sent", "delivered"):
            return JSONResponse({"errorCode": "ENVELOPE_CANNOT_VOID_INVALID_STATE", "message": "Only sent or delivered envelopes may be voided."}, 400)
        e["status"], e["voidedReason"] = "voided", b["voidedReason"]
        callback("DOCUSIGN", e, "envelope-voided")
        return {"envelopeId": eid}

    @app.get("/docusign/restapi/v2.1/accounts/{acct}/envelopes/{eid}/documents/{doc}")
    async def ds_doc(acct: str, eid: str, doc: str, authorization: Optional[str] = Header(None)):
        if not bearer("ds", authorization):
            return JSONResponse({"errorCode": "USER_AUTHENTICATION_FAILED"}, 401)
        e = st["envelopes"].get(eid)
        if e is None or doc not in ("combined", "certificate"):
            return JSONResponse({"errorCode": "ENVELOPE_DOES_NOT_EXIST"}, 404)
        if (f := fault("ds_docs")) == "nopdf":
            return Response(b"<html>not a pdf</html>", media_type="text/html")
        if f is not None:
            return err(f, "ds")
        if doc == "certificate":
            return Response(_mini_pdf(f"Certificate of Completion (SIMULATED) envelope {eid} status {e['status']}"), media_type="application/pdf")
        return Response(e["pdf"] + f"\n% signed (SIMULATED) envelope {eid}\n".encode(), media_type="application/pdf")

    # ── Acrobat Sign OAuth refresh + REST v6 ─────────────────────────────────
    @app.post("/adobe/oauth/v2/refresh")
    async def ad_refresh(request: Request):
        if (f := fault("ad_token")) is not None:
            return err(f, "ad")
        form = dict(await request.form())
        if form.get("grant_type") != "refresh_token":
            return JSONResponse({"error": "unsupported_grant_type"}, 400)
        if (form.get("client_id"), form.get("client_secret")) != (st["adobe_client"], st["adobe_secret"]):
            return JSONResponse({"error": "invalid_client"}, 401)
        if form.get("refresh_token") != st["adobe_refresh"]:
            return JSONResponse({"error": "invalid_request", "error_description": "INVALID_TOKEN"}, 400)
        tok = "sim-ad-" + secrets.token_urlsafe(16)
        st["tokens"][tok] = "ad"
        return {"access_token": tok, "token_type": "Bearer", "expires_in": 3600}

    def ad_auth(authorization):
        return None if bearer("ad", authorization) else JSONResponse({"code": "INVALID_ACCESS_TOKEN", "message": "Access token provided is invalid or has expired"}, 401)

    @app.post("/adobe/api/rest/v6/transientDocuments")
    async def ad_transient(request: Request, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        form = await request.form()
        f = form.get("File")
        data = await f.read() if f is not None and hasattr(f, "read") else b""
        if not data.startswith(b"%PDF-") or form.get("Mime-Type") != "application/pdf" or not form.get("File-Name"):
            return JSONResponse({"code": "INVALID_FILE", "message": "File is missing or not a PDF"}, 400)
        tid = "sim-transient-" + secrets.token_hex(8)
        st["transient"][tid] = data
        return JSONResponse({"transientDocumentId": tid}, 201)

    @app.post("/adobe/api/rest/v6/agreements")
    async def ad_create(request: Request, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        f = fault("ad_create")
        if f not in (None, "lost"):
            return err(f, "ad")
        b = await request.json()
        st["requests"].append({"op": "ad_create", "body": b})
        try:
            pdf = st["transient"].pop(b["fileInfos"][0]["transientDocumentId"])
            ps = b["participantSetsInfo"][0]
            ok = (ps["role"] == "SIGNER" and ps["order"] == 1 and ps["memberInfos"][0]["email"] and b["name"]
                  and b["signatureType"] in ("ESIGN", "WRITTEN") and b["state"] == "IN_PROCESS")
        except (KeyError, IndexError, TypeError):
            ok = False
        if not ok:
            return JSONResponse({"code": "INVALID_ARGUMENTS", "message": "Invalid agreement request"}, 400)
        aid = "CBJCHBCAABAA" + secrets.token_hex(10)
        st["agreements"][aid] = {"id": aid, "name": b["name"], "status": "OUT_FOR_SIGNATURE", "pdf": pdf,
                                 "externalId": b.get("externalId"), "events": [{"type": "CREATED", "date": _iso()}],
                                 "sent_at": time.time(), "delay": float(st["delay"]), "outcome": st["outcome"]}
        if f == "lost":
            return JSONResponse({"code": "MISC_SERVER_ERROR"}, 504)
        return JSONResponse({"id": aid}, 201)

    @app.get("/adobe/api/rest/v6/agreements")
    async def ad_list(pageSize: int = 100, cursor: Optional[str] = None, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        tick()
        items = list(st["agreements"].values())
        off, size = int(cursor or 0), min(pageSize, st["page_size"])
        page = items[off:off + size]
        out = {"userAgreementList": [{"id": a["id"], "name": a["name"], "status": a["status"]} for a in page], "page": {}}
        if off + size < len(items):
            out["page"]["nextCursor"] = str(off + size)
        return out

    @app.get("/adobe/api/rest/v6/agreements/{aid}")
    async def ad_get(aid: str, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        if (f := fault("ad_status")) is not None:
            return err(f, "ad")
        tick()
        a = st["agreements"].get(aid)
        if a is None:
            return JSONResponse({"code": "INVALID_AGREEMENT_ID", "message": "The Agreement ID specified is invalid."}, 404)
        return {"id": aid, "name": a["name"], "status": a["status"], "signatureType": "ESIGN",
                "externalId": None if st["strip_ref"] else a["externalId"]}

    @app.get("/adobe/api/rest/v6/agreements/{aid}/events")
    async def ad_events(aid: str, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        a = st["agreements"].get(aid)
        return {"events": a["events"]} if a else JSONResponse({"code": "INVALID_AGREEMENT_ID"}, 404)

    @app.put("/adobe/api/rest/v6/agreements/{aid}/state")
    async def ad_state(aid: str, request: Request, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        tick()
        a, b = st["agreements"].get(aid), await request.json()
        if a is None:
            return JSONResponse({"code": "INVALID_AGREEMENT_ID"}, 404)
        if b.get("state") != "CANCELLED":
            return JSONResponse({"code": "INVALID_STATE", "message": "Only CANCELLED is supported here"}, 400)
        if a["status"] != "OUT_FOR_SIGNATURE":
            return JSONResponse({"code": "AGREEMENT_NOT_EXPOSED", "message": "Agreement is not in a cancellable state"}, 400)
        a["status"] = "CANCELLED"
        a["events"].append({"type": "RECALLED", "date": _iso(), "comment": (b.get("agreementCancellationInfo") or {}).get("comment")})
        callback("ADOBE_SIGN", a, "AGREEMENT_RECALLED")
        return Response(status_code=204)

    @app.get("/adobe/api/rest/v6/agreements/{aid}/{doc}")
    async def ad_doc(aid: str, doc: str, authorization: Optional[str] = Header(None)):
        if (r := ad_auth(authorization)) is not None:
            return r
        a = st["agreements"].get(aid)
        if a is None or doc not in ("combinedDocument", "auditTrail"):
            return JSONResponse({"code": "INVALID_AGREEMENT_ID"}, 404)
        if (f := fault("ad_docs")) == "nopdf":
            return Response(b"{}", media_type="application/json")
        if f is not None:
            return err(f, "ad")
        if doc == "auditTrail":
            return Response(_mini_pdf(f"Audit report (SIMULATED) agreement {aid} status {a['status']}"), media_type="application/pdf")
        return Response(a["pdf"] + f"\n% signed (SIMULATED) agreement {aid}\n".encode(), media_type="application/pdf")

    app.state.sim = st
    return app


if __name__ == "__main__":      # browser walkthrough: python -m tests.provider_sim.esign_app --port 8766 (loopback only)
    import argparse

    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    uvicorn.run(create_esign_app(), host="127.0.0.1", port=ap.parse_args().port)
