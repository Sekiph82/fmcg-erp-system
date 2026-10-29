import { test as setup, expect } from "playwright/test";
import { createHmac } from "crypto";
import { lstat, readFile, realpath, writeFile } from "fs/promises";
import path from "path";

const authFile = process.env.E2E_STORAGE_STATE_PATH
  ? path.resolve(process.env.E2E_STORAGE_STATE_PATH)
  : path.join(__dirname, "../playwright/.auth/state.json");
const totpSecretFile = process.env.E2E_TOTP_SECRET_PATH
  ? path.resolve(process.env.E2E_TOTP_SECRET_PATH)
  : null;
const legacyAuthFile = path.resolve(path.join(__dirname, "../playwright/.auth/state.json"));
const authDirectory = path.resolve(path.join(__dirname, "../playwright/.auth"));

async function requireTaskOwnedAuthState(): Promise<void> {
  if (!process.env.E2E_STORAGE_STATE_PATH || authFile.toLowerCase() === legacyAuthFile.toLowerCase()) {
    throw new Error("Set E2E_STORAGE_STATE_PATH to a task-owned Playwright state file; the legacy auth state is protected.");
  }
  if (path.dirname(authFile).toLowerCase() !== authDirectory.toLowerCase()) {
    throw new Error("Task-owned Playwright state must remain inside frontend/playwright/.auth.");
  }
  if ((await realpath(authDirectory)).toLowerCase() !== authDirectory.toLowerCase()) {
    throw new Error("The Playwright auth directory must not resolve through a symlink.");
  }
  try {
    if ((await lstat(authFile)).isSymbolicLink()) {
      throw new Error("Task-owned Playwright state must not be a symlink.");
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
}

async function requireTaskOwnedTotpTarget(username: string): Promise<void> {
  if (process.env.E2E_ALLOW_REQUIRED_TOTP_ENROLLMENT !== "1") {
    throw new Error(
      "Privileged 2FA browser setup requires explicit E2E_ALLOW_REQUIRED_TOTP_ENROLLMENT=1 for a synthetic test account.",
    );
  }
  if (!process.env.E2E_STORAGE_STATE_PATH || !totpSecretFile) {
    throw new Error("Privileged 2FA browser setup requires separate task-owned storage-state and TOTP-secret paths.");
  }
  if (
    authFile.toLowerCase() === legacyAuthFile.toLowerCase() ||
    authFile.toLowerCase() === totpSecretFile.toLowerCase() ||
    totpSecretFile.toLowerCase() === legacyAuthFile.toLowerCase()
  ) {
    throw new Error("Task-owned browser state and TOTP secret must use distinct paths outside the legacy auth file.");
  }
  if (
    path.dirname(authFile).toLowerCase() !== authDirectory.toLowerCase() ||
    path.dirname(totpSecretFile).toLowerCase() !== authDirectory.toLowerCase()
  ) {
    throw new Error("Task-owned browser state and TOTP secret must remain inside frontend/playwright/.auth.");
  }
  if (!/^m20-virtual-[a-z0-9-]+$/i.test(username)) {
    throw new Error("Required TOTP browser setup is restricted to an explicitly synthetic m20-virtual-* account.");
  }
  if ((await realpath(authDirectory)).toLowerCase() !== authDirectory.toLowerCase()) {
    throw new Error("The Playwright auth directory must not resolve through a symlink.");
  }
  for (const filePath of [authFile, totpSecretFile]) {
    try {
      if ((await lstat(filePath)).isSymbolicLink()) {
        throw new Error("Task-owned browser state and TOTP secret must not use symlink paths.");
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }

  const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
  const appUrl = new URL(process.env.E2E_BASE_URL || "http://localhost:3000");
  const apiUrl = new URL(
    process.env.NEXT_PUBLIC_API_URL || process.env.E2E_API_URL || "http://localhost:8000",
  );
  if (!loopbackHosts.has(appUrl.hostname.toLowerCase()) || !loopbackHosts.has(apiUrl.hostname.toLowerCase())) {
    throw new Error("Privileged 2FA browser setup is limited to loopback UI and API targets.");
  }
}

function generateTotp(secret: string, now = Date.now()): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = secret
    .replace(/=+$/, "")
    .split("")
    .map((character) => {
      const value = alphabet.indexOf(character.toUpperCase());
      if (value < 0) throw new Error("The authenticator setup key is not valid Base32.");
      return value.toString(2).padStart(5, "0");
    })
    .join("");
  const keyBytes = Buffer.from(
    bits.match(/.{8}/g)?.map((byte) => Number.parseInt(byte, 2)) ?? [],
  );
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(now / 30_000)));
  const digest = createHmac("sha1", keyBytes).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const binary = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(binary % 1_000_000).padStart(6, "0");
}

async function readTotpSecret(): Promise<string | null> {
  if (!totpSecretFile) return null;
  try {
    return (await readFile(totpSecretFile, "utf8")).trim() || null;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

// All routes used in smoke tests — visited here to trigger Next.js dev-server
// compilation before any test runs, preventing ERR_EMPTY_RESPONSE under load.
const WARMUP_ROUTES = [
  // Workspace pages (section C)
  "/dashboard/sales",
  "/dashboard/inventory",
  "/dashboard/finance",
  "/dashboard/production",
  "/dashboard/hr",
  "/dashboard/quality",
  "/dashboard/marketing",
  "/dashboard/utility-management",
  "/dashboard/procurement",
  "/dashboard/documents",
  "/dashboard/admin",
  // Tab variants (section D) — each triggers a separate dynamic-import compilation
  "/dashboard/sales?tab=orders",
  "/dashboard/sales?tab=invoices",
  "/dashboard/sales?tab=van-sales",
  "/dashboard/inventory?tab=stock",
  "/dashboard/inventory?tab=shelf-life",
  "/dashboard/inventory?tab=cycle-count",
  "/dashboard/finance?tab=accounting",
  "/dashboard/finance?tab=fixed-assets",
  "/dashboard/finance?tab=bank-recon",
  "/dashboard/production?tab=orders",
  "/dashboard/production?tab=execution",
  "/dashboard/production?tab=material-flow",
  "/dashboard/hr?tab=employees",
  "/dashboard/hr?tab=recruitment",
  "/dashboard/hr?tab=expenses",
  "/dashboard/quality?tab=qms",
  "/dashboard/quality?tab=allergen",
  "/dashboard/quality?tab=inspections",
];

setup("authenticate as admin", async ({ page }) => {
  await requireTaskOwnedAuthState();
  const username = process.env.E2E_ADMIN_USERNAME || process.env.E2E_USERNAME;
  const password = process.env.E2E_ADMIN_PASSWORD || process.env.E2E_PASSWORD;
  if (!username || !password) {
    throw new Error("Set E2E_ADMIN_USERNAME/E2E_ADMIN_PASSWORD or E2E_USERNAME/E2E_PASSWORD for browser setup.");
  }

  await page.goto("/login");
  await expect(page.getByTestId("login-form")).toBeVisible();

  await page.getByTestId("login-username").fill(username);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();

  await page.waitForURL(/\/(?:dashboard|auth\/2fa(?:\/enroll)?)\b/, { timeout: 20_000 });

  if (page.url().endsWith("/auth/2fa/enroll")) {
    await requireTaskOwnedTotpTarget(username);
    const key = await page
      .locator("p")
      .filter({ hasText: "Manual setup key:" })
      .locator("strong")
      .innerText();
    const secret = key.trim();
    if (totpSecretFile) {
      try {
        const savedSecret = (await readFile(totpSecretFile, "utf8")).trim();
        if (savedSecret !== secret) {
          throw new Error("The saved task-owned TOTP secret differs from the active enrollment; use a fresh path.");
        }
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
        await writeFile(totpSecretFile, `${secret}\n`, { encoding: "utf8", flag: "wx", mode: 0o600 });
      }
    }
    await page.getByLabel("Authenticator code").fill(generateTotp(secret));
    await page.getByRole("button", { name: "Verify and continue" }).click();
    await expect(page.getByText("Two-factor authentication is enabled.")).toBeVisible();
    await page.getByRole("button", { name: "Continue to the ERP" }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  } else if (page.url().endsWith("/auth/2fa")) {
    await requireTaskOwnedTotpTarget(username);
    const secret = await readTotpSecret();
    if (!secret) {
      throw new Error(
        "The synthetic admin already has TOTP enabled. Set E2E_TOTP_SECRET_PATH to its task-owned secret file.",
      );
    }
    await page.getByLabel("Verification Code").fill(generateTotp(secret));
    await page.getByRole("button", { name: "Verify" }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  }

  // Save auth state (includes HttpOnly cookies) for all tests
  await page.context().storageState({ path: authFile });

  // Warm up every workspace route so the dev server compiles them before tests run.
  // The 2s pause after each navigation lets React hydrate and fire ssr:false dynamic
  // imports, which triggers server-side chunk compilation while we move to the next page.
  // Failures are swallowed — actual tests will retry.
  for (const route of WARMUP_ROUTES) {
    try {
      await page.goto(route, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await page.waitForTimeout(2_000);
    } catch {
      // non-fatal: test will handle via retries
    }
  }
});
