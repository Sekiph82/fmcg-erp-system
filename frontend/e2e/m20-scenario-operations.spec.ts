import { expect, test } from "playwright/test";

const planId = "11111111-1111-4111-8111-111111111111";
const lineOne = "22222222-2222-4222-8222-222222222222";
const lineTwo = "33333333-3333-4333-8333-333333333333";

test("what-if builder serializes merge, exact split, and added shift inputs", async ({ page }) => {
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

  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await page.goto("/dashboard/mps/whatif");
  await page.getByRole("combobox").first().selectOption(planId);

  await page.getByRole("combobox").nth(1).selectOption("MERGE");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByRole("combobox").nth(2).selectOption(lineTwo);
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByPlaceholder("Scenario name *").fill("Merge test");
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(1);
  expect(submitted[0].changes).toEqual([{ line_id: lineOne, change_type: "MERGE", new_value: lineTwo }]);

  await page.getByRole("combobox").nth(1).selectOption("SPLIT");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByLabel("First split quantity").fill("15.125");
  await page.getByLabel("Second split quantity").fill("24.875");
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByPlaceholder("Scenario name *").fill("Split test");
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(2);
  expect(submitted[1].changes).toEqual([{ line_id: lineOne, change_type: "SPLIT", new_value: { quantities: ["15.125", "24.875"] } }]);

  await page.getByRole("combobox").nth(1).selectOption("SHIFT_ADD");
  await page.locator("label").filter({ hasText: "LINE-1 · 2026-11-03" }).locator("input[type=checkbox]").check();
  await page.getByLabel("Shift date").fill("2026-11-03");
  await page.getByLabel("Additional shift hours").fill("2");
  await page.getByRole("button", { name: "Add Change to Scenario" }).click();
  await page.getByPlaceholder("Scenario name *").fill("Shift test");
  await page.getByRole("button", { name: "Compute Impact" }).click();
  await expect.poll(() => submitted.length).toBe(3);
  expect(submitted[2].changes).toEqual([{ line_id: lineOne, change_type: "SHIFT_ADD", new_value: { date: "2026-11-03", hours: "2" } }]);
});
