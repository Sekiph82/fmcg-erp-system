import { expect, test, type Page, type Route } from "playwright/test";

// Synthetic route mocks only — no backend, database or real quality data.

const ALL = ["quality.view", "quality.create", "quality.edit", "quality.approve"];
const ID = (n: number) => `${String(n).repeat(8)}-0000-4000-8000-${String(n).repeat(12)}`.slice(0, 36);
const TEMPLATE_ID = ID(1);

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes = ALL) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-qa-user", email: "qa-governance@example.invalid", username: "synthetic-qa", full_name: "Synthetic QA",
    is_active: true, is_superuser: false, must_change_password: false, roles: [], permission_codes: permissionCodes,
    modules: ["quality"], scopes: [], feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, { permission_codes: [], visible_permission_codes: [] }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-qa-token", url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
}

type Calls = Array<{ method: string; path: string; body?: unknown; query: Record<string, string> }>;

async function installApi(page: Page, overrides: Record<string, (route: Route) => Promise<void>> = {}) {
  const calls: Calls = [];
  const state = {
    specs: [{
      id: ID(2), spec_code: "SYN-PH", version: 1, name: "Synthetic pH", scope_type: "PROCESS", product_id: null,
      material_id: null, process_stage: "MIXING", template_id: TEMPLATE_ID, status: "DRAFT", effective_from: "2026-11-10",
      effective_to: null, change_request_id: null, created_by_id: "someone-else", approved_by_id: null, approved_at: null,
    }],
    crs: [] as Array<Record<string, unknown>>,
    plans: [] as Array<Record<string, unknown>>,
    concessions: [{
      id: ID(3), concession_no: "CON-SYN-1", deviation_id: ID(4), lot_id: ID(5), quantity_limit: null, uom: null,
      conditions: null, status: "PENDING", valid_until: null, requested_by_id: "requester", decided_by_id: null, decided_at: null,
    }],
    samples: [{
      id: ID(6), sample_no: "RS-SYN-1", lot_id: ID(5), quantity: "3.000", quantity_remaining: "3.000", uom: "bottle",
      storage_location: "Retain room A", collected_on: "2026-11-01", retain_until: "2027-11-01", status: "STORED",
    }],
  };
  await page.route("**/api/v1/qms/templates**", (route) => fulfillJson(route, [{ id: TEMPLATE_ID, name: "Synthetic pH template", is_active: true }]));
  await page.route("**/api/v1/quality-enterprise/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace("/api/v1/quality-enterprise", "");
    const method = req.method();
    const body = method === "GET" ? undefined : req.postDataJSON();
    calls.push({ method, path, body, query: Object.fromEntries(url.searchParams) });
    const key = `${method} ${path}`;
    if (overrides[key]) return overrides[key](route);

    if (key === "GET /specifications") return fulfillJson(route, state.specs);
    if (key === "POST /specifications") {
      const created = { ...state.specs[0], ...(body as object), id: ID(7), version: 2, status: "DRAFT", created_by_id: "synthetic-qa-user" };
      state.specs.push(created);
      return fulfillJson(route, created, 201);
    }
    if (method === "POST" && path.endsWith("/approve") && path.startsWith("/specifications/")) {
      const spec = state.specs.find((s) => path.includes(s.id))!;
      spec.status = "APPROVED";
      return fulfillJson(route, spec);
    }
    if (key === "GET /change-requests") return fulfillJson(route, state.crs);
    if (key === "POST /change-requests") {
      const cr = { id: ID(8), cr_no: "QCR-SYN-1", status: "DRAFT", requested_by_id: "synthetic-qa-user", decided_by_id: null,
        decided_at: null, implemented_at: null, closed_at: null, target_reference: null, ...(body as object) };
      state.crs.push(cr);
      return fulfillJson(route, cr, 201);
    }
    if (method === "POST" && path.endsWith("/transition")) {
      const cr = state.crs[0];
      cr.status = (body as { status: string }).status;
      return fulfillJson(route, cr);
    }
    if (key === "GET /qc-plans") return fulfillJson(route, state.plans);
    if (key === "POST /qc-plans") {
      const plan = { id: ID(9), version: 1, status: "DRAFT", created_by_id: "synthetic-qa-user", approved_by_id: null,
        product_id: null, material_id: null, ...(body as object) };
      state.plans.push(plan);
      return fulfillJson(route, plan, 201);
    }
    if (method === "GET" && path.endsWith("/coverage")) {
      return fulfillJson(route, { complete: false, missing_steps: [2], failed_steps: [], steps: [
        { sequence: 1, qc_type: "INCOMING", qc_sub_type: null, is_mandatory: true, state: "SATISFIED" },
        { sequence: 2, qc_type: "FINISHED_GOODS", qc_sub_type: null, is_mandatory: true, state: "NOT_STARTED" },
      ] });
    }
    if (key === "POST /aql/evaluate") {
      return fulfillJson(route, { plan_id: ID(1), plan_code: "AQL-SYN", sample_size: 50, decision: "REJECT",
        acceptance_number: 2, rejection_number: 3, defects_found: 4 });
    }
    if (key === "GET /spc/chart") {
      const values = [10, 10.2, 9.8, 10.1, 9.9, 10, 14];
      return fulfillJson(route, {
        n: 7, limits: { center: 10.571, sigma: 0.768, ucl: 12.876, lcl: 8.266, mr_bar: 0.867, mr_ucl: 2.831 },
        capability: { pp: 0.73, ppk: 0.62 }, lsl: 5, usl: 15,
        violations: [{ index: 6, rule: "WE1_BEYOND_3_SIGMA", test_result_id: "r6", value: 14 }],
        points: values.map((v, i) => ({ test_result_id: `r${i}`, value: v, recorded_at: null })),
      });
    }
    if (key === "GET /concessions") return fulfillJson(route, state.concessions);
    if (method === "POST" && path.endsWith("/decide")) {
      const c = state.concessions[0];
      const b = body as { approve: boolean; conditions?: string; valid_until?: string };
      Object.assign(c, { status: b.approve ? "APPROVED" : "REJECTED", conditions: b.conditions ?? null, valid_until: b.valid_until ?? null });
      return fulfillJson(route, c);
    }
    if (key === "GET /quality-costs/summary") {
      return fulfillJson(route, { by_category: { PREVENTION: "100.00", APPRAISAL: "100.00", INTERNAL_FAILURE: "300.00",
        EXTERNAL_FAILURE: "500.00" }, by_risk_level: {}, cost_of_good_quality: "200.00", cost_of_poor_quality: "800.00",
        total: "1000.00", copq_share_pct: "80.00", currencies: ["KES", "USD"], mixed_currency: true });
    }
    if (key === "GET /retain-samples") return fulfillJson(route, state.samples);
    if (method === "POST" && path.endsWith("/withdraw")) {
      const s = state.samples[0];
      s.quantity_remaining = "2.000";
      return fulfillJson(route, s);
    }
    if (key === "GET /test-methods") return fulfillJson(route, []);
    return fulfillJson(route, []);
  });
  return calls;
}

const open = async (page: Page, section?: string) => {
  await page.goto("/dashboard/quality?tab=qa-governance");
  await expect(page.getByTestId("qa-enterprise-workspace")).toBeVisible();
  if (section) await page.getByRole("tab", { name: section }).click();
};

test.describe("M35 QA governance UI (mocked API)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("approver approves a draft specification and drives a change request", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page);
    await open(page);

    await expect(page.getByRole("cell", { name: "SYN-PH v1", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Approve SYN-PH v1" }).click();
    await expect(page.getByText("Specification SYN-PH v1 approved")).toBeVisible();

    await page.getByLabel("Spec code").fill("SYN-PH");
    await page.getByLabel("Spec name").fill("Synthetic pH v2");
    await page.getByLabel("Scope").selectOption("PROCESS");
    await page.getByLabel("Process stage").fill("MIXING");
    await page.getByLabel("Parameter template").selectOption(TEMPLATE_ID);
    await page.getByRole("button", { name: "Save draft specification" }).click();
    await expect(page.getByText("Specification SYN-PH v2 saved as draft")).toBeVisible();
    expect(calls.find((c) => c.method === "POST" && c.path === "/specifications")?.body).toMatchObject({
      spec_code: "SYN-PH", scope_type: "PROCESS", process_stage: "MIXING", template_id: TEMPLATE_ID,
    });

    await page.getByLabel("Change title").fill("Tighten pH");
    await page.getByLabel("Description").fill("Narrow the range");
    await page.getByLabel("Risk assessment").fill("Low");
    await page.getByRole("button", { name: "Create change request" }).click();
    await page.getByRole("button", { name: "Submit QCR-SYN-1" }).click();
    await expect(page.getByText("QCR-SYN-1 is now SUBMITTED")).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve QCR-SYN-1" })).toBeVisible();
  });

  test("server segregation-of-duties errors are shown to the user", async ({ page }) => {
    await signIn(page);
    await installApi(page, {
      "POST /specifications/22222222-0000-4000-8000-222222222222/approve": (route) =>
        fulfillJson(route, { detail: "The specification author cannot approve it." }, 409),
    });
    await open(page);
    await page.getByRole("button", { name: "Approve SYN-PH v1" }).click();
    await expect(page.getByText("The specification author cannot approve it.")).toBeVisible();
  });

  test("view-only user sees records but no create or approve controls", async ({ page }) => {
    await signIn(page, ["quality.view"]);
    await installApi(page);
    await open(page);
    await expect(page.getByRole("cell", { name: "SYN-PH v1", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve SYN-PH v1" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save draft specification" })).toHaveCount(0);
    await page.getByRole("tab", { name: "Concessions & cost" }).click();
    await expect(page.getByRole("button", { name: "Approve CON-SYN-1" })).toHaveCount(0);
  });

  test("QC plan is saved with ordered steps and coverage shows a missing step", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page);
    await open(page, "QC plans");
    await page.getByLabel("Plan code").fill("PLAN-SYN");
    await page.getByLabel("Plan name").fill("Synthetic juice plan");
    await page.getByLabel("Item ID").fill(ID(5));
    await page.getByRole("button", { name: "Add step" }).click();
    await page.getByRole("button", { name: "Save draft plan" }).click();
    await expect(page.getByText("QC plan PLAN-SYN v1 saved as draft")).toBeVisible();
    expect(calls.find((c) => c.method === "POST" && c.path === "/qc-plans")?.body).toMatchObject({
      plan_code: "PLAN-SYN", product_id: ID(5),
      steps: [{ sequence: 1, qc_type: "INCOMING", is_mandatory: true }, { sequence: 2, qc_type: "FINISHED_GOODS", is_mandatory: true }],
    });

    await page.getByLabel("Plan", { exact: true }).selectOption({ label: "PLAN-SYN v1 (DRAFT)" });
    await page.getByLabel("Reference ID").fill(ID(5));
    await page.getByRole("button", { name: "Check coverage" }).click();
    const coverage = page.getByTestId("plan-coverage");
    await expect(coverage.getByText("Incomplete")).toBeVisible();
    await expect(coverage.getByText("NOT STARTED")).toBeVisible();
  });

  test("AQL decision and SPC chart with a flagged point", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page);
    await open(page, "AQL & SPC");
    await page.getByLabel("Lot size").fill("800");
    await page.getByLabel("Units inspected").fill("50");
    await page.getByLabel("Defects found").fill("4");
    await page.getByRole("button", { name: "Evaluate lot" }).click();
    await expect(page.getByTestId("aql-result").getByText("REJECT")).toBeVisible();
    expect(calls.find((c) => c.path === "/aql/evaluate")?.body).toMatchObject({ lot_size: 800, sample_inspected: 50, defects_found: 4 });

    await page.getByLabel("Product ID").fill(ID(5));
    await page.getByLabel("Parameter name").fill("Brix");
    await page.getByRole("button", { name: "Show chart" }).click();
    const spc = page.getByTestId("spc-result");
    await expect(spc.getByRole("img", { name: /7 points, 1 rule hits/ })).toBeVisible();
    await expect(spc.getByText("Point 7 (14): WE1 BEYOND 3 SIGMA")).toBeVisible();
    await expect(spc.getByText("0.62")).toBeVisible();
  });

  test("concession approval requires conditions and sends an expiry", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page);
    await open(page, "Concessions & cost");
    const approve = page.getByRole("button", { name: "Approve CON-SYN-1" });
    await expect(approve).toBeDisabled();
    await page.getByLabel("Conditions for CON-SYN-1").fill("Industrial customers only");
    await approve.click();
    await expect(page.getByText("Concession CON-SYN-1 approved")).toBeVisible();
    const decide = calls.find((c) => c.path.endsWith("/decide"))?.body as { approve: boolean; conditions: string; valid_until: string };
    expect(decide.approve).toBe(true);
    expect(decide.conditions).toBe("Industrial customers only");
    expect(new Date(decide.valid_until).getTime()).toBeGreaterThan(Date.now());

    const summary = page.getByTestId("cost-summary");
    await expect(summary.getByText("800.00")).toBeVisible();
    await expect(page.getByRole("alert").filter({ hasText: "more than one currency" })).toBeVisible();
  });

  test("retain sample withdrawal, and early disposal blocked without approval", async ({ page }) => {
    await signIn(page, ["quality.view", "quality.edit"]);
    const calls = await installApi(page);
    await open(page, "Retain samples & methods");
    await page.getByLabel("Reason for RS-SYN-1").fill("Complaint investigation");
    await expect(page.getByRole("button", { name: "Dispose RS-SYN-1" })).toBeDisabled();
    await page.getByLabel("Withdraw quantity for RS-SYN-1").fill("1");
    await page.getByRole("button", { name: "Withdraw from RS-SYN-1" }).click();
    await expect(page.getByText("RS-SYN-1: 2.000 bottle remaining")).toBeVisible();
    expect(calls.find((c) => c.path.endsWith("/withdraw"))?.body).toEqual({ quantity: "1", reason: "Complaint investigation" });
    await expect(page.getByRole("button", { name: "Register sample" })).toHaveCount(0);
  });
});
