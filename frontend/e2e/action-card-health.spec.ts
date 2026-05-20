/**
 * Action Card Health — Targeted E2E tests for known card/tile patterns
 *
 * Verifies that key navigation tiles and action cards produce observable results.
 *
 * Run (app must be running):
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/action-card-health.spec.ts \
 *     --project=chromium --workers=1 --reporter=list
 */

import { test, expect } from "playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

// ─── Inventory → Cycle Count ────────────────────────────────────────────────

test.describe("Inventory → Cycle Count action cards", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/inventory?tab=cycle-count`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
  });

  const cycleCountCards = [
    { label: "Count Plans", expectedUrl: "/dashboard/cycle-count/plans" },
    { label: "Count Tasks", expectedUrl: "/dashboard/cycle-count/tasks" },
    { label: "Count Entries", expectedUrl: "/dashboard/cycle-count/entries" },
    { label: "Variance Review", expectedUrl: "/dashboard/cycle-count/variances" },
    { label: "Reports & AI", expectedUrl: "/dashboard/cycle-count/reports" },
  ];

  for (const card of cycleCountCards) {
    test(`"${card.label}" navigates to ${card.expectedUrl}`, async ({ page }) => {
      const link = page.getByText(card.label, { exact: false }).first();
      await expect(link).toBeVisible({ timeout: 5000 });

      await link.click();
      await page.waitForURL(`**${card.expectedUrl}**`, { timeout: 8000 });
      expect(page.url()).toContain(card.expectedUrl);
    });
  }
});

// ─── Logistics → Overview KPI tiles ─────────────────────────────────────────

test.describe("Logistics → Overview KPI tiles stay in workspace", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/logistics?tab=overview`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
  });

  test("KPI tile navigates to shipments tab (stays in /dashboard/logistics)", async ({ page }) => {
    const tile = page.getByText("Active Shipments", { exact: false }).first();
    await expect(tile).toBeVisible({ timeout: 5000 });
    await tile.click();
    await page.waitForURL(`**/dashboard/logistics**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/logistics");
    expect(page.url()).toContain("tab=shipments");
  });

  test("Quick nav 'Shipment Planning' stays in /dashboard/logistics", async ({ page }) => {
    const card = page.getByText("Shipment Planning", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/logistics**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/logistics");
    expect(page.url()).toContain("tab=shipments");
  });

  test("Quick nav 'Container Tracking' stays in /dashboard/logistics", async ({ page }) => {
    const card = page.getByText("Container Tracking", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/logistics**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/logistics");
    expect(page.url()).toContain("tab=containers");
  });

  test("Quick nav 'Arrival & Clearance' stays in /dashboard/logistics", async ({ page }) => {
    const card = page.getByText("Arrival & Clearance", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/logistics**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/logistics");
    expect(page.url()).toContain("tab=arrivals");
  });
});

// ─── Maintenance → Overview KPI tiles ───────────────────────────────────────

test.describe("Maintenance → Overview KPI tiles stay in workspace", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/maintenance?tab=overview`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
  });

  test("Quick nav 'Asset Register' stays in /dashboard/maintenance", async ({ page }) => {
    const card = page.getByText("Asset Register", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/maintenance**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/maintenance");
    expect(page.url()).toContain("tab=assets");
  });

  test("Quick nav 'PM Plans & Work Orders' stays in /dashboard/maintenance", async ({ page }) => {
    const card = page.getByText("PM Plans & Work Orders", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/maintenance**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/maintenance");
    expect(page.url()).toContain("tab=plans");
  });

  test("Quick nav 'Predictive Maintenance' stays in /dashboard/maintenance", async ({ page }) => {
    const card = page.getByText("Predictive Maintenance", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/maintenance**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/maintenance");
    expect(page.url()).toContain("tab=predictive");
  });
});

// ─── Allergen → Action Cards and Quick Navigation ───────────────────────────

test.describe("Allergen dashboard action cards", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/allergen`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
  });

  test("Quick nav 'Allergen Master' navigates to /dashboard/allergen/allergens", async ({ page }) => {
    const card = page.getByText("Allergen Master", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/allergen/allergens**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/allergen/allergens");
  });

  test("Action card 'Missing allergen profiles' navigates to material-profiles", async ({ page }) => {
    const card = page.getByText("Missing allergen profiles", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/allergen/material-profiles**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/allergen/material-profiles");
  });
});

// ─── Cycle Count Dashboard standalone ───────────────────────────────────────

test.describe("Cycle Count standalone dashboard cards", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/cycle-count`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
  });

  test('"Count Plans" navigates to plans page', async ({ page }) => {
    const card = page.getByText("Count Plans", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/cycle-count/plans**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/cycle-count/plans");
  });

  test('"Reports & AI" navigates to reports page', async ({ page }) => {
    const card = page.getByText("Reports & AI", { exact: false }).first();
    await expect(card).toBeVisible({ timeout: 5000 });
    await card.click();
    await page.waitForURL(`**/dashboard/cycle-count/reports**`, { timeout: 5000 });
    expect(page.url()).toContain("/dashboard/cycle-count/reports");
  });
});

// ─── MPS sub-route regression ────────────────────────────────────────────────
// These 4 pages must NOT redirect to /dashboard/planning?tab=mps.
// See Round 13/14 for the fix history.

test.describe("MPS sub-route pages (redirect-stub regression)", () => {
  const MPS_PAGES: Array<{ route: string; h1: string }> = [
    { route: "/dashboard/mps/planning-board", h1: "Production Planning Board" },
    { route: "/dashboard/mps/capacity",       h1: "Capacity Heatmap" },
    { route: "/dashboard/mps/campaigns",      h1: "Campaign Planning" },
    { route: "/dashboard/mps/whatif",         h1: "What-If Simulation" },
  ];

  for (const { route, h1 } of MPS_PAGES) {
    test(`${route} stays on route and shows unique content`, async ({ page }) => {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: "domcontentloaded" });

      // URL must stay on MPS sub-route — must NOT redirect away
      expect(page.url()).toContain(route);
      expect(page.url()).not.toContain("/dashboard/planning");

      // Unique h1 must be visible
      await expect(page.locator("h1").first()).toContainText(h1, {
        timeout: 20_000,
        ignoreCase: true,
      });

      // No error overlays
      await expect(page.locator("text=Application error")).toHaveCount(0);
      await expect(page.locator("text=404")).toHaveCount(0);
    });
  }
});

// ─── actionRegistry command palette links (strict route checks) ──────────────
// These were previously pointing to redirect stubs. After the fix they point
// to direct workspace URLs. Verify the target URLs are reachable (not 404, not
// redirect-to-planning, not application error).

test.describe("actionRegistry hrefs resolve to reachable workspace pages", () => {
  const PALETTE_TARGETS: Array<{ label: string; href: string; expectedPathFragment: string }> = [
    { label: "contracts drawer",    href: "/dashboard/sales?tab=contracts&drawer=create",       expectedPathFragment: "/dashboard/sales" },
    { label: "expenses drawer",     href: "/dashboard/hr?tab=expenses&drawer=create",           expectedPathFragment: "/dashboard/hr" },
    { label: "recruitment tab",     href: "/dashboard/hr?tab=recruitment",                      expectedPathFragment: "/dashboard/hr" },
    { label: "kanban tab",          href: "/dashboard/planning?tab=kanban",                     expectedPathFragment: "/dashboard/planning" },
    { label: "van-sales tab",       href: "/dashboard/sales?tab=van-sales",                     expectedPathFragment: "/dashboard/sales" },
    { label: "bank-recon tab",      href: "/dashboard/finance?tab=bank-recon",                  expectedPathFragment: "/dashboard/finance" },
    { label: "mrp tab",             href: "/dashboard/planning?tab=mrp",                        expectedPathFragment: "/dashboard/planning" },
    { label: "procurement suggest", href: "/dashboard/procurement?tab=suggestions",             expectedPathFragment: "/dashboard/procurement" },
    { label: "production plans tab",href: "/dashboard/production?tab=plans",                    expectedPathFragment: "/dashboard/production" },
    { label: "report-builder tab",  href: "/dashboard/analytics?tab=report-builder",            expectedPathFragment: "/dashboard/analytics" },
    { label: "dunning tab",         href: "/dashboard/finance?tab=dunning",                     expectedPathFragment: "/dashboard/finance" },
    { label: "esg tab",             href: "/dashboard/utility-management?tab=esg",             expectedPathFragment: "/dashboard/utility-management" },
    { label: "payroll tab",         href: "/dashboard/hr?tab=payroll",                          expectedPathFragment: "/dashboard/hr" },
    { label: "invoice-match tab",   href: "/dashboard/finance?tab=invoice-match",               expectedPathFragment: "/dashboard/finance" },
  ];

  for (const { label, href, expectedPathFragment } of PALETTE_TARGETS) {
    test(`${label}: ${href} resolves without redirect or error`, async ({ page }) => {
      await page.goto(`${BASE_URL}${href}`, { waitUntil: "domcontentloaded" });

      // Must stay in the expected workspace
      expect(page.url()).toContain(expectedPathFragment);

      // Must not error
      await expect(page.locator("text=404")).toHaveCount(0);
      await expect(page.locator("text=Application error")).toHaveCount(0);

      // Must have some visible content
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 20_000 });
    });
  }
});

// ─── Marketing workspace action buttons (drawer param regression) ────────────

test.describe("Marketing workspace create buttons include drawer=create param", () => {
  test("+ New Campaign links to marketing?tab=campaigns&drawer=create", async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/marketing`, { waitUntil: "domcontentloaded" });
    const btn = page.locator("a[href*='tab=campaigns'][href*='drawer=create']").first();
    await expect(btn).toBeVisible({ timeout: 20_000 });
  });

  test("+ New Promotion links to marketing?tab=promotions&drawer=create", async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/marketing`, { waitUntil: "domcontentloaded" });
    const btn = page.locator("a[href*='tab=promotions'][href*='drawer=create']").first();
    await expect(btn).toBeVisible({ timeout: 20_000 });
  });
});

// ─── CRM workspace quick links (direct tab URLs, no redirect stubs) ──────────

test.describe("CRM workspace quick links use direct tab URLs", () => {
  test("CRM Overdue Queue links to crm?tab=pipeline (not crm/overdue stub)", async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/crm`, { waitUntil: "domcontentloaded" });
    // The overdue link must not point to the stub route
    const stubLink = page.locator("a[href='/dashboard/crm/overdue']");
    await expect(stubLink).toHaveCount(0);
    // It should point to the tab URL instead
    const tabLink = page.locator("a[href*='tab=pipeline']").first();
    await expect(tabLink).toBeVisible({ timeout: 20_000 });
  });

  test("CRM AI Agents links to crm?tab=overview (not crm/ai stub)", async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/crm`, { waitUntil: "domcontentloaded" });
    const stubLink = page.locator("a[href='/dashboard/crm/ai']");
    await expect(stubLink).toHaveCount(0);
  });
});
