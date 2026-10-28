import { expect, test } from "playwright/test";

const VIEWPORTS = [
  { name: "1536x960", width: 1536, height: 960 },
  { name: "1920x1080", width: 1920, height: 1080 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "390x844", width: 390, height: 844 },
];

const INTEGRATION_TABS = [
  { label: "Overview", heading: "Integration Hub" },
  { label: "M-Pesa", heading: "M-Pesa Transactions" },
  { label: "Sync", heading: "Sync Status" },
  { label: "Marketplace", heading: "Integration Marketplace" },
  { label: "Barcode", heading: "Barcode System" },
  { label: "Marketing Sync", heading: "Marketing Sync" },
  { label: "Logs", heading: "Integration Logs" },
  { label: "Webhooks", heading: "Webhook / Event Engine" },
  { label: "Developer", heading: "Developer Portal" },
];

async function signIn(page: import("playwright/test").Page) {
  await page.goto("/login");
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD || "Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
}

test("dashboard and integration tabs fit the required desktop, tablet, and phone widths", async ({ page }) => {
  test.setTimeout(240_000);
  await signIn(page);

  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/dashboard");
    await expect(page.getByTestId("dashboard-main")).toBeVisible();
    await expect(page.getByTestId("dashboard-main")).not.toContainText("Loading…", { timeout: 15_000 });
    if (viewport.width <= 390) {
      const kpiCards = page.getByTestId("dashboard-main").locator(".glow-card");
      expect(await kpiCards.count(), "dashboard renders its KPI cards").toBeGreaterThanOrEqual(8);
      for (let index = 0; index < 8; index += 1) {
        const card = kpiCards.nth(index);
        const textFits = await card.locator("p").first().evaluate((label) => (
          label.scrollWidth <= label.clientWidth
        ));
        expect(textFits, "phone KPI labels remain fully readable").toBeTruthy();
      }
      const firstKpiWidth = await kpiCards.first().evaluate((card) => card.getBoundingClientRect().width);
      expect(firstKpiWidth, "phone KPI cards use the available width").toBeGreaterThan(300);
    }

    const dashboardGeometry = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      main: document.querySelector<HTMLElement>("[data-testid='dashboard-main']")?.getBoundingClientRect().toJSON(),
      content: document.querySelector<HTMLElement>("[data-testid='dashboard-main']")?.firstElementChild?.firstElementChild?.getBoundingClientRect().toJSON(),
    }));
    expect(dashboardGeometry.document, `dashboard horizontal overflow at ${viewport.name}`).toBeLessThanOrEqual(viewport.width + 1);
    expect(dashboardGeometry.main?.right, `dashboard main exceeds viewport at ${viewport.name}`).toBeLessThanOrEqual(viewport.width + 1);
    expect(dashboardGeometry.content?.width, `dashboard content remains narrow at ${viewport.name}`).toBeGreaterThanOrEqual((dashboardGeometry.main?.width ?? 0) * 0.78);
    await page.screenshot({
      path: `test-results/m20-dashboard-${viewport.name}.png`, fullPage: true,
      mask: [page.locator("p").filter({ hasText: /@/ })], maskColor: "#0b1120",
    });

    await page.goto("/dashboard/integrations");
    await expect(page.getByTestId("dashboard-main")).toBeVisible();
    for (const tab of INTEGRATION_TABS) {
      const tabButton = page.getByTestId("dashboard-main").getByRole("button", { name: tab.label, exact: true });
      const marketplaceCategories = tab.label === "Marketplace"
        ? page.waitForResponse((response) => (
          response.url().includes("/api/v1/integrations/marketplace/categories")
          && response.request().method() === "GET"
        ))
        : null;
      await tabButton.click();
      if (marketplaceCategories) {
        const response = await marketplaceCategories;
        expect(response.status(), "Marketplace categories endpoint succeeds").toBe(200);
      }
      await expect(page.getByTestId("dashboard-main").getByRole("heading", { name: tab.heading }).first()).toBeVisible();
      if (viewport.width <= 768) {
        const bounds = await tabButton.evaluate((element) => {
          const rect = element.getBoundingClientRect();
          return { left: rect.left, right: rect.right, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
        });
        expect(bounds.left, "tab starts inside the viewport").toBeGreaterThanOrEqual(0);
        expect(bounds.right, "tab ends inside the viewport").toBeLessThanOrEqual(viewport.width + 1);
        expect(bounds.scrollWidth, "tab label is not clipped").toBeLessThanOrEqual(bounds.clientWidth + 1);
      }
      const geometry = await page.evaluate((expectedHeading) => ({
        viewport: window.innerWidth,
        document: document.documentElement.scrollWidth,
        main: document.querySelector<HTMLElement>("[data-testid='dashboard-main']")?.getBoundingClientRect().toJSON(),
        content: (() => {
          const main = document.querySelector<HTMLElement>("[data-testid='dashboard-main']");
          const heading = [...(main?.querySelectorAll("h1") ?? [])].find((candidate) => candidate.textContent?.includes(expectedHeading));
          let node = heading?.parentElement;
          while (node && !node.classList.contains("px-4") && !node.classList.contains("p-6")) node = node.parentElement;
          return node?.getBoundingClientRect().toJSON();
        })(),
      }), tab.heading);
      expect(geometry.document, `${tab.label} horizontal overflow at ${viewport.name}`).toBeLessThanOrEqual(viewport.width + 1);
      expect(geometry.main?.right, `${tab.label} content exceeds viewport at ${viewport.name}`).toBeLessThanOrEqual(viewport.width + 1);
      expect(geometry.content?.width, `${tab.label} content remains narrow at ${viewport.name}`).toBeGreaterThanOrEqual((geometry.main?.width ?? 0) * 0.78);
    }
    await page.screenshot({
      path: `test-results/m20-integrations-${viewport.name}.png`, fullPage: true,
      mask: [page.locator("p").filter({ hasText: /@/ })], maskColor: "#0b1120",
    });
  }
});
