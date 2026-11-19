// M37.S04 end-to-end evidence on a phone viewport against a DISPOSABLE demo stack with synthetic data:
// dispenser weighs + issues a prepared lot and prints its label; operator starts the work order,
// scans the label at the machine, confirms consumption; a second scan of the same label is refused.
// Usage: APP_URL=http://localhost:3200 M37_DEMO_PASSWORD=... node scripts/capture-m37-barcode-flow-evidence.mjs
import { chromium, devices } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const OUT = new URL("../../coordination/milestones/M37/screenshots/s04/", import.meta.url);
mkdirSync(OUT, { recursive: true });
const APP = process.env.APP_URL || "http://localhost:3200";
const PW = process.env.M37_DEMO_PASSWORD;
if (!PW) throw new Error("Set M37_DEMO_PASSWORD (synthetic demo users on the disposable stack only)");
const phone = devices["Pixel 7"];
const file = (name) => new URL(`${name}.png`, OUT).pathname.replace(/^\/([A-Z]:)/, "$1");
const report = { generated_at: new Date().toISOString(), app: APP, steps: [] };
const step = (name, data = {}) => { report.steps.push({ name, ...data }); console.log(name, JSON.stringify(data)); };

async function signIn(ctx, username) {
  const page = await ctx.newPage();
  await page.goto(`${APP}/login`);
  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(PW);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/dashboard/, { timeout: 60_000 });
  return page;
}

const browser = await chromium.launch();
try {
  // 1) Dispenser (warehouse) — weigh + issue + label
  const whCtx = await browser.newContext(phone);
  const wh = await signIn(whCtx, "m37-dispenser");
  step("dispenser landing", { path: new URL(wh.url()).pathname });
  await wh.goto(`${APP}/dashboard/shop-floor/dispensing`);
  await wh.getByText("PO-M37-DEMO-001").waitFor({ timeout: 60_000 });
  await wh.screenshot({ path: file("01-dispensing-orders"), fullPage: true });
  const sugar = wh.locator("article", { hasText: "Sugar (synthetic)" });
  await sugar.getByRole("button", { name: "Dispense" }).click();
  // wrong material lot is refused before issuing
  await sugar.locator("input[id^=source-lot-]").fill("SAL-2611-A");
  await sugar.locator("input[id^=source-lot-]").press("Enter");
  await sugar.getByRole("alert").waitFor();
  step("wrong lot refused", { message: await sugar.getByRole("alert").textContent() });
  await wh.screenshot({ path: file("02-dispense-wrong-lot-refused"), fullPage: true });
  await sugar.locator("input[id^=source-lot-]").fill("SUG-2611-A");
  await sugar.locator("input[id^=source-lot-]").press("Enter");
  await sugar.getByTestId("dispense-source").waitFor();
  await sugar.locator("input[data-testid^=dispense-actual-]").fill("12.4");
  await wh.screenshot({ path: file("03-dispense-source-scanned"), fullPage: true });
  const popupPromise = wh.waitForEvent("popup");
  await sugar.getByRole("button", { name: /Issue to order/ }).click();
  const label = await popupPromise;
  await label.waitForLoadState();
  const preparedLotNo = (await label.title()).trim();
  await label.screenshot({ path: file("04-prepared-lot-label") });
  step("prepared lot issued + label", { preparedLotNo });
  await label.close();
  await wh.getByText(preparedLotNo).first().waitFor();
  await wh.screenshot({ path: file("05-dispensing-after-issue"), fullPage: true });

  // 2) Operator — session, start WO, scan label, confirm
  const opCtx = await browser.newContext(phone);
  const op = await signIn(opCtx, "m37-operator");
  step("operator landing", { path: new URL(op.url()).pathname });
  await op.goto(`${APP}/dashboard/shop-floor/terminal`);
  await op.locator("#shop-floor-operator-name").fill("Synthetic Operator");
  await op.locator("#shop-floor-line-id").fill("SYN-LINE-1");
  await op.getByRole("button", { name: "Start operator session" }).click();
  await op.getByText("Mixing tank").first().click();
  await op.getByRole("button", { name: "START", exact: true }).click();
  await op.getByRole("button", { name: "materials" }).click();
  await op.getByTestId("material-scan-input").waitFor({ timeout: 30_000 });
  await op.screenshot({ path: file("06-terminal-materials-scan"), fullPage: true });
  // scan with keyboard-wedge style input: code + Enter
  await op.getByTestId("material-scan-input").fill(preparedLotNo);
  await op.getByTestId("material-scan-input").press("Enter");
  await op.getByTestId("material-scan-preview").waitFor();
  step("scan preview", { text: (await op.getByTestId("material-scan-preview").textContent())?.slice(0, 200) });
  await op.screenshot({ path: file("07-terminal-scan-preview"), fullPage: true });
  await op.getByTestId("material-scan-confirm").click();
  await op.getByTestId("material-scan-message").waitFor();
  step("consumption", { message: await op.getByTestId("material-scan-message").textContent() });
  await op.screenshot({ path: file("08-terminal-consumed"), fullPage: true });
  // same label again → refused + logged
  await op.getByTestId("material-scan-input").fill(preparedLotNo);
  await op.getByTestId("material-scan-input").press("Enter");
  await op.getByTestId("material-scan-confirm").click();
  await op.getByText(/already consumed/).first().waitFor();
  step("rescan refused", { message: await op.getByTestId("material-scan-message").textContent() });
  await op.screenshot({ path: file("09-terminal-rescan-refused"), fullPage: true });
  const overflow = await op.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  step("phone overflow px", { overflow });
} finally {
  writeFileSync(new URL("report.json", OUT), JSON.stringify(report, null, 2));
  await browser.close();
}
