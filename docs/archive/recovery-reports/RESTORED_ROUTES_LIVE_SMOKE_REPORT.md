# Restored Routes Live Smoke Report

**Date:** 2026-05-21
**Commit tested:** cdfde4e (stabilization) / 7de5623 (page restore)
**Test file:** `frontend/e2e/restored-routes-smoke.spec.ts`

---

## Summary

| Item | Result |
|------|--------|
| Docker status | **All 4 containers healthy** |
| Frontend | Up (healthy) — rebuilt with Wave 1A + 1B code |
| Backend | Healthy |
| DB | Healthy |
| Redis | Healthy |
| Total routes tested | **50** (+ 1 auth setup) |
| **Passed** | **50 / 50** |
| Failed | 0 |
| Skipped | 0 |
| Redirected (wrong URL) | 0 |
| 404 routes | 0 |
| Application error routes | 0 |
| Retries needed | 0 (all passed first attempt) |

---

## A. Cycle Count (5/5)

| Route | Result |
|-------|--------|
| `/dashboard/cycle-count/plans` | ✅ PASS |
| `/dashboard/cycle-count/tasks` | ✅ PASS |
| `/dashboard/cycle-count/entries` | ✅ PASS |
| `/dashboard/cycle-count/variances` | ✅ PASS |
| `/dashboard/cycle-count/reports` | ✅ PASS |

---

## B. Critical Create/New/Run Pages (17/17)

| Route | Result |
|-------|--------|
| `/dashboard/custom-fields/new-field` | ✅ PASS |
| `/dashboard/calendar/new-event` | ✅ PASS |
| `/dashboard/surveys/new` | ✅ PASS |
| `/dashboard/documents/new` | ✅ PASS |
| `/dashboard/knowledge-base/articles/new` | ✅ PASS |
| `/dashboard/fixed-assets/assets/new` | ✅ PASS |
| `/dashboard/expenses/claims/new` | ✅ PASS |
| `/dashboard/recruitment/requisitions/new` | ✅ PASS |
| `/dashboard/appraisals/records/new` | ✅ PASS |
| `/dashboard/marketing/campaigns/new` | ✅ PASS |
| `/dashboard/marketing/promotions/new` | ✅ PASS |
| `/dashboard/mrp/run` | ✅ PASS |
| `/dashboard/landed-cost/new` | ✅ PASS |
| `/dashboard/machine-ops/runtime` | ✅ PASS |
| `/dashboard/contracts/new` | ✅ PASS |
| `/dashboard/recurring-orders/templates/new` | ✅ PASS |
| `/dashboard/van-sales/vans/new` | ✅ PASS |

---

## C. Wave 1B Operational Sample (28/28)

| Route | Result |
|-------|--------|
| `/dashboard/bank-reconciliation/statements` | ✅ PASS |
| `/dashboard/bank-reconciliation/import` | ✅ PASS |
| `/dashboard/invoice-match/review-queue` | ✅ PASS |
| `/dashboard/fixed-assets/assets` | ✅ PASS |
| `/dashboard/dunning/aging` | ✅ PASS |
| `/dashboard/recruitment/pipeline` | ✅ PASS |
| `/dashboard/ess/profile` | ✅ PASS |
| `/dashboard/training/programs` | ✅ PASS |
| `/dashboard/timesheets/time-entry` | ✅ PASS |
| `/dashboard/webhooks/definitions` | ✅ PASS |
| `/dashboard/shelf-life/near-expiry` | ✅ PASS |
| `/dashboard/traceability/search` | ✅ PASS |
| `/dashboard/fleet/vehicles` | ✅ PASS |
| `/dashboard/tpm/plans` | ✅ PASS |
| `/dashboard/mrp/suggestions` | ✅ PASS |
| `/dashboard/kanban/cards` | ✅ PASS |
| `/dashboard/procurement-suggestion/suggestions` | ✅ PASS |
| `/dashboard/subcontracting/orders` | ✅ PASS |
| `/dashboard/machine-ops/machines` | ✅ PASS |
| `/dashboard/material-flow/issue` | ✅ PASS |
| `/dashboard/qms/inspections` | ✅ PASS |
| `/dashboard/allergen/material-profiles` | ✅ PASS |
| `/dashboard/contracts/list` | ✅ PASS |
| `/dashboard/commissions/rules` | ✅ PASS |
| `/dashboard/van-sales/route` | ✅ PASS |
| `/dashboard/portal/accounts` | ✅ PASS |
| `/dashboard/utility-management/kpi-center/electricity` | ✅ PASS |
| `/dashboard/esg/activities` | ✅ PASS |

---

## Failures

None.

---

## Notes on Test Design

- `procurement-suggestion/suggestions` requires `?run_id=` param to show full table — renders a valid "No run selected" empty state without that param. Page is correct, content check uses `<main>` inner text (not semantic heading requirement).
- Pages using lazy-loaded chunks need `networkidle` + 2s post-wait to complete hydration in production Docker build.

---

## Decision

**A — Ready for Wave 1C.**

All 50 tested routes pass live browser verification:
- Stay at correct URL (no redirect to parent workspace)
- Show real app shell (sidebar, nav)
- Render page-specific content in `<main>`
- No 404, no Application error
- No console crash

Wave 1C may proceed when approved.
