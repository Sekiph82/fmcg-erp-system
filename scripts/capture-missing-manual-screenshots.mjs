#!/usr/bin/env node
/**
 * Capture missing manual screenshots for ERP manuals.
 * Targets: payroll new-period-form, payroll-month-dropdown.
 * Also captures additional Kenya Go-Live beginner screenshots.
 */

import pkg from "../frontend/node_modules/playwright-core/index.js";
const { chromium } = pkg;
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const BASE_URL = "http://localhost:3000";
const PAYROLL_DIR = path.join(REPO_ROOT, "docs/user-manual/screenshots/captured/module-ui/finance-payroll/payroll");
const GOLIIVE_DIR = path.join(REPO_ROOT, "docs/user-manual/screenshots/captured/module-ui/kenya-go-live");

const CAPTURES = [
  // Payroll missing
  {
    name: "new-period-form",
    outDir: PAYROLL_DIR,
    route: "/dashboard/payroll",
    action: async (page) => {
      // Click the New Payroll Period button
      await page.waitForSelector("main", { timeout: 10000 });
      await page.waitForTimeout(1500);
      const btn = page.getByRole("button", { name: /new payroll period/i });
      if (await btn.count() > 0) {
        await btn.click();
        await page.waitForTimeout(1000);
      } else {
        // Try generic "New" button on payroll page
        const anyBtn = page.getByRole("button", { name: /new/i }).first();
        if (await anyBtn.count() > 0) {
          await anyBtn.click();
          await page.waitForTimeout(1000);
        }
      }
    },
  },
  {
    name: "payroll-month-dropdown",
    outDir: PAYROLL_DIR,
    route: "/dashboard/payroll",
    action: async (page) => {
      await page.waitForSelector("main", { timeout: 10000 });
      await page.waitForTimeout(1500);
      // Open new period form first
      const btn = page.getByRole("button", { name: /new payroll period/i });
      if (await btn.count() > 0) {
        await btn.click();
        await page.waitForTimeout(800);
      } else {
        const anyBtn = page.getByRole("button", { name: /new/i }).first();
        if (await anyBtn.count() > 0) {
          await anyBtn.click();
          await page.waitForTimeout(800);
        }
      }
      // Open month dropdown
      const monthSel = page.locator("select").first();
      if (await monthSel.count() > 0) {
        await monthSel.click();
        await page.waitForTimeout(500);
      } else {
        const combobox = page.getByRole("combobox").first();
        if (await combobox.count() > 0) {
          await combobox.click();
          await page.waitForTimeout(500);
        }
      }
    },
  },
];

// Kenya Go-Live additional screenshots - capture full-page views of key routes
const GOLIIVE_CAPTURES = [
  { name: "sidebar-navigation", route: "/dashboard/production", selector: "nav, aside, [role='navigation']" },
  { name: "module-overview-example", route: "/dashboard/procurement" },
  { name: "create-workflow-example", route: "/dashboard/sales" },
  { name: "approvals-queue", route: "/dashboard/approvals" },
  { name: "reports-filter-example", route: "/dashboard/analytics" },
];

async function loginAndGetPage(browser) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await ctx.newPage();
  await page.goto(`${BASE_URL}/login`);
  await page.getByTestId("login-username").fill("admin");
  await page.getByTestId("login-password").fill("Admin1234!");
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/dashboard/, { timeout: 15000 });
  return page;
}

(async () => {
  console.log("Launching browser...");
  const browser = await chromium.launch({ headless: true });

  // --- Payroll screenshots ---
  const page = await loginAndGetPage(browser);
  for (const cap of CAPTURES) {
    try {
      console.log(`Capturing: ${cap.name}`);
      await page.goto(`${BASE_URL}${cap.route}`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1200);
      if (cap.action) await cap.action(page);
      const outPath = path.join(cap.outDir, `${cap.name}.png`);
      fs.mkdirSync(cap.outDir, { recursive: true });
      await page.screenshot({ path: outPath, fullPage: false });
      const size = fs.statSync(outPath).size;
      console.log(`  ✅ ${outPath} (${(size/1024).toFixed(0)} KB)`);
    } catch (e) {
      console.log(`  ⚠ ${cap.name}: ${e.message.split("\n")[0]}`);
      // Take a fallback full-page screenshot
      const outPath = path.join(cap.outDir, `${cap.name}.png`);
      try {
        await page.screenshot({ path: outPath, fullPage: false });
        console.log(`  → fallback screenshot saved`);
      } catch {}
    }
  }

  // --- Kenya Go-Live additional screenshots ---
  fs.mkdirSync(GOLIIVE_DIR, { recursive: true });
  for (const cap of GOLIIVE_CAPTURES) {
    try {
      console.log(`Go-Live capture: ${cap.name}`);
      await page.goto(`${BASE_URL}${cap.route}`, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(1500);
      const outPath = path.join(GOLIIVE_DIR, `${cap.name}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      const size = fs.statSync(outPath).size;
      console.log(`  ✅ ${outPath} (${(size/1024).toFixed(0)} KB)`);
    } catch (e) {
      console.log(`  ⚠ ${cap.name}: ${e.message.split("\n")[0]}`);
    }
  }

  await browser.close();
  console.log("Done.");
})();
