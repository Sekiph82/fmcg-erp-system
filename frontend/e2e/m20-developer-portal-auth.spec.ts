import { expect, test } from "playwright/test";

test("Developer Portal 401 offers an explicit sign-in recovery action", async ({ page }) => {
  await page.route("**/api/v1/developer/**", async (route) => {
    const headers = {
      "access-control-allow-origin": "http://localhost:3000",
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
      "access-control-allow-headers": "content-type",
    };
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
      return;
    }
    await route.fulfill({
      status: 401,
      contentType: "text/html",
      body: "private diagnostic must not reach the UI",
      headers,
    });
  });

  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await page.goto("/dashboard/integrations?tab=developer");

  await page.waitForURL(/\/login/);
  await expect(page.locator("body")).not.toContainText("private diagnostic");
});

test("API Keys and GraphQL use the configured backend and the full content width", async ({ page }) => {
  const developerResponses: Array<{ path: string; method: string; status: number; origin: string }> = [];
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/v1/developer/")) {
      developerResponses.push({
        path: url.pathname,
        method: response.request().method(),
        status: response.status(),
        origin: url.origin,
      });
    }
  });

  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });

  for (const viewport of [{ width: 1536, height: 960 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    for (const pagePath of [
      { url: "/dashboard/developer/keys", heading: "API Keys", apiPath: "/api/v1/developer/keys" },
      { url: "/dashboard/developer/graphql", heading: "GraphQL Layer", apiPath: "/api/v1/developer/graphql/schema" },
    ]) {
      await page.goto(pagePath.url);
      await expect(page.getByTestId("dashboard-main").getByRole("heading", { name: pagePath.heading, exact: true })).toBeVisible();
      await expect.poll(() => developerResponses.some((result) => result.path === pagePath.apiPath && result.status === 200)).toBe(true);
      const geometry = await page.evaluate(() => {
        const main = document.querySelector<HTMLElement>("[data-testid='dashboard-main']");
        const pageRoot = main?.firstElementChild as HTMLElement | null;
        return {
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: window.innerWidth,
          mainWidth: main?.getBoundingClientRect().width ?? 0,
          pageWidth: pageRoot?.getBoundingClientRect().width ?? 0,
        };
      });
      expect(geometry.documentWidth).toBeLessThanOrEqual(viewport.width + 1);
      expect(geometry.pageWidth).toBeGreaterThanOrEqual(geometry.mainWidth * 0.78);
    }
  }

  const developerOrigin = developerResponses.find((response) => response.path === "/api/v1/developer/keys")?.origin;
  expect(developerOrigin).toBeTruthy();
  expect(developerOrigin).not.toBe("http://localhost:3000");
  expect(developerResponses).toEqual(expect.arrayContaining([
    expect.objectContaining({ path: "/api/v1/developer/keys", method: "GET", status: 200 }),
    expect.objectContaining({ path: "/api/v1/developer/graphql/schema", method: "GET", status: 200 }),
  ]));
});

test("invalid JSON from a successful Developer Portal response is handled safely", async ({ page }) => {
  await page.route("**/api/v1/developer/**", async (route) => {
    const headers = {
      "access-control-allow-origin": "http://localhost:3000",
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
      "access-control-allow-headers": "content-type",
    };
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "{ invalid json", headers });
  });

  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await page.goto("/dashboard/integrations?tab=developer");

  await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("response could not be read");
  await expect(page.locator("body")).not.toContainText("invalid json");
});

test("timed out Developer Portal requests show a bounded recovery state", async ({ page }) => {
  await page.route("**/api/v1/developer/**", async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: {
          "access-control-allow-origin": "http://localhost:3000",
          "access-control-allow-credentials": "true",
          "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
          "access-control-allow-headers": "content-type",
        },
      });
      return;
    }
    await route.abort("timedout");
  });

  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await page.goto("/dashboard/integrations?tab=developer");

  const alert = page.getByTestId("dashboard-main").getByRole("alert");
  await expect(alert).toContainText("API service could not be reached");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});
