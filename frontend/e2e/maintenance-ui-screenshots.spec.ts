import { test } from "playwright/test";
import path from "path";
import fs from "fs";

const MANIFEST_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/maintenance-ui-screenshot-manifest.json"
);
const SCREENSHOTS_DIR = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/captured"
);
const INDEX_PATH = path.resolve(
  __dirname,
  "../../docs/user-manual/screenshots/maintenance-ui-screenshots-index.json"
);
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8"));

const PRIORITY_IDS = process.env.MAINTENANCE_PRIORITY
  ? new Set(process.env.MAINTENANCE_PRIORITY.split(",").map((s) => s.trim()))
  : null;

const MISSING_ONLY = process.env.MAINTENANCE_MISSING_ONLY === "1";

const SELECTED_IDS = process.env.MAINTENANCE_IDS
  ? new Set(process.env.MAINTENANCE_IDS.split(",").map((s) => s.trim()))
  : null;

const screenshots: Array<{ id: string; path: string; capturedAt: string }> = [];

for (const shot of manifest.screenshots) {
  const outPath = path.join(SCREENSHOTS_DIR, shot.path);

  const skip =
    (SELECTED_IDS && !SELECTED_IDS.has(shot.id)) ||
    (PRIORITY_IDS && !PRIORITY_IDS.has(shot.id)) ||
    (MISSING_ONLY && fs.existsSync(outPath));

  test(shot.id, { skip }, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });

    for (const step of shot.steps) {
      if (step.type === "goto") {
        await page.goto(`${BASE_URL}${step.url}`, { waitUntil: "networkidle" });
      } else if (step.type === "wait") {
        await page.waitForTimeout(step.ms);
      } else if (step.type === "clickRole") {
        await page.getByRole(step.role, { name: step.name }).first().click();
      } else if (step.type === "clickText") {
        await page.getByText(step.text, { exact: false }).first().click();
      } else if (step.type === "clickTestId") {
        await page.getByTestId(step.testId).first().click();
      } else if (step.type === "clickSelector") {
        await page.locator(step.selector).first().click();
      } else if (step.type === "evaluate") {
        await page.evaluate(step.script);
      }
    }

    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    await page.screenshot({ path: outPath, fullPage: true });
    screenshots.push({ id: shot.id, path: shot.path, capturedAt: new Date().toISOString() });
  });
}

test.afterAll(() => {
  const index = {
    module: manifest.module,
    generatedAt: new Date().toISOString(),
    count: screenshots.length,
    screenshots,
  };
  fs.writeFileSync(INDEX_PATH, JSON.stringify(index, null, 2));
  console.log(`\nIndex written: ${INDEX_PATH} (${screenshots.length} screenshots)\n`);
});
