import { test } from "playwright/test";
import path from "path";
import fs from "fs";

const MANIFEST_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/crm-ui-screenshot-manifest.json"
);
const SCREENSHOTS_BASE = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/captured"
);
const INDEX_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/crm-ui-screenshots-index.json"
);

interface Step {
  type: "goto" | "wait" | "clickRole" | "clickText" | "clickTestId" | "clickSelector" | "evaluate";
  url?: string;
  ms?: number;
  role?: string;
  name?: string;
  text?: string;
  testId?: string;
  selector?: string;
  script?: string;
}

interface ManifestItem {
  id: string;
  label: string;
  path: string;
  steps: Step[];
}

function loadManifest(): ManifestItem[] {
  return JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8"));
}

function loadIndex(): Record<string, { status: string; path: string; captured_at?: string }> {
  if (fs.existsSync(INDEX_PATH)) {
    return JSON.parse(fs.readFileSync(INDEX_PATH, "utf-8"));
  }
  return {};
}

function saveIndex(index: Record<string, { status: string; path: string; captured_at?: string }>) {
  fs.writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2), "utf-8");
}

function filterItems(items: ManifestItem[]): ManifestItem[] {
  const page = process.env.CRM_PAGE;
  const ids = process.env.CRM_IDS;
  const missingOnly = process.env.CRM_MISSING_ONLY === "1";
  const requiredOnly = process.env.CRM_REQUIRED_ONLY === "1";
  const priority = process.env.CRM_PRIORITY;

  let filtered = items;

  if (page) {
    filtered = filtered.filter((item) => item.path.includes(`/crm/${page}/`));
  }
  if (ids) {
    const idSet = new Set(ids.split(",").map((s) => s.trim()));
    filtered = filtered.filter((item) => idSet.has(item.id));
  }
  if (missingOnly) {
    const index = loadIndex();
    filtered = filtered.filter((item) => {
      const entry = index[item.id];
      if (!entry) return true;
      if (entry.status === "failed") return true;
      const fullPath = path.join(SCREENSHOTS_BASE, item.path);
      return !fs.existsSync(fullPath);
    });
  }
  if (priority) {
    const priorityIds = new Set(priority.split(",").map((s) => s.trim()));
    const pri = filtered.filter((i) => priorityIds.has(i.id));
    const rest = filtered.filter((i) => !priorityIds.has(i.id));
    filtered = [...pri, ...rest];
  }

  return filtered;
}

const allItems = loadManifest();
const itemsToRun = filterItems(allItems);

for (const item of itemsToRun) {
  test(item.label, async ({ page }) => {
    const index = loadIndex();

    try {
      for (const step of item.steps) {
        if (step.type === "goto") {
          await page.goto(`http://localhost:3000${step.url}`, { waitUntil: "networkidle" });
        } else if (step.type === "wait") {
          await page.waitForTimeout(step.ms ?? 1000);
        } else if (step.type === "clickRole") {
          await page.getByRole(step.role as "button", { name: step.name }).click();
        } else if (step.type === "clickText") {
          await page.getByText(step.text!, { exact: true }).first().click();
        } else if (step.type === "clickTestId") {
          await page.getByTestId(step.testId!).click();
        } else if (step.type === "clickSelector") {
          await page.locator(step.selector!).first().click();
        } else if (step.type === "evaluate") {
          await page.evaluate(step.script!);
        }
      }

      const outPath = path.join(SCREENSHOTS_BASE, item.path);
      fs.mkdirSync(path.dirname(outPath), { recursive: true });
      await page.screenshot({ path: outPath, fullPage: false });

      index[item.id] = {
        status: "captured",
        path: item.path,
        captured_at: new Date().toISOString(),
      };
      saveIndex(index);
      console.log(`  ✓ ${item.id}`);
    } catch (err) {
      index[item.id] = {
        status: "failed",
        path: item.path,
        captured_at: new Date().toISOString(),
      };
      saveIndex(index);
      console.error(`  ✗ ${item.id}:`, err);
      throw err;
    }
  });
}
