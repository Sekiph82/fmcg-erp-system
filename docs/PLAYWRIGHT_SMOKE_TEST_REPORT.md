# Playwright Smoke Test Report

**Date:** 2026-05-17  
**Result:** ✅ 52/52 PASSED (exit 0)  
**Duration:** 4.9 minutes  
**Runner:** Local Windows host against Docker stack

---

## Environment

| Setting | Value |
|---------|-------|
| Frontend URL | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Auth | Admin login via real UI (admin / Admin1234!) |
| E2E_SKIP_WEBSERVER | 1 (Docker frontend used, not Playwright-spawned) |
| Docker frontend memory | 1G (cpus: 2.0) |
| Next.js mode | dev (`npm run dev`) |
| Playwright version | 1.59.x |
| Browser | Chromium (Desktop Chrome) |
| Retries | 2 |
| Test timeout | 60s |
| Setup project timeout | 300s (includes warmup) |

---

## Coverage

### A. Auth flow (3 tests)
- Login page loads and shows form
- Unauthenticated /dashboard redirects to /login
- Admin auth state active post-setup

### B. Dashboard root (1 test)
- /dashboard loads with content, no application error

### C. Main workspace pages (11 tests)
| Route | Status |
|-------|--------|
| /dashboard/sales | ✅ |
| /dashboard/inventory | ✅ |
| /dashboard/finance | ✅ |
| /dashboard/production | ✅ |
| /dashboard/hr | ✅ |
| /dashboard/quality | ✅ |
| /dashboard/marketing | ✅ |
| /dashboard/utility-management | ✅ |
| /dashboard/procurement | ✅ |
| /dashboard/documents | ✅ |
| /dashboard/admin | ✅ |

### D. Workspace tab navigation (18 tests)
| Route + Tab | Status |
|-------------|--------|
| /dashboard/sales?tab=orders | ✅ |
| /dashboard/sales?tab=invoices | ✅ |
| /dashboard/sales?tab=van-sales | ✅ |
| /dashboard/inventory?tab=stock | ✅ |
| /dashboard/inventory?tab=shelf-life | ✅ |
| /dashboard/inventory?tab=cycle-count | ✅ |
| /dashboard/finance?tab=accounting | ✅ |
| /dashboard/finance?tab=fixed-assets | ✅ |
| /dashboard/finance?tab=bank-recon | ✅ |
| /dashboard/production?tab=orders | ✅ |
| /dashboard/production?tab=execution | ✅ |
| /dashboard/production?tab=material-flow | ✅ |
| /dashboard/hr?tab=employees | ✅ |
| /dashboard/hr?tab=recruitment | ✅ |
| /dashboard/hr?tab=expenses | ✅ |
| /dashboard/quality?tab=qms | ✅ |
| /dashboard/quality?tab=allergen | ✅ |
| /dashboard/quality?tab=inspections | ✅ |

### E. Old static route redirects — middleware 308 (10 tests)
| From | Expected | Status |
|------|----------|--------|
| /dashboard/van-sales | /dashboard/sales | ✅ |
| /dashboard/qms | /dashboard/quality | ✅ |
| /dashboard/recruitment | /dashboard/hr | ✅ |
| /dashboard/fixed-assets | /dashboard/finance | ✅ |
| /dashboard/marketing/campaigns | /dashboard/marketing | ✅ |
| /dashboard/finance/accounting | /dashboard/finance | ✅ |
| /dashboard/production/orders | /dashboard/production | ✅ |
| /dashboard/shelf-life | /dashboard/inventory | ✅ |
| /dashboard/portal | /dashboard/sales | ✅ |
| /dashboard/bank-reconciliation | /dashboard/finance | ✅ |

### F. Dynamic [id] route redirects (6 tests)
| From | Pattern | Status |
|------|---------|--------|
| /dashboard/sales/orders/test-id | /\/dashboard\/sales/ | ✅ |
| /dashboard/procurement/orders/test-id | /\/dashboard\/procurement/ | ✅ |
| /dashboard/documents/test-id | /\/dashboard\/documents/ | ✅ |
| /dashboard/crm/records/test-id | /\/dashboard\/crm/ | ✅ |
| /dashboard/users/test-id | /\/dashboard\/admin/ | ✅ |
| /dashboard/payroll/runs/test-id | /\/dashboard\/hr.*tab=payroll/ | ✅ |

### G. Theme / layout sanity (2 tests)
- Sales workspace: h1 visible, body non-empty, no error overlay ✅
- Admin workspace: no error overlay ✅

---

## Fixes Applied (History)

| Fix | Reason |
|-----|--------|
| Import `playwright/test` not `@playwright/test` | Package is `playwright`, not `@playwright/test` |
| `waitUntil: "domcontentloaded"` (not networkidle) | SPA pages with API calls never reach networkidle |
| `retries: 2` globally | ERR_EMPTY_RESPONSE from dev server on first compilation |
| `timeout: 60_000` per test | Slow compilation under load exceeded 30s test timeout |
| Setup project `timeout: 300_000` | Warmup visits 30 routes; needs > 60s |
| Route warmup in auth.setup.ts | Pre-compiles all 30 workspace/tab routes before tests run |
| Docker frontend: 512M → 1G, cpus 1.0 → 2.0 | 512MB caused `ERR_EMPTY_RESPONSE` on heavy pages (production: 20 dynamic imports, utility-management) — core fix |
| Tab button timeout: 10s → 20s | `hasPermission` returns false during auth loading; tab buttons hidden until /me resolves |

---

## Artifacts

| Type | Location | Committed |
|------|----------|-----------|
| Test results | frontend/test-results/ | ❌ (gitignored) |
| Playwright report | frontend/playwright-report/ | ❌ (gitignored) |
| Auth state | frontend/playwright/.auth/ | ❌ (gitignored) |

---

## Remaining Manual Checks

- Section H (console error gating) is embedded in C/G tests via `collectConsoleErrors()` — no severe errors observed
- Headed/visual browser review not performed — tests are assertion-based only
- Mobile viewports not tested
- Firefox / WebKit not tested (Chromium only)
- Tests run against `next dev` not a production build — results may differ under production SSR

---

## Next Steps

None required. All 52 smoke tests pass. Playwright infrastructure is stable and committed.
