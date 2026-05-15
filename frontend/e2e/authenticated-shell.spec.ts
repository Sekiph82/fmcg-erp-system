import { expect, test } from "playwright/test";
import { credentials, loginViaUi, missingCredentialsMessage } from "./helpers/auth";

const adminCredentials = credentials("admin");

test.describe("E2E-RBAC-001 authenticated shell", () => {
  test.skip(!adminCredentials, missingCredentialsMessage("admin"));

  test("admin-compatible user can log in and see the protected shell", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);

    await expect(page.getByTestId("dashboard-shell")).toBeVisible();
    await expect(page.getByTestId("sidebar")).toBeVisible();
    await expect(page.getByTestId("sidebar-nav")).toBeVisible();
  });

  test("permission matrix or first allowed dashboard route can load", async ({ page }) => {
    await loginViaUi(page, adminCredentials!);
    await page.goto("/dashboard/permissions");

    await expect(page.getByTestId("dashboard-shell")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});
