import { expect, test } from "playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

const planId = "11111111-1111-4111-8111-111111111111";
const lineOne = "22222222-2222-4222-8222-222222222222";
const lineTwo = "33333333-3333-4333-8333-333333333333";

async function openWhatIfBuilder(page: import("playwright/test").Page) {
  await page.route("**/api/v1/auth/me**", async (route) => route.fulfill({ json: {
    id: "synthetic-mps-scenario-user", email: "mps-scenario@example.invalid", username: "mps-scenario",
    full_name: "Synthetic MPS Scenario Tester", is_active: true, is_superuser: true,
    must_change_password: false, roles: [], permission_codes: ["mps:view", "mps:edit"], modules: ["mps"],
    scopes: [], feature_flags: {},
  } }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-mps-scenario-ui-token",
    url: process.env.E2E_BASE_URL || "http://localhost:3000", httpOnly: true, sameSite: "Lax",
  }]);
  const submitted: Array<{ changes: Array<{ line_id: string; change_type: string; new_value: unknown }> }> = [];
  await page.route("**/api/v1/mps/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() === "GET" && url.pathname === "/api/v1/mps/plans") {
      await route.fulfill({ json: [{
        id: planId, plan_no: "M20-E2E", plan_name: "M20 scenario UI", status: "DRAFT",
        planning_mode: "ASSISTED", capacity_mode: "FINITE", start_date: "2026-11-03", end_date: "2026-11-03",
        total_lines: 2, overloaded_lines: 0, feasible_lines: 0, created_at: "2026-10-21T00:00:00Z",
      }] });
      return;
    }
    if (request.method() === "GET" && url.pathname === `/api/v1/mps/plans/${planId}/lines`) {
      await route.fulfill({ json: [
        { id: lineOne, line_no: "LINE-1", product_id: "44444444-4444-4444-8444-444444444444", product_name: "Product A", period_label: "2026-11-03", period_start: "2026-11-03", period_end: "2026-11-03", feasibility_status: "PENDING", is_locked: false },
        { id: lineTwo, line_no: "LINE-2", product_id: "44444444-4444-4444-8444-444444444444", product_name: "Product A", period_label: "2026-11-03", period_start: "2026-11-03", period_end: "2026-11-03", feasibility_status: "PENDING", is_locked: false },
      ] });
      return;
    }
    if (request.method() === "POST" && url.pathname === `/api/v1/mps/plans/${planId}/whatif`) {
      submitted.push(request.postDataJSON());
      await route.fulfill({ json: {
        id: `scenario-${submitted.length}`, scenario_no: `WI-${submitted.length}`, scenario_name: "Scenario",
        mps_id: planId, description: null, changes: request.postDataJSON().changes,
        impact_service_level_pct: 100, impact_delay_count: 0, impact_cost_delta: null,
        impact_summary: "Scenario saved", status: "COMPUTED", created_by_id: null, created_at: "2026-10-21T00:00:00Z",
      } });
      return;
    }
    await route.fulfill({ status: 200, json: [] });
  });

  await page.goto("/dashboard/mps/whatif");
  await page.getByRole("combobox").first().selectOption(planId);
  return submitted;
}

test("what-if builder serializes merge inputs", async ({ page }) => {
  const submitted = await openWhatIfBuilder(page);
  await page.getByRole("combobox").nth(1).selectOption("MERGE");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByRole("combobox").nth(2).selectOption(lineTwo);
  await page.getByPlaceholder("Scenario name *").fill("Merge test");
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0].changes).toEqual([{ line_id: lineOne, change_type: "MERGE", new_value: lineTwo }]);
});

test("what-if builder serializes exact split quantities", async ({ page }) => {
  const submitted = await openWhatIfBuilder(page);
  await page.getByRole("combobox").nth(1).selectOption("SPLIT");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByLabel("First split quantity").fill("15.125");
  await page.getByLabel("Second split quantity").fill("24.875");
  await page.getByPlaceholder("Scenario name *").fill("Split test");
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0].changes).toEqual([{ line_id: lineOne, change_type: "SPLIT", new_value: { quantities: ["15.125", "24.875"] } }]);
});

test("what-if builder serializes a concrete non-overlapping shift interval", async ({ page }) => {
  const submitted = await openWhatIfBuilder(page);
  await page.getByRole("combobox").nth(1).selectOption("SHIFT_ADD");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByLabel("Shift date").fill("2026-11-03");
  await page.getByLabel("Additional shift start time").fill("16:00");
  await page.getByLabel("Additional shift end time").fill("18:00");
  await page.getByPlaceholder("Scenario name *").fill("Shift test");
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0].changes).toEqual([{ line_id: lineOne, change_type: "SHIFT_ADD", new_value: { date: "2026-11-03", start_time: "16:00", end_time: "18:00", hours: "2" } }]);
});
