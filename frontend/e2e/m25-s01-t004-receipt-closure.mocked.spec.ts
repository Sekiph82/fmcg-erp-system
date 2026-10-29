import { expect, test, type Page, type Route } from "playwright/test";

const shipmentId = "11111111-1111-4111-8111-111111111111";
const grnId = "22222222-2222-4222-8222-222222222222";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes: string[]) {
  await page.route("**/api/v1/**", (route) => fulfillJson(route, { detail: "Unmocked synthetic API request" }, 404));
  await page.route("**/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-m25-receipt-user",
    email: "m25-receipt@example.invalid",
    username: "synthetic-m25-receipt",
    full_name: "Synthetic Warehouse Operator",
    is_active: true,
    is_superuser: false,
    must_change_password: false,
    roles: [],
    permission_codes: permissionCodes,
    modules: ["logistics", "procurement"],
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
    value: "synthetic-m25-receipt-token",
    domain: testOrigin.hostname,
    path: "/",
    httpOnly: true,
    sameSite: "Lax",
  }]);
}

test("closes a Kenya shipment only against selected posted GRNs and records the closure", async ({ page }) => {
  await signIn(page, ["logistics.view", "logistics.edit", "procurement.view"]);
  let shipmentStatus = "OUT_FOR_DELIVERY";
  let closure: Record<string, unknown> | null = null;
  let arrival: Record<string, unknown> | null = null;
  const closureSubmissions: string[][] = [];
  const shipment = {
    id: shipmentId,
    shipment_no: "SYN-M25-RECEIPT-001",
    mode: "SEA",
    origin_country: "Turkey",
    origin_city: "Istanbul",
    origin_port: "Synthetic origin port",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Port of Mombasa",
    status: shipmentStatus,
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
  };
  const option = {
    id: grnId,
    grn_no: "SYN-GRN-2026-001",
    po_id: "33333333-3333-4333-8333-333333333333",
    po_no: "SYN-PO-2026-001",
    received_date: "2026-10-29",
    warehouse_id: "44444444-4444-4444-8444-444444444444",
    warehouse_name: "Synthetic Mombasa warehouse",
  };

  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{ ...shipment, status: shipmentStatus }]));
  await page.route("**/api/v1/logistics/arrivals/alerts**", (route) => fulfillJson(route, []));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/arrival`, async (route) => {
    if (arrival) return fulfillJson(route, arrival);
    return fulfillJson(route, { detail: "Arrival record not found" }, 404);
  });
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/receipt-options`, (route) => fulfillJson(route, closure ? [] : [option]));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/receipt-closure`, async (route) => {
    if (route.request().method() === "GET") {
      return closure ? fulfillJson(route, closure) : fulfillJson(route, { detail: "Not closed" }, 404);
    }
    const body = route.request().postDataJSON() as { grn_ids: string[] };
    closureSubmissions.push(body.grn_ids);
    closure = {
      id: "55555555-5555-4555-8555-555555555555",
      shipment_id: shipmentId,
      closed_at: "2026-10-29T12:30:00Z",
      closed_by_id: "synthetic-m25-receipt-user",
      closed_by_name: "Synthetic Warehouse Operator",
      grns: [option].filter((grn) => body.grn_ids.includes(grn.id)),
    };
    arrival = {
      id: "66666666-6666-4666-8666-666666666666",
      shipment_id: shipmentId,
      delivery_date: option.received_date,
      grn_id: grnId,
      created_at: "2026-10-29T12:30:00Z",
    };
    shipmentStatus = "DELIVERED";
    return fulfillJson(route, closure, 201);
  });

  await page.goto("/dashboard/logistics/arrivals");
  await page.getByLabel("Shipment:").selectOption(shipmentId);
  await expect(page.getByText("No arrival timeline has been recorded yet.")).toBeVisible();
  await page.getByLabel(/SYN-GRN-2026-001/).check();
  await page.getByRole("button", { name: "Close receipt with selected GRNs" }).click();
  await expect(page.getByText(/Shipment receipt closed on/)).toBeVisible();
  await expect(page.getByText(/SYN-GRN-2026-001 · PO SYN-PO-2026-001/)).toBeVisible();
  await expect(page.getByLabel("Delivered to Warehouse")).toHaveValue("2026-10-29");
  expect(closureSubmissions).toEqual([[grnId]]);
});

test("view-only logistics user cannot close a receipt", async ({ page }) => {
  await signIn(page, ["logistics.view"]);
  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{
    id: shipmentId,
    shipment_no: "SYN-M25-READONLY-RECEIPT",
    mode: "SEA",
    origin_country: "Turkey",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Port of Mombasa",
    status: "OUT_FOR_DELIVERY",
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
  }]));
  await page.route("**/api/v1/logistics/arrivals/alerts**", (route) => fulfillJson(route, []));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/arrival`, (route) => fulfillJson(route, { detail: "Not found" }, 404));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/receipt-closure`, (route) => fulfillJson(route, { detail: "Not closed" }, 404));
  await page.route(`**/api/v1/logistics/shipments/${shipmentId}/receipt-options`, (route) => fulfillJson(route, []));

  await page.goto("/dashboard/logistics/arrivals");
  await page.getByLabel("Shipment:").selectOption(shipmentId);
  await expect(page.getByText("No unused posted GRNs are linked to this shipment yet. Post a warehouse receipt in Procurement first.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Close receipt with selected GRNs" })).toHaveCount(0);
});
