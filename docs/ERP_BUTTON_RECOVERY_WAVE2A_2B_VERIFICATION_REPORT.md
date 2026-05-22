# ERP Button Recovery — Wave 2A + Wave 2B Verification Report

**Date:** 2026-05-22
**Commit verified:** c8be2fc — `fix(ui): restore unresolved detail routes from git history`
**Branch:** main
**Working tree:** CLEAN

---

## Summary

| Item | Result |
|------|--------|
| Latest commit | c8be2fc |
| type-check | ✅ CLEAN |
| build | ✅ CLEAN |
| Backend tests | ✅ 482/482 passed |
| find-broken-action-cards | ✅ 0 |
| restored-routes-quality | ✅ 312/312 valid |
| audit-visible-import-graph (BVT) | ✅ 3 (Wave 2C only) |
| workspace tabs | ✅ All passed |
| page count | ✅ 755 total |
| Live smoke test | ⏳ SKIPPED — Docker not running |
| BVT before Wave 2A/2B | 47 |
| BVT after Wave 2A/2B | **3** |
| Restored detail route count | 37 |
| Wave 2B typo fixed | Yes |

---

## Static Audit Results

| Audit | Result | Detail |
|-------|--------|--------|
| `find-broken-action-cards.js` | ✅ 0 broken | All action card hrefs resolve to real pages |
| `check-restored-routes-quality.js` | ✅ 312/312 valid | All bypass routes have real UI |
| `audit-visible-import-graph.js` | ✅ 3 BVT | Only Wave 2C items remain |
| `find-redirect-stubs.js` | ✅ 153 stubs | Stubs are non-nav pages (expected) |
| `audit-page-count.js` | ✅ 755 pages | Up from 698 static (37 new [id] pages) |
| `check-workspace-tabs.js` | ✅ All passed | No broken tab routes |
| `check-route-redirects.js` | ⚠ 15 "Missing middleware" warnings | EXPECTED — 31 parent prefixes intentionally removed from middleware.ts; sub-entries in routeRedirectMap still exist for paths that had sub-routes. Not a regression. |

### Route redirect drift note
`check-route-redirects.js` reports 15 "Missing middleware" paths (e.g., `/dashboard/custom-fields`, `/dashboard/surveys`, etc.). These are **intentional** — Wave 2A removed 31 parent entries from `middleware.ts` to stop prefix-match hijacking of `[id]` sub-routes. The sub-route entries that remain in `routeRedirectMap.ts` for non-existent paths are benign (they only redirect if the path is actually visited, and those paths 404 gracefully).

---

## Live Smoke Results

**Status: SKIPPED**

Docker daemon not running (`//./pipe/dockerDesktopLinuxEngine` not found). Playwright requires a live app.

**Smoke spec updated:** `frontend/e2e/restored-routes-smoke.spec.ts`
Added group **E. Wave 2A restored [id] detail routes** — 37 routes using sample ID `00000000-0000-0000-0000-000000000001`.

To run when Docker is available:
```bash
docker compose --env-file .env.development up -d
cd frontend
E2E_SKIP_WEBSERVER=1 npx playwright test e2e/restored-routes-smoke.spec.ts --project=chromium --reporter=list
```

| Metric | Count |
|--------|-------|
| Total [id] routes in spec | 37 |
| Passed | — (not run) |
| Failed | — (not run) |
| Skipped | 37 |

---

## Remaining Wave 2C

| BVT | Route | Issue | Options |
|-----|-------|-------|---------|
| BVT-0001 | `/dashboard/nps/surveys` | middleware redirect (nps → crm tab) | A: Change href to `/dashboard/crm?tab=NPSPage`; B: Build standalone page |
| BVT-0002 | `/dashboard/knowledge-base/categories` | no page file | A: Add categories tab to knowledge-base page; B: Build standalone page |
| BVT-0003 | `/dashboard/secondary-sales/${h.id}` | no [id]/page.tsx | A: Build detail page; B: Drawer component |

**Status: BLOCKED — awaiting design approval**

---

## Decision

**A. Wave 2A/2B verified — ready for Wave 2C (pending design approval)**

All static checks pass. Backend test count improved (482 vs prior 478). Live smoke skipped due to Docker unavailability — spec updated with 37 new [id] route tests. No regressions detected. Wave 2C may proceed once design decisions for the 3 remaining items are approved.
