"""
Tests for eTIMS connector-ready skeleton.

Verifies:
- build_etims_payload includes invoice header and line items
- SimulationETIMSConnector returns normalized ACCEPTED response
- HttpETIMSConnector uses mocked httpx and does not call the internet
- get_etims_connector returns simulation when provider not configured
- get_etims_connector returns HTTP connector when ETIMS_CONFIGURED and provider=http
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.etims_connector import (
    SimulationETIMSConnector,
    HttpETIMSConnector,
    build_etims_payload,
    get_etims_connector,
)


def _make_invoice(lines=None):
    product = SimpleNamespace(name="Maize Flour 2kg", etims_item_code=None, tax_type_code=None)
    line = SimpleNamespace(
        product=product,
        description="Maize Flour 2kg",
        quantity=10,
        unit_price=150.0,
        discount_pct=0.0,
        tax_rate=0.16,
        line_total=1500.0,
    )
    customer = SimpleNamespace(name="Nairobi Traders Ltd", tax_id="A123456789B")
    return SimpleNamespace(
        invoice_no="INV-2025-001",
        invoice_date="2025-06-01",
        subtotal=1500.0,
        tax_amount=240.0,
        total_amount=1740.0,
        currency="KES",
        customer=customer,
        lines=lines if lines is not None else [line],
    )


def _make_settings(configured=False, provider="simulation"):
    return SimpleNamespace(
        ETIMS_PIN="A123456789B" if configured else "",
        ETIMS_BRANCH_ID="00" if configured else "",
        ETIMS_DEVICE_SERIAL_NO="VSCU001" if configured else "",
        ETIMS_API_URL="http://etims-sandbox.example.com" if configured else "",
        ETIMS_SALES_SUBMIT_PATH="/api/method/saveSales",
        ETIMS_PROVIDER=provider,
        ETIMS_CONFIGURED=configured,
    )


def test_build_etims_payload_includes_header():
    invoice = _make_invoice()
    settings = _make_settings(configured=True)
    payload = build_etims_payload(invoice, settings)
    assert payload["invoiceNo"] == "INV-2025-001"
    assert payload["tin"] == "A123456789B"
    assert payload["bhfId"] == "00"
    assert payload["totalAmt"] == 1740.0
    assert payload["custNm"] == "Nairobi Traders Ltd"


def test_build_etims_payload_includes_lines():
    invoice = _make_invoice()
    settings = _make_settings(configured=True)
    payload = build_etims_payload(invoice, settings)
    assert len(payload["itemList"]) == 1
    item = payload["itemList"][0]
    assert item["itemSeq"] == 1
    assert item["itemNm"] == "Maize Flour 2kg"
    assert item["qty"] == 10.0
    assert item["unitPrice"] == 150.0


@pytest.mark.asyncio
async def test_simulation_connector_returns_accepted():
    connector = SimulationETIMSConnector()
    payload = {"invoiceNo": "INV-001", "invoiceDate": "2025-06-01", "totalAmt": 1740.0}
    result = await connector.submit_sales_invoice(payload)
    assert result.success is True
    assert result.status == "ACCEPTED"
    assert result.control_unit_invoice_no is not None
    assert "KRA-INV-001" in result.control_unit_invoice_no
    assert result.signed_invoice_hash is not None
    assert result.invoice_qr_data is not None
    assert result.response_code == "00"


@pytest.mark.asyncio
async def test_http_connector_uses_mock_no_real_network():
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.content = b'{"rcptNo":"KRA-001","resultCd":"00","resultMsg":"Success"}'
    mock_resp.json.return_value = {"rcptNo": "KRA-001", "resultCd": "00", "resultMsg": "Success"}

    with patch(
        "app.services.etims_connector.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp))),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        settings = _make_settings(configured=True, provider="http")
        connector = HttpETIMSConnector(
            api_url=settings.ETIMS_API_URL,
            submit_path=settings.ETIMS_SALES_SUBMIT_PATH,
            settings=settings,
        )
        result = await connector.submit_sales_invoice({"invoiceNo": "INV-002"})

    assert result.success is True
    assert result.status == "SUBMITTED"
    assert result.control_unit_invoice_no == "KRA-001"


def test_get_etims_connector_returns_simulation_when_not_configured():
    settings = _make_settings(configured=False)
    connector = get_etims_connector(settings)
    assert isinstance(connector, SimulationETIMSConnector)


def test_get_etims_connector_returns_http_when_configured():
    settings = _make_settings(configured=True, provider="http")
    connector = get_etims_connector(settings)
    assert isinstance(connector, HttpETIMSConnector)
