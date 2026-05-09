# TASKS2.md

## Current Phase

Tier 5 - Advanced / Future Roadmap Complete - QA / Hardening

## Current Gap

All 70 gap items implemented - auth startup/login hardening completed

## In Progress

No gap implementation in progress. Next work should continue validation, migration graph review, backend tests, and production hardening.

## Completed in Last Run

QA / hardening hotfix:
- Diagnosed `POST /api/v1/auth/login net::ERR_EMPTY_RESPONSE` as a backend startup failure, not a React login payload issue.
- Fixed `backend/app/api/v1/endpoints/traceability.py` by importing the existing `get_current_user` dependency used by blockchain anchor endpoints.
- Verified the Docker backend reloader recovered and `/health` returns `{"status":"ok","database":"connected"}`.
- Diagnosed a follow-on login 500 as running database schema drift in `audit_logs`.
- Repaired the local Docker Postgres `audit_logs` table with the nullable columns expected by the current `AuditLog` model: `actor_name`, `session_id`, `user_agent`, `module`, `before_value`, `after_value`, and `row_hash`, plus indexes for `session_id` and `module`.
- Verified bad credentials now return 401 instead of 500.
- Verified seeded admin login succeeds with username `admin` and password `admin123`.

Gap 66 frontend completion:
- Built `/dashboard/ai/nl-command` as a usable natural-language ERP command console.
- Added shared `aiApi` client methods and types for command parsing, execution, rejection, and history.
- The page shows parsed intent, action plan, target endpoint, risk level, confirmation status, KPI summary, and command history.

Gap 67 completion:
- Confirmed existing backend model/API work for `AIAgentPolicy` and `AIAgentRun`.
- Fixed backend model import for `datetime.utcnow`.
- Tightened Gap 66 and Gap 67 AI endpoints to existing `require_permission("ai", ...)` patterns.
- Added `/dashboard/ai/governance` console for policy creation, policy activation/deactivation, governance KPIs, status mix, agent run logging, filtering, and run audit review.
- Added shared `aiApi` client methods and TypeScript types for AI governance.

Gap 68 completion:
- Added predictive maintenance data model in the existing maintenance module.
- Added rule-based prediction generation from IoT sensor trends, machine DOWN/FAULT states, critical IoT alerts, and recent breakdown history.
- Added persisted prediction records with risk, confidence, predicted failure date, failure mode, recommended action, evidence, source metrics, review status, and reviewer audit fields.
- Added backend endpoints to generate, list, and review maintenance predictions.
- Added frontend API types/methods for predictive maintenance.
- Added `/dashboard/maintenance/predictive` page with generation controls, KPI cards, status/risk filters, prediction evidence, confidence display, and review actions.
- Added Predictive Maintenance navigation under the existing Maintenance cluster and quick link from the Maintenance dashboard.

Gap 69 completion:
- Inspected existing ESG models/routes/services/pages, supplier/product masters, utility cost allocations, machine utility records, wastewater records, and ESG navigation before coding.
- Added `SupplierSustainabilityScore` model with scored ESG dimensions, supplier linkage, assessment period, risk/status, certification/disclosure flags, review timestamp, and assessor audit linkage.
- Added Alembic migration for the supplier sustainability score table and enum types.
- Added ESG intelligence schemas for supplier scorecards, energy intensity rows, wastewater compliance snapshots, and the combined dashboard response.
- Added ESG service logic for supplier score creation/list/update with validation, energy intensity per SKU from product-linked utility allocations, and wastewater compliance snapshots from existing wastewater operational records.
- Added ESG API endpoints for `/intelligence/dashboard`, `/intelligence/energy-intensity`, `/intelligence/wastewater-compliance`, and supplier scorecard CRUD-lite.
- Added frontend ESG API types/methods for ESG intelligence and supplier scorecards.
- Added `/dashboard/esg/intelligence` page with date filters, KPI cards, supplier scorecard entry/list, energy intensity per SKU table, and wastewater compliance/deviation review.
- Added ESG Intelligence entry to the ESG & Sustainability navigation and linked it from the ESG dashboard.

Gap 70 completion:
- Inspected existing Integrations marketplace, connector registry, integration services/routes/schemas, developer portal, webhooks, frontend integrations pages, and navigation before coding.
- Extended the existing `integration_connector_registry` model instead of creating a duplicate plugin system.
- Added governed plugin/app install state with tenant key, installed version, lifecycle status, environment, config metadata, installer, timestamps, and notes.
- Added plugin lifecycle audit events for install, enable, disable, uninstall, update, configure, and test actions.
- Added marketplace metadata for current version, module key, dependency connector codes, required permissions, tenant config support, and core-module flag.
- Added service logic for install/update/enable/disable/uninstall with dependency validation and audit event recording.
- Added marketplace API endpoints for connector catalog with installation state, installations list, lifecycle events, install, config update, lifecycle transitions, and tenant-aware tests.
- Upgraded `/dashboard/integrations/marketplace` into a governed marketplace console with tenant filtering, install/enable/disable/uninstall/test actions, dependency and permission display, and lifecycle audit panel.

## Implemented Gap Items

1-70 implemented.

## Remaining Gap Items

None.

## Next Immediate Task

All planned gap implementations are complete. Next immediate task:
1. Review and repair the Alembic graph because the repository has historical duplicate/branching revisions and the live Docker database is stamped at `e7f8a9b0c1d2`.
2. Convert the local `audit_logs` schema repair into a proper migration once the Alembic graph is safe to extend.
3. Run backend tests inside Docker if available.
4. Perform end-to-end UI/API smoke tests for `/dashboard/esg/intelligence` and `/dashboard/integrations/marketplace` against the running backend.
5. Decide whether to configure ESLint non-interactively or keep lint blocked.

## Blockers

Local backend Python remains blocked: `python`, `python3`, and `py` are not available on PATH, and `backend/venv/Scripts/python.exe` points to a missing local Python install. Backend compile is available and passing through Docker with `docker compose exec -T backend python -m compileall app`.

Alembic graph remains a blocker for migration discipline: the repository has duplicate revision IDs and the current Docker database is stamped at `e7f8a9b0c1d2`. The running dev DB was repaired directly for `audit_logs` so login works; convert this to a normal migration after graph cleanup.

`npm run lint` is blocked by interactive Next.js ESLint setup prompt because the project does not have a completed ESLint config. Do not accept or generate config automatically unless explicitly requested.

Git reports `C:\Users\sekip/.config/git/ignore` permission warnings during status/diff commands; this does not block code changes.

## Files Changed in Last Run

backend/app/models/ai.py - MODIFIED: added missing `datetime` import for existing Gap 67 `AIAgentRun.started_at`.

backend/app/api/v1/endpoints/ai.py - MODIFIED: tightened NL command and AI governance endpoints to AI permission dependencies.

frontend/src/lib/aiApi.ts - MODIFIED: added NL command and AI governance TypeScript types/API methods.

frontend/src/app/dashboard/ai/nl-command/page.tsx - NEW/MODIFIED: implemented command parser UI, confirmation flow, risk/status display, KPI cards, and history table using `aiApi`.

frontend/src/app/dashboard/ai/governance/page.tsx - NEW: implemented governance dashboard, policy registry form/list, run audit logger, filters, status KPIs, and run table.

backend/app/models/maintenance.py - MODIFIED: added `MaintenancePredictionStatus`, `MaintenancePredictionRisk`, and `MaintenancePrediction` linked to assets.

backend/app/schemas/maintenance.py - MODIFIED: added predictive maintenance read/review schemas.

backend/app/services/maintenance_service.py - MODIFIED: added rule-based predictive maintenance generation/list/review service logic.

backend/app/api/v1/endpoints/maintenance.py - MODIFIED: added predictive maintenance generate/list/review endpoints and serializer.

frontend/src/lib/maintenance.ts - MODIFIED: added predictive maintenance types/API methods.

frontend/src/app/dashboard/maintenance/predictive/page.tsx - NEW: added predictive maintenance operations page.

frontend/src/app/dashboard/maintenance/page.tsx - MODIFIED: added predictive maintenance quick link.

frontend/src/components/nav-config.tsx - MODIFIED: added Predictive Maintenance under Maintenance; AI nav entries for NL/Governance were already present before this run.

backend/app/models/esg.py - MODIFIED: added supplier sustainability risk/status enums and `SupplierSustainabilityScore`.

backend/app/models/__init__.py - MODIFIED: registered `SupplierSustainabilityScore`.

backend/alembic/versions/f0a1b2c3d4e5_esg_intelligence_gap69.py - NEW: migration for supplier sustainability score table and enum types.

backend/app/schemas/esg.py - MODIFIED: added supplier sustainability score schemas, energy intensity row, wastewater compliance snapshot, and ESG intelligence dashboard schemas.

backend/app/services/esg_service.py - MODIFIED: added supplier score validation/persistence, energy intensity per SKU aggregation, wastewater compliance aggregation, and ESG intelligence dashboard service.

backend/app/api/v1/endpoints/esg.py - MODIFIED: added ESG intelligence and supplier scorecard endpoints.

frontend/src/lib/esg.ts - MODIFIED: added ESG intelligence and supplier scorecard types/API methods.

frontend/src/app/dashboard/esg/intelligence/page.tsx - NEW: added ESG intelligence workspace.

frontend/src/app/dashboard/esg/page.tsx - MODIFIED: added ESG Intelligence quick link.

frontend/src/components/nav-config.tsx - MODIFIED: added ESG Intelligence under ESG & Sustainability.

backend/app/models/integrations.py - MODIFIED: added plugin install/lifecycle enums, marketplace metadata on connector registry, plugin installation state, and lifecycle audit event models.

backend/app/schemas/integrations.py - MODIFIED: added marketplace connector, plugin installation, install request/config update, and lifecycle event schemas.

backend/app/services/integration_service.py - MODIFIED: added marketplace install/config/lifecycle/dependency/audit service logic.

backend/app/api/v1/endpoints/integrations.py - MODIFIED: extended existing integration marketplace endpoints with tenant-aware catalog state, install/config/lifecycle/events APIs, and installation-aware connector test.

backend/app/models/__init__.py - MODIFIED: registered connector registry and plugin marketplace models.

backend/alembic/versions/f1a2b3c4d5e6_plugin_marketplace_gap70.py - NEW: migration for plugin marketplace metadata, install state, and lifecycle audit events.

frontend/src/lib/integrations.ts - MODIFIED: added marketplace connector, plugin installation, lifecycle event types, and marketplace API methods.

frontend/src/app/dashboard/integrations/marketplace/page.tsx - MODIFIED: upgraded marketplace UI to install/enable/disable/uninstall/test connectors with tenant state and lifecycle audit.

backend/app/api/v1/endpoints/traceability.py - MODIFIED: added missing `get_current_user` import so the backend can import traceability routes and start successfully.

Local Docker Postgres schema - UPDATED: added missing nullable `audit_logs` context/integrity columns and indexes to match the current `AuditLog` model.

## Validation Results

Frontend TypeScript: PASS (`npm.cmd run type-check`) after Gap 69 changes.

Frontend production build: PASS (`npm.cmd run build`). Build output includes `/dashboard/esg/intelligence`.

Frontend TypeScript: PASS (`npm.cmd run type-check`) after Gap 70 marketplace changes.

Frontend production build: PASS (`npm.cmd run build`) after Gap 70 marketplace changes.

Frontend lint: BLOCKED. `npm.cmd run lint` triggers interactive Next.js ESLint configuration prompt.

Local backend Python compile: BLOCKED. `python`, `python3`, and `py` are not available on PATH; Docker backend compile passed below.

Backend Docker startup/import: PASS. `docker compose exec -T backend python -c "import app.main; print('import-ok')"` completed successfully.

Backend Docker Python compile: PASS. `docker compose exec -T backend python -m compileall app` completed successfully.

Backend health check: PASS. `GET http://localhost:8000/health` returned HTTP 200 with database connected.

Auth bad-credentials path: PASS. `POST /api/v1/auth/login` with invalid password now returns 401 instead of an empty response or 500.

Auth seeded admin login: PASS. `POST /api/v1/auth/login` with username `admin` and password `admin123` returned HTTP 200 with an access token.

Note: one earlier parallel validation attempt caused `tsc` to read `.next/types` while `next build` was regenerating it, producing transient missing generated type-file errors. Sequential `npm.cmd run type-check` passed afterward.

## Notes for Next Claude Run

All 70 planned gaps are now marked implemented. The next run should focus on backend validation and hardening, not new gap implementation.

If login shows `ERR_EMPTY_RESPONSE` again, check Docker backend logs first. The last root cause was an import-time crash in `traceability.py`, which left the Uvicorn reloader listening while no worker was serving requests.

The default seeded login is username `admin`, not the email address. `admin@erp.com` is stored as email, but `authenticate()` currently looks up `User.username`.

The live dev DB audit schema has been repaired directly to restore login. Do not forget to normalize this through Alembic after resolving duplicate revision IDs.

Gap 70 marketplace deliberately models plugins/apps as governed connector/module metadata and tenant configuration. It does not load arbitrary code or install executable packages.

Gap 70 depends on the existing integration connector registry and `integrations.view` / `integrations.edit` permission pattern. Lifecycle actions are audited in `integration_plugin_lifecycle_events`.

Gap 69 ESG intelligence intentionally reuses existing `UtilityCostAllocation` and `WastewaterRecord` data. Energy intensity currently reports product-linked electricity/solar allocations with kWh-like quantities and flags rows with missing production volume or non-kWh quantities.

Gap 69 supplier scorecards support direct supplier FK when available but also store `supplier_name` for external suppliers or incomplete master-data onboarding.

Gap 68 predictive maintenance uses maintenance `asset_no` as the IoT `machine_id` bridge. If the plant later stores explicit IoT-to-asset mapping, update the generator to prefer that mapping.

Gap 68 prediction generation is explainable and rule-based, not ML. It stores score components in `source_metrics` for auditability and future ML replacement.

Gap 66 execute endpoint is still intentionally stubbed: it records execution but does not call target ERP endpoints. Future hardening should wire internal execution with extracted parameters and stricter permission checks per target action.

Gap 67 backend provides policy CRUD-lite, run logging, run listing, and dashboard KPIs. Future hardening can add immutable audit exports, policy evaluation helpers, and direct integration with all AI agent execution paths.
