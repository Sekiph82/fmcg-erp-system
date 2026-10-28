import { expect, test } from "playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("synthetic Developer Portal states remain readable and errors stay safe", async ({ page, context }) => {
  const baseUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  if (!new Set(["localhost", "127.0.0.1", "::1", "[::1]"]).has(baseUrl.hostname.toLowerCase())) {
    throw new Error("Synthetic Developer Portal test must use a loopback E2E_BASE_URL; refusing to send its test cookie remotely.");
  }
  await context.addCookies([{
    name: "erp_access_token",
    value: "synthetic-m20-developer-portal-session",
    url: baseUrl.origin,
    httpOnly: true,
    sameSite: "Lax",
  }]);

  let failureStatus: 401 | 404 | null = null;
  const dashboard = {
    total_keys: 0,
    active_keys: 0,
    total_api_calls: 0,
    success_calls: 0,
    error_calls: 0,
    available_scopes: ["read", "write"],
    default_rate_limit: 60,
  };
  const resources = {
    openapi_json: "/api/v1/openapi.json",
    openapi_ui: "/docs",
    redoc_ui: "/redoc",
    postman_collection_note: "Use the synthetic sample collection.",
    authentication: { token_type: "Bearer", cookie: "HttpOnly session cookie" },
    rate_limits: { default: "60 requests per minute" },
    sdk_note: "No SDK package is installed by this visual test.",
    webhooks: { available: "Tenant-managed webhooks" },
  };
  const graphql = {
    status: "STUB",
    note: "GraphQL is a planned interface. Use the REST API for current ERP operations.",
    planned_types: ["Product", "Material"],
    planned_queries: ["product(id: ID!)"],
    planned_mutations: ["createProduct(input: ProductInput!)"],
    rest_api_base: "/api/v1",
  };

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
        id: "00000000-0000-4000-8000-000000000021",
        email: "synthetic-m20-developer@example.invalid",
        username: "synthetic-developer",
        full_name: "Synthetic M20 Developer",
        is_active: true,
        is_superuser: true,
        must_change_password: false,
        roles: [],
        permission_codes: [],
        modules: [],
        scopes: [],
        feature_flags: {},
      }) });
      return;
    }
    if (path.endsWith("/auth/refresh")) {
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "synthetic expired refresh session" }) });
      return;
    }

    if (path.startsWith("/api/v1/developer/") && failureStatus !== null) {
      await route.fulfill({
        status: failureStatus,
        contentType: failureStatus === 404 ? "text/html" : "application/json",
        body: failureStatus === 404 ? "<html>PRIVATE_SERVER_SECRET_STACK</html>" : JSON.stringify({ detail: "synthetic expired session" }),
      });
      return;
    }

    let body: unknown = [];
    if (path.endsWith("/developer/dashboard")) body = dashboard;
    else if (path.endsWith("/developer/resources")) body = resources;
    else if (path.endsWith("/developer/graphql/schema")) body = graphql;
    else if (path.endsWith("/developer/keys")) body = [];

    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard/developer");
  await expect(page.getByRole("heading", { name: "Developer Portal" })).toBeVisible();
  await expect(page.getByText("Total API Calls")).toBeVisible();
  await expect(page.getByRole("link", { name: /API Keys/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  await page.screenshot({ path: "test-results/m20-current-developer-portal-mobile.png", fullPage: true });

  await page.goto("/dashboard/developer/keys");
  await expect(page.getByRole("heading", { name: "API Keys", exact: true })).toBeVisible();
  await expect(page.getByText("No API keys yet.")).toBeVisible();
  await page.screenshot({ path: "test-results/m20-current-developer-keys-empty-mobile.png", fullPage: true });

  await page.goto("/dashboard/developer/graphql");
  await expect(page.getByRole("heading", { name: "GraphQL Layer" })).toBeVisible();
  await expect(page.getByText("STUB", { exact: true })).toBeVisible();
  await expect(page.getByText("GraphQL is a planned interface. Use the REST API for current ERP operations.")).toBeVisible();
  await page.screenshot({ path: "test-results/m20-current-developer-graphql-mobile.png", fullPage: true });

  failureStatus = 401;
  const refreshResponse = page.waitForResponse((response) => (
    response.url().endsWith("/api/v1/auth/refresh")
  ));
  await page.goto("/dashboard/developer");
  expect((await refreshResponse).status()).toBe(401);
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "POVU ERP" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await page.screenshot({ path: "test-results/m20-current-developer-401-mobile.png", fullPage: true });

  failureStatus = 404;
  await page.goto("/dashboard/developer");
  const unavailableAlert = page.locator('[role="alert"]').filter({ hasText: "This Developer Portal resource is unavailable." });
  await expect(unavailableAlert).toBeVisible();
  await expect(unavailableAlert).not.toContainText("PRIVATE_SERVER_SECRET_STACK");
  await page.screenshot({ path: "test-results/m20-current-developer-404-safe-mobile.png", fullPage: true });

  await page.setViewportSize({ width: 1536, height: 960 });
  failureStatus = null;
  await page.goto("/dashboard/developer");
  await expect(page.getByRole("heading", { name: "Developer Portal" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1537);
  await page.screenshot({ path: "test-results/m20-current-developer-portal-desktop.png", fullPage: true });
});
