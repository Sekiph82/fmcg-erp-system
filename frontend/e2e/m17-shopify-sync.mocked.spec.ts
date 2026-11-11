import { expect, test, type Page, type Route } from "playwright/test";

// Synthetic route mocks only — no backend, database or real Shopify store.

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function setup(page: Page, configured: boolean) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-integrations-user", email: "integrations@example.invalid", username: "synthetic-integrations",
    full_name: "Synthetic Integrations", is_active: true, is_superuser: false, must_change_password: false, roles: [],
    permission_codes: ["integrations.view", "integrations.edit"], modules: ["integrations"], scopes: [], feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, { permission_codes: [], visible_permission_codes: [] }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-integrations-token", url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
  const calls: string[] = [];
  await page.route("**/api/v1/integrations/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/ecommerce/import-orders")) {
      calls.push(`import:${JSON.parse(route.request().postData() ?? "{}").platform}`);
      return configured
        ? fulfillJson(route, { platform: "SHOPIFY", imported: 2, mapped: 2, failed: 1,
          errors: ["Shopify order #1003: unknown SKU(s) NOT-IN-ERP"] })
        : fulfillJson(route, { detail: { provider: "SHOPIFY", status: "STUB_ONLY",
          detail: "Shopify is not configured (SHOPIFY_SHOP_DOMAIN / SHOPIFY_ACCESS_TOKEN); nothing was synchronised." } }, 501);
    }
    if (url.pathname.endsWith("/ecommerce/sync-inventory")) {
      calls.push(`inventory:${url.searchParams.get("platform")}`);
      return fulfillJson(route, { platform: "SHOPIFY", products_synced: 4, failed: 0, errors: [] });
    }
    return fulfillJson(route, []);
  });
  return calls;
}

test.describe("M17 Shopify sync (mocked API)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("imports Shopify orders and pushes stock, showing failed SKUs", async ({ page }) => {
    const calls = await setup(page, true);
    await page.goto("/dashboard/integrations/sync");
    await page.getByRole("button", { name: /E-commerce/ }).click();
    await page.getByRole("button", { name: /Import Orders/ }).click();
    await expect(page.getByText("Import result: 2 new draft sales orders, 1 failed")).toBeVisible();
    await expect(page.getByText(/unknown SKU\(s\) NOT-IN-ERP/)).toBeVisible();
    await page.getByRole("button", { name: /Sync Inventory/ }).click();
    await expect(page.getByText("Inventory sync complete")).toBeVisible();
    expect(calls).toEqual(["import:shopify", "inventory:shopify"]);
  });

  test("shows the not-configured message instead of a fake success", async ({ page }) => {
    await setup(page, false);
    await page.goto("/dashboard/integrations/sync");
    await page.getByRole("button", { name: /E-commerce/ }).click();
    await page.getByRole("button", { name: /Import Orders/ }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Shopify is not configured" })).toBeVisible();
    await expect(page.getByText(/Import result/)).toHaveCount(0);
  });
});
