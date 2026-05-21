# ERP Button Recovery Stabilization Report

**Date:** 2026-05-21
**Commit:** 7de5623
**Branch:** main
**Working tree:** CLEAN (verified git status)

---

## Summary

| Item | Result |
|------|--------|
| Files changed in recovery commit | 252 |
| Cycle Count pages restored | 5 |
| Critical create/new/run pages restored | 26 |
| Wave 1B operational pages restored | ~218 |
| Frontend type-check | **CLEAN** |
| Frontend build | **CLEAN** |
| Backend tests | **478/482 pass** (4 pre-existing migration failures) |
| Audit scripts | **All pass / no drift** |
| Live browser check | Skipped — Docker not running |

---

## Counts

| Metric | Before Recovery | After Recovery |
|--------|----------------|----------------|
| Total visible action targets | 487 | 487 |
| **Broken visible targets** | **353** | **102** |
| Critical | 26 | **0** |
| High | ~272 | 48 |
| Medium | ~55 | 54 |
| Git matches available | — | 55 |
| High-conf git matches | — | 54 |
| Unresolved (no git match) | — | 47 |
| **Total fixed this wave** | — | **251** |

---

## Middleware Bypass Review

| Metric | Count |
|--------|-------|
| Total BYPASS_PREFIX_REDIRECT entries | 253 |
| MPS routes (pre-existing, Wave 0) | 4 |
| Cycle Count routes (Wave 1A) | 5 |
| Critical create/new routes (Wave 1A) | 26 |
| Operational routes (Wave 1B) | 218 |
| Missing page files | 0 |
| Redirect-only bypass entries | 0 |
| Suspicious/fake bypass entries | 0 |
| Restored routes missing from bypass | 0 |

**Bypass check position:** BEFORE exact REDIRECTS lookup and BEFORE prefix matching ✓
**Redirect HTTP status:** 302 (not 308) ✓
**/dashboard/mps base redirect:** intact ✓
**Parent workspace consolidation:** intact ✓
**No broad wildcard bypass:** confirmed ✓

---

## Restored Route Quality

| Metric | Count |
|--------|-------|
| Total bypass routes checked | 253 |
| Valid (export default + JSX return) | **253** |
| Missing page files | **0** |
| Redirect-only pages | **0** |
| Placeholder/no-UI pages | **0** |

All 253 bypassed routes have real page implementations with UI.
Report: `docs/RESTORED_ROUTE_QUALITY_REPORT.md`

---

## Audit Script Results

| Script | Result |
|--------|--------|
| `audit-visible-import-graph.js` | 102 broken, 0 critical, 48 high, 54 medium |
| `find-redirect-stubs.js` | 249 stubs (expected — these are the workspace consolidation stubs) |
| `check-route-redirects.js` | ✅ No redirect drift |
| `find-broken-action-cards.js` | Remaining broken cards documented |
| `audit-page-count.js` | 755 pages: 31 workspace, 250 redirect, 213 wrapper, 242 full-duplicate, 19 standalone |
| `check-workspace-tabs.js` | ✅ All workspace tab checks passed |
| `erp-health-audit.py` | 501 findings (1 HIGH — pre-existing) |
| `check-restored-routes-quality.js` | 253/253 valid ✓ |

---

## Type Errors Fixed (stabilization pass)

All errors were in Wave 1B restored pages:

| File | Error | Fix |
|------|-------|-----|
| `machine-ops/performance/page.tsx` | Double `.data` wrap on `listMachines` and `listPerformance` | Removed `.then((r) => r.data)` |
| `machine-ops/performance/page.tsx` | Recharts `Formatter` type incompatible | `as never` cast |
| 7 files | `react/no-unescaped-entities` (literal `"` and `'` in JSX text) | Escaped with `&ldquo;`/`&rdquo;`/`&apos;` |

---

## Risks

1. **Wave 1B was bulk-restored** from git history. Pages build and type-check clean, but have not been tested in a live browser. Should be smoke-tested before deploying to production.
2. **47 unresolved targets** remain — these have no matching implementation in git history. They need new pages or confirmed removal from navigation.
3. **48 high-severity targets** still broken — these have git history matches (54 high-conf) but Wave 1C restoration was deferred per instructions.
4. **4 backend test failures** are pre-existing migration chain issues, unrelated to this recovery.

---

## Next Recommended Step

**A — Current state is STABLE. Commit is already at 7de5623 on origin/main.**

Recommended next steps in priority order:

1. **Smoke-test in browser** when Docker is running: hit the 14 sample routes listed in the audit task, verify each shows real UI without redirect loop or 404.
2. **Wave 1C** (deferred): restore the remaining 54 high-confidence git-matched pages — but only after browser smoke test passes.
3. **Investigate 47 unresolved** targets — determine if they need new pages or if the navigation tiles should be updated to point to existing pages.
4. **Add E2E regression tests** in `frontend/e2e/action-card-health.spec.ts` for the Cycle Count + critical routes.
