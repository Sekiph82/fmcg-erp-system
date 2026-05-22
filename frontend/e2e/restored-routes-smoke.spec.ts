/**
 * Live smoke test for all restored action target routes.
 * Verifies each route renders real UI and does NOT redirect to a parent workspace.
 *
 * Run against the Docker app:
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/restored-routes-smoke.spec.ts \
 *     --project=chromium --reporter=list
 */

import { test, expect } from "playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

// Helper: visit a route and assert it stayed there (no redirect to parent workspace).
// Allows ?tab= params (tab-routed pages are OK), blocks redirect to a *different* base path.
async function checkRoute(
  page: import("playwright/test").Page,
  route: string,
  label: string
) {
  const url = `${BASE_URL}${route}`;
  const resp = await page.goto(url, { waitUntil: "networkidle", timeout: 45_000 });
  await page.waitForTimeout(2_000);

  const finalUrl = page.url();

  // Must not redirect to /login
  expect(finalUrl, `[${label}] redirected to login`).not.toContain("/login");

  // Must not show 404
  const body = await page.content();
  expect(body, `[${label}] shows 404`).not.toMatch(/404.*not found|page not found/i);
  expect(body, `[${label}] shows Application error`).not.toMatch(/application error|an unexpected error/i);

  // Final URL must still contain the route path (not redirected to a parent workspace)
  const routeBase = route.split("?")[0];
  expect(finalUrl, `[${label}] redirected away from ${routeBase} — final: ${finalUrl}`).toContain(routeBase);

  // <main> must exist (DashboardShell rendered) and contain non-empty text
  const mainEl = page.locator("main");
  const mainExists = (await mainEl.count()) > 0;
  const mainText = mainExists ? (await mainEl.first().innerText()).trim() : "";
  expect(mainExists && mainText.length > 0, `[${label}] <main> missing or empty`).toBe(true);

  return { route, finalUrl, status: resp?.status() ?? 0 };
}

// ── A. Cycle Count (5 pages) ─────────────────────────────────────────────────

test.describe("A. Cycle Count restored pages", () => {
  const routes = [
    "/dashboard/cycle-count/plans",
    "/dashboard/cycle-count/tasks",
    "/dashboard/cycle-count/entries",
    "/dashboard/cycle-count/variances",
    "/dashboard/cycle-count/reports",
  ];

  for (const route of routes) {
    test(route, async ({ page }) => {
      await checkRoute(page, route, route);
    });
  }
});

// ── B. Critical create/new/run pages (17 tested) ────────────────────────────

test.describe("B. Critical create/new/run pages", () => {
  const routes = [
    "/dashboard/custom-fields/new-field",
    "/dashboard/calendar/new-event",
    "/dashboard/surveys/new",
    "/dashboard/documents/new",
    "/dashboard/knowledge-base/articles/new",
    "/dashboard/fixed-assets/assets/new",
    "/dashboard/expenses/claims/new",
    "/dashboard/recruitment/requisitions/new",
    "/dashboard/appraisals/records/new",
    "/dashboard/marketing/campaigns/new",
    "/dashboard/marketing/promotions/new",
    "/dashboard/mrp/run",
    "/dashboard/landed-cost/new",
    "/dashboard/machine-ops/runtime",
    "/dashboard/contracts/new",
    "/dashboard/recurring-orders/templates/new",
    "/dashboard/van-sales/vans/new",
  ];

  for (const route of routes) {
    test(route, async ({ page }) => {
      await checkRoute(page, route, route);
    });
  }
});

// ── C. Wave 1B operational sample (28 pages) ─────────────────────────────────

test.describe("C. Wave 1B operational sample", () => {
  const routes = [
    "/dashboard/bank-reconciliation/statements",
    "/dashboard/bank-reconciliation/import",
    "/dashboard/invoice-match/review-queue",
    "/dashboard/fixed-assets/assets",
    "/dashboard/dunning/aging",
    "/dashboard/recruitment/pipeline",
    "/dashboard/ess/profile",
    "/dashboard/training/programs",
    "/dashboard/timesheets/time-entry",
    "/dashboard/webhooks/definitions",
    "/dashboard/shelf-life/near-expiry",
    "/dashboard/traceability/search",
    "/dashboard/fleet/vehicles",
    "/dashboard/tpm/plans",
    "/dashboard/mrp/suggestions",
    "/dashboard/kanban/cards",
    "/dashboard/procurement-suggestion/suggestions",
    "/dashboard/subcontracting/orders",
    "/dashboard/machine-ops/machines",
    "/dashboard/material-flow/issue",
    "/dashboard/qms/inspections",
    "/dashboard/allergen/material-profiles",
    "/dashboard/contracts/list",
    "/dashboard/commissions/rules",
    "/dashboard/van-sales/route",
    "/dashboard/portal/accounts",
    "/dashboard/utility-management/kpi-center/electricity",
    "/dashboard/esg/activities",
  ];

  for (const route of routes) {
    test(route, async ({ page }) => {
      await checkRoute(page, route, route);
    });
  }
});

// ── D. Wave 1C AI and reports pages (54 pages) ───────────────────────────────

test.describe("D. Wave 1C AI and reports pages", () => {
  const routes = [
    // Cross-module reports
    "/dashboard/reports/inventory",
    "/dashboard/reports/production",
    "/dashboard/reports/procurement",
    "/dashboard/reports/sales",
    "/dashboard/reports/finance",
    "/dashboard/reports/payments",
    "/dashboard/reports/marketing",
    // AI utilities
    "/dashboard/custom-fields/ai",
    "/dashboard/report-builder/ai",
    // Communication
    "/dashboard/chatter/reports",
    "/dashboard/chatter/ai",
    "/dashboard/notification-center/reports",
    "/dashboard/notification-center/ai",
    // Finance AI
    "/dashboard/bank-reconciliation/ai",
    "/dashboard/invoice-match/ai",
    "/dashboard/fixed-assets/ai",
    "/dashboard/dimensions/ai",
    // Finance reports
    "/dashboard/tax/reports",
    "/dashboard/expenses/reports",
    "/dashboard/expenses/ai",
    // HR
    "/dashboard/recruitment/reports",
    "/dashboard/recruitment/ai",
    "/dashboard/ess/ai",
    "/dashboard/appraisals/reports",
    "/dashboard/appraisals/ai",
    "/dashboard/training/reports",
    "/dashboard/training/ai",
    "/dashboard/timesheets/reports",
    "/dashboard/timesheets/ai",
    // Operations
    "/dashboard/webhooks/reports",
    "/dashboard/fleet/reports",
    "/dashboard/tpm/ai",
    "/dashboard/kanban/reports",
    "/dashboard/kanban/ai",
    // Procurement
    "/dashboard/procurement-suggestion/ai",
    "/dashboard/subcontracting/ai",
    "/dashboard/landed-cost/ai",
    // Quality
    "/dashboard/qms/reports",
    "/dashboard/qms/ai",
    // Sales
    "/dashboard/contracts/ai",
    "/dashboard/recurring-orders/reports",
    "/dashboard/recurring-orders/ai",
    "/dashboard/commissions/ai",
    "/dashboard/van-sales/ai",
    "/dashboard/portal/ai",
    "/dashboard/portal/reports",
    // Utility reports
    "/dashboard/utility-management/reports/daily-consumption",
    "/dashboard/utility-management/reports/cost-allocation",
    "/dashboard/utility-management/reports/treatment",
    "/dashboard/utility-management/reports/equipment-efficiency",
    "/dashboard/utility-management/reports/load-analysis",
    "/dashboard/utility-management/reports/anomalies",
    "/dashboard/utility-management/reports/sustainability",
    // ESG
    "/dashboard/esg/reports",
  ];

  for (const route of routes) {
    test(route, async ({ page }) => {
      await checkRoute(page, route, route);
    });
  }
});
