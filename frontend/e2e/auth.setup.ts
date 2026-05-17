import { test as setup, expect } from "playwright/test";
import path from "path";

const authFile = path.join(__dirname, "../playwright/.auth/state.json");

// All routes used in smoke tests — visited here to trigger Next.js dev-server
// compilation before any test runs, preventing ERR_EMPTY_RESPONSE under load.
const WARMUP_ROUTES = [
  // Workspace pages (section C)
  "/dashboard/sales",
  "/dashboard/inventory",
  "/dashboard/finance",
  "/dashboard/production",
  "/dashboard/hr",
  "/dashboard/quality",
  "/dashboard/marketing",
  "/dashboard/utility-management",
  "/dashboard/procurement",
  "/dashboard/documents",
  "/dashboard/admin",
  // Tab variants (section D) — each triggers a separate dynamic-import compilation
  "/dashboard/sales?tab=orders",
  "/dashboard/sales?tab=invoices",
  "/dashboard/sales?tab=van-sales",
  "/dashboard/inventory?tab=stock",
  "/dashboard/inventory?tab=shelf-life",
  "/dashboard/inventory?tab=cycle-count",
  "/dashboard/finance?tab=accounting",
  "/dashboard/finance?tab=fixed-assets",
  "/dashboard/finance?tab=bank-recon",
  "/dashboard/production?tab=orders",
  "/dashboard/production?tab=execution",
  "/dashboard/production?tab=material-flow",
  "/dashboard/hr?tab=employees",
  "/dashboard/hr?tab=recruitment",
  "/dashboard/hr?tab=expenses",
  "/dashboard/quality?tab=qms",
  "/dashboard/quality?tab=allergen",
  "/dashboard/quality?tab=inspections",
];

setup("authenticate as admin", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByTestId("login-form")).toBeVisible();

  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill("Admin1234!");
  await page.getByTestId("login-submit").click();

  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });

  // Save auth state (includes HttpOnly cookies) for all tests
  await page.context().storageState({ path: authFile });

  // Warm up every workspace route so the dev server compiles them before tests run.
  // The 2s pause after each navigation lets React hydrate and fire ssr:false dynamic
  // imports, which triggers server-side chunk compilation while we move to the next page.
  // Failures are swallowed — actual tests will retry.
  for (const route of WARMUP_ROUTES) {
    try {
      await page.goto(route, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await page.waitForTimeout(2_000);
    } catch {
      // non-fatal: test will handle via retries
    }
  }
});
