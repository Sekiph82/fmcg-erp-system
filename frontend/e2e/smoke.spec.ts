/**
 * Smoke tests for FMCG ERP.
 *
 * Coverage:
 *   A. Auth / login flow
 *   B. Dashboard root
 *   C. Main workspace pages
 *   D. Workspace tab navigation
 *   E. Old static route redirects (middleware 308)
 *   F. Dynamic [id] route redirects
 *   G. Theme / layout sanity
 *   H. Console error gating
 */

import { test, expect, Page } from "playwright/test";

// ── Helpers ────────────────────────────────────────────────────────────────────

const SEVERE_CONSOLE_PATTERNS = [
  /uncaught exception/i,
  /hydration.*mismatch/i,
  /chunkloaderror/i,
  /unhandled.*rejection/i,
];

/** Returns a teardown fn; call at end of test to assert no severe errors. */
function collectConsoleErrors(page: Page): () => void {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(`PAGEERROR: ${err.message}`));
  return () => {
    const severe = errors.filter((e) =>
      SEVERE_CONSOLE_PATTERNS.some((re) => re.test(e))
    );
    if (severe.length > 0) {
      throw new Error(`Severe console errors:\n${severe.join("\n")}`);
    }
  };
}

/**
 * Navigate to a workspace URL and assert h1 is visible.
 * Uses domcontentloaded (not networkidle) — avoids flakiness from
 * long-running API calls in SPA pages.
 */
async function assertWorkspace(page: Page, url: string, titleText?: string) {
  await page.goto(url, { waitUntil: "domcontentloaded" });
  const h1 = page.locator("h1").first();
  await expect(h1).toBeVisible({ timeout: 20_000 });
  if (titleText) {
    await expect(h1).toContainText(titleText, { ignoreCase: true });
  }
  await expect(page.locator("text=Application error")).toHaveCount(0);
  await expect(page.locator("text=404")).toHaveCount(0);
}

// ── A. Auth / login flow ───────────────────────────────────────────────────────

test.describe("A. Auth flow", () => {
  test("login page loads and shows form", async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: undefined });
    const page = await ctx.newPage();
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("login-form")).toBeVisible();
    await expect(page.getByTestId("login-username")).toBeVisible();
    await expect(page.getByTestId("login-password")).toBeVisible();
    await expect(page.getByTestId("login-submit")).toBeVisible();
    await ctx.close();
  });

  test("unauthenticated /dashboard redirects to login", async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: undefined });
    const page = await ctx.newPage();
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
    await ctx.close();
  });

  test("admin auth state is active (post-setup)", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page).not.toHaveURL(/\/login/);
  });
});

// ── B. Dashboard root ──────────────────────────────────────────────────────────

test.describe("B. Dashboard", () => {
  test("/ dashboard root loads and has content", async ({ page }) => {
    const checkErrors = collectConsoleErrors(page);
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page.locator("body")).not.toBeEmpty();
    await expect(page.locator("text=Application error")).toHaveCount(0);
    checkErrors();
  });
});

// ── C. Main workspace pages ────────────────────────────────────────────────────

const WORKSPACES: [string, string][] = [
  ["/dashboard/sales",               "Sales"],
  ["/dashboard/inventory",           "Inventory"],
  ["/dashboard/finance",             "Finance"],
  ["/dashboard/production",          "Production"],
  ["/dashboard/hr",                  "HR"],
  ["/dashboard/quality",             "Quality"],
  ["/dashboard/marketing",           "Marketing"],
  ["/dashboard/utility-management",  "Utility"],
  ["/dashboard/procurement",         "Procurement"],
  ["/dashboard/documents",           "Documents"],
  ["/dashboard/admin",               "Admin"],
];

test.describe("C. Main workspaces", () => {
  for (const [url, title] of WORKSPACES) {
    test(`${url} loads with workspace header`, async ({ page }) => {
      const checkErrors = collectConsoleErrors(page);
      await assertWorkspace(page, url, title);
      checkErrors();
    });
  }
});

// ── D. Workspace tabs ──────────────────────────────────────────────────────────

const TABS: [string, string][] = [
  // Sales
  ["/dashboard/sales?tab=orders",           "Orders"],
  ["/dashboard/sales?tab=invoices",         "Invoices"],
  ["/dashboard/sales?tab=van-sales",        "Van"],
  // Inventory
  ["/dashboard/inventory?tab=stock",        "Stock"],
  ["/dashboard/inventory?tab=shelf-life",   "Shelf"],
  ["/dashboard/inventory?tab=cycle-count",  "Cycle"],
  // Finance
  ["/dashboard/finance?tab=accounting",     "Accounting"],
  ["/dashboard/finance?tab=fixed-assets",   "Fixed"],
  ["/dashboard/finance?tab=bank-recon",     "Bank"],
  // Production
  ["/dashboard/production?tab=orders",      "Orders"],
  ["/dashboard/production?tab=execution",   "Execution"],
  ["/dashboard/production?tab=material-flow","Material"],
  // HR
  ["/dashboard/hr?tab=employees",           "Employee"],
  ["/dashboard/hr?tab=recruitment",         "Recruit"],
  ["/dashboard/hr?tab=expenses",            "Expense"],
  // Quality
  ["/dashboard/quality?tab=qms",            "QMS"],
  ["/dashboard/quality?tab=allergen",       "Allergen"],
  ["/dashboard/quality?tab=inspections",    "Inspect"],
];

test.describe("D. Workspace tabs", () => {
  for (const [url, tabLabel] of TABS) {
    test(`${url} — tab "${tabLabel}" renders`, async ({ page }) => {
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 20_000 });
      const tabBtn = page.locator("button", { hasText: new RegExp(tabLabel, "i") }).first();
      await expect(tabBtn).toBeVisible({ timeout: 20_000 });
    });
  }
});

// ── E. Old static route redirects ─────────────────────────────────────────────

const STATIC_REDIRECTS: [string, string][] = [
  ["/dashboard/van-sales",              "/dashboard/sales"],
  ["/dashboard/qms",                    "/dashboard/quality"],
  ["/dashboard/recruitment",            "/dashboard/hr"],
  ["/dashboard/fixed-assets",           "/dashboard/finance"],
  ["/dashboard/marketing/campaigns",    "/dashboard/marketing"],
  ["/dashboard/finance/accounting",     "/dashboard/finance"],
  ["/dashboard/production/orders",      "/dashboard/production"],
  ["/dashboard/shelf-life",             "/dashboard/inventory"],
  ["/dashboard/portal",                 "/dashboard/sales"],
  ["/dashboard/bank-reconciliation",    "/dashboard/finance"],
];

test.describe("E. Static route redirects", () => {
  for (const [from, expectedPrefix] of STATIC_REDIRECTS) {
    test(`${from} → ${expectedPrefix}`, async ({ page }) => {
      await page.goto(from, { waitUntil: "domcontentloaded" });
      expect(page.url()).toContain(expectedPrefix);
      await expect(page.locator("text=404")).toHaveCount(0);
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 20_000 });
    });
  }
});

// ── F. Dynamic [id] route redirects ───────────────────────────────────────────

const DYNAMIC_REDIRECTS: [string, RegExp][] = [
  ["/dashboard/sales/orders/test-id",        /\/dashboard\/sales/],
  ["/dashboard/procurement/orders/test-id",  /\/dashboard\/procurement/],
  ["/dashboard/documents/test-id",           /\/dashboard\/documents/],
  ["/dashboard/crm/records/test-id",         /\/dashboard\/crm/],
  ["/dashboard/users/test-id",               /\/dashboard\/admin/],
  ["/dashboard/payroll/runs/test-id",        /\/dashboard\/hr.*tab=payroll/],
];

test.describe("F. Dynamic route redirects", () => {
  for (const [from, expectedURLPattern] of DYNAMIC_REDIRECTS) {
    test(`${from} → matches ${expectedURLPattern}`, async ({ page }) => {
      // Use waitUntil:"commit" — just wait for server response; the client-side
      // redirect fires in useEffect so we wait for the URL to change afterward.
      await page.goto(from, { waitUntil: "commit" });
      // Allow up to 15s for the client-side redirect to complete
      await page.waitForURL(expectedURLPattern, { timeout: 15_000 });
      await expect(page.locator("text=404")).toHaveCount(0);
    });
  }
});

// ── G. Theme / layout sanity ──────────────────────────────────────────────────

test.describe("G. Theme sanity", () => {
  test("sales workspace has h1, non-empty body, no error overlay", async ({
    page,
  }) => {
    await page.goto("/dashboard/sales", { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 20_000 });
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.trim().length).toBeGreaterThan(10);
    await expect(page.locator("text=Application error")).toHaveCount(0);
    await expect(page.locator("text=Unhandled Runtime Error")).toHaveCount(0);
  });

  test("admin workspace renders without error overlay", async ({ page }) => {
    await page.goto("/dashboard/admin", { waitUntil: "domcontentloaded" });
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("text=Application error")).toHaveCount(0);
  });
});

// ── H. MPS sub-route pages ────────────────────────────────────────────────────
// Each MPS sub-route must stay on its own URL, show unique h1 content,
// and must NOT redirect to /dashboard/planning?tab=mps.

const MPS_PAGES: [string, string][] = [
  ["/dashboard/mps/planning-board", "Production Planning Board"],
  ["/dashboard/mps/capacity",       "Capacity Heatmap"],
  ["/dashboard/mps/campaigns",      "Campaign Planning"],
  ["/dashboard/mps/whatif",         "What-If Simulation"],
];

test.describe("H. MPS sub-route pages", () => {
  for (const [route, expectedH1] of MPS_PAGES) {
    test(`${route} stays on route and shows unique content`, async ({ page }) => {
      await page.goto(route, { waitUntil: "domcontentloaded" });

      // 1. URL must stay on the MPS sub-route (not redirect away)
      expect(page.url()).toContain(route);

      // 2. Must NOT have redirected to /dashboard/planning?tab=mps
      expect(page.url()).not.toContain("/dashboard/planning");

      // 3. Unique page h1 content must appear
      await expect(page.locator("h1").first()).toContainText(expectedH1, {
        timeout: 20_000,
        ignoreCase: true,
      });

      // 4. No error overlays
      await expect(page.locator("text=Application error")).toHaveCount(0);
      await expect(page.locator("text=404")).toHaveCount(0);
    });
  }
});
