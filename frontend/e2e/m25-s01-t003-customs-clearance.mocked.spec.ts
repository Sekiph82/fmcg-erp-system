import { expect, test, type Page, type Route } from "playwright/test";

const shipmentId = "11111111-1111-4111-8111-111111111111";
const clearanceId = "22222222-2222-4222-8222-222222222222";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes: string[]) {
  await page.route("**/api/v1/**", (route) => fulfillJson(route, { detail: "Unmocked synthetic API request" }, 404));
  await page.route("**/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-m25-customs-user",
    email: "m25-customs@example.invalid",
    username: "synthetic-m25-customs",
    full_name: "Synthetic Clearance Operator",
    is_active: true,
    is_superuser: false,
    must_change_password: false,
    roles: [],
    permission_codes: permissionCodes,
    modules: ["logistics"],
    scopes: [],
    feature_flags: {},
  }));
  await page.route("**/api/v1/modules/manifest", (route) => fulfillJson(route, {
    permission_codes: permissionCodes,
    visible_permission_codes: permissionCodes,
  }));
  const testOrigin = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  await page.context().clearCookies({ name: "erp_access_token" });
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-m25-customs-token",
    domain: testOrigin.hostname,
    path: "/",
    httpOnly: true,
    sameSite: "Lax",
  }]);
  expect((await page.context().cookies(testOrigin.origin)).some((cookie) => cookie.name === "erp_access_token")).toBeTruthy();
}

test("records evidence-linked customs status changes and shows the audit timeline", async ({ page }) => {
  await signIn(page, ["logistics.view", "logistics.create", "logistics.edit"]);
  const shipment = {
    id: shipmentId,
    shipment_no: "SYN-M25-CLEARANCE-001",
    mode: "SEA",
    origin_country: "Turkey",
    origin_city: "Istanbul",
    origin_port: "Synthetic origin port",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Synthetic destination port",
    carrier: "Synthetic carrier",
    status: "ARRIVED_PORT",
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
  };
  const clearance = {
    id: clearanceId,
    shipment_id: shipmentId,
    status: "PENDING",
    entry_no: "SYN-IDF-0001",
    created_at: "2026-10-29T08:00:00Z",
  };
  const events: Array<Record<string, unknown>> = [];
  let currentStatus = "PENDING";

  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{ ...shipment, status: shipment.status }]));
  await page.route("**/api/v1/logistics/arrivals/alerts**", (route) => fulfillJson(route, []));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/arrival`, (route) => fulfillJson(route, {
    id: "33333333-3333-4333-8333-333333333333",
    shipment_id: shipmentId,
    ata: "2026-10-29",
    created_at: "2026-10-29T08:00:00Z",
  }));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/clearance`, async (route) => {
    if (route.request().method() === "GET") return fulfillJson(route, { ...clearance, status: currentStatus });
    const body = route.request().postDataJSON() as Record<string, unknown>;
    return fulfillJson(route, { ...clearance, ...body, status: currentStatus });
  });
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/clearance/milestones`, async (route) => {
    if (route.request().method() === "GET") return fulfillJson(route, events);
    const body = route.request().postDataJSON() as { new_status: string; source_reference: string; notes?: string };
    const event = {
      id: `event-${events.length + 1}`,
      clearance_id: clearanceId,
      previous_status: currentStatus,
      new_status: body.new_status,
      source_reference: body.source_reference,
      notes: body.notes ?? null,
      effective_at: "2026-10-29T09:00:00Z",
      changed_by_id: "synthetic-m25-customs-user",
      changed_by_name: "Synthetic Clearance Operator",
      created_at: "2026-10-29T09:00:00Z",
    };
    currentStatus = body.new_status;
    events.push(event);
    return fulfillJson(route, event, 201);
  });

  await page.goto("/dashboard/logistics/arrivals");
  await page.getByLabel("Shipment:").selectOption(shipmentId);
  await page.getByRole("button", { name: "Customs Clearance (KRA)" }).click();
  await expect(page.getByText("No milestone history is available. Current recorded status: PENDING. Existing status may predate history capture.")).toBeVisible();
  await page.getByLabel("Next milestone").selectOption("DOCS_SUBMITTED");
  await page.getByLabel("Supporting reference").fill("SYN-IDF-2026-0001");
  await page.getByRole("button", { name: "Record milestone" }).click();
  await expect(page.getByText("PENDING → DOCS SUBMITTED")).toBeVisible();
  await expect(page.getByText("SYN-IDF-2026-0001")).toBeVisible();
  await expect(page.getByRole("listitem").getByText(/Synthetic Clearance Operator/)).toBeVisible();
  expect(events).toHaveLength(1);
  expect(events[0]).toMatchObject({ previous_status: "PENDING", new_status: "DOCS_SUBMITTED" });
});

test("clearance view-only users can see history without milestone controls", async ({ page }) => {
  await signIn(page, ["logistics.view"]);
  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{
    id: shipmentId,
    shipment_no: "SYN-M25-READONLY-CLEARANCE",
    status: "ARRIVED_PORT",
    mode: "SEA",
    origin_country: "Turkey",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Synthetic destination port",
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
  }]));
  await page.route("**/api/v1/logistics/arrivals/alerts**", (route) => fulfillJson(route, []));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/arrival`, (route) => fulfillJson(route, {
    id: "33333333-3333-4333-8333-333333333333",
    shipment_id: shipmentId,
    created_at: "2026-10-29T08:00:00Z",
  }));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/clearance`, (route) => fulfillJson(route, {
    id: clearanceId,
    shipment_id: shipmentId,
    status: "PENDING",
    created_at: "2026-10-29T08:00:00Z",
  }));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/clearance/milestones`, (route) => fulfillJson(route, []));

  await page.goto("/dashboard/logistics/arrivals");
  await page.getByLabel("Shipment:").selectOption(shipmentId);
  await page.getByRole("button", { name: "Customs Clearance (KRA)" }).click();
  await expect(page.getByText("View-only access: logistics.edit permission is required to record milestones.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Record milestone" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save Clearance" })).toHaveCount(0);
});
