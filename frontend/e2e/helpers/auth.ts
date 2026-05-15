import { expect, Page, TestInfo } from "playwright/test";

export interface E2ECredentials {
  username: string;
  password: string;
}

export function credentials(kind: "admin" | "limited" | "default" = "default"): E2ECredentials | null {
  const username =
    kind === "admin"
      ? process.env.E2E_ADMIN_USERNAME || process.env.E2E_USERNAME
      : kind === "limited"
        ? process.env.E2E_LIMITED_USERNAME
        : process.env.E2E_USERNAME;
  const password =
    kind === "admin"
      ? process.env.E2E_ADMIN_PASSWORD || process.env.E2E_PASSWORD
      : kind === "limited"
        ? process.env.E2E_LIMITED_PASSWORD
        : process.env.E2E_PASSWORD;

  if (!username || !password) return null;
  return { username, password };
}

export function missingCredentialsMessage(kind: "admin" | "limited" | "default" = "default") {
  if (kind === "limited") {
    return "Set E2E_LIMITED_USERNAME and E2E_LIMITED_PASSWORD to run limited-role browser E2E checks.";
  }
  if (kind === "admin") {
    return "Set E2E_ADMIN_USERNAME/E2E_ADMIN_PASSWORD or E2E_USERNAME/E2E_PASSWORD to run authenticated browser E2E checks.";
  }
  return "Set E2E_USERNAME and E2E_PASSWORD to run authenticated browser E2E checks.";
}

export async function loginViaUi(page: Page, creds: E2ECredentials) {
  await page.goto("/login");
  await page.getByTestId("login-username").fill(creds.username);
  await page.getByTestId("login-password").fill(creds.password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 20_000 }).catch(() => null),
    page.getByTestId("login-submit").click(),
  ]);
  await expect(page).not.toHaveURL(/\/login$/);
}

export async function recordMissingData(testInfo: TestInfo, description: string) {
  testInfo.annotations.push({ type: "missing-data", description });
}
