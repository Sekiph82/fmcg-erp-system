# GAP-015 UI/UX Navigation and Sidebar Information Architecture — Audit

## Existing State Summary

| Layer | State |
|---|---|
| `frontend/src/components/nav-config.tsx` | 68 nav sections, 579 items — exists and functional |
| `frontend/src/lib/modules.ts` | Module manifest + permission coverage client — uses `apiClient` (no bare fetch) |
| Backend `MODULE_DEFINITIONS` | 20 modules with sidebar groups |
| Backend `ENDPOINT_ROUTE_DEFINITIONS` | 117 loose route definitions |
| Frontend dashboard routes | 106 actual pages/folders under `/app/dashboard/` |

---

## Critical Findings

### CRITICAL-001: 41 Dashboard Routes Have No Nav Entry

The following dashboard routes exist as code but are not reachable via the sidebar nav:

`approvals`, `calls`, `companies`, `containers`, `copacking`, `developer`, `dynamic-pricing`, `email`, `esign`, `import-history`, `inventory`, `iot`, `knowledge-base`, `logs`, `loyalty`, `market-intelligence`, `materials`, `meetings`, `messages`, `mobile`, `movements`, `npd`, `nps`, `payroll`, `permissions`, `portal`, `products`, `putaway`, `recipes`, `reports`, `roles`, `secondary-sales`, `security`, `shelf-life`, `suppliers`, `surveys`, `users`, `utilities`, `warehouses`, `whatsapp`, `wms`

Notable missing entries: `esign`, `knowledge-base`, `reports`, `payroll`, `users`, `roles`, `permissions`, `approvals` — all functional modules with backend support.

### CRITICAL-002: Admin Section Uses 7 Wrong-Domain Permission Codes

The `admin` nav section (guard: `utilities.view`) contains items gated by completely different domains:
- `hr.view` — HR domain items inside an admin section
- `users.view` — user management (should use `roles` or `users` module permission)
- `audit.view` — audit trail
- `finance.view` — finance items mixed in
- `knowledge_base.view`, `documents.view`, `esign.view` — document admin items

This means a user with only `utilities.view` sees the admin section header but each item independently blocks based on its own permission — creating a confusing experience where the section is visible but all items may be hidden.

### MEDIUM-001: Marketing Section Has 15 Unique Permission Codes

The marketing nav section uses 15 different permission codes across its items (`marketing.view`, `campaigns.view`, `crm.view`, `segments.view`, `promotions.view`, `ad_performance.view`, `brand_spend.view`, `trade_spend.view`, `social_media.view`, `influencers.view`, `customer_visits.view`, `ecommerce.view`, `surveys.view`, `ai_optimizer.view`, `marketing_analytics.view`). This creates extremely fragmented access control — many of these sub-modules may not have corresponding backend permissions in seed.

### MEDIUM-002: Warehouse Section Has No Section-Level Permission

The `warehouse` nav section has no `permission` guard at the section level. Items use both `inventory.view` and `wms.view`. Users see the section header regardless of their permission set.

### MEDIUM-003: Tax Section Has Cross-Domain Bleed

The `tax` nav section (guard: `tax.view`) contains items using `finance.view` — a separate permission domain. Items protected by `finance.view` are nested under a `tax.view`-gated section, creating inconsistent access patterns.

### LOW-001: Module Registry vs Nav Config Alignment Mismatch

Backend `MODULE_DEFINITIONS` has 20 modules with sidebar groups, but `nav-config.tsx` has 68 sections. The nav is far more granular than the registry, meaning:
- Backend permission codes drive nav item visibility
- Sidebar group names on `MODULE_DEFINITIONS` don't map to `nav-config.tsx` section IDs
- New modules promoted to `MODULE_DEFINITIONS` won't automatically appear in the sidebar

---

## What Is NOT Missing

- Core navigation infrastructure: `nav-config.tsx` is functional and drives sidebar rendering
- `modules.ts`: proper API client for module manifest/permission coverage
- Permission-filtered nav items: existing items do use permission guards (just sometimes wrong ones)
- `apiClient` usage: no bare `fetch` calls found in nav-config

---

## Orphan Detail — High-Value Missing Nav Entries

These should be added to the nav (they have functional backend and frontend pages):

| Route | Expected Section | Backend Module |
|---|---|---|
| `/reports` | Analytics | `reports` (MODULE_DEFINITIONS) |
| `/esign` | Administration | `esign` (MODULE_DEFINITIONS) |
| `/knowledge-base` | Administration | `knowledge_base` (MODULE_DEFINITIONS) |
| `/payroll` | HR & Payroll | `payroll_ke` (MODULE_DEFINITIONS) |
| `/users` | Administration | `users` (MODULE_DEFINITIONS) |
| `/roles` | Administration | `roles` (MODULE_DEFINITIONS) |
| `/permissions` | Administration | implicit (roles module) |
| `/approvals` | Operations | `approvals` (ENDPOINT_ROUTE_DEFINITIONS) |
| `/companies` | Administration | `company` (ENDPOINT_ROUTE_DEFINITIONS) |
| `/wms` | Warehouse | `wms` (MODULE_DEFINITIONS) |
| `/inventory` | Warehouse | `inventory` (MODULE_DEFINITIONS) |

---

## Scope for GAP-015

Based on this audit, prioritized work:

1. **GAP-015B** (Schema): No DB changes. Document which nav entries to add and which permission mismatches to fix.
2. **GAP-015C/D/E/F** (Migration/Models/Schemas/Services): SKIP — no backend schema changes needed.
3. **GAP-015G** (Endpoints): No new endpoints; existing module manifest endpoint is sufficient.
4. **GAP-015H** (Frontend): Add missing high-value nav entries; fix admin section permission guard; fix warehouse section guard; minor tax section cleanup.
5. **GAP-015I** (Permissions): No new permissions needed.
6. **GAP-015J** (Tests): Frontend type-check only — nav config is pure TypeScript.
7. **GAP-015K** (Docs): Implementation notes.
8. **GAP-015L** (Checks): Type-check and manual nav section review.
