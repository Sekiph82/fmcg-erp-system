import { expect, test, type Page, type Route } from "playwright/test";

const gateId = "11111111-1111-4111-8111-111111111111";
const templateId = "22222222-2222-4222-8222-222222222222";
const auditId = "33333333-3333-4333-8333-333333333333";

const definition = {
  id: gateId,
  code: "SYN_RECEIVING_GATE",
  name: "Synthetic receiving quality gate",
  gate_type: "INCOMING_QUALITY",
  trigger_event: "ON_RECEIPT",
  target_module: "procurement",
  description: "Synthetic UI acceptance data",
  is_active: true,
  version: 1,
  effective_from: "2026-10-29",
  effective_to: null,
  severity: "HIGH",
  is_mandatory: true,
  waiver_allowed: false,
  waiver_reason_required: true,
  waiver_approval_required: true,
  required_template_ids: [templateId],
  required_templates: [{ id: templateId, name: "Synthetic incoming template" }],
  created_at: "2026-10-29T10:00:00Z",
  updated_at: "2026-10-29T10:00:00Z",
};

const template = {
  id: templateId,
  name: "Synthetic incoming template",
  qc_type: "INCOMING",
  is_active: true,
  is_mandatory: true,
  blocks_progression: true,
  release_required: true,
  parameters: [{
    id: "44444444-4444-4444-8444-444444444444",
    parameter_name: "Synthetic acidity",
    parameter_type: "NUMERIC",
    target_value: "5",
    min_value: 4,
    max_value: 6,
  }],
};

const auditEvent = {
  id: auditId,
  evaluation_id: "55555555-5555-4555-8555-555555555555",
  target_module: "procurement",
  trigger_event: "ON_RECEIPT",
  gate_definition_id: gateId,
  gate_code: "SYN_RECEIVING_GATE",
  gate_version: 1,
  scope_type: "GRN_LINE",
  scope_id: "66666666-6666-4666-8666-666666666666",
  business_type: "GOODS_RECEIPT",
  business_id: "77777777-7777-4777-8777-777777777777",
  required_template_name: "Synthetic incoming template",
  result: "BLOCKED",
  evaluated_by_id: "88888888-8888-4888-8888-888888888888",
  reason: "Required incoming inspection is unresolved.",
  evaluated_at: "2026-10-29T10:05:00Z",
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes = ["quality.view", "quality.gate_configure"]) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-quality-user",
    email: "quality-gates@example.invalid",
    username: "synthetic-quality-gates",
    full_name: "Synthetic Quality Tester",
    is_active: true,
    is_superuser: false,
    must_change_password: false,
    roles: [],
    permission_codes: permissionCodes,
    modules: ["quality"],
    scopes: [],
    feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, {
    permission_codes: [],
    visible_permission_codes: [],
  }));
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-quality-gates-token",
    url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true,
    sameSite: "Lax",
  }]);
}

async function installQualityGateApi(page: Page, onCreate?: (body: Record<string, unknown>) => void) {
  const definitions = [{ ...definition }];
  await page.route("**/api/v1/qms/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/qms/gate-definitions" && request.method() === "GET") {
      return fulfillJson(route, definitions);
    }
    if (url.pathname === "/api/v1/qms/gate-definitions" && request.method() === "POST") {
      const body = request.postDataJSON() as Record<string, unknown>;
      onCreate?.(body);
      const created = {
        ...definition,
        id: "99999999-9999-4999-8999-999999999999",
        ...body,
        required_templates: [template],
        created_at: "2026-10-29T10:00:00Z",
        updated_at: "2026-10-29T10:00:00Z",
      };
      definitions.push(created as typeof definition);
      return fulfillJson(route, created, 201);
    }
    if (url.pathname.startsWith("/api/v1/qms/gate-definitions/") && request.method() === "PATCH") {
      const id = url.pathname.split("/").at(-1);
      const body = request.postDataJSON() as Record<string, unknown>;
      const index = definitions.findIndex((item) => item.id === id);
      const updated = { ...definitions[index], ...body };
      if (index >= 0) definitions[index] = updated as typeof definition;
      return fulfillJson(route, updated);
    }
    if (url.pathname === "/api/v1/qms/gate-audit-history") {
      const result = url.searchParams.get("result");
      return fulfillJson(route, !result || result === "BLOCKED" ? [auditEvent] : []);
    }
    if (url.pathname === "/api/v1/qms/templates") return fulfillJson(route, [template]);
    return fulfillJson(route, []);
  });
}

test.describe("Quality gate UI acceptance", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("authorized quality user can review definitions and blocked evaluation history", async ({ page }) => {
    await signIn(page);
    await installQualityGateApi(page);

    await page.goto("/dashboard/quality?tab=gates");

    await expect(page.getByTestId("quality-gate-workspace")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Quality gate definitions" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "SYN_RECEIVING_GATE v1", exact: true })).toBeVisible();
    await expect(page.getByText("Synthetic incoming template").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent gate evaluations" })).toBeVisible();
    await expect(page.getByText("Required incoming inspection is unresolved.")).toBeVisible();
    await expect(page.getByRole("cell", { name: "88888888-8888-4888-8888-888888888888", exact: true })).toBeVisible();

    await page.getByLabel("Filter audit outcome").selectOption("PASS");
    await expect(page.getByText("No evaluations match this outcome.")).toBeVisible();
  });

  test("gate configurator creates a version only with a specification-backed template", async ({ page }) => {
    await signIn(page);
    let createdBody: Record<string, unknown> | undefined;
    await installQualityGateApi(page, (body) => { createdBody = body; });

    await page.goto("/dashboard/quality?tab=gates");
    await page.getByRole("button", { name: "Create gate definition" }).click();
    await page.getByLabel("Gate code").fill("SYN_UI_GATE");
    await page.getByLabel("Name", { exact: true }).fill("Synthetic UI gate");
    await page.getByLabel("Required template: Synthetic incoming template").check();
    await page.getByRole("button", { name: "Save gate definition" }).click();

    await expect(page.getByText("Gate definition created")).toBeVisible();
    expect(createdBody).toMatchObject({
      code: "SYN_UI_GATE",
      name: "Synthetic UI gate",
      gate_type: "INCOMING_QUALITY",
      target_module: "procurement",
      trigger_event: "ON_RECEIPT",
      version: 1,
      is_active: true,
      is_mandatory: true,
      required_template_ids: [templateId],
    });
  });

  test("gate configurator closes an effective period before creating the next sequential version", async ({ page }) => {
    await signIn(page);
    let createdBody: Record<string, unknown> | undefined;
    await installQualityGateApi(page, (body) => { createdBody = body; });

    await page.goto("/dashboard/quality?tab=gates");
    await page.getByRole("button", { name: "Close version" }).click();
    await expect(page.getByText("Gate version closed")).toBeVisible();
    await page.getByRole("button", { name: "Create gate definition" }).click();
    await page.getByLabel("Gate code").fill("SYN_RECEIVING_GATE");
    await page.getByLabel("Name", { exact: true }).fill("Synthetic next gate version");
    await page.getByLabel("Required template: Synthetic incoming template").check();
    await page.getByRole("button", { name: "Save gate definition" }).click();

    await expect(page.getByText("Gate definition created")).toBeVisible();
    expect(createdBody).toMatchObject({
      code: "SYN_RECEIVING_GATE",
      version: 2,
      required_template_ids: [templateId],
    });
    expect(String(createdBody?.effective_from) > (definition.effective_to ?? "2026-10-29")).toBe(true);
  });

  test("quality-view user can review audit history but cannot read or configure gate definitions", async ({ page }) => {
    await signIn(page, ["quality.view"]);
    let definitionRequests = 0;
    await page.route("**/api/v1/qms/gate-definitions**", async (route) => {
      definitionRequests += 1;
      return fulfillJson(route, { detail: "Quality gate configuration permission is required." }, 403);
    });
    await page.route("**/api/v1/qms/gate-audit-history**", async (route) => fulfillJson(route, [auditEvent]));

    await page.goto("/dashboard/quality?tab=gates");

    await expect(page.getByRole("status").filter({ hasText: "Gate definition details require quality.view_all" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create gate definition" })).toHaveCount(0);
    await expect(page.getByText("Required incoming inspection is unresolved.")).toBeVisible();
    expect(definitionRequests).toBe(0);
  });
});
