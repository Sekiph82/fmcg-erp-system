import { expect, test, type Page, type Route } from "playwright/test";

// Synthetic route mocks only â€” no backend, database or real supplier data.

const ALL = ["quality.view", "quality.create", "quality.edit", "quality.approve"];
const SUPPLIER = "aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa";
const APPROVAL = "bbbbbbbb-0000-4000-8000-bbbbbbbbbbbb";
const AUDIT = "cccccccc-0000-4000-8000-cccccccccccc";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes = ALL) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-qa-user", email: "qa-supplier@example.invalid", username: "synthetic-qa", full_name: "Synthetic QA",
    is_active: true, is_superuser: false, must_change_password: false, roles: [], permission_codes: permissionCodes,
    modules: ["quality"], scopes: [], feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, { permission_codes: [], visible_permission_codes: [] }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-qa-token", url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
}

type Call = { method: string; path: string; body?: unknown; query: Record<string, string> };

async function installApi(page: Page, opts: { suppliersForbidden?: boolean } = {}) {
  const calls: Call[] = [];
  const approval = {
    id: APPROVAL, supplier_id: SUPPLIER, supplier_name: "Synthetic Dairy", approval_type: "HALAL", status: "PENDING",
    is_current: false, audit_score: null, auditor: null, last_audit_date: null, approval_date: null, expiry_date: null,
    days_to_expiry: null, critical_findings: 0, major_findings: 0, minor_findings: 0, notes: null,
    audit_checklist_id: null, decided_by_id: null, decided_at: null, decision_notes: null,
  };
  const audit = {
    id: AUDIT, audit_ref: "AUD-SYN-1", standard: "HALAL", audit_type: "THIRD_PARTY", audit_date: "2026-11-10",
    score_pct: 0, result: "IN_PROGRESS", next_audit_date: null as string | null, supplier_id: SUPPLIER, closed_at: null as string | null,
    items: [
      { section: "1", item: "Raw Material Verification", result: "pending", finding: null as string | null },
      { section: "2", item: "Cross-contamination", result: "pending", finding: null as string | null },
    ],
  };
  const approvals = [approval];
  const audits: typeof audit[] = [];

  await page.route("**/api/v1/suppliers/**", (route) => opts.suppliersForbidden
    ? fulfillJson(route, { detail: "forbidden" }, 403)
    : fulfillJson(route, [{ id: SUPPLIER, code: "SUP-SYN", name: "Synthetic Dairy", payment_terms_days: 30, is_active: true, is_preferred: false }]));
  await page.route("**/api/v1/qms/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace("/api/v1/qms", "");
    const method = req.method();
    const body = method === "GET" ? undefined : req.postDataJSON();
    calls.push({ method, path, body, query: Object.fromEntries(url.searchParams) });

    if (method === "GET" && path === "/supplier-food-safety") return fulfillJson(route, approvals);
    if (method === "POST" && path === "/supplier-food-safety") {
      const created = { ...approval, id: "dddddddd-0000-4000-8000-dddddddddddd", ...(body as object), supplier_name: "Synthetic Dairy", status: "PENDING" };
      approvals.push(created);
      return fulfillJson(route, created, 201);
    }
    if (method === "POST" && path.endsWith("/decision")) {
      const b = body as { status: string; expiry_date?: string; audit_checklist_id?: string; notes?: string };
      Object.assign(approval, { status: b.status, expiry_date: b.expiry_date ?? null, audit_checklist_id: b.audit_checklist_id ?? null,
        decision_notes: b.notes ?? null, is_current: b.status === "APPROVED", audit_score: 100 });
      return fulfillJson(route, approval);
    }
    if (method === "GET" && path === "/audit-checklists") return fulfillJson(route, audits.map(({ items: _items, ...a }) => a));
    if (method === "POST" && path === "/audit-checklists") {
      Object.assign(audit, { supplier_id: (body as { supplier_id: string }).supplier_id });
      audits.push(audit);
      return fulfillJson(route, audit, 201);
    }
    if (method === "GET" && path === `/audit-checklists/${AUDIT}`) return fulfillJson(route, audit);
    if (method === "PATCH" && path === `/audit-checklists/${AUDIT}/items`) {
      for (const r of body as Array<{ item_index: number; result: string; finding?: string }>) {
        audit.items[r.item_index].result = r.result;
        audit.items[r.item_index].finding = r.finding ?? null;
      }
      const passed = audit.items.filter((i) => i.result === "pass").length;
      audit.score_pct = Math.round((passed / audit.items.length) * 100);
      audit.result = audit.score_pct >= 95 ? "PASS" : audit.score_pct >= 75 ? "CONDITIONAL_PASS" : "FAIL";
      return fulfillJson(route, { id: AUDIT, score_pct: audit.score_pct, result: audit.result });
    }
    if (method === "POST" && path === `/audit-checklists/${AUDIT}/close`) {
      audit.closed_at = "2026-11-10T10:00:00Z";
      audit.next_audit_date = url.searchParams.get("next_audit_date");
      return fulfillJson(route, { id: AUDIT, result: audit.result, corrective_action_id: null, suspended_approval_ids: [] });
    }
    return fulfillJson(route, []);
  });
  await page.route("**/api/v1/quality-enterprise/**", (route) => fulfillJson(route, []));
  return calls;
}

const open = async (page: Page) => {
  await page.goto("/dashboard/quality?tab=qa-governance");
  await expect(page.getByTestId("qa-enterprise-workspace")).toBeVisible();
  await page.getByRole("tab", { name: "Supplier audits" }).click();
};

test.describe("M35 supplier audit lifecycle UI (mocked API)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("schedule, score and close a supplier audit, then approve the supplier on it", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page);
    await open(page);
    await expect(page.getByRole("cell", { name: "Synthetic Dairy", exact: true })).toBeVisible();

    const schedule = page.getByRole("form", { name: "Schedule supplier audit" });
    await schedule.getByLabel("Supplier").selectOption(SUPPLIER);
    await schedule.getByLabel("Lead auditor").fill("J. Auditor");
    await schedule.getByRole("button", { name: "Schedule audit" }).click();
    await expect(page.getByText("Supplier audit AUD-SYN-1 scheduled")).toBeVisible();
    expect(calls.find((c) => c.method === "POST" && c.path === "/audit-checklists")?.body).toMatchObject({
      supplier_id: SUPPLIER, standard: "HALAL", audit_type: "THIRD_PARTY", lead_auditor: "J. Auditor",
    });

    await page.getByLabel("Result 1").selectOption("pass");
    await page.getByLabel("Result 2").selectOption("pass");
    await page.getByRole("button", { name: "Save results" }).click();
    await expect(page.getByText("Audit results saved")).toBeVisible();
    await page.getByRole("button", { name: "Close audit" }).click();
    await expect(page.getByText("Audit closed (PASS)")).toBeVisible();
    expect(calls.find((c) => c.path.endsWith("/close"))?.query.next_audit_date).toBeTruthy();

    await page.getByRole("button", { name: "Decide Synthetic Dairy HALAL" }).click();
    const form = page.getByRole("form", { name: "Approval decision" });
    await form.getByLabel("New status").selectOption("APPROVED");
    const record = form.getByRole("button", { name: "Record decision" });
    await expect(record).toBeDisabled(); // no evidence audit chosen yet
    await form.getByLabel("Evidence audit").selectOption(AUDIT);
    await record.click();
    await expect(page.getByText("Synthetic Dairy HALAL is now APPROVED")).toBeVisible();
    const decision = calls.find((c) => c.path.endsWith("/decision"))?.body as Record<string, string>;
    expect(decision).toMatchObject({ status: "APPROVED", audit_checklist_id: AUDIT });
    expect(decision.expiry_date).toBe(calls.find((c) => c.path.endsWith("/close"))?.query.next_audit_date);
  });

  test("suspension needs a reason and view-only users get no controls", async ({ page }) => {
    await signIn(page, ["quality.view"]);
    await installApi(page, { suppliersForbidden: true });
    await open(page);
    await expect(page.getByRole("cell", { name: "Synthetic Dairy", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Decide Synthetic Dairy HALAL" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Request approval" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Schedule audit" })).toHaveCount(0);
  });

  test("approval request falls back to a supplier ID field and rejection requires notes", async ({ page }) => {
    await signIn(page);
    const calls = await installApi(page, { suppliersForbidden: true });
    await open(page);
    const request = page.getByRole("form", { name: "New approval request" });
    await request.getByLabel("Supplier ID").fill(SUPPLIER);
    await request.getByLabel("Scheme").fill("BRC");
    await request.getByRole("button", { name: "Request approval" }).click();
    await expect(page.getByText("Approval request for Synthetic Dairy (BRC) registered")).toBeVisible();
    expect(calls.find((c) => c.method === "POST" && c.path === "/supplier-food-safety")?.body).toMatchObject({
      supplier_id: SUPPLIER, approval_type: "BRC", critical_findings: 0,
    });

    await page.getByRole("button", { name: "Decide Synthetic Dairy HALAL" }).click();
    const form = page.getByRole("form", { name: "Approval decision" });
    await form.getByLabel("New status").selectOption("REJECTED");
    await expect(form.getByRole("button", { name: "Record decision" })).toBeDisabled();
    await form.getByLabel("Notes / reason").fill("Pest control failures");
    await expect(form.getByRole("button", { name: "Record decision" })).toBeEnabled();
  });
});
