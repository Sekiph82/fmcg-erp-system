import { expect, test } from "playwright/test";

test.describe("E2E-AUTH-001 public auth smoke", () => {
  test("login page renders stable form controls", async ({ page }) => {
    await page.goto("/login");

    await expect(page.getByTestId("login-form")).toBeVisible();
    await expect(page.getByTestId("login-username")).toBeVisible();
    await expect(page.getByTestId("login-password")).toBeVisible();
    await expect(page.getByTestId("login-submit")).toBeVisible();
  });

  test("protected dashboard redirects unauthenticated user to login", async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: undefined });
    const page = await ctx.newPage();
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
    await ctx.close();
  });

  test("bad login stays on login and shows a safe error", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill("e2e_invalid_user");
    await page.getByTestId("login-password").fill("definitely-not-a-real-password");
    await page.getByTestId("login-submit").click();

    await expect(page.getByTestId("login-error")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});
