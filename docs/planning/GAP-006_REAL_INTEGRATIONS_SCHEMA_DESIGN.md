# GAP-006 Real Integrations Schema Design

## Decision

No database schema or Alembic migration is required for the first GAP-006 hardening slice.

The repository already has durable integration tables:

- `integration_configs`
- `integration_logs`
- `integration_mpesa_transactions`
- connector registry / plugin installation tables
- webhook/event engine tables

The missing piece is not another table. The missing piece is an explicit source-owned capability registry that classifies whether each provider is live-ready, sandbox-ready, simulated-only, stub-only, or disabled.

## Proposed Capability Status Model

Add a code-level registry in a later implementation task, likely:

```text
backend/app/core/integration_capabilities.py
```

Suggested enum values:

```py
class IntegrationCapabilityStatus(str, Enum):
    LIVE_READY = "LIVE_READY"
    SANDBOX_READY = "SANDBOX_READY"
    SIMULATED_ONLY = "SIMULATED_ONLY"
    STUB_ONLY = "STUB_ONLY"
    DISABLED = "DISABLED"
```

Suggested definition shape:

```py
@dataclass(frozen=True)
class IntegrationCapability:
    provider: str
    label: str
    status: IntegrationCapabilityStatus
    live_env_vars: tuple[str, ...]
    sandbox_supported: bool
    simulation_supported: bool
    production_execution_allowed: bool
    requires_signature_validation: bool
    frontend_route: str | None = None
    notes: str = ""
```

## Initial Provider Classifications

Suggested first-pass classifications:

| Provider | Status | Notes |
|---|---|---|
| M-Pesa Daraja | `SANDBOX_READY` / `LIVE_READY` when env configured | Real Daraja STK flow exists, simulation fallback exists. |
| Webhooks/Event Engine | `SANDBOX_READY` | Internal event/subscription model exists; external signature/delivery hardening remains. |
| AI Providers | `SANDBOX_READY` or `SIMULATED_ONLY` depending config | Live provider hooks exist; mock mode is explicit. |
| Email Sync | `SIMULATED_ONLY` | Current sync creates demo threads. |
| WhatsApp | `SIMULATED_ONLY` until live provider config | Demo-mode send/inbound/template flows exist. |
| IoT | `STUB_ONLY` / `SIMULATED_ONLY` | Service describes future MQTT bridge. |
| CRM Sync | `STUB_ONLY` | Service describes scalable placeholder. |
| E-commerce Sync | `STUB_ONLY` | Import/push paths are simulated placeholders. |
| Barcode Printing | `STUB_ONLY` | Label generation exists; printer SDK integration is placeholder. |
| Bank API/Open Banking | `SIMULATED_ONLY` | Service describes mock bank sync. |
| GraphQL Developer API | `STUB_ONLY` | API portal explicitly marks GraphQL as stub. |
| Marketing Sync | `STUB_ONLY` | UI and backend comments mark hooks/placeholders. |

## Runtime Rules

The capability registry should be used by endpoints/services to enforce:

- Production must not execute `STUB_ONLY` operations.
- Production must not execute `SIMULATED_ONLY` operations unless a dedicated development flag is enabled and environment is not production.
- UI status should distinguish live, sandbox, simulated, stub, and disabled.
- Provider status responses must not expose secrets.
- Callback endpoints must record whether signature validation is implemented.

## Existing Schema Reuse

Use existing tables for persistent state:

- `IntegrationConfig.status` for configured provider health.
- `IntegrationConfig.environment` for sandbox/production.
- `IntegrationLog` for calls, callbacks, failures, idempotency keys, and sanitized payloads.
- Provider-specific tables such as `IntegrationMpesaTransaction` for transaction state.
- Webhook tables for event definitions, event logs, subscriptions, deliveries, and inbound endpoints.

## Why Not Persist Capability Definitions

Provider capability definitions are product/source metadata, not tenant data. Keeping them in code:

- makes CI/static tests possible
- avoids migration churn for simple status corrections
- keeps production guards close to implementation
- prevents admins from accidentally marking stub providers live-ready

Tenant-specific configuration remains in `IntegrationConfig`.

## Dependencies

- GAP-006A audit
- existing integration models and services
- existing integration provider summary endpoint
- existing frontend integration surfaces

## Acceptance Criteria for Later Implementation

- Capability registry exists in backend code.
- Provider summary includes capability status and safe labels.
- Production guards block `STUB_ONLY` and unsafe `SIMULATED_ONLY` operations.
- Frontend integration pages show live/sandbox/simulated/stub status clearly.
- Focused tests cover classification, production guard behavior, and no-secret status output.

