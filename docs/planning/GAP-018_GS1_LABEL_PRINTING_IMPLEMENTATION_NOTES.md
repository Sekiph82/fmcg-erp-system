# GAP-018 GS1 / Label Printing / Packaging Compliance — Implementation Notes

## Summary

GAP-018 fixed 3 runtime bugs (missing model fields causing AttributeError in production endpoints), promoted GS1 from ENDPOINT_ROUTE_DEFINITIONS to MODULE_DEFINITIONS with full permission framework, and aligned nav-config.tsx to use the correct permission domain.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Audit | `docs/planning/GAP-018_GS1_LABEL_PRINTING_AUDIT.md` |
| Schema Design | `docs/planning/GAP-018_GS1_LABEL_PRINTING_SCHEMA_DESIGN.md` |
| Migration | Added `backend/alembic/versions/20260515_0060_gs1_product_config_fields.py` |
| Models | Added 3 columns to `ProductGS1Config` in `backend/app/models/gs1.py` |
| Schemas | Added 3 fields to `ProductGS1ConfigCreate`/`Update`/`Out` in `backend/app/schemas/gs1.py` |
| Services | SKIPPED — service layer did not reference missing fields |
| Endpoints | SKIPPED — runtime bugs fixed by adding model fields; no endpoint code changes |
| Frontend | SKIPPED — 9 pages exist; nav guard fixed in permissions step |
| Permissions | GS1 promoted to MODULE_DEFINITIONS; 7 permission codes seeded; admin role updated; nav-config fixed |
| Tests | `backend/tests/test_gap018_gs1_label_printing.py` — 10/10 passed |

---

## Bug Fixes

### Root Cause

Three fields referenced in `gs1.py` endpoints (line ~506, ~545, ~547-548) did not exist on the `ProductGS1Config` ORM model:
- `product_config.product_sku_code`
- `product_config.net_weight_g`
- `product_config.net_volume_ml`

Any request hitting `GET /gs1/gtin/lookup` or `POST /gs1/scan/dispatch-validate` would raise `AttributeError` at runtime.

### Fix

Added 3 nullable columns to the model and migration. Endpoints now resolve correctly without any endpoint code changes.

---

## Changes Made

### Migration: `20260515_0060_gs1_product_config_fields.py`

| Table | Column | Type |
|---|---|---|
| `product_gs1_configs` | `product_sku_code` | VARCHAR(100) |
| `product_gs1_configs` | `net_weight_g` | NUMERIC(12,4) |
| `product_gs1_configs` | `net_volume_ml` | NUMERIC(12,4) |

Down_revision: `20260515_0050`. Offline SQL verified.

### Module Registry: `backend/app/core/module_registry.py`

- Removed: `EndpointRouteDefinition(key="gs1", ...)`
- Added: `ModuleDefinition(key="gs1", label="GS1 / Label Printing", permission_actions=("view", "create", "edit", "approve", "print", "report", "admin"), sidebar_group="Compliance", critical=False)`

### Seed: `backend/app/db/seed.py`

Added 7 permission tuples for `gs1` module. Added all 7 to admin role.

### Nav Config: `frontend/src/components/nav-config.tsx`

Fixed GS1 section guard and all 9 items from `quality.view` to correct `gs1.*` codes:
- Section guard: `gs1.view`
- Dashboard, Config, Barcodes, Labels, SSCC, Scan: `gs1.view`
- Print Queue: `gs1.print`
- Reports: `gs1.report`
- AI Agents: `gs1.admin`

---

## Known Limitations

| Item | Detail |
|---|---|
| Live migration | Blocked until Docker/PostgreSQL available |
| Barcode type coverage | GS1-DataMatrix, ITF-14, GS1-QR enumerated but not generated |
| Label template designer | HTML/CSS text fields only; no visual builder |
| PDF/ZPL export | Not implemented |
| Label approval workflow | No approval status field on templates |
