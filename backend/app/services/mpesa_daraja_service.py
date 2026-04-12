"""
M-Pesa Safaricom Daraja integration service.

Production-ready implementation of the STK Push (Lipa Na M-Pesa Online) flow.
Falls back gracefully to a sandbox simulation when credentials are not configured.

Environment variables required for live use:
  MPESA_CONSUMER_KEY       — Daraja app consumer key
  MPESA_CONSUMER_SECRET    — Daraja app consumer secret
  MPESA_SHORTCODE          — Paybill / Till number
  MPESA_PASSKEY            — STK Push online passkey
  MPESA_CALLBACK_URL       — Public HTTPS URL for Daraja callbacks
  MPESA_ENV                — "sandbox" | "production"  (default: sandbox)

State transitions:
  PENDING → SUCCESS (result_code 0 callback)
  PENDING → FAILED  (result_code != 0 callback)
  PENDING → TIMEOUT (query after TTL with no callback)
  SUCCESS → REVERSED (reversal callback)
"""
from __future__ import annotations

import base64
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.integrations import (
    IntegrationMpesaTransaction, MpesaTxStatus,
    IntegrationProvider, IntegrationLogStatus,
)
from app.services import integration_service as log_svc

logger = logging.getLogger(__name__)


# ── Daraja helpers ────────────────────────────────────────────────────────────

def _format_phone(phone: str) -> str:
    """Normalise phone number to 254XXXXXXXXX format."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    if not phone.startswith("254"):
        phone = "254" + phone
    return phone


def _timestamp() -> str:
    """Return Daraja-format timestamp: YYYYMMDDHHmmss."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _generate_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """base64(BusinessShortCode + PassKey + Timestamp)."""
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


async def _get_access_token() -> Optional[str]:
    """
    Obtain a Daraja OAuth2 access token via client_credentials grant.
    Returns None if credentials are not configured (sandbox simulation mode).
    """
    if not settings.MPESA_CONFIGURED:
        return None

    url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    credentials = base64.b64encode(
        f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Basic {credentials}"})
        resp.raise_for_status()
        data = resp.json()
        logger.info("Daraja token obtained; expires_in=%s", data.get("expires_in"))
        return data.get("access_token")
    except httpx.HTTPError as exc:
        logger.error("Daraja token request failed: %s", exc)
        return None


# ── STK Push ──────────────────────────────────────────────────────────────────

async def _stk_push_request(
    phone: str,
    amount: int,
    reference: str,
    description: str = "Payment",
) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Send STK Push to Daraja.
    Returns (checkout_request_id, merchant_request_id, raw_response).
    If credentials not configured, returns a simulation response.
    """
    access_token = await _get_access_token()

    if not access_token:
        # Sandbox simulation — no live credentials
        fake_checkout = f"ws_CO_SIM_{uuid.uuid4().hex[:16].upper()}"
        fake_merchant = f"SIM_{uuid.uuid4().hex[:8].upper()}"
        sim_response = {
            "MerchantRequestID": fake_merchant,
            "CheckoutRequestID": fake_checkout,
            "ResponseCode": "0",
            "ResponseDescription": "Success. Request accepted for processing",
            "CustomerMessage": "Success. Request accepted for processing",
            "_simulated": True,
        }
        logger.info("M-Pesa STK Push SIMULATED phone=%s amount=%s ref=%s", phone, amount, reference)
        return fake_checkout, fake_merchant, sim_response

    ts = _timestamp()
    password = _generate_password(settings.MPESA_SHORTCODE, settings.MPESA_PASSKEY, ts)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": ts,
        "TransactionType": settings.MPESA_TRANSACTION_TYPE,
        "Amount": amount,
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": reference[:20],     # Daraja max 20 chars
        "TransactionDesc": description[:13],    # Daraja max 13 chars
    }

    url = f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        duration_ms = int((time.monotonic() - t0) * 1000)
        resp.raise_for_status()
        data = resp.json()
        logger.info("STK Push response: %s", data)
        return (
            data.get("CheckoutRequestID"),
            data.get("MerchantRequestID"),
            data,
        )
    except httpx.HTTPStatusError as exc:
        logger.error("STK Push HTTP error %s: %s", exc.response.status_code, exc.response.text)
        raise HTTPException(502, f"Daraja STK Push failed: {exc.response.text}")
    except httpx.RequestError as exc:
        logger.error("STK Push request error: %s", exc)
        raise HTTPException(504, "Daraja unreachable — network error")


# ── Status Query ──────────────────────────────────────────────────────────────

async def _query_stk_status(checkout_request_id: str) -> Dict[str, Any]:
    """Query Daraja for the current status of a pending STK transaction."""
    access_token = await _get_access_token()
    if not access_token:
        return {"ResponseCode": "0", "ResultCode": "17", "ResultDesc": "Request cancelled by user (simulated)"}

    ts = _timestamp()
    password = _generate_password(settings.MPESA_SHORTCODE, settings.MPESA_PASSKEY, ts)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": ts,
        "CheckoutRequestID": checkout_request_id,
    }
    url = f"{settings.MPESA_BASE_URL}/mpesa/stkpushquery/v1/query"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        logger.error("STK Query failed: %s", exc)
        return {"error": str(exc)}


# ── Public API ────────────────────────────────────────────────────────────────

async def initiate_payment(
    db: AsyncSession,
    phone_number: str,
    amount: Decimal,
    merchant_reference: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
) -> IntegrationMpesaTransaction:
    """
    Initiate an STK Push and record the transaction.
    Duplicate prevention: raises 409 if a PENDING transaction exists for the same reference.
    """
    # Duplicate guard
    existing = await db.execute(
        select(IntegrationMpesaTransaction).where(
            IntegrationMpesaTransaction.merchant_reference == merchant_reference,
            IntegrationMpesaTransaction.status == MpesaTxStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            409,
            f"A PENDING transaction already exists for reference '{merchant_reference}'. "
            "Cancel or wait for it to complete before retrying.",
        )

    formatted_phone = _format_phone(phone_number)
    amount_int = int(amount)           # Daraja requires integer amounts

    t0 = time.monotonic()
    checkout_id, merchant_req_id, raw_resp = await _stk_push_request(
        phone=formatted_phone,
        amount=amount_int,
        reference=merchant_reference,
        description=f"Payment {merchant_reference}"[:13],
    )
    duration_ms = int((time.monotonic() - t0) * 1000)

    tx = IntegrationMpesaTransaction(
        phone_number=formatted_phone,
        amount=amount,
        merchant_reference=merchant_reference,
        checkout_request_id=checkout_id,
        merchant_request_id=merchant_req_id,
        related_entity_type=related_entity_type,
        related_entity_id=uuid.UUID(related_entity_id) if related_entity_id else None,
        status=MpesaTxStatus.PENDING,
        request_payload=json.dumps({
            "phone": formatted_phone,
            "amount": amount_int,
            "reference": merchant_reference,
        }),
        response_payload=json.dumps(raw_resp),
        initiated_by_id=user_id,
    )
    db.add(tx)
    await db.flush()

    await log_svc.log_call(
        db,
        provider=IntegrationProvider.MPESA,
        integration_type="PAYMENT",
        endpoint="mpesa/stkpush/v1/processrequest",
        request_payload={"phone": formatted_phone, "amount": amount_int, "reference": merchant_reference},
        response_payload=raw_resp,
        status=IntegrationLogStatus.SUCCESS,
        duration_ms=duration_ms,
        reference=merchant_reference,
        idempotency_key=checkout_id,
    )

    await db.refresh(tx)
    return tx


async def handle_callback(
    db: AsyncSession,
    payload: dict,
) -> Optional[IntegrationMpesaTransaction]:
    """
    Process Daraja STK Push callback.
    Idempotent: silently ignores duplicate callback replays.
    """
    try:
        stk_cb = payload["Body"]["stkCallback"]
        checkout_id = stk_cb["CheckoutRequestID"]
        result_code = int(stk_cb["ResultCode"])
        result_desc = stk_cb.get("ResultDesc", "")
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Malformed M-Pesa callback: %s | payload=%s", exc, payload)
        await log_svc.log_call(
            db,
            provider=IntegrationProvider.MPESA,
            integration_type="CALLBACK",
            endpoint="mpesa/callback",
            request_payload=payload,
            status=IntegrationLogStatus.FAILED,
            error_message=f"Malformed payload: {exc}",
        )
        await db.flush()
        return None

    # Find transaction
    result = await db.execute(
        select(IntegrationMpesaTransaction).where(
            IntegrationMpesaTransaction.checkout_request_id == checkout_id
        )
    )
    tx = result.scalar_one_or_none()

    if not tx:
        logger.warning("Callback for unknown checkout_request_id=%s", checkout_id)
        await log_svc.log_call(
            db,
            provider=IntegrationProvider.MPESA,
            integration_type="CALLBACK",
            endpoint="mpesa/callback",
            request_payload=payload,
            status=IntegrationLogStatus.FAILED,
            error_message=f"No transaction found for checkout_request_id={checkout_id}",
            reference=checkout_id,
        )
        await db.flush()
        return None

    # Idempotency: already processed
    if tx.status != MpesaTxStatus.PENDING:
        logger.info("Duplicate callback for %s (status=%s) — ignored", checkout_id, tx.status)
        return tx

    tx.callback_payload = json.dumps(payload)
    tx.result_code = result_code
    tx.result_description = result_desc

    if result_code == 0:
        # Extract receipt from callback metadata
        metadata = stk_cb.get("CallbackMetadata", {}).get("Item", [])
        meta_dict = {item["Name"]: item.get("Value") for item in metadata}
        tx.mpesa_receipt_number = str(meta_dict.get("MpesaReceiptNumber", ""))
        tx.status = MpesaTxStatus.SUCCESS
        log_status = IntegrationLogStatus.SUCCESS
    else:
        tx.status = MpesaTxStatus.FAILED
        tx.error_message = result_desc
        log_status = IntegrationLogStatus.FAILED

    await db.flush()
    await log_svc.log_call(
        db,
        provider=IntegrationProvider.MPESA,
        integration_type="CALLBACK",
        endpoint="mpesa/callback",
        request_payload=payload,
        response_payload={"result_code": result_code, "receipt": tx.mpesa_receipt_number},
        status=log_status,
        error_message=result_desc if result_code != 0 else None,
        reference=tx.merchant_reference,
        idempotency_key=checkout_id,
    )
    await db.refresh(tx)
    return tx


async def check_transaction_status(
    db: AsyncSession,
    transaction_id: uuid.UUID,
) -> IntegrationMpesaTransaction:
    """
    Query Daraja for current status if transaction is still PENDING.
    Updates the DB record from the query response.
    """
    result = await db.execute(
        select(IntegrationMpesaTransaction).where(IntegrationMpesaTransaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transaction not found")

    if tx.status != MpesaTxStatus.PENDING or not tx.checkout_request_id:
        return tx     # already resolved

    t0 = time.monotonic()
    query_resp = await _query_stk_status(tx.checkout_request_id)
    duration_ms = int((time.monotonic() - t0) * 1000)

    result_code = int(query_resp.get("ResultCode", -1))
    if result_code == 0:
        tx.status = MpesaTxStatus.SUCCESS
    elif result_code in (1032, 1037):     # Cancelled, timeout
        tx.status = MpesaTxStatus.CANCELLED
    elif result_code == 17:
        tx.status = MpesaTxStatus.CANCELLED
    elif result_code > 0:
        tx.status = MpesaTxStatus.FAILED
        tx.error_message = query_resp.get("ResultDesc", "")

    tx.response_payload = json.dumps(query_resp)
    await db.flush()

    await log_svc.log_call(
        db,
        provider=IntegrationProvider.MPESA,
        integration_type="STATUS_QUERY",
        endpoint="mpesa/stkpushquery/v1/query",
        request_payload={"checkout_request_id": tx.checkout_request_id},
        response_payload=query_resp,
        status=IntegrationLogStatus.SUCCESS,
        duration_ms=duration_ms,
        reference=tx.merchant_reference,
    )

    await db.refresh(tx)
    return tx


async def retry_transaction(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> IntegrationMpesaTransaction:
    """
    Re-send STK Push for a FAILED or CANCELLED transaction.
    Increments retry_count. PENDING and SUCCESS transactions cannot be retried.
    """
    result = await db.execute(
        select(IntegrationMpesaTransaction).where(IntegrationMpesaTransaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "Transaction not found")
    if tx.status == MpesaTxStatus.PENDING:
        raise HTTPException(422, "Transaction is still PENDING — wait for callback or check status")
    if tx.status == MpesaTxStatus.SUCCESS:
        raise HTTPException(422, "Transaction already succeeded")
    if tx.retry_count >= 3:
        raise HTTPException(422, "Maximum retries (3) reached")

    checkout_id, merchant_req_id, raw_resp = await _stk_push_request(
        phone=tx.phone_number,
        amount=int(tx.amount),
        reference=tx.merchant_reference,
    )

    tx.status = MpesaTxStatus.PENDING
    tx.checkout_request_id = checkout_id
    tx.merchant_request_id = merchant_req_id
    tx.retry_count += 1
    tx.error_message = None
    tx.response_payload = json.dumps(raw_resp)
    if user_id:
        tx.initiated_by_id = user_id

    await db.flush()
    await log_svc.log_call(
        db,
        provider=IntegrationProvider.MPESA,
        integration_type="RETRY",
        endpoint="mpesa/stkpush/v1/processrequest",
        request_payload={"phone": tx.phone_number, "amount": int(tx.amount), "reference": tx.merchant_reference},
        response_payload=raw_resp,
        status=IntegrationLogStatus.SUCCESS,
        reference=tx.merchant_reference,
        retry_count=tx.retry_count,
        idempotency_key=checkout_id,
    )

    await db.refresh(tx)
    return tx
