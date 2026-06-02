"""
TASK-005.1B: Provider-neutral eTIMS adapter interface + enhanced simulation connector.

Tests:
1. ETimsConnectorResponse has all required fields.
2. ETIMSResult backward-compat alias works.
3. SimulationETIMSConnector returns provider-neutral response with all fields.
4. Simulation ACCEPTED path — correct fields populated.
5. Simulation REJECTED path via _simulate_reject flag.
6. Simulation ERROR path via _simulate_error flag.
7. Simulation cancel_invoice returns CANCELLED.
8. Simulation get_submission_status returns ACCEPTED.
9. Simulation health_check returns ok.
10. Factory returns SimulationETIMSConnector by default.
11. Factory returns HttpETIMSConnector only when ETIMS_CONFIGURED=True + PROVIDER=http.
12. HttpETIMSConnector does NOT run by default.
13. Schema includes new 005.1A fields.
"""
import asyncio
from dataclasses import fields as dc_fields
from unittest.mock import MagicMock

import pytest

from app.services.etims_connector import (
    ETimsConnectorResponse,
    ETIMSResult,
    SimulationETIMSConnector,
    HttpETIMSConnector,
    get_etims_connector,
)


# ── 1. Response contract ───────────────────────────────────────────────────────

def test_response_has_all_required_fields():
    field_names = {f.name for f in dc_fields(ETimsConnectorResponse)}
    required = {
        "success", "status", "provider_name", "environment",
        "provider_reference", "control_unit_invoice_no",
        "signed_invoice_hash", "invoice_qr_data",
        "kra_response_code", "kra_response_message",
        "error_code", "error_message", "accepted_at", "raw_response",
    }
    assert required <= field_names, f"Missing fields: {required - field_names}"


def test_etims_result_backward_compat():
    assert ETIMSResult is ETimsConnectorResponse


# ── 2–4. Simulation ACCEPTED path ─────────────────────────────────────────────

_PAYLOAD = {
    "invoiceNo": "INV-TEST-001",
    "invoiceDate": "2026-06-02",
    "totalAmt": 1000.0,
    "itemList": [],
}


async def test_simulation_accepted_response():
    connector = SimulationETIMSConnector()
    result = await connector.submit_invoice(_PAYLOAD)

    assert result.success is True
    assert result.status == "ACCEPTED"
    assert result.provider_name == "simulation"
    assert result.environment == "simulation"
    assert result.provider_reference is not None
    assert result.provider_reference.startswith("SIM-ETIMS-INV-TEST-001-")
    assert result.control_unit_invoice_no is not None
    assert result.signed_invoice_hash is not None
    assert result.invoice_qr_data is not None
    assert result.kra_response_code == "00"
    assert result.accepted_at is not None
    assert isinstance(result.raw_response, dict)
    assert result.raw_response.get("simulationMode") is True
    assert result.error_code is None


async def test_simulation_submit_sales_invoice_legacy():
    """Legacy entry point still works."""
    connector = SimulationETIMSConnector()
    result = await connector.submit_sales_invoice(_PAYLOAD)
    assert result.status == "ACCEPTED"
    assert result.provider_name == "simulation"


# ── 5. Simulation REJECTED path ───────────────────────────────────────────────

async def test_simulation_reject_flag():
    connector = SimulationETIMSConnector()
    payload = {**_PAYLOAD, "_simulate_reject": True}
    result = await connector.submit_invoice(payload)

    assert result.success is False
    assert result.status == "REJECTED"
    assert result.provider_name == "simulation"
    assert result.error_code is not None
    assert result.accepted_at is None


# ── 6. Simulation ERROR path ──────────────────────────────────────────────────

async def test_simulation_error_flag():
    connector = SimulationETIMSConnector()
    payload = {**_PAYLOAD, "_simulate_error": True}
    result = await connector.submit_invoice(payload)

    assert result.success is False
    assert result.status == "ERROR"
    assert result.provider_name == "simulation"
    assert result.error_code is not None
    assert result.accepted_at is None


# ── 7–9. cancel / status / health ─────────────────────────────────────────────

async def test_simulation_cancel():
    connector = SimulationETIMSConnector()
    result = await connector.cancel_invoice("SIM-REF-001", "test cancellation")

    assert result.success is True
    assert result.status == "CANCELLED"
    assert result.provider_reference == "SIM-REF-001"
    assert result.provider_name == "simulation"


async def test_simulation_get_status():
    connector = SimulationETIMSConnector()
    result = await connector.get_submission_status("SIM-REF-001")

    assert result.success is True
    assert result.provider_reference == "SIM-REF-001"
    assert result.provider_name == "simulation"


async def test_simulation_health_check():
    connector = SimulationETIMSConnector()
    health = await connector.health_check()

    assert health["status"] == "ok"
    assert health["provider"] == "simulation"
    assert health["live"] is False


# ── 10–12. Factory behavior ────────────────────────────────────────────────────

def _make_settings(configured=False, provider="simulation"):
    s = MagicMock()
    s.ETIMS_CONFIGURED = configured
    s.ETIMS_PROVIDER = provider
    s.ETIMS_API_URL = "http://localhost:9000"
    s.ETIMS_SALES_SUBMIT_PATH = "/api/submit"
    s.ETIMS_ENV = "sandbox"
    return s


def test_factory_returns_simulation_by_default():
    settings = _make_settings(configured=False, provider="simulation")
    connector = get_etims_connector(settings)
    assert isinstance(connector, SimulationETIMSConnector)


def test_factory_returns_simulation_when_not_configured():
    settings = _make_settings(configured=False, provider="http")
    connector = get_etims_connector(settings)
    assert isinstance(connector, SimulationETIMSConnector), \
        "Must return simulation when ETIMS_CONFIGURED=False even if PROVIDER=http"


def test_factory_returns_http_only_when_explicitly_configured():
    settings = _make_settings(configured=True, provider="http")
    connector = get_etims_connector(settings)
    assert isinstance(connector, HttpETIMSConnector)


# ── 13. Schema includes new fields ────────────────────────────────────────────

def test_schema_includes_provider_fields():
    from app.schemas.tax_regulatory import ETimsSubmissionRead
    field_names = set(ETimsSubmissionRead.model_fields.keys())
    new_fields = {
        "provider_name", "provider_reference", "environment",
        "request_payload", "response_payload",
        "accepted_at", "last_attempt_at", "attempt_count", "error_code",
    }
    missing = new_fields - field_names
    assert not missing, f"Schema missing fields: {missing}"
