import { expect, test, type Page, type Route } from "playwright/test";

const apiBase = "**/api/v1/**";
const recordId = "44444444-4444-4444-8444-444444444444";
const actorId = "11111111-1111-4111-8111-111111111111";

function downtimeRecord(rootReason: string) {
  return {
    id: recordId,
    work_order_id: null,
    production_order_id: null,
    session_id: null,
    created_by_user_id: actorId,
    closed_by_user_id: null,
    machine_id: null,
    machine_name: null,
    line_id: "SYNTHETIC-LINE-T004",
    operator_id: null,
    operator_name: "Synthetic operator",
    team_id: null,
    shift_id: null,
    start_time: "2026-11-08T08:00:00Z",
    end_time: null,
    duration_minutes: null,
    is_closed: false,
    downtime_category: "IT_ISSUE",
    root_reason: rootReason,
    impact_level: "LOW",
    comments: null,
    created_at: "2026-11-08T08:00:00Z",
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page) {
  const baseUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  if (!new Set(["localhost", "127.0.0.1", "::1", "[::1]"]).has(baseUrl.hostname.toLowerCase())) {
    throw new Error("Mocked Shop Floor acceptance requires a loopback E2E_BASE_URL.");
  }
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-m23-shop-floor-token",
    url: baseUrl.origin,
    httpOnly: true,
    sameSite: "Lax",
  }]);
}

async function installShopFloorApi(
  page: Page,
  mode: "normal" | "server-error-once" | "commit-then-drop-response" = "normal",
) {
  const requestKeys: string[] = [];
  let savedRecord: ReturnType<typeof downtimeRecord> | null = null;
  let postCount = 0;
  let authMeCount = 0;

  await page.route(apiBase, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/auth/me")) {
      authMeCount += 1;
      return fulfillJson(route, {
        id: actorId,
        email: "shop-floor@example.invalid",
        username: "synthetic-shop-floor",
        full_name: "Synthetic Shop Floor User",
        is_active: true,
        is_superuser: true,
        must_change_password: false,
        roles: [],
        permission_codes: [],
        modules: ["production"],
        scopes: [],
        feature_flags: {},
      });
    }
    if (url.pathname.endsWith("/modules/manifest")) {
      return fulfillJson(route, { permission_codes: [], visible_permission_codes: [] });
    }
    if (url.pathname === "/api/v1/shop-floor/downtime" && request.method() === "GET") {
      return fulfillJson(route, savedRecord ? [savedRecord] : []);
    }
    if (url.pathname === "/api/v1/shop-floor/downtime" && request.method() === "POST") {
      postCount += 1;
      requestKeys.push(request.headers()["idempotency-key"] || "");
      const saved = downtimeRecord("Synthetic saved before response was lost");
      if (mode === "server-error-once" && postCount === 1) {
        return fulfillJson(route, { detail: "Synthetic temporary server failure" }, 503);
      }
      if (mode === "commit-then-drop-response" && postCount === 1) {
        savedRecord = saved;
        return route.abort("failed");
      }
      savedRecord = saved;
      return fulfillJson(route, saved, 201);
    }
    return fulfillJson(route, []);
  });
  return { requestKeys, authMeCount: () => authMeCount };
}

async function openDowntimeForm(page: Page) {
  await page.goto("/dashboard/shop-floor/downtime");
  await expect(page.getByRole("heading", { name: "Downtime Board" })).toBeVisible();
  await page.getByRole("button", { name: "+ Log Downtime" }).click();
  await page.getByLabel("Line ID").fill("SYNTHETIC-LINE-T004");
  await page.getByLabel("Root Reason").fill("Synthetic retry acceptance");
}

test.describe("Shop Floor online-only recovery", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("blocks writes while offline and requires a refresh after reconnecting", async ({ page, context }) => {
    await signIn(page);
    const api = await installShopFloorApi(page);
    await openDowntimeForm(page);
    const initialAuthCheckCount = api.authMeCount();

    await context.setOffline(true);
    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("changes are not saved offline");
    const submit = page.getByRole("button", { name: "Start Downtime" });
    await expect(submit).toBeDisabled();
    expect(api.requestKeys).toHaveLength(0);

    await context.setOffline(false);
    const reconnectNotice = page.getByText("Connection restored. Refresh the latest Shop Floor state and revalidate your sign-in and permissions before continuing.");
    await expect(reconnectNotice).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "Refresh Shop Floor state" }).click();
    await expect(reconnectNotice).not.toBeVisible();
    await expect(submit).toBeEnabled();
    expect(api.authMeCount()).toBeGreaterThan(initialAuthCheckCount);
    expect(api.requestKeys).toHaveLength(0);
  });

  test("refreshes after a server error and reuses the unchanged request key", async ({ page }) => {
    await signIn(page);
    const api = await installShopFloorApi(page, "server-error-once");
    await openDowntimeForm(page);

    await page.getByRole("button", { name: "Start Downtime" }).click();
    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("The result is not confirmed");
    await expect(page.getByRole("button", { name: "Start Downtime" })).toBeDisabled();
    await page.getByRole("dialog").getByRole("button", { name: "Refresh Shop Floor state" }).click();
    await page.getByRole("button", { name: "Start Downtime" }).click();

    await expect(page.getByRole("heading", { name: "Log Downtime Event" })).toHaveCount(0);
    expect(api.requestKeys).toHaveLength(2);
    expect(api.requestKeys[0]).toBeTruthy();
    expect(api.requestKeys[1]).toBe(api.requestKeys[0]);
  });

  test("reconciles a saved action after its response is lost before allowing another submit", async ({ page }) => {
    await signIn(page);
    const api = await installShopFloorApi(page, "commit-then-drop-response");
    await openDowntimeForm(page);

    await page.getByRole("button", { name: "Start Downtime" }).click();
    await expect(page.getByTestId("dashboard-main").getByRole("alert")).toContainText("The result is not confirmed");
    await page.getByRole("dialog").getByRole("button", { name: "Refresh Shop Floor state" }).click();
    await expect(page.getByText("Synthetic saved before response was lost")).toBeVisible();
    await page.getByRole("button", { name: "Start Downtime" }).click();

    await expect(page.getByRole("heading", { name: "Log Downtime Event" })).toHaveCount(0);
    expect(api.requestKeys).toHaveLength(2);
    expect(api.requestKeys[1]).toBe(api.requestKeys[0]);
  });
});
