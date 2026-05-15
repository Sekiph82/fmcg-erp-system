# GAP-018 GS1 / Label Printing / Packaging Compliance — Audit

## Summary

GS1 system is structurally complete (9 models, 22+ endpoints, 9 frontend pages, AI agents, 4 reports). However two critical bugs exist in production endpoints, the module is not promoted to MODULE_DEFINITIONS (so has no permission codes), and several barcode types are enumerated but not actually generated.

---

## What Exists

### Models (`backend/app/models/gs1.py`) — 9 tables

| Model | Purpose |
|---|---|
| `GS1CompanyConfig` | Company GS1 prefix, SSCC serial counter |
| `ProductGS1Config` | GTIN, barcode type, packaging level, serialization flags, packaging hierarchy counts |
| `LotBarcodeRecord` | Per-lot barcode generation with GS1 AI string, base64 image |
| `SSCCPallet` | SSCC-18 pallet with check digit, status, location |
| `SSCCPalletLot` | Many-lot-per-pallet link table |
| `GS1LabelTemplate` | HTML/CSS label template with width/height/fields metadata |
| `LabelPrintJob` | Print job with trigger, status, printer_name |
| `LabelPrintJobItem` | Per-item in a print job |
| `GS1AIRecommendation` | AI compliance suggestions |

### Service (`backend/app/services/gs1_service.py`) — 45+ functions

- Check digit algorithms: GS1 mod-10, GTIN-13/14, SSCC-18
- GS1 AI string builder and parser (AIs: 01, 10, 17, 11, 21, 00)
- Barcode image generation via python-barcode and qrcode libraries
- Full CRUD for all models
- Print job lifecycle (create → complete)
- AI agents: label validator, packaging optimizer

### Endpoints (`backend/app/api/v1/endpoints/gs1.py`) — 22+ endpoints

| Category | Endpoints |
|---|---|
| Dashboard | GET /dashboard |
| Company Config | POST, GET, GET /{id} |
| Product Config | POST, GET, GET /{id}, PATCH /{id}, GET /by-product/{id} |
| Barcode | POST /generate, GET, GET /{id} |
| Scanning | POST /scan/decode, GET /scan/decode, POST /scan/dispatch-validate, GET /gtin/lookup |
| SSCC/Pallet | POST /generate, GET, GET /{id}, POST /{id}/lots, PATCH /{id}/status |
| Label Templates | POST, GET, GET /{id}, PATCH /{id} |
| Print Jobs | POST /print, GET /print, POST /print/{id}/complete |
| AI Agents | POST /ai/run-label-validator, POST /ai/run-packaging-optimizer, GET /ai/recommendations, PATCH /ai/recommendations/{id} |
| Reports | GET /reports/print-history, /sscc-tracking, /packaging-hierarchy, /barcode-usage |

### Frontend

9 pages in `/dashboard/gs1/`: dashboard, config, barcodes, sscc, labels, print-queue, scan, ai, reports.

### GS1 Standards Covered

- GS1 AI strings: (01) GTIN, (10) lot, (17) expiry, (11) production date, (21) serial, (00) SSCC
- Check digits: EAN-13, GTIN-14, SSCC-18
- Packaging levels: UNIT, INNER_PACK, CARTON, PALLET
- Barcode generation working: EAN-13, CODE-128, QR Code

---

## Critical Bugs (Runtime Failures)

| Endpoint | Bug | Location |
|---|---|---|
| `GET /gtin/lookup` | References `product_config.product_sku_code` — field does not exist on model | gs1.py ~line 545 |
| `POST /scan/dispatch-validate` | References `product_config.product_sku_code` — same missing field | gs1.py ~line 506 |
| `GET /gtin/lookup` | References `product_config.net_weight_g` and `net_volume_ml` — fields don't exist | gs1.py ~lines 547-548 |

**Fix required:** Add `product_sku_code`, `net_weight_g`, `net_volume_ml` to `ProductGS1Config` model and migration, or remove references from endpoints.

---

## Module Registration Gap

- GS1 is in `ENDPOINT_ROUTE_DEFINITIONS` (not `MODULE_DEFINITIONS`)
- No permission codes in `registry_permission_codes()`
- No gs1 permissions seeded in `app/db/seed.py`
- All endpoints use only `get_current_user` (no `require_permission`)
- Navigation links use `quality.view` as guard (wrong domain)

---

## What Is Partial or Missing

### Backend Gaps

| Gap | Detail |
|---|---|
| Barcode generation — GS1-DataMatrix, ITF-14, GS1-QR | Enumerated in `BarcodeType` enum but no generation code |
| GLN (Global Location Number) | No model, no endpoint |
| Label approval workflow | No status field (DRAFT→PENDING_APPROVAL→APPROVED), no approver FK |
| Batch barcode generation | No bulk endpoint; generate is per-lot only |
| PDF/ZPL label export | HTML/CSS stored but no export/render endpoint |
| Packaging compliance checklist | No validation of label elements against standard requirements |
| Print queue scheduling | Only PENDING/COMPLETED; no queued/retry/failed states |

### Frontend Gaps

| Gap | Detail |
|---|---|
| Visual label template designer | Only HTML/CSS text fields; no drag-and-drop UI |
| Batch print builder | No UI to select multiple lots for one print job |
| Label approval UI | No approval workflow page |
| Packaging compliance checklist page | Not present |

---

## Recommended Scope for GAP-018

### Do (fix bugs + promotion)
1. Add missing model fields: `product_sku_code`, `net_weight_g`, `net_volume_ml` to `ProductGS1Config` (migration)
2. Promote GS1 from ENDPOINT_ROUTE_DEFINITIONS → MODULE_DEFINITIONS with permission actions: view, create, edit, approve, print, report, admin
3. Add gs1 permission codes to seed.py; add to admin role
4. Fix nav-config.tsx to use `gs1.view` guard (currently `quality.view`)
5. Add `require_permission` guards to write endpoints

### Skip (out of scope)
- Visual label template designer UI (complex frontend-only feature)
- GLN model (no regulatory requirement for current markets)
- GS1-DataMatrix/ITF-14 generation (requires external library)
- PDF/ZPL export (separate integration GAP)

---

## Files of Interest

| File | Purpose |
|---|---|
| `backend/app/models/gs1.py` | All GS1 models (ProductGS1Config missing 3 fields) |
| `backend/app/api/v1/endpoints/gs1.py` | GS1 endpoints (2 endpoints have runtime bugs) |
| `backend/app/services/gs1_service.py` | Service layer |
| `backend/app/core/module_registry.py` | GS1 in ENDPOINT_ROUTE_DEFINITIONS (line ~351) |
| `backend/alembic/versions/a3b4c5d6e7f8_gs1_label_printing.py` | Original GS1 migration |
| `frontend/src/components/nav-config.tsx` | GS1 nav section (wrong permission guard) |
