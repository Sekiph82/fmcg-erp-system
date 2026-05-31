"""
KRA eTIMS connector-ready skeleton.

Architecture:
  ERP → build_etims_payload() → ETIMSConnector.submit_sales_invoice() → provider

The final connector provider (direct KRA OSCU/VSCU, certified middleware, or
third-party service) is NOT yet confirmed. Use ETIMS_PROVIDER=simulation until
KRA sandbox credentials and official API spec are validated.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

import httpx


@dataclass
class ETIMSResult:
    success: bool
    status: str                            # maps to ETimsStatus enum value
    control_unit_invoice_no: str | None = None
    signed_invoice_hash: str | None = None
    invoice_qr_data: str | None = None
    response_code: str | None = None
    response_message: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ETIMSConnector(Protocol):
    async def submit_sales_invoice(self, payload: dict[str, Any]) -> ETIMSResult: ...


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


class SimulationETIMSConnector:
    """Simulation connector — returns a fake accepted response, no network calls."""

    async def submit_sales_invoice(self, payload: dict[str, Any]) -> ETIMSResult:
        invoice_no = payload.get("invoiceNo", "UNKNOWN")
        invoice_date = payload.get("invoiceDate", str(datetime.now(timezone.utc).date()))
        total = payload.get("totalAmt", 0)

        invoice_hash = hashlib.sha256(
            f"{invoice_no}:{total}:{invoice_date}".encode()
        ).hexdigest()
        tims_serial = f"KRA-{invoice_no}-{invoice_date.replace('-', '')}"
        qr_data = (
            f"INV={invoice_no}|DATE={invoice_date}"
            f"|TOTAL={total}|HASH={invoice_hash[:16]}"
        )
        return ETIMSResult(
            success=True,
            status="ACCEPTED",
            control_unit_invoice_no=tims_serial,
            signed_invoice_hash=invoice_hash,
            invoice_qr_data=qr_data,
            response_code="00",
            response_message=(
                "Accepted (simulation mode — configure ETIMS_API_URL and "
                "ETIMS_PROVIDER=http for live integration)"
            ),
        )


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

    async def submit_sales_invoice(self, payload: dict[str, Any]) -> ETIMSResult:
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
                return ETIMSResult(
                    success=True,
                    status="SUBMITTED",
                    control_unit_invoice_no=data.get("rcptNo") or data.get("controlUnitInvoiceNo"),
                    signed_invoice_hash=data.get("signedInvoiceHash"),
                    invoice_qr_data=data.get("qrCode"),
                    response_code=str(data.get("resultCd", "00")),
                    response_message=data.get("resultMsg", "Submitted"),
                    raw_response=data,
                )
            error_msg = data.get("resultMsg") or resp.text[:300]
            return ETIMSResult(
                success=False,
                status="FAILED",
                response_code=str(data.get("resultCd", resp.status_code)),
                response_message=error_msg,
                raw_response=data,
            )
        except httpx.RequestError as exc:
            return ETIMSResult(
                success=False,
                status="FAILED",
                response_message=f"Network error: {exc}",
            )


def get_etims_connector(settings: Any) -> ETIMSConnector:
    """Return simulation or HTTP connector based on settings."""
    if settings.ETIMS_CONFIGURED and settings.ETIMS_PROVIDER == "http":
        return HttpETIMSConnector(
            api_url=settings.ETIMS_API_URL,
            submit_path=settings.ETIMS_SALES_SUBMIT_PATH,
            settings=settings,
        )
    return SimulationETIMSConnector()
