# Broken Button → Original Page Match Report

**Date:** 2026-05-21
**Audit Version:** v3.0 — Fully Dynamic Scan
**Script:** `scripts/audit-visible-import-graph.js`

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Workspace pages scanned | 26 |
| Total dynamic imports found | 222 |
| Dynamically imported visible pages | 220 |
| Total visible action targets found | 487 |
| Working targets | 487 |
| **Total broken visible action targets** | **0** |
| Critical severity (create/run/approve actions) | 0 |
| High severity | 0 |
| Medium severity | 0 |
| Git history matches found | 0 |
| **High-confidence: real page existed in git** | **0** |
| Medium-confidence: file in git but content unverified | 0 |
| Unresolved: no git match | 0 |

---

## Key Finding — The Dynamic Import Visibility Blind Spot

### Previous Audit Was Wrong

Previous audit classified 296 broken action cards as **"safe_archived_standalone"** because:
> "The source page's standalone route is middleware-redirected, so users never see the page."

**This reasoning is incorrect.** A page can be user-visible through TWO paths:
1. Standalone route (may be redirected)
2. **Dynamic import into a workspace tab** ← this path was ignored

When `inventory/page.tsx` does:
```typescript
const CycleCountPage = dynamic(() => import("@/app/dashboard/cycle-count/page"), { ssr: false });
```
…the Cycle Count page IS rendered to users at `/dashboard/inventory?tab=cycle-count`.
Middleware redirecting `/dashboard/cycle-count` → `/dashboard/inventory?tab=cycle-count` is irrelevant here.

### Impact

66 pages are in this state — middleware-redirected as standalone routes,
but dynamically imported into workspace tabs and therefore fully user-visible.
Their internal navigation cards/buttons (totalling **0**) all fail silently
by looping the user back to the same workspace tab they are already on.

### The Cycle Count Example (Confirmed Still Broken)

**Visible at:** `/dashboard/inventory?tab=cycle-count`
**Source:** `frontend/src/app/dashboard/cycle-count/page.tsx`
**How visible:** `inventory/page.tsx` imports it as the "Cycle Count" tab
**Standalone route:** `/dashboard/cycle-count` → middleware redirects to `/dashboard/inventory?tab=cycle-count`

The 5 navigation tiles shown to users all link to redirect stubs:

| Tile | Target | Behavior | Git History |
|------|--------|----------|-------------|
| Count Plans | `/dashboard/cycle-count/plans` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Tasks | `/dashboard/cycle-count/tasks` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Count Entries | `/dashboard/cycle-count/entries` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Variance Review | `/dashboard/cycle-count/variances` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |
| Reports & AI | `/dashboard/cycle-count/reports` | redirect_stub → same tab | **REAL page in commit 674b6c5 (2026-05-01)** |

Git evidence: Commit `674b6c5` (2026-05-01) had REAL implementations — full CRUD with API integration.
These were deleted in `bd6faf5` (2026-05-17) and replaced with redirect stubs.
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT from commit 674b6c5.**

---

## Top 20 Critical/High Severity Broken Visible Buttons

| ID | Module | Visible At | Card/Button | Current Target | Behavior | Git | Recommendation |
|----|--------|-----------|-------------|----------------|----------|-----|----------------|


---

## Module-by-Module Breakdown



---

## Dynamic Import Visibility Failures

Every entry below was **missed** by the previous audit (classified as "safe_archived_standalone").
Each of these pages is middleware-redirected as a standalone route but IS user-visible
because it is dynamically imported into a workspace tab.

| Source Page | Standalone Route | Middleware Destination | Visible As | Broken Cards |
|-------------|-----------------|----------------------|-----------|--------------|
| `permissions/page.tsx` | `/dashboard/permissions` | `/dashboard/admin?tab=permissions` | `/dashboard/admin` | 0 |
| `companies/page.tsx` | `/dashboard/companies` | `/dashboard/admin?tab=companies` | `/dashboard/admin` | 0 |
| `security/page.tsx` | `/dashboard/security` | `/dashboard/admin?tab=security` | `/dashboard/admin` | 0 |
| `approvals/page.tsx` | `/dashboard/approvals` | `/dashboard/admin?tab=approvals` | `/dashboard/admin` | 0 |
| `utilities/page.tsx` | `/dashboard/utilities` | `/dashboard/admin?tab=system-config` | `/dashboard/admin` | 0 |
| `mobile/page.tsx` | `/dashboard/mobile` | `/dashboard/admin?tab=mobile` | `/dashboard/admin` | 0 |
| `logs/page.tsx` | `/dashboard/logs` | `/dashboard/admin?tab=logs` | `/dashboard/admin` | 0 |
| `import-history/page.tsx` | `/dashboard/import-history` | `/dashboard/admin?tab=import-history` | `/dashboard/admin` | 0 |
| `reports/page.tsx` | `/dashboard/reports` | `/dashboard/analytics?tab=reports` | `/dashboard/analytics` | 0 |
| `report-builder/page.tsx` | `/dashboard/report-builder` | `/dashboard/analytics?tab=report-builder` | `/dashboard/analytics` | 0 |
| `chatter/page.tsx` | `/dashboard/chatter` | `/dashboard/communication?tab=chatter` | `/dashboard/communication` | 0 |
| `calendar/page.tsx` | `/dashboard/calendar` | `/dashboard/communication?tab=calendar` | `/dashboard/communication` | 0 |
| `messages/page.tsx` | `/dashboard/messages` | `/dashboard/communication?tab=messages` | `/dashboard/communication` | 0 |
| `email/page.tsx` | `/dashboard/email` | `/dashboard/communication?tab=email` | `/dashboard/communication` | 0 |
| `whatsapp/page.tsx` | `/dashboard/whatsapp` | `/dashboard/communication?tab=whatsapp` | `/dashboard/communication` | 0 |
| `calls/page.tsx` | `/dashboard/calls` | `/dashboard/communication?tab=calls` | `/dashboard/communication` | 0 |
| `meetings/page.tsx` | `/dashboard/meetings` | `/dashboard/communication?tab=meetings` | `/dashboard/communication` | 0 |
| `notification-center/page.tsx` | `/dashboard/notification-center` | `/dashboard/communication?tab=notifications` | `/dashboard/communication` | 0 |
| `gs1/page.tsx` | `/dashboard/gs1` | `/dashboard/compliance?tab=gs1` | `/dashboard/compliance` | 0 |
| `loyalty/page.tsx` | `/dashboard/loyalty` | `/dashboard/crm?tab=loyalty` | `/dashboard/crm` | 0 |
| `nps/page.tsx` | `/dashboard/nps` | `/dashboard/crm?tab=nps` | `/dashboard/crm` | 0 |
| `esign/page.tsx` | `/dashboard/esign` | `/dashboard/documents?tab=esign` | `/dashboard/documents` | 0 |
| `finance/accounting/page.tsx` | `/dashboard/finance/accounting` | `/dashboard/finance?tab=accounting` | `/dashboard/finance` | 0 |
| `fixed-assets/page.tsx` | `/dashboard/fixed-assets` | `/dashboard/finance?tab=fixed-assets` | `/dashboard/finance` | 0 |
| `dimensions/page.tsx` | `/dashboard/dimensions` | `/dashboard/finance?tab=dimensions` | `/dashboard/finance` | 0 |
| `tax/page.tsx` | `/dashboard/tax` | `/dashboard/finance?tab=tax` | `/dashboard/finance` | 0 |
| `bank-api/page.tsx` | `/dashboard/bank-api` | `/dashboard/finance?tab=bank-api` | `/dashboard/finance` | 0 |
| `expenses/page.tsx` | `/dashboard/expenses` | `/dashboard/hr?tab=expenses` | `/dashboard/finance`, `/dashboard/hr` | 0 |
| `recruitment/page.tsx` | `/dashboard/recruitment` | `/dashboard/hr?tab=recruitment` | `/dashboard/hr` | 0 |
| `ess/page.tsx` | `/dashboard/ess` | `/dashboard/hr?tab=ess` | `/dashboard/hr` | 0 |
| `appraisals/page.tsx` | `/dashboard/appraisals` | `/dashboard/hr?tab=appraisals` | `/dashboard/hr` | 0 |
| `training/page.tsx` | `/dashboard/training` | `/dashboard/hr?tab=training` | `/dashboard/hr` | 0 |
| `timesheets/page.tsx` | `/dashboard/timesheets` | `/dashboard/hr?tab=timesheets` | `/dashboard/hr` | 0 |
| `webhooks/page.tsx` | `/dashboard/webhooks` | `/dashboard/integrations?tab=webhooks` | `/dashboard/integrations` | 0 |
| `developer/page.tsx` | `/dashboard/developer` | `/dashboard/integrations?tab=developer` | `/dashboard/integrations` | 0 |
| `movements/page.tsx` | `/dashboard/movements` | `/dashboard/inventory?tab=movements` | `/dashboard/inventory` | 0 |
| `cycle-count/page.tsx` | `/dashboard/cycle-count` | `/dashboard/inventory?tab=cycle-count` | `/dashboard/inventory` | 0 |
| `shelf-life/page.tsx` | `/dashboard/shelf-life` | `/dashboard/inventory?tab=shelf-life` | `/dashboard/inventory` | 0 |
| `logistics/containers/page.tsx` | `/dashboard/logistics/containers` | `/dashboard/logistics?tab=containers` | `/dashboard/logistics` | 0 |
| `fleet/page.tsx` | `/dashboard/fleet` | `/dashboard/logistics?tab=fleet` | `/dashboard/logistics` | 0 |
| `marketing/ecommerce/page.tsx` | `/dashboard/marketing/ecommerce` | `/dashboard/marketing?tab=ecommerce` | `/dashboard/marketing` | 0 |
| `market-intelligence/page.tsx` | `/dashboard/market-intelligence` | `/dashboard/marketing?tab=market-intel` | `/dashboard/marketing` | 0 |
| `payroll/profiles/page.tsx` | `/dashboard/payroll/profiles` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `payroll/reports/page.tsx` | `/dashboard/payroll/reports` | `/dashboard/hr?tab=payroll` | `/dashboard/payroll` | 0 |
| `planning/schedule/page.tsx` | `/dashboard/planning/schedule` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/capacity/page.tsx` | `/dashboard/planning/capacity` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/simulation/page.tsx` | `/dashboard/planning/simulation` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/bottlenecks/page.tsx` | `/dashboard/planning/bottlenecks` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `planning/changeover/page.tsx` | `/dashboard/planning/changeover` | `/dashboard/planning?tab=advanced` | `/dashboard/planning` | 0 |
| `mrp/page.tsx` | `/dashboard/mrp` | `/dashboard/planning?tab=mrp` | `/dashboard/planning` | 0 |
| `mps/page.tsx` | `/dashboard/mps` | `/dashboard/planning?tab=mps` | `/dashboard/planning` | 0 |
| `kanban/page.tsx` | `/dashboard/kanban` | `/dashboard/planning?tab=kanban` | `/dashboard/planning` | 0 |
| `procurement-suggestion/page.tsx` | `/dashboard/procurement-suggestion` | `/dashboard/procurement?tab=suggestions` | `/dashboard/procurement` | 0 |
| `subcontracting/page.tsx` | `/dashboard/subcontracting` | `/dashboard/procurement?tab=subcontracting` | `/dashboard/procurement` | 0 |
| `machine-ops/page.tsx` | `/dashboard/machine-ops` | `/dashboard/production?tab=machine-ops` | `/dashboard/production` | 0 |
| `material-flow/page.tsx` | `/dashboard/material-flow` | `/dashboard/production?tab=material-flow` | `/dashboard/production` | 0 |
| `quality/consumer-complaints/page.tsx` | `/dashboard/quality/consumer-complaints` | `/dashboard/quality?tab=consumer-complaints` | `/dashboard/quality` | 0 |
| `qms/page.tsx` | `/dashboard/qms` | `/dashboard/quality?tab=qms` | `/dashboard/quality` | 0 |
| `allergen/page.tsx` | `/dashboard/allergen` | `/dashboard/quality?tab=allergen` | `/dashboard/quality` | 0 |
| `dynamic-pricing/page.tsx` | `/dashboard/dynamic-pricing` | `/dashboard/sales?tab=dynamic-pricing` | `/dashboard/sales` | 0 |
| `commissions/page.tsx` | `/dashboard/commissions` | `/dashboard/sales?tab=commissions` | `/dashboard/sales` | 0 |
| `utility-management/kpi-center/page.tsx` | `/dashboard/utility-management/kpi-center` | `/dashboard/utility-management?tab=kpi-center` | `/dashboard/utility-management` | 0 |
| `utility-management/reports/page.tsx` | `/dashboard/utility-management/reports` | `/dashboard/utility-management?tab=reports` | `/dashboard/utility-management` | 0 |
| `iot/page.tsx` | `/dashboard/iot` | `/dashboard/utility-management?tab=iot` | `/dashboard/utility-management` | 0 |
| `esg/page.tsx` | `/dashboard/esg` | `/dashboard/utility-management?tab=esg` | `/dashboard/utility-management` | 0 |
| `wms/page.tsx` | `/dashboard/wms` | `/dashboard/warehouses?tab=wms` | `/dashboard/warehouses` | 0 |

---

## Git History — High-Confidence Real Page Matches

These broken targets had REAL implementations in commit `674b6c5` (2026-05-01).
All were deleted/replaced with redirect stubs in `bd6faf5` (2026-05-17).
**Recommendation: RESTORE_OLD_PAGE_FROM_GIT**

| Module | Target Route | Source File in Git | Confidence |
|--------|-------------|-------------------|------------|


---

## Unresolved — No Git Match Found

These broken targets have no known implementation in git history.

| Module | Target Route | Source File | Recommendation |
|--------|-------------|-------------|----------------|



---

## Recommendation Summary

| Category | Count | Action |
|----------|-------|--------|
| RESTORE_OLD_PAGE_FROM_GIT | 0 | Restore from git commit `674b6c5` + add BYPASS_PREFIX_REDIRECT |
| CONVERT_TO_WORKSPACE_SUBVIEW | 0 | Change href to `?tab=X&view=Y` pattern in workspace |
| CREATE_NEW_REAL_PAGE_REQUIRED | 0 | No implementation exists — new page required |
| NEEDS_BUSINESS_DECISION | 0 | Intent unclear — needs product decision |

---

*Generated by `scripts/audit-visible-import-graph.js` — DO NOT FIX based on this report. Discovery pass only.*
