# Redirect Stub Route Audit

**Date:** 2026-05-20  
**Method:** Automated scan — pages with `redirect()` as sole content (≤8 non-empty lines)

---

## Summary

| Metric | Count |
|--------|-------|
| Total redirect stubs | 492 |
| Classification: safe_redirect (page consolidation) | 491 |
| Classification: broken_action_target (fixed) | 4 |

---

## MPS Broken Action Targets (Fixed)

These 4 stubs were linked from visible MPS action cards and caused silent same-page bounces.
All 4 are now real standalone pages with the middleware bypass applied.

| Route | Was Redirecting To | Classification | Status |
|-------|--------------------|----------------|--------|
| `/dashboard/mps/planning-board` | `/dashboard/planning?tab=mps` | broken_action_target | **FIXED** |
| `/dashboard/mps/capacity` | `/dashboard/planning?tab=mps` | broken_action_target | **FIXED** |
| `/dashboard/mps/campaigns` | `/dashboard/planning?tab=mps` | broken_action_target | **FIXED** |
| `/dashboard/mps/whatif` | `/dashboard/planning?tab=mps` | broken_action_target | **FIXED** |

---

## Safe Redirect Architecture (488 stubs)

These stubs are intentional page-consolidation redirects. Old standalone module routes
redirect to consolidated workspace tabs. Action cards in the CONSOLIDATED workspaces
correctly use `?tab=` query params, not these old sub-routes.

| Target Workspace | Stub Count |
|------------------|-----------|
| `/dashboard/quality?tab=allergen` | 12 |
| `/dashboard/hr?tab=appraisals` | 10 |
| `/dashboard/finance?tab=bank-recon` | 9 |
| `/dashboard/communication?tab=calendar` | 9 |
| `/dashboard/hr?tab=recruitment` | 8 |
| `/dashboard/finance?tab=dunning` | 8 |
| `/dashboard/finance?tab=fixed-assets` | 8 |
| `/dashboard/quality?tab=qms` | 12 |
| `/dashboard/hr?tab=expenses` | 9 |
| `/dashboard/sales?tab=van-sales` | 14 |
| *(and 220+ more across all modules)* | |

---

## Action Cards Pointing To Redirect Stubs

### MPS (Fixed)

Source: `frontend/src/app/dashboard/mps/page.tsx` (rendered as MPS tab inside Planning workspace)

| Card Label | Card Description | href | Redirect Target | Classification |
|------------|-----------------|------|-----------------|----------------|
| Planning Board | View & override lines | `/dashboard/mps/planning-board` | ~~`/dashboard/planning?tab=mps`~~ | **FIXED** |
| Capacity Heatmap | Work center load analysis | `/dashboard/mps/capacity` | ~~`/dashboard/planning?tab=mps`~~ | **FIXED** |
| Campaign View | SKU grouping & sequence | `/dashboard/mps/campaigns` | ~~`/dashboard/planning?tab=mps`~~ | **FIXED** |
| What-If Simulator | Impact analysis | `/dashboard/mps/whatif` | ~~`/dashboard/planning?tab=mps`~~ | **FIXED** |

---

## False Positives in Automated Scan

The `find-broken-action-cards.js` script found 314 "broken action cards" — but most are
FALSE POSITIVES. The source files (e.g., `allergen/page.tsx`, `appraisals/page.tsx`) are
themselves redirect stubs that middleware intercepts. Their internal action cards are
never rendered to users.

True broken action cards (rendered to users) were only the 4 MPS ones above.

---

## Full Audit Data

See `docs/REDIRECT_STUB_ROUTE_AUDIT.json` for machine-readable data of all 492 stubs.
