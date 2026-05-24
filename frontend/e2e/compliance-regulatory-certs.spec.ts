/**
 * Regression test: Compliance → Regulatory Certs tab must not produce
 * a JSON parse error from a bare /api/v1/... fetch hitting Next.js (HTML).
 *
 * Run against the Docker app:
 *   E2E_SKIP_WEBSERVER=1 npx playwright test e2e/compliance-regulatory-certs.spec.ts \
 *     --project=chromium --reporter=list
 */

import { test, expect } from "playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const ROUTE = "/dashboard/compliance?tab=regulatory-certs";

test.describe("Compliance — Regulatory Certs tab", () => {
  test("loads without JSON parse error", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    const uncaughtErrors: string[] = [];
    page.on("pageerror", (err) => uncaughtErrors.push(err.message));

    const url = `${BASE_URL}${ROUTE}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 45_000 });
    await page.waitForTimeout(2_000);

    const finalUrl = page.url();

    // Must not redirect to login
    expect(finalUrl, "redirected to login").not.toContain("/login");

    // Must not show application error
    const body = await page.content();
    expect(body, "shows Application error").not.toMatch(/application error|an unexpected error/i);

    // Must stay on compliance tab
    expect(finalUrl, "redirected away from compliance").toContain("/dashboard/compliance");

    // No JSON parse errors in console or uncaught
    const jsonErrors = [...consoleErrors, ...uncaughtErrors].filter(
      (e) =>
        e.includes("Unexpected token '<'") ||
        e.includes("is not valid JSON") ||
        e.includes("JSON.parse") ||
        e.includes("SyntaxError")
    );
    expect(
      jsonErrors,
      `JSON parse errors detected: ${jsonErrors.join(" | ")}`
    ).toHaveLength(0);

    // No 404 errors in console
    const notFoundErrors = [...consoleErrors, ...uncaughtErrors].filter(
      (e) => e.includes("404") || e.includes("Not Found")
    );
    expect(
      notFoundErrors,
      `404 errors detected: ${notFoundErrors.join(" | ")}`
    ).toHaveLength(0);

    // <main> must exist and contain text
    const mainEl = page.locator("main");
    const mainExists = (await mainEl.count()) > 0;
    const mainText = mainExists ? (await mainEl.first().innerText()).trim() : "";
    expect(
      mainExists && mainText.length > 0,
      "<main> missing or empty"
    ).toBe(true);

    // Regulatory Certs tab must be visible
    const tabEl = page.locator("text=Regulatory Certs").first();
    await expect(tabEl).toBeVisible({ timeout: 10_000 });
  });
});
