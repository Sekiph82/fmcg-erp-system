"""Local Pesapal API 3.0 simulator (M48.S01.T010), synthetic, local only. Contract as documented at
https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/api-reference (paths under /pesapalv3, like the
sandbox https://cybqa.pesapal.com/pesapalv3):
  POST /api/Auth/RequestToken, POST /api/URLSetup/RegisterIPN, GET /api/URLSetup/GetIpnList,
  POST /api/Transactions/SubmitOrderRequest, GET /api/Transactions/GetTransactionStatus, POST /api/Transactions/RefundRequest.
Application errors come back as HTTP 200 with {"error": {...}, "status": "500"} like Pesapal; a bad bearer is 401.
Test controls (not Pesapal): POST /_sim/pay {order_tracking_id, outcome: completed|failed|invalid, after_polls, amount,
currency} — the payer's result on the hosted page, visible only after `after_polls` status queries (delayed status);
POST /_sim/fail {count} — next N API calls answer 503; refunds turn the order REVERSED after `refund_after_polls` queries.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

SIM_KEY, SIM_SECRET = "povu-sim-consumer-key", "povu-sim-consumer-secret"
BASE = "http://pesapal-sim.test/pesapalv3"
CODES = {"INVALID": 0, "COMPLETED": 1, "FAILED": 2, "REVERSED": 3}


def _err(code: str, msg: str = "") -> dict:
    return {"error": {"error_type": "api_error", "code": code, "message": msg}, "status": "500"}


def create_card_app() -> FastAPI:
    app = FastAPI(title="POVU Pesapal simulator (synthetic, local only)")
    st = app.state.sim = {"tokens": set(), "ipns": {}, "orders": {}, "fail": 0, "calls": [], "refunds": [],
                          "refund_after_polls": 1}

    def authed(authorization) -> bool:
        return bool(authorization and authorization.startswith("Bearer ") and authorization[7:] in st["tokens"])

    @app.middleware("http")
    async def faults(request: Request, call_next):
        if not request.url.path.startswith("/pesapalv3/_sim"):
            st["calls"].append((request.method, request.url.path))
            if st["fail"] > 0:
                st["fail"] -= 1
                return JSONResponse({"message": "Service Unavailable"}, 503)
        return await call_next(request)

    @app.post("/pesapalv3/api/Auth/RequestToken")
    async def token(request: Request):
        b = await request.json()
        if (b.get("consumer_key"), b.get("consumer_secret")) != (SIM_KEY, SIM_SECRET):
            return {"token": None, "expiryDate": None, **_err("invalid_consumer_key_or_secret_provided"), "message": ""}
        t = secrets.token_urlsafe(24)
        st["tokens"].add(t)
        exp = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        return {"token": t, "expiryDate": exp, "error": None, "status": "200", "message": "Request processed successfully"}

    @app.post("/pesapalv3/api/URLSetup/RegisterIPN")
    async def register_ipn(request: Request, authorization: str | None = Header(None)):
        if not authed(authorization):
            return JSONResponse({"message": "Unauthorized"}, 401)
        b = await request.json()
        if not str(b.get("url", "")).startswith("http") or b.get("ipn_notification_type") not in ("GET", "POST"):
            return _err("invalid_ipn_details", "url and ipn_notification_type GET|POST are required")
        ipn = str(uuid.uuid4())
        st["ipns"][ipn] = b
        return {"url": b["url"], "created_date": datetime.now(timezone.utc).isoformat(), "ipn_id": ipn,
                "notification_type": 0 if b["ipn_notification_type"] == "GET" else 1, "ipn_status": 1,
                "error": None, "status": "200"}

    @app.get("/pesapalv3/api/URLSetup/GetIpnList")
    async def ipn_list(authorization: str | None = Header(None)):
        if not authed(authorization):
            return JSONResponse({"message": "Unauthorized"}, 401)
        return [{"url": v["url"], "ipn_id": k, "ipn_status": 1} for k, v in st["ipns"].items()]

    @app.post("/pesapalv3/api/Transactions/SubmitOrderRequest")
    async def submit(request: Request, authorization: str | None = Header(None)):
        if not authed(authorization):
            return JSONResponse({"message": "Unauthorized"}, 401)
        b = await request.json()
        ba = b.get("billing_address") or {}
        if not b.get("id") or len(str(b["id"])) > 50 or len(str(b.get("description", ""))) > 100:
            return _err("invalid_order_details", "id (max 50) and description (max 100) are required")
        if b.get("notification_id") not in st["ipns"]:
            return _err("invalid_notification_id", "register the IPN URL first")
        if not (ba.get("email_address") or ba.get("phone_number")) or not str(b.get("callback_url", "")).startswith("http"):
            return _err("invalid_order_details", "billing email or phone and callback_url are required")
        if not isinstance(b.get("amount"), (int, float)) or b["amount"] <= 0 or b.get("currency") not in ("KES", "USD"):
            return _err("invalid_amount", "amount > 0 and a supported currency are required")
        tid = str(uuid.uuid4())
        st["orders"][tid] = {"ref": b["id"], "amount": float(b["amount"]), "currency": b["currency"], "state": "PENDING",
                             "outcome": None, "after": 0, "polls": 0, "code": None, "paid_amount": None,
                             "paid_currency": None, "refund_polls": None}
        return {"order_tracking_id": tid, "merchant_reference": b["id"],
                "redirect_url": f"{BASE}/iframe/PesapalIframe3/Index?OrderTrackingId={tid}", "error": None, "status": "200"}

    @app.get("/pesapalv3/api/Transactions/GetTransactionStatus")
    async def status(orderTrackingId: str = "", authorization: str | None = Header(None)):
        if not authed(authorization):
            return JSONResponse({"message": "Unauthorized"}, 401)
        o = st["orders"].get(orderTrackingId)
        if o is None:
            return {**_err("invalid_order_tracking_id", "order not found"), "status_code": None}
        o["polls"] += 1
        if o["state"] == "PENDING" and o["outcome"] and o["polls"] >= o["after"]:
            o["state"] = o["outcome"]
            if o["state"] == "COMPLETED":
                o["code"] = f"SIM{secrets.token_hex(4).upper()}"
        if o["refund_polls"] is not None:
            o["refund_polls"] -= 1
            if o["refund_polls"] <= 0:
                o["state"], o["refund_polls"] = "REVERSED", None
        state = "INVALID" if o["state"] == "PENDING" else o["state"]   # unpaid orders read INVALID (status_code 0)
        return {"payment_method": "Visa" if o["code"] else "", "amount": o["paid_amount"] or o["amount"],
                "created_date": datetime.now(timezone.utc).isoformat(), "confirmation_code": o["code"] or "",
                "payment_status_description": state, "description": "", "message": "Request processed successfully",
                "payment_account": "476173**0010" if o["code"] else "", "call_back_url": "",
                "status_code": CODES[state], "merchant_reference": o["ref"], "payment_status_code": "",
                "currency": o["paid_currency"] or o["currency"], "error": {"error_type": None, "code": None,
                                                                          "message": None, "call_back_url": None},
                "status": "200"}

    @app.post("/pesapalv3/api/Transactions/RefundRequest")
    async def refund(request: Request, authorization: str | None = Header(None)):
        if not authed(authorization):
            return JSONResponse({"message": "Unauthorized"}, 401)
        b = await request.json()
        st["refunds"].append(b)
        o = next((o for o in st["orders"].values() if o["code"] and o["code"] == b.get("confirmation_code")), None)
        if o is None or o["state"] != "COMPLETED":
            return {"status": "500", "message": "Refund rejected: payment not found or not completed"}
        if o.get("refunded"):
            return {"status": "500", "message": "Refund rejected: multiple refunds are not allowed"}
        try:
            amt = float(b.get("amount"))
        except (TypeError, ValueError):
            return {"status": "500", "message": "Refund rejected: invalid amount"}
        if amt <= 0 or amt > (o["paid_amount"] or o["amount"]) or not b.get("username") or not b.get("remarks"):
            return {"status": "500", "message": "Refund rejected: invalid amount, username or remarks"}
        o["refunded"], o["refund_polls"] = True, st["refund_after_polls"]
        return {"status": "200", "message": "Refund request successfully"}

    # -- test controls --
    @app.post("/pesapalv3/_sim/pay")
    async def sim_pay(request: Request):
        b = await request.json()
        o = st["orders"][b["order_tracking_id"]]
        o["outcome"], o["after"], o["polls"] = b["outcome"].upper(), int(b.get("after_polls", 0)), 0
        o["paid_amount"], o["paid_currency"] = b.get("amount"), b.get("currency")
        return {"ok": True}

    @app.post("/pesapalv3/_sim/fail")
    async def sim_fail(request: Request):
        st["fail"] = int((await request.json()).get("count", 1))
        return {"ok": True}

    return app
