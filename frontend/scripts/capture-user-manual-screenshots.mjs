#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const screenshotsRoot = path.join(repoRoot, "docs", "user-manual", "screenshots");
const routesPath = path.join(screenshotsRoot, "routes.json");
const indexPath = path.join(screenshotsRoot, "screenshots-index.json");

const baseUrl = (process.env.MANUAL_TEST_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const username = process.env.MANUAL_TEST_USERNAME;
const password = process.env.MANUAL_TEST_PASSWORD;
const viewport = { width: 1440, height: 1000 };

function slug(value) {
  return String(value || "page")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 90) || "page";
}

function instructions() {
  return [
    "Missing manual screenshot login credentials.",
    "",
    "Set these environment variables, then rerun:",
    "  MANUAL_TEST_BASE_URL=http://localhost:3000",
    "  MANUAL_TEST_USERNAME=<username>",
    "  MANUAL_TEST_PASSWORD=<password>",
    "  npm run manual:screenshots",
  ].join("\n");
}

async function ensureInputs() {
  if (!username || !password) {
    throw new Error(instructions());
  }

  const routesRaw = await fs.readFile(routesPath, "utf8").catch(() => {
    throw new Error(`Route manifest not found: ${routesPath}`);
  });

  const routes = JSON.parse(routesRaw);
  if (!Array.isArray(routes) || routes.length === 0) {
    throw new Error(`Route manifest is empty or invalid: ${routesPath}`);
  }
  return routes;
}

async function login(page) {
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.fill("#username", username);
  await page.fill("#password", password);

  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 20000 }).catch(() => null),
    page.click('button[type="submit"]'),
  ]);

  if (page.url().includes("/login")) {
    const errorText = await page.locator("text=Invalid username or password").first().isVisible().catch(() => false);
    throw new Error(errorText ? "Login failed: invalid username or password." : "Login failed: still on /login after submit.");
  }
}

async function visibleActions(page) {
  return page.locator("button, a, [role='button'], [role='menuitem']").evaluateAll((nodes) => {
    const seen = new Set();
    const labels = [];
    for (const node of nodes) {
      const element = node;
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if (style.visibility === "hidden" || style.display === "none" || rect.width === 0 || rect.height === 0) {
        continue;
      }
      const label = (element.getAttribute("aria-label") || element.textContent || "").replace(/\s+/g, " ").trim();
      if (!label || label.length > 80 || seen.has(label)) continue;
      seen.add(label);
      labels.push(label);
    }
    return labels.slice(0, 80);
  });
}

async function captureRoute(page, route) {
  if (route.capture === false) {
    return {
      ...route,
      screenshot: null,
      status: "skipped",
      error: "Route marked capture=false.",
      capturedAt: new Date().toISOString(),
      viewport: `${viewport.width}x${viewport.height}`,
      visibleActions: [],
    };
  }

  const moduleSlug = slug(route.module);
  const routeSlug = slug(route.id || route.path);
  const outputDir = path.join(screenshotsRoot, moduleSlug);
  const screenshotFile = path.join(outputDir, `${routeSlug}.png`);
  const relativeScreenshot = path.relative(screenshotsRoot, screenshotFile).replaceAll("\\", "/");

  try {
    await fs.mkdir(outputDir, { recursive: true });
    await page.goto(`${baseUrl}${route.path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => null);
    await page.screenshot({ path: screenshotFile, fullPage: true });
    return {
      ...route,
      screenshot: relativeScreenshot,
      status: "captured",
      error: null,
      capturedAt: new Date().toISOString(),
      viewport: `${viewport.width}x${viewport.height}`,
      visibleActions: await visibleActions(page),
    };
  } catch (error) {
    return {
      ...route,
      screenshot: null,
      status: "failed",
      error: error instanceof Error ? error.message : String(error),
      capturedAt: new Date().toISOString(),
      viewport: `${viewport.width}x${viewport.height}`,
      visibleActions: [],
    };
  }
}

async function main() {
  const routes = await ensureInputs();
  await fs.mkdir(screenshotsRoot, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();

  try {
    await login(page);
    const results = [];
    for (const route of routes) {
      results.push(await captureRoute(page, route));
      await fs.writeFile(indexPath, `${JSON.stringify(results, null, 2)}\n`, "utf8");
    }
  } finally {
    await browser.close();
  }

  console.log(`Screenshot index written to ${indexPath}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
