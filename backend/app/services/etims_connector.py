"""
KRA eTIMS connector — provider-neutral adapter interface.

Architecture:
  ERP → build_etims_payload() → ETIMSConnector.submit_invoice() → provider

Provider routing:
  ETIMS_PROVIDER=simulation (default) → SimulationETIMSConnector (no network)
  ETIMS_PROVIDER=http               → HttpETIMSConnector (skeleton, live when configured)

The final provider (direct KRA OSCU/VSCU, certified middleware, or third-party)
is NOT yet confirmed. Keep ETIMS_PROVIDER=simulation until KRA sandbox credentials
and official API spec are validated.

Failure simulation (test/demo only — normal path unaffected):
  Pass _simulate_reject=True or _simulate_error=True in payload to trigger
  REJECTED or ERROR responses from SimulationETIMSConnector.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


# ── Provider-neutral response contract ────────────────────────────────────────

@dataclass
class ETimsConnectorResponse:
    """
    Provider-neutral response returned by every ETIMSConnector method.
    All connector implementations must populate these fields.
    """
    success: bool
    status: str                             # maps to ETimsStatus enum value
    provider_name: str                      # e.g. "simulation", "kra_direct"
    environment: str                        # "simulation", "sandbox", "production"
    provider_reference: str | None = None   # provider's own submission ID
    control_unit_invoice_no: str | None = None
    signed_invoice_hash: str | None = None
    invoice_qr_data: str | None = None
    kra_response_code: str | None = None
    kra_response_message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    accepted_at: datetime | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


# Backward-compat alias — existing code that imports ETIMSResult still works
ETIMSResult = ETimsConnectorResponse


# ── Provider-neutral connector interface ──────────────────────────────────────

@runtime_checkable
class ETIMSConnector(Protocol):
    """
    Provider-neutral adapter interface. All connector implementations must
    implement submit_invoice. cancel_invoice, get_submission_status, and
    health_check are optional for stub providers.
    """
    async def submit_invoice(self, payload: dict[str, Any]) -> ETimsConnectorResponse: ...

    async def cancel_invoice(
        self, provider_reference: str, reason: str
    ) -> ETimsConnectorResponse: ...

    async def get_submission_status(
        self, provider_reference: str
    ) -> ETimsConnectorResponse: ...

    async def health_check(self) -> dict[str, Any]: ...


# Legacy alias — submit_sales_invoice is still accepted by SimulationETIMSConnector
# to avoid breaking the existing endpoint call site until Step 5 migration.
# New code should call submit_invoice().


# ── Payload builder ────────────────────────────────────────────────────────────

def build_etims_payload(invoice: Any, settings: Any) -> dict[str, Any]:
    """
    Build a KRA eTIMS-compatible saveSales payload from an Invoice instance.

    Requires invoice.lines to be eagerly loaded before calling.
    KRA item classification codes (itemCd / taxTyCd) are marked TODO
    because the Product model does not yet carry eTIMS-specific fields.
    """
    lines = []
    for idx, line in enumerate(getattr(invoice, "lines", []), start=1):
        product = getattr(line, "product", None)
        lines.append({
            "itemSeq": idx,
            "itemNm": (product.name if product else None) or (line.description or ""),
            # TODO: populate itemCd from Product.etims_item_code once field is added
            "itemCd": "",
            # TODO: populate taxTyCd from Product.tax_type_code once field is added
            "taxTyCd": "VAT",
            "qty": float(line.quantity),
            "unitPrice": float(line.unit_price),
            "discountRt": float(line.discount_pct),
            "taxRt": float(line.tax_rate),
            "taxAmt": float(line.line_total) * float(line.tax_rate),
            "lineTotal": float(line.line_total),
        })

    customer = getattr(invoice, "customer", None)
    return {
        "tin": settings.ETIMS_PIN or "",
        "bhfId": settings.ETIMS_BRANCH_ID or "",
        "sdcId": settings.ETIMS_DEVICE_SERIAL_NO or "",
        "invoiceNo": invoice.invoice_no,
        "invoiceDate": str(invoice.invoice_date),
        "custNm": (customer.name if customer else None) or "",
        "custTin": (customer.tax_id if customer else None) or "",
        "currency": getattr(invoice, "currency", "KES"),
        "subtotal": float(invoice.subtotal),
        "taxAmt": float(invoice.tax_amount),
        "totalAmt": float(invoice.total_amount),
        "itemList": lines,
    }


# ── Simulation connector ───────────────────────────────────────────────────────

class SimulationETIMSConnector:
    """
    Simulation connector — no network calls, deterministic responses.

    Supports failure simulation via payload test flags (demo/test use only):
      _simulate_reject=True  → returns REJECTED (provider refusal)
      _simulate_error=True   → returns ERROR (system error)
    Normal submissions always return ACCEPTED.
    """

    PROVIDER_NAME = "simulation"
    ENVIRONMENT = "simulation"

    async def submit_invoice(self, payload: dict[str, Any]) -> ETimsConnectorResponse:
        invoice_no = payload.get("invoiceNo", "UNKNOWN")
        invoice_date = payload.get("invoiceDate", str(datetime.now(timezone.utc).date()))
        total = payload.get("totalAmt", 0)

        invoice_hash = hashlib.sha256(
            f"{invoice_no}:{total}:{invoice_date}".encode()
        ).hexdigest()
        provider_ref = f"SIM-ETIMS-{invoice_no}-{invoice_hash[:8].upper()}"

        # Failure simulation (test/demo — payload flags only, never affects normal path)
        if payload.get("_simulate_reject"):
            return ETimsConnectorResponse(
                success=False,
                status="REJECTED",
                provider_name=self.PROVIDER_NAME,
                environment=self.ENVIRONMENT,
                provider_reference=provider_ref,
                kra_response_code="REJECT-001",
                kra_response_message="Simulated rejection — invoice failed KRA validation",
                error_code="REJECT-001",
                error_message="Simulated rejection for testing",
                raw_response={"simulationMode": True, "reject": True},
            )

        if payload.get("_simulate_error"):
            return ETimsConnectorResponse(
                success=False,
                status="ERROR",
                provider_name=self.PROVIDER_NAME,
                environment=self.ENVIRONMENT,
                provider_reference=provider_ref,
                kra_response_code="ERR-500",
                kra_response_message="Simulated system error",
                error_code="ERR-500",
                error_message="Simulated system error for testing",
                raw_response={"simulationMode": True, "error": True},
            )

        # Normal path — ACCEPTED
        tims_serial = f"KRA-{invoice_no}-{invoice_date.replace('-', '')}"
        qr_data = (
            f"INV={invoice_no}|DATE={invoice_date}"
            f"|TOTAL={total}|HASH={invoice_hash[:16]}"
        )
        accepted_at = datetime.now(timezone.utc)
        return ETimsConnectorResponse(
            success=True,
            status="ACCEPTED",
            provider_name=self.PROVIDER_NAME,
            environment=self.ENVIRONMENT,
            provider_reference=provider_ref,
            control_unit_invoice_no=tims_serial,
            signed_invoice_hash=invoice_hash,
            invoice_qr_data=qr_data,
            kra_response_code="00",
            kra_response_message=(
                "Accepted (simulation mode — configure ETIMS_API_URL and "
                "ETIMS_PROVIDER=http for live integration)"
            ),
            accepted_at=accepted_at,
            raw_response={
                "simulationMode": True,
                "rcptNo": tims_serial,
                "signedInvoiceHash": invoice_hash,
                "qrCode": qr_data,
                "resultCd": "00",
                "resultMsg": "Accepted",
                "acceptedAt": accepted_at.isoformat(),
            },
        )

    # Legacy entry point — keeps existing endpoint call site working unchanged
    async def submit_sales_invoice(self, payload: dict[str, Any]) -> ETimsConnectorResponse:
        return await self.submit_invoice(payload)

    async def cancel_invoice(
        self, provider_reference: str, reason: str
    ) -> ETimsConnectorResponse:
        return ETimsConnectorResponse(
            success=True,
            status="CANCELLED",
            provider_name=self.PROVIDER_NAME,
            environment=self.ENVIRONMENT,
            provider_reference=provider_reference,
            kra_response_code="00",
            kra_response_message=f"Cancelled (simulation): {reason}",
            raw_response={"simulationMode": True, "cancelled": True, "reason": reason},
        )

    async def get_submission_status(
        self, provider_reference: str
    ) -> ETimsConnectorResponse:
        return ETimsConnectorResponse(
            success=True,
            status="ACCEPTED",
            provider_name=self.PROVIDER_NAME,
            environment=self.ENVIRONMENT,
            provider_reference=provider_reference,
            kra_response_code="00",
            kra_response_message="Status OK (simulation)",
            raw_response={"simulationMode": True, "providerReference": provider_reference},
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": self.PROVIDER_NAME,
            "environment": self.ENVIRONMENT,
            "live": False,
        }


# ── HTTP connector skeleton ────────────────────────────────────────────────────

class HttpETIMSConnector:
    """
    HTTP connector skeleton for KRA OSCU/VSCU or certified middleware.

    Provider/KRA-spec dependent. The final endpoint, authentication scheme,
    and payload format MUST be confirmed before production use.
    Not production-ready — KRA sandbox validation still required.
    """

    def __init__(self, api_url: str, submit_path: str, settings: Any) -> None:
        self._api_url = api_url.rstrip("/")
        self._submit_path = submit_path
        self._settings = settings
        self._provider_name = "http"
        self._environment = getattr(settings, "ETIMS_ENV", "sandbox")

    async def submit_invoice(self, payload: dict[str, Any]) -> ETimsConnectorResponse:
        import httpx

        url = f"{self._api_url}{self._submit_path}"
        headers = {"Content-Type": "application/json"}
        # TODO: add provider-specific auth header once scheme is confirmed
        # (e.g., Bearer token, HMAC signature, mutual TLS — provider-dependent)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
            data = resp.json() if resp.content else {}
            if resp.is_success:
                return ETimsConnectorResponse(
                    success=True,
                    status="SUBMITTED",
                    provider_name=self._provider_name,
                    environment=self._environment,
                    provider_reference=data.get("submissionId") or data.get("referenceNo"),
                    control_unit_invoice_no=data.get("rcptNo") or data.get("controlUnitInvoiceNo"),
                    signed_invoice_hash=data.get("signedInvoiceHash"),
                    invoice_qr_data=data.get("qrCode"),
                    kra_response_code=str(data.get("resultCd", "00")),
                    kra_response_message=data.get("resultMsg", "Submitted"),
                    raw_response=data,
                )
            error_msg = data.get("resultMsg") or resp.text[:300]
            return ETimsConnectorResponse(
                success=False,
                status="FAILED",
                provider_name=self._provider_name,
                environment=self._environment,
                kra_response_code=str(data.get("resultCd", resp.status_code)),
                kra_response_message=error_msg,
                error_code=str(data.get("resultCd", resp.status_code)),
                error_message=error_msg,
                raw_response=data,
            )
        except Exception as exc:
            return ETimsConnectorResponse(
                success=False,
                status="ERROR",
                provider_name=self._provider_name,
                environment=self._environment,
                error_code="NETWORK_ERROR",
                error_message=f"Network error: {exc}",
            )

    # Legacy entry point
    async def submit_sales_invoice(self, payload: dict[str, Any]) -> ETimsConnectorResponse:
        return await self.submit_invoice(payload)

    async def cancel_invoice(
        self, provider_reference: str, reason: str
    ) -> ETimsConnectorResponse:
        # TODO: implement when provider cancel endpoint is confirmed
        raise NotImplementedError(
            "cancel_invoice not yet implemented for HttpETIMSConnector — "
            "provider cancel endpoint/spec not yet confirmed"
        )

    async def get_submission_status(
        self, provider_reference: str
    ) -> ETimsConnectorResponse:
        # TODO: implement when provider status polling endpoint is confirmed
        raise NotImplementedError(
            "get_submission_status not yet implemented for HttpETIMSConnector — "
            "provider status endpoint/spec not yet confirmed"
        )

    async def health_check(self) -> dict[str, Any]:
        # TODO: implement when provider health endpoint is confirmed
        return {
            "status": "unknown",
            "provider": self._provider_name,
            "environment": self._environment,
            "live": True,
            "note": "health_check not yet implemented — provider spec required",
        }


# ── Connector factory ──────────────────────────────────────────────────────────

def get_etims_connector(settings: Any) -> SimulationETIMSConnector | HttpETIMSConnector:
    """
    Return simulation or HTTP connector based on settings.
    Defaults to SimulationETIMSConnector (no network calls) unless
    ETIMS_CONFIGURED=True and ETIMS_PROVIDER=http are explicitly set.
    """
    if getattr(settings, "ETIMS_CONFIGURED", False) and \
            getattr(settings, "ETIMS_PROVIDER", "simulation") == "http":
        return HttpETIMSConnector(
            api_url=settings.ETIMS_API_URL,
            submit_path=settings.ETIMS_SALES_SUBMIT_PATH,
            settings=settings,
        )
    return SimulationETIMSConnector()
