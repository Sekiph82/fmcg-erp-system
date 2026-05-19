/**
 * Module Manual Action Screenshot Capture
 *
 * Captures page overview + action/modal screenshots for module manual PDFs.
 * Reads manifest from docs/user-manual/screenshots/module-action-routes.json
 *
 * Env filters:
 *   MANUAL_ACTION_MODULE=manufacturing|supply-chain|all (default: all)
 *   MANUAL_ACTION_IDS=id1,id2,...                       (default: all)
 *   MANUAL_ACTION_ONLY_MISSING=true                     (skip already-captured)
 *
 * Usage (app must be running on localhost:3000):
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/manual-action-screenshots.spec.ts --project=chromium
 *   E2E_SKIP_WEBSERVER=1 MANUAL_ACTION_MODULE=manufacturing npx playwright test e2e/manual-action-screenshots.spec.ts --project=chromium
 *   E2E_SKIP_WEBSERVER=1 MANUAL_ACTION_IDS=recipes-new-recipe-modal npx playwright test e2e/manual-action-screenshots.spec.ts --project=chromium
 */

import { test, expect } from "playwright/test";
import fs from "fs";
import path from "path";

// ── Config ─────────────────────────────────────────────────────────────────────

const MODULE_FILTER = (process.env.MANUAL_ACTION_MODULE || "all").toLowerCase();
const ID_FILTER = (process.env.MANUAL_ACTION_IDS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const ONLY_MISSING = process.env.MANUAL_ACTION_ONLY_MISSING === "true";

// ── Paths ──────────────────────────────────────────────────────────────────────

const REPO_ROOT = path.resolve(__dirname, "../..");
const MANIFEST_FILE = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/module-action-routes.json"
);
const INDEX_FILE = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/action-screenshots-index.json"
);
const OUTPUT_DIR = path.join(
  REPO_ROOT,
  "docs/user-manual/screenshots/captured"
);

// ── Types ──────────────────────────────────────────────────────────────────────

interface ActionRoute {
  id: string;
  module: string;
  page: string;
  route: string;
  actionType: "modal" | "tab" | "drawer" | "page";
  actionLabel: string;
  selectorStrategy: "testid" | "text" | "route" | "role";
  selector: string | null;
  output: string;
  requiredForPdf: boolean;
  notes: string;
}

type CaptureStatus =
  | "captured"
  | "failed"
  | "not_implemented"
  | "skipped";

interface IndexEntry {
  id: string;
  module: string;
  page: string;
  route: string;
  actionType: string;
  actionLabel: string;
  screenshot: string | null;
  capturedAt: string;
  status: CaptureStatus;
  error?: string;
  failureClass?: string;
  notes: string;
}

type FailureClass =
  | "button-not-found"
  | "modal-not-opened"
  | "auth-failed"
  | "route-not-found"
  | "timeout"
  | "render-error"
  | "not-implemented"
  | "unknown";

// ── Helpers ────────────────────────────────────────────────────────────────────

function loadManifest(): ActionRoute[] {
  return JSON.parse(fs.readFileSync(MANIFEST_FILE, "utf-8")) as ActionRoute[];
}

function loadIndex(): Map<string, IndexEntry> {
  if (!fs.existsSync(INDEX_FILE)) return new Map();
  const arr = JSON.parse(fs.readFileSync(INDEX_FILE, "utf-8")) as IndexEntry[];
  return new Map(arr.map((e) => [e.id, e]));
}

function saveIndex(indexMap: Map<string, IndexEntry>): void {
  const arr = Array.from(indexMap.values());
  fs.writeFileSync(INDEX_FILE, JSON.stringify(arr, null, 2), "utf-8");
}

function classifyError(err: string): FailureClass {
  if (err.includes("login") || err.includes("auth")) return "auth-failed";
  if (err.includes("404") || err.includes("not found")) return "route-not-found";
  if (err.includes("button") || err.includes("locator")) return "button-not-found";
  if (err.includes("dialog") || err.includes("modal")) return "modal-not-opened";
  if (err.includes("Timeout") || err.includes("timeout")) return "timeout";
  if (err.includes("Application error") || err.includes("render")) return "render-error";
  return "unknown";
}

function absOut(output: string): string {
  return path.join(OUTPUT_DIR, output);
}

function ensureDir(p: string): void {
  fs.mkdirSync(path.dirname(p), { recursive: true });
}

// ── Main test ──────────────────────────────────────────────────────────────────

test.describe("Module Manual Action Screenshots", () => {
  let manifest: ActionRoute[];
  let indexMap: Map<string, IndexEntry>;

  test.beforeAll(() => {
    manifest = loadManifest();
    indexMap = loadIndex();
    fs.mkdirSync(path.join(OUTPUT_DIR, "actions"), { recursive: true });
  });

  test.afterAll(() => {
    saveIndex(indexMap);
  });

  // Filter routes
  function getRoutes(): ActionRoute[] {
    let routes = manifest;
    if (MODULE_FILTER !== "all") {
      routes = routes.filter((r) => r.module === MODULE_FILTER);
    }
    if (ID_FILTER.length > 0) {
      routes = routes.filter((r) => ID_FILTER.includes(r.id));
    }
    if (ONLY_MISSING) {
      routes = routes.filter((r) => {
        const existing = indexMap.get(r.id);
        if (!existing) return true;
        if (existing.status !== "captured") return true;
        const outPath = absOut(r.output);
        if (!fs.existsSync(outPath)) return true;
        return false;
      });
    }
    return routes;
  }

  // Generate one test per action route
  const routesForTest = JSON.parse(fs.readFileSync(MANIFEST_FILE, "utf-8")) as ActionRoute[];

  for (const route of routesForTest) {
    test(`capture: ${route.id}`, async ({ page }) => {
      // Re-load per-test so afterAll save picks up all results
      const localIndex = loadIndex();

      // Skip filter
      if (MODULE_FILTER !== "all" && route.module !== MODULE_FILTER) {
        test.skip();
        return;
      }
      if (ID_FILTER.length > 0 && !ID_FILTER.includes(route.id)) {
        test.skip();
        return;
      }
      if (ONLY_MISSING) {
        const existing = localIndex.get(route.id);
        if (existing?.status === "captured" && fs.existsSync(absOut(route.output))) {
          test.skip();
          return;
        }
      }

      let status: CaptureStatus = "failed";
      let error: string | undefined;
      let failureClass: FailureClass | undefined;
      let capturedFile: string | null = null;

      try {
        const base = (process.env.E2E_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
        const url = base + route.route;

        // Navigate to page
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
        await page.waitForTimeout(1500);

        // Auth check
        if (page.url().includes("/login")) {
          throw new Error("Redirected to login — auth issue");
        }

        // For "tab" or "route" actions — just capture page state
        if (route.actionType === "tab" || route.actionType === "page" || !route.selector) {
          await page.waitForTimeout(1000);
          const outPath = absOut(route.output);
          ensureDir(outPath);
          await page.screenshot({ path: outPath, fullPage: false });
          capturedFile = route.output;
          status = "captured";
        } else {
          // Click-triggered modal/drawer
          let locator: import("playwright/test").Locator;

          if (route.selectorStrategy === "testid") {
            locator = page.locator(route.selector!);
          } else if (route.selectorStrategy === "text") {
            locator = page.locator(route.selector!);
          } else if (route.selectorStrategy === "role") {
            locator = page.locator(route.selector!);
          } else {
            locator = page.locator(route.selector!);
          }

          // Check element exists
          const count = await locator.count();
          if (count === 0) {
            throw new Error(`Button/element not found: ${route.selector}`);
          }

          // Click to open modal
          await locator.first().click();
          await page.waitForTimeout(1200);

          // Capture with modal open
          const outPath = absOut(route.output);
          ensureDir(outPath);
          await page.screenshot({ path: outPath, fullPage: false });
          capturedFile = route.output;
          status = "captured";

          // Close modal (press Escape)
          await page.keyboard.press("Escape");
          await page.waitForTimeout(400);
        }

      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        error = msg;
        failureClass = classifyError(msg);
        status = "failed";
        console.error(`[FAILED] ${route.id}: ${msg} (${failureClass})`);
      }

      // Update index
      const entry: IndexEntry = {
        id: route.id,
        module: route.module,
        page: route.page,
        route: route.route,
        actionType: route.actionType,
        actionLabel: route.actionLabel,
        screenshot: capturedFile,
        capturedAt: new Date().toISOString(),
        status,
        ...(error && { error }),
        ...(failureClass && { failureClass }),
        notes: route.notes,
      };
      indexMap.set(route.id, entry);
      saveIndex(indexMap);

      // Always pass — failures are logged in index, not as test failures
      console.log(`[${status.toUpperCase()}] ${route.id}${error ? ` — ${error}` : ""}`);
    });
  }
});
