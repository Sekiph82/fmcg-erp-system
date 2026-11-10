import { expect, test, type Page, type Route } from "playwright/test";

const reservationId = "22222222-2222-4222-8222-222222222222";
const reservationLineId = "33333333-3333-4333-8333-333333333333";
const productionOrderId = "44444444-4444-4444-8444-444444444444";
const actorId = "11111111-1111-4111-8111-111111111111";

const reservation = {
  id: reservationId,
  reservation_no: "M24-SYNTHETIC-RES-001",
  production_order_id: productionOrderId,
  status: "ACTIVE",
  lines: [{
    id: reservationLineId,
    reservation_id: reservationId,
    line_no: 1,
    item_type: "material",
    material_id: "55555555-5555-4555-8555-555555555555",
    material_name: "Synthetic ingredient",
    lot_number: "SYNTHETIC-LOT-001",
    warehouse_id: "66666666-6666-4666-8666-666666666666",
    quantity_required: 5,
    quantity_reserved: 5,
    quantity_issued: 0,
    uom: "kg",
  }],
};

function issueTransaction(quantity: number) {
  return {
    id: "77777777-7777-4777-8777-777777777777",
    flow_no: "M24-SYNTHETIC-ISSUE-001",
    flow_type: "RAW_ISSUE",
    flow_mode: "ONE_STEP",
    status: "POSTED",
    production_order_id: productionOrderId,
    source_document_type: "MATERIAL_RESERVATION",
    source_document_id: reservationId,
    transaction_datetime: "2026-11-08T08:00:00Z",
    lines: [{
      id: "88888888-8888-4888-8888-888888888888",
      transaction_id: "77777777-7777-4777-8777-777777777777",
      line_no: 1,
      item_type: "material",
      material_id: reservation.lines[0].material_id,
      reservation_line_id: reservationLineId,
      quantity,
      uom: "kg",
      quality_status: "RELEASED",
      movement_reason: "PRODUCTION_ISSUE",
      issue_flag: true,
      return_flag: false,
      scrap_flag: false,
      material_name: "Synthetic ingredient",
      lot_number: "SYNTHETIC-LOT-001",
    }],
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installSyntheticApi(page: Page) {
  const baseUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  if (!new Set(["localhost", "127.0.0.1", "::1", "[::1]"]).has(baseUrl.hostname.toLowerCase())) {
    throw new Error("M24 mocked acceptance requires a loopback E2E_BASE_URL.");
  }
  await page.context().addCookies([{
    name: "erp_access_token",
    value: "synthetic-m24-material-flow-token",
    url: baseUrl.origin,
    httpOnly: true,
    sameSite: "Lax",
  }]);

  const posts: Array<{ path: string; body: Record<string, unknown> }> = [];
  let transactions: ReturnType<typeof issueTransaction>[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/auth/me")) {
      return fulfillJson(route, {
        id: actorId,
        email: "m24@example.invalid",
        username: "synthetic-m24-user",
        full_name: "Synthetic M24 User",
        is_active: true,
        is_superuser: true,
        must_change_password: false,
        roles: [],
        permission_codes: [],
        modules: ["inventory", "production"],
        scopes: [],
        feature_flags: {},
      });
    }
    if (url.pathname.endsWith("/modules/manifest")) {
      return fulfillJson(route, { permission_codes: [], visible_permission_codes: [] });
    }
    if (url.pathname === "/api/v1/material-flow/reservations" && request.method() === "GET") {
      return fulfillJson(route, [reservation]);
    }
    if (url.pathname === "/api/v1/material-flow/transactions" && request.method() === "GET") {
      return fulfillJson(route, transactions.filter((transaction) => transaction.flow_type === url.searchParams.get("flow_type")));
    }
    if (url.pathname === `/api/v1/material-flow/reservations/${reservationId}/issue` && request.method() === "POST") {
      const body = request.postDataJSON() as Record<string, unknown>;
      posts.push({ path: url.pathname, body });
      const lines = body.lines as Array<{ quantity: number }>;
      transactions = [issueTransaction(lines[0].quantity)];
      return fulfillJson(route, transactions[0], 201);
    }
    return fulfillJson(route, []);
  });
  return { posts };
}

test.describe("M24 material issue UI with synthetic API", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("posts only the selected reserved line and shows the confirmed issue", async ({ page }) => {
    const api = await installSyntheticApi(page);
    await page.goto("/dashboard/material-flow/issue");

    await expect(page.getByRole("heading", { name: "Issue Reserved Materials" })).toBeVisible();
    await page.getByLabel("Reservation").selectOption(reservationId);
    await page.getByLabel("Issue quantity for reservation line 1").fill("2.5");
    await page.getByRole("button", { name: "Post raw-material issue" }).click();

    await expect(page.getByRole("status")).toContainText("M24-SYNTHETIC-ISSUE-001");
    expect(api.posts).toHaveLength(1);
    expect(api.posts[0].path).toBe(`/api/v1/material-flow/reservations/${reservationId}/issue`);
    expect(api.posts[0].body).toMatchObject({
      lines: [{ reservation_line_id: reservationLineId, quantity: 2.5 }],
    });
    expect(api.posts[0].body.idempotency_key).toEqual(expect.any(String));
  });
});
