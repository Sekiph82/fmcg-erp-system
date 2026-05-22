# Auto-Fix Continuation Guide

Date: 2026-05-22 (Wave 2A + 2B — Verified)

## Current State

**Latest commit:** c8be2fc — fix(ui): restore unresolved detail routes from git history
**Working tree:** CLEAN (verification commit pending)
**Type-check:** CLEAN | **Build:** CLEAN | **Backend tests:** 482/482 PASS

### Wave 2A + 2B Results (2026-05-22)

| Metric | Value |
|--------|-------|
| BVT before | 47 |
| BVT after | **3** |
| Routes restored | 37 [id] detail pages |
| Middleware entries removed | 31 parent prefixes |
| Href typo fixed | 1 (ai/compliance) |
| TS fixes | 9 |
| Build entity escapes | 4 |

**Wave 2C BLOCKED — pending user approval (3 items):**
- BVT-0001: `/dashboard/nps/surveys` — middleware redirect (nps → crm); Option A: fix href; Option B: build page
- BVT-0002: `/dashboard/knowledge-base/categories` — no page file; Option A: add tab; Option B: build page
- BVT-0003: `/dashboard/secondary-sales/[id]` — no [id] page; Option A: build page; Option B: drawer

**Verification report:** `docs/ERP_BUTTON_RECOVERY_WAVE2A_2B_VERIFICATION_REPORT.md`
**Implementation report:** `docs/ERP_BUTTON_RECOVERY_WAVE2A_2B_REPORT.md`

### What has been restored (all waves)

| Wave | Pages | Status |
|------|-------|--------|
| Wave 0 — MPS | 4 | ✅ done (prior session) |
| Wave 1A — Cycle Count | 5 | ✅ done |
| Wave 1A — Critical create/new/run | 26 | ✅ done |
| Wave 1B — High-conf operational | ~218 | ✅ done |
| Wave 1C — AI and reports | 54 | ✅ done (eecbba1) |
| Six broken action cards | 8 pages + 3 link fixes | ✅ done (this session) |

### Pages restored this session (6 broken action card fixes)

| Page | Route |
|------|-------|
| calendar/events | restored from `674b6c5` |
| marketing/crm | restored from `674b6c5` |
| marketing/crm/followup | restored from `674b6c5` |
| marketing/surveys | restored from `674b6c5` |
| marketing/surveys/new | restored from `674b6c5` |

### Source links updated (no restore needed)

| File | Old href | New href |
|------|----------|----------|
| finance/accounting/page.tsx | `/dashboard/finance/accounting/controls` | `/dashboard/finance?tab=accounting` |
| marketing/ecommerce/stores/page.tsx | `router.push("/dashboard/marketing/ecommerce/stores/new")` | `router.push("/dashboard/marketing?tab=ecommerce&drawer=create")` |
| recruitment/candidates/page.tsx | `/dashboard/recruitment/candidates/new` | `/dashboard/hr?tab=recruitment&drawer=create` |

### Broken visible targets

- **Before (Wave 1C complete):** 48 (critical: 0, high: 48, medium: 0)
- **After (broken action cards fixed):** 47 (critical: 0, high: 47, medium: 0)
- **Broken action cards:** 6 → 0

### Middleware bypass

312 entries in BYPASS_PREFIX_REDIRECT (was 307). All verified as valid real pages.

### Redirect map

Removed `/dashboard/marketing/crm` and `/dashboard/marketing/surveys` from:
- `frontend/src/middleware.ts`
- `frontend/src/lib/routeRedirectMap.ts`

---

## Key rules (carry forward)

- **BYPASS_PREFIX_REDIRECT check must come BEFORE exact REDIRECTS and prefix matching** in `matchRedirect()`.
- **API lib `.data` pattern:** `moApi.*`, `mfApi.*`, etc. already call `.then((r) => r.data)` — pages must NOT call `.then((r) => r.data)` again on the return value.
- **Recharts Formatter type:** wrap `(v: number) => ...` with `as never`.
- **Set/matchAll iteration:** use `Array.from()`, not spread `[...set]` (strict TS/target issue).
- **Unescaped JSX entities:** literal `"` → `&ldquo;&rdquo;`, literal `'` → `&apos;` in JSX text nodes.
- **Git commits for page recovery:** `674b6c5` (2026-05-01) = real page implementations. `bd6faf5` = replaced with stubs.
- **Do NOT restore pages blindly:** verify type-check passes after each batch.
- **routeRedirectMap.ts must stay in sync with middleware.ts** redirect map — both must be updated when adding/removing redirects.

---

## Next session tasks (in order)

1. **Wave 2A** — Restore 37 [id] detail pages from git history (see `docs/UNRESOLVED_47_IMPLEMENTATION_PLAN.md`)
   - 31 routes: remove parent from REDIRECTS + restore [id] page
   - 6 routes: restore [id] page only
2. **Wave 2B** — Fix href typo in `ai/compliance/page.tsx` (`production/quality` → `production/quality-control`)
3. **Wave 2C** — Requires user approval for 3 design decisions before implementing
4. **E2E regression** — expand smoke test to cover newly restored [id] routes
