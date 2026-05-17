import { defineConfig, devices } from "playwright/test";
import path from "path";

const baseURL = (process.env.E2E_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const apiURL = process.env.NEXT_PUBLIC_API_URL || process.env.E2E_API_URL || "http://localhost:8000";
const authFile = path.join(__dirname, "playwright/.auth/state.json");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 2,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: process.env.E2E_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120_000,
        env: {
          NEXT_PUBLIC_API_URL: apiURL,
        },
      },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
      timeout: 300_000, // 5 min — includes route warmup for all workspace + tab pages
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: authFile,
      },
      dependencies: ["setup"],
    },
  ],
});
