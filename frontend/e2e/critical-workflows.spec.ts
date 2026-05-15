import { expect, test } from "playwright/test";
import {
  credentials,
  loginViaUi,
  missingCredentialsMessage,
  recordMissingData,
} from "./helpers/auth";

const adminCredentials = credentials("admin");
const limitedCredentials = credentials("limited");

const criticalRoutes: { name: string; path: string; marker?: string }[] = [
  { name: "Inventory", path: "/dashboard/inventory", marker: "inventory-page" },
  { name: "Production", path: "/dashboard/production", marker: "production-page" },
  { name: "Quality", path: "/dashboard/quality", marker: "quality-page" },
  { name: "Finance Accounting Controls", path: "/dashboard/finance/accounting/controls", marker: "finance-accounting-controls-page" },
  { name: "Procurement", path: "/dashboard/procurement", marker: "procurement-page" },
  { name: "Sales Customers", path: "/dashboard/sales/customers", marker: "sales-customers-page" },
];

test.describe("E2E-UI-001 critical page smoke", () => {
  test.skip(!adminCredentials, missingCredentialsMessage("admin"));

  for (const route of criticalRoutes) {
    test(`${route.name} page loads without a fatal shell failure`, async ({ page }) => {
      await loginViaUi(page, adminCredentials!);
      await page.goto(route.path);

      await expect(page.getByTestId("dashboard-shell")).toBeVisible();
      await expect(page.locator("body")).not.toContainText("Application error");
      if (route.marker) {
        await expect(page.getByTestId(route.marker)).toBeVisible();
      }
    });
  }
});

test.describe("E2E-INVENTORY-001 scoped inventory UX smoke", () => {
  test.skip(!adminCredentials, missingCredentialsMessage("admin"));

  test("inventory stock table exposes action/view-only markers when data exists", async ({ page }, testInfo) => {
    await loginViaUi(page, adminCredentials!);
    await page.goto("/dashboard/inventory");

    await expect(page.getByTestId("inventory-page")).toBeVisible();
    await expect(page.getByTestId("inventory-tab-stock")).toBeVisible();
    await expect(page.getByTestId("inventory-stock-table")).toBeVisible();

    const actionCount =
      (await page.getByTestId("inventory-adjust-button").count()) +
      (await page.getByTestId("inventory-view-only-badge").count());
    if (actionCount === 0) {
      await recordMissingData(testInfo, "No inventory stock rows were available to assert per-row access hints.");
    }
  });
});

test.describe("E2E-RBAC-001 limited role browser smoke", () => {
  test.skip(!limitedCredentials, missingCredentialsMessage("limited"));

  test("limited user can load a protected shell without seeing unrestricted admin assumptions", async ({ page }) => {
    await loginViaUi(page, limitedCredentials!);

    await expect(page.getByTestId("dashboard-shell")).toBeVisible();
    await expect(page.getByTestId("sidebar")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});
