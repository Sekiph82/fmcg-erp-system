import { expect, test, type Page, type Route } from "playwright/test";

// Synthetic route mocks only — no backend and no physical printer.

const PRINTER = "abababab-0000-4000-8000-abababababab";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-label-user", email: "labels@example.invalid", username: "synthetic-labels",
    full_name: "Synthetic Labels", is_active: true, is_superuser: true, must_change_password: false, roles: [],
    permission_codes: ["gs1.view", "gs1.print", "gs1.admin"], modules: ["gs1", "compliance"], scopes: [], feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, { permission_codes: [], visible_permission_codes: [] }));
  await page.context().addCookies([{
    name: "erp_access_token", value: "synthetic-labels-token", url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true, sameSite: "Lax",
  }]);
  const printers: Array<Record<string, unknown>> = [];
  const calls: Array<{ method: string; path: string; body: unknown }> = [];
  await page.route("**/api/v1/gs1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.replace("/api/v1/gs1", "");
    const body = req.method() === "GET" ? undefined : req.postDataJSON();
    calls.push({ method: req.method(), path, body });
    if (path === "/printers" && req.method() === "GET") return fulfillJson(route, printers);
    if (path === "/printers" && req.method() === "POST") {
      const created = { id: PRINTER, ...(body as object), location: null, is_active: true };
      printers.push(created);
      return fulfillJson(route, created, 201);
    }
    if (path === `/printers/${PRINTER}/test`) {
      return fulfillJson(route, { detail: "Cannot connect to printer 192.168.1.50:9100: timeout" }, 502);
    }
    if (path === "/dashboard") {
      return fulfillJson(route, { total_products_configured: 0, total_gtins: 0, total_barcodes_generated: 0,
        total_labels_printed: 0, total_sscc_pallets: 0, active_sscc_pallets: 0, total_print_jobs: 0,
        pending_print_jobs: 0, total_label_templates: 0, ai_recommendations_pending: 0, recent_barcodes: [], recent_sscc: [] });
    }
    return fulfillJson(route, []);
  });
  await page.route("**/api/v1/products**", (route) => fulfillJson(route, []));
  return calls;
}

test.describe("M17 network label printers (mocked API)", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("registers a ZPL printer, offers it as a print target and surfaces printer errors", async ({ page }) => {
    const calls = await setup(page);
    await page.goto("/dashboard/compliance?tab=gs1");
    const section = page.getByRole("region", { name: "Network label printers" });
    await expect(section.getByText("No network printers registered.")).toBeVisible({ timeout: 30_000 });

    await section.getByLabel("Printer name").fill("Line 1 Zebra");
    await section.getByLabel("Printer host").fill("192.168.1.50");
    await section.getByRole("button", { name: "Add printer" }).click();
    await expect(section.getByText("Printer Line 1 Zebra registered.")).toBeVisible();
    expect(calls.find((c) => c.method === "POST" && c.path === "/printers")?.body).toMatchObject({
      name: "Line 1 Zebra", protocol: "ZPL", host: "192.168.1.50", port: 9100,
    });

    await page.getByRole("button", { name: "Generate Label" }).click();
    await expect(page.getByLabel("Send to")).toContainText("Line 1 Zebra — ZPL 192.168.1.50:9100");

    await section.getByRole("button", { name: "Test Line 1 Zebra" }).click();
    await expect(section.getByText(/Cannot connect to printer 192.168.1.50:9100/)).toBeVisible();
  });
});
