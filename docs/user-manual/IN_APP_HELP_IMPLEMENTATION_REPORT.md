# In-App Help Implementation Report

**Date:** 2026-05-19  
**Status:** COMPLETE — Help Center and contextual help drawer live

---

## Goal

Surface the existing ERP manual content (Kenya Go-Live + Full Reference) directly inside the application so users can access guidance without leaving the ERP.

---

## What Was Implemented

### 1. Help Registry (`frontend/src/lib/help/`)

Typed registry mapping 60+ ERP routes/tabs to manual guidance.

| File | Purpose |
|------|---------|
| `types.ts` | `HelpEntry` TypeScript interface |
| `help-registry.ts` | Static registry of all critical ERP routes with descriptions, module, role, manual paths, keywords |
| `get-help-for-route.ts` | Route matching: exact → base path → partial. Search, filter by module/role. |

Each `HelpEntry` contains:
- `id`, `title`, `route`, `path`, `tab?`
- `role` (admin/production/warehouse/procurement/quality/sales/finance/hr/manager)
- `module` (admin/production/inventory/wms/procurement/quality/compliance/sales/logistics/finance/hr/payroll/analytics/ai/master-data/core)
- `description` — short human-readable explanation
- `fullReferencePath` — relative path to full-reference MD chapter
- `quickGuidePath?` — relative path to Kenya go-live MD chapter (where applicable)
- `screenshotFile?` — screenshot filename in `captured/`
- `keywords[]` — search terms

### 2. Help Drawer (`frontend/src/components/help/HelpDrawer.tsx`)

Contextual slide-in panel (right-side, full-height).

- Opens via `?` button (mobile header or desktop floating button)
- Shows page title, module, role, description
- Kenya Quick Guide box (with manual file reference) — amber highlight
- Full Reference box (with chapter file reference)
- PDF note: "PDF available from admin/training package"
- Related keywords as chips
- "Browse Help Center" link at the bottom
- ESC key closes
- Backdrop click closes
- Accessible: `role="dialog"`, `aria-modal="true"`

### 3. Help Button (`frontend/src/components/help/HelpButton.tsx`)

Small `?` icon button. Added in two places in `DashboardShell.tsx`:
- Mobile header (next to NotificationBell)
- Desktop: floating button fixed bottom-right

**Single insertion point** — not added to 700 individual pages.

### 4. Help Center Page (`frontend/src/app/dashboard/help/page.tsx`)

Route: `/dashboard/help`

Features:
- Keyword search across all help entries
- Filter by module
- Filter by role
- Clear filters button
- Entry count display
- Card grid — each card links directly to the ERP route
- Shows Kenya guide badge where applicable
- Manual source file references at bottom
- PDF generation note (no public URL assumed)

### 5. Audit Script Fix (`scripts/audit-page-count.js`)

Added `"help"` to `STANDALONE_DIRS` so `/dashboard/help` is correctly classified as `E STANDALONE_OPERATIONAL` instead of `D FULL_DUPLICATE_UI`. Keeps D=0.

---

## PDF / Manual Link Strategy

**Decision: Option C — internal reference, no assumed public URL.**

- Help drawer shows manual file paths (`docs/user-manual/...`) as reference
- No broken external links
- PDF generation note: "Generate locally with `node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`"
- If PDFs are served publicly in the future, update `HelpDrawer.tsx` PDF note to include the URL

---

## Routes Covered

| Module | Routes in Registry |
|--------|-------------------|
| Core | dashboard |
| Admin | admin, users, roles, permissions |
| Master Data | products, materials, suppliers |
| Procurement | 4 routes |
| Inventory | 5 routes |
| WMS | 3 routes |
| Production | 8 routes |
| Shop Floor | 1 route |
| BOM & Planning | 2 routes |
| Quality | 4 routes |
| Compliance | 1 route |
| Sales | 5 routes |
| Logistics | 1 route |
| Finance | 6 routes |
| HR | 6 routes |
| Payroll | 3 routes |
| Analytics | 1 route |
| AI | 1 route |

**Total: 60+ entries**. Route fallback logic handles any route not explicitly in the registry.

---

## Files Changed

| File | Status |
|------|--------|
| `frontend/src/lib/help/types.ts` | NEW |
| `frontend/src/lib/help/help-registry.ts` | NEW |
| `frontend/src/lib/help/get-help-for-route.ts` | NEW |
| `frontend/src/components/help/HelpButton.tsx` | NEW |
| `frontend/src/components/help/HelpDrawer.tsx` | NEW |
| `frontend/src/app/dashboard/help/page.tsx` | NEW |
| `frontend/src/components/DashboardShell.tsx` | MODIFIED — added HelpButton + HelpDrawer |
| `scripts/audit-page-count.js` | MODIFIED — added "help" to STANDALONE_DIRS |

---

## What Remains for Later

| Item | Priority |
|------|----------|
| Screenshot thumbnails in drawer (requires static file serving of captured/) | Medium |
| Add /dashboard/help to Sidebar nav | Low |
| Add nav entry in CommandPalette | Low |
| Serve PDFs via public URL (S3, CDN, or static hosting) | Low |
| Smoke test for /dashboard/help | Low |
| Search integration with existing CommandPalette | Medium |

---

## Next Recommended Task

Add `/dashboard/help` to the Sidebar nav config so users can discover the Help Center from navigation.
