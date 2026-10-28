import { expect, test } from "playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const backend = process.env.M20_BACKEND_URL || "";
const apiPort = process.env.M20_API_PORT || "";
const disposableDatabaseName = process.env.M20_DISPOSABLE_TEST_DATABASE_NAME || "";
const testUsername = process.env.M20_TEST_USERNAME || "";
const testPassword = process.env.E2E_PASSWORD || "";
const expectedWarehouseId = process.env.M20_TEST_WAREHOUSE_ID || "";

// This test signs into its own isolated backend. Do not inherit the shared
// browser project's owner auth state or local storage.
test.use({ storageState: { cookies: [], origins: [] } });

test("MPS scenario UI persists a real split through the PostgreSQL-backed API", async ({ page }) => {
  test.skip(
    process.env.M20_DISPOSABLE_TEST_DATABASE !== "1",
    "requires explicit opt-in for a task-owned disposable M20 database; this test persists scenario history",
  );
  // The disposable runner validates the connected database before starting
  // Uvicorn on this exact loopback port; the browser asserts the same endpoint.
  expect(backend, "set the explicit loopback URL of the runner-launched API").not.toBe("");
  expect(apiPort, "set the runner's explicit API listener port").toMatch(/^\d{4,5}$/);
  const backendUrl = new URL(backend);
  expect(backendUrl.hostname, "E2E endpoint must use the same localhost cookie host as the UI").toBe("localhost");
  expect(backendUrl.port, "E2E endpoint port must be the API runner's verified listener port").toBe(apiPort);
  expect(backendUrl.username).toBe("");
  expect(backendUrl.password).toBe("");
  console.log(`M20 API endpoint under test: http://localhost:${apiPort} (runner listener 127.0.0.1:${apiPort})`);
  expect(disposableDatabaseName, "set the exact per-run disposable database name for both backend and browser test").toMatch(
    /^fmcg_m20_[a-z0-9]+_[a-f0-9]{20,32}$/,
  );
  expect(testUsername, "use an explicitly provisioned synthetic least-privilege MPS planner").toMatch(/^m20-planner-[a-f0-9]{10,}$/);
  expect(testPassword, "supply the disposable planner password through E2E_PASSWORD; never use a built-in fallback").not.toBe("");
  console.log(`M20 synthetic principal: ${testUsername}`);
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/mps/")) console.log(`MPS browser API ${response.status()} ${new URL(response.url()).pathname}`);
  });
  const login = await page.request.post(`${backend}/api/v1/auth/login`, {
    form: { username: testUsername, password: testPassword },
  });
  expect(login.ok(), `synthetic planner login returned ${login.status()}`).toBeTruthy();
  const authCookies = await page.context().cookies(backend);
  const authCookie = authCookies.find((cookie) => cookie.name === "erp_access_token" && cookie.httpOnly && cookie.value.length > 0);
  expect(authCookie, "backend login must establish the real HttpOnly auth cookie").toBeTruthy();
  const profileResponse = await page.request.get(`${backend}/api/v1/auth/me`);
  expect(profileResponse.ok(), `synthetic planner profile returned ${profileResponse.status()}`).toBeTruthy();
  const profile = await profileResponse.json() as {
    username: string; is_superuser: boolean; permission_codes: string[];
    scopes: Array<{ scope_type: string; scope_id: string; is_active: boolean; can_view: boolean; can_edit: boolean }>;
  };
  expect(profile.username).toBe(testUsername);
  expect(profile.is_superuser).toBe(false);
  expect([...profile.permission_codes].sort()).toEqual(["mps.edit_own_warehouse", "mps.simulate", "mps.view"]);
  expect(expectedWarehouseId).toMatch(/^[0-9a-f-]{36}$/i);
  expect(profile.scopes).toHaveLength(1);
  expect(profile.scopes[0]).toMatchObject({
    scope_type: "warehouse", scope_id: expectedWarehouseId,
    is_active: true, can_view: true, can_edit: true,
  });
  console.log(`M20 principal authorization: is_superuser=false permissions=mps.view,mps.simulate,mps.edit_own_warehouse warehouse_scope=${expectedWarehouseId}`);
  // The browser UI is served on another localhost port. Explicitly install
  // the real backend-issued host cookie for that origin before navigating.
  await page.context().clearCookies({ name: "erp_access_token" });
  await page.context().addCookies([{
    name: authCookie!.name,
    value: authCookie!.value,
    url: process.env.E2E_BASE_URL || "http://localhost:3000",
    expires: authCookie!.expires,
    httpOnly: authCookie!.httpOnly,
    secure: authCookie!.secure,
    sameSite: authCookie!.sameSite,
  }]);
  const uiAuthCookie = (await page.context().cookies(process.env.E2E_BASE_URL || "http://localhost:3000"))
    .find((cookie) => cookie.name === "erp_access_token");
  expect(uiAuthCookie, `real auth cookie was not scoped to the frontend origin (backend domain=${authCookie!.domain})`).toBeTruthy();

  const plansResponse = await page.request.get(`${backend}/api/v1/mps/plans`);
  expect(plansResponse.ok(), `MPS plans returned ${plansResponse.status()}`).toBeTruthy();
  const plans = await plansResponse.json() as Array<{ id: string; plan_no: string; capacity_mode: string }>;
  const isolatedPlanPrefix = "M20-OPS-PLAN-";
  let selected: { planId: string; planNo: string; line: { id: string; line_no: string; planned_production_qty: number } } | undefined;
  for (const plan of plans) {
    if (plan.capacity_mode !== "FINITE" || !plan.plan_no.startsWith(isolatedPlanPrefix)) continue;
    const response = await page.request.get(`${backend}/api/v1/mps/plans/${plan.id}/lines`);
    if (!response.ok()) continue;
    const lines = await response.json() as Array<{
      id: string; line_no: string; planned_production_qty: number; is_locked: boolean;
    }>;
    const line = lines.find((item) => !item.is_locked && Number(item.planned_production_qty) >= 0.002);
    if (line) {
      selected = { planId: plan.id, planNo: plan.plan_no, line };
      break;
    }
  }
  expect(selected, `requires a disposable finite-capacity test plan with prefix ${isolatedPlanPrefix} and an unlocked positive line`).toBeTruthy();
  const { planId, line } = selected!;
  const total = Number(line.planned_production_qty);
  const first = Math.round(total * 500) / 1000;
  const second = Number((total - first).toFixed(3));
  expect(first).toBeGreaterThan(0);
  expect(second).toBeGreaterThan(0);

  const dashboardRequest = page.waitForRequest((request) => request.url().includes("/dashboard/mps/whatif"));
  await page.goto("/dashboard/mps/whatif");
  const dashboardHeaders = await (await dashboardRequest).allHeaders();
  expect(dashboardHeaders.cookie?.includes("erp_access_token="), "frontend navigation must send the HttpOnly auth cookie").toBeTruthy();
  await expect(page.getByRole("heading", { name: "What-If Simulation" })).toBeVisible();
  await page.getByRole("combobox").first().selectOption(planId);
  await expect(page.getByText(line.line_no, { exact: false })).toBeVisible();

  await page.getByRole("combobox").nth(1).selectOption("SPLIT");
  await page.locator("label").filter({ hasText: line.line_no }).locator("input[type=checkbox]").check();
  await page.getByLabel("First split quantity").fill(first.toFixed(3));
  await page.getByLabel("Second split quantity").fill(second.toFixed(3));
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();

  const scenarioName = `M20-real-backend-${Date.now()}`;
  await page.getByPlaceholder("Scenario name *").fill(scenarioName);
  const post = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().includes(`/api/v1/mps/plans/${planId}/whatif`),
  );
  await page.getByRole("button", { name: "Compute Impact" }).click();
  const response = await post;
  expect(response.status()).toBe(201);
  const body = await response.json() as { id: string; changes: Array<{ change_type: string; new_value: { quantities: string[] } }> };
  console.log(`M20 persisted scenario id: ${body.id}`);
  expect(body.changes).toEqual([{ line_id: line.id, change_type: "SPLIT", new_value: { quantities: [first.toFixed(3), second.toFixed(3)] } }]);
  const savedScenario = page.locator("div.cursor-pointer").filter({ hasText: scenarioName });
  await expect(savedScenario).toBeVisible();

  await page.reload();
  await page.getByRole("combobox").first().selectOption(planId);
  await expect(savedScenario).toBeVisible();
  await expect(savedScenario).toContainText("SL: 100.0%");
  await expect(savedScenario).toContainText("Delays: 0");
  if (process.env.M20_EVIDENCE_DIR) {
    const screenshotPath = resolve(process.env.M20_EVIDENCE_DIR, "m20-scenario-backend-roundtrip.png");
    mkdirSync(dirname(screenshotPath), { recursive: true });
    await page.screenshot({
      path: screenshotPath,
      fullPage: true,
      mask: [page.getByText(/\S+@\S+\.\S+/)],
      maskColor: "#334155",
    });
  }
  await savedScenario.click();
  await expect(page.getByText(/Projected service level: 100\.0%/).last()).toBeVisible();
});
