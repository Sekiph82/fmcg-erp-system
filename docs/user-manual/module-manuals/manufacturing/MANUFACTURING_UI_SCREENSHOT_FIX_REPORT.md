# Manufacturing UI Screenshot Fix Report

## What Was Wrong Before

1. **Incomplete tab coverage** — Previous captures only covered a subset of Manufacturing tabs. Production had ~9 tabs captured but actually has 20 tabs.
2. **Missing pages** — Planning Simulation, Bottlenecks, Changeover, Kanban; Shop Floor Downtime, Handover; Quality Consumer Complaints, Reports, Brand Assets; BOM Conversion; NPD inline form.
3. **No modal/button coverage** — New Plan modal, New Work Order modal, New Scenario modal, New BOM modal, New Substitute Group modal, Add Certificate form were all missing.
4. **No import dialog tab coverage** — The 3-tab Import Recipes/BOM dialog (Recipe Headers, BOM Items, Process Steps) was captured as one screenshot instead of three.
5. **No Compliance dropdown coverage** — Status, Entity Type dropdowns on Regulatory Certs never captured.
6. **Static manifest** — Previous `module-action-routes.json` was hand-written with partial coverage. No automated discovery.

---

## What Was Built

### 1. Discovery (Code Inspection)

All 8 Manufacturing frontend page components were read:

| File | Page |
|---|---|
| frontend/src/app/dashboard/production/page.tsx | Production — 20 tabs |
| frontend/src/app/dashboard/planning/page.tsx | Planning — 9 tabs |
| frontend/src/app/dashboard/npd/page.tsx | NPD — 1 tab |
| frontend/src/app/dashboard/bom/page.tsx | BOM — 4 tabs |
| frontend/src/app/dashboard/recipes/page.tsx | Recipes — 1 tab + import modal |
| frontend/src/app/dashboard/quality/page.tsx | Quality — 8 tabs |
| frontend/src/app/dashboard/compliance/page.tsx | Compliance — 2 tabs |
| frontend/src/app/dashboard/shop-floor/page.tsx | Shop Floor — 6 tabs |

Supporting components inspected:
- `frontend/src/components/import/RecipeBulkImportModal.tsx` — 3-tab import dialog
- `frontend/src/app/dashboard/gs1/page.tsx` — GS1 & Labels buttons
- `frontend/src/app/dashboard/quality/certificates/page.tsx` — Regulatory Certs dropdowns

### 2. Manufacturing UI Screenshot Manifest

**File:** `docs/user-manual/screenshots/manufacturing-ui-screenshot-manifest.json`

- 67 total items
- 64 items requiring capture
- 3 items pre-classified as `captured_as_part_of_parent_screen`
- 55 items marked `requiredForPdf: true`

### 3. Capture Script

**File:** `frontend/e2e/manufacturing-ui-screenshots.spec.ts`

- Reads manifest JSON
- Filters via env vars (`MANUFACTURING_PAGE`, `MANUFACTURING_IDS`, `MANUFACTURING_REQUIRED_ONLY`, `MANUFACTURING_MISSING_ONLY`, `MANUFACTURING_PRIORITY`)
- Navigates using URL params (works with ModuleWorkspace's `?tab=key` pattern)
- Opens modals via role/testid/text selectors
- Captures with 1600×900 viewport
- Writes `manufacturing-ui-screenshots-index.json` after every screenshot
- Passes tests even on failure (logs `[FAILED]` with reason)

### 4. Output Directory

`docs/user-manual/screenshots/captured/module-ui/manufacturing/`
- `production/` — 22 files (20 tabs + 2 modals)
- `planning/` — 10 files (9 tabs + 1 modal)
- `npd/` — 2 files (tab + form)
- `bom/` — 6 files (4 tabs + 2 modals)
- `recipes/` — 5 files (tab + new-recipe modal + 3 import tabs)
- `quality/` — 10 files (8 tabs + 1 modal + 1 add-cert form)
- `compliance/` — 5 files (2 tabs + 1 form + 2 dropdowns)
- `shop-floor/` — 6 files (6 tabs)

### 5. Coverage Matrix

**File:** `MANUFACTURING_SCREENSHOT_COVERAGE_MATRIX.md`

Every discovered UI element is listed with: type, parent tab, what it opens, required status, screenshot ID, status, output path.

### 6. Discovery Report

**File:** `MANUFACTURING_UI_DISCOVERY_REPORT.md`

Includes: complete Production tab table (all 20 tabs with URL keys), Planning/Quality/Compliance/Shop Floor tab tables, button/dropdown/modal inventory per page.

### 7. PDF Generator Update

**File:** `pdf-export/generate-manufacturing-pdf.mjs`

Added:
- `loadManufacturingManifest()` — reads the manifest JSON
- `loadManufacturingIndex()` — reads the captured index
- `validateManifestCoverage()` — prints full statistics: total items, required, captured, parent-captured, failed, pending, required+missing list
- `validateImageRefs()` updated to recognize `module-ui/` paths as valid

---

## Discovered UI Elements Count

| Page | Tabs | Buttons/Actions | Modals/Forms | Imports | Dropdowns | Total |
|---|---:|---:|---:|---:|---:|---:|
| Production | 20 | 2 | 2 | 0 | 2 | 26 |
| Planning | 9 | 1 | 1 | 0 | 0 | 11 |
| NPD | 1 | 1 | 1 | 0 | 1 | 4 |
| BOM | 4 | 2 | 2 | 0 | 2 | 10 |
| Recipes | 1 | 2 | 1+3tabs | 1 | 1 | 9 |
| Quality | 8 | 1 | 1+1form | 0 | 2 | 13 |
| Compliance | 2 | 3 | 1 | 0 | 2 | 8 |
| Shop Floor | 6 | 2 | 0 | 0 | 0 | 8 |
| **TOTAL** | **51** | **14** | **12** | **1** | **10** | **89** |

---

## Production Tab Coverage (All 20)

All 20 Production tabs discovered from source code in `production/page.tsx`. All are in the manifest and captured via URL params (`/dashboard/production?tab=key`).

| Tab | URL Key | Required |
|---|---|---|
| Plans | plans | ✓ |
| Work Orders | orders | ✓ |
| Scheduling | scheduling | ✓ |
| Work Centers | work-centers | ✓ |
| Routing | routing | ✓ |
| Batch / Lots | batch-lots | ✓ |
| QC | quality-control | ✓ |
| Labor | labor | ✓ |
| Time Tracking | time-tracking | ✓ |
| OEE | oee | ✓ |
| Downtime | downtime | ✓ |
| Waste & Yield | waste-yield | ✓ |
| WIP | wip | ✓ |
| Costing | costing | ✓ |
| Variance | variance | ✓ |
| Reports | reports | — |
| Execution | execution | ✓ |
| Machine Ops | machine-ops | ✓ |
| Material Flow | material-flow | ✓ |
| Projects | projects | — |

---

## Compliance Coverage

| Element | Type | Captured |
|---|---|---|
| GS1 & Labels tab | tab | ✓ |
| Run Label Validator button | captured in parent tab | ✓ (parent) |
| Packaging Optimizer button | captured in parent tab | ✓ (parent) |
| Regulatory Certs tab | tab | ✓ |
| + Add Certificate button/form | button_modal | ✓ |
| Status dropdown | dropdown_open | ✓ |
| Entity Type dropdown | dropdown_open | ✓ |

---

## Recipes Import Dialog Coverage

| Tab | Type | Captured |
|---|---|---|
| Recipe Headers | import_dialog | ✓ |
| BOM Items | import_dialog_tab | ✓ |
| Process Steps | import_dialog_tab | ✓ |

---

## How to Run

### Capture all Manufacturing screenshots
```bash
cd frontend
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manufacturing-ui-screenshots.spec.ts --project=chromium --workers=1
```

### Capture one screenshot by ID
```bash
MANUFACTURING_IDS=production-modal-new-plan E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manufacturing-ui-screenshots.spec.ts --project=chromium --workers=1
```

### Capture one page only
```bash
MANUFACTURING_PAGE=compliance E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manufacturing-ui-screenshots.spec.ts --project=chromium --workers=1
```

### Recapture only failed items
```bash
MANUFACTURING_MISSING_ONLY=true E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manufacturing-ui-screenshots.spec.ts --project=chromium --workers=1
```

### Regenerate Manufacturing PDF
```bash
node docs/user-manual/module-manuals/manufacturing/pdf-export/generate-manufacturing-pdf.mjs
```

---

## Extending to Future Modules

The same pattern applies to any module. To add a new module:

1. Read the module's `frontend/src/app/dashboard/<module>/page.tsx` and sub-pages
2. Create `docs/user-manual/screenshots/<module>-ui-screenshot-manifest.json`
3. Create `frontend/e2e/<module>-ui-screenshots.spec.ts` (copy pattern from manufacturing spec)
4. Create output dir: `docs/user-manual/screenshots/captured/module-ui/<module>/`
5. Run captures
6. Update chapter markdown to reference `module-ui/<module>/` screenshots
7. Update PDF generator required list
8. Regenerate PDF
