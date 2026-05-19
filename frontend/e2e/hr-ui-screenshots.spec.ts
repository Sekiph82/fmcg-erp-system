import { test, expect } from "playwright/test";
import fs from "fs";
import path from "path";

const MANIFEST_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/hr-ui-screenshot-manifest.json"
);
const SCREENSHOTS_BASE = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/captured"
);
const INDEX_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/hr-ui-screenshots-index.json"
);
const BASE_URL = "http://localhost:3000";

type Step =
  | { type: "goto"; url: string }
  | { type: "wait"; ms: number }
  | { type: "clickText"; text: string }
  | { type: "clickRole"; role: string; name: string; exact?: boolean }
  | { type: "clickTestId"; testId: string }
  | { type: "clickSelector"; selector: string }
  | { type: "evaluate"; script: string };

interface ManifestItem {
  id: string;
  label: string;
  path: string;
  steps: Step[];
}

const manifest: ManifestItem[] = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8"));

function loadIndex(): Record<string, { status: string; path: string; capturedAt: string }> {
  if (fs.existsSync(INDEX_PATH)) {
    return JSON.parse(fs.readFileSync(INDEX_PATH, "utf-8"));
  }
  return {};
}

function saveIndex(index: Record<string, { status: string; path: string; capturedAt: string }>) {
  fs.writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2), "utf-8");
}

function getFilteredItems(): ManifestItem[] {
  const pageFilter = process.env.HR_PAGE;
  const idsFilter = process.env.HR_IDS;
  const missingOnly = process.env.HR_MISSING_ONLY === "1";
  const requiredOnly = process.env.HR_REQUIRED_ONLY === "1";
  const priorityFilter = process.env.HR_PRIORITY;

  let items = manifest;

  if (pageFilter) {
    items = items.filter((i) => i.path.includes(pageFilter));
  }
  if (idsFilter) {
    const ids = idsFilter.split(",").map((s) => s.trim());
    items = items.filter((i) => ids.includes(i.id));
  }
  if (missingOnly) {
    const index = loadIndex();
    items = items.filter((i) => !index[i.id] || index[i.id].status !== "captured");
  }
  if (priorityFilter) {
    items = items.filter((i) => i.id.includes(priorityFilter));
  }

  return items;
}

const filteredItems = getFilteredItems();

for (const item of filteredItems) {
  test(`capture: ${item.label}`, async ({ page }) => {
    page.setDefaultTimeout(20000);

    for (const step of item.steps) {
      if (step.type === "goto") {
        await page.goto(`${BASE_URL}${step.url}`, { waitUntil: "networkidle" });
      } else if (step.type === "wait") {
        await page.waitForTimeout(step.ms);
      } else if (step.type === "clickText") {
        await page.getByText(step.text, { exact: true }).first().click();
      } else if (step.type === "clickRole") {
        await page
          .getByRole(step.role as Parameters<typeof page.getByRole>[0], {
            name: step.name,
            exact: step.exact ?? false,
          })
          .first()
          .click();
      } else if (step.type === "clickTestId") {
        await page.getByTestId(step.testId).click();
      } else if (step.type === "clickSelector") {
        await page.locator(step.selector).first().click();
      } else if (step.type === "evaluate") {
        await page.evaluate(step.script);
        await page.waitForTimeout(300);
      }
    }

    const outPath = path.join(SCREENSHOTS_BASE, item.path);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });

    const index = loadIndex();
    index[item.id] = { status: "captured", path: item.path, capturedAt: new Date().toISOString() };
    saveIndex(index);

    console.log(`  captured: ${item.path}`);
  });
}
