/**
 * User Manual Screenshot Capture (v2)
 *
 * Features:
 *   MANUAL_CAPTURE_ONLY_FAILED=true    retry only failed/missing routes
 *   MANUAL_CAPTURE_BATCH_SIZE=N        process N routes per run
 *   MANUAL_CAPTURE_BATCH_INDEX=N       which batch (0-based)
 *   MANUAL_CAPTURE_ROLE=module         filter by module name (sales|finance|hr|...)
 *   MANUAL_CAPTURE_IDS=id1,id2         filter by specific route IDs
 *
 * Usage (Docker stack must be running):
 *   E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots
 *   E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ONLY_FAILED=true npm run test:manual-screenshots
 *   E2E_SKIP_WEBSERVER=1 MANUAL_CAPTURE_ROLE=sales npm run test:manual-screenshots
 *
 * Progress is saved after each route — restartable.
 * Successful entries are never erased during failed-only recapture.
 */

import { test, expect } from "playwright/test";
import fs from "fs";
import path from "path";

// ── Config from env ────────────────────────────────────────────────────────────

const ONLY_FAILED = process.env.MANUAL_CAPTURE_ONLY_FAILED === "true";
const BATCH_SIZE = parseInt(process.env.MANUAL_CAPTURE_BATCH_SIZE || "0");
const BATCH_INDEX = parseInt(process.env.MANUAL_CAPTURE_BATCH_INDEX || "0");
const ROLE_FILTER = (process.env.MANUAL_CAPTURE_ROLE || "all").toLowerCase();
const ID_FILTER = (process.env.MANUAL_CAPTURE_IDS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 4000;
const INTER_ROUTE_DELAY_MS = 800;

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
const AUTH_STATE = path.join(__dirname, "../playwright/.auth/state.json");

// ── Types ──────────────────────────────────────────────────────────────────────

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

interface IndexEntry {
  id: string;
  title: string;
  path: string;
  role: string;
  module: string;
  priority: number;
  screenshot: string | null;
  capturedAt: string;
  status: "captured" | "failed";
  error?: string;
  failureClass?: string;
  filename: string;
}

type CaptureResult =
  | { ok: true }
  | { ok: false; error: string; failureClass: string };

// ── Helpers ────────────────────────────────────────────────────────────────────

function seq(n: number): string {
  return String(n).padStart(3, "0");
}

function filenameForRoute(globalIndex: number, id: string): string {
  return `${seq(globalIndex + 1)}_${id.replace(/[^a-z0-9_-]/gi, "_")}.png`;
}

function classifyError(err: string): string {
  if (err.includes("ERR_EMPTY_RESPONSE")) return "dev-server-crash";
  if (err.includes("ERR_CONNECTION_REFUSED")) return "server-down";
  if (err.includes("404 page")) return "route-not-found";
  if (err.includes("Redirected to login")) return "auth-failed";
  if (err.includes("Application error")) return "render-error";
  if (err.includes("Timeout") || err.includes("timeout")) return "timeout";
  if (err.includes("closed") || err.includes("Target page")) return "dev-server-crash";
  return "unknown";
}

function loadRoutes(): RouteEntry[] {
  return JSON.parse(fs.readFileSync(ROUTES_FILE, "utf-8")) as RouteEntry[];
}

function loadExistingIndex(): Map<string, IndexEntry> {
  if (!fs.existsSync(INDEX_FILE)) return new Map();
  const arr = JSON.parse(
    fs.readFileSync(INDEX_FILE, "utf-8")
  ) as IndexEntry[];
  return new Map(arr.map((e) => [e.id, e]));
}

function saveIndex(
  indexMap: Map<string, IndexEntry>,
  allRoutes: RouteEntry[]
): void {
  const idOrder = allRoutes.map((r) => r.id);
  const ordered: IndexEntry[] = [];
  for (const id of idOrder) {
    const entry = indexMap.get(id);
    if (entry) ordered.push(entry);
  }
  // Append any entries not in routes (safety)
  indexMap.forEach((entry, id) => {
    if (!idOrder.includes(id)) ordered.push(entry);
  });
  fs.writeFileSync(INDEX_FILE, JSON.stringify(ordered, null, 2), "utf-8");
}

function pngExists(filename: string): boolean {
  return fs.existsSync(path.join(OUTPUT_DIR, filename));
}

// ── Page capture ───────────────────────────────────────────────────────────────

async function capturePage(
  page: import("playwright/test").Page,
  url: string,
  outPath: string
): Promise<CaptureResult> {
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });

    if (!url.includes("/login") && page.url().includes("/login")) {
      return {
        ok: false,
        error: "Redirected to login — auth issue",
        failureClass: "auth-failed",
      };
    }

    if (url.includes("/login")) {
      await expect(page.getByTestId("login-form")).toBeVisible({
        timeout: 15_000,
      });
    } else {
      const h1 = page.locator("h1").first();
      await expect(h1).toBeVisible({ timeout: 20_000 });
    }

    const errorOverlay = page.locator("text=Application error");
    if ((await errorOverlay.count()) > 0) {
      return {
        ok: false,
        error: "Application error overlay visible",
        failureClass: "render-error",
      };
    }

    const notFound = page.locator("text=404");
    if ((await notFound.count()) > 0) {
      return {
        ok: false,
        error: "404 page",
        failureClass: "route-not-found",
      };
    }

    await page.waitForTimeout(1200);

    await page.screenshot({ path: outPath, fullPage: false });
    return { ok: true };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, error: msg, failureClass: classifyError(msg) };
  }
}

// ── Test suite ─────────────────────────────────────────────────────────────────

test.describe("Manual Screenshot Capture", () => {
  // 60 min — enough for 140 routes × retries
  test.setTimeout(60 * 60 * 1000);

  test("capture routes from routes.json", async ({ browser }) => {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });

    const allRoutes = loadRoutes();
    const indexMap = loadExistingIndex();
    const capturedAt = new Date().toISOString();

    // Global index map: route id → position in full routes array (for stable filenames)
    const globalPosMap = new Map(allRoutes.map((r, i) => [r.id, i]));

    // Seed index map for routes not yet tracked
    for (let i = 0; i < allRoutes.length; i++) {
      const r = allRoutes[i];
      if (!indexMap.has(r.id)) {
        indexMap.set(r.id, {
          id: r.id,
          title: r.title,
          path: r.path,
          role: r.role,
          module: r.module,
          priority: r.priority,
          screenshot: null,
          capturedAt: "",
          status: "failed",
          filename: filenameForRoute(i, r.id),
        });
      }
    }

    // ── Build filtered work list ──
    let toCapture = allRoutes.filter((r) => r.capture !== false);

    if (ONLY_FAILED) {
      toCapture = toCapture.filter((r) => {
        const entry = indexMap.get(r.id);
        if (!entry) return true;
        if (entry.status === "failed") return true;
        // Re-capture if PNG is missing even though status=captured
        if (
          entry.screenshot &&
          !pngExists(path.basename(entry.screenshot))
        )
          return true;
        return false;
      });
      console.log(`ONLY_FAILED mode: ${toCapture.length} routes to retry`);
    }

    if (ID_FILTER.length > 0) {
      const idSet = new Set(ID_FILTER);
      toCapture = toCapture.filter((r) => idSet.has(r.id));
      console.log(`ID filter: ${toCapture.length} routes`);
    }

    if (ROLE_FILTER !== "all") {
      toCapture = toCapture.filter(
        (r) =>
          r.module === ROLE_FILTER ||
          r.role === ROLE_FILTER ||
          r.module.startsWith(ROLE_FILTER)
      );
      console.log(`ROLE filter (${ROLE_FILTER}): ${toCapture.length} routes`);
    }

    if (BATCH_SIZE > 0) {
      const start = BATCH_INDEX * BATCH_SIZE;
      const before = toCapture.length;
      toCapture = toCapture.slice(start, start + BATCH_SIZE);
      console.log(
        `BATCH ${BATCH_INDEX} (size ${BATCH_SIZE}): routes ${start}–${start + toCapture.length - 1} of ${before}`
      );
    }

    if (toCapture.length === 0) {
      console.log("No routes to capture — all done or filter matched nothing.");
      expect(true).toBe(true);
      return;
    }

    // ── Auth context ──
    let ctx = await browser.newContext({
      storageState: AUTH_STATE,
      viewport: { width: 1440, height: 900 },
    });
    let page = await ctx.newPage();

    let capturedCount = 0;
    let failedCount = 0;

    for (let i = 0; i < toCapture.length; i++) {
      const route = toCapture[i];
      const globalIdx = globalPosMap.get(route.id) ?? i;
      const filename = filenameForRoute(globalIdx, route.id);
      const outPath = path.join(OUTPUT_DIR, filename);

      console.log(
        `[${seq(i + 1)}/${seq(toCapture.length)}] ${route.path} → ${filename}`
      );

      let result: CaptureResult = {
        ok: false,
        error: "not attempted",
        failureClass: "unknown",
      };

      for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        if (attempt > 0) {
          console.log(`  retry ${attempt}/${MAX_RETRIES - 1}...`);
          await new Promise((res) => setTimeout(res, RETRY_DELAY_MS));

          // Fresh context after crash
          const lastErr = !result.ok ? result.error : "";
          if (
            lastErr.includes("ERR_EMPTY_RESPONSE") ||
            lastErr.includes("closed") ||
            lastErr.includes("Target page") ||
            lastErr.includes("server-down")
          ) {
            console.log("  refreshing browser context after crash...");
            await ctx.close().catch(() => {});
            ctx = await browser.newContext({
              storageState: AUTH_STATE,
              viewport: { width: 1440, height: 900 },
            });
            page = await ctx.newPage();
          }
        }

        result = await capturePage(page, route.path, outPath);
        if (result.ok) break;
      }

      const entry: IndexEntry = {
        id: route.id,
        title: route.title,
        path: route.path,
        role: route.role,
        module: route.module,
        priority: route.priority,
        screenshot: result.ok ? `captured/${filename}` : null,
        capturedAt: result.ok ? capturedAt : "",
        status: result.ok ? "captured" : "failed",
        filename,
        ...(!result.ok
          ? { error: result.error, failureClass: result.failureClass }
          : {}),
      };

      indexMap.set(route.id, entry);
      // Persist after every route
      saveIndex(indexMap, allRoutes);

      if (result.ok) {
        capturedCount++;
      } else {
        failedCount++;
        console.log(`  FAILED: ${!result.ok ? result.error?.slice(0, 80) : ""}`);
      }

      // Breathing room between routes
      if (i < toCapture.length - 1) {
        await page.waitForTimeout(INTER_ROUTE_DELAY_MS);
      }
    }

    await ctx.close().catch(() => {});

    const total = Array.from(indexMap.values());
    const allCaptured = total.filter((e) => e.status === "captured").length;
    const allFailed = total.filter((e) => e.status === "failed").length;

    console.log(
      `\nBatch complete: ${capturedCount} captured, ${failedCount} failed`
    );
    console.log(
      `Index total: ${allCaptured} captured, ${allFailed} failed across all routes`
    );

    expect(toCapture.length).toBeGreaterThan(0);
  });
});
