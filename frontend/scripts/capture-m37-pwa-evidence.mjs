// M37 evidence: installability + offline fallback (prod build) and phone-width screens (dev stack).
// Usage: PROD_URL=http://localhost:3100 DEV_URL=http://localhost:3000 E2E_PASSWORD=... node scripts/capture-m37-pwa-evidence.mjs
import { chromium, devices } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const OUT = new URL("../../coordination/milestones/M37/screenshots/", import.meta.url);
mkdirSync(OUT, { recursive: true });
const PROD = process.env.PROD_URL || "http://localhost:3100";
const DEV = process.env.DEV_URL || "http://localhost:3000";
const phone = { ...devices["Pixel 7"] };
const report = { generated_at: new Date().toISOString(), prod: {}, screens: [] };
const shot = (page, name) => page.screenshot({ path: new URL(`${name}.png`, OUT).pathname.replace(/^\/([A-Z]:)/, "$1"), fullPage: false });

const browser = await chromium.launch();

// 1) Prod build: SW, manifest installability, offline fallback
{
  const ctx = await browser.newContext(phone);
  const page = await ctx.newPage();
  await page.goto(`${PROD}/login`);
  await page.evaluate(() => navigator.serviceWorker.ready);
  const cdp = await ctx.newCDPSession(page);
  const { installabilityErrors } = await cdp.send("Page.getInstallabilityErrors");
  report.prod.installability_errors = installabilityErrors;
  report.prod.cached_paths = await page.evaluate(async () =>
    (await (await caches.open("povu-pwa-v2")).keys()).map((r) => new URL(r.url).pathname));
  await shot(page, "01-prod-login-phone");
  await ctx.setOffline(true);
  await page.goto(`${PROD}/dashboard/shop-floor/terminal`).catch(() => undefined);
  report.prod.offline_heading = await page.locator("h1").first().textContent();
  await shot(page, "02-prod-offline-fallback");
  await ctx.close();
}

// 2) Phone-width screens. With E2E_USERNAME/E2E_PASSWORD: real sign-in against the dev stack.
// Without: LAYOUT-ONLY evidence — the API is mocked with the real shop_floor_operator permission
// codes and empty lists; screenshots then prove responsive layout, not live data or auth.
const MOCK_USER = {
  id: "00000000-0000-4000-8000-000000000037", email: "m37@synthetic.invalid", username: "m37-mock-operator",
  full_name: "M37 Mock Operator (synthetic)", is_active: true, is_superuser: false, must_change_password: false,
  roles: [], modules: ["shop_floor", "production", "planning"], scopes: [], feature_flags: {},
  permission_codes: ["planning.view_own_scope", "production.view_own_scope", "production_execution.update_own_line", "shop_floor.view_own_scope"],
};
{
  const mocked = !process.env.E2E_USERNAME;
  report.screens_mode = mocked ? "mocked-api-layout-only" : "live-dev-session";
  const ctx = await browser.newContext(phone);
  const page = await ctx.newPage();
  if (mocked) {
    await ctx.addCookies([{ name: "erp_access_token", value: "layout-only", url: DEV }]);
    await ctx.route(/\/api\/v1\//, (route) => {
      const url = route.request().url();
      if (url.includes("/auth/me")) return route.fulfill({ json: MOCK_USER });
      return route.fulfill({ json: [] });
    });
    await page.goto(`${DEV}/dashboard`);
  } else {
    await page.goto(`${DEV}/login`);
    await page.getByTestId("login-username").fill(process.env.E2E_USERNAME);
    await page.getByTestId("login-password").fill(process.env.E2E_PASSWORD);
    await page.getByTestId("login-submit").click();
    await page.waitForURL(/\/(dashboard|auth)/, { timeout: 30_000 });
  }
  report.login_landing = new URL(page.url()).pathname;
  if (report.login_landing.startsWith("/dashboard")) {
    for (const [name, path] of [
      ["03-dashboard-phone", "/dashboard"],
      ["04-shop-floor-terminal-phone", "/dashboard/shop-floor/terminal"],
      ["05-mobile-approvals-phone", "/dashboard/mobile/approvals"],
      ["06-mobile-devices-phone", "/dashboard/mobile/devices"],
    ]) {
      await page.goto(`${DEV}${path}`);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.waitForTimeout(1500);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      report.screens.push({ name, path, final_path: new URL(page.url()).pathname, horizontal_overflow_px: overflow });
      await shot(page, name);
    }
  }
  await ctx.close();
}

await browser.close();
writeFileSync(new URL("report.json", OUT), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
