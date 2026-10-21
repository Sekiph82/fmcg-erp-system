import { expect, test } from "playwright/test";

const next404 = "<!doctype html><html><body>404: This page could not be found</body></html>";

async function signIn(page: import("playwright/test").Page) {
  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
}

async function reply(route: import("playwright/test").Route, status: number, contentType: string, body: string) {
  const corsHeaders = {
    "access-control-allow-origin": "http://localhost:3000",
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
    "access-control-allow-headers": "content-type",
  };
  if (route.request().method() === "OPTIONS") {
    await route.fulfill({ status: 204, headers: corsHeaders });
    return;
  }
  await route.fulfill({ status, contentType, body, headers: corsHeaders });
}

test.describe("Developer Portal API failures", () => {
  test("loads dashboard and resources from the configured backend", async ({ page }) => {
    const developerStatuses: number[] = [];
    page.on("response", (response) => {
      if (response.url().includes("/api/v1/developer/")) developerStatuses.push(response.status());
    });

    await signIn(page);
    await page.goto("/dashboard/integrations");
    await page.getByTestId("dashboard-main").getByRole("button", { name: "Developer", exact: true }).click();

    await expect(page.getByText("Total Keys", { exact: true })).toBeVisible();
    await expect(page.getByText("Authentication", { exact: true })).toBeVisible();
    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toHaveCount(0);
    expect(developerStatuses).toEqual(expect.arrayContaining([200, 200]));
  });

  test("shows a retryable safe error for HTML 404 responses from both dashboard calls", async ({ page }) => {
    const requested: string[] = [];
    await page.route("**/api/v1/developer/**", async (route) => {
      requested.push(new URL(route.request().url()).pathname);
      await reply(route, 404, "text/html", next404);
    });

    await signIn(page);
    await page.goto("/dashboard/integrations");
    await page.getByTestId("dashboard-main").getByRole("button", { name: "Developer" }).click();

    const alert = page.getByTestId("dashboard-main").getByRole("alert");
    await expect(alert).toContainText("Developer Portal resource is unavailable");
    await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
    await expect(page.locator("body")).not.toContainText("<!doctype html>");
    expect(requested).toEqual(expect.arrayContaining([
      "/api/v1/developer/dashboard",
      "/api/v1/developer/resources",
    ]));
  });

  test("shows a permission message without exposing a server response body", async ({ page }) => {
    await page.route("**/api/v1/developer/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/resources")) {
        await reply(route, 200, "application/json", JSON.stringify({
          authentication: {}, sdk_note: "", openapi_json: "", openapi_ui: "", redoc_ui: "",
          postman_collection_note: "", rate_limits: {}, webhooks: {},
        }));
      } else {
        await reply(route, 403, "text/html", "private diagnostic");
      }
    });

    await signIn(page);
    await page.goto("/dashboard/integrations");
    await page.getByTestId("dashboard-main").getByRole("button", { name: "Developer" }).click();

    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("does not have permission");
    await expect(page.locator("body")).not.toContainText("private diagnostic");
  });

  test("shows a session-expired message for API 401 without rendering the body", async ({ page }) => {
    await page.route("**/api/v1/developer/**", async (route) => {
      await reply(route, 401, "text/html", "private diagnostic");
    });

    await signIn(page);
    await page.goto("/dashboard/integrations");
    await page.getByTestId("dashboard-main").getByRole("button", { name: "Developer", exact: true }).click();

    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("session has expired");
    await expect(page.locator("body")).not.toContainText("private diagnostic");
  });

  test("rejects successful HTML responses safely", async ({ page }) => {
    await page.route("**/api/v1/developer/**", async (route) => {
      await reply(route, 200, "text/html", next404);
    });

    await signIn(page);
    await page.goto("/dashboard/integrations?tab=developer");

    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("unexpected response");
    await expect(page.locator("body")).not.toContainText("404: This page could not be found");
  });

  test("shows a stable server error for an API 500", async ({ page }) => {
    await page.route("**/api/v1/developer/**", async (route) => {
      await reply(route, 500, "text/html", "private diagnostic");
    });

    await signIn(page);
    await page.goto("/dashboard/integrations?tab=developer");

    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("API service could not complete");
    await expect(page.locator("body")).not.toContainText("private diagnostic");
  });
});
