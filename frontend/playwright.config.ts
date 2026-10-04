import { defineConfig, devices } from "@playwright/test";

// Browser tests run against a production build of the frontend (built with NEXT_PUBLIC_API_BASE_URL pointing at
// the mock API) so they see what users see. They use the Chrome that is already installed (channel "chrome"),
// which is present on GitHub-hosted runners, so no browser download is needed.
const WEB_PORT = 3100;
const API_PORT = 8100;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1280, height: 800 } } },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } },
  ],
  webServer: [
    {
      command: "node e2e/mock-api.mjs",
      url: `http://localhost:${API_PORT}/health`,
      env: { MOCK_API_PORT: String(API_PORT) },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `npx next start -p ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
