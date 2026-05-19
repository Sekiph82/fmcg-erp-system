# Module Manual Production Queue

**Rule:** One module per run. Inspect actual code before writing any field-level documentation. Do not guess field names, status values, or import formats.

---

## Status

| Module | Routes | Chapters | Status | Completed |
|--------|--------|----------|--------|-----------|
| **Manufacturing** | recipes, bom, production, planning, shop-floor, npd, quality, compliance | 13 | ✅ COMPLETE | 2026-05-19 |
| Supply Chain | procurement, inventory, warehouses, wms, logistics | TBD | ⏳ PENDING | — |
| Finance & Payroll | finance, hr, payroll | TBD | ⏳ PENDING | — |
| Sales & Distribution | sales, pos, logistics | TBD | ⏳ PENDING | — |
| Admin & Master Data | admin, products, materials, suppliers | TBD | ⏳ PENDING | — |
| Analytics & AI | analytics, ai-hub | TBD | ⏳ PENDING | — |

---

## Next Module

**Supply Chain** — procurement, inventory, warehouses, WMS, logistics.

Before writing: inspect `frontend/src/app/dashboard/procurement/page.tsx`, `inventory/page.tsx`, `warehouses/page.tsx`, `wms/page.tsx`, and their backend schemas in `backend/app/schemas/`.

---

## Per-Module Deliverables (checklist)

- [ ] `module-manuals/{module}/` folder with numbered chapter `.md` files
- [ ] `module-manuals/{module}/pdf-export/generate-{module}-pdf.mjs` — Playwright PDF generator
- [ ] `module-manuals/{module}/pdf-export/run-{module}-pdf.ps1` — Windows runner
- [ ] `module-manuals/{module}/pdf-export/run-{module}-pdf.sh` — Unix runner
- [ ] `module-manuals/{module}/SCREENSHOT_PLAN.md` — list of screenshots needed per chapter
- [ ] `module-manuals/{module}/PDF_EXPORT_REPORT.md` — generated after PDF run (not committed if gitignored)
- [ ] Help registry updated with `moduleManualPath` for all routes in this module
- [ ] Queue JSON updated: status → complete, completed_date set

---

## Code Inspection Checklist (per module)

Before writing field-level docs, read:

1. `frontend/src/app/dashboard/{module}/page.tsx` — form fields, status enums, table columns, tabs
2. `frontend/src/components/import/{Module}BulkImportModal.tsx` — CSV column names (if exists)
3. `backend/app/schemas/{module}.py` — Pydantic field names and types
4. `backend/app/api/v1/endpoints/{module}.py` — endpoint URLs, query params, HTTP methods
5. `backend/app/models/{module}.py` — database field names (source of truth)
