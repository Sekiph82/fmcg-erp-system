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
