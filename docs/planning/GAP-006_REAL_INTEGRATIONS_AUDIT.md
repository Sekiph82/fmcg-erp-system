# GAP-006 Real Integrations Audit

## Scope

GAP-006 audits whether integrations are real production integrations or stubs/placeholders. This audit is documentation-only and does not change business logic.

Technical area: integrations, AI, IoT, webhooks, external syncs, payment gateways, messaging, developer portal, and connector/plugin infrastructure.

## What Exists

### Shared Integration Foundation

The repository has a real integration foundation:

- `IntegrationConfig` stores provider configuration, environment, status, webhook URL, and masked settings JSON.
- `IntegrationLog` provides unified integration audit logging with provider, type, endpoint, sanitized request/response payloads, status, retry count, duration, reference, and idempotency key.
- `ConnectorRegistry`, `PluginInstallation`, and lifecycle event models exist for marketplace/plugin style integrations.
- `integration_service.log_call()` masks sensitive keys before persisting request payloads.
- Integration permissions exist around `integrations.view` and `integrations.edit`.

This is a good enterprise-grade base.

### M-Pesa / Daraja

M-Pesa has the strongest real-provider implementation:

- `mpesa_daraja_service.py` supports Daraja OAuth token retrieval.
- STK Push payload construction is implemented.
- Callback handling and status query helpers exist.
- Transactions are persisted in `IntegrationMpesaTransaction`.
- The service falls back to sandbox simulation when credentials are not configured.

Current status: Partial but close to real. Live behavior depends on valid Daraja credentials and public callback URL configuration.

### Webhooks / Event Engine

The webhook/event engine is a meaningful internal integration foundation:

- event definitions
- event logs
- subscriptions
- delivery attempts
- replay/retry operations
- inbound endpoints
- dashboard/report schemas

Current status: Partial. The event model is real, but external delivery hardening, auth/signature rules, retry policy details, and tenant isolation need review before production use.

### AI Provider Layer

AI has real architecture:

- provider detection
- mock mode
- status endpoint
- live provider hooks
- mock-mode safety labels and disabled high-risk behavior from earlier hardening

Current status: Partial. Live LLM use depends on configured provider keys. Mock mode is intentionally supported and must remain visibly labeled.

### Frontend Integration Surfaces

Integration-related dashboard areas exist:

- integrations
- webhooks
- iot
- bank-api
- bank-reconciliation
- mobile
- portal
- supplier-portal
- whatsapp
- developer
- ai

Current status: Mixed. Several pages are operational admin surfaces, while others expose simulation/demo behavior or future hooks.

## Stub / Placeholder / Demo Areas Found

The audit found explicit stub or simulation signals:

- `backend/app/api/v1/endpoints/api_portal.py`: GraphQL endpoint information is explicitly marked as a stub.
- `backend/app/api/v1/endpoints/integrations.py`: print job queuing is a placeholder until connected to a printer SDK.
- `backend/app/api/v1/endpoints/integrations.py`: machine token handling is described as a placeholder.
- `backend/app/api/v1/endpoints/integrations.py`: marketing sync hooks are placeholders.
- `backend/app/api/v1/endpoints/integrations.py`: connector test endpoint is marked as a stub.
- `backend/app/api/v1/endpoints/email_integration.py`: inbox sync is simulated and creates demo email threads.
- `backend/app/services/crm_service.py`: CRM integration service is explicitly described as a scalable placeholder.
- `backend/app/services/ecommerce_service.py`: e-commerce import and inventory push are placeholder/simulated.
- `backend/app/services/iot_service.py`: IoT/machine integration service is explicitly described as placeholder/future bridge.
- `backend/app/services/mpesa_service.py`: older M-Pesa service is placeholder/simulated, while `mpesa_daraja_service.py` is the more production-oriented implementation.
- `backend/app/services/bank_api_service.py`: open banking service currently says mock Kenyan bank sync.
- `backend/app/services/barcode_service.py`: printer integration is a placeholder for label printer SDK.
- `backend/app/services/forecast_service.py`: Prophet-style AI forecasting is stubbed/fallback.
- `frontend/src/app/dashboard/integrations/marketing-sync/page.tsx`: syncs are queued as placeholders until credentials are configured.
- `frontend/src/app/dashboard/ai/nl-command/page.tsx`: execution KPI still references a stub execution log.
- WhatsApp includes demo-mode delivery and demo inbound/template endpoints.

## Production Risks

1. Some integration endpoints simulate success, which can be mistaken for live connectivity.
2. Multiple integration surfaces mix real foundations with placeholders in the same module.
3. Some webhook/event endpoints have weaker auth posture than core ERP modules and need production review.
4. External callbacks need signature validation, replay protection, and idempotency rules per provider.
5. Credential/config health should be visible without exposing secrets.
6. Demo/simulation actions need explicit development-only guards or clear UI labels.
7. There are two M-Pesa service paths: one production-oriented Daraja service and one older placeholder service. This should be consolidated or clearly separated.

## Recommended GAP-006 Direction

Start with a provider capability matrix rather than implementing every integration at once.

For each provider, classify:

- `LIVE_READY`
- `SANDBOX_READY`
- `SIMULATED_ONLY`
- `STUB_ONLY`
- `DISABLED`

Suggested first hardening slice:

1. Add an integration capability/status registry.
2. Expose capability status through existing integration provider summary without secrets.
3. Add explicit simulator/demo labels in frontend integration pages.
4. Disable or guard production execution of `STUB_ONLY` and `SIMULATED_ONLY` operations.
5. Prioritize M-Pesa Daraja, webhooks, and notification/email/WhatsApp as first real-provider hardening targets.

## Suggested Acceptance for Later GAP-006 Tasks

- Every integration provider has an explicit capability status.
- Demo/simulated actions are labeled and blocked in production unless explicitly allowed.
- External callbacks validate provider signatures or secrets where provider supports it.
- Integration calls use `IntegrationLog` consistently.
- Credentials are masked in every response and log.
- Frontend distinguishes live, sandbox, simulated, and stub providers.
- Tests cover live-disabled, sandbox/simulated, and production-guard behavior.

## Audit Commands Used

```powershell
rg -n "stub|placeholder|mock|TODO|not implemented|coming soon|future|simulate|demo" backend\app\api\v1\endpoints backend\app\services frontend\src\app\dashboard\integrations frontend\src\app\dashboard\iot frontend\src\app\dashboard\ai frontend\src\app\dashboard\webhooks -g "*.py" -g "*.tsx"
Get-ChildItem -Path backend\app\api\v1\endpoints -File | Where-Object { $_.Name -match 'integr|webhook|iot|bank|mpesa|email|whatsapp|mobile|receipt|ai|portal' }
Get-ChildItem -Path frontend\src\app\dashboard -Directory | Where-Object { $_.Name -match 'integr|webhook|iot|bank|mpesa|email|whatsapp|mobile|ai|portal|developer' }
rg -n "class IntegrationProvider|class IntegrationConfig|class ConnectorRegistry|class IntegrationLog" backend\app\models\integrations.py backend\app\models\webhook.py
```

