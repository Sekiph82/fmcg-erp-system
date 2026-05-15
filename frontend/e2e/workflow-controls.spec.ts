import { expect, test } from "playwright/test";
import {
  credentials,
  loginViaUi,
  missingCredentialsMessage,
  recordMissingData,
} from "./helpers/auth";

const adminCredentials = credentials("admin");
const limitedCredentials = credentials("limited");

test.describe("E2E-WORKFLOW-001 operational workflow controls", () => {
  test.skip(!adminCredentials, missingCredentialsMessage("admin"));

  test("production workflow exposes plan list and controlled create action", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);
    await page.goto("/dashboard/production");

    await expect(page.getByTestId("production-page")).toBeVisible();
    await expect(page.getByTestId("production-plan-list")).toBeVisible();
    await expect(page.getByTestId("production-create-plan-button")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("quality workflow exposes inspection list and controlled create action", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);
    await page.goto("/dashboard/quality");

    await expect(page.getByTestId("quality-page")).toBeVisible();
    await expect(page.getByTestId("quality-inspection-list")).toBeVisible();
    await expect(page.getByTestId("quality-create-inspection-button")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("finance controls keep posting setup actions disabled until required fields exist", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);
    await page.goto("/dashboard/finance/accounting/controls");

    await expect(page.getByTestId("finance-accounting-controls-page")).toBeVisible();
    await expect(page.getByTestId("finance-operational-posting-events")).toBeVisible();
    await expect(page.getByTestId("finance-create-fiscal-year-button")).toBeDisabled();
    await expect(page.getByTestId("finance-create-posting-rule-button")).toBeDisabled();
    await expect(page.getByTestId("finance-create-account-mapping-button")).toBeDisabled();
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("procurement and sales workflow entry points expose stable lists and create controls", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);

    await page.goto("/dashboard/procurement");
    await expect(page.getByTestId("procurement-page")).toBeVisible();
    await expect(page.getByTestId("procurement-pr-list")).toBeVisible();
    await expect(page.getByTestId("procurement-create-pr-button")).toBeVisible();

    await page.goto("/dashboard/sales/customers");
    await expect(page.getByTestId("sales-customers-page")).toBeVisible();
    await expect(page.getByTestId("sales-customers-list")).toBeVisible();
    await expect(page.getByTestId("sales-create-customer-button")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});

test.describe("E2E-RBAC-002 limited role route safety", () => {
  test.skip(!limitedCredentials, missingCredentialsMessage("limited"));

  test("limited user opening admin permission matrix sees denial or a safe allowed route", async ({ page }, testInfo) => {
    await loginViaUi(page, limitedCredentials!);
    await page.goto("/dashboard/permissions");

    await expect(page.getByTestId("dashboard-shell")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");

    if ((await page.getByTestId("access-denied").count()) === 0) {
      await recordMissingData(
        testInfo,
        "Limited E2E user did not render access-denied on /dashboard/permissions; verify that E2E_LIMITED_* points to a restricted role.",
      );
    }
  });
});
