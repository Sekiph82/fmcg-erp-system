/**
 * User Manual Screenshot Capture
 *
 * Reads docs/user-manual/screenshots/routes.json, visits each route,
 * captures a 1440x900 PNG, and writes results to screenshots-index.json.
 *
 * Usage (Docker stack must be running):
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-screenshots.spec.ts \
 *     --project=chromium --reporter=list
 *
 * Or via npm script:
 *   npm run test:manual-screenshots
 *
 * Output:
 *   docs/user-manual/screenshots/captured/{seq}_{id}.png
 *   docs/user-manual/screenshots/screenshots-index.json
 *
 * Failures do NOT stop the run — they are recorded in the index with status=failed.
 */

import { test, expect } from "playwright/test";
import fs from "fs";
import path from "path";

// ── Paths ──────────────────────────────────────────────────────────────────────

const REPO_ROOT = path.resolve(__dirname, "../..");
const ROUTES_FILE = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/routes.json"
);
const INDEX_FILE = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/screenshots-index.json"
);
const OUTPUT_DIR = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/captured"
);

// ── Route type ─────────────────────────────────────────────────────────────────

interface RouteEntry {
  id: string;
  title: string;
  role: string;
  module: string;
  path: string;
  priority: number;
  capture: boolean;
  manualChapter?: string;
  notes?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function seq(n: number): string {
  return String(n).padStart(3, "0");
}

function filenameForRoute(index: number, id: string): string {
  return `${seq(index + 1)}_${id.replace(/[^a-z0-9_-]/gi, "_")}.png`;
}

function loadRoutes(): RouteEntry[] {
  const raw = fs.readFileSync(ROUTES_FILE, "utf-8");
  return JSON.parse(raw) as RouteEntry[];
}

// ── Single page capture ────────────────────────────────────────────────────────

async function capturePage(
  page: import("playwright/test").Page,
  url: string,
  outPath: string
): Promise<{ ok: boolean; error?: string }> {
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });

    // Fail if redirected back to login (session expired), but not if the route IS /login
    if (!url.includes("/login") && page.url().includes("/login")) {
      return { ok: false, error: "Redirected to login — auth issue" };
    }

    // Wait for h1 to appear (workspace renders); login page uses form instead
    if (url.includes("/login")) {
      await expect(page.getByTestId("login-form")).toBeVisible({ timeout: 15_000 });
    } else {
      const h1 = page.locator("h1").first();
      await expect(h1).toBeVisible({ timeout: 20_000 });
    }

    // Fail if error overlay visible
    const errorText = page.locator("text=Application error");
    if ((await errorText.count()) > 0) {
      return { ok: false, error: "Application error overlay visible" };
    }

    // Fail if 404
    const notFound = page.locator("text=404");
    if ((await notFound.count()) > 0) {
      return { ok: false, error: "404 page" };
    }

    // Short wait for data-fetching components to settle
    await page.waitForTimeout(800);

    await page.screenshot({
      path: outPath,
      fullPage: false,
    });

    return { ok: true };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, error: msg };
  }
}

// ── Test suite ─────────────────────────────────────────────────────────────────

test.describe("Manual Screenshot Capture", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
  });

  // 140 routes × ~8s each = ~20 minutes; allow plenty of headroom
  test.setTimeout(30 * 60 * 1000);

  test("capture all routes from routes.json", async ({ page }) => {
    const routes = loadRoutes();
    const captureRoutes = routes.filter((r) => r.capture !== false);

    fs.mkdirSync(OUTPUT_DIR, { recursive: true });

    const results: object[] = [];
    const capturedAt = new Date().toISOString();

    let captureIndex = 0;

    for (let i = 0; i < captureRoutes.length; i++) {
      const route = captureRoutes[i];
      const filename = filenameForRoute(captureIndex, route.id);
      const outPath = path.join(OUTPUT_DIR, filename);

      console.log(`[${seq(captureIndex + 1)}/${seq(captureRoutes.length)}] ${route.path} → ${filename}`);

      const result = await capturePage(
        page,
        route.path,
        outPath
      );

      results.push({
        id: route.id,
        title: route.title,
        path: route.path,
        role: route.role,
        module: route.module,
        priority: route.priority,
        screenshot: result.ok ? `captured/${filename}` : null,
        capturedAt,
        status: result.ok ? "captured" : "failed",
        ...(result.error ? { error: result.error } : {}),
      });

      captureIndex++;
    }

    // Write index
    fs.writeFileSync(INDEX_FILE, JSON.stringify(results, null, 2), "utf-8");

    const captured = results.filter((r: any) => r.status === "captured").length;
    const failed = results.filter((r: any) => r.status === "failed").length;

    console.log(`\nCapture complete: ${captured} captured, ${failed} failed`);
    console.log(`Index written to: ${INDEX_FILE}`);

    // Test passes regardless of individual failures — index records them all
    expect(results.length).toBeGreaterThan(0);
  });
});
