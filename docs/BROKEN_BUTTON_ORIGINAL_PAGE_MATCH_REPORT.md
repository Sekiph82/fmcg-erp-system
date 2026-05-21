# Broken Button → Original Page Match Report

**Date:** 2026-05-21
**Audit Version:** v2.0 — Dynamic Import Aware

---

## THE AUDIT BLIND SPOT: Dynamic Import Visibility

### Why Previous Reports Were Wrong

Previous audit logic:
> "If a standalone route is middleware-redirected, all action cards in that page are invisible to users."

**This is incorrect.** A page is user-visible if ANY of these are true:
1. It is directly reachable from sidebar/nav
2. It is dynamically imported by a workspace page as tab content

### The Cycle Count Example (Still Broken)

**Visible location:** `/dashboard/inventory?tab=cycle-count`
**Source component:** `frontend/src/app/dashboard/cycle-count/page.tsx`
**How it becomes visible:** `inventory/page.tsx` dynamically imports `cycle-count/page`
**Standalone route redirect:** `/dashboard/cycle-count` → `/dashboard/inventory?tab=cycle-count` (middleware)
**Result:** User sees Cycle Count dashboard with 5 navigation tiles — ALL broken.

| Card | Target | Current Behavior | Git History | Recommendation |
|------|--------|------------------|-------------|----------------|
| Count Plans | `/dashboard/cycle-count/plans` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Count Tasks | `/dashboard/cycle-count/tasks` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Count Entries | `/dashboard/cycle-count/entries` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Variance Review | `/dashboard/cycle-count/variances` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |
| Reports & AI | `/dashboard/cycle-count/reports` | Redirect stub → same tab | REAL page in commit 674b6c5 (2026-05-01) | RESTORE_OLD_PAGE_FROM_GIT |

**Git evidence:** Commit `674b6c5` (2026-05-01) contained REAL implementations:
- `cycle-count/plans/page.tsx`: Full CRUD — listPlans, createPlan, generateTasks, updatePlan
- `cycle-count/variances/page.tsx`: Full approve/reject workflow with bulk selection
- `cycle-count/tasks/page.tsx`: Task queue management
- `cycle-count/entries/page.tsx`: Physical count entry recording
- `cycle-count/reports/page.tsx`: Accuracy and variance reporting

These were deleted in `bd6faf5` (2026-05-17) and replaced with redirect stubs.

---

## Statistics

| Metric | Count |
|--------|-------|
| Dynamically imported pages analyzed | 188 |
| Pages with broken cards (user-visible) | 59 |
| Pages: BOTH redirect stub AND has broken cards | 58 |
| **Total broken visible action targets** | **296** |
| Critical severity | 24 |
| High severity | 217 |
| Medium severity | 55 |
| Git history matches found | 22 |
| High-confidence original page found | 5 |

---

## Recommendation Categories

| Category | Count | Description |
|----------|-------|-------------|
| RESTORE_OLD_PAGE_FROM_GIT | 5 | Real page existed in git — restore from commit 674b6c5 |
| CONVERT_TO_WORKSPACE_SUBVIEW | 291 | No prior real page — implement as ?view= or ?subtab= |

---

## Top 20 Critical/High Severity Broken Visible Buttons

| ID | Module | Visible At | Card Target | Why Broken | Git Found | Recommendation |
|----|--------|-----------|-------------|------------|-----------|----------------|
| BVT-0001 | Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/entries` | Redirect stub → /dashboard/inventory?tab=cycle-count | YES (real page) | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0002 | Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/plans` | Redirect stub → /dashboard/inventory?tab=cycle-count | YES (real page) | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0004 | Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/tasks` | Redirect stub → /dashboard/inventory?tab=cycle-count | YES (real page) | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0005 | Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `/dashboard/cycle-count/variances` | Redirect stub → /dashboard/inventory?tab=cycle-count | YES (real page) | RESTORE_OLD_PAGE_FROM_GIT |
| BVT-0006 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/bulk-hold-monitor` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0007 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/compliance` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0008 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/customer-rules` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0009 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/disposition` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0010 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/expired` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0011 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/fefo-config` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0012 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/lot-aging` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0013 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/near-expiry` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0014 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/production-validation` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0015 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/retest-queue` | Redirect stub → /dashboard/inventory?tab=shelf-life | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0016 | Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `/dashboard/shelf-life/shipment-validation` | Redirect stub → /dashboard/inventory?tab=shelf-life | NO | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0017 | Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `/dashboard/traceability/backward` | Redirect stub → /dashboard/inventory?tab=traceability | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0018 | Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `/dashboard/traceability/forward` | Redirect stub → /dashboard/inventory?tab=traceability | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0019 | Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `/dashboard/traceability/genealogy` | Redirect stub → /dashboard/inventory?tab=traceability | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0020 | Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `/dashboard/traceability/mock-recall` | Redirect stub → /dashboard/inventory?tab=traceability | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |
| BVT-0021 | Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `/dashboard/traceability/recalls` | Redirect stub → /dashboard/inventory?tab=traceability | YES (stub) | CONVERT_TO_WORKSPACE_SUBVIEW |

---

## Full Breakdown by Module

### Supply Chain / Inventory

**Broken count:** 23

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `entries` | `/dashboard/cycle-count/entries` | redirect_stub → /dashboard/inventory?tab=cycle-count | Yes — real page commit 674b6c5 (2026-05-01) | frontend/src/app/dashboard/cycle-count/entries/page.tsx | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `plans` | `/dashboard/cycle-count/plans` | redirect_stub → /dashboard/inventory?tab=cycle-count | Yes — real page commit 674b6c5 (2026-05-01) | frontend/src/app/dashboard/cycle-count/plans/page.tsx | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `reports` | `/dashboard/cycle-count/reports` | redirect_stub → /dashboard/inventory?tab=cycle-count | Yes — real page commit 674b6c5 (2026-05-01) | frontend/src/app/dashboard/cycle-count/reports/page.tsx | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `tasks` | `/dashboard/cycle-count/tasks` | redirect_stub → /dashboard/inventory?tab=cycle-count | Yes — real page commit 674b6c5 (2026-05-01) | frontend/src/app/dashboard/cycle-count/tasks/page.tsx | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory?tab=cycle-count | `variances` | `/dashboard/cycle-count/variances` | redirect_stub → /dashboard/inventory?tab=cycle-count | Yes — real page commit 674b6c5 (2026-05-01) | frontend/src/app/dashboard/cycle-count/variances/page.tsx | high | RESTORE_OLD_PAGE_FROM_GIT |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `bulk-hold-monitor` | `/dashboard/shelf-life/bulk-hold-monitor` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `compliance` | `/dashboard/shelf-life/compliance` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `customer-rules` | `/dashboard/shelf-life/customer-rules` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `disposition` | `/dashboard/shelf-life/disposition` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `expired` | `/dashboard/shelf-life/expired` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `fefo-config` | `/dashboard/shelf-life/fefo-config` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `lot-aging` | `/dashboard/shelf-life/lot-aging` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `near-expiry` | `/dashboard/shelf-life/near-expiry` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `production-validation` | `/dashboard/shelf-life/production-validation` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `retest-queue` | `/dashboard/shelf-life/retest-queue` | redirect_stub → /dashboard/inventory?tab=shelf-life | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=shelf-life | `shipment-validation` | `/dashboard/shelf-life/shipment-validation` | redirect_stub → /dashboard/inventory?tab=shelf-life | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `backward` | `/dashboard/traceability/backward` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `forward` | `/dashboard/traceability/forward` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `genealogy` | `/dashboard/traceability/genealogy` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `mock-recall` | `/dashboard/traceability/mock-recall` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `recalls` | `/dashboard/traceability/recalls` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `regulatory` | `/dashboard/traceability/regulatory` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Inventory | /dashboard/inventory?tab=traceability | `search` | `/dashboard/traceability/search` | redirect_stub → /dashboard/inventory?tab=traceability | Yes — redirect stub commit bd6faf5 | Needs new implementation | medium | CONVERT_TO_WORKSPACE_SUBVIEW |


### Manufacturing / Planning

**Broken count:** 8

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Manufacturing / Planning | /dashboard/planning?tab=mrp | `forecast` | `/dashboard/mrp/forecast` | redirect_stub → /dashboard/planning?tab=mrp | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=mrp | `run` | `/dashboard/mrp/run` | redirect_stub → /dashboard/planning?tab=mrp | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=mrp | `suggestions` | `/dashboard/mrp/suggestions` | redirect_stub → /dashboard/planning?tab=mrp | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=kanban | `ai` | `/dashboard/kanban/ai` | redirect_stub → /dashboard/planning?tab=kanban | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=kanban | `boards` | `/dashboard/kanban/boards` | redirect_stub → /dashboard/planning?tab=kanban | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=kanban | `cards` | `/dashboard/kanban/cards` | redirect_stub → /dashboard/planning?tab=kanban | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=kanban | `reports` | `/dashboard/kanban/reports` | redirect_stub → /dashboard/planning?tab=kanban | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Planning | /dashboard/planning?tab=kanban | `view` | `/dashboard/kanban/view` | redirect_stub → /dashboard/planning?tab=kanban | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Manufacturing / Production

**Broken count:** 19

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Manufacturing / Production | /dashboard/production?tab=execution | `work-orders` | `/dashboard/production-execution/work-orders` | redirect_stub → /dashboard/production?tab=execution | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `assignment` | `/dashboard/machine-ops/assignment` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `certs` | `/dashboard/machine-ops/certs` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `costing` | `/dashboard/machine-ops/costing` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `downtime` | `/dashboard/machine-ops/downtime` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `machines` | `/dashboard/machine-ops/machines` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `operators` | `/dashboard/machine-ops/operators` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `performance` | `/dashboard/machine-ops/performance` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `runtime` | `/dashboard/machine-ops/runtime` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=machine-ops | `teams` | `/dashboard/machine-ops/teams` | redirect_stub → /dashboard/production?tab=machine-ops | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `bulk-transfer` | `/dashboard/material-flow/bulk-transfer` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `fg-receipt` | `/dashboard/material-flow/fg-receipt` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `history` | `/dashboard/material-flow/history` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `issue` | `/dashboard/material-flow/issue` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `reconciliation` | `/dashboard/material-flow/reconciliation` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `reservations` | `/dashboard/material-flow/reservations` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `returns` | `/dashboard/material-flow/returns` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `tanks` | `/dashboard/material-flow/tanks` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Manufacturing / Production | /dashboard/production?tab=material-flow | `wip-transfer` | `/dashboard/material-flow/wip-transfer` | redirect_stub → /dashboard/production?tab=material-flow | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Finance

**Broken count:** 54

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Finance | /dashboard/finance?tab=accounting | `controls` | `/dashboard/finance/accounting/controls` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=accounting | `customers-ledger` | `/dashboard/finance/accounting/customers-ledger` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=accounting | `payments` | `/dashboard/finance/accounting/payments` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=accounting | `purchase-invoices` | `/dashboard/finance/accounting/purchase-invoices` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=accounting | `sales-invoices` | `/dashboard/finance/accounting/sales-invoices` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=accounting | `suppliers-ledger` | `/dashboard/finance/accounting/suppliers-ledger` | redirect_stub → /dashboard/finance?tab=accounting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `ai` | `/dashboard/bank-reconciliation/ai` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `balance` | `/dashboard/bank-reconciliation/balance` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `import` | `/dashboard/bank-reconciliation/import` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `open-items` | `/dashboard/bank-reconciliation/open-items` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `rules` | `/dashboard/bank-reconciliation/rules` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=bank-recon | `statements` | `/dashboard/bank-reconciliation/statements` | redirect_stub → /dashboard/finance?tab=bank-recon | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=invoice-match | `ai` | `/dashboard/invoice-match/ai` | redirect_stub → /dashboard/finance?tab=invoice-match | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=invoice-match | `blocked` | `/dashboard/invoice-match/blocked` | redirect_stub → /dashboard/finance?tab=invoice-match | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=invoice-match | `duplicates` | `/dashboard/invoice-match/duplicates` | redirect_stub → /dashboard/finance?tab=invoice-match | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=invoice-match | `matches` | `/dashboard/invoice-match/matches` | redirect_stub → /dashboard/finance?tab=invoice-match | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=invoice-match | `review-queue` | `/dashboard/invoice-match/review-queue` | redirect_stub → /dashboard/finance?tab=invoice-match | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `ai` | `/dashboard/fixed-assets/ai` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `new` | `/dashboard/fixed-assets/assets/new` | redirect_stub → /dashboard/finance?tab=fixed-assets&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `assets` | `/dashboard/fixed-assets/assets` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `categories` | `/dashboard/fixed-assets/categories` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `depreciation` | `/dashboard/fixed-assets/depreciation` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `disposal` | `/dashboard/fixed-assets/disposal` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `import` | `/dashboard/fixed-assets/import` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `posting` | `/dashboard/fixed-assets/posting` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=fixed-assets | `transfer` | `/dashboard/fixed-assets/transfer` | redirect_stub → /dashboard/finance?tab=fixed-assets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `ai` | `/dashboard/dimensions/ai` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `allocation-run` | `/dashboard/dimensions/allocation-run` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `allocations` | `/dashboard/dimensions/allocations` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `completeness` | `/dashboard/dimensions/completeness` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `cost-centers` | `/dashboard/dimensions/cost-centers` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `defaults` | `/dashboard/dimensions/defaults` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `reclassify` | `/dashboard/dimensions/reclassify` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `types` | `/dashboard/dimensions/types` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `validation` | `/dashboard/dimensions/validation` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dimensions | `values` | `/dashboard/dimensions/values` | redirect_stub → /dashboard/finance?tab=dimensions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dunning | `aging` | `/dashboard/dunning/aging` | redirect_stub → /dashboard/finance?tab=dunning | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dunning | `cases` | `/dashboard/dunning/cases` | redirect_stub → /dashboard/finance?tab=dunning | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dunning | `credit-holds` | `/dashboard/dunning/credit-holds` | redirect_stub → /dashboard/finance?tab=dunning | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dunning | `policies` | `/dashboard/dunning/policies` | redirect_stub → /dashboard/finance?tab=dunning | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=dunning | `workqueue` | `/dashboard/dunning/workqueue` | redirect_stub → /dashboard/finance?tab=dunning | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=tax | `regulatory` | `/dashboard/tax/regulatory` | redirect_stub → /dashboard/finance?tab=tax | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=tax | `reports` | `/dashboard/tax/reports` | redirect_stub → /dashboard/finance?tab=tax | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=tax | `rules` | `/dashboard/tax/rules` | redirect_stub → /dashboard/finance?tab=tax | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=tax | `transactions` | `/dashboard/tax/transactions` | redirect_stub → /dashboard/finance?tab=tax | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `advances` | `/dashboard/expenses/advances` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `ai` | `/dashboard/expenses/ai` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `approval` | `/dashboard/expenses/approval` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `categories` | `/dashboard/expenses/categories` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `new` | `/dashboard/expenses/claims/new` | redirect_stub → /dashboard/hr?tab=expenses&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `claims` | `/dashboard/expenses/claims` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `policies` | `/dashboard/expenses/policies` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `reimbursement` | `/dashboard/expenses/reimbursement` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Finance | /dashboard/finance?tab=expenses | `reports` | `/dashboard/expenses/reports` | redirect_stub → /dashboard/hr?tab=expenses | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### HR & Payroll

**Broken count:** 41

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| HR & Payroll | /dashboard/hr?tab=recruitment | `ai` | `/dashboard/recruitment/ai` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `candidates` | `/dashboard/recruitment/candidates` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `interviews` | `/dashboard/recruitment/interviews` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `offers` | `/dashboard/recruitment/offers` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `pipeline` | `/dashboard/recruitment/pipeline` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `reports` | `/dashboard/recruitment/reports` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `new` | `/dashboard/recruitment/requisitions/new` | redirect_stub → /dashboard/hr?tab=recruitment&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `requisitions` | `/dashboard/recruitment/requisitions` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=recruitment | `stages` | `/dashboard/recruitment/stages` | redirect_stub → /dashboard/hr?tab=recruitment | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `admin` | `/dashboard/ess/admin` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `ai` | `/dashboard/ess/ai` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `attendance` | `/dashboard/ess/attendance` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `documents` | `/dashboard/ess/documents` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `leave` | `/dashboard/ess/leave` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `notifications` | `/dashboard/ess/notifications` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `profile` | `/dashboard/ess/profile` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=ess | `requests` | `/dashboard/ess/requests` | redirect_stub → /dashboard/hr?tab=ess | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `ai` | `/dashboard/appraisals/ai` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `development-plans` | `/dashboard/appraisals/development-plans` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `hr-review` | `/dashboard/appraisals/hr-review` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `manager-queue` | `/dashboard/appraisals/manager-queue` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `periods` | `/dashboard/appraisals/periods` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `new` | `/dashboard/appraisals/records/new` | redirect_stub → /dashboard/hr?tab=appraisals&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `records` | `/dashboard/appraisals/records` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `reports` | `/dashboard/appraisals/reports` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `self-review` | `/dashboard/appraisals/self-review` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=appraisals | `templates` | `/dashboard/appraisals/templates` | redirect_stub → /dashboard/hr?tab=appraisals | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `ai` | `/dashboard/training/ai` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `assignments` | `/dashboard/training/assignments` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `certifications` | `/dashboard/training/certifications` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `feedback` | `/dashboard/training/feedback` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `programs` | `/dashboard/training/programs` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `reports` | `/dashboard/training/reports` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `sessions` | `/dashboard/training/sessions` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=training | `skill-matrix` | `/dashboard/training/skill-matrix` | redirect_stub → /dashboard/hr?tab=training | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `ai` | `/dashboard/timesheets/ai` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `approval-queue` | `/dashboard/timesheets/approval-queue` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `my-timesheets` | `/dashboard/timesheets/my-timesheets` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `reports` | `/dashboard/timesheets/reports` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `time-entry` | `/dashboard/timesheets/time-entry` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| HR & Payroll | /dashboard/hr?tab=timesheets | `weekly-view` | `/dashboard/timesheets/weekly-view` | redirect_stub → /dashboard/hr?tab=timesheets | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / Sales

**Broken count:** 30

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Commercial / Sales | /dashboard/sales?tab=price-lists | `approval-queue` | `/dashboard/price-lists/approval-queue` | redirect_stub → /dashboard/sales?tab=price-lists | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=contracts | `ai` | `/dashboard/contracts/ai` | redirect_stub → /dashboard/sales?tab=contracts | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=contracts | `expiring` | `/dashboard/contracts/expiring` | redirect_stub → /dashboard/sales?tab=contracts | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=contracts | `list` | `/dashboard/contracts/list` | redirect_stub → /dashboard/sales?tab=contracts | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=contracts | `new` | `/dashboard/contracts/new` | redirect_stub → /dashboard/sales?tab=contracts&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=recurring | `ai` | `/dashboard/recurring-orders/ai` | redirect_stub → /dashboard/sales?tab=recurring | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=recurring | `reports` | `/dashboard/recurring-orders/reports` | redirect_stub → /dashboard/sales?tab=recurring | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=recurring | `new` | `/dashboard/recurring-orders/templates/new` | redirect_stub → /dashboard/sales?tab=recurring&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=recurring | `templates` | `/dashboard/recurring-orders/templates` | redirect_stub → /dashboard/sales?tab=recurring | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=commissions | `ai` | `/dashboard/commissions/ai` | redirect_stub → /dashboard/sales?tab=commissions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=commissions | `payouts` | `/dashboard/commissions/payouts` | redirect_stub → /dashboard/sales?tab=commissions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=commissions | `rules` | `/dashboard/commissions/rules` | redirect_stub → /dashboard/sales?tab=commissions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=commissions | `transactions` | `/dashboard/commissions/transactions` | redirect_stub → /dashboard/sales?tab=commissions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=secondary | `analysis` | `/dashboard/secondary-sales/analysis` | redirect_stub → /dashboard/sales?tab=secondary | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=secondary | `inventory` | `/dashboard/secondary-sales/inventory` | redirect_stub → /dashboard/sales?tab=secondary | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=secondary | `upload` | `/dashboard/secondary-sales/upload` | redirect_stub → /dashboard/sales?tab=secondary | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `ai` | `/dashboard/van-sales/ai` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `pos` | `/dashboard/van-sales/pos` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `reconciliation` | `/dashboard/van-sales/reconciliation` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `route` | `/dashboard/van-sales/route` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `stock` | `/dashboard/van-sales/stock` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `new` | `/dashboard/van-sales/vans/new` | redirect_stub → /dashboard/sales?tab=van-sales&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=van-sales | `vans` | `/dashboard/van-sales/vans` | redirect_stub → /dashboard/sales?tab=van-sales | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `accounts` | `/dashboard/portal/accounts` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `activity` | `/dashboard/portal/activity` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `ai` | `/dashboard/portal/ai` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `claims` | `/dashboard/portal/claims` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `drafts` | `/dashboard/portal/drafts` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `reports` | `/dashboard/portal/reports` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Sales | /dashboard/sales?tab=portal | `users` | `/dashboard/portal/users` | redirect_stub → /dashboard/sales?tab=portal | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Supply Chain / Procurement

**Broken count:** 12

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Supply Chain / Procurement | /dashboard/procurement?tab=suggestions | `ai` | `/dashboard/procurement-suggestion/ai` | redirect_stub → /dashboard/procurement?tab=suggestions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=suggestions | `groups` | `/dashboard/procurement-suggestion/groups` | redirect_stub → /dashboard/procurement?tab=suggestions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=suggestions | `suggestions` | `/dashboard/procurement-suggestion/suggestions` | redirect_stub → /dashboard/procurement?tab=suggestions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=suggestions | `supplier-prices` | `/dashboard/procurement-suggestion/supplier-prices` | redirect_stub → /dashboard/procurement?tab=suggestions | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=subcontracting | `ai` | `/dashboard/subcontracting/ai` | redirect_stub → /dashboard/procurement?tab=subcontracting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=subcontracting | `locations` | `/dashboard/subcontracting/locations` | redirect_stub → /dashboard/procurement?tab=subcontracting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=subcontracting | `orders` | `/dashboard/subcontracting/orders` | redirect_stub → /dashboard/procurement?tab=subcontracting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=subcontracting | `stock` | `/dashboard/subcontracting/stock` | redirect_stub → /dashboard/procurement?tab=subcontracting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=subcontracting | `yield` | `/dashboard/subcontracting/yield` | redirect_stub → /dashboard/procurement?tab=subcontracting | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=landed-cost | `ai` | `/dashboard/landed-cost/ai` | redirect_stub → /dashboard/procurement?tab=landed-cost | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=landed-cost | `documents` | `/dashboard/landed-cost/documents` | redirect_stub → /dashboard/procurement?tab=landed-cost | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Supply Chain / Procurement | /dashboard/procurement?tab=landed-cost | `new` | `/dashboard/landed-cost/new` | redirect_stub → /dashboard/procurement?tab=landed-cost&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Factory Operations / Quality

**Broken count:** 13

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Factory Operations / Quality | /dashboard/quality?tab=qms | `ai` | `/dashboard/qms/ai` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `allergen` | `/dashboard/qms/allergen` | redirect_stub → /dashboard/quality?tab=allergen | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `ccp` | `/dashboard/qms/ccp` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `corrective-actions` | `/dashboard/qms/corrective-actions` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `deviations` | `/dashboard/qms/deviations` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `haccp` | `/dashboard/qms/haccp` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `inspections` | `/dashboard/qms/inspections` | redirect_stub → /dashboard/quality?tab=inspections | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `quarantine` | `/dashboard/qms/quarantine` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `reports` | `/dashboard/qms/reports` | redirect_stub → /dashboard/quality?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=qms | `templates` | `/dashboard/qms/templates` | redirect_stub → /dashboard/quality?tab=qms | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=allergen | `change-logs` | `/dashboard/allergen/change-logs` | redirect_stub → /dashboard/quality?tab=allergen | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=allergen | `material-profiles` | `/dashboard/allergen/material-profiles` | redirect_stub → /dashboard/quality?tab=allergen | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Quality | /dashboard/quality?tab=allergen | `product-allergens` | `/dashboard/allergen/product-allergens` | redirect_stub → /dashboard/quality?tab=allergen | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Logistics

**Broken count:** 7

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Logistics | /dashboard/logistics?tab=fleet | `drivers` | `/dashboard/fleet/drivers` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `fuel` | `/dashboard/fleet/fuel` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `incidents` | `/dashboard/fleet/incidents` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `maintenance` | `/dashboard/fleet/maintenance` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `reports` | `/dashboard/fleet/reports` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `trips` | `/dashboard/fleet/trips` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Logistics | /dashboard/logistics?tab=fleet | `vehicles` | `/dashboard/fleet/vehicles` | redirect_stub → /dashboard/logistics?tab=fleet | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Documents & Communication

**Broken count:** 17

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Documents & Communication | /dashboard/communication?tab=chatter | `ai` | `/dashboard/chatter/ai` | redirect_stub → /dashboard/communication?tab=chatter | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=chatter | `feed` | `/dashboard/chatter/feed` | redirect_stub → /dashboard/communication?tab=chatter | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=chatter | `reports` | `/dashboard/chatter/reports` | redirect_stub → /dashboard/communication?tab=chatter | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=chatter | `search` | `/dashboard/chatter/search` | redirect_stub → /dashboard/communication?tab=chatter | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=calendar | `availability` | `/dashboard/calendar/availability` | redirect_stub → /dashboard/communication?tab=calendar | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=calendar | `new-event` | `/dashboard/calendar/new-event` | redirect_stub → /dashboard/communication?tab=calendar | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=calendar | `resources` | `/dashboard/calendar/resources` | redirect_stub → /dashboard/communication?tab=calendar | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=calendar | `view` | `/dashboard/calendar/view` | redirect_stub → /dashboard/communication?tab=calendar | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `ai` | `/dashboard/notification-center/ai` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `list` | `/dashboard/notification-center/list` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `preferences` | `/dashboard/notification-center/preferences` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `reports` | `/dashboard/notification-center/reports` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `schedules` | `/dashboard/notification-center/schedules` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/communication?tab=notifications | `templates` | `/dashboard/notification-center/templates` | redirect_stub → /dashboard/communication?tab=notifications | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents?tab=compliance | `new` | `/dashboard/documents/new` | redirect_stub → /dashboard/documents?drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents?tab=knowledge-base | `new` | `/dashboard/knowledge-base/articles/new` | redirect_stub → /dashboard/documents?tab=knowledge-base&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Documents & Communication | /dashboard/documents?tab=knowledge-base | `articles` | `/dashboard/knowledge-base/articles` | redirect_stub → /dashboard/documents?tab=knowledge-base | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Intelligence / Analytics

**Broken count:** 14

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `finance` | `/dashboard/reports/finance` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `inventory` | `/dashboard/reports/inventory` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `marketing` | `/dashboard/reports/marketing` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `payments` | `/dashboard/reports/payments` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `procurement` | `/dashboard/reports/procurement` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `production` | `/dashboard/reports/production` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=reports | `sales` | `/dashboard/reports/sales` | redirect_stub → /dashboard/analytics?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `ai` | `/dashboard/report-builder/ai` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `builder` | `/dashboard/report-builder/builder` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `catalog` | `/dashboard/report-builder/catalog` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `dashboards` | `/dashboard/report-builder/dashboards` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `saved` | `/dashboard/report-builder/saved` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `schedules` | `/dashboard/report-builder/schedules` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Intelligence / Analytics | /dashboard/analytics?tab=report-builder | `viewer` | `/dashboard/report-builder/viewer` | redirect_stub → /dashboard/analytics?tab=report-builder | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Administration

**Broken count:** 8

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Administration | /dashboard/admin?tab=custom-fields | `ai` | `/dashboard/custom-fields/ai` | redirect_stub → /dashboard/admin?tab=custom-fields | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=custom-fields | `fields` | `/dashboard/custom-fields/fields` | redirect_stub → /dashboard/admin?tab=custom-fields | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=custom-fields | `form-builder` | `/dashboard/custom-fields/form-builder` | redirect_stub → /dashboard/admin?tab=custom-fields | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=custom-fields | `new-field` | `/dashboard/custom-fields/new-field` | redirect_stub → /dashboard/admin?tab=custom-fields&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=custom-fields | `values` | `/dashboard/custom-fields/values` | redirect_stub → /dashboard/admin?tab=custom-fields | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=custom-fields | `workflow-rules` | `/dashboard/custom-fields/workflow-rules` | redirect_stub → /dashboard/admin?tab=custom-fields | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=mobile | `approvals` | `/dashboard/mobile/approvals` | redirect_stub → /dashboard/admin?tab=mobile | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration | /dashboard/admin?tab=mobile | `devices` | `/dashboard/mobile/devices` | redirect_stub → /dashboard/admin?tab=mobile | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / Marketing

**Broken count:** 19

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Commercial / Marketing | /dashboard/marketing?tab=campaigns | `new` | `/dashboard/marketing/campaigns/new` | redirect_stub → /dashboard/marketing?tab=campaigns&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=promotions | `new` | `/dashboard/marketing/promotions/new` | redirect_stub → /dashboard/marketing?tab=promotions&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=trade-spend | `new` | `/dashboard/marketing/trade-spend/new` | redirect_stub → /dashboard/marketing?tab=trade-spend&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=ads | `new` | `/dashboard/marketing/ads/new` | redirect_stub → /dashboard/marketing?tab=ads&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=social-media | `new` | `/dashboard/marketing/social-media/new` | redirect_stub → /dashboard/marketing?tab=social-media&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=segments | `new` | `/dashboard/marketing/segments/new` | redirect_stub → /dashboard/marketing?tab=segments&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=influencers | `new` | `/dashboard/marketing/influencers/new` | redirect_stub → /dashboard/marketing?tab=influencers&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=visits | `new` | `/dashboard/marketing/visits/new` | redirect_stub → /dashboard/marketing?tab=visits&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=brand-spend | `new` | `/dashboard/marketing/brand-spend/new` | redirect_stub → /dashboard/marketing?tab=brand-spend&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `ai` | `/dashboard/tpm/ai` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `budget` | `/dashboard/tpm/budget` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `calendar` | `/dashboard/tpm/calendar` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `claims` | `/dashboard/tpm/claims` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `new` | `/dashboard/tpm/plans/new` | redirect_stub → /dashboard/marketing?tab=tpm&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `plans` | `/dashboard/tpm/plans` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `new` | `/dashboard/tpm/promotions/new` | redirect_stub → /dashboard/marketing?tab=tpm&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `promotions` | `/dashboard/tpm/promotions` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `roi` | `/dashboard/tpm/roi` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Commercial / Marketing | /dashboard/marketing?tab=tpm | `settlement` | `/dashboard/tpm/settlement` | redirect_stub → /dashboard/marketing?tab=tpm | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Commercial / CRM

**Broken count:** 1

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Commercial / CRM | /dashboard/crm?tab=surveys | `new` | `/dashboard/surveys/new` | redirect_stub → /dashboard/crm?tab=surveys&drawer=create | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Administration / Integrations

**Broken count:** 8

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `dead-letter` | `/dashboard/webhooks/dead-letter` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `definitions` | `/dashboard/webhooks/definitions` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `deliveries` | `/dashboard/webhooks/deliveries` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `inbound` | `/dashboard/webhooks/inbound` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `reports` | `/dashboard/webhooks/reports` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=webhooks | `subscriptions` | `/dashboard/webhooks/subscriptions` | redirect_stub → /dashboard/integrations?tab=webhooks | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=developer | `graphql` | `/dashboard/developer/graphql` | redirect_stub → /dashboard/integrations?tab=developer | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Administration / Integrations | /dashboard/integrations?tab=developer | `keys` | `/dashboard/developer/keys` | redirect_stub → /dashboard/integrations?tab=developer | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |


### Factory Operations / Utilities

**Broken count:** 22

| Module | Visible Location | Button/Card | Current Target | Current Behavior | Original Page Found? | Best Match | Confidence | Recommended Fix |
|--------|-----------------|-------------|----------------|------------------|---------------------|------------|------------|-----------------|
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `boiler` | `/dashboard/utility-management/kpi-center/boiler` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `chemicals` | `/dashboard/utility-management/kpi-center/chemicals` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `compressor` | `/dashboard/utility-management/kpi-center/compressor` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `electricity` | `/dashboard/utility-management/kpi-center/electricity` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `machine-utility` | `/dashboard/utility-management/kpi-center/machine-utility` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `soft-water` | `/dashboard/utility-management/kpi-center/soft-water` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `solar` | `/dashboard/utility-management/kpi-center/solar` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `utility-cost` | `/dashboard/utility-management/kpi-center/utility-cost` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `wastewater` | `/dashboard/utility-management/kpi-center/wastewater` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=kpi-center | `water` | `/dashboard/utility-management/kpi-center/water` | redirect_stub → /dashboard/utility-management?tab=kpi-center | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `anomalies` | `/dashboard/utility-management/reports/anomalies` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `cost-allocation` | `/dashboard/utility-management/reports/cost-allocation` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `daily-consumption` | `/dashboard/utility-management/reports/daily-consumption` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `equipment-efficiency` | `/dashboard/utility-management/reports/equipment-efficiency` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `load-analysis` | `/dashboard/utility-management/reports/load-analysis` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `sustainability` | `/dashboard/utility-management/reports/sustainability` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=reports | `treatment` | `/dashboard/utility-management/reports/treatment` | redirect_stub → /dashboard/utility-management?tab=reports | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=esg | `activities` | `/dashboard/esg/activities` | redirect_stub → /dashboard/utility-management?tab=esg | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=esg | `factors` | `/dashboard/esg/factors` | redirect_stub → /dashboard/utility-management?tab=esg | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=esg | `intelligence` | `/dashboard/esg/intelligence` | redirect_stub → /dashboard/utility-management?tab=esg | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=esg | `reports` | `/dashboard/esg/reports` | redirect_stub → /dashboard/utility-management?tab=esg | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |
| Factory Operations / Utilities | /dashboard/utility-management?tab=esg | `targets` | `/dashboard/esg/targets` | redirect_stub → /dashboard/utility-management?tab=esg | No | Unknown | low | CONVERT_TO_WORKSPACE_SUBVIEW |



---

## Dynamic Import Visibility Failures

These cases were MISSED by the previous audit because it treated middleware-redirected pages
as "invisible to users" without checking if they are dynamically imported into workspace tabs.

### /dashboard/cycle-count (5 broken cards)

- **Standalone route:** `/dashboard/cycle-count` → middleware redirects to `/dashboard/inventory?tab=cycle-count`
- **Also visible as:** Tab content in `/dashboard/inventory?tab=cycle-count`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/cycle-count/entries`, `/dashboard/cycle-count/plans`, `/dashboard/cycle-count/reports`, `/dashboard/cycle-count/tasks`, `/dashboard/cycle-count/variances`

### /dashboard/shelf-life (11 broken cards)

- **Standalone route:** `/dashboard/shelf-life` → middleware redirects to `/dashboard/inventory?tab=shelf-life`
- **Also visible as:** Tab content in `/dashboard/inventory?tab=shelf-life`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/shelf-life/bulk-hold-monitor`, `/dashboard/shelf-life/compliance`, `/dashboard/shelf-life/customer-rules`, `/dashboard/shelf-life/disposition`, `/dashboard/shelf-life/expired`, `/dashboard/shelf-life/fefo-config`, `/dashboard/shelf-life/lot-aging`, `/dashboard/shelf-life/near-expiry`, `/dashboard/shelf-life/production-validation`, `/dashboard/shelf-life/retest-queue`, `/dashboard/shelf-life/shipment-validation`

### /dashboard/traceability (7 broken cards)

- **Standalone route:** `/dashboard/traceability` → middleware redirects to `/dashboard/inventory?tab=traceability`
- **Also visible as:** Tab content in `/dashboard/inventory?tab=traceability`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/traceability/backward`, `/dashboard/traceability/forward`, `/dashboard/traceability/genealogy`, `/dashboard/traceability/mock-recall`, `/dashboard/traceability/recalls`, `/dashboard/traceability/regulatory`, `/dashboard/traceability/search`

### /dashboard/mrp (3 broken cards)

- **Standalone route:** `/dashboard/mrp` → middleware redirects to `/dashboard/planning?tab=mrp`
- **Also visible as:** Tab content in `/dashboard/planning?tab=mrp`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/mrp/forecast`, `/dashboard/mrp/run`, `/dashboard/mrp/suggestions`

### /dashboard/kanban (5 broken cards)

- **Standalone route:** `/dashboard/kanban` → middleware redirects to `/dashboard/planning?tab=kanban`
- **Also visible as:** Tab content in `/dashboard/planning?tab=kanban`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/kanban/ai`, `/dashboard/kanban/boards`, `/dashboard/kanban/cards`, `/dashboard/kanban/reports`, `/dashboard/kanban/view`

### /dashboard/production-execution (1 broken cards)

- **Standalone route:** `/dashboard/production-execution` → middleware redirects to `/dashboard/production?tab=execution`
- **Also visible as:** Tab content in `/dashboard/production?tab=execution`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/production-execution/work-orders`

### /dashboard/machine-ops (9 broken cards)

- **Standalone route:** `/dashboard/machine-ops` → middleware redirects to `/dashboard/production?tab=machine-ops`
- **Also visible as:** Tab content in `/dashboard/production?tab=machine-ops`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/machine-ops/assignment`, `/dashboard/machine-ops/certs`, `/dashboard/machine-ops/costing`, `/dashboard/machine-ops/downtime`, `/dashboard/machine-ops/machines`, `/dashboard/machine-ops/operators`, `/dashboard/machine-ops/performance`, `/dashboard/machine-ops/runtime`, `/dashboard/machine-ops/teams`

### /dashboard/material-flow (9 broken cards)

- **Standalone route:** `/dashboard/material-flow` → middleware redirects to `/dashboard/production?tab=material-flow`
- **Also visible as:** Tab content in `/dashboard/production?tab=material-flow`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/material-flow/bulk-transfer`, `/dashboard/material-flow/fg-receipt`, `/dashboard/material-flow/history`, `/dashboard/material-flow/issue`, `/dashboard/material-flow/reconciliation`, `/dashboard/material-flow/reservations`, `/dashboard/material-flow/returns`, `/dashboard/material-flow/tanks`, `/dashboard/material-flow/wip-transfer`

### /dashboard/finance/accounting (6 broken cards)

- **Standalone route:** `/dashboard/finance/accounting` → middleware redirects to `/dashboard/finance?tab=accounting`
- **Also visible as:** Tab content in `/dashboard/finance?tab=accounting`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/finance/accounting/controls`, `/dashboard/finance/accounting/customers-ledger`, `/dashboard/finance/accounting/payments`, `/dashboard/finance/accounting/purchase-invoices`, `/dashboard/finance/accounting/sales-invoices`, `/dashboard/finance/accounting/suppliers-ledger`

### /dashboard/bank-reconciliation (6 broken cards)

- **Standalone route:** `/dashboard/bank-reconciliation` → middleware redirects to `/dashboard/finance?tab=bank-recon`
- **Also visible as:** Tab content in `/dashboard/finance?tab=bank-recon`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/bank-reconciliation/ai`, `/dashboard/bank-reconciliation/balance`, `/dashboard/bank-reconciliation/import`, `/dashboard/bank-reconciliation/open-items`, `/dashboard/bank-reconciliation/rules`, `/dashboard/bank-reconciliation/statements`

### /dashboard/invoice-match (5 broken cards)

- **Standalone route:** `/dashboard/invoice-match` → middleware redirects to `/dashboard/finance?tab=invoice-match`
- **Also visible as:** Tab content in `/dashboard/finance?tab=invoice-match`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/invoice-match/ai`, `/dashboard/invoice-match/blocked`, `/dashboard/invoice-match/duplicates`, `/dashboard/invoice-match/matches`, `/dashboard/invoice-match/review-queue`

### /dashboard/fixed-assets (9 broken cards)

- **Standalone route:** `/dashboard/fixed-assets` → middleware redirects to `/dashboard/finance?tab=fixed-assets`
- **Also visible as:** Tab content in `/dashboard/finance?tab=fixed-assets`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/fixed-assets/ai`, `/dashboard/fixed-assets/assets/new`, `/dashboard/fixed-assets/assets`, `/dashboard/fixed-assets/categories`, `/dashboard/fixed-assets/depreciation`, `/dashboard/fixed-assets/disposal`, `/dashboard/fixed-assets/import`, `/dashboard/fixed-assets/posting`, `/dashboard/fixed-assets/transfer`

### /dashboard/dimensions (10 broken cards)

- **Standalone route:** `/dashboard/dimensions` → middleware redirects to `/dashboard/finance?tab=dimensions`
- **Also visible as:** Tab content in `/dashboard/finance?tab=dimensions`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/dimensions/ai`, `/dashboard/dimensions/allocation-run`, `/dashboard/dimensions/allocations`, `/dashboard/dimensions/completeness`, `/dashboard/dimensions/cost-centers`, `/dashboard/dimensions/defaults`, `/dashboard/dimensions/reclassify`, `/dashboard/dimensions/types`, `/dashboard/dimensions/validation`, `/dashboard/dimensions/values`

### /dashboard/dunning (5 broken cards)

- **Standalone route:** `/dashboard/dunning` → middleware redirects to `/dashboard/finance?tab=dunning`
- **Also visible as:** Tab content in `/dashboard/finance?tab=dunning`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/dunning/aging`, `/dashboard/dunning/cases`, `/dashboard/dunning/credit-holds`, `/dashboard/dunning/policies`, `/dashboard/dunning/workqueue`

### /dashboard/tax (4 broken cards)

- **Standalone route:** `/dashboard/tax` → middleware redirects to `/dashboard/finance?tab=tax`
- **Also visible as:** Tab content in `/dashboard/finance?tab=tax`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/tax/regulatory`, `/dashboard/tax/reports`, `/dashboard/tax/rules`, `/dashboard/tax/transactions`

### /dashboard/expenses (9 broken cards)

- **Standalone route:** `/dashboard/expenses` → middleware redirects to `/dashboard/hr?tab=expenses`
- **Also visible as:** Tab content in `/dashboard/finance?tab=expenses`, `/dashboard/hr?tab=expenses`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/expenses/advances`, `/dashboard/expenses/ai`, `/dashboard/expenses/approval`, `/dashboard/expenses/categories`, `/dashboard/expenses/claims/new`, `/dashboard/expenses/claims`, `/dashboard/expenses/policies`, `/dashboard/expenses/reimbursement`, `/dashboard/expenses/reports`

### /dashboard/recruitment (9 broken cards)

- **Standalone route:** `/dashboard/recruitment` → middleware redirects to `/dashboard/hr?tab=recruitment`
- **Also visible as:** Tab content in `/dashboard/hr?tab=recruitment`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/recruitment/ai`, `/dashboard/recruitment/candidates`, `/dashboard/recruitment/interviews`, `/dashboard/recruitment/offers`, `/dashboard/recruitment/pipeline`, `/dashboard/recruitment/reports`, `/dashboard/recruitment/requisitions/new`, `/dashboard/recruitment/requisitions`, `/dashboard/recruitment/stages`

### /dashboard/ess (8 broken cards)

- **Standalone route:** `/dashboard/ess` → middleware redirects to `/dashboard/hr?tab=ess`
- **Also visible as:** Tab content in `/dashboard/hr?tab=ess`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/ess/admin`, `/dashboard/ess/ai`, `/dashboard/ess/attendance`, `/dashboard/ess/documents`, `/dashboard/ess/leave`, `/dashboard/ess/notifications`, `/dashboard/ess/profile`, `/dashboard/ess/requests`

### /dashboard/appraisals (10 broken cards)

- **Standalone route:** `/dashboard/appraisals` → middleware redirects to `/dashboard/hr?tab=appraisals`
- **Also visible as:** Tab content in `/dashboard/hr?tab=appraisals`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/appraisals/ai`, `/dashboard/appraisals/development-plans`, `/dashboard/appraisals/hr-review`, `/dashboard/appraisals/manager-queue`, `/dashboard/appraisals/periods`, `/dashboard/appraisals/records/new`, `/dashboard/appraisals/records`, `/dashboard/appraisals/reports`, `/dashboard/appraisals/self-review`, `/dashboard/appraisals/templates`

### /dashboard/training (8 broken cards)

- **Standalone route:** `/dashboard/training` → middleware redirects to `/dashboard/hr?tab=training`
- **Also visible as:** Tab content in `/dashboard/hr?tab=training`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/training/ai`, `/dashboard/training/assignments`, `/dashboard/training/certifications`, `/dashboard/training/feedback`, `/dashboard/training/programs`, `/dashboard/training/reports`, `/dashboard/training/sessions`, `/dashboard/training/skill-matrix`

### /dashboard/timesheets (6 broken cards)

- **Standalone route:** `/dashboard/timesheets` → middleware redirects to `/dashboard/hr?tab=timesheets`
- **Also visible as:** Tab content in `/dashboard/hr?tab=timesheets`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/timesheets/ai`, `/dashboard/timesheets/approval-queue`, `/dashboard/timesheets/my-timesheets`, `/dashboard/timesheets/reports`, `/dashboard/timesheets/time-entry`, `/dashboard/timesheets/weekly-view`

### /dashboard/price-lists (1 broken cards)

- **Standalone route:** `/dashboard/price-lists` → middleware redirects to `/dashboard/sales?tab=price-lists`
- **Also visible as:** Tab content in `/dashboard/sales?tab=price-lists`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/price-lists/approval-queue`

### /dashboard/contracts (4 broken cards)

- **Standalone route:** `/dashboard/contracts` → middleware redirects to `/dashboard/sales?tab=contracts`
- **Also visible as:** Tab content in `/dashboard/sales?tab=contracts`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/contracts/ai`, `/dashboard/contracts/expiring`, `/dashboard/contracts/list`, `/dashboard/contracts/new`

### /dashboard/recurring-orders (4 broken cards)

- **Standalone route:** `/dashboard/recurring-orders` → middleware redirects to `/dashboard/sales?tab=recurring`
- **Also visible as:** Tab content in `/dashboard/sales?tab=recurring`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/recurring-orders/ai`, `/dashboard/recurring-orders/reports`, `/dashboard/recurring-orders/templates/new`, `/dashboard/recurring-orders/templates`

### /dashboard/commissions (4 broken cards)

- **Standalone route:** `/dashboard/commissions` → middleware redirects to `/dashboard/sales?tab=commissions`
- **Also visible as:** Tab content in `/dashboard/sales?tab=commissions`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/commissions/ai`, `/dashboard/commissions/payouts`, `/dashboard/commissions/rules`, `/dashboard/commissions/transactions`

### /dashboard/secondary-sales (3 broken cards)

- **Standalone route:** `/dashboard/secondary-sales` → middleware redirects to `/dashboard/sales?tab=secondary`
- **Also visible as:** Tab content in `/dashboard/sales?tab=secondary`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/secondary-sales/analysis`, `/dashboard/secondary-sales/inventory`, `/dashboard/secondary-sales/upload`

### /dashboard/van-sales (7 broken cards)

- **Standalone route:** `/dashboard/van-sales` → middleware redirects to `/dashboard/sales?tab=van-sales`
- **Also visible as:** Tab content in `/dashboard/sales?tab=van-sales`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/van-sales/ai`, `/dashboard/van-sales/pos`, `/dashboard/van-sales/reconciliation`, `/dashboard/van-sales/route`, `/dashboard/van-sales/stock`, `/dashboard/van-sales/vans/new`, `/dashboard/van-sales/vans`

### /dashboard/portal (7 broken cards)

- **Standalone route:** `/dashboard/portal` → middleware redirects to `/dashboard/sales?tab=portal`
- **Also visible as:** Tab content in `/dashboard/sales?tab=portal`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/portal/accounts`, `/dashboard/portal/activity`, `/dashboard/portal/ai`, `/dashboard/portal/claims`, `/dashboard/portal/drafts`, `/dashboard/portal/reports`, `/dashboard/portal/users`

### /dashboard/procurement-suggestion (4 broken cards)

- **Standalone route:** `/dashboard/procurement-suggestion` → middleware redirects to `/dashboard/procurement?tab=suggestions`
- **Also visible as:** Tab content in `/dashboard/procurement?tab=suggestions`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/procurement-suggestion/ai`, `/dashboard/procurement-suggestion/groups`, `/dashboard/procurement-suggestion/suggestions`, `/dashboard/procurement-suggestion/supplier-prices`

### /dashboard/subcontracting (5 broken cards)

- **Standalone route:** `/dashboard/subcontracting` → middleware redirects to `/dashboard/procurement?tab=subcontracting`
- **Also visible as:** Tab content in `/dashboard/procurement?tab=subcontracting`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/subcontracting/ai`, `/dashboard/subcontracting/locations`, `/dashboard/subcontracting/orders`, `/dashboard/subcontracting/stock`, `/dashboard/subcontracting/yield`

### /dashboard/landed-cost (3 broken cards)

- **Standalone route:** `/dashboard/landed-cost` → middleware redirects to `/dashboard/procurement?tab=landed-cost`
- **Also visible as:** Tab content in `/dashboard/procurement?tab=landed-cost`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/landed-cost/ai`, `/dashboard/landed-cost/documents`, `/dashboard/landed-cost/new`

### /dashboard/qms (10 broken cards)

- **Standalone route:** `/dashboard/qms` → middleware redirects to `/dashboard/quality?tab=qms`
- **Also visible as:** Tab content in `/dashboard/quality?tab=qms`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/qms/ai`, `/dashboard/qms/allergen`, `/dashboard/qms/ccp`, `/dashboard/qms/corrective-actions`, `/dashboard/qms/deviations`, `/dashboard/qms/haccp`, `/dashboard/qms/inspections`, `/dashboard/qms/quarantine`, `/dashboard/qms/reports`, `/dashboard/qms/templates`

### /dashboard/allergen (3 broken cards)

- **Standalone route:** `/dashboard/allergen` → middleware redirects to `/dashboard/quality?tab=allergen`
- **Also visible as:** Tab content in `/dashboard/quality?tab=allergen`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/allergen/change-logs`, `/dashboard/allergen/material-profiles`, `/dashboard/allergen/product-allergens`

### /dashboard/fleet (7 broken cards)

- **Standalone route:** `/dashboard/fleet` → middleware redirects to `/dashboard/logistics?tab=fleet`
- **Also visible as:** Tab content in `/dashboard/logistics?tab=fleet`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/fleet/drivers`, `/dashboard/fleet/fuel`, `/dashboard/fleet/incidents`, `/dashboard/fleet/maintenance`, `/dashboard/fleet/reports`, `/dashboard/fleet/trips`, `/dashboard/fleet/vehicles`

### /dashboard/chatter (4 broken cards)

- **Standalone route:** `/dashboard/chatter` → middleware redirects to `/dashboard/communication?tab=chatter`
- **Also visible as:** Tab content in `/dashboard/communication?tab=chatter`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/chatter/ai`, `/dashboard/chatter/feed`, `/dashboard/chatter/reports`, `/dashboard/chatter/search`

### /dashboard/calendar (4 broken cards)

- **Standalone route:** `/dashboard/calendar` → middleware redirects to `/dashboard/communication?tab=calendar`
- **Also visible as:** Tab content in `/dashboard/communication?tab=calendar`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/calendar/availability`, `/dashboard/calendar/new-event`, `/dashboard/calendar/resources`, `/dashboard/calendar/view`

### /dashboard/notification-center (6 broken cards)

- **Standalone route:** `/dashboard/notification-center` → middleware redirects to `/dashboard/communication?tab=notifications`
- **Also visible as:** Tab content in `/dashboard/communication?tab=notifications`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/notification-center/ai`, `/dashboard/notification-center/list`, `/dashboard/notification-center/preferences`, `/dashboard/notification-center/reports`, `/dashboard/notification-center/schedules`, `/dashboard/notification-center/templates`

### /dashboard/reports (7 broken cards)

- **Standalone route:** `/dashboard/reports` → middleware redirects to `/dashboard/analytics?tab=reports`
- **Also visible as:** Tab content in `/dashboard/analytics?tab=reports`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/reports/finance`, `/dashboard/reports/inventory`, `/dashboard/reports/marketing`, `/dashboard/reports/payments`, `/dashboard/reports/procurement`, `/dashboard/reports/production`, `/dashboard/reports/sales`

### /dashboard/report-builder (7 broken cards)

- **Standalone route:** `/dashboard/report-builder` → middleware redirects to `/dashboard/analytics?tab=report-builder`
- **Also visible as:** Tab content in `/dashboard/analytics?tab=report-builder`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/report-builder/ai`, `/dashboard/report-builder/builder`, `/dashboard/report-builder/catalog`, `/dashboard/report-builder/dashboards`, `/dashboard/report-builder/saved`, `/dashboard/report-builder/schedules`, `/dashboard/report-builder/viewer`

### /dashboard/custom-fields (6 broken cards)

- **Standalone route:** `/dashboard/custom-fields` → middleware redirects to `/dashboard/admin?tab=custom-fields`
- **Also visible as:** Tab content in `/dashboard/admin?tab=custom-fields`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/custom-fields/ai`, `/dashboard/custom-fields/fields`, `/dashboard/custom-fields/form-builder`, `/dashboard/custom-fields/new-field`, `/dashboard/custom-fields/values`, `/dashboard/custom-fields/workflow-rules`

### /dashboard/mobile (2 broken cards)

- **Standalone route:** `/dashboard/mobile` → middleware redirects to `/dashboard/admin?tab=mobile`
- **Also visible as:** Tab content in `/dashboard/admin?tab=mobile`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/mobile/approvals`, `/dashboard/mobile/devices`

### /dashboard/marketing/campaigns (1 broken cards)

- **Standalone route:** `/dashboard/marketing/campaigns` → middleware redirects to `/dashboard/marketing?tab=campaigns`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=campaigns`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/campaigns/new`

### /dashboard/marketing/promotions (1 broken cards)

- **Standalone route:** `/dashboard/marketing/promotions` → middleware redirects to `/dashboard/marketing?tab=promotions`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=promotions`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/promotions/new`

### /dashboard/marketing/trade-spend (1 broken cards)

- **Standalone route:** `/dashboard/marketing/trade-spend` → middleware redirects to `/dashboard/marketing?tab=trade-spend`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=trade-spend`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/trade-spend/new`

### /dashboard/marketing/ads (1 broken cards)

- **Standalone route:** `/dashboard/marketing/ads` → middleware redirects to `/dashboard/marketing?tab=ads`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=ads`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/ads/new`

### /dashboard/marketing/social-media (1 broken cards)

- **Standalone route:** `/dashboard/marketing/social-media` → middleware redirects to `/dashboard/marketing?tab=social-media`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=social-media`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/social-media/new`

### /dashboard/marketing/segments (1 broken cards)

- **Standalone route:** `/dashboard/marketing/segments` → middleware redirects to `/dashboard/marketing?tab=segments`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=segments`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/segments/new`

### /dashboard/marketing/influencers (1 broken cards)

- **Standalone route:** `/dashboard/marketing/influencers` → middleware redirects to `/dashboard/marketing?tab=influencers`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=influencers`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/influencers/new`

### /dashboard/marketing/visits (1 broken cards)

- **Standalone route:** `/dashboard/marketing/visits` → middleware redirects to `/dashboard/marketing?tab=visits`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=visits`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/visits/new`

### /dashboard/marketing/brand-spend (1 broken cards)

- **Standalone route:** `/dashboard/marketing/brand-spend` → middleware redirects to `/dashboard/marketing?tab=brand-spend`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=brand-spend`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/marketing/brand-spend/new`

### /dashboard/tpm (10 broken cards)

- **Standalone route:** `/dashboard/tpm` → middleware redirects to `/dashboard/marketing?tab=tpm`
- **Also visible as:** Tab content in `/dashboard/marketing?tab=tpm`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/tpm/ai`, `/dashboard/tpm/budget`, `/dashboard/tpm/calendar`, `/dashboard/tpm/claims`, `/dashboard/tpm/plans/new`, `/dashboard/tpm/plans`, `/dashboard/tpm/promotions/new`, `/dashboard/tpm/promotions`, `/dashboard/tpm/roi`, `/dashboard/tpm/settlement`

### /dashboard/surveys (1 broken cards)

- **Standalone route:** `/dashboard/surveys` → middleware redirects to `/dashboard/crm?tab=surveys`
- **Also visible as:** Tab content in `/dashboard/crm?tab=surveys`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/surveys/new`

### /dashboard/knowledge-base (2 broken cards)

- **Standalone route:** `/dashboard/knowledge-base` → middleware redirects to `/dashboard/documents?tab=knowledge-base`
- **Also visible as:** Tab content in `/dashboard/documents?tab=knowledge-base`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/knowledge-base/articles/new`, `/dashboard/knowledge-base/articles`

### /dashboard/webhooks (6 broken cards)

- **Standalone route:** `/dashboard/webhooks` → middleware redirects to `/dashboard/integrations?tab=webhooks`
- **Also visible as:** Tab content in `/dashboard/integrations?tab=webhooks`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/webhooks/dead-letter`, `/dashboard/webhooks/definitions`, `/dashboard/webhooks/deliveries`, `/dashboard/webhooks/inbound`, `/dashboard/webhooks/reports`, `/dashboard/webhooks/subscriptions`

### /dashboard/developer (2 broken cards)

- **Standalone route:** `/dashboard/developer` → middleware redirects to `/dashboard/integrations?tab=developer`
- **Also visible as:** Tab content in `/dashboard/integrations?tab=developer`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/developer/graphql`, `/dashboard/developer/keys`

### /dashboard/utility-management/kpi-center (10 broken cards)

- **Standalone route:** `/dashboard/utility-management/kpi-center` → middleware redirects to `/dashboard/utility-management?tab=kpi-center`
- **Also visible as:** Tab content in `/dashboard/utility-management?tab=kpi-center`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/utility-management/kpi-center/boiler`, `/dashboard/utility-management/kpi-center/chemicals`, `/dashboard/utility-management/kpi-center/compressor`, `/dashboard/utility-management/kpi-center/electricity`, `/dashboard/utility-management/kpi-center/machine-utility`, `/dashboard/utility-management/kpi-center/soft-water`, `/dashboard/utility-management/kpi-center/solar`, `/dashboard/utility-management/kpi-center/utility-cost`, `/dashboard/utility-management/kpi-center/wastewater`, `/dashboard/utility-management/kpi-center/water`

### /dashboard/utility-management/reports (7 broken cards)

- **Standalone route:** `/dashboard/utility-management/reports` → middleware redirects to `/dashboard/utility-management?tab=reports`
- **Also visible as:** Tab content in `/dashboard/utility-management?tab=reports`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/utility-management/reports/anomalies`, `/dashboard/utility-management/reports/cost-allocation`, `/dashboard/utility-management/reports/daily-consumption`, `/dashboard/utility-management/reports/equipment-efficiency`, `/dashboard/utility-management/reports/load-analysis`, `/dashboard/utility-management/reports/sustainability`, `/dashboard/utility-management/reports/treatment`

### /dashboard/esg (5 broken cards)

- **Standalone route:** `/dashboard/esg` → middleware redirects to `/dashboard/utility-management?tab=esg`
- **Also visible as:** Tab content in `/dashboard/utility-management?tab=esg`
- **Previous audit classified:** "safe_archived_standalone" — INCORRECT
- **Correct classification:** DYNAMICALLY_IMPORTED_VISIBLE with broken cards
- **Broken cards:** `/dashboard/esg/activities`, `/dashboard/esg/factors`, `/dashboard/esg/intelligence`, `/dashboard/esg/reports`, `/dashboard/esg/targets`


---

## Do Not Fix

This report is READ-ONLY. No code was modified.
Recommendations are provided for future fix passes only.
