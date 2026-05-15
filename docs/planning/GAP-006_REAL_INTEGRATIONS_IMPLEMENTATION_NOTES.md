# GAP-006 Real Integrations Implementation Notes

## Scope Completed

GAP-006 adds a source-owned integration capability registry so the ERP can distinguish real, sandbox, simulated, stub-only, and disabled integration surfaces.

This is intentionally not a new integration persistence model. The existing `IntegrationConfig`, `IntegrationLog`, M-Pesa transaction, connector marketplace, webhook, and provider-specific tables remain the persistence layer.

## Backend Capability Registry

Implemented in `backend/app/core/integration_capabilities.py`.

The registry classifies providers with:

- `LIVE_READY`
- `SANDBOX_READY`
- `SIMULATED_ONLY`
- `STUB_ONLY`
- `DISABLED`

Each capability records:

- provider key and display label
- live environment variable names without exposing values
- sandbox and simulation support
- whether production execution is allowed
- whether signature validation is required
- frontend route
- operational notes

Production execution is denied by default for stub-only and simulated-only providers. Live or sandbox providers must also explicitly set `production_execution_allowed=True`.

## API Endpoint

Added:

- `GET /api/v1/integrations/capabilities`

Permission:

- `integrations.view`

The endpoint returns capability metadata plus:

- `effective_status`
- `can_execute_in_development`
- `can_execute_in_production`
- `production_blocked_reason`

It does not expose secrets.

## Frontend

Updated the Integration Hub:

- `frontend/src/app/dashboard/integrations/page.tsx`

The page now shows a provider capability status section that separates runtime provider activity from production-readiness status. This prevents placeholder/simulated integrations from looking production-ready just because a route or UI exists.

Updated API client:

- `frontend/src/lib/integrations.ts`

## Permissions

No new permission was added.

The capability endpoint is a read-only governance surface and uses existing `integrations.view`. Existing `integrations.edit` remains reserved for configuration and mutation actions.

## Tests and Checks

Focused checks run:

```powershell
cd backend
.\venv\Scripts\python.exe -m py_compile app\core\integration_capabilities.py app\api\v1\endpoints\integrations.py tests\test_gap006_integration_capabilities.py
.\venv\Scripts\python.exe -m pytest tests\test_gap006_integration_capabilities.py -q

cd frontend
npm.cmd run type-check
```

Results:

- backend compile passed
- 7 focused backend tests passed
- frontend type-check passed

## Remaining Follow-Up

Later GAPs should harden individual providers:

- add real signature validation for inbound webhook/callback paths
- replace placeholder connector tests with provider-specific credential checks
- move simulated marketing, CRM, e-commerce, bank, IoT, and barcode-print flows toward real provider implementations
- add CI enforcement so `STUB_ONLY` and `SIMULATED_ONLY` providers cannot be enabled for production execution
