from __future__ import annotations

from app.core.integration_capabilities import (
    IntegrationCapability,
    IntegrationCapabilityStatus,
    can_execute_in_environment,
    get_integration_capability,
    iter_blocked_production_capabilities,
    list_integration_capabilities,
    production_block_reason,
)


def test_capability_registry_classifies_real_and_stub_providers():
    providers = {capability.provider: capability for capability in list_integration_capabilities()}

    assert providers["MPESA_DARAJA"].status == IntegrationCapabilityStatus.SANDBOX_READY
    assert providers["MPESA_DARAJA"].production_execution_allowed is True
    assert providers["IOT"].status == IntegrationCapabilityStatus.STUB_ONLY
    assert providers["EMAIL_SYNC"].status == IntegrationCapabilityStatus.SIMULATED_ONLY
    assert providers["GRAPHQL_API"].status == IntegrationCapabilityStatus.STUB_ONLY


def test_get_integration_capability_is_case_insensitive():
    capability = get_integration_capability("mpesa_daraja")

    assert capability is not None
    assert capability.provider == "MPESA_DARAJA"


def test_production_blocks_stub_and_simulated_capabilities():
    stub = IntegrationCapability(
        provider="TEST_STUB",
        label="Test Stub",
        status=IntegrationCapabilityStatus.STUB_ONLY,
    )
    simulated = IntegrationCapability(
        provider="TEST_SIM",
        label="Test Simulated",
        status=IntegrationCapabilityStatus.SIMULATED_ONLY,
        simulation_supported=True,
    )

    assert can_execute_in_environment(stub, environment="development") is True
    assert can_execute_in_environment(stub, environment="production") is False
    assert can_execute_in_environment(simulated, environment="production") is False


def test_live_ready_capability_requires_production_execution_flag_in_production():
    blocked_live = IntegrationCapability(
        provider="TEST_LIVE_BLOCKED",
        label="Blocked Live",
        status=IntegrationCapabilityStatus.LIVE_READY,
        production_execution_allowed=False,
    )
    allowed_live = IntegrationCapability(
        provider="TEST_LIVE_ALLOWED",
        label="Allowed Live",
        status=IntegrationCapabilityStatus.LIVE_READY,
        production_execution_allowed=True,
    )

    assert can_execute_in_environment(blocked_live, environment="production") is False
    assert can_execute_in_environment(allowed_live, environment="production") is True


def test_blocked_production_capability_report_includes_known_stub_providers():
    blocked = {capability.provider for capability in iter_blocked_production_capabilities()}

    assert "IOT" in blocked
    assert "CRM_SYNC" in blocked
    assert "GRAPHQL_API" in blocked


def test_production_block_reason_explains_stub_and_allowed_providers():
    stub = get_integration_capability("IOT")
    mpesa = get_integration_capability("MPESA_DARAJA")

    assert stub is not None
    assert production_block_reason(stub) == "Provider is stub-only and must not execute in production."
    assert mpesa is not None
    assert production_block_reason(mpesa) is None


def test_integration_capabilities_endpoint_is_registered():
    from app.api.v1.endpoints.integrations import router

    route = next(route for route in router.routes if route.path == "/capabilities")
    dependency = route.dependencies[0].dependency

    assert "GET" in route.methods
    assert dependency.__closure__ is not None
    assert dependency.__closure__[0].cell_contents == "integrations.view"
