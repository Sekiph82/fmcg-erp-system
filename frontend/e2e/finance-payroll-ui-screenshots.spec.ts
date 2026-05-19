/**
 * Finance & Payroll UI Screenshot Capture
 *
 * Reads finance-payroll-ui-screenshot-manifest.json, captures each item,
 * writes finance-payroll-ui-screenshots-index.json after every capture.
 *
 * Env filters:
 *   FINANCE_PAYROLL_PAGE=finance|cashbook|payroll|expenses|fixed-assets|bank-reconciliation|bank-api|tax|contracts|invoice-match|all
 *   FINANCE_PAYROLL_IDS=id1,id2,id3
 *   FINANCE_PAYROLL_REQUIRED_ONLY=true
 *   FINANCE_PAYROLL_MISSING_ONLY=true
 *   FINANCE_PAYROLL_PRIORITY=1|2|3
 *
 * Run (app must be running on localhost:3000):
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/finance-payroll-ui-screenshots.spec.ts --project=chromium --workers=1
 */

import { test } from "playwright/test";
import fs from "fs";
import path from "path";

// ── Paths ─────────────────────────────────────────────────────────────────────

const REPO_ROOT     = path.resolve(__dirname, "../..");
const MANIFEST_FILE = path.join(REPO_ROOT, "docs/user-manual/screenshots/finance-payroll-ui-screenshot-manifest.json");
const INDEX_FILE    = path.join(REPO_ROOT, "docs/user-manual/screenshots/finance-payroll-ui-screenshots-index.json");
const SCREENSHOT_DIR= path.join(REPO_ROOT, "docs/user-manual/screenshots/captured");

// ── Types ─────────────────────────────────────────────────────────────────────

interface OpenStep {
  type: string;
  url?: string;
  role?: string;
  name?: string;
  text?: string;
  selector?: string;
  ms?: number;
}

interface ManifestItem {
  id: string;
  module: string;
  page: string;
  route: string;
  type: string;
  label: string;
  requiredForPdf: boolean;
  priority: number;
  openSteps: OpenStep[];
  waitFor: string | null;
  output: string | null;
  caption: string;
  status: string;
  reason?: string;
}

interface IndexEntry {
  id: string;
  module: string;
  page: string;
  route: string;
  type: string;
  label: string;
  output: string | null;
  status: string;
  reason: string;
  capturedAt: string;
  usedInManual: boolean;
  usedInPdf: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadManifest(): ManifestItem[] {
  return JSON.parse(fs.readFileSync(MANIFEST_FILE, "utf-8"));
}

function loadIndex(): Map<string, IndexEntry> {
  if (!fs.existsSync(INDEX_FILE)) return new Map();
  try {
    const arr: IndexEntry[] = JSON.parse(fs.readFileSync(INDEX_FILE, "utf-8"));
    return new Map(arr.map((e) => [e.id, e]));
  } catch {
    return new Map();
  }
}

function saveIndex(m: Map<string, IndexEntry>): void {
  const arr = Array.from(m.values()).sort((a, b) => a.id.localeCompare(b.id));
  fs.writeFileSync(INDEX_FILE, JSON.stringify(arr, null, 2) + "\n", "utf-8");
}

// ── Load once at module level so test.skip works ──────────────────────────────

const MANIFEST = loadManifest();

// ── Main describe ─────────────────────────────────────────────────────────────

test.describe("Finance & Payroll UI Screenshots", () => {
  let indexMap: Map<string, IndexEntry>;

  test.beforeAll(() => {
    indexMap = loadIndex();

    for (const item of MANIFEST) {
      if (item.status === "captured_as_part_of_parent_screen" && !indexMap.has(item.id)) {
        indexMap.set(item.id, {
          id: item.id,
          module: item.module,
          page: item.page,
          route: item.route,
          type: item.type,
          label: item.label,
          output: null,
          status: "captured_as_part_of_parent_screen",
          reason: item.reason ?? "Visible in parent tab screenshot.",
          capturedAt: new Date().toISOString(),
          usedInManual: false,
          usedInPdf: false,
        });
      }
    }
    saveIndex(indexMap);
  });

  for (const item of MANIFEST) {
    test(`capture: ${item.id}`, async ({ page }) => {
      const PAGE_FILTER   = (process.env.FINANCE_PAYROLL_PAGE   || "all").toLowerCase();
      const IDS_FILTER    = (process.env.FINANCE_PAYROLL_IDS    || "").split(",").filter(Boolean);
      const REQUIRED_ONLY = process.env.FINANCE_PAYROLL_REQUIRED_ONLY === "true";
      const MISSING_ONLY  = process.env.FINANCE_PAYROLL_MISSING_ONLY  === "true";
      const MAX_PRIORITY  = parseInt(process.env.FINANCE_PAYROLL_PRIORITY || "3");

      if (item.status === "captured_as_part_of_parent_screen" || item.output === null) {
        test.skip();
        return;
      }

      if (PAGE_FILTER !== "all" && item.page !== PAGE_FILTER) { test.skip(); return; }
      if (IDS_FILTER.length > 0 && !IDS_FILTER.includes(item.id))  { test.skip(); return; }
      if (REQUIRED_ONLY && !item.requiredForPdf)                    { test.skip(); return; }
      if (item.priority > MAX_PRIORITY)                             { test.skip(); return; }
      if (MISSING_ONLY) {
        const existing = indexMap.get(item.id);
        const outPath = path.join(SCREENSHOT_DIR, item.output);
        if (existing?.status === "captured" && fs.existsSync(outPath)) { test.skip(); return; }
      }

      const base = (process.env.E2E_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
      let status  = "failed";
      let reason  = "";

      try {
        for (const step of item.openSteps) {
          if (step.type === "goto") {
            await page.goto(base + step.url!, { waitUntil: "networkidle" });
            await page.waitForTimeout(1500);
          } else if (step.type === "clickRole") {
            const loc = page.getByRole(step.role as any, { name: step.name!, exact: false });
            await loc.first().waitFor({ state: "visible", timeout: 8000 });
            await loc.first().click();
            await page.waitForTimeout(1200);
          } else if (step.type === "clickText") {
            const loc = page.getByText(step.text!, { exact: false });
            await loc.first().waitFor({ state: "visible", timeout: 8000 });
            await loc.first().click();
            await page.waitForTimeout(1200);
          } else if (step.type === "clickTestId") {
            const loc = page.getByTestId(step.selector!);
            await loc.first().waitFor({ state: "visible", timeout: 8000 });
            await loc.first().click();
            await page.waitForTimeout(1200);
          } else if (step.type === "clickSelector") {
            const loc = page.locator(step.selector!);
            await loc.first().waitFor({ state: "visible", timeout: 8000 });
            await loc.first().click();
            await page.waitForTimeout(800);
          } else if (step.type === "evaluate") {
            await page.evaluate(step.selector!);
            await page.waitForTimeout(500);
          } else if (step.type === "wait") {
            await page.waitForTimeout(step.ms ?? 1000);
          }
        }

        if (item.waitFor) {
          await page.waitForSelector(`text=${item.waitFor}`, { timeout: 8000 }).catch(() => {});
        }

        const isModal = ["button_modal", "import_dialog", "import_dialog_tab", "inline_form"].includes(item.type);
        if (isModal) await page.waitForTimeout(600);

        const outputPath = path.join(SCREENSHOT_DIR, item.output);
        fs.mkdirSync(path.dirname(outputPath), { recursive: true });
        await page.screenshot({ path: outputPath, fullPage: false });

        if (isModal) {
          await page.keyboard.press("Escape");
          await page.waitForTimeout(300);
        }

        status = "captured";
        console.log(`[CAPTURED] ${item.id}`);
      } catch (err: any) {
        reason = String(err?.message ?? err).slice(0, 300);
        console.log(`[FAILED] ${item.id}: ${reason}`);
      }

      indexMap.set(item.id, {
        id: item.id,
        module: item.module,
        page: item.page,
        route: item.route,
        type: item.type,
        label: item.label,
        output: item.output,
        status,
        reason,
        capturedAt: new Date().toISOString(),
        usedInManual: false,
        usedInPdf: false,
      });
      saveIndex(indexMap);
    });
  }
});
