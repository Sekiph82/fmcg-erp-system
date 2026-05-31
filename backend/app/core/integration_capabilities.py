from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable

from app.core.config import settings


class IntegrationCapabilityStatus(str, Enum):
    LIVE_READY = "LIVE_READY"
    SANDBOX_READY = "SANDBOX_READY"
    SIMULATED_ONLY = "SIMULATED_ONLY"
    STUB_ONLY = "STUB_ONLY"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class IntegrationCapability:
    provider: str
    label: str
    status: IntegrationCapabilityStatus
    live_env_vars: tuple[str, ...] = ()
    sandbox_supported: bool = False
    simulation_supported: bool = False
    production_execution_allowed: bool = False
    requires_signature_validation: bool = False
    frontend_route: str | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["live_env_vars"] = list(self.live_env_vars)
        return data


CAPABILITIES: tuple[IntegrationCapability, ...] = (
    IntegrationCapability(
        provider="MPESA_DARAJA",
        label="M-Pesa Daraja",
        status=IntegrationCapabilityStatus.SANDBOX_READY,
        live_env_vars=(
            "MPESA_CONSUMER_KEY",
            "MPESA_CONSUMER_SECRET",
            "MPESA_SHORTCODE",
            "MPESA_PASSKEY",
            "MPESA_CALLBACK_URL",
        ),
        sandbox_supported=True,
        simulation_supported=True,
        production_execution_allowed=True,
        requires_signature_validation=True,
        frontend_route="/dashboard/integrations/mpesa",
        notes="Daraja STK push is implemented and falls back to sandbox simulation when credentials are missing.",
    ),
    IntegrationCapability(
        provider="WEBHOOKS",
        label="Webhook / Event Engine",
        status=IntegrationCapabilityStatus.SANDBOX_READY,
        sandbox_supported=True,
        production_execution_allowed=False,
        requires_signature_validation=True,
        frontend_route="/dashboard/webhooks",
        notes="Internal event/subscription model exists; production delivery and inbound signature hardening still need review.",
    ),
    IntegrationCapability(
        provider="AI_PROVIDERS",
        label="AI Providers",
        status=IntegrationCapabilityStatus.SIMULATED_ONLY,
        live_env_vars=("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"),
        sandbox_supported=True,
        simulation_supported=True,
        production_execution_allowed=True,
        frontend_route="/dashboard/ai",
        notes="Live providers are available when configured; mock mode must remain visibly labeled.",
    ),
    IntegrationCapability(
        provider="EMAIL_SYNC",
        label="Email Sync",
        status=IntegrationCapabilityStatus.SIMULATED_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/email",
        notes="Current sync creates demo email threads.",
    ),
    IntegrationCapability(
        provider="WHATSAPP",
        label="WhatsApp",
        status=IntegrationCapabilityStatus.SANDBOX_READY,
        live_env_vars=(),  # credentials stored in DB per WhatsAppConfig row, not env vars
        sandbox_supported=True,
        simulation_supported=True,
        production_execution_allowed=True,
        requires_signature_validation=True,
        frontend_route="/dashboard/whatsapp",
        notes=(
            "Live Meta Cloud API send implemented. "
            "Credentials (api_token, business_phone_id, webhook_verify_token) stored in whatsapp_configs table. "
            "Set is_demo_mode=False via Config tab PATCH to enable live sends. "
            "Requires Meta Business Manager account, approved phone number, and system user access token."
        ),
    ),
    IntegrationCapability(
        provider="ETIMS",
        label="KRA eTIMS (Kenya e-Invoice)",
        status=IntegrationCapabilityStatus.SANDBOX_READY,
        live_env_vars=(
            "ETIMS_API_URL",
            "ETIMS_PIN",
            "ETIMS_BRANCH_ID",
            "ETIMS_DEVICE_SERIAL_NO",
        ),
        sandbox_supported=True,
        simulation_supported=True,
        production_execution_allowed=False,
        requires_signature_validation=True,
        frontend_route="/dashboard/finance/etims",
        notes=(
            "Connector-ready skeleton implemented. "
            "SimulationETIMSConnector active when ETIMS_PROVIDER=simulation (default). "
            "HttpETIMSConnector skeleton prepared for KRA OSCU/VSCU or certified middleware. "
            "Final provider/middleware decision still pending. "
            "KRA sandbox credentials, official API spec, and device registration required before live use. "
            "Set ETIMS_PROVIDER=http and all ETIMS_* vars to enable HTTP connector. "
            "Not production-ready — production_execution_allowed=False until KRA validation is complete."
        ),
    ),
    IntegrationCapability(
        provider="IOT",
        label="IoT / Machine Streaming",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        simulation_supported=True,
        requires_signature_validation=True,
        frontend_route="/dashboard/iot",
        notes="Current service is a placeholder for a future MQTT/streaming bridge.",
    ),
    IntegrationCapability(
        provider="CRM_SYNC",
        label="CRM Sync",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/crm",
        notes="CRM integration service is explicitly a scalable placeholder.",
    ),
    IntegrationCapability(
        provider="ECOMMERCE_SYNC",
        label="E-commerce Sync",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/portal",
        notes="Order import and inventory push are simulated placeholders.",
    ),
    IntegrationCapability(
        provider="BARCODE_PRINTING",
        label="Barcode / Label Printing",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/integrations/barcode",
        notes="Label generation exists; physical printer SDK integration is still a placeholder.",
    ),
    IntegrationCapability(
        provider="BANK_API",
        label="Bank API / Open Banking",
        status=IntegrationCapabilityStatus.SIMULATED_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/bank-api",
        notes="Current service describes mock Kenyan bank sync.",
    ),
    IntegrationCapability(
        provider="GRAPHQL_API",
        label="GraphQL Developer API",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        frontend_route="/dashboard/developer/graphql",
        notes="API portal explicitly marks GraphQL as a stub.",
    ),
    IntegrationCapability(
        provider="MARKETING_SYNC",
        label="Marketing Sync",
        status=IntegrationCapabilityStatus.STUB_ONLY,
        simulation_supported=True,
        frontend_route="/dashboard/integrations/marketing-sync",
        notes="Frontend and backend mark marketing sync hooks as placeholders.",
    ),
)

_CAPABILITY_BY_PROVIDER = {capability.provider: capability for capability in CAPABILITIES}


def list_integration_capabilities() -> tuple[IntegrationCapability, ...]:
    return CAPABILITIES


def get_integration_capability(provider: str) -> IntegrationCapability | None:
    return _CAPABILITY_BY_PROVIDER.get(provider.upper())


def effective_capability_status(capability: IntegrationCapability) -> IntegrationCapabilityStatus:
    if capability.provider == "MPESA_DARAJA" and settings.MPESA_CONFIGURED:
        return (
            IntegrationCapabilityStatus.LIVE_READY
            if settings.MPESA_ENV == "production"
            else IntegrationCapabilityStatus.SANDBOX_READY
        )
    if capability.provider == "AI_PROVIDERS" and settings.AI_CONFIGURED:
        return IntegrationCapabilityStatus.LIVE_READY
    return capability.status


def can_execute_in_environment(
    capability: IntegrationCapability,
    *,
    environment: str | None = None,
) -> bool:
    env = (environment or settings.ENVIRONMENT).lower()
    status = effective_capability_status(capability)
    if status == IntegrationCapabilityStatus.DISABLED:
        return False
    if env == "production" and status in {
        IntegrationCapabilityStatus.SIMULATED_ONLY,
        IntegrationCapabilityStatus.STUB_ONLY,
    }:
        return False
    if env == "production" and not capability.production_execution_allowed:
        return False
    return True


def production_block_reason(capability: IntegrationCapability) -> str | None:
    status = effective_capability_status(capability)
    if can_execute_in_environment(capability, environment="production"):
        return None
    if status == IntegrationCapabilityStatus.DISABLED:
        return "Provider is disabled."
    if status == IntegrationCapabilityStatus.STUB_ONLY:
        return "Provider is stub-only and must not execute in production."
    if status == IntegrationCapabilityStatus.SIMULATED_ONLY:
        return "Provider only returns simulated/demo results and must not execute in production."
    if not capability.production_execution_allowed:
        return "Provider needs production execution hardening before live use."
    return "Provider is not approved for production execution."


def iter_blocked_production_capabilities(
    capabilities: Iterable[IntegrationCapability] = CAPABILITIES,
) -> tuple[IntegrationCapability, ...]:
    return tuple(
        capability
        for capability in capabilities
        if not can_execute_in_environment(capability, environment="production")
    )
