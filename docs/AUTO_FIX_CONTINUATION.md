# Auto-Fix Continuation Guide

Date: 2026-05-22 (ERP Button Recovery — Wave 1C complete + verified)

## Current State

**Latest commit:** `eecbba1` — fix(ui): restore Wave 1C — 54 AI and reports pages with TS/ESLint fixes
**Working tree:** CLEAN
**Type-check:** CLEAN | **Build:** CLEAN | **Backend tests:** 478/482 PASS

### What has been restored (all waves)

| Wave | Pages | Status |
|------|-------|--------|
| Wave 0 — MPS | 4 | ✅ done (prior session) |
| Wave 1A — Cycle Count | 5 | ✅ done |
| Wave 1A — Critical create/new/run | 26 | ✅ done |
| Wave 1B — High-conf operational | ~218 | ✅ done |
| Wave 1C — AI and reports | 54 | ✅ done (eecbba1) |

### Broken visible targets
- **Before:** 353
- **After Wave 1A+1B:** 102 (critical: 0, high: 48, medium: 54)
- **After Wave 1C:** 48 (critical: 0, high: 48, medium: 0)
- **Total fixed:** 305

### Middleware bypass
307 entries in BYPASS_PREFIX_REDIRECT. All 307 verified as valid real pages (UI present, not redirect-only, not missing).

### Stabilization fixes (this session)
- `machine-ops/performance/page.tsx`: double `.data` wrap removed + Recharts formatter `as never` cast
- 7 files: `react/no-unescaped-entities` (literal quotes in JSX text) escaped

---

## Key rules (carry forward)

- **BYPASS_PREFIX_REDIRECT check must come BEFORE exact REDIRECTS and prefix matching** in `matchRedirect()`.
- **API lib `.data` pattern:** `moApi.*`, `mfApi.*`, etc. already call `.then((r) => r.data)` — pages must NOT call `.then((r) => r.data)` again on the return value.
- **Recharts Formatter type:** wrap `(v: number) => ...` with `as never`.
- **Set/matchAll iteration:** use `Array.from()`, not spread `[...set]` (strict TS/target issue).
- **Unescaped JSX entities:** literal `"` → `&ldquo;&rdquo;`, literal `'` → `&apos;` in JSX text nodes.
- **Git commits for page recovery:** `674b6c5` (2026-05-01) = real page implementations. `bd6faf5` = replaced with stubs.
- **Do NOT restore pages blindly:** verify type-check passes after each batch.

---

## Wave 1C verification (2026-05-22)

- [x] Type-check: CLEAN
- [x] Build: CLEAN
- [x] Backend: 478/482 (4 pre-existing failures)
- [x] Static audits: all green (307/307 valid, route redirects OK, workspace tabs OK)
- [x] Live smoke: **104/104 PASSED** (1 flaky transient on `/dashboard/invoice-match/ai`, passed on retry 2)
- [x] Audit BYPASS set synced in `scripts/audit-visible-import-graph.js`
- [x] Wave 1C report: `docs/ERP_BUTTON_RECOVERY_WAVE1C_REPORT.md`

## Next session tasks (in order)

1. **Unresolved/no-git-match design pass** — 47 routes with no git history match
   - ~38 are dynamic detail routes (`/dashboard/users/${id}` etc.) → need subview/modal pattern
   - ~10 are new pages requiring design decisions
   - Requires user/stakeholder approval before implementation
2. **6 remaining broken-action-cards** — `find-broken-action-cards.js` shows 6 pages with action cards pointing to redirect stubs (calendar/events, finance/accounting/controls, marketing/ecommerce/stores/new, recruitment/candidates/new, reports/marketing CRM/surveys links)
3. **E2E regression** — expand smoke test to cover full 104 routes on every Docker build
