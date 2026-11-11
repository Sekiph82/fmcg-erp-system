import { expect, test, type Page, type Route } from "playwright/test";

// Synthetic route mocks only — no backend, database or real bank data.

const ACCOUNT = "eeeeeeee-0000-4000-8000-eeeeeeeeeeee";
const STATEMENT = "ffffffff-0000-4000-8000-ffffffffffff";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function setup(page: Page, importStatus: number) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-finance-user", email: "finance@example.invalid", username: "synthetic-finance",
    full_name: "Synthetic Finance", is_active: true, is_superuser: false, must_change_password: false, roles: [],
    permission_codes: ["finance.view", "finance.edit"], modules: ["finance"], scopes: [], feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, { permission_codes: [], visible_permission_codes: [] }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-finance-token", url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
  const uploads: Array<{ contentType: string; body: string }> = [];
  await page.route("**/api/v1/bank-reconciliation/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith("/accounts")) {
      return fulfillJson(route, [{ id: ACCOUNT, bank_name: "Synthetic Bank", account_name: "Operating", currency: "KES",
        account_number_masked: "****5678", active: true }]);
    }
    if (path.endsWith("/statements/import-file")) {
      uploads.push({ contentType: req.headers()["content-type"] ?? "", body: req.postData() ?? "" });
      return importStatus === 201
        ? fulfillJson(route, { id: STATEMENT, statement_no: "BRS-SYN-1", status: "IMPORTED" }, 201)
        : fulfillJson(route, { detail: "Statement does not balance: opening 100000 + credits 20000.5 - debits 7500 = 112500.5, but closing is 112600.5." }, 422);
    }
    if (path.endsWith(`/statements/${STATEMENT}`)) {
      return fulfillJson(route, { id: STATEMENT, statement_no: "BRS-SYN-1", status: "IMPORTED", bank_account_id: ACCOUNT,
        statement_currency: "KES", opening_balance: 100000, closing_balance: 120000.5, total_lines: 1,
        total_credits: 20000.5, total_debits: 0, period_start_date: "2026-10-01", period_end_date: "2026-10-31" });
    }
    return fulfillJson(route, []);
  });
  return uploads;
}

const MT940 = ":20:STMT\n:25:0110012345678\n:60F:C261001KES100000,00\n:61:2610051005C20000,50NTRFREF//B1\n:62F:C261031KES120000,50\n";

test.describe("M17 bank statement file upload (mocked API)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("uploads an MT940 file as multipart and opens the imported statement", async ({ page }) => {
    const uploads = await setup(page, 201);
    await page.goto("/dashboard/bank-reconciliation/import");
    const form = page.getByRole("form", { name: "Upload bank statement file" });
    await form.getByLabel("Bank Account *").selectOption(ACCOUNT);
    await form.getByLabel("File format").selectOption("MT940");
    await form.getByLabel("Statement file *").setInputFiles({ name: "oct.sta", mimeType: "text/plain", buffer: Buffer.from(MT940) });
    await form.getByRole("button", { name: "Import file" }).click();
    // first visit compiles the detail route on the dev server
    await expect(page).toHaveURL(new RegExp(`/dashboard/bank-reconciliation/statements/${STATEMENT}`), { timeout: 30_000 });
    await expect(page.getByText("BRS-SYN-1").first()).toBeVisible(); // detail page renders, not redirected away
    expect(uploads).toHaveLength(1);
    expect(uploads[0].contentType).toContain("multipart/form-data");
    expect(uploads[0].body).toContain('name="file_format"');
    expect(uploads[0].body).toContain("MT940");
    expect(uploads[0].body).toContain(ACCOUNT);
    expect(uploads[0].body).toContain(":60F:C261001KES100000,00");
  });

  test("shows the server's balance check message when the file does not balance", async ({ page }) => {
    await setup(page, 422);
    await page.goto("/dashboard/bank-reconciliation/import");
    const form = page.getByRole("form", { name: "Upload bank statement file" });
    await expect(form.getByRole("button", { name: "Import file" })).toBeDisabled();
    await form.getByLabel("Bank Account *").selectOption(ACCOUNT);
    await form.getByLabel("Statement file *").setInputFiles({ name: "bad.xml", mimeType: "text/xml", buffer: Buffer.from("<Document/>") });
    await form.getByRole("button", { name: "Import file" }).click();
    await expect(page.getByText(/Statement does not balance/)).toBeVisible();
  });
});
