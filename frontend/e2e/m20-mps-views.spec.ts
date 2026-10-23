import { expect, test, type Page, type Route } from "playwright/test";

const planId = "11111111-1111-4111-8111-111111111111";
const lineId = "22222222-2222-4222-8222-222222222222";
const plan = {
  id: planId, plan_no: "M20-VIEW-PLAN", plan_name: "Synthetic MPS view plan", status: "DRAFT",
  planning_mode: "ASSISTED", capacity_mode: "FINITE", start_date: "2026-11-03", end_date: "2026-11-04",
  total_lines: 1, overloaded_lines: 0, feasible_lines: 1, created_at: "2026-10-21T00:00:00Z",
};
const line = {
  id: lineId, line_no: "LINE-001", mps_id: planId, product_id: "33333333-3333-4333-8333-333333333333",
  product_name: "Synthetic Juice", period_label: "2026-11-03", period_start: "2026-11-03", period_end: "2026-11-03",
  net_requirement_qty: 50, planned_production_qty: 50, priority_score: 80, feasibility_status: "FEASIBLE",
  is_locked: false, required_hours: 2, campaign_id: "44444444-4444-4444-8444-444444444444",
};

async function signIn(page: Page, options: {
  isSuperuser?: boolean;
  permissionCodes?: string[];
  scopes?: Array<Record<string, unknown>>;
} = {}) {
  const { isSuperuser = true, permissionCodes = [], scopes = [] } = options;
  await page.route("**/api/v1/auth/me", async (route) => fulfillJson(route, {
    id: "test-user", email: "mps-view-test@example.invalid", username: "mps-view-test",
    full_name: "Synthetic MPS View Tester", is_active: true, is_superuser: isSuperuser,
    must_change_password: false, roles: [], permission_codes: permissionCodes, modules: ["mps"],
    scopes, feature_flags: {},
  }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-mps-view-test-token",
    url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installApi(page: Page, handler: (route: Route, pathname: string) => Promise<void>) {
  await page.route("**/api/v1/mps/**", async (route) => {
    await handler(route, new URL(route.request().url()).pathname);
  });
}

test.describe("MPS planning views", () => {
  test.use({ storageState: { cookies: [], origins: [] } });
  test("planning board announces loading and renders the plan's line", async ({ page }) => {
    await signIn(page);
    let releaseLines!: () => void;
    const linesGate = new Promise<void>((resolve) => { releaseLines = resolve; });
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) {
        await linesGate;
        return fulfillJson(route, [line]);
      }
      return fulfillJson(route, []);
    });

    await page.goto("/dashboard/mps/planning-board");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("status").filter({ hasText: "Loading lines" })).toBeVisible();
    releaseLines();
    await expect(page.getByText("LINE-001")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Planned Qty" })).toBeVisible();
  });

  test("planning board shows an empty state when a plan has no lines", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) {
        return fulfillJson(route, []);
      }
      return fulfillJson(route, []);
    });

    await page.goto("/dashboard/mps/planning-board");
    const planSelector = page.getByLabel("Select Plan:");
    await planSelector.selectOption(planId);
    await expect(page.getByText("No lines yet. Generate from MRP to populate.")).toBeVisible();
  });

  test("planning board reports denied access to plan lines", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, { detail: "Access denied" }, 403);
      return fulfillJson(route, []);
    });
    await page.goto("/dashboard/mps/planning-board");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("alert").filter({ hasText: "Could not load plan lines" })).toBeVisible();
  });

  test("capacity heatmap renders utilization", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/capacity-heatmap`) {
        return fulfillJson(route, {
              mps_id: planId,
              rows: [{
                work_center_id: "wc-1", work_center_name: "Filling Line 1", peak_utilization_pct: 80,
                overloaded_days: 0,
                slots: [{ id: "slot-1", work_center_id: "wc-1", slot_date: "2026-11-03", available_hours: 8,
                  allocated_hours: 6.4, downtime_hours: 0, overload_hours: 0, utilization_pct: 80, is_overloaded: false }],
              }],
              overload_alerts: [],
          });
      }
      return fulfillJson(route, {});
    });

    await page.goto("/dashboard/mps/capacity");
    const planSelector = page.getByLabel("Select Plan:");
    await planSelector.selectOption(planId);
    await expect(page.getByText("Filling Line 1")).toBeVisible();
    await expect(page.getByText("80%", { exact: true }).first()).toBeVisible();
  });

  test("capacity page reports denied access to heatmap data", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/capacity-heatmap`) return fulfillJson(route, { detail: "Access denied" }, 403);
      return fulfillJson(route, {});
    });
    await page.goto("/dashboard/mps/capacity");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("alert").filter({ hasText: "Could not load capacity data" })).toBeVisible();
  });

  test("campaign page renders campaign details", async ({ page }) => {
    await signIn(page);
    let releaseCampaigns!: () => void;
    const campaignGate = new Promise<void>((resolve) => { releaseCampaigns = resolve; });
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/campaigns`) {
        await campaignGate;
        return fulfillJson(route, [{
          id: "44444444-4444-4444-8444-444444444444", campaign_code: "CMP-001", campaign_name: "Citrus run",
          mps_id: planId, work_center_id: "wc-1", campaign_start: "2026-11-03", campaign_end: "2026-11-03",
          total_production_hrs: 2, total_changeover_hrs: 0.5, sequence_order: 1, sku_count: 1,
        }]);
      }
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      return fulfillJson(route, {});
    });

    await page.goto("/dashboard/mps/campaigns");
    const planSelector = page.getByLabel("Select Plan:");
    await planSelector.selectOption(planId);
    await expect(page.getByRole("status").filter({ hasText: "Loading campaign data" })).toBeVisible();
    releaseCampaigns();
    await expect(page.getByText("Citrus run")).toBeVisible();
    await expect(page.getByText("Campaign Efficiency")).toBeVisible();
  });

  test("campaign page presents an empty state", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/campaigns`) return fulfillJson(route, []);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      return fulfillJson(route, {});
    });
    await page.goto("/dashboard/mps/campaigns");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByText("No campaigns yet. Run campaign grouping to group SKUs automatically.")).toBeVisible();
  });

  test("campaign page reports denied access", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/campaigns`) return fulfillJson(route, { detail: "Access denied" }, 403);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      return fulfillJson(route, {});
    });
    await page.goto("/dashboard/mps/campaigns");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("alert").filter({ hasText: "Could not load campaigns" })).toBeVisible();
  });

  test("what-if page presents an empty state for scenarios", async ({ page }) => {
    await signIn(page);
    let releaseScenarios!: () => void;
    const scenariosGate = new Promise<void>((resolve) => { releaseScenarios = resolve; });
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      if (pathname === `/api/v1/mps/plans/${planId}/whatif`) {
        await scenariosGate;
        return fulfillJson(route, []);
      }
      return fulfillJson(route, {});
    });

    await page.goto("/dashboard/mps/whatif");
    const planSelector = page.getByLabel("Select MPS plan");
    await planSelector.selectOption(planId);
    await expect(page.getByRole("status").filter({ hasText: "Loading scenarios" })).toBeVisible();
    releaseScenarios();
    await expect(page.getByText("No scenarios yet")).toBeVisible();
  });

  test("what-if page reports denied access to scenarios", async ({ page }) => {
    await signIn(page);
    await installApi(page, async (route, pathname) => {
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      if (pathname === `/api/v1/mps/plans/${planId}/whatif`) return fulfillJson(route, { detail: "Access denied" }, 403);
      return fulfillJson(route, {});
    });
    await page.goto("/dashboard/mps/whatif");
    await page.getByLabel("Select MPS plan").selectOption(planId);
    await expect(page.getByRole("alert").filter({ hasText: "Could not load scenarios" })).toBeVisible();
  });

  test("view-only users do not see MPS mutation controls", async ({ page }) => {
    await signIn(page, {
      isSuperuser: false,
      permissionCodes: ["mps.view"],
      scopes: [{
        scope_type: "warehouse", scope_id: "warehouse-view-only", scope_name: "Synthetic MPS View Warehouse",
        can_view: true, can_create: false, can_edit: false, can_delete: false, can_approve: false,
        can_post: false, can_release: false, can_cancel: false, can_export: false, can_import: false,
        can_transfer: false, can_adjust: false, can_receive: false, can_dispatch: false,
        is_active: true, source: "user",
      }],
    });
    await page.route("**/api/v1/mps/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      if (pathname.endsWith("/capacity-heatmap")) return fulfillJson(route, { mps_id: planId, rows: [], overload_alerts: [] });
      if (pathname.endsWith("/campaigns") || pathname.endsWith("/whatif")) return fulfillJson(route, []);
      return fulfillJson(route, {});
    });

    await page.goto("/dashboard/mps/planning-board");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("button", { name: "Generate from MRP" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Run Capacity" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Group Campaigns" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Run AI" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Approve Plan" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Edit", exact: true })).toHaveCount(0);

    await page.goto("/dashboard/mps/capacity");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("button", { name: "Re-run Capacity Scheduling" })).toHaveCount(0);

    await page.goto("/dashboard/mps/campaigns");
    await page.getByLabel("Select Plan:").selectOption(planId);
    await expect(page.getByRole("button", { name: "Re-run Campaign Grouping" })).toHaveCount(0);

    await page.goto("/dashboard/mps/whatif");
    await page.getByLabel("Select MPS plan").selectOption(planId);
    await expect(page.getByRole("heading", { name: "Build Scenario" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Compute Impact" })).toHaveCount(0);
  });

  test("what-if comparison errors are announced to assistive technology", async ({ page }) => {
    await signIn(page);
    await page.route("**/api/v1/mps/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === "/api/v1/mps/plans") return fulfillJson(route, [plan]);
      if (pathname === `/api/v1/mps/plans/${planId}/lines`) return fulfillJson(route, [line]);
      if (pathname === `/api/v1/mps/plans/${planId}/whatif`) return fulfillJson(route, [
        { id: "baseline", scenario_name: "Baseline", scenario_no: "WI-0001", mps_id: planId, changes: [], status: "COMPUTED", created_at: "2026-10-21T00:00:00Z" },
        { id: "candidate", scenario_name: "Candidate", scenario_no: "WI-0002", mps_id: planId, changes: [], status: "COMPUTED", created_at: "2026-10-21T00:00:00Z" },
      ]);
      if (pathname === `/api/v1/mps/plans/${planId}/scenario-comparison`) return fulfillJson(route, { detail: "Access denied" }, 403);
      return fulfillJson(route, {});
    });
    await page.goto("/dashboard/mps/whatif");
    await page.getByLabel("Select MPS plan").selectOption(planId);
    await page.getByLabel("Baseline scenario").selectOption("baseline");
    await page.getByLabel("Candidate scenario").selectOption("candidate");
    await page.getByRole("button", { name: "Compare" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "status code 403" })).toBeVisible();
  });
});
