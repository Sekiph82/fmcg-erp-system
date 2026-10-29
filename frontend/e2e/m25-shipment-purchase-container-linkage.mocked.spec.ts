import { expect, test, type Page, type Route } from "playwright/test";

const shipmentId = "11111111-1111-4111-8111-111111111111";
const poId = "22222222-2222-4222-8222-222222222222";
const linkId = "33333333-3333-4333-8333-333333333333";
const containerId = "44444444-4444-4444-8444-444444444444";

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function signIn(page: Page, permissionCodes = ["logistics.view", "logistics.create", "logistics.edit", "procurement.view", "procurement.create_all"]) {
  await page.route("**/api/v1/auth/me**", (route) => fulfillJson(route, {
    id: "synthetic-m25-logistics-user",
    email: "m25-logistics@example.invalid",
    username: "synthetic-m25-logistics",
    full_name: "Synthetic Logistics Tester",
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
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-m25-logistics-token",
    url: process.env.E2E_BASE_URL || "http://localhost:3000",
    httpOnly: true,
    sameSite: "Lax",
  }]);
}

test("links an eligible purchase order and its shipping container to one shipment", async ({ page }) => {
  await signIn(page);
  const shipment = {
    id: shipmentId,
    shipment_no: "SYN-M25-SHIP-001",
    mode: "SEA",
    origin_country: "Turkey",
    origin_city: "Istanbul",
    origin_port: "Port of Istanbul",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Port of Mombasa",
    carrier: "Synthetic Carrier",
    status: "IN_TRANSIT",
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
    container_count: 0,
    po_count: 0,
  };
  const order = {
    id: poId,
    po_no: "SYN-PO-001",
    supplier_id: "55555555-5555-4555-8555-555555555555",
    supplier_name: "Synthetic Supplier",
    order_date: "2026-10-20",
    expected_delivery_date: "2026-11-12",
    currency: "USD",
    exchange_rate: 1,
    status: "ORDERED",
    created_at: "2026-10-20T08:00:00Z",
    payment_status: "pending",
  };
  const links: Array<Record<string, unknown>> = [];
  const containers: Array<Record<string, unknown>> = [];
  const ownershipEvents: Array<Record<string, unknown>> = [];

  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{
    ...shipment,
    po_count: links.length,
    container_count: containers.length,
  }]));
  await page.route("**/api/v1/procurement/po/**", (route) => fulfillJson(route, [order]));
  await page.route("**/api/v1/logistics/shipments/*/po-links", async (route) => {
    if (route.request().method() === "GET") return fulfillJson(route, links);
    const created = {
      id: linkId,
      shipment_id: shipmentId,
      po_id: poId,
      po_no: order.po_no,
      supplier_name: order.supplier_name,
      inventory_owner_status: "UNCONFIRMED",
      notes: null,
      created_at: "2026-10-29T08:10:00Z",
    };
    links.push(created);
    return fulfillJson(route, created, 201);
  });
  await page.route("**/api/v1/logistics/po-links/*", (route) => {
    const index = links.findIndex((link) => link.id === linkId);
    if (index >= 0) links.splice(index, 1);
    return route.fulfill({ status: 204, body: "" });
  });
  await page.route("**/api/v1/logistics/shipments/*/po-links/*/ownership-events", (route) => fulfillJson(route, ownershipEvents));
  await page.route("**/api/v1/logistics/shipments/*/po-links/*/ownership", async (route) => {
    const body = route.request().postDataJSON() as { new_owner: string; source_reference: string; notes?: string };
    const event = {
      id: "66666666-6666-4666-8666-666666666666",
      shipment_po_link_id: linkId,
      previous_owner: links[0]?.inventory_owner_status ?? "UNCONFIRMED",
      new_owner: body.new_owner,
      source_reference: body.source_reference,
      notes: body.notes,
      effective_at: "2026-10-29T09:00:00Z",
      changed_by_id: "synthetic-m25-logistics-user",
      changed_by_name: "Synthetic Logistics Tester",
      created_at: "2026-10-29T09:00:00Z",
    };
    if (links[0]) links[0].inventory_owner_status = body.new_owner;
    ownershipEvents.push(event);
    return fulfillJson(route, event, 201);
  });
  await page.route("**/api/v1/logistics/containers/**", async (route) => {
    if (route.request().method() === "GET") return fulfillJson(route, containers);
    const body = route.request().postDataJSON() as Record<string, unknown>;
    const created = {
      id: containerId,
      shipment_id: shipmentId,
      shipment_no: shipment.shipment_no,
      container_no: body.container_no,
      container_type: body.container_type,
      status: "LOADING",
      created_at: "2026-10-29T08:12:00Z",
    };
    containers.push(created);
    return fulfillJson(route, created, 201);
  });

  await page.goto("/dashboard/logistics?tab=shipments");
  await expect(page.getByText(shipment.shipment_no)).toBeVisible();
  await page.getByRole("button", { name: "View POs & containers" }).click();
  await page.getByLabel("Purchase order", { exact: true }).selectOption(poId);
  await page.getByRole("button", { name: "Link purchase order" }).click();
  await expect(page.getByText(order.po_no)).toBeVisible();
  await expect(page.getByText("Ownership stays unconfirmed until a source reference is entered. Incoterm does not set ownership automatically.")).toBeVisible();
  await page.getByLabel("New inventory owner").selectOption("BUYER_OWNED");
  await page.getByLabel("Source document reference").fill("SYN-COMMERCIAL-CONTRACT-001");
  await page.getByRole("button", { name: "Record owner" }).click();
  await expect(page.getByText("BUYER OWNED", { exact: true })).toBeVisible();
  await expect(page.getByText(/UNCONFIRMED → BUYER OWNED/)).toBeVisible();
  expect(ownershipEvents).toHaveLength(1);

  await page.getByLabel("Container number").fill("SYNM25BOX01");
  await page.getByRole("button", { name: "Add container" }).click();
  await expect(page.getByText("SYNM25BOX01")).toBeVisible();
  expect(links).toHaveLength(1);
  expect(containers).toHaveLength(1);
  expect(containers[0]).toMatchObject({ shipment_id: shipmentId, container_no: "SYNM25BOX01" });
});

test("logistics view-only users can inspect links but cannot change them", async ({ page }) => {
  await signIn(page, ["logistics.view"]);
  await page.route("**/api/v1/logistics/shipments/", (route) => fulfillJson(route, [{
    id: shipmentId,
    shipment_no: "SYN-M25-READONLY",
    mode: "SEA",
    origin_country: "Turkey",
    origin_city: "Istanbul",
    origin_port: "Port of Istanbul",
    destination_country: "Kenya",
    destination_city: "Mombasa",
    destination_port: "Port of Mombasa",
    status: "IN_TRANSIT",
    currency: "USD",
    created_at: "2026-10-29T08:00:00Z",
    container_count: 0,
    po_count: 0,
  }]));
  await page.route("**/api/v1/logistics/shipments/*/po-links", (route) => fulfillJson(route, [{
    id: linkId,
    shipment_id: shipmentId,
    po_id: poId,
    po_no: "SYN-READONLY-PO",
    supplier_name: "Synthetic Supplier",
    inventory_owner_status: "UNCONFIRMED",
    created_at: "2026-10-29T08:10:00Z",
  }]));
  await page.route("**/api/v1/logistics/shipments/*/po-links/*/ownership-events", (route) => fulfillJson(route, []));
  await page.route("**/api/v1/logistics/containers/**", (route) => fulfillJson(route, []));

  await page.goto("/dashboard/logistics?tab=shipments");
  await page.getByRole("button", { name: "View POs & containers" }).click();
  await expect(page.getByText("You have view-only access to shipment links.")).toBeVisible();
  await expect(page.getByText("You have view-only access to ownership history.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Link purchase order" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Unlink" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Record owner" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Add container" })).toHaveCount(0);
});
