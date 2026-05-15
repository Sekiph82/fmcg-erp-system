# GAP-019 Shelf-Life / FEFO / Expiry Control — Implementation Notes

## Summary

GAP-019 promoted `shelf_life` from `EndpointRouteDefinition` to `ModuleDefinition` with a full permission framework, seeded 7 permissions, and aligned nav-config.tsx to use the correct permission domain. No schema changes were required — the module was already fully implemented.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Audit | `docs/planning/GAP-019_SHELF_LIFE_FEFO_AUDIT.md` |
| Schema Design | SKIP — no new tables needed |
| Migration | SKIP — no schema changes |
| Models | SKIP — 11 models already complete |
| Schemas | SKIP — schemas already complete |
| Services | SKIP — 1293-line service complete |
| Endpoints | SKIP — 32 endpoints already complete |
| Frontend | SKIP — 12 pages + TypeScript client complete |
| Permissions | shelf_life promoted to MODULE_DEFINITIONS; 7 codes seeded; admin role updated; nav-config fixed |
| Tests | `backend/tests/test_gap019_shelf_life_fefo.py` — 10/10 passed |

---

## What Was Already Complete

### Models (11 total)
`LotShelfLifeProfile`, `ItemShelfLifeConfig`, `BulkHoldRecord`, `CustomerShelfLifeRule`, `DispositionSuggestion`, `FEFOAuditLog`, `ShelfLifeAlert`, `RetestRequest`, `SLAIRecommendation`, `ShelfLifeExtension`, `PickingStrategyConfig`

### Service (`shelf_life_service.py`)
Key functions: `rank_lots_fefo`, `validate_issue`, `validate_shipment`, `create_bulk_hold`, `get_fefo_compliance_report`, `generate_alerts`, `generate_disposition_suggestions`, `list_near_expiry`, `list_expired`, `run_all_ai_agents`

### Endpoints (32 total)
Full FEFO, batch, rules, alerts, holds, customer requirements, disposal, retest, reports, and AI agent coverage.

### Frontend (12 pages)
`/dashboard/shelf-life/` — Dashboard, FEFO Config, Lot Aging, Near-Expiry, Expired, Retest Queue, Shipment Validation, Production Validation, FEFO Compliance Audit, Disposition Console, Customer SL Rules, Bulk Hold Monitor

---

## Changes Made

### Module Registry: `backend/app/core/module_registry.py`

- Removed: `EndpointRouteDefinition(key="shelf_life", ...)` → replaced with comment `# shelf_life promoted to MODULE_DEFINITIONS`
- Added new `ModuleDefinition`:
  ```python
  ModuleDefinition(
      key="shelf_life",
      label="Shelf-Life / FEFO",
      route_prefix="/shelf-life",
      import_path="app.api.v1.endpoints.shelf_life",
      permission_actions=("view", "create", "edit", "approve", "hold", "dispose", "report"),
      sidebar_group="Supply Chain",
      icon_key="calendar-clock",
      critical=True,
  )
  ```

### Seed: `backend/app/db/seed.py`

Added 7 permission tuples for `shelf_life` module. Added all 7 to admin role.

| Code | Label | Sensitive |
|---|---|---|
| `shelf_life.view` | View Shelf-Life | Public |
| `shelf_life.create` | Create Shelf-Life | No |
| `shelf_life.edit` | Edit Shelf-Life | No |
| `shelf_life.approve` | Approve Shelf-Life | No |
| `shelf_life.hold` | Hold Batches | No |
| `shelf_life.dispose` | Dispose Batches | No |
| `shelf_life.report` | Report Shelf-Life | No |

### Nav Config: `frontend/src/components/nav-config.tsx`

Fixed shelf-life section (12 items):
- Section guard: `production.view` → `shelf_life.view`
- Dashboard, FEFO Config, Lot Aging, Near-Expiry, Expired, Shipment/Production Validation: `shelf_life.view`
- Retest Queue: `shelf_life.approve`
- FEFO Compliance Audit: `shelf_life.report`
- Disposition Console: `shelf_life.dispose`
- Customer SL Rules: `shelf_life.edit`
- Bulk Hold Monitor: `shelf_life.hold`

---

## Known Limitations

| Item | Detail |
|---|---|
| FEFO blocking | `validate_issue` returns violations but does not block picks at WMS layer |
| Stock value at risk | Endpoint exists but calculation returns placeholder; no inventory costing join |
| Temperature-adjusted shelf life | No temp correction factor — requires IoT/sensor integration |
| Regulatory minimums | No FDA/EU/Kenya regulatory floor enforcement |
| Live migration | No new migration needed; alembic head remains `20260515_0040` |
