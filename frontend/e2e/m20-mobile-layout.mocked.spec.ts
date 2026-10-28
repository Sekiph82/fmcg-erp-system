import { expect, test } from "playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("synthetic ERP dashboard and integration navigation stay readable on a phone", async ({ page, context }) => {
  const baseUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  if (!new Set(["localhost", "127.0.0.1", "::1", "[::1]"]).has(baseUrl.hostname.toLowerCase())) {
    throw new Error("Synthetic mobile test must use a loopback E2E_BASE_URL; refusing to send its test cookie remotely.");
  }
  await context.addCookies([{
    name: "erp_access_token",
    value: "synthetic-m20-mobile-session",
    url: baseUrl.origin,
    httpOnly: true,
    sameSite: "Lax",
  }]);

  const dashboard = {
    generated_at: "2026-10-29T08:00:00Z",
    production: {
      active_orders: 6,
      today_planned_qty: 120,
      today_actual_qty: 60,
      completion_rate: 50,
      machines_down: 0,
      open_breakdowns: 0,
      trend_7d: [],
    },
    inventory: {
      total_stock_value: 85000,
      total_sku_count: 8,
      critical_low_stock_count: 0,
      low_stock_items: [],
    },
    sales: {
      today_invoices_amount: 42000,
      today_orders_count: 12,
      pending_payments_amount: 3000,
      overdue_invoices_count: 0,
      pending_shipments_count: 0,
      trend_7d: [],
    },
    mpesa: {
      today_collected: 16000,
      pending_count: 0,
      failed_today: 0,
      total_today: 20,
      success_rate: 95,
      last_10: [],
    },
    logistics: {
      in_transit: 1,
      arrived_port: 0,
      customs_hold: 0,
      delayed_count: 0,
      arrivals_this_week: 1,
    },
    alerts: [],
  };

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/auth/me")) {
      body = {
        id: "00000000-0000-4000-8000-000000000020",
        email: "synthetic-m20-planner@example.invalid",
        username: "synthetic-m20-planner",
        full_name: "Synthetic M20 Planner",
        is_active: true,
        is_superuser: true,
        must_change_password: false,
        roles: [],
        permission_codes: [],
        modules: [],
        scopes: [],
        feature_flags: {},
      };
    } else if (path.endsWith("/dashboard/summary")) {
      body = dashboard;
    } else if (path.endsWith("/notifications/unread-count")) {
      body = { unread_count: 0 };
    } else if (path.endsWith("/integrations/marketplace/categories")) {
      body = [{ category: "Synthetic FMCG", total: 1, active: 0 }];
    } else if (path.endsWith("/integrations/marketplace/events")) {
      body = [];
    } else if (path.endsWith("/integrations/marketplace")) {
      body = [];
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Executive Dashboard" })).toBeVisible();
  const dashboardMain = page.getByTestId("dashboard-main");
  const kpiCards = dashboardMain.locator(".glow-card");
  await expect(kpiCards).toHaveCount(8);
  for (let index = 0; index < 8; index += 1) {
    const card = kpiCards.nth(index);
    const label = card.locator("p").first();
    await expect(label).toBeVisible();
    const labelMetrics = await label.evaluate((element) => ({
      text: element.textContent?.trim() ?? "",
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
    }));
    expect(
      labelMetrics.scrollWidth,
      `KPI label "${labelMetrics.text}" is truncated (${labelMetrics.scrollWidth}px content in ${labelMetrics.clientWidth}px)`,
    ).toBeLessThanOrEqual(labelMetrics.clientWidth);
  }
  const firstCardWidth = await kpiCards.first().evaluate((element) => element.getBoundingClientRect().width);
  expect(firstCardWidth).toBeGreaterThan(300);
  await page.screenshot({ path: "test-results/m20-current-dashboard-mobile.png", fullPage: true });

  await page.goto("/dashboard/integrations");
  const tabs = [
    "Overview", "M-Pesa", "Sync", "Marketplace", "Barcode",
    "Marketing Sync", "Logs", "Webhooks", "Developer",
  ];
  for (const label of tabs) {
    const tab = page.getByTestId("dashboard-main").getByRole("button", { name: label, exact: true });
    await expect(tab).toBeVisible();
    const bounds = await tab.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      return { left: rect.left, right: rect.right, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
    });
    expect(bounds.left, label + " starts within the viewport").toBeGreaterThanOrEqual(0);
    expect(bounds.right, label + " ends within the viewport").toBeLessThanOrEqual(391);
    expect(bounds.scrollWidth, label + " text is not clipped").toBeLessThanOrEqual(bounds.clientWidth + 1);
  }

  const categoriesResponse = page.waitForResponse((response) => (
    response.url().includes("/api/v1/integrations/marketplace/categories")
  ));
  await page.getByTestId("dashboard-main").getByRole("button", { name: "Marketplace", exact: true }).click();
  expect((await categoriesResponse).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Integration Marketplace" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Synthetic FMCG (1)" })).toBeVisible();
  await page.screenshot({ path: "test-results/m20-current-integrations-mobile.png", fullPage: true });
});
