import { test } from "playwright/test";
import fs from "fs";
import path from "path";

const MANIFEST_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/logistics-ui-screenshot-manifest.json"
);
const CAPTURED_DIR = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/captured"
);
const INDEX_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/logistics-ui-screenshots-index.json"
);

const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8"));

const IDS_FILTER   = process.env.LOGISTICS_IDS?.split(",").map((s) => s.trim()).filter(Boolean) ?? [];
const MISSING_ONLY = process.env.LOGISTICS_MISSING_ONLY === "1";
const PRIORITY     = process.env.LOGISTICS_PRIORITY?.split(",").map((s) => s.trim()).filter(Boolean) ?? [];

function shouldCapture(item: { id: string; output: string }) {
  if (IDS_FILTER.length > 0 && !IDS_FILTER.includes(item.id)) return false;
  if (PRIORITY.length > 0 && !PRIORITY.includes(item.id)) return false;
  if (MISSING_ONLY) {
    const dest = path.join(CAPTURED_DIR, item.output);
    if (fs.existsSync(dest)) return false;
  }
  return true;
}

const index: Record<string, { status: string; path: string; capturedAt: string }> = fs.existsSync(INDEX_PATH)
  ? JSON.parse(fs.readFileSync(INDEX_PATH, "utf-8"))
  : {};

function saveIndex() {
  fs.writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2), "utf-8");
}

test.describe("Logistics UI Screenshots", () => {
  for (const item of manifest.screenshots) {
    if (!shouldCapture(item)) continue;

    test(item.label, async ({ page }) => {
      test.setTimeout(90_000);

      for (const step of item.steps) {
        if (step.type === "goto") {
          await page.goto(step.url, { waitUntil: "networkidle" });
        } else if (step.type === "wait") {
          await page.waitForTimeout(step.ms);
        } else if (step.type === "clickRole") {
          await page.getByRole(step.role as "button", { name: step.name }).click();
        } else if (step.type === "clickText") {
          await page.getByText(step.text!, { exact: true }).first().click();
        } else if (step.type === "clickTestId") {
          await page.getByTestId(step.testId!).click();
        } else if (step.type === "clickSelector") {
          await page.locator(step.selector!).click();
        } else if (step.type === "evaluate") {
          await page.evaluate(step.script!);
        }
      }

      const dest = path.join(CAPTURED_DIR, item.output);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      await page.screenshot({ path: dest, fullPage: false });

      index[item.id] = {
        status: "captured",
        path: item.output,
        capturedAt: new Date().toISOString(),
      };
      saveIndex();

      console.log(`✓ ${item.id}`);
    });
  }
});
